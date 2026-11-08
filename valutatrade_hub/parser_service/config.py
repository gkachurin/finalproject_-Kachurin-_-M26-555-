"""Конфигурация Parser Service."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from valutatrade_hub.infra.settings import SettingsLoader


def _setting_path(key: str) -> Path:
    """Возвращает путь из SettingsLoader по ключу настройки."""
    return Path(SettingsLoader().get(key))


@dataclass
class ParserConfig:
    """Настройки внешних API и хранилищ курсов."""

    # Ключ берётся из переменной окружения и не хранится в коде.
    EXCHANGERATE_API_KEY: str = field(
        default_factory=lambda: os.getenv("EXCHANGERATE_API_KEY", "")
    )

    COINGECKO_URL: str = "https://api.coingecko.com/api/v3/simple/price"
    EXCHANGERATE_API_URL: str = "https://v6.exchangerate-api.com/v6"

    BASE_CURRENCY: str = "USD"
    FIAT_CURRENCIES: tuple[str, ...] = ("EUR", "GBP", "RUB")
    CRYPTO_CURRENCIES: tuple[str, ...] = ("BTC", "ETH", "SOL")
    CRYPTO_ID_MAP: dict[str, str] = field(
        default_factory=lambda: {
            "BTC": "bitcoin",
            "ETH": "ethereum",
            "SOL": "solana",
        }
    )

    RATES_FILE_PATH: Path = field(default_factory=lambda: _setting_path("rates_file"))
    HISTORY_FILE_PATH: Path = field(
        default_factory=lambda: _setting_path("history_file")
    )

    REQUEST_TIMEOUT: int = 10
