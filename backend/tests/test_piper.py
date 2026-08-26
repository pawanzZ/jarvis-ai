from __future__ import annotations
import asyncio
import pytest
from jarvis.core.bus import Event, EventBus
from jarvis.plugins.base import PluginType
from jarvis.plugins.builtins.piper_tts import PiperTTSPlugin


@pytest.mark.asyncio
async def test_piper_plugin_metadata_and_schema():
    plugin = PiperTTSPlugin()
    assert plugin.name == "piper_tts"
    assert plugin.plugin_type == PluginType.TTS

    schema = plugin.get_schema()
    assert "properties" in schema
    assert "voice" in schema["properties"]
    assert "rate" in schema["properties"]
    assert "volume" in schema["properties"]


@pytest.mark.asyncio
async def test_piper_start_stop():
    plugin = PiperTTSPlugin()
    await plugin.start({"voice": "en_GB-alan-low", "rate": 1.2, "volume": 0.8})
    assert plugin._running is True
    assert plugin._voice == "en_GB-alan-low"
    assert plugin._rate == 1.2
    assert plugin._volume == 0.8

    await plugin.stop()
    assert plugin._running is False


def test_piper_synthesize_samples():
    plugin = PiperTTSPlugin()
    samples = plugin.synthesize("Hello sir, all systems nominal.")
    assert len(samples) > 0
    assert all(-1.0 <= s <= 1.0 for s in samples)
    # Empty text returns empty list
    assert plugin.synthesize("") == []


@pytest.mark.asyncio
async def test_piper_speak_lifecycle_events():
    bus = EventBus()
    bus_task = asyncio.create_task(bus.process())
    plugin = PiperTTSPlugin(bus=bus)
    await plugin.start({})

    emitted_types = []

    async def _capture(ev: Event):
        emitted_types.append(ev.type)

    bus.on("tts_start", _capture)
    bus.on("audio_chunk", _capture)
    bus.on("audio_level", _capture)
    bus.on("tts_done", _capture)

    # Issue speak request
    resp = await plugin.on_event(
        Event(type="tts_speak", data={"text": "Online."})
    )
    assert resp is not None
    assert resp.type == "tts_start"

    # Wait for synthesis & playback completion
    await asyncio.sleep(0.4)

    assert "tts_start" in emitted_types
    assert "audio_chunk" in emitted_types
    assert "audio_level" in emitted_types
    assert "tts_done" in emitted_types

    await plugin.stop()
    bus_task.cancel()
    try:
        await bus_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_piper_stop_speaking_interruption():
    bus = EventBus()
    bus_task = asyncio.create_task(bus.process())
    plugin = PiperTTSPlugin(bus=bus)
    await plugin.start({})

    # Start speaking long text
    long_text = "This is a longer paragraph to verify interruption capability of the TTS subsystem."
    await plugin.on_event(Event(type="speak", data={"text": long_text}))
    await asyncio.sleep(0.02)
    assert plugin._speaking is True

    # Interrupt
    resp = await plugin.on_event(Event(type="tts_stop", data={}))
    assert resp is not None
    assert resp.type == "tts_done"
    assert resp.data.get("interrupted") is True
    assert plugin._speaking is False

    await plugin.stop()
    bus_task.cancel()
    try:
        await bus_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_piper_ignores_when_stopped():
    plugin = PiperTTSPlugin()
    resp = await plugin.on_event(Event(type="tts_speak", data={"text": "Test"}))
    assert resp is None
