"""Планировщик периодического обновления курсов."""

import logging
import threading

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service.updater import RatesUpdater, build_updater

logger = logging.getLogger(__name__)

DEFAULT_INTERVAL_SECONDS = 300


class RateScheduler:
    """Запускает обновление курсов через заданный интервал."""

    def __init__(
        self,
        updater: RatesUpdater | None = None,
        interval: int = DEFAULT_INTERVAL_SECONDS,
    ) -> None:
        if interval <= 0:
            raise ValueError("Интервал должен быть положительным")

        self.updater = updater or build_updater()
        self.interval = interval
        self._stop_event = threading.Event()

    def run_once(self) -> dict:
        """Выполняет одно обновление курсов."""
        try:
            result = self.updater.run_update()
            logger.info("Курсы обновлены: %s", result)
            return result
        except ApiRequestError:
            logger.exception("Не удалось обновить курсы")
            raise

    def start(self) -> None:
        """Запускает периодическое обновление."""
        self._stop_event.clear()
        logger.info("Планировщик запущен. Интервал: %s сек.", self.interval)

        try:
            while not self._stop_event.is_set():
                try:
                    self.run_once()
                except ApiRequestError:
                    pass

                self._stop_event.wait(self.interval)

        except KeyboardInterrupt:
            logger.info("Получен сигнал остановки планировщика")

        finally:
            self._stop_event.set()
            logger.info("Планировщик остановлен")

    def stop(self) -> None:
        """Останавливает планировщик."""
        self._stop_event.set()
