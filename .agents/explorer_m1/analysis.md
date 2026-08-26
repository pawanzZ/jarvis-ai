# Technical Analysis & Implementation Specification: Milestone 1 (Core Backend & Plugin Architecture)

**Author:** Explorer M1  
**Target Milestone:** M1 — Core Backend & Plugin Architecture (Features 1–5, Tasks 1, 3, 4, 6, 7)  
**Target Files:**
1. `backend/jarvis/plugins/base.py` (New)
2. `backend/jarvis/plugins/manager.py` (New)
3. `backend/jarvis/core/config.py` (Enhancement)
4. `backend/jarvis/__main__.py` (Wiring & Background Task Lifecycle)
5. `backend/tests/test_plugin_base.py` (New Unit Tests)
6. `backend/tests/test_plugin_manager.py` (New Unit Tests)
7. `backend/tests/test_config.py` (New Unit Tests)

---

## 1. Executive Summary

Milestone 1 establishes the bedrock of Jarvis AI:
1. A strongly typed abstract **Plugin Base Interface** (`Plugin`, `PluginType`) ensuring uniformity across STT, TTS, LLM, activation, and vision backends.
2. A resilient, dynamic **Plugin Manager** (`PluginManager`) capable of discovery, lifecycle control (`start`/`stop`), state tracking (`active`/`inactive`), schema aggregation, and isolated event routing.
3. An enhanced, resilient **Configuration Store** (`Config`) providing namespace enumeration (`list_namespaces`), bulk namespace access (`get_all`), atomic disk persistence, and corrupt JSON fault recovery.
4. An integrated async runtime in **`__main__.py`** concurrently driving the `EventBus.process()` consumer loop alongside the `WSServer` gateway and plugin manager.
5. Comprehensive unit test suites validating all tiers (Feature, Boundary, Cross-feature, and Scenario) with 100% pass rates.

---

## 2. Detailed Component Specifications

### 2.1 Plugin Base Specification (`backend/jarvis/plugins/base.py`)

#### Interface Contract & Design
```python
from __future__ import annotations
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Optional
from jarvis.core.bus import Event, EventBus
from jarvis.core.config import Config


class PluginType(str, Enum):
    STT = "stt"
    TTS = "tts"
    LLM = "llm"
    WAKE_WORD = "wake_word"
    ACTIVATION = "activation"
    VISION = "vision"


class Plugin(ABC):
    name: str = "unnamed"
    plugin_type: PluginType = PluginType.STT

    def __init__(
        self,
        bus: Optional[EventBus] = None,
        config: Optional[Config] = None,
    ) -> None:
        self.bus = bus
        self.config = config

    @abstractmethod
    async def start(self, config: Optional[dict[str, Any]] = None) -> None:
        """Start the plugin with optional configuration dict."""
        ...

    @abstractmethod
    async def stop(self) -> None:
        """Stop the plugin and release resources."""
        ...

    @abstractmethod
    async def on_event(self, event: Event) -> Optional[Event]:
        """Handle incoming event and optionally return a response event."""
        ...

    @abstractmethod
    def get_schema(self) -> dict[str, Any]:
        """Return JSON schema describing configuration options for UI generation."""
        ...
```

#### Key Design Decisions:
- **Dual Construction Flexibility:** `__init__` takes optional `bus` and `config`. When dynamically loaded by `PluginManager`, references are automatically injected.
- **Async Lifecycle:** `start` accepts an optional dictionary (`config: Optional[dict[str, Any]] = None`) populated from the Config store (`plugins.json` or `{name}.json`). `stop` cleans up any tasks, file handles, or device streams.
- **Event Transformation:** `on_event` can return an `Optional[Event]`. If an `Event` is returned, `PluginManager` routes and re-emits it onto the `EventBus`.
- **UI Schema Generator:** `get_schema()` returns a valid JSON Schema `dict` representing configurable parameters (e.g., model name, voice ID, thresholds) used by the Electron Settings Drawer.

---

### 2.2 Plugin Manager Specification (`backend/jarvis/plugins/manager.py`)

#### Class Architecture
```python
from __future__ import annotations
import importlib.util
import sys
from pathlib import Path
from typing import Any, Optional
from jarvis.core.bus import EventBus, Event
from jarvis.core.config import Config
from jarvis.plugins.base import Plugin, PluginType


class PluginManager:
    def __init__(self, bus: EventBus, config: Config) -> None:
        self.bus = bus
        self.config = config
        self._plugins: dict[str, Plugin] = {}
        self._active: dict[str, Plugin] = {}

    def register(self, plugin: Plugin) -> None:
        """Register a plugin instance. Injects bus and config if unset."""
        if plugin.bus is None:
            plugin.bus = self.bus
        if plugin.config is None:
            plugin.config = self.config
        self._plugins[plugin.name] = plugin

    def discover(self, plugins_dir: Path | str) -> list[str]:
        """Scan directory for plugin Python files, instantiate and register them."""
        plugins_dir = Path(plugins_dir)
        discovered: list[str] = []
        if not plugins_dir.exists() or not plugins_dir.is_dir():
            return discovered

        for path in sorted(plugins_dir.glob("*.py")):
            if path.name.startswith("_"):
                continue
            module_name = f"jarvis_dynamic_plugin_{path.stem}"
            try:
                spec = importlib.util.spec_from_file_location(module_name, path)
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = mod
                    spec.loader.exec_module(mod)

                    if hasattr(mod, "plugin_class"):
                        cls = mod.plugin_class
                        try:
                            plugin = cls(bus=self.bus, config=self.config)
                        except TypeError:
                            plugin = cls()
                        self.register(plugin)
                        discovered.append(plugin.name)
                    else:
                        for attr_name in dir(mod):
                            attr = getattr(mod, attr_name)
                            if (
                                isinstance(attr, type)
                                and issubclass(attr, Plugin)
                                and attr is not Plugin
                            ):
                                try:
                                    plugin = attr(bus=self.bus, config=self.config)
                                except TypeError:
                                    plugin = attr()
                                self.register(plugin)
                                discovered.append(plugin.name)
                                break
            except Exception:
                # Fault isolation: invalid syntax/import does not crash discovery
                continue
        return discovered

    async def activate(self, name: str) -> bool:
        """Activate registered plugin by name, reading its config and invoking start()."""
        if name not in self._plugins:
            return False
        if name in self._active:
            return True
        plugin = self._plugins[name]
        cfg = self.config.get("plugins", name)
        if cfg is None or not isinstance(cfg, dict):
            cfg = self.config.get_all(name)
        try:
            await plugin.start(cfg)
            self._active[name] = plugin
            return True
        except Exception:
            return False

    async def deactivate(self, name: str) -> bool:
        """Deactivate active plugin by name and invoke stop()."""
        if name not in self._active:
            return False
        plugin = self._active[name]
        try:
            await plugin.stop()
        finally:
            del self._active[name]
        return True

    async def stop_all(self) -> None:
        """Stop all active plugins."""
        for name in list(self._active.keys()):
            await self.deactivate(name)

    def get_plugin(self, name: str) -> Optional[Plugin]:
        return self._plugins.get(name)

    def get_active(self, plugin_type: PluginType | str) -> Optional[Plugin]:
        target = plugin_type.value if isinstance(plugin_type, PluginType) else str(plugin_type)
        for plugin in self._active.values():
            p_type = plugin.plugin_type.value if isinstance(plugin.plugin_type, PluginType) else str(plugin.plugin_type)
            if p_type == target:
                return plugin
        return None

    def get_active_plugins(self) -> dict[str, Plugin]:
        return dict(self._active)

    def list_all(self) -> dict[str, Plugin]:
        return dict(self._plugins)

    def get_schemas(self) -> dict[str, dict[str, Any]]:
        schemas: dict[str, dict[str, Any]] = {}
        for name, plugin in self._plugins.items():
            try:
                schemas[name] = plugin.get_schema()
            except Exception:
                schemas[name] = {}
        return schemas

    async def route_event(self, event: Event) -> list[Event]:
        """Route event to all active plugins and emit returned response events onto the bus."""
        responses: list[Event] = []
        for name, plugin in list(self._active.items()):
            try:
                resp = await plugin.on_event(event)
                if resp is not None and isinstance(resp, Event):
                    responses.append(resp)
                    await self.bus.emit(resp)
            except Exception:
                continue
        return responses
```

---

### 2.3 Config Loader Enhancement Specification (`backend/jarvis/core/config.py`)

#### Enhanced Implementation
```python
from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Any


class Config:
    def __init__(self, base_dir: Path) -> None:
        self._base_dir = Path(base_dir)
        self._config_dir = self._base_dir / "config"
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

    def list_namespaces(self) -> list[str]:
        namespaces: set[str] = set()
        if self._config_dir.exists() and self._config_dir.is_dir():
            for p in self._config_dir.rglob("*.json"):
                rel = p.relative_to(self._config_dir).with_suffix("").as_posix()
                namespaces.add(rel)
                namespaces.add(p.stem)
        for ns in self._cache.keys():
            namespaces.add(ns)
        return sorted(list(namespaces))

    def get_all(self, namespace: str) -> dict[str, Any]:
        if namespace not in self._cache:
            self._load(namespace)
        return dict(self._cache.get(namespace, {}))

    def _load(self, namespace: str) -> None:
        path = self._config_dir / f"{namespace}.json"
        if path.exists() and path.is_file():
            try:
                content = path.read_text(encoding="utf-8")
                self._cache[namespace] = json.loads(content)
            except (json.JSONDecodeError, UnicodeDecodeError):
                self._cache[namespace] = {}
        else:
            self._cache[namespace] = {}

    def _save(self, namespace: str) -> None:
        path = self._config_dir / f"{namespace}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_suffix(".tmp")
        serialized = json.dumps(self._cache[namespace], indent=2)
        temp_path.write_text(serialized, encoding="utf-8")
        temp_path.replace(path)
```

#### Enhancements Highlights:
- **`list_namespaces()`**: Enumerates all `.json` files in `config/` (both flat and nested) plus in-memory loaded namespaces. Returns sorted list.
- **`get_all()`**: Returns an isolated dictionary copy of the namespace data.
- **Atomic File Writing**: Writes serialized JSON to `.tmp` file and atomically replaces destination via `os.replace` (`Path.replace`), preventing corrupt configuration state on mid-write crashes.
- **Corrupt File Resilience**: Gracefully catches `json.JSONDecodeError` on malformed config files and defaults to `{}` without raising uncaught exceptions.

---

### 2.4 Event Bus Background Processing & Entry Point (`backend/jarvis/__main__.py`)

#### Complete Integration
```python
import asyncio
from pathlib import Path
from jarvis.core.bus import EventBus, Event
from jarvis.core.state import StateMachine, JarvisState
from jarvis.core.config import Config
from jarvis.ws_server import WSServer
from jarvis.plugins.manager import PluginManager


async def main() -> None:
    base_dir = Path(__file__).parent.parent.parent
    bus = EventBus()
    state = StateMachine()
    config = Config(base_dir)
    server = WSServer(bus, state)
    plugin_mgr = PluginManager(bus, config)

    # Discover built-in plugins
    builtins_dir = Path(__file__).parent / "plugins" / "builtins"
    if builtins_dir.exists():
        discovered = plugin_mgr.discover(builtins_dir)
        print(f"Discovered plugins: {discovered}")

    # Broadcast state transitions to HUD clients
    async def broadcast_state(old: JarvisState, new: JarvisState) -> None:
        await server.broadcast({
            "type": "state_change",
            "state": new.value,
            "data": {"state": new.value, "previous": old.value},
        })

    state.on_change(broadcast_state)

    # Core Event Handlers
    async def handle_activate(event: Event) -> None:
        if state.state == JarvisState.IDLE:
            await state.transition(JarvisState.LISTENING)

    async def handle_deactivate(event: Event) -> None:
        if state.state != JarvisState.IDLE:
            await state.transition(JarvisState.IDLE)

    async def handle_config_update(event: Event) -> None:
        plugin = event.data.get("plugin") or event.data.get("namespace", "core")
        key = event.data.get("key")
        value = event.data.get("value")
        if plugin and key:
            config.set(plugin, key, value)
            await server.broadcast({
                "type": "config_updated",
                "data": {"namespace": plugin, "key": key, "value": value},
            })

    bus.on("activate", handle_activate)
    bus.on("deactivate", handle_deactivate)
    bus.on("config_update", handle_config_update)

    print("Jarvis backend starting...")

    # Spawn background event bus processing loop
    bus_task = asyncio.create_task(bus.process())

    try:
        await server.start()
    finally:
        bus_task.cancel()
        await plugin_mgr.stop_all()


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 3. Unit Test Specifications

### 3.1 `backend/tests/test_plugin_base.py`
1. `test_plugin_type_enum()`: Asserts all 6 `PluginType` enum values (`stt`, `tts`, `llm`, `wake_word`, `activation`, `vision`).
2. `test_plugin_abstract_instantiation_fails()`: Asserts `TypeError` when attempting to instantiate abstract `Plugin` directly or when any abstract method (`start`, `stop`, `on_event`, `get_schema`) is un-implemented.
3. `test_plugin_concrete_subclass()`: Instantiates concrete test plugin subclass and verifies default attributes (`name`, `plugin_type`, `bus=None`, `config=None`).
4. `test_plugin_init_with_bus_and_config()`: Instantiates plugin passing `bus` and `config` instances and asserts properties are set.
5. `test_plugin_lifecycle_methods()`: Executes `await plugin.start({"param": 10})` and `await plugin.stop()` and verifies execution flags.
6. `test_plugin_on_event_returns_event()`: Verifies `on_event` processes an input event and returns a valid `Event(type="output_event", data=...)`.
7. `test_plugin_on_event_returns_none()`: Verifies `on_event` returns `None` for ignored event types.
8. `test_plugin_get_schema()`: Verifies `get_schema()` returns a valid dictionary.

### 3.2 `backend/tests/test_plugin_manager.py`
1. `test_manager_initialization()`: Verifies `PluginManager(bus, config)` initializes with empty plugins dictionary and empty active dictionary.
2. `test_register_plugin()`: Verifies registering a plugin injects `bus` and `config` and makes it accessible in `list_all()`.
3. `test_discover_plugins(tmp_path)`: Creates dynamic `.py` plugin file in temporary directory, calls `manager.discover(dir)`, and asserts plugin is discovered and registered.
4. `test_discover_plugins_ignores_private_files(tmp_path)`: Creates `__init__.py` and `_hidden.py` and verifies they are skipped.
5. `test_discover_plugins_syntax_error_handling(tmp_path)`: Creates invalid Python file with broken syntax alongside a valid plugin; asserts `discover()` safely recovers and discovers the valid plugin.
6. `test_discover_nonexistent_directory(tmp_path)`: Asserts `discover(nonexistent_dir)` returns `[]` without throwing exceptions.
7. `test_activate_and_deactivate_plugin()`: Tests activating registered plugin (`await manager.activate(name)` -> `True`), checks `get_active(plugin_type)`, and deactivates it (`await manager.deactivate(name)` -> `True`).
8. `test_activate_nonexistent_plugin()`: Asserts `await manager.activate("unknown")` returns `False`.
9. `test_activate_already_active_plugin()`: Asserts calling `activate` on an already active plugin returns `True` idempotently.
10. `test_deactivate_nonactive_plugin()`: Asserts calling `deactivate` on an inactive plugin returns `False`.
11. `test_get_active_by_enum_and_string()`: Verifies `get_active(PluginType.STT)` and `get_active("stt")` return the active plugin instance.
12. `test_get_schemas()`: Verifies `get_schemas()` returns a dict mapping plugin names to their schema dicts.
13. `test_route_event_to_active_plugins()`: Verifies `route_event(event)` delivers event to active plugins, collects returned events, and emits them to `bus`.
14. `test_route_event_ignores_inactive_plugins()`: Verifies inactive plugins never receive routed events.
15. `test_route_event_fault_isolation()`: Tests that an active plugin raising an unhandled exception inside `on_event` does not prevent subsequent active plugins from receiving the event.
16. `test_stop_all()`: Tests `await manager.stop_all()` shuts down all currently active plugins.

### 3.3 `backend/tests/test_config.py`
1. `test_config_get_default()`: Asserts `config.get("test", "nonexistent_key", default=100)` returns `100`.
2. `test_config_get_all_missing_namespace()`: Asserts `config.get_all("missing")` returns `{}`.
3. `test_config_set_and_get(tmp_path)`: Tests setting keys, reading keys, and persistence across `Config` instances.
4. `test_list_namespaces(tmp_path)`: Creates multiple JSON config files and asserts `config.list_namespaces()` returns all namespace names.
5. `test_list_namespaces_empty(tmp_path)`: Asserts `list_namespaces()` returns `[]` when config directory is empty or absent.
6. `test_get_all(tmp_path)`: Asserts `get_all(namespace)` returns a copy of dictionary without leaking mutable cache references.
7. `test_atomic_save(tmp_path)`: Verifies `_save()` replaces file atomically and leaves no orphaned `.tmp` files.
8. `test_corrupt_json_file(tmp_path)`: Writes broken JSON to a config file and asserts `_load()` gracefully defaults to `{}` without raising `JSONDecodeError`.

---

## 4. Verification & Validation Steps

1. **Unit Test Execution:**
   ```bash
   cd /home/pawan/Projects/jarvis-ai/backend && python3 -m pytest tests/ -v
   ```
   *Expected:* All test suites pass (all existing tests + 3 new test suites).

2. **Integration Sanity Check:**
   Verify `python3 -m jarvis` starts cleanly without missing imports or syntax errors.
