from __future__ import annotations
import json
from pathlib import Path
from typing import Any


class Config:
    """Namespace-based configuration manager with atomic disk persistence."""

    def __init__(self, base_dir: Path | str) -> None:
        self._base_dir = Path(base_dir)
        self._config_dir = self._base_dir / "config"
        self._cache: dict[str, dict[str, Any]] = {}

    def get(self, namespace: str, key: str | None = None, default: Any = None) -> Any:
        """Get configuration value for a namespace and key, or entire namespace dict."""
        if namespace not in self._cache:
            self._load(namespace)
        data = self._cache.get(namespace, {})
        if key is None:
            return data
        return data.get(key, default)

    def set(self, namespace: str, key: str, value: Any) -> None:
        """Set configuration value for a namespace and persist atomically."""
        if namespace not in self._cache:
            self._load(namespace)
        self._cache.setdefault(namespace, {})[key] = value
        self._save(namespace)

    def list_namespaces(self) -> list[str]:
        """List all available namespaces from disk and memory."""
        namespaces: set[str] = set()
        if self._config_dir.exists() and self._config_dir.is_dir():
            for p in self._config_dir.rglob("*.json"):
                rel = p.relative_to(self._config_dir).with_suffix("").as_posix()
                namespaces.add(rel)
        for ns in self._cache.keys():
            namespaces.add(ns)
        return sorted(list(namespaces))

    def get_all(self, namespace: str) -> dict[str, Any]:
        """Return a copy of all key-values in a namespace."""
        if namespace not in self._cache:
            self._load(namespace)
        return dict(self._cache.get(namespace, {}))

    def _load(self, namespace: str) -> None:
        path = self._config_dir / f"{namespace}.json"
        if path.exists() and path.is_file():
            try:
                content = path.read_text(encoding="utf-8")
                self._cache[namespace] = json.loads(content)
            except (json.JSONDecodeError, UnicodeDecodeError, OSError):
                self._cache[namespace] = {}
        else:
            self._cache[namespace] = {}

    def _save(self, namespace: str) -> None:
        path = self._config_dir / f"{namespace}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_name(f"{path.name}.tmp")
        serialized = json.dumps(self._cache[namespace], indent=2)
        temp_path.write_text(serialized, encoding="utf-8")
        temp_path.replace(path)
