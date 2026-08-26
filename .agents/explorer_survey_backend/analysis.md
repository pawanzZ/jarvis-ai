# Backend Architecture & System Survey Report — Jarvis AI

**Date:** 2026-08-26 / 2026-08-27  
**Explorer:** Backend & Architecture Explorer  
**Workspace:** `/home/pawan/Projects/jarvis-ai`  
**Target Requirements:** R1 (Core Backend Architecture & WebSocket Service), R2 (Pluggable AI & Audio Pipeline)

---

## 1. Executive Summary

This survey analyzes the backend architecture, module contracts, event routing, state transitions, configuration management, WebSocket protocol, and plugin ecosystem for **Jarvis AI** — a voice-interactive desktop assistant inspired by Iron Man.

The backend is built around Python 3.11+ using `asyncio` and `websockets` to drive an event-driven, decoupled microkernel architecture. The Python backend hosts all heavy compute and ML workloads (STT, TTS, LLM, activation detection, and vision/face tracking) while serving as the authoritative state coordinator communicating with the Electron HUD frontend over `ws://localhost:8765`.

---

## 2. Requirements & Scope Breakdown

### Requirement 1: Core Backend Architecture & WebSocket Service (R1)
- **Asyncio Event Loop & Lifecycle:** Single authoritative async coordinator in `backend/jarvis/__main__.py` managing background event dispatch, WebSocket server, and audio/plugin loops.
- **EventBus (`backend/jarvis/core/bus.py`):** Asynchronous pub/sub message bus with an event queue and typed callback subscribers.
- **StateMachine (`backend/jarvis/core/state.py`):** Deterministic 5-state FSM (`IDLE`, `LISTENING`, `THINKING`, `SPEAKING`, `ERROR`) with transition validation and state-change notification hooks.
- **ConfigLoader (`backend/jarvis/core/config.py`):** File-backed configuration store supporting per-namespace caching, dynamic retrieval, updates, and persistence in `config/{namespace}.json`.
- **WebSocket Server (`backend/jarvis/ws_server.py`):** Localhost WebSocket service listening on port `8765`, facilitating bidirectional JSON messaging, client registration, command dispatch, state broadcasts, and ping/pong heartbeats.

### Requirement 2: Pluggable AI & Audio Pipeline (R2)
- **Plugin Architecture (`backend/jarvis/plugins/`):** Standard abstract interface (`Plugin`) with lifecycle management (`start`, `stop`, `on_event`, `get_schema`) and a dynamic loader (`PluginManager`) for hot-pluggable backends.
- **Speech-to-Text (STT):** Local Whisper plugin (`whisper_local.py`) processing audio chunks and streaming partial/final transcripts.
- **Text-to-Speech (TTS):** Piper TTS plugin (`piper_tts.py`) synthesizing response text into audio stream chunks.
- **Large Language Model (LLM):** Ollama plugin (`ollama_llm.py`) interfacing with local models (default `llama3`) via `http://localhost:11434` with streaming token emission.
- **Activation Gate:** Multi-modal activation plugins:
  1. *Push-to-talk (`push_to_talk.py`):* Configurable keyboard trigger (default: Space hold).
  2. *Double-clap detector (`clap_detector.py`):* Dual energy spike pattern recognition within a 300ms window.
  3. *Wake Word & Gesture (Future / Pluggable extensions).*
- **Vision & Face Tracking (`face_tracker.py`):** MediaPipe Face Mesh integration capturing gaze coordinates, head pose angles (pitch, yaw, roll), and blink indicators.
- **Audio Pipeline Foundation (`backend/jarvis/audio/`):** Stream abstractions for microphone capture (`mic_stream.py`), audio playback (`speaker_output.py`), and voice activity detection (`vad.py`).
- **Mock / Offline Fallbacks:** Robust fallback mechanisms ensuring zero fatal crashes when audio devices, cameras, or external AI daemons (e.g. Ollama) are unavailable.

---

## 3. Current Workspace Inventory vs. Target Architecture

| Component | Target File | Current Status | Findings & Required Next Steps |
|---|---|---|---|
| Package Manifest | `backend/pyproject.toml` | **Present** | Configured with `websockets>=12.0`, `pydantic>=2.0`, `pytest>=8.0`. Need optional dependencies for audio/ML (numpy, etc.). |
| Core Entry Point | `backend/jarvis/__main__.py` | **Partial** | Instantiates `EventBus`, `StateMachine`, `Config`, `WSServer`. Needs `bus.process()` task execution and plugin initialization. |
| Event Bus | `backend/jarvis/core/bus.py` | **Present** | `Event` dataclass and `EventBus` class implemented. Needs integration with main loop for background processing. |
| State Machine | `backend/jarvis/core/state.py` | **Present** | Enum `JarvisState`, `TRANSITIONS` map, `StateMachine` class implemented with tests passing. |
| Config Loader | `backend/jarvis/core/config.py` | **Partial** | Basic `get`, `set`, `_load`, `_save` present. Needs `list_namespaces()` and `get_all(namespace)` from Task 7. |
| WebSocket Server | `backend/jarvis/ws_server.py` | **Present** | Port `8765`, connection pool, broadcast, command routing (`activate`, `deactivate`, `config_update`, `ping`). |
| Plugin Interface | `backend/jarvis/plugins/base.py` | **Missing** | `PluginType` enum and `Plugin` ABC need to be created. |
| Plugin Manager | `backend/jarvis/plugins/manager.py` | **Missing** | `PluginManager` with `discover()`, `activate()`, `deactivate()`, `get_active()` needs to be created. |
| Audio Subsystem | `backend/jarvis/audio/mic_stream.py`<br>`backend/jarvis/audio/speaker_output.py`<br>`backend/jarvis/audio/vad.py` | **Missing** | Directory `backend/jarvis/audio/` exists but files are uncreated. |
| Whisper STT Plugin | `backend/jarvis/plugins/builtins/whisper_local.py` | **Missing** | File uncreated. |
| Piper TTS Plugin | `backend/jarvis/plugins/builtins/piper_tts.py` | **Missing** | File uncreated. |
| Ollama LLM Plugin | `backend/jarvis/plugins/builtins/ollama_llm.py` | **Missing** | File uncreated. |
| Push-to-Talk Plugin | `backend/jarvis/plugins/builtins/push_to_talk.py` | **Missing** | File uncreated. |
| Clap Detector Plugin | `backend/jarvis/plugins/builtins/clap_detector.py` | **Missing** | File uncreated. |
| Face Tracker Plugin | `backend/jarvis/plugins/builtins/face_tracker.py` | **Missing** | File uncreated. |
| Unit Tests | `backend/tests/` | **Partial** | `test_bus.py`, `test_state.py`, `test_ws_server.py` exist. Plugin and audio tests need to be added. |

---

## 4. Deep-Dive Component Architecture

### 4.1 State Machine Specification

```
                  ┌────────────────────────┐
                  │                        │
                  ▼                        │ (error recovered)
           ┌──────────────┐                │
      ┌───▶│     IDLE     │◀───────────────┤
      │    └──────┬───────┘                │
      │           │ (wake/PTT/clap)        │
      │           ▼                        │
      │    ┌──────────────┐                │
(stop)│    │  LISTENING   │                │
      │    └──────┬───────┘                │
      │           │ (VAD speech end)       │
      │           ▼                        │
      │    ┌──────────────┐                │
      │    │   THINKING   │                │
      │    └──────┬───────┘                │
      │           │ (LLM 1st token/audio)  │
      │           ▼                        │
      │    ┌──────────────┐                │
      │    │   SPEAKING   │────────────────┘
      │    └──────┬───────┘ (barge-in: user speaks)
      │           │
      │           ▼
      │    (back to LISTENING)
      │
      └────▶ [ Any State ] ──▶ ERROR ──▶ IDLE
```

#### States:
- `JarvisState.IDLE = "idle"`: Ambient state. ARC reactor spins slowly in dim blue (#1a3a5c). Low CPU monitoring for wake events.
- `JarvisState.LISTENING = "listening"`: Audio capture active. Waveform visualizer active, ARC reactor cyan pulse (#00d4ff). Partial STT streaming.
- `JarvisState.THINKING = "thinking"`: STT final transcript submitted to LLM. Reactor spinner amber glow (#ff9500).
- `JarvisState.SPEAKING = "speaking"`: TTS streaming audio back. Core bright white/blue (#ffffff / #00b4ff). Barge-in enabled.
- `JarvisState.ERROR = "error"`: Fault condition (e.g. Ollama down, device unplugged). Red warning (#ff3b30). Auto-resets to IDLE.

#### State Transitions Map:
```python
TRANSITIONS: dict[JarvisState, set[JarvisState]] = {
    JarvisState.IDLE: {JarvisState.LISTENING, JarvisState.ERROR},
    JarvisState.LISTENING: {JarvisState.THINKING, JarvisState.IDLE, JarvisState.ERROR},
    JarvisState.THINKING: {JarvisState.SPEAKING, JarvisState.IDLE, JarvisState.ERROR},
    JarvisState.SPEAKING: {JarvisState.LISTENING, JarvisState.IDLE, JarvisState.ERROR},
    JarvisState.ERROR: {JarvisState.IDLE},
}
```

---

### 4.2 EventBus & Dispatch Flow

The `EventBus` decouples all core modules and plugins.

```python
@dataclass
class Event:
    type: str
    data: dict[str, Any] = field(default_factory=dict)
    source: str = ""
```

#### Event Catalog:

| Event Type | Producer | Consumer(s) | Payload (`data`) | Description |
|---|---|---|---|---|
| `activate` | WS Server / HUD / PTT / Clap | StateMachine, Audio Pipeline | `{}` | Requests transition to `LISTENING`. |
| `deactivate` | WS Server / HUD / PTT | StateMachine, Audio Pipeline | `{}` | Requests return to `IDLE`. |
| `audio_chunk` | MicStream | VAD, STT Plugin | `{"audio": np.ndarray, "sample_rate": 16000}` | Raw audio buffer from mic. |
| `audio_energy` | Audio Preprocessor | Clap Detector | `{"energy": float}` | Audio RMS amplitude (0.0 to 1.0). |
| `transcript_partial` | Whisper STT | WSServer -> Frontend HUD | `{"text": str}` | Real-time preliminary transcription. |
| `transcript_final` | Whisper STT | StateMachine, LLM Plugin | `{"text": str}` | Completed speech transcription. |
| `llm_request` | Core / StateMachine | Ollama LLM Plugin | `{"prompt": str}` | Prompt to send to LLM. |
| `llm_token` | Ollama LLM | WSServer -> Frontend HUD | `{"token": str}` | Single token streamed from LLM. |
| `response_complete` | Ollama LLM | Piper TTS, HUD | `{"text": str}` | Full LLM completion string. |
| `speak` | Core / StateMachine | Piper TTS Plugin | `{"text": str}` | Command to synthesize speech. |
| `camera_frame` | Camera Capture Loop | FaceTracker Plugin | `{"frame": np.ndarray}` | Video frame for vision tracking. |
| `face_data` | FaceTracker | WSServer -> Frontend HUD | `{"gaze": [x, y], "pose": {...}, "blink": bool, "face_detected": bool}` | Tracking metrics. |
| `config_update` | WSServer / HUD | Config, PluginManager | `{"plugin": str, "key": str, "value": Any}` | Dynamic configuration mutation. |
| `error` | Any Subsystem | StateMachine, WSServer | `{"message": str, "code": Optional[str]}` | Error notification. |

---

### 4.3 WebSocket Server Protocol (`localhost:8765`)

All payloads are serialized JSON objects with a top-level `"type"` property.

#### Inbound (Frontend -> Backend):
1. **Command Activation:**
   ```json
   { "type": "command", "action": "activate" }
   ```
2. **Command Deactivation:**
   ```json
   { "type": "command", "action": "deactivate" }
   ```
3. **Config Update:**
   ```json
   { "type": "config_update", "plugin": "ollama_llm", "key": "model", "value": "llama3:8b" }
   ```
4. **Settings Schema Request:**
   ```json
   { "type": "settings_request" }
   ```
5. **Heartbeat Ping:**
   ```json
   { "type": "ping" }
   ```

#### Outbound (Backend -> Frontend):
1. **State Broadcast:**
   ```json
   { "type": "state_change", "state": "listening" }
   ```
2. **Streaming Transcripts:**
   ```json
   { "type": "transcript_partial", "text": "Jarvis what is" }
   { "type": "transcript_final", "text": "Jarvis what is the time?" }
   ```
3. **Streaming LLM Tokens:**
   ```json
   { "type": "llm_token", "token": "It" }
   { "type": "llm_token", "token": " is" }
   { "type": "response_complete", "full_text": "It is currently 7:30 PM, sir." }
   ```
4. **Audio Visualizer Level:**
   ```json
   { "type": "audio_level", "level": 0.65 }
   ```
5. **Vision & Face Tracking:**
   ```json
   {
     "type": "face_data",
     "gaze": [0.48, 0.52],
     "pose": { "pitch": 2.1, "yaw": -1.4, "roll": 0.3 },
     "blink": false,
     "face_detected": true
   }
   ```
6. **Plugin Registration:**
   ```json
   { "type": "plugin_loaded", "name": "whisper_local", "type": "stt" }
   ```
7. **Error Notification:**
   ```json
   { "type": "error", "message": "Ollama service unavailable at http://localhost:11434" }
   ```
8. **Heartbeat Pong:**
   ```json
   { "type": "pong" }
   ```

---

### 4.4 Plugin Architecture & Schema Contracts

All plugins derive from `Plugin` (`backend/jarvis/plugins/base.py`):

```python
class PluginType(str, Enum):
    STT = "stt"
    TTS = "tts"
    LLM = "llm"
    WAKE_WORD = "wake_word"
    ACTIVATION = "activation"
    VISION = "vision"

class Plugin(ABC):
    name: str = "unnamed"
    plugin_type: PluginType = PluginType.STT

    @abstractmethod
    async def start(self, config: dict[str, Any]) -> None: ...

    @abstractmethod
    async def stop(self) -> None: ...

    @abstractmethod
    async def on_event(self, event: Event) -> Optional[Event]: ...

    @abstractmethod
    def get_schema(self) -> dict[str, Any]: ...
```

#### Builtin Plugin Specifications:

1. **`WhisperLocalPlugin` (`whisper_local.py`):**
   - Type: `PluginType.STT`
   - Config Schema:
     ```json
     {
       "type": "object",
       "properties": {
         "model": {
           "type": "string",
           "enum": ["tiny", "base", "small", "medium", "large"],
           "default": "base"
         }
       }
     }
     ```
   - Behavior: Consumes `audio_chunk` buffers. When voice activity ceases (`speech_end`), generates `transcript_final`. Emits `transcript_partial` on intermediate segments.

2. **`PiperTTSPlugin` (`piper_tts.py`):**
   - Type: `PluginType.TTS`
   - Config Schema:
     ```json
     {
       "type": "object",
       "properties": {
         "voice": {
           "type": "string",
           "default": "en_US-lessac-medium"
         },
         "rate": {
           "type": "number",
           "default": 1.0
         }
       }
     }
     ```
   - Behavior: Consumes `speak` events. Generates audio chunks (`audio_chunk`) for playback or streaming to frontend.

3. **`OllamaLLMPlugin` (`ollama_llm.py`):**
   - Type: `PluginType.LLM`
   - Config Schema:
     ```json
     {
       "type": "object",
       "properties": {
         "model": { "type": "string", "default": "llama3" },
         "base_url": { "type": "string", "default": "http://localhost:11434" },
         "temperature": { "type": "number", "default": 0.7 }
       }
     }
     ```
   - Behavior: Consumes `llm_request`. Connects to Ollama HTTP API, iterates streaming tokens (`llm_token`), then yields `response_complete`. Gracefully falls back to offline canned responses or error messages if Ollama is unreachable.

4. **`PushToTalkPlugin` (`push_to_talk.py`):**
   - Type: `PluginType.ACTIVATION`
   - Config Schema:
     ```json
     {
       "type": "object",
       "properties": {
         "key": { "type": "string", "default": "space" }
       }
     }
     ```
   - Behavior: Translates `key_down` to `activation` and `key_up` to `deactivation`.

5. **`ClapDetectorPlugin` (`clap_detector.py`):**
   - Type: `PluginType.ACTIVATION`
   - Config Schema:
     ```json
     {
       "type": "object",
       "properties": {
         "threshold": { "type": "number", "default": 0.7 },
         "window_ms": { "type": "integer", "default": 300 }
       }
     }
     ```
   - Behavior: Detects two high-energy spikes within `window_ms` and emits `activation`.

6. **`FaceTrackerPlugin` (`face_tracker.py`):**
   - Type: `PluginType.VISION`
   - Config Schema:
     ```json
     {
       "type": "object",
       "properties": {
         "camera": { "type": "integer", "default": 0 },
         "min_detection_confidence": { "type": "number", "default": 0.5 }
       }
     }
     ```
   - Behavior: Processes camera frames, computes face landmarks, head rotation matrix, gaze center, and blink ratio, emitting `face_data`.

---

### 4.5 Configuration Management

Configuration files reside in `config/` (or `jarvis/config/`):
- `core.json`: Core app settings (ports, log levels, default active plugins).
- `plugins/{plugin_name}.json`: Per-plugin settings matching the plugin's `get_schema()` definitions.
- `themes/{theme_name}.json`: HUD theme definitions.

The `Config` class loads, caches, and serializes updates on `set()`, ensuring changes via the HUD Settings panel persist across restarts.

---

## 5. Critical Implementation Insights & Recommendations

1. **Async EventBus Execution:**
   In `backend/jarvis/__main__.py`, ensure `asyncio.create_task(bus.process())` is launched. Without this, events pushed via `emit()` accumulate in `_queue` without dispatching to registered handlers.

2. **WebSockets Server Compatibility:**
   `websockets>=12.0` changed import semantics (`websockets.asyncio.server.serve` vs legacy `websockets.server.serve`). The implementation in `ws_server.py` and `test_ws_server.py` already includes dual import fallbacks, which must be preserved across future tests.

3. **Pluggable Discovery & Module Loading:**
   `PluginManager.discover()` should inspect `backend/jarvis/plugins/builtins/*.py` (and optionally user plugins in a configured external path), safely importing each module and instantiating its `plugin_class`.

4. **Graceful Degraded / Mock Mode:**
   When running on headless Linux CI or machines without webcam/mic/Ollama:
   - `MicStream` and `FaceTrackerPlugin` must yield synthetic/mock data rather than crashing.
   - `OllamaLLMPlugin` must catch connection exceptions and emit descriptive error events without terminating the process.

5. **Audio Pipeline Synchronization:**
   When state transitions from `LISTENING` -> `THINKING`, the microphone stream should pause or decouple to avoid processing background noise during thinking. When TTS finishes (`SPEAKING` -> `IDLE` or `LISTENING`), the barge-in gate should reset.

---

## 6. Implementation Checklist & Roadmap

- [ ] **Phase 2 Implementation:**
  - Create `backend/jarvis/plugins/__init__.py`, `base.py`, `manager.py`.
  - Enhance `backend/jarvis/core/config.py` with `list_namespaces()` and `get_all()`.
  - Create plugin test suite `backend/tests/test_plugins.py` and `test_config.py`.
- [ ] **Phase 3 Implementation (Voice Core):**
  - Implement `backend/jarvis/audio/mic_stream.py`, `speaker_output.py`, `vad.py`.
  - Implement `backend/jarvis/plugins/builtins/whisper_local.py`.
  - Implement `backend/jarvis/plugins/builtins/piper_tts.py`.
  - Implement `backend/jarvis/plugins/builtins/ollama_llm.py`.
  - Create tests: `test_audio.py`, `test_whisper_plugin.py`, `test_piper_plugin.py`, `test_ollama_plugin.py`.
- [ ] **Phase 4 Implementation (Activation):**
  - Implement `backend/jarvis/plugins/builtins/push_to_talk.py`.
  - Implement `backend/jarvis/plugins/builtins/clap_detector.py`.
  - Create tests: `test_push_to_talk.py`, `test_clap_detector.py`.
- [ ] **Phase 6 Implementation (Vision):**
  - Implement `backend/jarvis/plugins/builtins/face_tracker.py`.
  - Create tests: `test_face_tracker.py`.
- [ ] **End-to-End Wiring:**
  - Wire plugin manager discovery, active plugin activation, and event forwarding into `backend/jarvis/__main__.py`.
  - Verify complete backend test suite: `pytest tests/ -v`.
