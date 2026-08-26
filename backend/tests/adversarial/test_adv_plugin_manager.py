import asyncio
from pathlib import Path
from typing import Any, Optional
import pytest
from jarvis.core.bus import Event, EventBus
from jarvis.core.config import Config
from jarvis.plugins.base import Plugin, PluginType
from jarvis.plugins.manager import PluginManager


class FragilePlugin(Plugin):
    name = "fragile"
    plugin_type = PluginType.LLM

    def __init__(self, bus=None, config=None, crash_on_start=False, crash_on_stop=False, crash_on_event=False):
        super().__init__(bus, config)
        self.crash_on_start = crash_on_start
        self.crash_on_stop = crash_on_stop
        self.crash_on_event = crash_on_event
        self.started = False
        self.stopped = False

    async def start(self, config: Optional[dict[str, Any]] = None) -> None:
        if self.crash_on_start:
            raise RuntimeError("Fatal start crash")
        self.started = True

    async def stop(self) -> None:
        if self.crash_on_stop:
            raise RuntimeError("Fatal stop crash")
        self.stopped = True

    async def on_event(self, event: Event) -> Optional[Event]:
        if self.crash_on_event:
            raise ValueError("Fatal event routing error")
        return Event(type="fragile_ack", data={"source": self.name})

    def get_schema(self) -> dict[str, Any]:
        return {}


class RobustPlugin(Plugin):
    name = "robust"
    plugin_type = PluginType.TTS

    def __init__(self, bus=None, config=None):
        super().__init__(bus, config)
        self.received = []
        self.stopped = False

    async def start(self, config: Optional[dict[str, Any]] = None) -> None:
        pass

    async def stop(self) -> None:
        self.stopped = True

    async def on_event(self, event: Event) -> Optional[Event]:
        self.received.append(event)
        return Event(type="robust_ack", data={"received": event.type})

    def get_schema(self) -> dict[str, Any]:
        return {"robust": True}


@pytest.mark.asyncio
async def test_route_event_resilience_under_crashing_plugins(tmp_path: Path):
    """Adversarial test: Crashing plugins during event routing must not crash manager or other plugins."""
    bus = EventBus()
    cfg = Config(tmp_path)
    mgr = PluginManager(bus, cfg)

    p_bad = FragilePlugin(crash_on_event=True)
    p_good = RobustPlugin()

    mgr.register(p_bad)
    mgr.register(p_good)

    await mgr.activate("fragile")
    await mgr.activate("robust")

    emitted_responses = []

    async def bus_handler(ev: Event):
        emitted_responses.append(ev)

    bus.on("robust_ack", bus_handler)

    test_ev = Event(type="broadcast_test", data={"hello": "world"})
    responses = await mgr.route_event(test_ev)

    assert len(responses) == 1
    assert responses[0].type == "robust_ack"
    assert len(p_good.received) == 1


@pytest.mark.asyncio
async def test_stop_all_resilience_when_plugin_throws(tmp_path: Path):
    """Adversarial test: If one plugin throws during stop(), other plugins should still be stopped."""
    bus = EventBus()
    cfg = Config(tmp_path)
    mgr = PluginManager(bus, cfg)

    p_bad = FragilePlugin(crash_on_stop=True)
    p_good = RobustPlugin()

    mgr.register(p_bad)
    mgr.register(p_good)

    await mgr.activate("fragile")
    await mgr.activate("robust")

    # stop_all should ideally stop all plugins even if one throws
    try:
        await mgr.stop_all()
    except Exception:
        pass

    assert p_good.stopped is True, "RobustPlugin should have been stopped despite FragilePlugin throwing in stop()"
    assert len(mgr.get_active_plugins()) == 0


@pytest.mark.asyncio
async def test_concurrent_event_routing_and_activation(tmp_path: Path):
    """Stress test: Routing events while plugins are dynamically activated and deactivated."""
    bus = EventBus()
    cfg = Config(tmp_path)
    mgr = PluginManager(bus, cfg)

    for i in range(10):
        p = RobustPlugin()
        p.name = f"plugin_{i}"
        mgr.register(p)

    stop_event = asyncio.Event()

    async def event_router():
        count = 0
        while not stop_event.is_set():
            await mgr.route_event(Event(type="tick", data={"tick": count}))
            count += 1
            await asyncio.sleep(0.001)

    async def lifecycle_churn():
        for _ in range(20):
            for i in range(10):
                await mgr.activate(f"plugin_{i}")
            await asyncio.sleep(0.005)
            for i in range(10):
                await mgr.deactivate(f"plugin_{i}")
            await asyncio.sleep(0.005)

    router_task = asyncio.create_task(event_router())
    churn_task = asyncio.create_task(lifecycle_churn())

    await churn_task
    stop_event.set()
    await router_task


def test_discover_malformed_plugins_spectrum(tmp_path: Path):
    """Adversarial test: Discovering directory containing various broken/malicious Python files."""
    p_dir = tmp_path / "adversarial_plugins"
    p_dir.mkdir()

    # 1. Missing dependencies / import error
    (p_dir / "bad_import.py").write_text("import definitely_non_existent_package_xyz123\n", encoding="utf-8")
    # 2. Syntax error
    (p_dir / "bad_syntax.py").write_text("def %$$$ broken :::", encoding="utf-8")
    # 3. plugin_class is not a class (it's None)
    (p_dir / "none_class.py").write_text("plugin_class = None\n", encoding="utf-8")
    # 4. plugin_class is an integer
    (p_dir / "int_class.py").write_text("plugin_class = 42\n", encoding="utf-8")
    # 5. Abstract Plugin class with missing abstract methods
    (p_dir / "unimplemented_plugin.py").write_text("""
from jarvis.plugins.base import Plugin
class Incomplete(Plugin):
    name = "incomplete"
plugin_class = Incomplete
""", encoding="utf-8")
    # 6. Valid plugin
    (p_dir / "valid_plugin.py").write_text("""
from jarvis.plugins.base import Plugin, PluginType
from typing import Any, Optional
from jarvis.core.bus import Event

class ValidDynamic(Plugin):
    name = "valid_dynamic"
    plugin_type = PluginType.VISION
    async def start(self, config: Optional[dict[str, Any]] = None) -> None: pass
    async def stop(self) -> None: pass
    async def on_event(self, event: Event) -> Optional[Event]: return None
    def get_schema(self) -> dict[str, Any]: return {}

plugin_class = ValidDynamic
""", encoding="utf-8")

    bus = EventBus()
    cfg = Config(tmp_path)
    mgr = PluginManager(bus, cfg)

    discovered = mgr.discover(p_dir)
    assert "valid_dynamic" in discovered
    assert len(discovered) == 1
