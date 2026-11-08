import hashlib
import math
import secrets
from datetime import datetime

from .exceptions import InsufficientFundsError


class User:
    """Представляет зарегистрированного пользователя системы."""

    def __init__(
        self,
        user_id: int,
        username: str,
        hashed_password: str,
        salt: str,
        registration_date: datetime | None = None,
    ) -> None:
        """Создаёт пользователя с проверкой всех полей."""
        if isinstance(user_id, bool) or not isinstance(user_id, int):
            raise TypeError("ID пользователя должен быть целым числом")

        if user_id <= 0:
            raise ValueError("ID пользователя должен быть положительным")

        if not isinstance(username, str) or not username.strip():
            raise ValueError("Имя пользователя не может быть пустым")

        if not isinstance(hashed_password, str):
            raise TypeError("Хеш пароля должен быть строкой")

        if not isinstance(salt, str):
            raise TypeError("Соль должна быть строкой")

        if registration_date is not None and not isinstance(
            registration_date, datetime
        ):
            raise TypeError("Дата регистрации должна иметь тип datetime")

        self._user_id = user_id
        self._username = username.strip()
        self._salt = salt
        self._registration_date = registration_date or datetime.now()
        self._hashed_password = hashed_password

    @property
    def user_id(self) -> int:
        """Уникальный идентификатор пользователя."""
        return self._user_id

    @property
    def username(self) -> str:
        """Имя пользователя."""
        return self._username

    @username.setter
    def username(self, value: str) -> None:
        """Устанавливает имя пользователя."""
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Имя пользователя не может быть пустым")
        self._username = value.strip()

    @property
    def hashed_password(self) -> str:
        """SHA-256 хеш пароля с солью."""
        return self._hashed_password

    @property
    def salt(self) -> str:
        """Уникальная соль пользователя."""
        return self._salt

    @property
    def registration_date(self) -> datetime:
        """Дата и время регистрации."""
        return self._registration_date

    def get_user_info(self) -> dict:
        """Возвращает информацию о пользователе без пароля."""
        return {
            "user_id": self._user_id,
            "username": self._username,
            "registration_date": self._registration_date.isoformat(),
        }

    def change_password(self, new_password: str) -> None:
        """Изменяет пароль пользователя."""
        if not isinstance(new_password, str) or len(new_password) < 4:
            raise ValueError("Пароль должен быть не короче 4 символов")

        self._salt = secrets.token_hex(16)
        self._hashed_password = hashlib.sha256(
            (new_password + self._salt).encode("utf-8")
        ).hexdigest()

    def verify_password(self, password: str) -> bool:
        """Проверяет соответствие введённого пароля."""
        if not isinstance(password, str):
            return False

        candidate_hash = hashlib.sha256(
            (password + self._salt).encode("utf-8")
        ).hexdigest()

        return secrets.compare_digest(
            self._hashed_password,
            candidate_hash,
        )


class Wallet:
    """Представляет кошелёк пользователя в определённой валюте."""

    def __init__(self, currency_code: str, balance: float = 0.0) -> None:
        """Создаёт кошелёк в указанной валюте с начальным балансом."""
        self._currency_code = self._validate_currency_code(currency_code)
        self.balance = balance

    @staticmethod
    def _validate_currency_code(currency_code: str) -> str:
        """Проверяет и нормализует код валюты."""
        if not isinstance(currency_code, str) or not currency_code.strip():
            raise ValueError("Код валюты не может быть пустым")

        currency_code = currency_code.strip().upper()

        if not currency_code.isalpha():
            raise ValueError("Код валюты должен содержать только буквы")

        return currency_code

    @property
    def currency_code(self) -> str:
        """Код валюты кошелька."""
        return self._currency_code

    @property
    def balance(self) -> float:
        """Текущий баланс кошелька."""
        return self._balance

    @balance.setter
    def balance(self, value: float) -> None:
        """Устанавливает баланс: конечное неотрицательное число."""
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError("Баланс должен быть числом")

        if not math.isfinite(value):
            raise ValueError("Баланс должен быть конечным числом")

        if value < 0:
            raise ValueError("Баланс не может быть отрицательным")

        self._balance = float(value)

    def deposit(self, amount: float) -> None:
        """Пополняет кошелёк."""
        self._validate_amount(amount)
        self.balance += amount

    def withdraw(self, amount: float) -> None:
        """Снимает средства с кошелька."""
        if (
            isinstance(amount, bool)
            or not isinstance(amount, (int, float))
            or not math.isfinite(amount)
            or amount <= 0
        ):
            raise ValueError("Сумма снятия должна быть положительным конечным числом")

        if amount > self._balance:
            raise InsufficientFundsError(
                available=self._balance,
                required=amount,
                code=self.currency_code,
            )

        self._balance -= amount

    def get_balance_info(self) -> dict:
        """Возвращает информацию о балансе."""
        return {
            "currency_code": self.currency_code,
            "balance": self.balance,
        }

    @staticmethod
    def _validate_amount(amount: float) -> None:
        """Проверяет, что сумма операции — положительное конечное число."""
        if isinstance(amount, bool) or not isinstance(amount, (int, float)):
            raise TypeError("Сумма должна быть числом")

        if not math.isfinite(amount) or amount <= 0:
            raise ValueError("Сумма должна быть положительным конечным числом")


class Portfolio:
    """Представляет портфель пользователя с набором валютных кошельков."""

    def __init__(
        self,
        user: User,
        wallets: dict[str, Wallet] | None = None,
    ) -> None:
        """Создаёт портфель пользователя с набором кошельков."""
        if not isinstance(user, User):
            raise TypeError("Портфель должен принадлежать объекту User")

        self._user = user
        self._user_id = user.user_id
        self._wallets = {}

        if wallets is not None:
            for currency_code, wallet in wallets.items():
                if not isinstance(wallet, Wallet):
                    raise TypeError("Портфель может содержать только объекты Wallet")

                code = self._validate_currency_code(currency_code)

                if code != wallet.currency_code:
                    raise ValueError("Код валюты не совпадает с кодом кошелька")

                self._wallets[code] = wallet

    @staticmethod
    def _validate_currency_code(currency_code: str) -> str:
        """Проверяет и нормализует код валюты."""
        if not isinstance(currency_code, str) or not currency_code.strip():
            raise ValueError("Код валюты не может быть пустым")

        currency_code = currency_code.strip().upper()

        if not currency_code.isalpha():
            raise ValueError("Код валюты должен содержать только буквы")

        return currency_code

    @property
    def user(self) -> User:
        """Владелец портфеля."""
        return self._user

    @property
    def user_id(self) -> int:
        """Идентификатор владельца портфеля."""
        return self._user_id

    @property
    def wallets(self) -> dict[str, Wallet]:
        """Копия словаря кошельков {код валюты: Wallet}."""
        return self._wallets.copy()

    def add_currency(
        self,
        currency_code: str,
        initial_balance: float = 0.0,
    ) -> Wallet:
        """Добавляет новый валютный кошелёк."""
        code = self._validate_currency_code(currency_code)

        if code in self._wallets:
            raise ValueError(f"Кошелёк {code} уже существует")

        wallet = Wallet(code, initial_balance)
        self._wallets[code] = wallet

        return wallet

    def get_wallet(self, currency_code: str) -> Wallet | None:
        """Возвращает кошелёк или None, если его нет."""
        code = self._validate_currency_code(currency_code)
        return self._wallets.get(code)

    def get_total_value(
        self,
        base_currency: str = "USD",
        rates: dict[str, float] | None = None,
    ) -> float:
        """Считает общую стоимость портфеля в базовой валюте."""
        base_code = self._validate_currency_code(base_currency)
        rates = rates or {}
        total = 0.0

        def get_conversion_rate(from_code: str, to_code: str) -> float:
            """Конвертация валюты"""
            if from_code == to_code:
                return 1.0

            direct_key = f"{from_code}_{to_code}"
            reverse_key = f"{to_code}_{from_code}"

            if direct_key in rates:
                rate = rates[direct_key]
            elif reverse_key in rates:
                reverse_rate = rates[reverse_key]
                if reverse_rate <= 0:
                    raise ValueError(f"Некорректный курс валюты: {reverse_key}")
                rate = 1 / reverse_rate
            else:
                # Пробуем конвертацию через USD.
                first_key = f"{from_code}_USD"
                second_key = f"{to_code}_USD"

                if first_key not in rates or second_key not in rates:
                    raise ValueError(
                        f"Нет курса для конвертации {from_code} в {to_code}"
                    )

                first_rate = rates[first_key]
                second_rate = rates[second_key]

                rate = first_rate / second_rate

            if (
                isinstance(rate, bool)
                or not isinstance(rate, (int, float))
                or not math.isfinite(rate)
                or rate <= 0
            ):
                raise ValueError(f"Некорректный курс валюты: {from_code}_{to_code}")

            return rate

        for code, wallet in self._wallets.items():
            rate = get_conversion_rate(code, base_code)
            total += wallet.balance * rate

        return total
