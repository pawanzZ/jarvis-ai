# E2E Test Infra: Jarvis AI

## Test Philosophy
- Opaque-box, requirement-driven verification across all 4 tiers (Feature, Boundary, Combinatorial, Real-World Workload) plus adversarial Tier 5.
- Zero-tolerance for integrity violations, mocking tricks without fallbacks, or bypasses.

## Feature Inventory & Test Coverage Goals
| # | Feature | Scope | Tier 1 (Feature) | Tier 2 (Boundary) | Tier 3 (Cross-Feature) | Tier 4 (Scenario) |
|---|---------|-------|:----------------:|:-----------------:|:----------------------:|:-----------------:|
| 1 | EventBus & Async Loop | Core | >=5 cases | >=5 cases | Event routing | Multi-subscriber |
| 2 | StateMachine & Transitions | Core | >=5 cases | >=5 cases | Illegal transitions | Full lifecycle |
| 3 | Config Store & Persistence | Core | >=5 cases | >=5 cases | Missing keys/files | Live reload |
| 4 | WebSocket Server Gateway | Core | >=5 cases | >=5 cases | Disconnect/reconnect | Streamed tokens |
| 5 | Plugin Manager & Lifecycle | Plugin | >=5 cases | >=5 cases | Duplicate/failed plugins | Hot dynamic reload |
| 6 | Audio & VAD Subsystem | Audio | >=5 cases | >=5 cases | Silence/clipping | Voice thresholding |
| 7 | Whisper Local STT Plugin | AI | >=5 cases | >=5 cases | Empty audio/noise | Audio to text flow |
| 8 | Piper Local TTS Plugin | AI | >=5 cases | >=5 cases | Empty text/long text | Text to speech flow |
| 9 | Ollama Local LLM Plugin | AI | >=5 cases | >=5 cases | Context overflow | Stream token flow |
| 10| Push-to-Talk Plugin | Activation | >=5 cases | >=5 cases | Rapid press/release | PTT to State Machine |
| 11| Clap Detector Plugin | Activation | >=5 cases | >=5 cases | False peaks/ambient noise | Clap to Listening |
| 12| Face Tracker Vision Plugin | Vision | >=5 cases | >=5 cases | Occlusion/lost face | Telemetry broadcast |
| 13| Frontend HUD & Canvas UI | UI | Build + render | Zero crash | State-reactive UI | Fullscreen layout |
| 14| Web Audio SFX Synthesizer | Audio | Procedural audio | Zero missing assets | State change sounds | AudioContext unlock |
| 15| Automation Scripts & Tooling | Tooling | Executable | Trap signals | Concurrent run | Setup & launch |

## Test Architecture
- Backend: `pytest` runner executing 12 test modules in `backend/tests/`.
- Frontend: `npm run build` validating strict TypeScript compilation.
- Integration: WebSocket ping/pong, activate/deactivate commands, config updating.
