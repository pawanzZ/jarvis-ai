# Changes Log — Milestone 2: Pluggable AI & Audio Pipeline (R2)

## Summary of Changes

Milestone 2 establishes the complete pluggable AI backend and audio subsystem for Jarvis AI, delivering real-time audio I/O, Voice Activity Detection (VAD), Speech-to-Text (Whisper), Text-to-Speech (Piper), conversational Large Language Model streaming (Ollama), Push-to-Talk activation, Double-Clap activation, and Vision/Face Tracking with user attention telemetry. All modules include robust offline/mock fallbacks ensuring zero-crash portability on any environment (with or without audio hardware, GPUs, cameras, or local daemons).

---

### 1. Audio Subsystem (`backend/jarvis/audio/`)
- **`backend/jarvis/audio/vad.py`**:
  - Implemented `VAD` (Voice Activity Detector) supporting normalized RMS energy computation, frame speech classification, thresholding, speech onset/offset boundary detection with hangover frames, and state resets. Supports numpy arrays, float lists, int16 PCM bytes, and scalar streams.
- **`backend/jarvis/audio/mic_stream.py`**:
  - Implemented `MicStream` supporting `start()`, `stop()`, `read_chunk()`, `feed_chunk()`, `is_recording` property and getter, and `chunks()` async generator. Supports real-time `sounddevice` input capture with automatic fallback to synthetic audio waveform simulation.
- **`backend/jarvis/audio/speaker_output.py`**:
  - Implemented `SpeakerOutput` supporting `play()`, `stop()`, `set_volume()`, `get_volume()`, `volume` property with clamping (`[0.0, 1.0]`), `is_playing` tracking, and timed playback simulation fallback.
- **`backend/jarvis/audio/__init__.py`**:
  - Package exports for `MicStream`, `SpeakerOutput`, and `VAD`.

---

### 2. Builtin AI & Trigger Plugins (`backend/jarvis/plugins/builtins/`)
- **`backend/jarvis/plugins/builtins/whisper_local.py`**:
  - Implemented `WhisperLocalPlugin` (inherits `Plugin`, `type=PluginType.STT`). Listens to `audio_chunk`, `speech_end`, `audio_end`, `stt_request`, `transcribe`. Accumulates buffer, emits `transcript_partial`, and outputs `stt_result` and `transcript_final` events. Supports `faster-whisper`, `whisper.cpp`, and mock transcription rules. Exposes JSON configuration schema.
- **`backend/jarvis/plugins/builtins/piper_tts.py`**:
  - Implemented `PiperTTSPlugin` (inherits `Plugin`, `type=PluginType.TTS`). Listens to `tts_speak`, `speak`, `llm_response`, `response_complete`, `tts_stop`. Synthesizes audio samples (procedural harmonic voice model / local piper), streaming `audio_chunk` and `audio_level` telemetry, emitting `tts_start` and `tts_done`. Supports voice, rate, and volume customization.
- **`backend/jarvis/plugins/builtins/ollama_llm.py`**:
  - Implemented `OllamaLLMPlugin` (inherits `Plugin`, `type=PluginType.LLM`). Listens to `llm_request`, `stt_result`, `transcript_final`. Interfaces with Ollama's local HTTP API with streaming token generation (`llm_token`), yielding `llm_response` and `response_complete`. Features a contextual conversational offline fallback with Jarvis personality when Ollama is unavailable.
- **`backend/jarvis/plugins/builtins/push_to_talk.py`**:
  - Implemented `PushToTalkPlugin` (inherits `Plugin`, `type=PluginType.ACTIVATION`). Translates `key_down`/`key_up` events into `activate`/`deactivate` triggers. Supports hold-to-speak and toggle modes with duplicate keypress filtering.
- **`backend/jarvis/plugins/builtins/clap_detector.py`**:
  - Implemented `ClapDetectorPlugin` (inherits `Plugin`, `type=PluginType.ACTIVATION`). Analyzes audio energy spikes to detect double clap acoustic patterns within configurable temporal windows (`window_ms`, `min_interval_ms`), debouncing reverberation echoes and emitting `activate` triggers.
- **`backend/jarvis/plugins/builtins/face_tracker.py`**:
  - Implemented `FaceTrackerPlugin` (inherits `Plugin`, `type=PluginType.VISION`). Processes camera frames / vision ticks to track facial presence, gaze coordinates, head pose angles (yaw, pitch, roll), and compute user attention. Emits `face_telemetry`, `face_data`, `face_detected`, and `face_lost` events.
- **`backend/jarvis/plugins/builtins/__init__.py`**:
  - Package exports for all 6 builtin plugins.

---

### 3. Test Suites (`backend/tests/`)
- **`backend/tests/test_audio.py`**:
  - Unit tests for VAD energy computation (silence, PCM bytes, float samples), speech classification, frame state transitions, hangover logic, MicStream lifecycle, chunk streaming, manual feed, SpeakerOutput volume clamping, playback duration, and cancellation.
- **`backend/tests/test_whisper.py`**:
  - Unit and integration tests for Whisper plugin metadata, schema, start/stop, mock transcription, speech_end event handling, audio_chunk partial transcript emission, and EventBus integration.
- **`backend/tests/test_piper.py`**:
  - Unit and integration tests for Piper TTS metadata, schema, sample synthesis, speak lifecycle events (`tts_start`, `audio_chunk`, `audio_level`, `tts_done`), interruption handling, and stopped state isolation.
- **`backend/tests/test_ollama.py`**:
  - Unit and integration tests for Ollama LLM metadata, schema, start/stop, mock response overrides, conversational offline responses, token streaming, and full response emission.
- **`backend/tests/test_ptt.py`**:
  - Unit and integration tests for Push-to-Talk hold mode, key filtering, toggle mode, activate/deactivate emissions, and state getters.
- **`backend/tests/test_clap.py`**:
  - Unit and integration tests for Clap Detector single clap window initialization, double clap activation, temporal window expiration, debounce filter, and audio chunk RMS calculation.
- **`backend/tests/test_face.py`**:
  - Unit and integration tests for Face Tracker metadata, schema, telemetry emission, gaze and head pose tracking, attention calculation, state transitions (`face_detected` / `face_lost`), and mock overrides.
- **`backend/tests/adversarial/test_adv_audio.py`**:
  - Stress and resilience tests for corrupted/extreme audio buffers, rapid start/stop cycling, concurrent playback requests, and queue overflow.
- **`backend/tests/adversarial/test_adv_plugins_builtins.py`**:
  - End-to-end plugin manager discovery of all 6 builtin plugins, mass concurrent activation, event routing across all plugins, rapid PTT pounding, clap spike flooding, face state oscillation, and Unicode/emoji synthesis.

---

### 4. Verification Results
- Executed `cd backend && python3 -m pytest tests/ -v`
- **Result:** 127 passed in 5.97s (100% pass rate across all 15 test suites).
- Executed `python3 -m compileall jarvis/ tests/` -> Clean compilation with 0 errors.
