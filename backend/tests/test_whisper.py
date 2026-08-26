from __future__ import annotations
import asyncio
import pytest
from jarvis.core.bus import Event, EventBus
from jarvis.plugins.base import PluginType
from jarvis.plugins.builtins.whisper_local import WhisperLocalPlugin


@pytest.mark.asyncio
async def test_whisper_plugin_metadata_and_schema():
    plugin = WhisperLocalPlugin()
    assert plugin.name == "whisper_local"
    assert plugin.plugin_type == PluginType.STT

    schema = plugin.get_schema()
    assert "properties" in schema
    assert "model" in schema["properties"]
    assert "language" in schema["properties"]
    assert "engine" in schema["properties"]


@pytest.mark.asyncio
async def test_whisper_start_stop():
    plugin = WhisperLocalPlugin()
    await plugin.start({"model": "tiny", "language": "en", "engine": "mock"})
    assert plugin._running is True
    assert plugin._model_size == "tiny"
    assert plugin._language == "en"

    await plugin.stop()
    assert plugin._running is False


@pytest.mark.asyncio
async def test_whisper_mock_transcribe():
    plugin = WhisperLocalPlugin()
    await plugin.start({})

    plugin.set_mock_transcript("Jarvis initiate protocol zero")
    text = plugin.transcribe([0.1, 0.2, 0.3])
    assert text == "Jarvis initiate protocol zero"

    await plugin.stop()


@pytest.mark.asyncio
async def test_whisper_speech_end_event():
    bus = EventBus()
    bus_task = asyncio.create_task(bus.process())
    plugin = WhisperLocalPlugin(bus=bus)
    await plugin.start({})

    plugin.set_mock_transcript("What is the current time?")
    events_received = []

    async def _on_event(ev: Event):
        events_received.append(ev)

    bus.on("stt_result", _on_event)
    bus.on("transcript_final", _on_event)

    # Trigger speech_end
    result = await plugin.on_event(
        Event(type="speech_end", data={"audio": [0.1] * 1000})
    )

    assert result is not None
    assert result.type == "stt_result"
    assert result.data["text"] == "What is the current time?"

    # Allow bus to process
    await asyncio.sleep(0.05)

    # Check bus emissions
    assert len(events_received) == 2
    assert events_received[0].type == "stt_result"
    assert events_received[1].type == "transcript_final"
    assert events_received[1].data["speaker"] == "user"

    await plugin.stop()
    bus_task.cancel()
    try:
        await bus_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_whisper_audio_chunk_partial_transcript():
    bus = EventBus()
    bus_task = asyncio.create_task(bus.process())
    plugin = WhisperLocalPlugin(bus=bus)
    await plugin.start({})

    plugin.set_mock_transcript("Jarvis...")
    partials = []

    async def _on_partial(ev: Event):
        partials.append(ev)

    bus.on("transcript_partial", _on_partial)

    # Send 8000 samples to trigger partial emission
    chunk_event = Event(type="audio_chunk", data={"audio": [0.05] * 8000})
    resp = await plugin.on_event(chunk_event)

    assert resp is not None
    assert resp.type == "transcript_partial"

    await asyncio.sleep(0.05)
    assert len(partials) == 1
    assert partials[0].data["text"] == "Jarvis..."

    await plugin.stop()
    bus_task.cancel()
    try:
        await bus_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_whisper_ignores_unknown_or_stopped_events():
    plugin = WhisperLocalPlugin()
    # Stopped
    resp1 = await plugin.on_event(Event(type="speech_end", data={}))
    assert resp1 is None

    # Started but unknown event
    await plugin.start({})
    resp2 = await plugin.on_event(Event(type="unrelated_event", data={}))
    assert resp2 is None
    await plugin.stop()
