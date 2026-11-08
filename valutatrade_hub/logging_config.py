"""Настройка логирования приложения."""

import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from valutatrade_hub.infra.settings import SettingsLoader


class JsonFormatter(logging.Formatter):
    """Форматирует записи логов в JSON."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
            "action": getattr(record, "action", None),
            "username": getattr(record, "username", None),
            "user_id": getattr(record, "user_id", None),
            "currency": getattr(record, "currency", None),
            "amount": getattr(record, "amount", None),
            "rate": getattr(record, "rate", None),
            "result": getattr(record, "result", None),
        }

        if record.exc_info:
            log_data["error"] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False)


def _setup(name: str, file_key: str) -> logging.Logger:
    settings = SettingsLoader()
    log_file = Path(settings.get(file_key))
    log_file.parent.mkdir(parents=True, exist_ok=True)

    log = logging.getLogger(name)
    log.setLevel(getattr(logging, settings.get("log_level", "INFO").upper()))
    log.propagate = False

    if not log.handlers:
        handler = RotatingFileHandler(
            log_file,
            maxBytes=settings.get("log_max_bytes", 1_048_576),
            backupCount=settings.get("log_backup_count", 3),
            encoding="utf-8",
        )
        if settings.get("log_format", "text").lower() == "json":
            handler.setFormatter(JsonFormatter())
        else:
            handler.setFormatter(
                logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
            )
        log.addHandler(handler)
    return log


logger = _setup("valutatrade_hub", "log_file")
parser_logger = _setup("valutatrade_hub.parser", "parser_log_file")
