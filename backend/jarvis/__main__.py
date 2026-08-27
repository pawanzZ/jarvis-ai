from __future__ import annotations
import asyncio
import time
from pathlib import Path
from jarvis.core.bus import EventBus, Event
from jarvis.core.state import StateMachine, JarvisState
from jarvis.core.config import Config
from jarvis.ws_server import WSServer
from jarvis.plugins.manager import PluginManager
from jarvis.plugins.base import PluginType
from jarvis.audio.mic_stream import MicStream
from jarvis.audio.vad import VAD
from jarvis.audio.speaker_output import SpeakerOutput
from jarvis.system.monitor import SystemMonitor


async def main() -> None:
    base_dir = Path(__file__).parent.parent.parent
    bus = EventBus()
    state = StateMachine()
    config = Config(base_dir)
    system_monitor = SystemMonitor()
    server = WSServer(bus, state, config=config, system_monitor=system_monitor)
    plugin_mgr = PluginManager(bus, config)

    # 1. Discover and activate built-in plugins
    builtins_dir = Path(__file__).parent / "plugins" / "builtins"
    if builtins_dir.exists():
        discovered = plugin_mgr.discover(builtins_dir)
        print(f"[Jarvis] Discovered plugins: {discovered}")
        for name in ["whisper_local", "ollama_llm", "piper_tts", "push_to_talk", "clap_detector", "face_tracker"]:
            if name in discovered:
                try:
                    await plugin_mgr.activate(name)
                    print(f"[Jarvis] Activated plugin: {name}")
                except Exception as e:
                    print(f"[Jarvis] Warning: Failed to activate {name}: {e}")

    # 2. Audio Subsystems & Hardware Gain Calibration
    try:
        import subprocess
        # Prevent rail-to-rail clipping on Realtek ALC257 if internal mic boost was set to +30dB
        subprocess.run(["amixer", "-c", "1", "set", "Internal Mic Boost", "0"], capture_output=True, timeout=1.0)
        subprocess.run(["amixer", "-c", "1", "set", "Capture", "45"], capture_output=True, timeout=1.0)
    except Exception:
        pass

    mic = MicStream(sample_rate=16000, chunk_size=1024, simulate=False)
    vad = VAD(threshold=0.015, sample_rate=16000, hangover_frames=8, min_speech_frames=2)
    speaker = SpeakerOutput(sample_rate=22050, simulate=False)

    # 3. Broadcast state transitions to HUD clients
    async def broadcast_state(old: JarvisState, new: JarvisState) -> None:
        print(f"[Jarvis] State: {old.value} -> {new.value}")
        await server.broadcast({
            "type": "state_change",
            "state": new.value,
            "data": {"state": new.value, "previous": old.value},
        })

    state.on_change(broadcast_state)

    # Audio State & Speech Buffers
    speech_buffer: list[float] = []
    speech_frames = 0
    silence_frames = 0
    ambient_energy = 0.009
    is_processing_turn = False
    barge_in = asyncio.Event()
    last_voice_time = time.monotonic()
    LISTEN_IDLE_TIMEOUT = 10.0  # drop from LISTENING back to IDLE after this much silence

    def _is_sentence_boundary(text: str) -> bool:
        return any(ch in text for ch in ".!?\n")

    async def handle_speech_turn(audio_samples: list[float]) -> None:
        nonlocal is_processing_turn, last_voice_time
        if is_processing_turn:
            return
        is_processing_turn = True

        try:
            print(f"[Jarvis] Transcribing {len(audio_samples)} audio samples (~{len(audio_samples)/16000:.2f}s)...")
            # 1. Speech-to-Text with Whisper
            stt = plugin_mgr.get_active(PluginType.STT)
            transcript = ""
            if stt and hasattr(stt, "transcribe"):
                transcript = stt.transcribe(audio_samples)
            elif stt:
                ev = await stt.on_event(Event(type="transcribe", data={"audio": audio_samples}))
                if ev:
                    transcript = ev.data.get("text", "")

            transcript = (transcript or "").strip()
            if not transcript:
                print("[Jarvis] No intelligible speech detected.")
                await server.broadcast({
                    "type": "transcript_final",
                    "data": {"speaker": "user", "text": "(Inaudible)"},
                    "text": "(Inaudible)",
                })
                if state.state != JarvisState.LISTENING:
                    await state.transition(JarvisState.LISTENING)
                return

            print(f"[Jarvis] Recognized: '{transcript}'")
            await server.broadcast({
                "type": "transcript_final",
                "data": {"speaker": "user", "text": transcript},
                "speaker": "user",
                "text": transcript,
            })

            # 2. Stream LLM tokens while enqueueing spoken sentences in sync
            tts = plugin_mgr.get_active(PluginType.TTS)
            llm = plugin_mgr.get_active(PluginType.LLM)
            barge_in.clear()
            full_response = ""
            pending = ""

            if llm and hasattr(llm, "generate_stream"):
                async for token in llm.generate_stream(transcript):
                    if barge_in.is_set():
                        break
                    full_response += token
                    pending += token
                    await server.broadcast({
                        "type": "llm_token",
                        "data": {"token": token},
                        "token": token,
                    })
                    # Speak as soon as a sentence is complete so audio tracks the transcript
                    if tts and _is_sentence_boundary(pending):
                        flush = pending.strip()
                        pending = ""
                        await tts.on_event(Event(type="tts_enqueue", data={"text": flush}))
            elif llm:
                ev = await llm.on_event(Event(type="llm_request", data={"prompt": transcript}))
                if ev:
                    full_response = ev.data.get("full_text") or ev.data.get("text", "")
            else:
                full_response = f"Subsystems nominal, sir. Acknowledged: {transcript}"

            full_response = (full_response or "").strip()

            # Move to SPEAKING once there is content to verbalize
            if full_response and state.state in (JarvisState.THINKING, JarvisState.LISTENING):
                await state.transition(JarvisState.SPEAKING)

            if barge_in.is_set():
                pending = ""

            # Flush any trailing (unpunctuated) text so it is still spoken
            if tts and pending.strip() and not barge_in.is_set():
                await tts.on_event(Event(type="tts_enqueue", data={"text": pending.strip()}))
            elif tts and full_response and not hasattr(llm, "generate_stream"):
                # Non-streaming path: speak the full response once
                await tts.on_event(Event(type="tts_enqueue", data={"text": full_response}))

            await server.broadcast({
                "type": "response_complete",
                "data": {"full_text": full_response},
                "full_text": full_response,
            })

            # 3. Wait for speech to finish; barge-in interrupts and returns early
            if tts:
                while getattr(tts, "_speaking", False) and not barge_in.is_set():
                    await asyncio.sleep(0.1)

            # 4. Voice detection HOLD: return to LISTENING for the next turn
            await asyncio.sleep(0.3)
            last_voice_time = time.monotonic()
            if barge_in.is_set():
                barge_in.clear()
            if state.state != JarvisState.LISTENING:
                await state.transition(JarvisState.LISTENING)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"[Jarvis] Speech processing error: {e}")
            await server.broadcast({"type": "error", "data": {"message": str(e)}, "message": str(e)})
            if state.state != JarvisState.IDLE:
                await state.transition(JarvisState.IDLE)
        finally:
            is_processing_turn = False

    # 4. Background Audio Worker Loop
    async def audio_worker() -> None:
        nonlocal speech_buffer, speech_frames, silence_frames, ambient_energy, is_processing_turn, last_voice_time
        clap = plugin_mgr.get_plugin("clap_detector")
        idle_voiced_run = 0
        barge_run = 0
        await mic.start()
        print("[Jarvis] Microphone stream online and listening...")

        while True:
            try:
                chunk = await mic.read_chunk(timeout=0.15)
                if not chunk:
                    continue

                # Audio level calculation for HUD visualizer
                energy = vad.calculate_energy(chunk)
                level = min(1.0, energy * 25.0)

                # Send real-time audio levels to HUD
                await server.broadcast({
                    "type": "audio_level",
                    "data": {"level": level, "source": "mic"},
                    "level": level,
                })

                await bus.emit(Event(type="audio_energy", data={"energy": energy}, source="mic"))

                # Adaptively track ambient noise floor
                ambient_energy = 0.96 * ambient_energy + 0.04 * energy

                current_state = state.state

                # Mode 1: IDLE - activation (double-clap + confirmed single-sound trigger)
                if current_state == JarvisState.IDLE:
                    if not is_processing_turn:
                        clap_fired = False
                        # Wire the real double-clap detector into the live pipeline
                        if clap is not None and getattr(clap, "_running", False):
                            try:
                                resp = await clap.on_event(Event(type="audio_energy", data={"energy": energy}))
                                clap_fired = resp is not None
                            except Exception:
                                pass

                        # Confirmed single-sound fallback: requires consecutive loud frames,
                        # with a higher floor and wider margin so ordinary noise can't trip it.
                        speech_threshold = max(0.07, ambient_energy * 3.5)
                        if energy > speech_threshold:
                            idle_voiced_run += 1
                        else:
                            idle_voiced_run = 0
                        if idle_voiced_run >= 2 and not clap_fired:
                            print(f"[Jarvis] Loud activation ({energy:.4f} > {speech_threshold:.4f}) -> activating to LISTENING")
                            await state.transition(JarvisState.LISTENING)
                            speech_buffer = list(chunk)
                            speech_frames = 1
                            silence_frames = 0
                            last_voice_time = time.monotonic()
                            idle_voiced_run = 0
                            continue

                # Mode 2: LISTENING - Accumulate speech turn
                elif current_state == JarvisState.LISTENING:
                    is_voiced = energy > max(0.02, ambient_energy * 2.0)

                    if is_voiced:
                        last_voice_time = time.monotonic()
                        speech_buffer.extend(chunk)
                        speech_frames += 1
                        silence_frames = 0
                        if speech_frames % 5 == 0:
                            await server.broadcast({
                                "type": "transcript_partial",
                                "data": {"text": "Listening..."},
                                "text": "Listening...",
                            })
                    else:
                        # Non-voiced chunk
                        if speech_frames >= 2:  # User has started speaking
                            speech_buffer.extend(chunk)
                            silence_frames += 1

                            # ~0.5s of silence after speech -> finish turn!
                            if silence_frames >= 8 and not is_processing_turn:
                                print(f"[Jarvis] Speech pause detected ({len(speech_buffer)} samples). Transitioning to THINKING...")
                                await state.transition(JarvisState.THINKING)
                                audio_copy = list(speech_buffer)
                                speech_buffer.clear()
                                speech_frames = 0
                                silence_frames = 0
                                asyncio.create_task(handle_speech_turn(audio_copy))
                        else:
                            # Pre-buffer: Keep rolling window so utterance start isn't clipped
                            if len(speech_buffer) > 2048:
                                speech_buffer = speech_buffer[-2048:]
                            else:
                                speech_buffer.extend(chunk)

                    # Safety duration limit (8 seconds max speech per utterance)
                    if len(speech_buffer) >= 16000 * 8 and not is_processing_turn:
                        print(f"[Jarvis] Max turn duration reached ({len(speech_buffer)} samples). Transitioning to THINKING...")
                        await state.transition(JarvisState.THINKING)
                        audio_copy = list(speech_buffer)
                        speech_buffer.clear()
                        speech_frames = 0
                        silence_frames = 0
                        asyncio.create_task(handle_speech_turn(audio_copy))

                    # Idle timeout: drop to IDLE after sustained silence in listen mode
                    if (
                        speech_frames == 0
                        and not is_processing_turn
                        and (time.monotonic() - last_voice_time) > LISTEN_IDLE_TIMEOUT
                    ):
                        print("[Jarvis] No voice for a while -> dropping from LISTENING to IDLE")
                        speech_buffer.clear()
                        speech_frames = 0
                        silence_frames = 0
                        await state.transition(JarvisState.IDLE)

                # Mode 3: THINKING - barge-in allowed (mic is clean while Jarvis reasons).
                # SPEAKING deliberately has NO open-mic barge-in: on speakers Jarvis would
                # otherwise hear its own voice and interrupt itself (abrupt stop/start loop).
                elif current_state == JarvisState.THINKING:
                    barge_floor = 0.08
                    burst = energy > max(barge_floor, ambient_energy * 4.5)
                    barge_run = barge_run + 1 if burst else 0
                    if barge_run >= 2 and not is_processing_turn:
                        print(f"[Jarvis] Barge-in ({energy:.4f}) during thinking -> interrupting and listening")
                        tts = plugin_mgr.get_active(PluginType.TTS)
                        if tts:
                            await tts.on_event(Event(type="tts_interrupt"))
                        speaker.stop()
                        barge_in.set()
                        speech_buffer.clear()
                        speech_frames = 0
                        silence_frames = 0
                        last_voice_time = time.monotonic()
                        barge_run = 0
                        if state.state != JarvisState.LISTENING:
                            await state.transition(JarvisState.LISTENING)

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[Jarvis] Error in audio worker: {e}")
                await asyncio.sleep(0.1)

    # 5. Core Event Handlers
    async def handle_activate(event: Event) -> None:
        nonlocal speech_buffer, speech_frames, silence_frames, is_processing_turn, last_voice_time
        tts = plugin_mgr.get_active(PluginType.TTS)
        if tts:
            await tts.on_event(Event(type="tts_stop"))
        speaker.stop()
        barge_in.set()
        speech_buffer.clear()
        speech_frames = 0
        silence_frames = 0
        is_processing_turn = False
        last_voice_time = time.monotonic()
        if state.state != JarvisState.LISTENING:
            await state.transition(JarvisState.LISTENING)

    async def handle_deactivate(event: Event) -> None:
        nonlocal speech_buffer, speech_frames, silence_frames, last_voice_time
        tts = plugin_mgr.get_active(PluginType.TTS)
        if tts:
            await tts.on_event(Event(type="tts_stop"))
        speaker.stop()
        barge_in.clear()

        # If user spoke and then deactivated (e.g. released PTT or clicked stop), process what was spoken!
        if len(speech_buffer) >= 3200 and not is_processing_turn:
            print(f"[Jarvis] Deactivate with {len(speech_buffer)} samples -> processing utterance!")
            await state.transition(JarvisState.THINKING)
            audio_copy = list(speech_buffer)
            speech_buffer.clear()
            speech_frames = 0
            silence_frames = 0
            asyncio.create_task(handle_speech_turn(audio_copy))
            return

        speech_buffer.clear()
        speech_frames = 0
        silence_frames = 0
        last_voice_time = time.monotonic()
        if state.state != JarvisState.IDLE:
            await state.transition(JarvisState.IDLE)

    bus.on("activate", handle_activate)
    bus.on("deactivate", handle_deactivate)

    # 6. Telemetry & Weather Broadcast Workers
    async def telemetry_worker() -> None:
        while True:
            try:
                snapshot = system_monitor.get_telemetry_snapshot()
                await server.broadcast({
                    "type": "system_telemetry",
                    "data": snapshot,
                })
                await asyncio.sleep(1.0)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[Jarvis] Telemetry worker error: {e}")
                await asyncio.sleep(2.0)

    async def weather_worker() -> None:
        while True:
            try:
                weather = await system_monitor.fetch_weather_and_location()
                await server.broadcast({
                    "type": "weather_telemetry",
                    "data": weather,
                })
                # Refresh every 10 minutes
                await asyncio.sleep(600)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[Jarvis] Weather worker error: {e}")
                await asyncio.sleep(60)

    print("Jarvis backend starting...")

    # Spawn background tasks
    bus_task = asyncio.create_task(bus.process())
    audio_task = asyncio.create_task(audio_worker())
    telemetry_task = asyncio.create_task(telemetry_worker())
    weather_task = asyncio.create_task(weather_worker())

    try:
        await server.start()
    finally:
        bus_task.cancel()
        audio_task.cancel()
        telemetry_task.cancel()
        weather_task.cancel()
        await mic.stop()
        speaker.stop()
        await plugin_mgr.stop_all()


if __name__ == "__main__":
    asyncio.run(main())
