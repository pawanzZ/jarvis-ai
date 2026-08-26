from __future__ import annotations
import asyncio
import pytest
from jarvis.core.bus import Event, EventBus
from jarvis.plugins.base import PluginType
from jarvis.plugins.builtins.push_to_talk import PushToTalkPlugin


@pytest.mark.asyncio
async def test_ptt_plugin_metadata_and_schema():
    plugin = PushToTalkPlugin()
    assert plugin.name == "push_to_talk"
    assert plugin.plugin_type == PluginType.ACTIVATION

    schema = plugin.get_schema()
    assert "properties" in schema
    assert "key" in schema["properties"]
    assert "mode" in schema["properties"]


@pytest.mark.asyncio
async def test_ptt_hold_mode_activation_and_deactivation():
    bus = EventBus()
    bus_task = asyncio.create_task(bus.process())
    plugin = PushToTalkPlugin(bus=bus)
    await plugin.start({"key": "space", "mode": "hold"})

    emissions = []

    async def _capture(ev: Event):
        emissions.append(ev)

    bus.on("activate", _capture)
    bus.on("deactivate", _capture)

    # Press space
    down_resp = await plugin.on_event(Event(type="key_down", data={"key": "space"}))
    assert down_resp is not None
    assert down_resp.type == "activation"
    assert plugin.is_pressed is True
    assert plugin.is_active is True

    await asyncio.sleep(0.05)
    assert len(emissions) == 1
    assert emissions[0].type == "activate"

    # Redundant key down while held
    down_resp_repeat = await plugin.on_event(Event(type="key_down", data={"key": "space"}))
    assert down_resp_repeat is None
    await asyncio.sleep(0.02)
    assert len(emissions) == 1

    # Release space
    up_resp = await plugin.on_event(Event(type="key_up", data={"key": "space"}))
    assert up_resp is not None
    assert up_resp.type == "deactivation"
    assert plugin.is_pressed is False
    assert plugin.is_active is False

    await asyncio.sleep(0.05)
    assert len(emissions) == 2
    assert emissions[1].type == "deactivate"

    await plugin.stop()
    bus_task.cancel()
    try:
        await bus_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_ptt_ignores_unmatched_key():
    plugin = PushToTalkPlugin()
    await plugin.start({"key": "space"})

    resp = await plugin.on_event(Event(type="key_down", data={"key": "enter"}))
    assert resp is None
    assert plugin.is_pressed is False

    await plugin.stop()


@pytest.mark.asyncio
async def test_ptt_toggle_mode():
    bus = EventBus()
    bus_task = asyncio.create_task(bus.process())
    plugin = PushToTalkPlugin(bus=bus)
    await plugin.start({"key": "capslock", "mode": "toggle"})

    # 1st press -> Activate
    resp1 = await plugin.on_event(Event(type="key_down", data={"key": "capslock"}))
    assert resp1 is not None
    assert resp1.type == "activation"
    assert plugin.is_active is True

    # 2nd press -> Deactivate
    resp2 = await plugin.on_event(Event(type="key_down", data={"key": "capslock"}))
    assert resp2 is not None
    assert resp2.type == "deactivation"
    assert plugin.is_active is False

    await plugin.stop()
    bus_task.cancel()
    try:
        await bus_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_ptt_ignores_when_stopped():
    plugin = PushToTalkPlugin()
    resp = await plugin.on_event(Event(type="key_down", data={"key": "space"}))
    assert resp is None
