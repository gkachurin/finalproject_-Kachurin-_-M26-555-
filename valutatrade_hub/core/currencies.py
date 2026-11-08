import math
from abc import ABC, abstractmethod

from .exceptions import CurrencyNotFoundError


class Currency(ABC):
    """Абстрактный базовый класс валюты."""

    def __init__(self, name: str, code: str) -> None:
        """Создаёт валюту: код 2–5 букв в верхнем регистре, имя не пустое."""
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Название валюты не может быть пустым")

        if not isinstance(code, str):
            raise TypeError("Код валюты должен быть строкой")

        code = code.strip().upper()

        if not 2 <= len(code) <= 5 or not code.isalpha():
            raise ValueError("Код валюты должен содержать от 2 до 5 букв")

        self.name = name.strip()
        self.code = code

    @abstractmethod
    def get_display_info(self) -> str:
        """Возвращает информацию о валюте."""
        raise NotImplementedError


class FiatCurrency(Currency):
    """Представляет фиатную валюту."""

    def __init__(
        self,
        name: str,
        code: str,
        issuing_country: str,
    ) -> None:
        """Создаёт фиатную валюту со страной эмиссии."""
        super().__init__(name, code)

        if not isinstance(issuing_country, str) or not issuing_country.strip():
            raise ValueError("Страна эмиссии не может быть пустой")

        self.issuing_country = issuing_country.strip()

    def get_display_info(self) -> str:
        """Возвращает строку вида '[FIAT] USD — US Dollar (Issuing: ...)'."""
        return f"[FIAT] {self.code} — {self.name} (Issuing: {self.issuing_country})"


class CryptoCurrency(Currency):
    """Представляет криптовалюту."""

    def __init__(
        self,
        name: str,
        code: str,
        algorithm: str,
        market_cap: float,
    ) -> None:
        """Создаёт криптовалюту с алгоритмом и капитализацией."""
        super().__init__(name, code)

        if not isinstance(algorithm, str) or not algorithm.strip():
            raise ValueError("Алгоритм не может быть пустым")

        if isinstance(market_cap, bool) or not isinstance(market_cap, (int, float)):
            raise TypeError("Капитализация должна быть числом")

        if not math.isfinite(market_cap) or market_cap < 0:
            raise ValueError(
                "Капитализация должна быть конечным неотрицательным числом"
            )

        self.algorithm = algorithm.strip()
        self.market_cap = float(market_cap)

    def get_display_info(self) -> str:
        """Возвращает описание: '[CRYPTO] BTC — Bitcoin (Algo..., MCAP...)'."""
        return (
            f"[CRYPTO] {self.code} — {self.name} "
            f"(Algo: {self.algorithm}, MCAP: {self.market_cap:.2e})"
        )


# Демонстрационные значения капитализации, не актуальные рыночные данные.
CURRENCY_REGISTRY: dict[str, Currency] = {
    "USD": FiatCurrency("US Dollar", "USD", "United States"),
    "EUR": FiatCurrency("Euro", "EUR", "Eurozone"),
    "RUB": FiatCurrency("Russian Ruble", "RUB", "Russia"),
    "BTC": CryptoCurrency("Bitcoin", "BTC", "SHA-256", 1.12e12),
    "ETH": CryptoCurrency("Ethereum", "ETH", "Proof of Stake", 4.45e11),
    "SOL": CryptoCurrency("Solana", "SOL", "Proof of History", 8.0e10),
    "GBP": FiatCurrency("British Pound", "GBP", "United Kingdom"),
}


def get_currency(code: str) -> Currency:
    """Возвращает валюту из реестра по её коду."""
    if not isinstance(code, str):
        raise CurrencyNotFoundError(str(code))

    normalized_code = code.strip().upper()

    currency = CURRENCY_REGISTRY.get(normalized_code)

    if currency is None:
        raise CurrencyNotFoundError(normalized_code)

    return currency
