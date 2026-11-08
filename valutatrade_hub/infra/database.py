"""Управление JSON-хранилищем приложения."""

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from valutatrade_hub.infra.settings import SettingsLoader


class DatabaseManager:
    """Singleton-класс для работы с JSON-файлами."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return

        self.settings = SettingsLoader()
        self._initialized = True

    def read(self, file_key: str) -> Any:
        """Безопасно читает JSON-файл по ключу настройки."""
        file_path = Path(self.settings.get(file_key))

        if not file_path.exists():
            return {}

        try:
            with file_path.open("r", encoding="utf-8") as file:
                return json.load(file)
        except json.JSONDecodeError as error:
            raise ValueError(f"Некорректный JSON в файле {file_path}") from error
        except OSError as error:
            raise ValueError(
                f"Не удалось прочитать файл {file_path}: {error}"
            ) from error

    def write(self, file_key: str, data: Any) -> None:
        """Атомарно записывает данные в JSON-файл (tmp → rename)."""
        file_path = Path(self.settings.get(file_key))
        file_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=file_path.parent,
                suffix=".tmp",
                delete=False,
            ) as tmp:
                json.dump(data, tmp, ensure_ascii=False, indent=4)
            os.replace(tmp.name, file_path)
        except OSError as error:
            raise ValueError(
                f"Не удалось записать файл {file_path}: {error}"
            ) from error
