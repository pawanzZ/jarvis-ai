from __future__ import annotations
import json
from pathlib import Path
from typing import Any


class Config:
    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir
        self._config_dir = base_dir / "config"
        self._cache: dict[str, dict[str, Any]] = {}

    def get(self, namespace: str, key: str | None = None, default: Any = None) -> Any:
        if namespace not in self._cache:
            self._load(namespace)
        data = self._cache.get(namespace, {})
        if key is None:
            return data
        return data.get(key, default)

    def set(self, namespace: str, key: str, value: Any) -> None:
        if namespace not in self._cache:
            self._load(namespace)
        self._cache.setdefault(namespace, {})[key] = value
        self._save(namespace)

    def _load(self, namespace: str) -> None:
        path = self._config_dir / f"{namespace}.json"
        if path.exists():
            self._cache[namespace] = json.loads(path.read_text())
        else:
            self._cache[namespace] = {}

    def _save(self, namespace: str) -> None:
        self._config_dir.mkdir(parents=True, exist_ok=True)
        path = self._config_dir / f"{namespace}.json"
        path.write_text(json.dumps(self._cache[namespace], indent=2))
