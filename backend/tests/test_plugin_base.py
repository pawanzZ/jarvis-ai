import pytest
from typing import Any, Optional
from jarvis.plugins.base import Plugin, PluginType
from jarvis.core.bus import Event, EventBus
from jarvis.core.config import Config


def test_plugin_type_enum():
    assert PluginType.STT == "stt"
    assert PluginType.TTS == "tts"
    assert PluginType.LLM == "llm"
    assert PluginType.WAKE_WORD == "wake_word"
    assert PluginType.ACTIVATION == "activation"
    assert PluginType.VISION == "vision"
    assert isinstance(PluginType.STT, str)


def test_plugin_abstract_instantiation_fails():
    with pytest.raises(TypeError):
        Plugin()  # type: ignore

    class IncompletePlugin(Plugin):
        name = "incomplete"
        # missing start, stop, on_event, get_schema

    with pytest.raises(TypeError):
        IncompletePlugin()  # type: ignore

    class MissingSchemaPlugin(Plugin):
        async def start(self, config: Optional[dict[str, Any]] = None) -> None:
            pass

        async def stop(self) -> None:
            pass

        async def on_event(self, event: Event) -> Optional[Event]:
            return None

    with pytest.raises(TypeError):
        MissingSchemaPlugin()  # type: ignore


class DummyPlugin(Plugin):
    name = "dummy_test"
    plugin_type = PluginType.STT

    def __init__(self, bus: Optional[EventBus] = None, config: Optional[Config] = None) -> None:
        super().__init__(bus, config)
        self.started = False
        self.started_config: Optional[dict[str, Any]] = None
        self.stopped = False

    async def start(self, config: Optional[dict[str, Any]] = None) -> None:
        self.started = True
        self.started_config = config

    async def stop(self) -> None:
        self.stopped = True

    async def on_event(self, event: Event) -> Optional[Event]:
        if event.type == "ping_event":
            return Event(type="pong_event", data={"echo": event.data.get("val")}, source=self.name)
        return None

    def get_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "sample_rate": {"type": "integer", "default": 16000},
            },
        }


def test_plugin_concrete_subclass_defaults():
    plugin = DummyPlugin()
    assert plugin.name == "dummy_test"
    assert plugin.plugin_type == PluginType.STT
    assert plugin.bus is None
    assert plugin.config is None


def test_plugin_init_with_bus_and_config(tmp_path):
    bus = EventBus()
    cfg = Config(tmp_path)
    plugin = DummyPlugin(bus=bus, config=cfg)
    assert plugin.bus is bus
    assert plugin.config is cfg


@pytest.mark.asyncio
async def test_plugin_lifecycle_methods():
    plugin = DummyPlugin()
    assert plugin.started is False
    assert plugin.stopped is False

    await plugin.start({"sample_rate": 24000})
    assert plugin.started is True
    assert plugin.started_config == {"sample_rate": 24000}

    await plugin.stop()
    assert plugin.stopped is True


@pytest.mark.asyncio
async def test_plugin_on_event_returns_event():
    plugin = DummyPlugin()
    in_event = Event(type="ping_event", data={"val": 42})
    out_event = await plugin.on_event(in_event)
    assert out_event is not None
    assert out_event.type == "pong_event"
    assert out_event.data == {"echo": 42}
    assert out_event.source == "dummy_test"


@pytest.mark.asyncio
async def test_plugin_on_event_returns_none():
    plugin = DummyPlugin()
    in_event = Event(type="unhandled_event", data={})
    out_event = await plugin.on_event(in_event)
    assert out_event is None


def test_plugin_get_schema():
    plugin = DummyPlugin()
    schema = plugin.get_schema()
    assert isinstance(schema, dict)
    assert schema.get("type") == "object"
    assert "sample_rate" in schema.get("properties", {})
