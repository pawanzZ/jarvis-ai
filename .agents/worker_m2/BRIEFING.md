# BRIEFING — 2026-08-27T01:32:00Z

## Mission
Implement Milestone 2: Pluggable AI & Audio Pipeline (R2) including audio I/O, VAD, STT (Whisper), TTS (Piper), LLM (Ollama), PTT, Clap detection, Face tracking, and full test suites with 100% pass rate.

## 🔒 My Identity
- Archetype: worker
- Roles: implementer, qa, specialist
- Working directory: /home/pawan/Projects/jarvis-ai/.agents/worker_m2
- Original parent: f1eeec08-7834-44ca-82e1-a3b3f0402e8a
- Milestone: Milestone 2 (R2 Pluggable AI & Audio Pipeline)

## 🔒 Key Constraints
- Production-grade modular code with reliable mock/offline fallbacks.
- Pass all unit and integration tests under pytest with 100% pass rate without requiring physical audio hardware, GPU, or active Ollama server.
- Follow EventBus and Plugin contracts defined in Milestone 1.
- No dummy/facade implementations, genuine stateful logic and mathematical signal/event processing.

## Current Parent
- Conversation ID: f1eeec08-7834-44ca-82e1-a3b3f0402e8a
- Updated: 2026-08-27T01:32:00Z

## Task Summary
- **What to build**: Audio pipeline (`MicStream`, `SpeakerOutput`, `VAD`) and Builtin Plugins (`WhisperLocalPlugin`, `PiperTTSPlugin`, `OllamaLLMPlugin`, `PushToTalkPlugin`, `ClapDetectorPlugin`, `FaceTrackerPlugin`) with full test coverage.
- **Success criteria**: All modules functional, comprehensive test suite in `backend/tests/`, 100% test pass rate across all tests.
- **Interface contracts**: `/home/pawan/Projects/jarvis-ai/.agents/PROJECT.md`
- **Code layout**: `backend/jarvis/audio/`, `backend/jarvis/plugins/builtins/`, `backend/tests/`

## Change Tracker
- **Files modified**:
  - `backend/jarvis/audio/vad.py`: VAD with RMS energy calculation and frame state machine
  - `backend/jarvis/audio/mic_stream.py`: MicStream with hardware/simulation capture
  - `backend/jarvis/audio/speaker_output.py`: SpeakerOutput with volume attenuation & playback
  - `backend/jarvis/audio/__init__.py`: Export audio modules
  - `backend/jarvis/plugins/builtins/whisper_local.py`: Whisper STT plugin
  - `backend/jarvis/plugins/builtins/piper_tts.py`: Piper TTS plugin
  - `backend/jarvis/plugins/builtins/ollama_llm.py`: Ollama LLM plugin with offline fallback
  - `backend/jarvis/plugins/builtins/push_to_talk.py`: PushToTalk activation plugin
  - `backend/jarvis/plugins/builtins/clap_detector.py`: Double clap detector plugin
  - `backend/jarvis/plugins/builtins/face_tracker.py`: Face tracker vision plugin
  - `backend/jarvis/plugins/builtins/__init__.py`: Export builtin plugins
  - `backend/tests/test_audio.py`: Audio & VAD test suite
  - `backend/tests/test_whisper.py`: Whisper STT test suite
  - `backend/tests/test_piper.py`: Piper TTS test suite
  - `backend/tests/test_ollama.py`: Ollama LLM test suite
  - `backend/tests/test_ptt.py`: PushToTalk test suite
  - `backend/tests/test_clap.py`: Clap detector test suite
  - `backend/tests/test_face.py`: Face tracker test suite
  - `backend/tests/adversarial/test_adv_audio.py`: Adversarial audio tests
  - `backend/tests/adversarial/test_adv_plugins_builtins.py`: Adversarial plugin tests
- **Build status**: 127/127 tests passing (100% pass rate)
- **Pending issues**: None

## Quality Status
- **Build/test result**: PASS (127 passed in 5.97s)
- **Lint status**: Clean (compileall passed 0 errors)
- **Tests added/modified**: 15 test files (59 new tests added for Milestone 2)

## Loaded Skills
- None
