import asyncio
import pytest
from pathlib import Path
from typing import Any, Optional
from jarvis.core.bus import Event, EventBus
from jarvis.core.config import Config
from jarvis.plugins.base import Plugin, PluginType
from jarvis.plugins.manager import PluginManager


class MockPlugin(Plugin):
    def __init__(
        self,
        name: str = "mock_plugin",
        plugin_type: PluginType = PluginType.STT,
        bus: Optional[EventBus] = None,
        config: Optional[Config] = None,
        fail_start: bool = False,
        fail_event: bool = False,
        fail_stop: bool = False,
    ) -> None:
        super().__init__(bus, config)
        self.name = name
        self.plugin_type = plugin_type
        self.fail_start = fail_start
        self.fail_event = fail_event
        self.fail_stop = fail_stop
        self.started = False
        self.stopped = False
        self.received_events: list[Event] = []
        self.received_config: Optional[dict[str, Any]] = None

    async def start(self, config: Optional[dict[str, Any]] = None) -> None:
        if self.fail_start:
            raise RuntimeError("Failed to start plugin")
        self.started = True
        self.received_config = config

    async def stop(self) -> None:
        if self.fail_stop:
            raise RuntimeError("Failed to stop plugin")
        self.stopped = True

    async def on_event(self, event: Event) -> Optional[Event]:
        if self.fail_event:
            raise ValueError("Error processing event")
        self.received_events.append(event)
        if event.type == "req":
            return Event(type="res", data={"reply": "ok"}, source=self.name)
        return None

    def get_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {"name": {"type": "string"}}}


@pytest.fixture
def manager(tmp_path: Path):
    bus = EventBus()
    cfg = Config(tmp_path)
    return PluginManager(bus, cfg)


def test_manager_initialization(manager: PluginManager):
    assert len(manager.list_all()) == 0
    assert len(manager.get_active_plugins()) == 0


def test_register_plugin(manager: PluginManager):
    p = MockPlugin(name="test_p")
    assert p.bus is None
    assert p.config is None

    manager.register(p)
    assert p.bus is manager.bus
    assert p.config is manager.config
    assert manager.get_plugin("test_p") is p
    assert "test_p" in manager.list_all()


def test_discover_plugins(manager: PluginManager, tmp_path: Path):
    p_dir = tmp_path / "plugins"
    p_dir.mkdir()
    plugin_code = """
from jarvis.plugins.base import Plugin, PluginType
from jarvis.core.bus import Event
from typing import Any, Optional

class DynamicSample(Plugin):
    name = "dynamic_sample"
    plugin_type = PluginType.TTS
    async def start(self, config: Optional[dict[str, Any]] = None) -> None: pass
    async def stop(self) -> None: pass
    async def on_event(self, event: Event) -> Optional[Event]: return None
    def get_schema(self) -> dict[str, Any]: return {"type": "object"}

plugin_class = DynamicSample
"""
    (p_dir / "sample.py").write_text(plugin_code, encoding="utf-8")
    discovered = manager.discover(p_dir)
    assert "dynamic_sample" in discovered
    assert manager.get_plugin("dynamic_sample") is not None
    assert manager.get_plugin("dynamic_sample").plugin_type == PluginType.TTS


def test_discover_plugins_class_fallback(manager: PluginManager, tmp_path: Path):
    p_dir = tmp_path / "plugins_fallback"
    p_dir.mkdir()
    plugin_code = """
from jarvis.plugins.base import Plugin, PluginType
from jarvis.core.bus import Event
from typing import Any, Optional

class DirectPlugin(Plugin):
    name = "direct_plugin"
    plugin_type = PluginType.LLM
    async def start(self, config: Optional[dict[str, Any]] = None) -> None: pass
    async def stop(self) -> None: pass
    async def on_event(self, event: Event) -> Optional[Event]: return None
    def get_schema(self) -> dict[str, Any]: return {}
"""
    (p_dir / "direct.py").write_text(plugin_code, encoding="utf-8")
    discovered = manager.discover(p_dir)
    assert "direct_plugin" in discovered
    assert manager.get_plugin("direct_plugin") is not None


def test_discover_plugins_ignores_private_files(manager: PluginManager, tmp_path: Path):
    p_dir = tmp_path / "plugins_private"
    p_dir.mkdir()
    (p_dir / "__init__.py").write_text("# init", encoding="utf-8")
    (p_dir / "_private.py").write_text("# private", encoding="utf-8")
    discovered = manager.discover(p_dir)
    assert len(discovered) == 0


def test_discover_plugins_syntax_error_handling(manager: PluginManager, tmp_path: Path):
    p_dir = tmp_path / "plugins_broken"
    p_dir.mkdir()
    (p_dir / "broken.py").write_text("def invalid syntax ::: !!!", encoding="utf-8")
    (p_dir / "good.py").write_text("""
from jarvis.plugins.base import Plugin, PluginType
from jarvis.core.bus import Event
from typing import Any, Optional

class GoodPlugin(Plugin):
    name = "good_plugin"
    plugin_type = PluginType.VISION
    async def start(self, config: Optional[dict[str, Any]] = None) -> None: pass
    async def stop(self) -> None: pass
    async def on_event(self, event: Event) -> Optional[Event]: return None
    def get_schema(self) -> dict[str, Any]: return {}

plugin_class = GoodPlugin
""", encoding="utf-8")
    discovered = manager.discover(p_dir)
    assert "good_plugin" in discovered
    assert len(discovered) == 1


def test_discover_nonexistent_directory(manager: PluginManager, tmp_path: Path):
    nonexistent = tmp_path / "does_not_exist"
    assert manager.discover(nonexistent) == []


@pytest.mark.asyncio
async def test_activate_and_deactivate_plugin(manager: PluginManager):
    p = MockPlugin(name="stt_plugin", plugin_type=PluginType.STT)
    manager.register(p)

    manager.config.set("plugins", "stt_plugin", {"model": "base"})

    activated = await manager.activate("stt_plugin")
    assert activated is True
    assert p.started is True
    assert p.received_config == {"model": "base"}
    assert manager.get_active(PluginType.STT) is p
    assert manager.get_active("stt") is p
    assert "stt_plugin" in manager.get_active_plugins()

    deactivated = await manager.deactivate("stt_plugin")
    assert deactivated is True
    assert p.stopped is True
    assert manager.get_active(PluginType.STT) is None
    assert "stt_plugin" not in manager.get_active_plugins()


@pytest.mark.asyncio
async def test_activate_nonexistent_plugin(manager: PluginManager):
    assert await manager.activate("unknown_plugin") is False


@pytest.mark.asyncio
async def test_activate_already_active_plugin(manager: PluginManager):
    p = MockPlugin(name="active_test")
    manager.register(p)
    assert await manager.activate("active_test") is True
    assert await manager.activate("active_test") is True


@pytest.mark.asyncio
async def test_activate_failing_plugin(manager: PluginManager):
    p = MockPlugin(name="failing", fail_start=True)
    manager.register(p)
    assert await manager.activate("failing") is False
    assert manager.get_active_plugins() == {}


@pytest.mark.asyncio
async def test_deactivate_nonactive_plugin(manager: PluginManager):
    assert await manager.deactivate("not_active") is False


def test_get_schemas(manager: PluginManager):
    p1 = MockPlugin(name="p1")
    p2 = MockPlugin(name="p2")
    manager.register(p1)
    manager.register(p2)
    schemas = manager.get_schemas()
    assert "p1" in schemas
    assert "p2" in schemas
    assert schemas["p1"]["type"] == "object"


@pytest.mark.asyncio
async def test_route_event_to_active_plugins(manager: PluginManager):
    p1 = MockPlugin(name="p1", plugin_type=PluginType.STT)
    p2 = MockPlugin(name="p2", plugin_type=PluginType.TTS)
    manager.register(p1)
    manager.register(p2)

    await manager.activate("p1")
    await manager.activate("p2")

    emitted_events: list[Event] = []

    async def bus_handler(event: Event) -> None:
        emitted_events.append(event)

    manager.bus.on("res", bus_handler)

    test_ev = Event(type="req", data={"query": "test"})
    responses = await manager.route_event(test_ev)

    assert len(p1.received_events) == 1
    assert len(p2.received_events) == 1
    assert len(responses) == 2
    assert responses[0].type == "res"
    assert responses[1].type == "res"

    # Process bus queue to verify bus.emit was invoked
    ev1 = await asyncio.wait_for(manager.bus._queue.get(), timeout=1)
    await bus_handler(ev1)
    ev2 = await asyncio.wait_for(manager.bus._queue.get(), timeout=1)
    await bus_handler(ev2)

    assert len(emitted_events) == 2


@pytest.mark.asyncio
async def test_route_event_ignores_inactive_plugins(manager: PluginManager):
    p1 = MockPlugin(name="p1")
    manager.register(p1)

    test_ev = Event(type="test_event", data={})
    responses = await manager.route_event(test_ev)
    assert len(responses) == 0
    assert len(p1.received_events) == 0


@pytest.mark.asyncio
async def test_route_event_fault_isolation(manager: PluginManager):
    p_fail = MockPlugin(name="p_fail", fail_event=True)
    p_good = MockPlugin(name="p_good")

    manager.register(p_fail)
    manager.register(p_good)

    await manager.activate("p_fail")
    await manager.activate("p_good")

    test_ev = Event(type="req", data={})
    responses = await manager.route_event(test_ev)

    assert len(responses) == 1
    assert responses[0].source == "p_good"
    assert len(p_good.received_events) == 1


@pytest.mark.asyncio
async def test_stop_all(manager: PluginManager):
    p1 = MockPlugin(name="p1")
    p2 = MockPlugin(name="p2")
    manager.register(p1)
    manager.register(p2)

    await manager.activate("p1")
    await manager.activate("p2")
    assert len(manager.get_active_plugins()) == 2

    await manager.stop_all()
    assert len(manager.get_active_plugins()) == 0
    assert p1.stopped is True
    assert p2.stopped is True


@pytest.mark.asyncio
async def test_deactivate_failing_stop(manager: PluginManager):
    p = MockPlugin(name="failing_stop", fail_stop=True)
    manager.register(p)
    await manager.activate("failing_stop")
    assert "failing_stop" in manager.get_active_plugins()

    # Deactivating failing plugin returns False but pops from _active
    deactivated = await manager.deactivate("failing_stop")
    assert deactivated is False
    assert "failing_stop" not in manager.get_active_plugins()


@pytest.mark.asyncio
async def test_stop_all_fault_isolation(manager: PluginManager):
    p_fail = MockPlugin(name="p_fail", fail_stop=True)
    p_good = MockPlugin(name="p_good")
    manager.register(p_fail)
    manager.register(p_good)

    await manager.activate("p_fail")
    await manager.activate("p_good")

    await manager.stop_all()
    assert len(manager.get_active_plugins()) == 0
    assert p_good.stopped is True
