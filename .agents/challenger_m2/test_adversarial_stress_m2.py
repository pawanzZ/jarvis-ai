"""Adversarial Stress Test Suite for Milestone 2: Pluggable AI & Audio Pipeline.

Deeply stress-tests edge cases, boundary conditions, rapid event bursts,
concurrency, memory safety, and failure isolation.
"""
from __future__ import annotations
import asyncio
import json
import math
import random
import sys
import time
from pathlib import Path
from typing import Any

# Ensure backend jarvis is importable
backend_path = Path("/home/pawan/Projects/jarvis-ai/backend")
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from jarvis.core.bus import Event, EventBus
from jarvis.core.config import Config
from jarvis.core.state import StateMachine, JarvisState
from jarvis.audio.vad import VAD
from jarvis.audio.mic_stream import MicStream
from jarvis.audio.speaker_output import SpeakerOutput
from jarvis.plugins.base import Plugin, PluginType
from jarvis.plugins.manager import PluginManager
from jarvis.plugins.builtins.whisper_local import WhisperLocalPlugin
from jarvis.plugins.builtins.piper_tts import PiperTTSPlugin
from jarvis.plugins.builtins.ollama_llm import OllamaLLMPlugin
from jarvis.plugins.builtins.push_to_talk import PushToTalkPlugin
from jarvis.plugins.builtins.clap_detector import ClapDetectorPlugin
from jarvis.plugins.builtins.face_tracker import FaceTrackerPlugin


async def test_vad_boundary_and_flutter():
    """Test VAD under rapid speech flutter, boundary transitions, and non-standard inputs."""
    print("\n--- [ADV TEST 1] VAD Boundary & Flutter Stress ---")
    vad = VAD(threshold=0.05, hangover_frames=5, min_speech_frames=3)

    # 1. Speech Flutter (1 voiced frame, 1 silence frame alternating 20 times)
    # Because min_speech_frames=3, isolated single voiced frames must NOT trigger speech_started
    voiced = [0.1] * 256
    silence = [0.001] * 256

    for i in range(20):
        res_v = vad.process_frame(voiced)
        assert res_v["speech_started"] is False, "Single flutter frame should not trigger speech start"
        assert res_v["in_speech"] is False
        res_s = vad.process_frame(silence)
        assert res_s["speech_ended"] is False
        assert res_s["in_speech"] is False

    assert vad.in_speech is False

    # 2. Reaching min_speech_frames exactly
    vad.process_frame(voiced)  # frame 1
    assert vad.in_speech is False
    vad.process_frame(voiced)  # frame 2
    assert vad.in_speech is False
    r3 = vad.process_frame(voiced)  # frame 3 -> triggers!
    assert r3["speech_started"] is True
    assert r3["in_speech"] is True
    assert vad.in_speech is True

    # 3. Ongoing speech -> remains in speech
    for _ in range(10):
        r = vad.process_frame(voiced)
        assert r["in_speech"] is True
        assert r["speech_started"] is False

    # 4. Hangover frames smoothing (4 frames silence -> still in_speech, 5th frame -> speech_ended)
    for _ in range(4):
        r_sil = vad.process_frame(silence)
        assert r_sil["in_speech"] is True
        assert r_sil["speech_ended"] is False

    r_end = vad.process_frame(silence)  # 5th silence frame
    assert r_end["speech_ended"] is True
    assert r_end["in_speech"] is False
    assert vad.in_speech is False

    # 5. Non-standard data types: int16 bytes, scalar, float list, empty, nan/inf
    assert vad.calculate_energy(0.5) == 0.5
    assert vad.calculate_energy(16384) == 0.5  # int16 scale
    assert vad.calculate_energy(b"\x00\x20\x00\x20") > 0.0  # valid PCM bytes
    assert vad.calculate_energy(b"") == 0.0
    vad.reset()
    assert vad.in_speech is False
    print("  => PASSED: VAD boundary and flutter resilience verified.")


async def test_audio_hardware_simulation_and_interruption():
    """Test MicStream and SpeakerOutput under cancellation and concurrency stress."""
    print("\n--- [ADV TEST 2] Audio Simulation & Interruption Stress ---")
    # 1. MicStream async iteration under rapid start/stop
    mic = MicStream(sample_rate=16000, chunk_size=256, simulate=True)
    await mic.start()

    collected_chunks = 0
    async def read_worker():
        nonlocal collected_chunks
        async for chunk in mic.chunks():
            collected_chunks += 1
            if collected_chunks >= 5:
                break

    task = asyncio.create_task(read_worker())
    await asyncio.wait_for(task, timeout=1.0)
    assert collected_chunks >= 5
    await mic.stop()
    assert mic.is_recording is False

    # 2. SpeakerOutput rapid start-stop-start interruption (barge-in stress)
    speaker = SpeakerOutput(sample_rate=24000, simulate=True)
    speaker.set_volume(0.8)
    assert speaker.get_volume() == 0.8

    # Clamping test
    speaker.volume = 1.5
    assert speaker.volume == 1.0
    speaker.volume = -0.5
    assert speaker.volume == 0.0
    speaker.volume = 0.9

    long_audio = [0.1] * 48000  # 2.0 seconds of audio

    for _ in range(10):
        # Start play
        play_task = asyncio.create_task(speaker.play(long_audio))
        await asyncio.sleep(0.01)
        assert speaker.is_playing is True
        # Immediately interrupt
        speaker.stop()
        assert speaker.is_playing is False
        try:
            await play_task
        except asyncio.CancelledError:
            pass

    print("  => PASSED: Audio simulation and interruption stress verified.")


async def test_whisper_streaming_and_edge_events():
    """Test Whisper STT with partial transcript thresholds, edge payloads, and schema."""
    print("\n--- [ADV TEST 3] Whisper STT Streaming & Edge Events ---")
    bus = EventBus()
    bus_task = asyncio.create_task(bus.process())
    config = Config(Path("/tmp/jarvis_challenger_cfg3"))
    whisper = WhisperLocalPlugin(bus=bus, config=config)
    await whisper.start({"engine": "mock", "language": "en"})

    partial_events: list[Event] = []
    final_events: list[Event] = []

    async def on_partial(ev: Event):
        partial_events.append(ev)

    async def on_final(ev: Event):
        final_events.append(ev)

    bus.on("transcript_partial", on_partial)
    bus.on("transcript_final", on_final)

    # 1. Feed small chunks < 8000 samples -> No partial transcript yet
    for _ in range(5):
        await whisper.on_event(Event(type="audio_chunk", data={"audio": [0.02] * 1000}))

    await asyncio.sleep(0.01)
    assert len(partial_events) == 0, "Partial transcript should not emit under 8000 samples"

    # 2. Feed enough chunks to exceed 8000 samples -> Partial transcript emitted
    for _ in range(4):
        await whisper.on_event(Event(type="audio_chunk", data={"audio": [0.02] * 1000}))

    await asyncio.sleep(0.02)
    assert len(partial_events) >= 1, "Partial transcript should emit once >= 8000 samples"
    assert partial_events[0].data.get("is_final") is False

    # 3. Speech End -> Final transcript emitted, audio buffer cleared
    stt_resp = await whisper.on_event(Event(type="speech_end", data={}))
    await asyncio.sleep(0.02)
    assert stt_resp is not None
    assert stt_resp.type == "stt_result"
    assert len(final_events) == 1
    assert final_events[0].data.get("speaker") == "user"
    assert len(whisper._audio_buffer) == 0, "Buffer must be cleared on speech_end"

    # 4. speech_end with empty buffer
    empty_res = await whisper.on_event(Event(type="speech_end", data={"audio": []}))
    assert empty_res is not None
    assert "Hello Jarvis" in empty_res.data.get("text")

    # 5. Schema validation
    schema = whisper.get_schema()
    assert schema["type"] == "object"
    assert "model" in schema["properties"]
    assert "language" in schema["properties"]

    await whisper.stop()
    bus_task.cancel()
    try:
        await bus_task
    except asyncio.CancelledError:
        pass
    print("  => PASSED: Whisper STT streaming and edge events verified.")


async def test_piper_tts_cancellation_and_waveform_integrity():
    """Test Piper TTS cancellation mid-speech, waveform amplitude limits, and zero text."""
    print("\n--- [ADV TEST 4] Piper TTS Interruption & Waveform Integrity ---")
    bus = EventBus()
    bus_task = asyncio.create_task(bus.process())
    piper = PiperTTSPlugin(bus=bus)
    await piper.start({"voice": "en_US-lessac-medium", "rate": 1.2, "volume": 0.9})

    # 1. Synthesize huge text and verify all samples are in [-1.0, 1.0] range
    long_text = "Iron Man Mark 85 armor diagnostic complete. " * 50
    samples = piper.synthesize(long_text)
    assert len(samples) > 1000
    for s in samples:
        assert -1.0 <= s <= 1.0, f"Sample out of bounds: {s}"

    # 2. Empty text synthesis
    assert piper.synthesize("") == []

    # 3. Active speech cancellation mid-stream via tts_stop event
    done_events: list[Event] = []
    async def on_done(ev: Event):
        done_events.append(ev)

    bus.on("tts_done", on_done)

    # Start long utterance
    start_res = await piper.on_event(Event(type="tts_speak", data={"text": long_text}))
    assert start_res is not None
    assert start_res.type == "tts_start"
    await asyncio.sleep(0.05)
    assert piper._speaking is True

    # Send tts_stop to interrupt
    stop_res = await piper.on_event(Event(type="tts_stop", data={}))
    assert stop_res is not None
    assert stop_res.type == "tts_done"
    assert stop_res.data.get("interrupted") is True
    assert piper._speaking is False

    await asyncio.sleep(0.05)

    # 4. Schema validation
    schema = piper.get_schema()
    assert schema["type"] == "object"
    assert "voice" in schema["properties"]
    assert "rate" in schema["properties"]

    await piper.stop()
    bus_task.cancel()
    try:
        await bus_task
    except asyncio.CancelledError:
        pass
    print("  => PASSED: Piper TTS interruption and waveform integrity verified.")


async def test_ollama_offline_fallback_and_token_streaming():
    """Test Ollama LLM offline conversational rule engine and token streaming."""
    print("\n--- [ADV TEST 5] Ollama LLM Fallback & Token Streaming ---")
    bus = EventBus()
    bus_task = asyncio.create_task(bus.process())
    ollama = OllamaLLMPlugin(bus=bus)
    # Point to nonexistent port to trigger automatic offline fallback
    await ollama.start({"base_url": "http://127.0.0.1:9999", "model": "llama3"})

    tokens_streamed: list[str] = []
    async def on_token(ev: Event):
        tokens_streamed.append(ev.data.get("token", ""))

    bus.on("llm_token", on_token)

    # 1. Test conversational triggers
    prompts_and_keywords = [
        ("What is your status?", "ARC reactor"),
        ("What is the time right now?", "current time"),
        ("What is the weather?", "Atmospheric"),
        ("Who are you?", "JARVIS"),
        ("Hello Jarvis", "Greetings"),
        ("Thank you very much", "pleasure"),
    ]

    for prompt, expected_keyword in prompts_and_keywords:
        tokens_streamed.clear()
        res = await ollama.on_event(Event(type="llm_request", data={"prompt": prompt}))
        assert res is not None
        assert res.type == "response_complete"
        full_text = res.data.get("text", "")
        assert expected_keyword.lower() in full_text.lower(), (
            f"Prompt '{prompt}' generated '{full_text}', missing '{expected_keyword}'"
        )
        assert len(tokens_streamed) > 0

    # 2. Test mock override priority
    ollama.set_mock_response("override_key", "OVERRIDE_ACTIVE")
    res_override = await ollama.on_event(Event(type="llm_request", data={"prompt": "test override_key"}))
    assert "OVERRIDE_ACTIVE" in res_override.data.get("text", "")

    # 3. Schema validation
    schema = ollama.get_schema()
    assert schema["type"] == "object"
    assert "model" in schema["properties"]
    assert "temperature" in schema["properties"]

    await ollama.stop()
    bus_task.cancel()
    try:
        await bus_task
    except asyncio.CancelledError:
        pass
    print("  => PASSED: Ollama LLM fallback and streaming verified.")


async def test_face_tracker_exact_angles_and_json_serialization():
    """Test Face Tracker boundary attention angles and WebSocket JSON serialization."""
    print("\n--- [ADV TEST 6] Face Tracker Angles & JSON Serialization ---")
    bus = EventBus()
    bus_task = asyncio.create_task(bus.process())
    face = FaceTrackerPlugin(bus=bus)
    await face.start({})

    # 1. Exact boundary testing of _compute_attention
    # Gaze boundary: [0.2, 0.8]
    assert face._compute_attention([0.20, 0.50], {"yaw": 0, "pitch": 0}) is True
    assert face._compute_attention([0.80, 0.50], {"yaw": 0, "pitch": 0}) is True
    assert face._compute_attention([0.19, 0.50], {"yaw": 0, "pitch": 0}) is False
    assert face._compute_attention([0.81, 0.50], {"yaw": 0, "pitch": 0}) is False

    # Pose boundary: yaw <= 25.0, pitch <= 25.0
    assert face._compute_attention([0.5, 0.5], {"yaw": 25.0, "pitch": 0.0}) is True
    assert face._compute_attention([0.5, 0.5], {"yaw": -25.0, "pitch": 0.0}) is True
    assert face._compute_attention([0.5, 0.5], {"yaw": 25.1, "pitch": 0.0}) is False
    assert face._compute_attention([0.5, 0.5], {"yaw": 0.0, "pitch": 25.0}) is True
    assert face._compute_attention([0.5, 0.5], {"yaw": 0.0, "pitch": 25.1}) is False

    # 2. Verify all emitted telemetry payloads are valid JSON for WebSocket broadcasting
    last_telemetry: dict[str, Any] = {}
    async def on_telemetry(ev: Event):
        nonlocal last_telemetry
        last_telemetry = ev.data

    bus.on("face_telemetry", on_telemetry)

    face.set_mock_face_state(detected=True, gaze=[0.5, 0.5], pose={"yaw": 10.0, "pitch": -5.0, "roll": 2.0}, blink=True)
    await face.on_event(Event(type="camera_frame", data={}))
    await asyncio.sleep(0.01)

    # Serialize to JSON (must not raise TypeError)
    json_str = json.dumps(last_telemetry)
    parsed = json.loads(json_str)
    assert parsed["detected"] is True
    assert parsed["attention"] is True
    assert parsed["blink"] is True
    assert parsed["head_pose"]["yaw"] == 10.0

    await face.stop()
    bus_task.cancel()
    try:
        await bus_task
    except asyncio.CancelledError:
        pass
    print("  => PASSED: Face Tracker boundary angles and JSON serialization verified.")


async def test_plugin_manager_lifecycle_stress():
    """Test PluginManager rapid load, activation, event routing, and teardown cycles."""
    print("\n--- [ADV TEST 7] PluginManager Dynamic Lifecycle Stress ---")
    bus = EventBus()
    bus_task = asyncio.create_task(bus.process())
    config = Config(Path("/tmp/jarvis_challenger_cfg_pm"))
    pm = PluginManager(bus, config)

    builtins_dir = Path("/home/pawan/Projects/jarvis-ai/backend/jarvis/plugins/builtins")
    discovered = pm.discover(builtins_dir)
    assert len(discovered) == 6
    assert set(discovered) == {
        "whisper_local",
        "piper_tts",
        "ollama_llm",
        "push_to_talk",
        "clap_detector",
        "face_tracker",
    }

    # 10 Rapid Activate / Deactivate cycles
    for cycle in range(10):
        for name in discovered:
            act_ok = await pm.activate(name)
            assert act_ok is True
        assert len(pm.get_active_plugins()) == 6

        # Route test event
        resps = await pm.route_event(Event(type="test_ping", data={"cycle": cycle}))
        assert isinstance(resps, list)

        # Deactivate
        await pm.stop_all()
        assert len(pm.get_active_plugins()) == 0

    # Test schemas retrieval
    schemas = pm.get_schemas()
    assert len(schemas) == 6
    for name, schema in schemas.items():
        assert isinstance(schema, dict)
        assert schema.get("type") == "object"

    bus_task.cancel()
    try:
        await bus_task
    except asyncio.CancelledError:
        pass
    print("  => PASSED: PluginManager dynamic lifecycle stress verified.")


async def main():
    print("=================================================================")
    print("  STARTING ADVERSARIAL STRESS TEST SUITE FOR MILESTONE 2")
    print("=================================================================")
    t0 = time.time()
    await test_vad_boundary_and_flutter()
    await test_audio_hardware_simulation_and_interruption()
    await test_whisper_streaming_and_edge_events()
    await test_piper_tts_cancellation_and_waveform_integrity()
    await test_ollama_offline_fallback_and_token_streaming()
    await test_face_tracker_exact_angles_and_json_serialization()
    await test_plugin_manager_lifecycle_stress()
    elapsed = time.time() - t0
    print("\n=================================================================")
    print(f"  ALL 7 ADVERSARIAL STRESS TEST SUITES PASSED in {elapsed:.2f}s!")
    print("=================================================================")


if __name__ == "__main__":
    asyncio.run(main())
