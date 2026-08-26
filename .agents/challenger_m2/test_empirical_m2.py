"""Empirical Challenge Verification Harness for Milestone 2: Pluggable AI & Audio Pipeline.

This script executes deep, adversarial stress tests and end-to-end pipeline verifications
for the Jarvis AI Milestone 2 subsystems.
"""
from __future__ import annotations
import asyncio
import math
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


async def test_end_to_end_voice_loop():
    """Verify End-to-End Voice Loop:

    Mic -> VAD -> Whisper STT -> Ollama LLM -> Piper TTS -> Speaker Output
    with coordinated StateMachine state transitions.
    """
    print("\n--- [TEST] End-to-End Voice Loop ---")
    bus = EventBus()
    bus_task = asyncio.create_task(bus.process())
    state = StateMachine()
    config = Config(Path("/tmp/jarvis_challenger_cfg"))

    # Track received events and state changes
    events_log: list[str] = []
    state_transitions: list[str] = []

    async def log_state(old_st: JarvisState, new_st: JarvisState):
        msg = f"{old_st.value}->{new_st.value}"
        state_transitions.append(msg)
        print(f"  [State Transition] {msg}")

    state.on_change(log_state)

    # Instantiate plugins and components
    mic = MicStream(sample_rate=16000, chunk_size=512, simulate=True)
    vad = VAD(threshold=0.03, sample_rate=16000, hangover_frames=3, min_speech_frames=2)
    whisper = WhisperLocalPlugin(bus=bus, config=config)
    ollama = OllamaLLMPlugin(bus=bus, config=config)
    piper = PiperTTSPlugin(bus=bus, config=config)
    speaker = SpeakerOutput(sample_rate=22050, simulate=True)

    await whisper.start({"engine": "mock"})
    await ollama.start({"model": "llama3"})
    await piper.start({"voice": "en_US-lessac-medium", "sample_rate": 22050})
    await mic.start()

    # Configure custom mock LLM response for determinism
    whisper.set_mock_transcript("Jarvis, report reactor status")
    ollama.set_mock_response("reactor", "Reactor operating at 100 percent nominal output.")

    # Wire bus listeners to transition StateMachine
    async def on_stt_result(ev: Event):
        events_log.append("stt_result")
        print(f"  [STT Result Received] '{ev.data.get('text')}'")
        if state.state == JarvisState.LISTENING:
            await state.transition(JarvisState.THINKING)
        # Forward prompt to LLM
        await ollama.on_event(ev)

    async def on_llm_response(ev: Event):
        events_log.append("llm_response")
        print(f"  [LLM Response Generated] '{ev.data.get('text')}'")
        if state.state == JarvisState.THINKING:
            await state.transition(JarvisState.SPEAKING)
        # Forward to TTS
        await piper.on_event(ev)

    async def on_tts_start(ev: Event):
        events_log.append("tts_start")
        print(f"  [TTS Speaking Started] text='{ev.data.get('text')}'")

    async def on_audio_chunk_tts(ev: Event):
        if ev.data.get("source") == "tts":
            events_log.append("tts_audio_chunk")

    async def on_tts_done(ev: Event):
        events_log.append("tts_done")
        print(f"  [TTS Playback Complete] duration={ev.data.get('duration'):.2f}s")
        if state.state == JarvisState.SPEAKING:
            await state.transition(JarvisState.IDLE)

    bus.on("stt_result", on_stt_result)
    bus.on("llm_response", on_llm_response)
    bus.on("tts_start", on_tts_start)
    bus.on("audio_chunk", on_audio_chunk_tts)
    bus.on("tts_done", on_tts_done)

    # 1. Start Voice Trigger (Transition to LISTENING)
    assert state.state == JarvisState.IDLE
    await state.transition(JarvisState.LISTENING)

    # 2. Simulate User Speech: 5 frames of voiced audio (amplitude 0.1)
    voiced_frame = [0.1] * 512
    silence_frame = [0.001] * 512

    for _ in range(5):
        vad_res = vad.process_frame(voiced_frame)
        assert vad_res["energy"] >= 0.03
        await whisper.on_event(Event(type="audio_chunk", data={"audio": voiced_frame}))

    assert vad.in_speech is True

    # 3. Simulate Speech End: 4 frames of silence (hangover=3 triggers speech_ended)
    speech_ended_triggered = False
    for _ in range(4):
        vad_res = vad.process_frame(silence_frame)
        if vad_res["speech_ended"]:
            speech_ended_triggered = True
            await whisper.on_event(Event(type="speech_end", data={"audio": voiced_frame * 5}))

    assert speech_ended_triggered is True

    # 4. Wait for full asynchronous pipeline propagation (LLM streaming + TTS playback)
    tts_done_flag = asyncio.Event()

    async def on_tts_done_signal(ev: Event):
        tts_done_flag.set()

    bus.on("tts_done", on_tts_done_signal)

    try:
        await asyncio.wait_for(tts_done_flag.wait(), timeout=3.0)
    except asyncio.TimeoutError:
        pass
    await asyncio.sleep(0.05)

    # 5. Verify State Transitions and Pipeline Flow
    print(f"  Events recorded: {set(events_log)}")
    print(f"  State history: {state_transitions}")

    assert "stt_result" in events_log, "STT Result was not emitted"
    assert "llm_response" in events_log, "LLM Response was not generated"
    assert "tts_start" in events_log, "TTS start was not emitted"
    assert "tts_audio_chunk" in events_log, "TTS audio chunks were not streamed"
    assert "tts_done" in events_log, "TTS completion was not signaled"

    assert state_transitions == [
        "idle->listening",
        "listening->thinking",
        "thinking->speaking",
        "speaking->idle",
    ], f"Unexpected state transition sequence: {state_transitions}"

    # Cleanup
    await mic.stop()
    await whisper.stop()
    await ollama.stop()
    await piper.stop()
    bus_task.cancel()
    try:
        await bus_task
    except asyncio.CancelledError:
        pass
    print("  => PASSED: End-to-End Voice Loop verified successfully.")


async def test_clap_detector_timing_and_noise_rejection():
    """Verify Clap Detector temporal windows, debouncing, and noise rejection."""
    print("\n--- [TEST] Clap Detector Double-Clap Timing & Noise Rejection ---")
    bus = EventBus()
    bus_task = asyncio.create_task(bus.process())
    clap_plugin = ClapDetectorPlugin(bus=bus)

    # Config: threshold=0.7, window=400ms, min_interval=60ms
    await clap_plugin.start({"threshold": 0.7, "window_ms": 400, "min_interval_ms": 60})

    activations = 0

    async def on_activate(ev: Event):
        nonlocal activations
        activations += 1
        print(f"  [Clap Detector Triggered] activation count={activations}")

    bus.on("activate", on_activate)

    # Scenario A: Single isolated clap -> No activation
    t0 = 100.0
    await clap_plugin.on_event(Event(type="test_clap", data={"timestamp": t0}))
    await asyncio.sleep(0.01)
    assert activations == 0, "Single clap must not trigger activation"
    assert clap_plugin.clap_count == 1

    # Scenario B: Second clap too fast (echo/reverberation at 20ms < min_interval 60ms) -> Ignored
    await clap_plugin.on_event(Event(type="test_clap", data={"timestamp": t0 + 0.020}))
    await asyncio.sleep(0.01)
    assert activations == 0, "Sub-min-interval echo must be debounced"

    # Scenario C: Valid second clap at 150ms -> Triggers Activation
    await clap_plugin.on_event(Event(type="test_clap", data={"timestamp": t0 + 0.150}))
    await asyncio.sleep(0.02)
    assert activations == 1, "Valid double-clap must trigger activation"
    assert clap_plugin.clap_count == 0, "Clap count must reset after activation"

    # Scenario D: Second clap too late (500ms > window_ms 400ms) -> Expired window
    t1 = 200.0
    await clap_plugin.on_event(Event(type="test_clap", data={"timestamp": t1}))
    assert clap_plugin.clap_count == 1
    # Expired 2nd clap at t1 + 0.5s -> should reset window and become new 1st clap
    await clap_plugin.on_event(Event(type="test_clap", data={"timestamp": t1 + 0.500}))
    await asyncio.sleep(0.01)
    assert activations == 1, "Clap outside window must not trigger double-clap"
    assert clap_plugin.clap_count == 1, "Late clap becomes new first clap"

    # Scenario E: Continuous sub-threshold noise (energy 0.5 < 0.7) -> Ignored
    for _ in range(20):
        await clap_plugin.on_event(Event(type="audio_energy", data={"energy": 0.5}))
    await asyncio.sleep(0.01)
    assert activations == 1, "Sub-threshold noise must be rejected"

    # Scenario F: Raw audio chunk RMS calculation with pulse waveform
    # Create sharp impulse: 0.95 amplitude spike
    spike_audio = [0.0] * 256
    spike_audio[10] = 0.95
    spike_audio[11] = 0.90
    spike_audio[12] = 0.85
    # Wait for min_interval
    t_now = time.monotonic()
    # Feed first spike via test_clap to establish clean baseline time
    await clap_plugin.stop()
    await clap_plugin.start({"threshold": 0.05, "window_ms": 500, "min_interval_ms": 20})
    await clap_plugin.on_event(Event(type="audio_chunk", data={"audio": spike_audio}))
    assert clap_plugin.clap_count == 1
    await asyncio.sleep(0.05)  # 50ms pause > 20ms min_interval
    await clap_plugin.on_event(Event(type="audio_chunk", data={"audio": spike_audio}))
    await asyncio.sleep(0.02)
    assert activations == 2, "Double spike audio chunk must trigger activation"

    await clap_plugin.stop()
    bus_task.cancel()
    try:
        await bus_task
    except asyncio.CancelledError:
        pass
    print("  => PASSED: Clap Detector timing and noise rejection verified.")


async def test_push_to_talk_state_transitions():
    """Verify Push-to-Talk Hold and Toggle modes with edge cases."""
    print("\n--- [TEST] Push-to-Talk State Transitions ---")
    bus = EventBus()
    bus_task = asyncio.create_task(bus.process())
    ptt = PushToTalkPlugin(bus=bus)

    emitted_events: list[str] = []

    async def on_bus_event(ev: Event):
        emitted_events.append(ev.type)

    bus.on("activate", on_bus_event)
    bus.on("deactivate", on_bus_event)

    # 1. Test HOLD Mode (Default)
    await ptt.start({"key": "control_l", "mode": "hold"})
    assert ptt.is_pressed is False
    assert ptt.is_active is False

    # Key down for configured key
    ev_down = await ptt.on_event(Event(type="key_down", data={"key": "control_l"}))
    assert ev_down is not None and ev_down.type == "activation"
    assert ptt.is_pressed is True
    assert ptt.is_active is True

    # Repeated key down (holding key generates multiple OS events) -> No duplicate activate
    ev_repeat = await ptt.on_event(Event(type="key_down", data={"key": "control_l"}))
    assert ev_repeat is None
    await asyncio.sleep(0.01)
    assert emitted_events == ["activate"]

    # Key up
    ev_up = await ptt.on_event(Event(type="key_up", data={"key": "control_l"}))
    assert ev_up is not None and ev_up.type == "deactivation"
    assert ptt.is_pressed is False
    assert ptt.is_active is False
    await asyncio.sleep(0.01)
    assert emitted_events == ["activate", "deactivate"]

    # Repeated key up -> No duplicate deactivate
    ev_up_repeat = await ptt.on_event(Event(type="key_up", data={"key": "control_l"}))
    assert ev_up_repeat is None

    # Unrelated key -> Ignored
    ev_other = await ptt.on_event(Event(type="key_down", data={"key": "shift_r"}))
    assert ev_other is None
    assert ptt.is_active is False

    # 2. Test TOGGLE Mode
    emitted_events.clear()
    await ptt.stop()
    await ptt.start({"key": "f12", "mode": "toggle"})

    # 1st Press -> Activate
    await ptt.on_event(Event(type="key_down", data={"key": "f12"}))
    assert ptt.is_active is True
    # Key up in toggle mode should do nothing
    await ptt.on_event(Event(type="key_up", data={"key": "f12"}))
    assert ptt.is_active is True

    # 2nd Press -> Deactivate
    await ptt.on_event(Event(type="key_down", data={"key": "f12"}))
    assert ptt.is_active is False

    # 3rd Press -> Activate again
    await ptt.on_event(Event(type="key_down", data={"key": "f12"}))
    assert ptt.is_active is True

    await asyncio.sleep(0.01)
    assert emitted_events == ["activate", "deactivate", "activate"]

    await ptt.stop()
    bus_task.cancel()
    try:
        await bus_task
    except asyncio.CancelledError:
        pass
    print("  => PASSED: Push-to-Talk state transitions verified.")


async def test_face_tracker_attention_telemetry_stream():
    """Verify Face Tracker telemetry emissions, attention classification, and boundary events."""
    print("\n--- [TEST] Face Tracker Attention Telemetry Stream ---")
    bus = EventBus()
    bus_task = asyncio.create_task(bus.process())
    face = FaceTrackerPlugin(bus=bus)

    telemetry_records: list[dict[str, Any]] = []
    face_detected_events = 0
    face_lost_events = 0

    async def on_telemetry(ev: Event):
        telemetry_records.append(ev.data)

    async def on_detected(ev: Event):
        nonlocal face_detected_events
        face_detected_events += 1

    async def on_lost(ev: Event):
        nonlocal face_lost_events
        face_lost_events += 1

    bus.on("face_telemetry", on_telemetry)
    bus.on("face_detected", on_detected)
    bus.on("face_lost", on_lost)

    await face.start({})

    # 1. Face Enters Frame: Centered gaze and head pose -> Attention=True
    face.set_mock_face_state(
        detected=True,
        gaze=[0.5, 0.5],
        pose={"yaw": 5.0, "pitch": -2.0, "roll": 0.0},
        blink=False,
    )
    await face.on_event(Event(type="camera_frame", data={}))
    await asyncio.sleep(0.01)

    assert face_detected_events == 1, "face_detected must be emitted when face first appears"
    assert len(telemetry_records) == 1
    t1 = telemetry_records[-1]
    assert t1["detected"] is True
    assert t1["attention"] is True
    assert t1["head_pose"]["yaw"] == 5.0
    assert t1["gaze"] == [0.5, 0.5]
    assert t1["blink"] is False

    # 2. Face Remains in Frame: Continuous stream, but no duplicate face_detected
    face.set_mock_face_state(
        detected=True,
        gaze=[0.45, 0.52],
        pose={"yaw": 6.0, "pitch": -1.0, "roll": 0.5},
    )
    await face.on_event(Event(type="camera_frame", data={}))
    await asyncio.sleep(0.01)

    assert face_detected_events == 1, "face_detected must not re-emit while face stays detected"
    assert len(telemetry_records) == 2

    # 3. User Looks Away (Distracted / Gaze Off-Screen): Gaze=[0.95, 0.5] -> Attention=False
    face.set_mock_face_state(
        detected=True,
        gaze=[0.95, 0.5],
        pose={"yaw": 0.0, "pitch": 0.0, "roll": 0.0},
    )
    await face.on_event(Event(type="vision_tick", data={}))
    await asyncio.sleep(0.01)
    t3 = telemetry_records[-1]
    assert t3["detected"] is True
    assert t3["attention"] is False, "Distracted gaze must yield attention=False"

    # 4. User Turns Head Away: Yaw=45.0 degrees -> Attention=False
    face.set_mock_face_state(
        detected=True,
        gaze=[0.5, 0.5],
        pose={"yaw": 45.0, "pitch": 0.0, "roll": 0.0},
    )
    await face.on_event(Event(type="vision_tick", data={}))
    await asyncio.sleep(0.01)
    t4 = telemetry_records[-1]
    assert t4["detected"] is True
    assert t4["attention"] is False, "Turned head pose must yield attention=False"

    # 5. Face Leaves Frame: Detected=False -> Emits face_lost
    face.set_mock_face_state(detected=False)
    await face.on_event(Event(type="camera_frame", data={}))
    await asyncio.sleep(0.01)

    assert face_lost_events == 1, "face_lost must be emitted when face disappears"
    t5 = telemetry_records[-1]
    assert t5["detected"] is False
    assert t5["attention"] is False

    # 6. Face Remains Gone: No duplicate face_lost
    await face.on_event(Event(type="camera_frame", data={}))
    await asyncio.sleep(0.01)
    assert face_lost_events == 1, "face_lost must not re-emit while face remains absent"

    await face.stop()
    bus_task.cancel()
    try:
        await bus_task
    except asyncio.CancelledError:
        pass
    print("  => PASSED: Face Tracker attention telemetry stream verified.")


async def test_concurrency_and_stress():
    """Verify concurrency safety, lifecycle stress, and error boundary isolation."""
    print("\n--- [TEST] Concurrency, Stress & Error Isolation ---")
    bus = EventBus()
    bus_task = asyncio.create_task(bus.process())
    config = Config(Path("/tmp/jarvis_challenger_cfg2"))
    pm = PluginManager(bus, config)

    # Register mock plugins alongside builtins
    whisper = WhisperLocalPlugin(bus=bus, config=config)
    ollama = OllamaLLMPlugin(bus=bus, config=config)
    piper = PiperTTSPlugin(bus=bus, config=config)
    ptt = PushToTalkPlugin(bus=bus, config=config)
    clap = ClapDetectorPlugin(bus=bus, config=config)
    face = FaceTrackerPlugin(bus=bus, config=config)

    for p in [whisper, ollama, piper, ptt, clap, face]:
        pm.register(p)
        await pm.activate(p.name)

    assert len(pm.get_active_plugins()) == 6

    # Launch 50 concurrent routing tasks generating mixed events
    async def stress_worker(worker_id: int):
        events = [
            Event(type="audio_chunk", data={"audio": [0.05] * 128}),
            Event(type="audio_energy", data={"energy": 0.2}),
            Event(type="camera_frame", data={}),
            Event(type="key_down", data={"key": "unrelated"}),
        ]
        for ev in events:
            resps = await pm.route_event(ev)
            assert isinstance(resps, list)
            await asyncio.sleep(0.002)

    workers = [asyncio.create_task(stress_worker(i)) for i in range(50)]
    await asyncio.gather(*workers)
    print("  50 concurrent event routing workers completed without exception.")

    # Test Stop All and Reactivation
    await pm.stop_all()
    assert len(pm.get_active_plugins()) == 0

    for name in ["whisper_local", "piper_tts", "ollama_llm"]:
        success = await pm.activate(name)
        assert success is True

    assert len(pm.get_active_plugins()) == 3
    await pm.stop_all()

    bus_task.cancel()
    try:
        await bus_task
    except asyncio.CancelledError:
        pass
    print("  => PASSED: Concurrency and lifecycle stress verified.")


async def main():
    print("=================================================================")
    print("  STARTING EMPIRICAL CHALLENGER VERIFICATION FOR MILESTONE 2")
    print("=================================================================")
    t0 = time.time()
    await test_end_to_end_voice_loop()
    await test_clap_detector_timing_and_noise_rejection()
    await test_push_to_talk_state_transitions()
    await test_face_tracker_attention_telemetry_stream()
    await test_concurrency_and_stress()
    elapsed = time.time() - t0
    print("\n=================================================================")
    print(f"  ALL 5 EMPIRICAL CHALLENGER TEST SUITES PASSED in {elapsed:.2f}s!")
    print("=================================================================")


if __name__ == "__main__":
    asyncio.run(main())
