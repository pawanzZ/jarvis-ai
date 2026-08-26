from __future__ import annotations
import asyncio
from pathlib import Path
import pytest
from jarvis.core.bus import Event, EventBus
from jarvis.core.config import Config
from jarvis.plugins.manager import PluginManager
from jarvis.plugins.builtins.clap_detector import ClapDetectorPlugin
from jarvis.plugins.builtins.push_to_talk import PushToTalkPlugin
from jarvis.plugins.builtins.face_tracker import FaceTrackerPlugin
from jarvis.plugins.builtins.piper_tts import PiperTTSPlugin
from jarvis.plugins.builtins.ollama_llm import OllamaLLMPlugin


@pytest.mark.asyncio
async def test_full_builtin_suite_discovery_activation_and_routing(tmp_path):
    bus = EventBus()
    bus_task = asyncio.create_task(bus.process())
    config = Config(tmp_path)
    pm = PluginManager(bus, config)

    builtins_dir = Path(__file__).parent.parent.parent / "jarvis" / "plugins" / "builtins"
    discovered = pm.discover(builtins_dir)
    assert len(discovered) == 6

    # Activate all 6 plugins
    for name in discovered:
        success = await pm.activate(name)
        assert success is True, f"Failed to activate {name}"

    assert len(pm.get_active_plugins()) == 6

    # Route various events across all active plugins
    events_to_test = [
        Event(type="key_down", data={"key": "space"}),
        Event(type="key_up", data={"key": "space"}),
        Event(type="audio_energy", data={"energy": 0.9}),
        Event(type="camera_frame", data={"frame": None}),
        Event(type="speech_end", data={"audio": [0.1] * 500}),
        Event(type="llm_request", data={"prompt": "System report"}),
        Event(type="tts_speak", data={"text": "Acknowledged."}),
        Event(type="unknown_event", data={"foo": "bar"}),
    ]

    for ev in events_to_test:
        responses = await pm.route_event(ev)
        assert isinstance(responses, list)

    await asyncio.sleep(0.1)

    # Stop all plugins cleanly
    await pm.stop_all()
    assert len(pm.get_active_plugins()) == 0

    bus_task.cancel()
    try:
        await bus_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_ptt_rapid_pounding():
    plugin = PushToTalkPlugin()
    await plugin.start({"key": "space", "mode": "hold"})

    for _ in range(50):
        await plugin.on_event(Event(type="key_down", data={"key": "space"}))
        await plugin.on_event(Event(type="key_up", data={"key": "space"}))

    assert plugin.is_pressed is False
    await plugin.stop()


@pytest.mark.asyncio
async def test_clap_detector_flood_spikes():
    plugin = ClapDetectorPlugin()
    await plugin.start({"threshold": 0.5, "window_ms": 300, "min_interval_ms": 50})

    # 100 spikes within 10ms (should debounce and not trigger 50 activations)
    for _ in range(100):
        await plugin.on_event(Event(type="audio_energy", data={"energy": 0.9}))

    assert plugin.clap_count == 1
    await plugin.stop()


@pytest.mark.asyncio
async def test_face_tracker_oscillation_stress():
    bus = EventBus()
    bus_task = asyncio.create_task(bus.process())
    plugin = FaceTrackerPlugin(bus=bus)
    await plugin.start({})

    for i in range(20):
        plugin.set_mock_face_state(detected=(i % 2 == 0))
        await plugin.on_event(Event(type="poll_face", data={}))

    await asyncio.sleep(0.05)
    await plugin.stop()
    bus_task.cancel()
    try:
        await bus_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_tts_and_llm_unicode_and_emoji_handling():
    tts = PiperTTSPlugin()
    await tts.start({})
    samples = tts.synthesize("Jarvis 🔥 Iron Man Mark 85 🚀 100% efficiency!")
    assert len(samples) > 0
    await tts.stop()

    llm = OllamaLLMPlugin()
    await llm.start({})
    tokens = [t async for t in llm.generate_stream("Status 🛡️ ⚡")]
    assert len(tokens) > 0
    await llm.stop()
