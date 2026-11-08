"""Сервис обновления курсов валют."""

from datetime import datetime, timezone
from typing import Any

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.logging_config import parser_logger as logger
from valutatrade_hub.parser_service.api_clients import (
    BaseApiClient,
    CoinGeckoClient,
    ExchangeRateApiClient,
)
from valutatrade_hub.parser_service.config import ParserConfig
from valutatrade_hub.parser_service.storage import RateStorage

SOURCES: dict[str, type[BaseApiClient]] = {
    "coingecko": CoinGeckoClient,
    "exchangerate": ExchangeRateApiClient,
}


class RatesUpdater:
    """Опрашивает клиентов, объединяет курсы и сохраняет их."""

    def __init__(self, clients: list[BaseApiClient], storage: RateStorage) -> None:
        self.clients = clients
        self.storage = storage

    def run_update(self) -> dict[str, Any]:
        """Обновляет курсы; сбой одного клиента не останавливает остальных."""
        logger.info("Starting rates update...")
        updated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        collected: dict[str, dict[str, Any]] = {}
        errors: list[str] = []

        for client in self.clients:
            name = type(client).__name__
            logger.info("Fetching from %s...", name)
            try:
                rates = client.fetch_rates()
            except ApiRequestError as error:
                logger.error("Failed to fetch from %s: %s", name, error)
                errors.append(f"{name}: {error.reason}")
                continue
            logger.info("Fetching from %s... OK (%d rates)", name, len(rates))
            for pair, info in rates.items():
                collected[pair] = {**info, "updated_at": updated_at}

        if not collected:
            logger.error("Update failed: %s", "; ".join(errors))
            raise ApiRequestError("; ".join(errors) or "нет данных")

        logger.info("Writing %d rates to %s", len(collected), self.storage.rates_file)
        self.storage.save_rates(collected)
        self.storage.append_history(
            [
                {
                    "id": f"{pair}_{updated_at}",
                    "from_currency": pair.split("_", 1)[0],
                    "to_currency": pair.split("_", 1)[1],
                    "rate": info["rate"],
                    "timestamp": updated_at,
                    "source": info["source"],
                    "meta": info.get("meta", {}),
                }
                for pair, info in collected.items()
            ]
        )
        logger.info("Update finished. Errors: %d", len(errors))
        return {"updated": len(collected), "errors": errors, "last_refresh": updated_at}


def build_updater(
    source: str | None = None,
    config: ParserConfig | None = None,
) -> RatesUpdater:
    """Собирает RatesUpdater для всех источников или одного из них."""
    config = config or ParserConfig()
    if source is None:
        classes = list(SOURCES.values())
    elif source.lower() in SOURCES:
        classes = [SOURCES[source.lower()]]
    else:
        raise ValueError(
            f"Неизвестный источник '{source}'. Доступно: coingecko, exchangerate"
        )
    storage = RateStorage(config.RATES_FILE_PATH, config.HISTORY_FILE_PATH)
    return RatesUpdater([cls(config) for cls in classes], storage)
