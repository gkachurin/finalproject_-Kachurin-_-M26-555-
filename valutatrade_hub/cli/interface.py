"""CLI: разбор команд и вывод результатов. Бизнес-логика живёт в core.usecases."""

import shlex

from prettytable import PrettyTable

from valutatrade_hub.core import usecases
from valutatrade_hub.core.currencies import CURRENCY_REGISTRY
from valutatrade_hub.core.exceptions import (
    ApiRequestError,
    CurrencyNotFoundError,
    InsufficientFundsError,
)

PROMPT = "valutatrade> "


def parse_arguments(parts: list[str]) -> dict[str, str]:
    """Разбирает аргументы вида --key value и --key=value."""
    args: dict[str, str] = {}
    index = 0
    while index < len(parts):
        part = parts[index]
        if not part.startswith("--"):
            raise ValueError(f"Неожиданный аргумент: {part}")
        key_value = part[2:]
        if "=" in key_value:
            key, value = key_value.split("=", 1)
            if not key or not value:
                raise ValueError(f"Некорректный аргумент: {part}")
            args[key] = value
            index += 1
        else:
            if index + 1 >= len(parts) or parts[index + 1].startswith("--"):
                raise ValueError(f"Для аргумента {part} не указано значение")
            args[key_value] = parts[index + 1]
            index += 2
    return args


def _amount(raw: str) -> float:
    """Преобразует строку в число или сообщает об ошибке."""
    try:
        return float(raw)
    except ValueError:
        raise ValueError("'amount' должен быть положительным числом") from None


def _format_rate(rate: float) -> str:
    """Форматирует курс с подходящей точностью."""
    if rate >= 1000:
        return f"{rate:,.2f}"
    if rate >= 1:
        return f"{rate:.4f}".rstrip("0").rstrip(".")
    return f"{rate:.8f}"


def _register(args: dict[str, str]) -> str:
    """Регистрирует пользователя."""
    user = usecases.register_user(args["username"], args["password"])
    return (
        f"Пользователь '{user.username}' зарегистрирован (id={user.user_id}). "
        f"Войдите: login --username {user.username} --password ****"
    )


def _login(args: dict[str, str]) -> str:
    """Выполняет вход."""
    user = usecases.login_user(args["username"], args["password"])
    return f"Вы вошли как '{user.username}'"


def _show_portfolio(args: dict[str, str]) -> str:
    """Показывает портфель и его стоимость в базовой валюте."""
    return usecases.show_portfolio(args.get("base"))


def _deposit(args: dict[str, str]) -> str:
    """Пополняет USD-кошелёк."""
    return usecases.deposit_usd(_amount(args["amount"]))


def _buy(args: dict[str, str]) -> str:
    """Покупает валюту за USD."""
    return usecases.buy_currency(args["currency"], _amount(args["amount"]))


def _sell(args: dict[str, str]) -> str:
    """Продаёт валюту за USD."""
    return usecases.sell_currency(args["currency"], _amount(args["amount"]))


def _get_rate(args: dict[str, str]) -> str:
    """Показывает курс пары и обратный курс."""
    from_code, to_code = args["from"].strip().upper(), args["to"].strip().upper()
    rate, updated_at = usecases.get_rate(from_code, to_code)
    return (
        f"Курс {from_code}→{to_code}: {_format_rate(rate)} "
        f"(обновлено: {updated_at:%Y-%m-%d %H:%M:%S})\n"
        f"Обратный курс {to_code}→{from_code}: {_format_rate(1 / rate)}"
    )


def _update_rates(args: dict[str, str]) -> str:
    """Запускает обновление курсов через Parser Service."""
    result = usecases.update_rates(args.get("source"))
    if result["errors"]:
        return (
            f"Обновление завершено с ошибками. Обновлено курсов: {result['updated']}.\n"
            + "\n".join(f"ERROR: {error}" for error in result["errors"])
            + "\nПодробности: logs/parser.log"
        )
    return (
        f"Обновление успешно. Обновлено курсов: {result['updated']}. "
        f"Последнее обновление: {result['last_refresh']}"
    )


def _show_rates(args: dict[str, str]) -> str:
    """Показывает курсы из локального кеша с фильтрами."""
    top = None
    if "top" in args:
        try:
            top = int(args["top"])
        except ValueError:
            raise ValueError("--top должен быть целым числом") from None

    rows, base, refreshed = usecases.get_cached_rates(
        args.get("currency"), top, args.get("base")
    )
    if not rows:
        return "Подходящих курсов в кеше нет."

    table = PrettyTable(["Пара", "Курс", "Обновлено"])
    for code, rate, updated_at in rows:
        table.add_row(
            [f"{code}_{base}", _format_rate(rate), f"{updated_at:%Y-%m-%d %H:%M:%S}"]
        )
    return f"Курсы из кеша (обновлено: {refreshed}):\n{table}"


# имя команды: (обработчик, обязательные аргументы, необязательные, пример)
COMMANDS = {
    "register": (
        _register,
        ("username", "password"),
        (),
        "register --username alice --password 1234",
    ),
    "login": (
        _login,
        ("username", "password"),
        (),
        "login --username alice --password 1234",
    ),
    "show-portfolio": (
        _show_portfolio,
        (),
        ("base",),
        "show-portfolio [--base USD]",
    ),
    "deposit": (_deposit, ("amount",), (), "deposit --amount 1000"),
    "buy": (
        _buy,
        ("currency", "amount"),
        (),
        "buy --currency BTC --amount 0.05",
    ),
    "sell": (
        _sell,
        ("currency", "amount"),
        (),
        "sell --currency BTC --amount 0.01",
    ),
    "get-rate": (_get_rate, ("from", "to"), (), "get-rate --from BTC --to USD"),
    "update-rates": (
        _update_rates,
        (),
        ("source",),
        "update-rates [--source coingecko|exchangerate]",
    ),
    "show-rates": (
        _show_rates,
        (),
        ("currency", "top", "base"),
        "show-rates [--currency BTC] [--top 2] [--base EUR]",
    ),
}


def handle_command(command: str) -> str:
    """Выполняет команду и возвращает текст для пользователя."""
    try:
        parts = shlex.split(command)
    except ValueError:
        return "Ошибка: незакрытые кавычки"
    if not parts:
        return "Введите команду."

    name, *rest = parts
    if name not in COMMANDS:
        return f"Неизвестная команда: {name}. Доступно: {', '.join(COMMANDS)}"

    handler, required, optional, usage = COMMANDS[name]
    try:
        args = parse_arguments(rest)
        if set(required) - set(args) or set(args) - set(required) - set(optional):
            return f"Использование: {usage}"
        return handler(args)

    except InsufficientFundsError as error:
        return str(error)
    except CurrencyNotFoundError as error:
        return (
            f"{error}. Поддерживаемые коды: {', '.join(CURRENCY_REGISTRY)}. "
            "Подробнее: get-rate --from BTC --to USD"
        )
    except ApiRequestError as error:
        return f"{error}\nПовторите попытку позже или проверьте подключение к сети."
    except ValueError as error:
        return str(error)


def run() -> None:
    """Запускает интерактивный цикл CLI."""
    print("Добро пожаловать в ValutaTrade Hub!")
    print("Введите команду или 'exit' для выхода.")
    while True:
        try:
            command = input(PROMPT).strip()
        except (KeyboardInterrupt, EOFError):
            print("\nДо свидания!")
            return
        if command.lower() == "exit":
            print("До свидания!")
            return
        print(handle_command(command))
