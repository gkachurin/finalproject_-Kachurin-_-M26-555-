"""Бизнес-логика приложения."""

from datetime import datetime, timedelta, timezone

from prettytable import PrettyTable

from valutatrade_hub.decorators import log_action, set_log_context
from valutatrade_hub.infra.database import DatabaseManager
from valutatrade_hub.infra.settings import SettingsLoader
from valutatrade_hub.parser_service.updater import build_updater

from .currencies import CURRENCY_REGISTRY, CryptoCurrency, get_currency
from .exceptions import ApiRequestError, CurrencyNotFoundError
from .models import Portfolio, User, Wallet
from .utils import validate_amount, validate_currency_code

BASE_CURRENCY = "USD"
MIN_PASSWORD_LENGTH = 4

current_user: User | None = None


# ---------- вспомогательные функции ----------


def _require_login() -> User:
    if current_user is None:
        raise ValueError("Сначала выполните login")
    return current_user


def _load_portfolio(user: User) -> Portfolio:
    records = DatabaseManager().read("portfolios_file") or []
    for record in records:
        if record["user_id"] == user.user_id:
            wallets = {
                code: Wallet(code, data["balance"])
                for code, data in record["wallets"].items()
            }
            return Portfolio(user, wallets)
    return Portfolio(user)


def _save_portfolio(portfolio: Portfolio) -> None:
    database = DatabaseManager()
    records = [
        record
        for record in (database.read("portfolios_file") or [])
        if record["user_id"] != portfolio.user_id
    ]
    records.append(
        {
            "user_id": portfolio.user_id,
            "wallets": {
                code: wallet.get_balance_info()
                for code, wallet in portfolio.wallets.items()
            },
        }
    )
    records.sort(key=lambda record: record["user_id"])
    database.write("portfolios_file", records)


def _get_or_create_wallet(portfolio: Portfolio, code: str) -> Wallet:
    return portfolio.get_wallet(code) or portfolio.add_currency(code)


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _lookup(pairs: dict, from_code: str, to_code: str):
    """Ищет прямую или обратную пару в кеше."""
    for key, inverted in (
        (f"{from_code}_{to_code}", False),
        (f"{to_code}_{from_code}", True),
    ):
        info = pairs.get(key)
        if not isinstance(info, dict):
            continue
        try:
            rate = float(info["rate"])
            updated_at = _parse_time(info["updated_at"])
        except (KeyError, TypeError, ValueError):
            continue
        if rate > 0:
            return (1 / rate if inverted else rate), updated_at
    return None


def _find_rate(pairs: dict, from_code: str, to_code: str):
    """Возвращает самый свежий курс: напрямую или через USD."""
    candidates = []
    direct = _lookup(pairs, from_code, to_code)
    if direct:
        candidates.append(direct)
    first = _lookup(pairs, from_code, BASE_CURRENCY)
    second = _lookup(pairs, BASE_CURRENCY, to_code)
    if first and second:
        candidates.append((first[0] * second[0], min(first[1], second[1])))
    return max(candidates, key=lambda item: item[1]) if candidates else None


def _read_pairs() -> dict:
    data = DatabaseManager().read("rates_file")
    return data.get("pairs", {}) if isinstance(data, dict) else {}


# ---------- пользователи ----------


@log_action("register")
def register_user(username: str, password: str) -> User:
    """Регистрирует пользователя и создаёт пустой портфель."""
    username = username.strip()
    if not username:
        raise ValueError("Имя пользователя не может быть пустым")

    database = DatabaseManager()
    users = database.read("users_file") or []

    if any(user["username"] == username for user in users):
        raise ValueError(f"Имя пользователя '{username}' уже занято")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError("Пароль должен быть не короче 4 символов")

    user_id = max((user["user_id"] for user in users), default=0) + 1
    user = User(user_id=user_id, username=username, hashed_password="", salt="")
    user.change_password(password)

    record = user.get_user_info()
    record["hashed_password"] = user.hashed_password
    record["salt"] = user.salt
    users.append(record)

    database.write("users_file", users)
    _save_portfolio(Portfolio(user))
    return user


@log_action("login")
def login_user(username: str, password: str) -> User:
    """Авторизует пользователя и открывает сессию."""
    global current_user

    for record in DatabaseManager().read("users_file") or []:
        if record["username"] == username:
            user = User(
                user_id=record["user_id"],
                username=record["username"],
                hashed_password=record["hashed_password"],
                salt=record["salt"],
                registration_date=datetime.fromisoformat(record["registration_date"]),
            )
            if not user.verify_password(password):
                raise ValueError("Неверный пароль")
            current_user = user
            return user

    raise ValueError(f"Пользователь '{username}' не найден")


# ---------- курсы ----------


def get_rate(from_currency: str, to_currency: str) -> tuple[float, datetime]:
    """Возвращает курс и время обновления с учётом TTL кеша."""
    from_code = get_currency(validate_currency_code(from_currency)).code
    to_code = get_currency(validate_currency_code(to_currency)).code
    now = datetime.now(timezone.utc)

    if from_code == to_code:
        return 1.0, now

    ttl = timedelta(seconds=SettingsLoader().get("rates_ttl", 300))
    found = _find_rate(_read_pairs(), from_code, to_code)
    if found and now - found[1] < ttl:
        return found

    build_updater().run_update()  # ApiRequestError, если все источники недоступны

    found = _find_rate(_read_pairs(), from_code, to_code)
    if found is None or now - found[1] >= ttl:
        raise ApiRequestError(
            f"Курс {from_code}→{to_code} недоступен. Повторите попытку позже."
        )
    return found


def update_rates(source: str | None = None) -> dict:
    """Запускает Parser Service."""
    return build_updater(source).run_update()


def get_cached_rates(
    currency: str | None = None,
    top: int | None = None,
    base: str | None = None,
) -> tuple[list[tuple[str, float, datetime]], str, str | None]:
    """Возвращает курсы из кеша: (строки, база, last_refresh)."""
    data = DatabaseManager().read("rates_file") or {}
    pairs = data.get("pairs", {})
    if not pairs:
        raise ValueError(
            "Локальный кеш курсов пуст. "
            "Выполните 'update-rates', чтобы загрузить данные."
        )

    base_code = BASE_CURRENCY
    if base:
        base_code = get_currency(validate_currency_code(base)).code
    codes = sorted({code for key in pairs for code in key.split("_")} - {base_code})

    rows = []
    for code in codes:
        found = _find_rate(pairs, code, base_code)
        if found:
            rows.append((code, found[0], found[1]))

    if currency:
        wanted = validate_currency_code(currency)
        rows = [row for row in rows if row[0] == wanted]
        if not rows:
            raise ValueError(f"Курс для '{wanted}' не найден в кеше.")

    if top is not None:
        if top <= 0:
            raise ValueError("--top должен быть положительным числом")
        crypto = {
            code
            for code, item in CURRENCY_REGISTRY.items()
            if isinstance(item, CryptoCurrency)
        }
        rows = sorted(
            (r for r in rows if r[0] in crypto), key=lambda r: r[1], reverse=True
        )[:top]

    return rows, base_code, data.get("last_refresh")


# ---------- портфель и сделки ----------


def show_portfolio(base_currency: str | None = None) -> str:
    """Показывает кошельки и итоговую стоимость в базовой валюте."""
    user = _require_login()
    requested = base_currency or SettingsLoader().get(
        "default_base_currency", BASE_CURRENCY
    )
    try:
        base = get_currency(requested.strip().upper()).code
    except CurrencyNotFoundError:
        raise ValueError(f"Неизвестная базовая валюта '{requested}'") from None

    wallets = _load_portfolio(user).wallets
    if not wallets:
        return "Ваш портфель пока пуст."

    rates = {
        f"{code}_{base}": get_rate(code, base)[0] for code in wallets if code != base
    }
    portfolio = _load_portfolio(user)
    total = portfolio.get_total_value(base, rates)

    table = PrettyTable(["Валюта", "Баланс", f"Стоимость в {base}"])
    for code, wallet in sorted(wallets.items()):
        rate = 1.0 if code == base else rates[f"{code}_{base}"]
        table.add_row([code, f"{wallet.balance:.4f}", f"{wallet.balance * rate:,.2f}"])
    table.add_row(["ИТОГО", "", f"{total:,.2f}"])

    return f"Портфель пользователя '{user.username}' (база: {base}):\n{table}"


@log_action("deposit")
def deposit_usd(amount: float) -> str:
    """Пополняет USD-кошелёк (симуляция ввода средств)."""
    user = _require_login()
    amount = validate_amount(amount)

    portfolio = _load_portfolio(user)
    wallet = _get_or_create_wallet(portfolio, BASE_CURRENCY)
    before = wallet.balance
    wallet.deposit(amount)
    _save_portfolio(portfolio)

    set_log_context(base=BASE_CURRENCY, before=before, after=wallet.balance)
    return (
        f"Пополнение выполнено: +{amount:,.2f} USD\n"
        f"- USD: было {before:,.2f} → стало {wallet.balance:,.2f}"
    )


@log_action("buy")
def buy_currency(currency_code: str, amount: float) -> str:
    """Покупает валюту за USD."""
    user = _require_login()
    code = get_currency(validate_currency_code(currency_code)).code
    amount = validate_amount(amount)
    if code == BASE_CURRENCY:
        raise ValueError(
            "Нельзя покупать USD за USD. Пополнить баланс: deposit --amount 100"
        )

    rate, _ = get_rate(code, BASE_CURRENCY)
    cost = amount * rate

    portfolio = _load_portfolio(user)
    usd_wallet = _get_or_create_wallet(portfolio, BASE_CURRENCY)
    wallet = _get_or_create_wallet(portfolio, code)
    before = wallet.balance

    usd_wallet.withdraw(cost)  # InsufficientFundsError, если не хватает USD
    wallet.deposit(amount)
    _save_portfolio(portfolio)

    set_log_context(rate=rate, base=BASE_CURRENCY, before=before, after=wallet.balance)
    return (
        f"Покупка выполнена: {amount:.4f} {code} по курсу {rate:,.2f} USD/{code}\n"
        f"Изменения в портфеле:\n"
        f"- {code}: было {before:.4f} → стало {wallet.balance:.4f}\n"
        f"Оценочная стоимость покупки: {cost:,.2f} USD"
    )


@log_action("sell")
def sell_currency(currency_code: str, amount: float) -> str:
    """Продаёт валюту, начисляя выручку в USD."""
    user = _require_login()
    code = get_currency(validate_currency_code(currency_code)).code
    amount = validate_amount(amount)
    if code == BASE_CURRENCY:
        raise ValueError("Нельзя продавать USD за USD")

    portfolio = _load_portfolio(user)
    wallet = portfolio.get_wallet(code)
    if wallet is None:
        raise ValueError(
            f"У вас нет кошелька '{code}'. Добавьте валюту: "
            "она создаётся автоматически при первой покупке."
        )

    before = wallet.balance
    wallet.withdraw(amount)  # InsufficientFundsError

    rate, _ = get_rate(code, BASE_CURRENCY)
    revenue = amount * rate
    _get_or_create_wallet(portfolio, BASE_CURRENCY).deposit(revenue)
    _save_portfolio(portfolio)

    set_log_context(rate=rate, base=BASE_CURRENCY, before=before, after=wallet.balance)
    return (
        f"Продажа выполнена: {amount:.4f} {code} по курсу {rate:,.2f} USD/{code}\n"
        f"Изменения в портфеле:\n"
        f"- {code}: было {before:.4f} → стало {wallet.balance:.4f}\n"
        f"Оценочная выручка: {revenue:,.2f} USD"
    )
