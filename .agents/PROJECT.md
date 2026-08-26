# Project: Jarvis AI

## Architecture
Jarvis AI is a voice-interactive desktop AI assistant with a full-screen Iron Man-inspired HUD visualizer and pluggable local/cloud AI backends.

```
+-------------------------------------------------------------------------------+
|                             Electron HUD Frontend                            |
|  - Fullscreen transparent window (Iron Man HUD)                               |
|  - Multi-ring ARC Reactor Canvas & CSS animations (IDLE/LISTENING/THINKING...) |
|  - Audio Waveform Visualizer & Particle System Canvas                         |
|  - Status Bar, Streaming Transcript Bar, Settings Overlay Panel               |
|  - Web Audio API Procedural SFX Synthesizer (0 audio asset dependencies)      |
+---------------------------------------^---------------------------------------+
                                        | WebSocket JSON (ws://localhost:8765)
+---------------------------------------v---------------------------------------+
|                            Python AsyncIO Backend                             |
|  +-------------------------------------------------------------------------+  |
|  |                            Core Event Loop                              |  |
|  |   EventBus (asyncio.Queue) <---> StateMachine (5 Jarvis states)         |  |
|  |   Config (JSON/YAML namespace store) <---> WSServer (WebSocket Gateway) |  |
|  +------------------------------------^------------------------------------+  |
|                                       | Internal Events & State Updates       |
|  +------------------------------------v------------------------------------+  |
|  |                            Plugin Manager                               |  |
|  |   Base Plugin Interface (start, stop, on_event, get_schema)              |  |
|  |   Builtins:                                                             |  |
|  |     - STT: Whisper (Local whisper.cpp / faster-whisper / mock)          |  |
|  |     - TTS: Piper (Local piper-tts / speech-dispatcher / mock)          |  |
|  |     - LLM: Ollama (Local llama3 / mock offline fallback)               |  |
|  |     - Activation: Push-to-Talk (Global shortcut / mock)                 |  |
|  |     - Activation: Double-Clap Detector (Energy & peak analysis)         |  |
|  |     - Vision: Face Tracker (MediaPipe Face Mesh telemetry / mock)       |  |
|  +-------------------------------------------------------------------------+  |
|  |                            Audio Subsystem                              |  |
|  |   MicStream (SoundDevice/PyAudio) | SpeakerOutput | VAD (Energy/Silero) |  |
|  +-------------------------------------------------------------------------+  |
+-------------------------------------------------------------------------------+
```

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | AsyncIO Event Bus | Async event queue and typed subscription bus | M1 | Backend Spec / Plan Phase 1 |
| 2 | State Machine | 5-state FSM (IDLE, LISTENING, THINKING, SPEAKING, ERROR) | M1 | Backend Spec / Plan Phase 1 |
| 3 | Config Store | Namespace-isolated config loader, getter/setter, persistence | M1 | Backend Spec / Plan Phase 2 |
| 4 | WebSocket Server | WebSocket server on port 8765 with client broadcast & command routing | M1 | Backend Spec / Plan Phase 1 |
| 5 | Plugin Architecture & Manager | Base Plugin abstract class, discovery, lifecycle, dynamic registration | M1 | Backend Spec / Plan Phase 2 |
| 6 | Audio Foundation | MicStream, SpeakerOutput, and Voice Activity Detection (VAD) | M2 | Audio Spec / Plan Phase 3 |
| 7 | Whisper Local STT Plugin | Speech-to-text plugin supporting Whisper model inference & mock fallback | M2 | Plugin Spec / Plan Phase 3 |
| 8 | Piper Local TTS Plugin | Text-to-speech plugin supporting Piper synthesis & mock fallback | M2 | Plugin Spec / Plan Phase 3 |
| 9 | Ollama Local LLM Plugin | Chat completion & streaming response generation with Ollama & fallback | M2 | Plugin Spec / Plan Phase 3 |
| 10 | Push-to-Talk Activation Plugin | Key press/release event detection for listening state toggling | M2 | Plugin Spec / Plan Phase 4 |
| 11 | Double-Clap Detector Plugin | Audio peak & time interval analysis for hands-free activation | M2 | Plugin Spec / Plan Phase 4 |
| 12 | Face Tracker Vision Plugin | MediaPipe face mesh tracking for user attention telemetry & head pose | M2 | Plugin Spec / Plan Phase 6 |
| 13 | Fullscreen HUD Layout | Borderless transparent Electron window with 3-panel HUD layout | M3 | Frontend Spec / Plan Phase 1,5 |
| 14 | Multi-Ring ARC Reactor Core | Canvas multi-ring visualizer with rotation & pulse state animations | M3 | Frontend Spec / Plan Phase 5 |
| 15 | Waveform Audio Visualizer | Canvas bar/line visualizer reacting to audio levels | M3 | Frontend Spec / Plan Phase 5 |
| 16 | Particle System Engine | Background floating particles with state-dependent density & speed | M3 | Frontend Spec / Plan Phase 5 |
| 17 | Status & Transcript Bars | UI bars for system state, model telemetry, and streaming token display | M3 | Frontend Spec / Plan Phase 5 |
| 18 | Procedural Web Audio SFX | Zero-dependency synthesized sound effects (power-up, chimes, buzz, whirr) | M3 | Frontend Spec / Plan Phase 7 |
| 19 | Settings Overlay Drawer Panel | Slide-out configuration panel for voice, brain, activation, appearance, SFX | M3 | Frontend Spec / Plan Phase 7 |
| 20 | Frontend WebSocket Client | WS Client with auto-reconnect, state syncing, and typed message dispatch | M3 | Frontend Spec / Plan Phase 1,5 |
| 21 | Environment Setup Automation | `scripts/setup.sh` automated venv & package installer | M4 | Tooling Spec / Plan Phase 8 |
| 22 | Development Runner Automation | `scripts/dev.sh` concurrent backend & frontend runner with trap cleanup | M4 | Tooling Spec / Plan Phase 8 |
| 23 | Configuration Defaults | Modular JSON namespaces (`config/`) and unified YAML (`config/default.yaml`) | M4 | Config Spec / Plan Phase 8 |
| 24 | Documentation & Plan Tracking | Comprehensive `README.md` and updated task checkboxes in plan | M4 | Docs Spec / Plan Phase 8 |
| 25 | Comprehensive Test & E2E Validation | All 12 backend pytest suites, TypeScript build, and E2E verification | M5 | Verification Spec / Plan All |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Core Backend & Plugin Architecture | Features 1-5: Base Plugin, PluginManager, Config enhancements, Event loop wiring, core test suites | None | DONE |
| M2 | Pluggable AI & Audio Pipeline | Features 6-12: MicStream, SpeakerOutput, VAD, Whisper STT, Piper TTS, Ollama LLM, PTT, Clap, Face Tracker plugins & test suites | M1 | DONE |
| M3 | Full-Screen HUD Visualizer & Audio SFX | Features 13-20: Electron HUD, ARC Reactor, Waveform, Particles, Status/Transcript bars, SFX Synthesizer, Settings panel, TypeScript build | None | DONE |
| M4 | Project Tooling, Automation & Documentation | Features 21-24: scripts/setup.sh, scripts/dev.sh, config/default.yaml, config JSONs, README.md, task checkboxes in plan | M1, M2, M3 | DONE |
| M5 | E2E Integration & Verification | Feature 25: 100% backend unit test pass (12 suites), frontend clean build, E2E protocol verification | M1, M2, M3, M4 | DONE |

## Interface Contracts

### WebSocket Gateway (Backend ↔ Frontend)
- Endpoint: `ws://localhost:8765`
- Backend -> Frontend Messages:
  - `{"type": "state_change", "data": {"state": "idle"|"listening"|"thinking"|"speaking"|"error", "previous": "..."}}`
  - `{"type": "transcript_stream", "data": {"token": "Hello", "is_final": false}}`
  - `{"type": "transcript_final", "data": {"speaker": "user"|"jarvis", "text": "..."}}`
  - `{"type": "audio_level", "data": {"level": 0.75, "source": "mic"|"tts"}}`
  - `{"type": "face_telemetry", "data": {"detected": true, "attention": true, "head_pose": {"yaw": 0.1, "pitch": -0.05, "roll": 0.0}}}`
  - `{"type": "settings_response", "data": {"settings": {...}}}`
  - `{"type": "config_updated", "data": {"namespace": "...", "key": "...", "value": ...}}`
  - `{"type": "pong", "data": {"timestamp": 1234567890}}`
  - `{"type": "error", "data": {"code": "...", "message": "..."}}`
- Frontend -> Backend Messages:
  - `{"type": "activate"}` / `{"type": "deactivate"}`
  - `{"type": "config_update", "data": {"namespace": "...", "key": "...", "value": ...}}`
  - `{"type": "settings_request"}`
  - `{"type": "ping", "data": {"timestamp": 1234567890}}`

### EventBus Internal Events
- `state_change`: State transition events
- `stt_result`: Transcribed speech from mic
- `llm_request`: Prompt to LLM plugin
- `llm_token`: Streamed token from LLM
- `llm_response`: Complete text response from LLM
- `tts_speak`: Request to synthesize & play speech
- `tts_start` / `tts_done`: Speech playback lifecycle
- `audio_level`: Live mic/speaker volume
- `face_detected` / `face_lost`: Vision tracking events
- `config_change`: Configuration updates

### Plugin Interface Contract
```python
class Plugin(ABC):
    @abstractmethod
    def __init__(self, bus: EventBus, config: Config): ...
    @abstractmethod
    async def start(self) -> None: ...
    @abstractmethod
    async def stop(self) -> None: ...
    @abstractmethod
    async def on_event(self, event: Event) -> None: ...
    @abstractmethod
    def get_schema(self) -> dict: ...
```

## Code Layout
```
/home/pawan/Projects/jarvis-ai/
├── backend/
│   ├── pyproject.toml
│   ├── jarvis/
│   │   ├── __init__.py
│   │   ├── __main__.py
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── bus.py
│   │   │   ├── state.py
│   │   │   └── config.py
│   │   ├── audio/
│   │   │   ├── __init__.py
│   │   │   ├── mic_stream.py
│   │   │   ├── speaker_output.py
│   │   │   └── vad.py
│   │   ├── plugins/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── manager.py
│   │   │   └── builtins/
│   │   │       ├── __init__.py
│   │   │       ├── whisper_local.py
│   │   │       ├── piper_tts.py
│   │   │       ├── ollama_llm.py
│   │   │       ├── push_to_talk.py
│   │   │       ├── clap_detector.py
│   │   │       └── face_tracker.py
│   │   └── ws_server.py
│   └── tests/
│       ├── test_bus.py
│       ├── test_state.py
│       ├── test_config.py
│       ├── test_ws_server.py
│       ├── test_plugin_base.py
│       ├── test_plugin_manager.py
│       ├── test_audio.py
│       ├── test_whisper.py
│       ├── test_piper.py
│       ├── test_ollama.py
│       ├── test_ptt.py
│       ├── test_clap.py
│       └── test_face.py
├── frontend/
│   ├── package.json
│   ├── tsconfig.json
│   ├── src/
│   │   ├── main.ts
│   │   ├── preload.ts
│   │   └── renderer/
│   │       ├── index.html
│   │       ├── core/
│   │       │   ├── app.ts
│   │       │   ├── ws-client.ts
│   │       │   └── types.ts
│   │       ├── hud/
│   │       │   ├── layout.css
│   │       │   ├── arc-reactor.ts
│   │       │   ├── arc-reactor.css
│   │       │   ├── waveform.ts
│   │       │   ├── particles.ts
│   │       │   ├── status-bar.ts
│   │       │   ├── transcript-bar.ts
│   │       │   └── panels/
│   │       │       ├── settings.ts
│   │       │       └── settings.css
│   │       └── sfx/
│   │           └── synthesizer.ts
│   └── dist/
├── config/
│   ├── default.yaml
│   ├── core.json
│   ├── plugins/
│   └── themes/
├── scripts/
│   ├── setup.sh
│   └── dev.sh
├── docs/
│   └── superpowers/
└── README.md
```
