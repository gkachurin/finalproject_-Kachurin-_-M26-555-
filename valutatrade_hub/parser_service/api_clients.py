"""Клиенты внешних API для получения курсов валют."""

from abc import ABC, abstractmethod
from math import isfinite
from time import perf_counter
from typing import Any

import requests

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service.config import ParserConfig

STATUS_MESSAGES = {
    401: "неверный API-ключ",
    403: "доступ запрещён, проверьте API-ключ",
    429: "превышен лимит запросов, повторите позже",
}


class BaseApiClient(ABC):
    """Базовый класс клиента внешнего API."""

    def __init__(self, config: ParserConfig) -> None:
        self.config = config

    @abstractmethod
    def fetch_rates(self) -> dict[str, dict[str, Any]]:
        """Получает курсы и возвращает их в едином формате."""

    def _get_json(
        self,
        url: str,
        params: dict[str, str] | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Выполняет GET-запрос и возвращает JSON с метаданными."""
        start = perf_counter()

        try:
            response = requests.get(
                url,
                params=params,
                timeout=self.config.REQUEST_TIMEOUT,
            )
            if response.status_code != 200:
                reason = STATUS_MESSAGES.get(response.status_code, "ошибка сервера")
                raise ApiRequestError(f"{reason} (HTTP {response.status_code})")
            data = response.json()

        except requests.exceptions.RequestException as error:
            raise ApiRequestError(str(error)) from error
        except ValueError as error:
            raise ApiRequestError("API вернул некорректный JSON") from error

        if not isinstance(data, dict):
            raise ApiRequestError("Некорректный формат ответа API")

        meta = {
            "request_ms": round((perf_counter() - start) * 1000, 2),
            "status_code": response.status_code,
            "etag": response.headers.get("ETag"),
            "raw_id": None,
        }

        return data, meta

    @staticmethod
    def _valid_rate(value: Any) -> bool:
        """Проверяет, что курс является конечным положительным числом."""
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and isfinite(value)
            and value > 0
        )


class CoinGeckoClient(BaseApiClient):
    """Получает курсы криптовалют через CoinGecko."""

    def fetch_rates(self) -> dict[str, dict[str, Any]]:
        ids = ",".join(self.config.CRYPTO_ID_MAP.values())

        data, meta = self._get_json(
            self.config.COINGECKO_URL,
            params={
                "ids": ids,
                "vs_currencies": self.config.BASE_CURRENCY.lower(),
            },
        )

        result = {}

        for code, coin_id in self.config.CRYPTO_ID_MAP.items():
            coin_data = data.get(coin_id)

            if not isinstance(coin_data, dict):
                continue

            rate = coin_data.get(self.config.BASE_CURRENCY.lower())

            if not self._valid_rate(rate):
                continue

            pair = f"{code}_{self.config.BASE_CURRENCY}"
            result[pair] = {
                "rate": float(rate),
                "source": "CoinGecko",
                "meta": {**meta, "raw_id": coin_id},
            }

        if not result:
            raise ApiRequestError("CoinGecko не вернул ни одного корректного курса")

        return result


class ExchangeRateApiClient(BaseApiClient):
    """Получает курсы фиатных валют через ExchangeRate-API."""

    def fetch_rates(self) -> dict[str, dict[str, Any]]:
        if not self.config.EXCHANGERATE_API_KEY:
            raise ApiRequestError("Не задан API-ключ EXCHANGERATE_API_KEY")

        url = (
            f"{self.config.EXCHANGERATE_API_URL}/"
            f"{self.config.EXCHANGERATE_API_KEY}/latest/"
            f"{self.config.BASE_CURRENCY}"
        )

        data, meta = self._get_json(url)

        if data.get("result") != "success":
            raise ApiRequestError(
                "ExchangeRate-API вернул ошибку: "
                f"{data.get('error-type', 'неизвестная ошибка')}"
            )

        rates = data.get("conversion_rates") or data.get("rates")

        if not isinstance(rates, dict):
            raise ApiRequestError("В ответе ExchangeRate-API отсутствуют курсы")

        meta["raw_id"] = data.get("time_last_update_unix")

        result = {}

        for code in self.config.FIAT_CURRENCIES:
            usd_to_currency = rates.get(code)

            if not self._valid_rate(usd_to_currency):
                continue

            # API возвращает USD -> валюта.
            # Нам нужен обратный курс: валюта -> USD.
            pair = f"{code}_{self.config.BASE_CURRENCY}"
            result[pair] = {
                "rate": 1 / float(usd_to_currency),
                "source": "ExchangeRate-API",
                "meta": meta.copy(),
            }

        if not result:
            raise ApiRequestError("ExchangeRate-API не вернул корректных курсов")

        return result
