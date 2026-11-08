"""Хранилище актуальных курсов и истории обновлений."""

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class RateStorage:
    """Сохраняет актуальные курсы и историю изменений."""

    def __init__(
        self,
        rates_file: Path,
        history_file: Path,
    ) -> None:
        self.rates_file = Path(rates_file)
        self.history_file = Path(history_file)

    @staticmethod
    def _now() -> str:
        """Возвращает текущее время в UTC (без микросекунд)."""
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    @staticmethod
    def _read_json(path: Path, default: Any) -> Any:
        """Читает JSON или возвращает значение по умолчанию."""
        if not path.exists():
            return default

        try:
            with path.open(encoding="utf-8") as file:
                return json.load(file)
        except (json.JSONDecodeError, OSError):
            return default

    @staticmethod
    def _atomic_write(path: Path, data: Any) -> None:
        """Безопасно записывает JSON через временный файл."""
        path.parent.mkdir(parents=True, exist_ok=True)

        temp_path = None

        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=path.parent,
                suffix=".tmp",
                delete=False,
            ) as temp_file:
                json.dump(
                    data,
                    temp_file,
                    ensure_ascii=False,
                    indent=2,
                )
                temp_file.write("\n")
                temp_path = Path(temp_file.name)

            temp_path.replace(path)

        finally:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink()

    def load_rates(self) -> dict[str, Any]:
        """Загружает актуальные курсы."""
        data = self._read_json(self.rates_file, {"pairs": {}})

        # Поддерживаем старый формат rates.json.
        if "pairs" not in data:
            data = {"pairs": data}

        return data

    def save_rates(
        self,
        new_rates: dict[str, dict[str, Any]],
    ) -> None:
        """Обновляет курсы, сохраняя только более свежие значения."""
        data = self.load_rates()
        pairs = data.setdefault("pairs", {})

        for pair, info in new_rates.items():
            current = pairs.get(pair)
            new_time = info.get("updated_at", "")
            current_time = (
                current.get("updated_at", "") if isinstance(current, dict) else ""
            )

            if new_time >= current_time:
                pairs[pair] = info

        data["last_refresh"] = self._now()
        self._atomic_write(self.rates_file, data)

    def append_history(
        self,
        records: list[dict[str, Any]],
    ) -> None:
        """Добавляет новые записи в историю курсов."""
        history = self._read_json(self.history_file, [])

        if not isinstance(history, list):
            history = []

        existing_ids = {
            record.get("id") for record in history if isinstance(record, dict)
        }

        for record in records:
            if record.get("id") not in existing_ids:
                history.append(record)
                existing_ids.add(record.get("id"))

        self._atomic_write(self.history_file, history)
