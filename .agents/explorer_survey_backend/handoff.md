# Handoff Report — Backend Architecture & Survey

**Agent:** Backend & Architecture Explorer (`explorer_survey_backend`)  
**Parent / Recipient:** Project Orchestrator (`f1eeec08-7834-44ca-82e1-a3b3f0402e8a`)  
**Date:** 2026-08-26 / 2026-08-27  
**Artifact:** `/home/pawan/Projects/jarvis-ai/.agents/explorer_survey_backend/analysis.md`

---

## 1. Observation

1. **Specification & Plan Documents:**
   - `docs/superpowers/specs/2026-08-26-jarvis-ai-design.md`:
     - System architecture: Python backend ↔ Electron frontend via WebSocket on `ws://localhost:8765`.
     - 5 states: `IDLE`, `LISTENING`, `THINKING`, `SPEAKING`, `ERROR`.
     - Pluggable components: STT (Whisper), TTS (Piper), LLM (Ollama), Activation (PTT, Clap, Wake Word), Vision (MediaPipe Face Mesh).
   - `docs/superpowers/plans/2026-08-26-jarvis-ai-implementation.md`:
     - Phase 1 (Tasks 1, 3, 4) targets backend scaffolding and WebSocket server.
     - Phase 2 (Tasks 6, 7) targets Plugin interface, Manager, and Config enhancement.
     - Phase 3 (Tasks 8, 9, 10, 11) targets Audio pipeline, Whisper STT, Piper TTS, Ollama LLM.
     - Phase 4 (Tasks 12, 13) targets Push-to-Talk and Clap Detector plugins.
     - Phase 6 (Task 17) targets MediaPipe Face Tracker plugin.

2. **Existing Workspace State (`/home/pawan/Projects/jarvis-ai`):**
   - Backend files present:
     - `backend/pyproject.toml` (lines 1-20): Dependencies defined (`websockets>=12.0`, `pydantic>=2.0`, `pytest>=8.0`).
     - `backend/jarvis/core/bus.py` (lines 1-40): `Event` dataclass and `EventBus` class implemented.
     - `backend/jarvis/core/state.py` (lines 1-43): `JarvisState` enum, `TRANSITIONS` dictionary, `StateMachine` class implemented.
     - `backend/jarvis/core/config.py` (lines 1-38): `Config` class with `get`, `set`, `_load`, `_save` implemented.
     - `backend/jarvis/ws_server.py` (lines 1-72): `WSServer` with `start`, `_handle`, `_on_message`, `broadcast` implemented.
     - `backend/jarvis/__main__.py` (lines 1-26): Entry point wiring `bus`, `state`, `config`, `server`.
     - Tests present: `backend/tests/test_bus.py`, `backend/tests/test_state.py`, `backend/tests/test_ws_server.py`.
   - Backend files missing:
     - `backend/jarvis/plugins/base.py` & `backend/jarvis/plugins/manager.py`.
     - `backend/jarvis/audio/mic_stream.py`, `backend/jarvis/audio/speaker_output.py`, `backend/jarvis/audio/vad.py`.
     - Builtin plugins: `whisper_local.py`, `piper_tts.py`, `ollama_llm.py`, `push_to_talk.py`, `clap_detector.py`, `face_tracker.py`.
     - Config helper extensions (`list_namespaces`, `get_all`).
     - Corresponding plugin and audio unit tests.

---

## 2. Logic Chain

1. **Architecture Decoupling:**
   - The system is structured around an event-driven core where the `EventBus` provides loose coupling between plugins and the core state machine.
   - The `StateMachine` acts as the single source of truth for conversational state (`idle` -> `listening` -> `thinking` -> `speaking` -> `idle`), preventing race conditions between concurrent input sources (PTT, Clap, STT, LLM).
2. **WebSocket Gateway as Bridge:**
   - The `WSServer` on `localhost:8765` exposes state transitions, streaming tokens, transcripts, and telemetry (audio levels, face tracking) to the Electron HUD.
   - It also receives commands (`activate`, `deactivate`, `config_update`, `settings_request`) from the frontend and pushes them to the `EventBus`.
3. **Plugin Extensibility:**
   - Every AI/ML capability inherits from `Plugin` with a uniform lifecycle (`start`, `stop`, `on_event`, `get_schema`).
   - `PluginManager` discovers and dynamically loads plugins from `backend/jarvis/plugins/builtins/`, allowing zero-downtime additions and schema-driven settings generation.
4. **Execution Flow Requirement:**
   - Because `EventBus.emit()` puts events into an `asyncio.Queue`, `backend/jarvis/__main__.py` must run `bus.process()` as a background task alongside `server.start()` so that queued events are dispatched to listeners.

---

## 3. Caveats

1. **Hardware / Daemon Independence:**
   - Local ML models (Ollama, Whisper.cpp, Piper, MediaPipe) depend on runtime environments that may not have GPUs, webcams, or running Ollama daemons during testing.
   - All plugins must implement robust fallback / mock modes so unit tests and headless executions pass deterministically.
2. **Configuration File Format:**
   - While the prompt mentions YAML/JSON, the specification and current code use JSON (`config/{namespace}.json`). Both formats represent equivalent key-value trees; adhering to the existing JSON implementation in `backend/jarvis/core/config.py` preserves full compatibility.

---

## 4. Conclusion

The core backend skeleton (Phase 1) is already established with working event bus, state machine, basic config loader, and WebSocket server. The next development milestones require implementing:
1. **Plugin Core:** `base.py` and `manager.py` (Phase 2).
2. **Voice & Audio Pipeline:** `mic_stream.py`, `speaker_output.py`, `vad.py`, `whisper_local.py`, `piper_tts.py`, `ollama_llm.py` (Phase 3).
3. **Activation Plugins:** `push_to_talk.py`, `clap_detector.py` (Phase 4).
4. **Vision Plugin:** `face_tracker.py` (Phase 6).
5. **Event Loop Wiring:** Background `bus.process()` dispatch in `__main__.py`.

All specifications, event payload definitions, schemas, and file contracts are fully documented in `/home/pawan/Projects/jarvis-ai/.agents/explorer_survey_backend/analysis.md`.

---

## 5. Verification Method

To independently verify backend functionality and tests:

1. **Inspect Analysis Report:**
   ```bash
   view_file /home/pawan/Projects/jarvis-ai/.agents/explorer_survey_backend/analysis.md
   ```
2. **Inspect Existing Core Modules:**
   ```bash
   view_file /home/pawan/Projects/jarvis-ai/backend/jarvis/core/bus.py
   view_file /home/pawan/Projects/jarvis-ai/backend/jarvis/core/state.py
   view_file /home/pawan/Projects/jarvis-ai/backend/jarvis/core/config.py
   view_file /home/pawan/Projects/jarvis-ai/backend/jarvis/ws_server.py
   ```
3. **Run Unit Tests (when executing backend tasks):**
   ```bash
   cd /home/pawan/Projects/jarvis-ai/backend && python3 -m pytest tests/ -v
   ```
