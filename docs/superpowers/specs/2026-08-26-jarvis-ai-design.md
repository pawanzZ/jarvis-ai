# Jarvis AI — Voice-Interactive Desktop Agent

**Date:** 2026-08-26
**Classification:** Architectural — New project
**Status:** Implemented (v1 complete) — reflects final shipped architecture

---

## Overview

A voice-first, always-on desktop AI assistant inspired by JARVIS from Iron Man. Features a full-screen HUD with ARC reactor aesthetics, face/eye tracking, multiple activation methods, and pluggable AI backends. Built as a hybrid system: Python backend for ML workloads, Electron frontend for the visual experience.

## Goals

1. Voice-first interaction — speak naturally, get responses spoken back
2. Always-on presence — HUD overlay with living, breathing AI core visualization
3. Pluggable backends — swap STT, TTS, LLM, activation methods via config/plugins
4. Free by default — local-first with optional cloud fallback
5. Nerdy aesthetic — Iron Man HUD, ARC reactor imagery, sophisticated animations

## Delivered Capabilities (v1)

Beyond the core roadmap, the following were implemented and shipped:

- **Real-time hardware telemetry** — CPU, GPU, RAM, Disk, Network rates, OS/kernel/hostname detection, system & session uptime (screen time), streamed over WebSocket to a System Monitor HUD panel.
- **Weather & location** — live conditions fetched from `wttr.in` (cached with network fallback), surfaced in the Status Bar.
- **3D Particle Orb core visualizer** — a second "core" variant alongside the ARC Reactor: a 1,350-particle Fibonacci-distributed 3D point cloud with perspective projection, state-driven color, and a rigid sphere surface with only a handful of randomly-pulsing dots. Switch via the `V` key, on-screen buttons, or the settings panel; preference persists to `localStorage` and syncs to backend config.
- **Fully wired real audio pipeline** — actual microphone streaming (sounddevice) with adaptive VAD (noise-floor tracking, hangover windows, pre-buffering to avoid utterance clipping), live Whisper STT transcription, streaming Ollama LLM tokens, and neural TTS playback with smooth turn completion.
- **Runtime settings persistence** — slide-out settings drawer with radio/range/select controls that push `config_update`/`settings_save` messages over WebSocket; the backend persists JSON namespaces per plugin/core.
- **Live network state sync** — `connection`/`latency` events, `settings_response`, `config_updated` broadcasting, and typed in/out message protocol in the shared frontend type module.

## Non-Goals (v1)

- Mobile companion app
- Multi-user support
- Cloud sync / account system
- Voice cloning (v2 feature)

---

## Architecture

### Hybrid Model

```
┌─────────────────────────────────────────────┐
│              Electron (HUD)                 │
│  ┌─────────┐ ┌──────────┐ ┌─────────────┐  │
│  │ Canvas  │ │ Settings │ │  Wave Anim  │  │
│  │ Renderer│ │  Panel   │ │  Engine     │  │
│  └────┬────┘ └──────────┘ └─────────────┘  │
│       │ WebSocket (localhost:8765)          │
└───────┼─────────────────────────────────────┘
        │
┌───────┼─────────────────────────────────────┐
│       │        Python Backend               │
│  ┌────┴────┐ ┌──────────┐ ┌──────────────┐ │
│  │  Core   │ │ Plugin   │ │  State       │ │
│  │  Bus    │ │ Manager  │ │  Machine     │ │
│  └────┬────┘ └──────────┘ └──────────────┘ │
│       │                                     │
│  ┌────┴────────────────────────────────┐    │
│  │         Plugin Layer                │    │
│  │  ┌─────┐ ┌─────┐ ┌─────┐ ┌──────┐ │    │
│  │  │ STT │ │ TTS │ │ LLM │ │ Wake │ │    │
│  │  └─────┘ └─────┘ └─────┘ └──────┘ │    │
│  └─────────────────────────────────────┘    │
└─────────────────────────────────────────────┘
```

- **Python backend** handles all ML/AI: STT, TTS, LLM, wake word, face tracking
- **Electron frontend** handles all visualization: HUD, animations, SFX, settings UI
- **WebSocket** on localhost:8765 connects them. JSON message protocol.

---

## Plugin System

### Interface

```python
class Plugin(ABC):
    name: str
    plugin_type: PluginType  # STT | TTS | LLM | WAKE_WORD | ACTIVATION | VISION

    @abstractmethod
    async def start(self, config: dict) -> None: ...

    @abstractmethod
    async def stop(self) -> None: ...

    @abstractmethod
    async def on_event(self, event: Event) -> Optional[Event]: ...
```

### Plugin Types (v1)

| Type | Plugins | Notes |
|------|---------|-------|
| **STT** | Whisper.cpp (local), faster-whisper | Free, offline |
| **TTS** | Piper (local), edge-tts (free cloud) | Piper = British butler default |
| **LLM** | Ollama (local), OpenAI, Anthropic, Gemini | Local default, cloud fallback |
| **WAKE_WORD** | openWakeWord, Porcupine (free tier) | Custom trainable word |
| **ACTIVATION** | Push-to-talk, Hotkey, Clap detector, Gesture (MediaPipe) | All four supported |
| **VISION** | Face tracker (MediaPipe Face Mesh) | Gaze, head pose, blink |

### Plugin Discovery

Scans `jarvis/plugins/` directory. User drops `.py` file → appears in Settings → enable/disable toggle. Hot-reload via file watcher, no restart needed.

### Plugin Config

Each plugin reads `jarvis/config/plugins/{plugin_name}.json`. Settings UI auto-generates controls from plugin schema.

---

## Voice Pipeline

### Flow

```
MIC → [Activation Gate] → [VAD] → [STT] → [LLM] → [TTS] → SPEAKER
         │                                      │
         ▼                                      ▼
   ┌────────────┐                         ┌──────────┐
   │ Wake Word  │                         │ Streaming│
   │ Clap Det.  │                         │ Response │
   │ Push-to-talk│                        └──────────┘
   │ Gesture    │
   └────────────┘
```

### Activation Gate

Monitors audio continuously (~2% CPU). Opens when any method fires:

- **Hotword**: openWakeWord — "Hey Jarvis" (custom trainable)
- **Clap**: energy spike + pattern matcher (two sharp peaks within 300ms)
- **Push-to-talk**: configurable key hold (default: Space)
- **Gesture**: MediaPipe hand tracking — raised open palm

### State Machine

```
IDLE → LISTENING → THINKING → SPEAKING → IDLE
       (waveform)  (spinner)  (waveform)  (pulse)
```

- **Barge-in**: user speaking during TTS → gate re-opens immediately, agent stops and listens
- **VAD**: Silero VAD (free, local) detects speech start/end precisely
- **Streaming**: partial transcripts appear in real-time as user speaks

### Timing Targets

- Wake word detection: < 500ms
- STT first token: < 300ms
- LLM first token: < 1s (local), < 2s (cloud)
- TTS first audio: < 200ms

---

## HUD Visualizer

### Layout

```
┌─────────────────────────────────────────────┐
│ STATUS BAR                                  │
│ [Model: llama3] [Mode: Voice] [⚡ Active]   │
├─────────────────────────────────────────────┤
│         ┌───────────────────┐               │
│  LEFT   │   ARC REACTOR     │   RIGHT       │
│  PANEL  │   CORE            │   PANEL       │
│  Chat   │   (3D pulsing     │   System      │
│  History│    reactor)       │   Stats       │
│  Logs   │                   │   Tools       │
│         └───────────────────┘               │
├─────────────────────────────────────────────┤
│ TRANSCRIPT BAR                              │
└─────────────────────────────────────────────┘
```

### ARC Reactor Core

Center-stage Canvas/CSS animation:

- **Outer ring**: rotating segmented arcs (reactor housing)
- **Middle ring**: pulsing concentric circles with energy lines
- **Inner core**: bright glow, intensity scales with audio level & activity

**States:**
- **Idle**: dim blue, slow rotation
- **Listening**: ripple waves outward, cyan shift
- **Thinking**: spinning particles, amber glow
- **Speaking**: waveform rings emanating, bright white/blue
- **Boot**: energy burst, full brightness surge

### Particle Orb Core (Alternate Visualizer)

A switchable 3D particle orb rendered on Canvas:

- ~1,350 particles distributed on a unit sphere via Fibonacci lattice
- 3D rotation + perspective projection
- Rigid sphere surface that never changes shape
- Only a small random subset of dots pulse gently in place
- State-reactive color palette (idle/listening/thinking/speaking/error)
- Switch between ARC Reactor and Orb via `V` key, buttons, or settings; persisted

### Visual Elements

1. **Energy Arcs**: SVG lines from core to panel edges. Faint, pulsing. Intensity = LLM load.
2. **HUD Frame**: border styled as reactor housing. Corner brackets, bolt details, glowing seams.
3. **Particles**: triangular/arrow shapes (Iron Man HUD markers). Drift, cluster, scatter on state changes.
4. **Scan Lines**: subtle CRT overlay + grid pattern. Toggleable.
5. **Helmet Boot Animation**: on wake, faint helmet frame SVG fades in around detected face position, then dissolves as HUD expands outward.

### Eye/Face Detection

Using MediaPipe Face Mesh (468 landmarks, runs locally):

- **Gaze Tracking**: panels brighten when looked at, core follows gaze (parallax)
- **Head Pose**: pitch/yaw/roll for gestures (tilt=dismiss, lean=zoom, shake=no)
- **Blink Detection**: single blink=acknowledge, double blink=toggle, long blink=sleep
- **Helmet Effect**: HUD "boots up" from face position like Iron Man mask locking on

Privacy: camera never leaves machine. No images stored/transmitted. Toggleable.

### Color Scheme

```
Background:    #0a0a0f
Idle:          #1a3a5c (dim blue)
Listening:     #00d4ff (cyan)
Thinking:      #ff9500 (amber)
Speaking:      #ffffff (white/blue)
Error:         #ff3b30 (red)
```

All configurable via CSS variables / theme JSON.

---

## Sound Effects

| Event | Sound | Method |
|-------|-------|--------|
| Wake/Activation | Arc reactor power-up + repulsor charge | Web Audio synthesis |
| Listening start | Subtle reactor hum (looping) | Low-freq oscillator |
| Thinking | Processing whirr | Pitched click sequence |
| Speaking start | Soft boot chime | Single clean tone |
| Error | Warning buzz | Low descending tone |
| Sleep/Deactivate | Power-down fade | Reverse of wake |

All generated via Web Audio API (no external files). User can replace with custom `.wav` files via config.

---

## Settings System

### Config Structure

```
config/
├── default.yaml             # Master reference configuration
├── core.json                # Host, port, audio sample/chunk, log level, theme
├── voice.json               # STT/TTS plugin selection, voice, rate, sensitivity, volume
├── brain.json               # LLM plugin, model, temperature, max tokens, system prompt
├── activation.json          # Wake word, PTT (key/mode), clap, gesture toggles
├── appearance.json          # Theme, core variant, particle density, CRTs, glow, ui scale
├── vision.json              # Camera index, face tracking / gaze / helmet boot toggles
├── sfx.json                 # Master volume + per-SFX enable toggles
├── plugins/
│   ├── whisper_local.json   # STT model
│   ├── piper_tts.json       # TTS voice
│   ├── ollama_llm.json      # LLM model & base URL
│   ├── push_to_talk.json    # Keybind & mode
│   ├── clap_detector.json   # Threshold & window
│   └── face_tracker.json    # Camera & confidence
└── themes/
    ├── arc-reactor.json
    └── iron_man.json
```

### Settings UI

Voice command: *"Open settings"* → panel slides in from right.

| Section | Controls |
|---------|----------|
| **Voice** | STT plugin, TTS voice, mic device, volume, rate |
| **AI Brain** | LLM plugin, model dropdown, temperature, max tokens, system prompt |
| **Activation** | Toggle methods (wake word, PTT, clap), hotkey picker (Space), clap sensitivity |
| **Appearance** | Theme picker, core visualizer variant (ARC Reactor / Particle Orb), particle density, CRT scanlines, glow, ui scale |
| **Face/Eye** | Camera device, gaze tracking, helmet boot toggle |
| **Sounds** | Volume, per-SFX toggle (power-up/chimes/hum/error/thinking) |
| **Developer** | Debug logs, WebSocket inspector, plugin hot-reload |

Settings changes are persisted by the backend to the matching JSON namespace and broadcast back (`config_updated`) so all clients stay in sync.

### Themes

JSON defines colors, animation speeds, SVG assets. Ship 3:
- **Arc Reactor** (default) — blue/white, Iron Man
- **Matrix** — green/black, cascading code
- **Synthwave** — pink/purple, retro neon

---

## Project Structure

```
jarvis-ai/
├── backend/                    # Python
│   ├── pyproject.toml
│   ├── jarvis/
│   │   ├── __main__.py         # Orchestrator: plugins, audio worker, telemetry
│   │   ├── core/
│   │   │   ├── bus.py          # Event bus
│   │   │   ├── state.py        # State machine
│   │   │   └── config.py       # JSON/YAML namespace store
│   │   ├── plugins/
│   │   │   ├── base.py         # Plugin interface
│   │   │   ├── manager.py      # Plugin loader & lifecycle
│   │   │   └── builtins/
│   │   │       ├── whisper_local.py   # STT
│   │   │       ├── piper_tts.py       # TTS
│   │   │       ├── ollama_llm.py      # LLM
│   │   │       ├── push_to_talk.py    # Activation
│   │   │       ├── clap_detector.py   # Activation
│   │   │       └── face_tracker.py    # Vision
│   │   ├── audio/
│   │   │   ├── mic_stream.py
│   │   │   ├── speaker_output.py
│   │   │   └── vad.py          # Noise-adaptive VAD
│   │   ├── system/
│   │   │   └── monitor.py      # Hardware/OS/network/weather telemetry
│   │   └── ws_server.py        # WebSocket gateway + settings/telemetry handlers
│   └── tests/                  # Unit + adversarial suites
│
├── frontend/                   # Electron + TypeScript
│   ├── package.json
│   ├── tsconfig.json
│   ├── scripts/                # copy-assets, test-modules
│   └── src/
│       ├── main.ts
│       ├── preload.ts
│       └── renderer/
│           ├── index.html
│           ├── core/
│           │   ├── app.ts             # Master coordinator
│           │   ├── types.ts           # Typed WS protocol
│           │   └── ws-client.ts
│           ├── hud/
│           │   ├── arc-reactor.ts/.css
│           │   ├── particle-orb.ts/.css
│           │   ├── waveform.ts
│           │   ├── particles.ts
│           │   ├── system-monitor.ts
│           │   ├── status-bar.ts
│           │   ├── transcript-bar.ts
│           │   └── panels/
│           │       ├── settings.ts/.css
│           │       └── ...
│           └── sfx/
│               └── synthesizer.ts
│
├── config/                     # Defaults (core, voice, brain, activation,
│                              #   appearance, vision, sfx, themes, plugins/)
├── docs/superpowers/           # Plan & design specification
├── scripts/
│   ├── setup.sh
│   └── dev.sh
└── README.md
```

---

## WebSocket Protocol

JSON messages over localhost:8765.

### Backend → Frontend

```json
{"type": "state_change", "state": "listening", "data": {"state": "listening", "previous": "idle"}}
{"type": "transcript_partial", "text": "Hey Jarvis what's the"}
{"type": "transcript_final", "text": "Hey Jarvis, what's the weather?", "speaker": "user"}
{"type": "transcript_stream", "token": "The"}
{"type": "llm_token", "token": "The"}
{"type": "llm_token", "token": " temperature"}
{"type": "response_complete", "full_text": "The temperature is 72°F."}
{"type": "audio_level", "level": 0.73, "data": {"level": 0.73, "source": "mic"}}
{"type": "face_data", "gaze": [0.4, 0.6], "pose": {"pitch": 5, "yaw": -2}, "attention": true}
{"type": "face_telemetry", ...}
{"type": "plugin_loaded", "name": "whisper_local", "type": "stt"}
{"type": "system_telemetry", "data": {"cpu": {...}, "gpu": {...}, "memory": {...}, "disk": {...}, "network": {...}, "uptime": {...}, "os": {...}, "weather": {...}}}
{"type": "weather_telemetry", "data": {"city": "...", "temp_c": 24, "condition": "..."}}
{"type": "settings_response", "settings": {"voice": {...}, "brain": {...}, "activation": {...}, "appearance": {...}, "vision": {...}, "sfx": {...}}}
{"type": "config_updated", "namespace": "appearance", "key": "core_variant", "value": "particle_orb"}
{"type": "connection", "connected": true}
{"type": "latency", "latencyMs": 12}
{"type": "error", "message": "Ollama connection refused"}
```

### Frontend → Backend

```json
{"type": "activate"}  or  {"type": "command", "action": "activate"}
{"type": "deactivate"}  or  {"type": "command", "action": "deactivate"}
{"type": "config_update", "plugin": "llm", "key": "model", "value": "llama3"}
{"type": "settings_save", "settings": {"voice": {...}, ...}}
{"type": "settings_request"}
{"type": "telemetry_request"}
{"type": "weather_request"}
{"type": "ping", "data": {"timestamp": 1234}}
```

---

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Ollama not running | Prompt in HUD: "Local AI offline. Start Ollama or switch to cloud?" |
| Mic not available | HUD shows mic-off icon, text-only mode enabled |
| Camera denied | Face tracking disabled, HUD works without parallax |
| Plugin crash | Plugin auto-restarts once. If fails again, disabled with notification |
| WebSocket disconnect | Backend auto-reconnects. HUD shows "Reconnecting..." overlay |
| TTS failure | Response shown as text only, error sound plays |

---

## Performance Targets

| Metric | Target |
|--------|--------|
| RAM usage (idle) | < 300MB |
| RAM usage (active) | < 600MB |
| CPU (idle, face tracking off) | < 5% |
| CPU (active, face tracking on) | < 20% |
| HUD FPS | 60fps consistent |
| Cold start | < 5s to interactive |

---

## Testing Strategy

- **Unit tests**: plugin interface, event bus, config loader, system monitor, all built-in plugins
- **Adversarial tests**: `backend/tests/adversarial/` — malformed WebSocket payloads, error routing, plugin manager isolation, config edge cases
- **Integration tests**: voice pipeline end-to-end (mock audio)
- **E2E tests**: WebSocket message flow between Python and Electron
- **Manual tests**: HUD animations, sound sync, activation methods
- **Performance tests**: memory profiling, CPU usage over time

## Implementation Order

1. **Phase 1 — Skeleton**: Electron app + Python WebSocket server + basic HUD
2. **Phase 2 — Plugin system**: Plugin interface, manager, config loader
3. **Phase 3 — Voice core**: STT + TTS + LLM plugins (Ollama + Piper + Whisper)
4. **Phase 4 — Activation**: PTT + double-clap detector
5. **Phase 5 — HUD polish**: ARC reactor, particles, waveform, SFX synthesizer
6. **Phase 6 — Face tracking**: MediaPipe integration, gaze telemetry
7. **Phase 7 — SFX & settings**: Sound synthesis, settings panel
8. **Phase 8 — Packaging**: setup script, dev script, README

**Post-planty extensions (shipped):** real wired audio pipeline + adaptive VAD, system telemetry HUD, weather & location, 3D Particle Orb core variant, config persistence/sync, adversarial test suites.
