from __future__ import annotations
import asyncio
import pytest
from jarvis.core.bus import Event, EventBus
from jarvis.plugins.base import PluginType
from jarvis.plugins.builtins.clap_detector import ClapDetectorPlugin


@pytest.mark.asyncio
async def test_clap_plugin_metadata_and_schema():
    plugin = ClapDetectorPlugin()
    assert plugin.name == "clap_detector"
    assert plugin.plugin_type == PluginType.ACTIVATION

    schema = plugin.get_schema()
    assert "properties" in schema
    assert "threshold" in schema["properties"]
    assert "window_ms" in schema["properties"]
    assert "min_interval_ms" in schema["properties"]


@pytest.mark.asyncio
async def test_single_clap_no_activation():
    plugin = ClapDetectorPlugin()
    await plugin.start({"threshold": 0.5})

    resp = await plugin.on_event(Event(type="audio_energy", data={"energy": 0.8}))
    assert resp is None
    assert plugin.clap_count == 1

    await plugin.stop()


@pytest.mark.asyncio
async def test_double_clap_triggers_activation():
    bus = EventBus()
    bus_task = asyncio.create_task(bus.process())
    plugin = ClapDetectorPlugin(bus=bus)
    await plugin.start({"threshold": 0.5, "window_ms": 500, "min_interval_ms": 50})

    activations = []

    async def _capture(ev: Event):
        activations.append(ev)

    bus.on("activate", _capture)

    # Clap 1 at t=10.0s
    await plugin.on_event(Event(type="test_clap", data={"timestamp": 10.0}))
    assert plugin.clap_count == 1
    assert len(activations) == 0

    # Clap 2 at t=10.2s (200ms later -> within 50ms..500ms window)
    resp = await plugin.on_event(Event(type="test_clap", data={"timestamp": 10.2}))
    assert resp is not None
    assert resp.type == "activation"
    assert resp.data.get("pattern") == "double_clap"

    await asyncio.sleep(0.05)
    assert len(activations) == 1
    assert activations[0].type == "activate"
    assert plugin.clap_count == 0

    await plugin.stop()
    bus_task.cancel()
    try:
        await bus_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_clap_window_expiration():
    plugin = ClapDetectorPlugin()
    await plugin.start({"threshold": 0.5, "window_ms": 300, "min_interval_ms": 50})

    # Clap 1 at t=10.0s
    await plugin.on_event(Event(type="test_clap", data={"timestamp": 10.0}))
    assert plugin.clap_count == 1

    # Clap 2 at t=10.5s (500ms later -> window expired!)
    resp = await plugin.on_event(Event(type="test_clap", data={"timestamp": 10.5}))
    assert resp is None
    assert plugin.clap_count == 1  # Reset to 1 (new window started)

    await plugin.stop()


@pytest.mark.asyncio
async def test_clap_debounce_too_fast():
    plugin = ClapDetectorPlugin()
    await plugin.start({"threshold": 0.5, "window_ms": 500, "min_interval_ms": 50})

    # Clap 1 at t=10.0s
    await plugin.on_event(Event(type="test_clap", data={"timestamp": 10.0}))
    assert plugin.clap_count == 1

    # Echo at t=10.02s (20ms later -> too fast, ignored)
    resp = await plugin.on_event(Event(type="test_clap", data={"timestamp": 10.02}))
    assert resp is None
    assert plugin.clap_count == 1

    await plugin.stop()


@pytest.mark.asyncio
async def test_clap_low_energy_ignored():
    plugin = ClapDetectorPlugin()
    await plugin.start({"threshold": 0.7})

    resp = await plugin.on_event(Event(type="audio_energy", data={"energy": 0.3}))
    assert resp is None
    assert plugin.clap_count == 0

    await plugin.stop()


@pytest.mark.asyncio
async def test_clap_audio_chunk_rms():
    plugin = ClapDetectorPlugin()
    await plugin.start({"threshold": 0.4})

    # Loud chunk
    loud_chunk = [0.8] * 128
    await plugin.on_event(Event(type="audio_chunk", data={"audio": loud_chunk}))
    assert plugin.clap_count == 1

    await plugin.stop()
