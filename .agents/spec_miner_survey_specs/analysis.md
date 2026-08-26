# Tooling & Verification Specification Mining Report

**Project:** Jarvis AI — Voice-Interactive Desktop AI Assistant  
**Author:** Tooling & Verification Spec Miner  
**Date:** 2026-08-26 (UTC) / 2026-08-27 (Local)  
**Spec Sources:**
- `ORIGINAL_REQUEST.md`
- `docs/superpowers/specs/2026-08-26-jarvis-ai-design.md` (Architectural Design Spec)
- `docs/superpowers/plans/2026-08-26-jarvis-ai-implementation.md` (Implementation Roadmap, Tasks 1–20)
- Existing workspace code & configuration (`backend/`, `frontend/`, `docs/`)

---

## 1. Executive Summary & Tooling Overview (Requirement R4)

Jarvis AI is architected as a hybrid desktop system:
- **Backend**: Python (>= 3.11) managing asyncio event loop, state machine, configuration persistence, audio I/O, AI plugins (STT Whisper, TTS Piper, LLM Ollama, Activation triggers, Face tracking), and an asynchronous WebSocket server on `ws://localhost:8765`.
- **Frontend**: Electron (>= 30.0.0) + TypeScript (>= 5.4.0) rendering an Iron Man-inspired full-screen HUD, multi-ring SVG/Canvas ARC reactor, audio waveform visualizer, particle engine, settings sliding panel, and synthesized Web Audio sound effects.
- **Automation & Tooling (R4)**: End-to-end setup automation (`scripts/setup.sh`), concurrent dev runner with trap cleanup (`scripts/dev.sh`), configuration system supporting both JSON namespaces and YAML defaults, comprehensive `README.md`, and strict verification gates across backend unit tests and frontend type checking/builds.

---

## 2. Tooling, Automation & Environment Specification

### 2.1 Developer Setup Script (`scripts/setup.sh`)
- **File Path**: `/home/pawan/Projects/jarvis-ai/scripts/setup.sh`
- **Permissions**: Executable (`chmod +x scripts/setup.sh`, `0755`)
- **Interpreter**: `#!/bin/bash`
- **Options**: `set -e` (fail fast on non-zero exit)
- **Execution Workflow**:
  1. Print startup banner: `"Setting up Jarvis AI..."`
  2. Setup Python environment:
     ```bash
     cd backend
     python3 -m venv .venv
     source .venv/bin/activate
     pip install --upgrade pip
     pip install -e ".[dev]"
     ```
  3. Setup Node/Electron environment:
     ```bash
     cd ../frontend
     npm install
     ```
  4. Ensure configuration directory existence (`config/`).
  5. Completion notice: `"Setup complete! Run ./scripts/dev.sh to start."`
- **Prerequisite Checks & External Tool Notes**:
  - Python >= 3.11 available
  - Node >= 20 and npm available
  - Local AI engine note: Ollama daemon (`ollama serve` and `ollama pull llama3`)
  - Audio dependencies: ALSA/PulseAudio/PipeWire development headers if compiling audio bindings.

### 2.2 Development Orchestration Script (`scripts/dev.sh`)
- **File Path**: `/home/pawan/Projects/jarvis-ai/scripts/dev.sh`
- **Permissions**: Executable (`chmod +x scripts/dev.sh`, `0755`)
- **Interpreter**: `#!/bin/bash`
- **Options**: `set -e`
- **Execution Workflow**:
  1. Print startup banner: `"Starting Jarvis AI in development mode..."`
  2. Launch Python backend in background:
     ```bash
     cd backend
     source .venv/bin/activate 2>/dev/null || true
     python3 -m jarvis &
     BACKEND_PID=$!
     ```
  3. Launch Electron frontend in background:
     ```bash
     cd ../frontend
     npm run dev &
     FRONTEND_PID=$!
     ```
  4. Trap signal handler for process termination:
     ```bash
     trap "echo 'Terminating Jarvis AI processes...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true" EXIT INT TERM
     wait
     ```

### 2.3 Dependency Specifications

#### Python Backend (`backend/pyproject.toml`)
- **Build System**: `hatchling`
- **Python Compatibility**: `>=3.11` (verified working on Python 3.14)
- **Core Dependencies**:
  - `websockets>=12.0` (asyncio WebSocket server & client)
  - `pydantic>=2.0` (data structures & schema validation)
  - `numpy>=1.24.0` (audio buffer representations and signal processing)
  - `pyyaml>=6.0` (optional YAML configuration support)
- **Plugin Runtime Dependencies (optional/pluggable)**:
  - `sounddevice>=0.4.6` (microphone capture and speaker playback)
  - `requests>=2.31.0` or `httpx>=0.27.0` (Ollama HTTP REST communication)
  - `mediapipe>=0.10.0` (face mesh landmark tracking)
- **Dev Dependencies**:
  - `pytest>=8.0`
  - `pytest-asyncio>=0.23`

#### Electron Frontend (`frontend/package.json`)
- **Node Engine**: `>=20.0.0`
- **Main Process Entry**: `dist/main.js`
- **NPM Scripts**:
  - `"build"`: `"tsc"`
  - `"dev"`: `"tsc && electron dist/main.js"`
  - `"start"`: `"electron dist/main.js"`
- **Dependencies**:
  - `ws`: `^8.16.0` (WebSocket protocol support)
- **Dev Dependencies**:
  - `electron`: `^30.0.0` or `^44.0.0`
  - `typescript`: `^5.4.0`
  - `@types/ws`: `^8.5.0`
  - `@types/node`: `^20.0.0`
- **TypeScript Configuration (`frontend/tsconfig.json`)**:
  - Target: `ES2022`
  - Module: `commonjs`
  - Libs: `["ES2022", "DOM"]`
  - OutDir: `dist`, RootDir: `src`
  - Compiler Flags: `strict: true`, `esModuleInterop: true`, `resolveJsonModule: true`, `declaration: true`

### 2.4 Configuration Layout & Defaults Specification

The configuration architecture supports both modular namespace JSON files (`config/*.json`) and a unified default configuration (`config/default.yaml` / `config/core.json`).

#### Directory Structure
```
config/
├── default.yaml            # Unified YAML fallback / reference defaults
├── core.json               # Backend host, port, active theme, default state
├── plugins/
│   ├── whisper_local.json  # STT model: "base"
│   ├── piper_tts.json      # TTS voice: "en_US-lessac-medium"
│   ├── ollama_llm.json     # LLM model: "llama3", base_url: "http://localhost:11434"
│   ├── push_to_talk.json   # Key: "space"
│   ├── clap_detector.json  # Threshold: 0.7, window_ms: 300
│   └── face_tracker.json   # Camera: 0, gaze_enabled: true
└── themes/
    ├── arc-reactor.json    # Default Iron Man cyan/blue/white theme
    ├── matrix.json         # Matrix green/black theme
    └── synthwave.json      # Retro neon pink/purple theme
```

#### Default Schema & Values:
1. **Core Settings (`config/core.json` / `config/default.yaml`)**:
   ```json
   {
     "host": "localhost",
     "port": 8765,
     "theme": "arc-reactor",
     "debug": false,
     "audio": {
       "sample_rate": 16000,
       "chunk_size": 1024
     }
   }
   ```
2. **Plugin Settings**:
   - `whisper_local`: `{"model": "base"}` (options: `tiny`, `base`, `small`, `medium`, `large`)
   - `piper_tts`: `{"voice": "en_US-lessac-medium"}`
   - `ollama_llm`: `{"model": "llama3", "base_url": "http://localhost:11434"}`
   - `push_to_talk`: `{"key": "space"}`
   - `clap_detector`: `{"threshold": 0.7, "window_ms": 300}`
   - `face_tracker`: `{"camera": 0, "gaze_enabled": true}`
3. **Theme Settings (`arc-reactor.json`)**:
   ```json
   {
     "name": "Arc Reactor",
     "colors": {
       "background": "#0a0a0f",
       "idle": "#1a3a5c",
       "listening": "#00d4ff",
       "thinking": "#ff9500",
       "speaking": "#ffffff",
       "error": "#ff3b30"
     },
     "core": {
       "outerRingSpeed": 20,
       "middleRingSpeed": 15,
       "innerRingSpeed": 10,
       "pulseSpeed": 2.0
     }
   }
   ```

### 2.5 Documentation Specification (`README.md`)
The root `README.md` must provide:
1. Project title, badge/status, and high-level mission (Iron Man JARVIS-inspired voice assistant).
2. Key features list (Voice interaction, ARC reactor HUD, pluggable AI backend, offline-first, Web Audio SFX).
3. Hybrid architecture overview (Python backend + Electron frontend + WebSocket `ws://localhost:8765`).
4. System Prerequisites (Python 3.11+, Node 20+, Ollama).
5. Quick Start guide (`./scripts/setup.sh` and `./scripts/dev.sh`).
6. Plugin developer documentation (how to create a custom plugin in `backend/jarvis/plugins/builtins/`).
7. Configuration guide (modifying `config/*.json` or using Settings panel).
8. Testing & Verification guide (`pytest` command and `npm run build`).

---

## 3. WebSocket Protocol & Communication Contracts

The WebSocket protocol operates over `ws://localhost:8765` using JSON message payloads.

### 3.1 Backend to Frontend Message Contract
| Message Type | Fields | Payload Example | Trigger / Source |
|---|---|---|---|
| `state_change` | `state`: `"idle"` \| `"listening"` \| `"thinking"` \| `"speaking"` \| `"error"` | `{"type": "state_change", "state": "listening"}` | State machine transition |
| `transcript_partial` | `text`: string | `{"type": "transcript_partial", "text": "Hey Jarvis what is"}` | Whisper STT streaming partial chunk |
| `transcript_final` | `text`: string | `{"type": "transcript_final", "text": "Hey Jarvis, what is the weather?"}` | Whisper STT end of speech detection |
| `llm_token` | `token`: string | `{"type": "llm_token", "token": "The"}` | Ollama LLM streaming response token |
| `response_complete` | `full_text`: string | `{"type": "response_complete", "full_text": "The weather is sunny."}` | Ollama LLM response generation completed |
| `audio_level` | `level`: float (0.0–1.0) | `{"type": "audio_level", "level": 0.73}` | Microphone energy stream / waveform anim |
| `face_data` | `gaze`: [x, y], `pose`: {pitch, yaw, roll}, `blink`: bool, `face_detected`: bool | `{"type": "face_data", "gaze": [0.4, 0.6], "pose": {"pitch": 5, "yaw": -2, "roll": 0}, "blink": false, "face_detected": true}` | MediaPipe face tracker plugin |
| `plugin_loaded` | `name`: string, `type`: string | `{"type": "plugin_loaded", "name": "whisper_local", "type": "stt"}` | PluginManager dynamic discovery/activation |
| `error` | `message`: string | `{"type": "error", "message": "Ollama connection refused"}` | Error state or exception handler |
| `pong` | (none) | `{"type": "pong"}` | Heartbeat response to client `ping` |

### 3.2 Frontend to Backend Message Contract
| Message Type | Fields | Payload Example | Purpose / Handler |
|---|---|---|---|
| `command` | `action`: `"activate"` \| `"deactivate"` | `{"type": "command", "action": "activate"}` | Manual trigger / HUD click / Push-to-talk |
| `config_update` | `plugin`: string, `key`: string, `value`: any | `{"type": "config_update", "plugin": "ollama_llm", "key": "model", "value": "llama3"}` | Dynamic runtime settings update from HUD |
| `settings_request` | (none) | `{"type": "settings_request"}` | Requests full configuration dump for UI |
| `ping` | (none) | `{"type": "ping"}` | Client liveness probe / heartbeat |

---

## 4. Test Suites, Verification Criteria & Acceptance Gates

### 4.1 Backend Pytest Suites
- **Execution Command**: `cd backend && python3 -m pytest tests/ -v`
- **Framework**: `pytest >= 8.0`, `pytest-asyncio >= 0.23`
- **Test Modules Inventory**:
  1. `tests/test_bus.py`:
     - `test_emit_and_receive`: Verifies event publishing and async handler dispatch.
     - `test_off_removes_handler`: Verifies handler removal without side effects.
  2. `tests/test_state.py`:
     - `test_initial_state`: Confirms default state is `JarvisState.IDLE`.
     - `test_valid_transition`: Tests valid transitions (`IDLE -> LISTENING`, `LISTENING -> THINKING`, `THINKING -> SPEAKING`, `SPEAKING -> IDLE`).
     - `test_invalid_transition`: Verifies illegal transitions (e.g. `IDLE -> SPEAKING`) return `False` and preserve current state.
     - `test_on_change_callback`: Verifies registered callback receives `(old_state, new_state)`.
  3. `tests/test_ws_server.py`:
     - `test_server_broadcast`: Tests real WebSocket server startup on test port, client connection, and broadcasting JSON messages.
  4. `tests/test_plugins.py`:
     - `test_discover`: Tests discovering `.py` plugin files from a directory and loading plugin classes.
     - `test_activate_deactivate`: Tests activating and stopping plugins, and querying active plugins by `PluginType`.
  5. `tests/test_config.py`:
     - `test_list_namespaces`: Tests listing available JSON configuration namespaces.
     - `test_get_all`: Tests reading entire namespace configuration dictionary.
     - `test_get_set`: Tests getting specific keys with default fallbacks and persisting updates to disk.
  6. `tests/test_audio.py`:
     - `test_vad_silence`: Tests VAD returns `False` for zero/low-energy buffer.
     - `test_vad_speech`: Tests VAD returns `True` for high-energy buffer.
     - `test_mic_start_stop`: Tests mic stream start/stop flag transitions.
  7. `tests/test_whisper_plugin.py`:
     - `test_start_stop`: Tests plugin start/stop with config dictionary.
     - `test_on_event_returns_none_for_unknown`: Confirms ignoring irrelevant events.
     - `test_get_schema`: Confirms presence of schema properties (`model`).
  8. `tests/test_piper_plugin.py`:
     - `test_start_stop`: Tests Piper plugin start/stop lifecycle.
     - `test_speak_returns_audio`: Tests `speak` event emits `audio_chunk` event.
     - `test_get_schema`: Confirms presence of `voice` schema property.
  9. `tests/test_ollama_plugin.py`:
     - `test_start_stop`: Tests Ollama plugin configuration loading (`model`, `base_url`).
     - `test_llm_request`: Tests `llm_request` produces `response_complete`.
     - `test_get_schema`: Confirms schema contains `model` and `base_url`.
  10. `tests/test_push_to_talk.py`:
      - `test_key_down_activates`: Tests configured key down triggers `activation`.
      - `test_key_up_deactivates`: Tests configured key up triggers `deactivation`.
      - `test_wrong_key_ignored`: Tests non-matching key presses are ignored.
  11. `tests/test_clap_detector.py`:
      - `test_single_clap_no_activation`: Tests single energy peak does not trigger activation.
      - `test_double_clap_activates`: Tests two peaks within window_ms trigger `activation`.
      - `test_low_energy_ignored`: Tests low energy peaks are ignored.
  12. `tests/test_face_tracker.py`:
      - `test_start_stop`: Tests vision plugin start/stop.
      - `test_face_data_event`: Tests `camera_frame` emits `face_data` with gaze and pose fields.

### 4.2 Frontend Build & Compilation Validation
- **Execution Command**: `cd frontend && npm run build`
- **Compiler**: `tsc` (TypeScript Compiler ES2022 / CommonJS)
- **Validation Criteria**:
  - Zero compilation errors (`tsc` exit code 0).
  - Emits all declaration files (`.d.ts`) and compiled JavaScript into `dist/`.
  - Electron main process (`dist/main.js`), preload script (`dist/preload.js`), and renderer scripts (`dist/renderer/**/*.js`) generated cleanly.

### 4.3 End-to-End Acceptance Gates
| Gate ID | Gate Name | Verification Command / Action | Acceptance Criterion |
|---|---|---|---|
| **GATE-1** | Unit Test Suite | `cd backend && python3 -m pytest tests/ -v` | 100% tests pass (minimum 12 suites, 25+ assertions) |
| **GATE-2** | Frontend Typecheck | `cd frontend && npm run build` | Zero TypeScript compiler errors |
| **GATE-3** | Setup Automation | `./scripts/setup.sh` | Clean execution, virtual environment created, packages installed |
| **GATE-4** | Dev Script Orchestration | `./scripts/dev.sh` | Concurrently starts backend & frontend, trap terminates both on exit |
| **GATE-5** | WebSocket Handshake | Backend running on 8765, frontend connects | Console logs `"Connected to Jarvis backend"`, status bar shows `"● Idle"` |
| **GATE-6** | State Machine Sync | Send `activate` command | State transitions `idle -> listening`, HUD shifts to cyan glow, ARC reactor accelerates |
| **GATE-7** | Live Transcript Streaming | Emit `transcript_partial` / `transcript_final` | Text renders immediately in `#transcript-text` |
| **GATE-8** | Web Audio SFX Synthesis | State changes trigger synthesized audio | Sounds play cleanly via Web Audio API without external audio file requests |
| **GATE-9** | Reconnection Resilience | Kill backend, wait 2s, restart backend | Frontend reconnects automatically with exponential backoff and resumes sync |

---

## 5. Discovered Features & Edge Cases

## Features Discovered
| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|---|---|---|---|---|---|---|
| 1 | Tooling | `scripts/setup.sh` | Automated environment setup for Python venv, pip dependencies, and npm packages | None (CLI execution) | stdout logs, venv, node_modules | Exits with error code on failure (`set -e`) | Implementation Plan Task 20 |
| 2 | Tooling | `scripts/dev.sh` | Concurrent dev runner with trap cleanup for backend & frontend | None (CLI execution) | Spawns background PIDs, merges logs | Traps EXIT/INT/TERM and kills child processes | Implementation Plan Task 20 |
| 3 | Tooling | `README.md` | Comprehensive documentation of architecture, quickstart, plugins, and config | Markdown doc | Rendered documentation | N/A | Implementation Plan Task 20 & ORIGINAL_REQUEST.md |
| 4 | Configuration | Namespace JSON Loader | Dynamic JSON configuration loader per component (`config/*.json`) | Namespace string, key, default value | Config dictionary or value | Returns default if key/file missing, creates dir on save | Implementation Plan Task 1 & 7 |
| 5 | Configuration | Default YAML Support | Unified default configuration file for system reference (`config/default.yaml`) | YAML file parsing | Default config tree | Falls back to hardcoded defaults if missing | ORIGINAL_REQUEST.md R4 |
| 6 | Core Backend | Async Event Bus | Asynchronous publish-subscribe event dispatch system | `Event(type, data, source)` | Dispatched async handlers | Queue isolates handler errors | Implementation Plan Task 1 |
| 7 | Core Backend | State Machine | 5-state automaton (`idle`, `listening`, `thinking`, `speaking`, `error`) | `JarvisState` transition target | Boolean success, listener callbacks | Returns `False` on invalid transition | Implementation Plan Task 1 |
| 8 | Core Backend | WebSocket Server | Async WebSocket server on `ws://localhost:8765` for IPC | JSON client messages | Broadcast JSON events | Discards closed connections gracefully | Implementation Plan Task 3 |
| 9 | Plugin System | Dynamic Plugin Discovery | Scans directory for `.py` files and instantiates `Plugin` classes | Directory path (`plugins/`) | List of discovered plugin names | Skips files prefixed with `_` or invalid syntax | Implementation Plan Task 6 |
| 10 | Plugin System | Plugin Activation Lifecycle | Starts/stops plugins dynamically with config injection | Plugin name | Boolean success status | Returns `False` if plugin name unknown | Implementation Plan Task 6 |
| 11 | Audio Pipeline | Microphone Stream | Continuous audio chunk generator for STT and activation | Sample rate, chunk size | Async generator of `np.ndarray` float32 | Yields silent buffers if device unavailable | Implementation Plan Task 8 |
| 12 | Audio Pipeline | Speaker Output | Audio buffer playback sink for synthesized speech | Audio `np.ndarray`, sample rate | Audio playback | Ignores playback when stopped | Implementation Plan Task 8 |
| 13 | Audio Pipeline | Voice Activity Detection (VAD) | Energy/model-based speech detector | Audio buffer chunk | Boolean `is_speech` | Returns `False` on silence / below threshold | Implementation Plan Task 8 |
| 14 | Builtin Plugin | Whisper STT Plugin | Speech-to-text inference emitting partial & final transcripts | Audio chunks, `speech_end` events | `transcript_partial`, `transcript_final` | Emits `None` on silence | Implementation Plan Task 9 |
| 15 | Builtin Plugin | Piper TTS Plugin | Text-to-speech engine emitting raw audio chunks | `speak` event with text string | `audio_chunk` event with audio array | Returns `None` on empty or invalid event | Implementation Plan Task 10 |
| 16 | Builtin Plugin | Ollama LLM Plugin | Local LLM inference engine via Ollama REST API | `llm_request` with prompt string | `llm_token` stream, `response_complete` | Returns error event if Ollama unreachable | Implementation Plan Task 11 |
| 17 | Builtin Plugin | Push-to-Talk Plugin | Hotkey hold activation detector | `key_down`, `key_up` events | `activation`, `deactivation` events | Ignores keys other than configured key | Implementation Plan Task 12 |
| 18 | Builtin Plugin | Clap Detector Plugin | Double-clap pattern energy detector | `audio_energy` events with energy level | `activation` event on double-clap | Resets counter if interval exceeds `window_ms` | Implementation Plan Task 13 |
| 19 | Builtin Plugin | Face Tracker Plugin | MediaPipe face mesh tracker for gaze and head pose | `camera_frame` events | `face_data` event (gaze, pose, blink) | Degrades to default coordinates if camera lost | Implementation Plan Task 17 |
| 20 | Frontend HUD | Multi-Ring ARC Reactor | Concentric rotating SVG/Canvas rings reacting to states | State string (`idle`, `listening`, etc.) | Animated visual rendering on HUD | Falls back to idle blue animation | Implementation Plan Task 14 |
| 21 | Frontend HUD | Waveform Visualizer | Real-time audio spectrum/level visualizer | `audio_level` event floats | 64-bar animated audio canvas | Clears canvas when audio stops | Implementation Plan Task 15 |
| 22 | Frontend HUD | Particle Engine | State-reactive ambient floating HUD particles | State string | Spawns & renders particles (30–100) | Reduces density to 30 on idle | Implementation Plan Task 16 |
| 23 | Frontend HUD | Web Audio SFX Synth | Synthesizes Iron Man repulsor/boot/chime sound effects | Method triggers (`powerUp`, `chime`, etc.) | Web Audio API oscillator/gain audio | Fails silently if Web Audio blocked | Implementation Plan Task 18 |
| 24 | Frontend HUD | Sliding Settings Panel | Right-docked configuration panel with runtime config dispatch | User UI interactions | `config_update` WebSocket messages | Logs error if WebSocket closed | Implementation Plan Task 19 |
| 25 | Frontend HUD | WebSocket Client | Reconnecting WebSocket client with typed event bus | WebSocket URL | Dispatches typed events to HUD elements | Reconnects with exponential backoff (1s–10s) | Implementation Plan Task 2 |

## Edge Cases
| # | Feature | Input | Observed Behavior |
|---|---|---|---|
| 1 | `scripts/dev.sh` Cleanup | SIGINT (`Ctrl+C`) or SIGTERM | Trap catches signal, sends `kill` to `$BACKEND_PID` and `$FRONTEND_PID`, avoids orphaned zombie processes |
| 2 | `scripts/setup.sh` Idempotency | Running `./scripts/setup.sh` multiple times | Safely upgrades existing virtualenv and updates npm packages without failing |
| 3 | Config Loader | Missing namespace JSON file (e.g. `config/unknown.json`) | Returns empty dictionary or fallback default value without raising `FileNotFoundError` |
| 4 | State Machine | Invalid transition attempt (e.g. `JarvisState.IDLE -> JarvisState.SPEAKING`) | Returns `False`, state remains `JarvisState.IDLE`, no listeners notified |
| 5 | WebSocket Server | Client abruptly disconnects during broadcast | Server catches `websockets.ConnectionClosed` and removes client from active subscriber set |
| 6 | WebSocket Client | Backend server crashes or is restarted | Client triggers `onclose`, displays reconnecting state, retries connection every `min(delay * 2, 10000)` ms |
| 7 | Clap Detector | Single loud noise (door slam / single clap) | Registers clap 1, but window expires without second clap; no activation triggered |
| 8 | Push-to-Talk | Rapid key repeat events from OS | State remains pressed without sending redundant activation events |
| 9 | Ollama LLM | Ollama service offline or model missing | Error caught, broadcasts `{"type": "error", "message": "Ollama connection refused"}`, state machine transitions to `error` |
| 10 | Web Audio Synth | AudioContext created before user interaction | AudioContext resumes on first click/interaction as required by modern browser autoplay policies |
| 11 | Plugin Manager | Malformed Python plugin file in `plugins/` | Skips file with logged warning during discovery, does not crash core application |
| 12 | Face Tracker | Camera denied or unavailable | Emits `face_detected: false`, HUD falls back to standard centered view without gaze parallax |

---

## 6. Recommendations & Implementation Order for Downstream Agents

1. **Verify Python Virtual Environment & Test Baseline**:
   - Ensure Hatchling build configuration and pytest dependencies in `backend/pyproject.toml` are recognized.
   - Run `cd backend && python3 -m pytest tests/ -v`.
2. **Verify Frontend Build Baseline**:
   - Run `cd frontend && npm run build` to ensure TypeScript compilation produces clean `dist/` outputs.
3. **Execute Full Suite on Every Phase**:
   - Follow the 20-task roadmap in `docs/superpowers/plans/2026-08-26-jarvis-ai-implementation.md`.
   - Ensure all 12 backend test modules and all frontend HUD visualizer components are thoroughly implemented.
4. **Final Packaging & Script Verification**:
   - Ensure `scripts/setup.sh` and `scripts/dev.sh` have executable permissions (`+x`) and pass manual invocation tests.
   - Ensure `README.md` documents exact procedures for installation, execution, and plugin authoring.
