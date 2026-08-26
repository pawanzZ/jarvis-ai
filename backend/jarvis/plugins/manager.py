from __future__ import annotations
import importlib.util
import sys
from pathlib import Path
from typing import Any, Optional
from jarvis.core.bus import Event, EventBus
from jarvis.core.config import Config
from jarvis.plugins.base import Plugin, PluginType


class PluginManager:
    """Manages plugin discovery, lifecycle, configuration, and event routing."""

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
        plugins_path = Path(plugins_dir)
        discovered: list[str] = []
        if not plugins_path.exists() or not plugins_path.is_dir():
            return discovered

        for path in sorted(plugins_path.glob("*.py")):
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
                        cls = getattr(mod, "plugin_class")
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
                # Fault isolation: invalid syntax or runtime import failure does not crash discovery
                continue
        return discovered

    async def activate(self, name: str) -> bool:
        """Activate a registered plugin by name, reading its config and invoking start()."""
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
        """Deactivate an active plugin by name and invoke stop()."""
        if name not in self._active:
            return False
        plugin = self._active[name]
        try:
            await plugin.stop()
            return True
        except Exception as e:
            print(f"Error stopping plugin {name}: {e}")
            return False
        finally:
            self._active.pop(name, None)

    async def stop_all(self) -> None:
        """Stop all active plugins."""
        for name in list(self._active.keys()):
            try:
                await self.deactivate(name)
            except Exception as e:
                print(f"Error deactivating plugin {name} during stop_all: {e}")

    def get_plugin(self, name: str) -> Optional[Plugin]:
        """Return registered plugin instance by name."""
        return self._plugins.get(name)

    def get_active(self, plugin_type: PluginType | str) -> Optional[Plugin]:
        """Return the active plugin matching the given PluginType or string."""
        target = (
            plugin_type.value
            if isinstance(plugin_type, PluginType)
            else str(plugin_type)
        )
        for plugin in self._active.values():
            p_type = (
                plugin.plugin_type.value
                if isinstance(plugin.plugin_type, PluginType)
                else str(plugin.plugin_type)
            )
            if p_type == target:
                return plugin
        return None

    def get_active_plugins(self) -> dict[str, Plugin]:
        """Return dictionary copy of all active plugins."""
        return dict(self._active)

    def list_all(self) -> dict[str, Plugin]:
        """Return dictionary copy of all registered plugins."""
        return dict(self._plugins)

    def get_schemas(self) -> dict[str, dict[str, Any]]:
        """Return a mapping of plugin names to their configuration schemas."""
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
