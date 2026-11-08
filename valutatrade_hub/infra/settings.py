"""Загрузка и хранение настроек приложения."""

import tomllib
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[2]
PYPROJECT_FILE = BASE_DIR / "pyproject.toml"


class SettingsLoader:
    """Singleton-класс для управления настройками приложения.

    Значения читаются из секции [tool.valutatrade] в pyproject.toml,
    недостающие ключи берутся из DEFAULTS.
    """

    _instance = None

    DEFAULTS: dict[str, Any] = {
        "data_dir": "data",
        "users_file": "data/users.json",
        "portfolios_file": "data/portfolios.json",
        "rates_file": "data/rates.json",
        "history_file": "data/exchange_rates.json",
        "log_file": "logs/actions.log",
        "parser_log_file": "logs/parser.log",
        "rates_ttl": 300,
        "default_base_currency": "USD",
        "log_level": "INFO",
        "log_format": "text",
        "log_max_bytes": 1_048_576,
        "log_backup_count": 3,
    }

    # Ключи, значения которых — пути (относительные считаются от корня проекта).
    PATH_KEYS = (
        "data_dir",
        "users_file",
        "portfolios_file",
        "rates_file",
        "history_file",
        "log_file",
        "parser_log_file",
    )

    # Singleton через __new__: проще и читабельнее метакласса,
    # повторные импорты не создают новых экземпляров.
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return

        self._settings: dict[str, Any] = {}
        self._initialized = True
        self.reload()

    def reload(self) -> None:
        """Перечитывает настройки из pyproject.toml."""
        settings = self.DEFAULTS.copy()

        if PYPROJECT_FILE.exists():
            try:
                with PYPROJECT_FILE.open("rb") as file:
                    project = tomllib.load(file)
            except (OSError, tomllib.TOMLDecodeError) as error:
                raise ValueError(f"Не удалось загрузить настройки: {error}") from error

            settings.update(project.get("tool", {}).get("valutatrade", {}))

        for key in self.PATH_KEYS:
            path = Path(settings[key])
            settings[key] = str(path if path.is_absolute() else BASE_DIR / path)

        self._settings = settings

    def get(self, key: str, default: Any = None) -> Any:
        """Возвращает настройку по ключу."""
        return self._settings.get(key, default)
