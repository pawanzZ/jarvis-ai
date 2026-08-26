## 2026-08-26T19:57:47Z
You are the Worker for Milestone 2: Pluggable AI & Audio Pipeline (R2).
Your working directory is: /home/pawan/Projects/jarvis-ai/.agents/worker_m2
Original Request: /home/pawan/Projects/jarvis-ai/.agents/ORIGINAL_REQUEST.md
Master Project Spec: /home/pawan/Projects/jarvis-ai/.agents/PROJECT.md
Backend Survey Analysis: /home/pawan/Projects/jarvis-ai/.agents/explorer_survey_backend/analysis.md
Implementation Plan: /home/pawan/Projects/jarvis-ai/docs/superpowers/plans/2026-08-26-jarvis-ai-implementation.md (Phases 3, 4, 6, Tasks 8, 9, 10, 11, 12, 13, 17)

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your Tasks:
1. Read ORIGINAL_REQUEST.md, PROJECT.md, and the implementation plan tasks for Phases 3, 4, 6.
2. Implement production-grade modules with reliable offline/mock fallback logic so tests pass on any environment (with or without audio hardware/GPU/daemons):
   - `backend/jarvis/audio/__init__.py`
   - `backend/jarvis/audio/mic_stream.py`: `MicStream` supporting start, stop, read_chunk, is_recording, with sounddevice / simulation fallback.
   - `backend/jarvis/audio/speaker_output.py`: `SpeakerOutput` supporting play, stop, volume control, with sounddevice / simulation fallback.
   - `backend/jarvis/audio/vad.py`: `VAD` (Voice Activity Detector) detecting speech boundaries via energy / amplitude thresholding.
   - `backend/jarvis/plugins/builtins/__init__.py`
   - `backend/jarvis/plugins/builtins/whisper_local.py`: `WhisperLocalPlugin` (inherits `Plugin`, `type=PluginType.STT`), transcribes speech, emits `stt_result`, supports mock/faster-whisper/whisper.cpp engine.
   - `backend/jarvis/plugins/builtins/piper_tts.py`: `PiperTTSPlugin` (inherits `Plugin`, `type=PluginType.TTS`), listens to `tts_speak` and `llm_response`, synthesizes speech, emits `tts_start`, `tts_done`, `audio_level`.
   - `backend/jarvis/plugins/builtins/ollama_llm.py`: `OllamaLLMPlugin` (inherits `Plugin`, `type=PluginType.LLM`), listens to `stt_result` and `llm_request`, calls Ollama streaming endpoint (with offline conversational fallback), streams `llm_token`, and emits `llm_response`.
   - `backend/jarvis/plugins/builtins/push_to_talk.py`: `PushToTalkPlugin` (inherits `Plugin`, `type=PluginType.ACTIVATION`), detects PTT keydown/keyup, toggles listening state.
   - `backend/jarvis/plugins/builtins/clap_detector.py`: `ClapDetectorPlugin` (inherits `Plugin`, `type=PluginType.ACTIVATION`), detects double clap from audio frames within time window, transitions state to listening.
   - `backend/jarvis/plugins/builtins/face_tracker.py`: `FaceTrackerPlugin` (inherits `Plugin`, `type=PluginType.VISION`), detects face presence and head pose, emits `face_telemetry`, `face_detected`, `face_lost`.
3. Implement comprehensive test suites in `backend/tests/`:
   - `backend/tests/test_audio.py`
   - `backend/tests/test_whisper.py`
   - `backend/tests/test_piper.py`
   - `backend/tests/test_ollama.py`
   - `backend/tests/test_ptt.py`
   - `backend/tests/test_clap.py`
   - `backend/tests/test_face.py`
4. Run all backend tests: `cd backend && python3 -m pytest tests/ -v`. Ensure 100% test pass rate across all test suites (including Milestone 1 tests).
5. Write your changes log to `/home/pawan/Projects/jarvis-ai/.agents/worker_m2/changes.md` and complete handoff report to `/home/pawan/Projects/jarvis-ai/.agents/worker_m2/handoff.md`.
6. Send a message to parent when complete.
