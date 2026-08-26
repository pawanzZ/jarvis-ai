# Jarvis AI — Voice-Interactive Desktop Agent

**Date:** 2026-08-26
**Classification:** Architectural — New project
**Status:** Draft

---

## Overview

A voice-first, always-on desktop AI assistant inspired by JARVIS from Iron Man. Features a full-screen HUD with ARC reactor aesthetics, face/eye tracking, multiple activation methods, and pluggable AI backends. Built as a hybrid system: Python backend for ML workloads, Electron frontend for the visual experience.

## Goals

1. Voice-first interaction — speak naturally, get responses spoken back
2. Always-on presence — HUD overlay with living, breathing AI core visualization
3. Pluggable backends — swap STT, TTS, LLM, activation methods via config/plugins
4. Free by default — local-first with optional cloud fallback
5. Nerdy aesthetic — Iron Man HUD, ARC reactor imagery, sophisticated animations

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

Center-stage SVG/Three.js animation:

- **Outer ring**: rotating segmented arcs (reactor housing)
- **Middle ring**: pulsing concentric circles with energy lines
- **Inner core**: bright glow, intensity scales with activity

**States:**
- **Idle**: dim blue, slow rotation
- **Listening**: ripple waves outward, cyan shift
- **Thinking**: spinning particles, amber glow
- **Speaking**: waveform rings emanating, bright white/blue
- **Boot**: energy burst, full brightness surge

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
jarvis/config/
├── core.json
├── plugins/
│   ├── stt.json
│   ├── tts.json
│   ├── llm.json
│   └── activation.json
└── themes/
    ├── arc-reactor.json
    └── custom.json
```

### Settings UI

Voice command: *"Open settings"* → panel slides in from right.

| Section | Controls |
|---------|----------|
| **Voice** | STT plugin, TTS voice, mic device, volume |
| **AI Brain** | LLM plugin, model dropdown, API keys (encrypted), temperature |
| **Activation** | Toggle methods, hotkey picker, wake word trainer, clap sensitivity |
| **Appearance** | Theme picker, color accents, scan lines, particle density |
| **Face/Eye** | Camera device, gaze tracking, helmet boot toggle |
| **Sounds** | Volume, per-SFX toggle, custom sound upload |
| **Developer** | Debug logs, WebSocket inspector, plugin hot-reload |

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
│   │   ├── __main__.py
│   │   ├── core/
│   │   │   ├── bus.py          # Event bus
│   │   │   ├── state.py        # State machine
│   │   │   └── config.py
│   │   ├── plugins/
│   │   │   ├── base.py         # Plugin interface
│   │   │   ├── manager.py      # Plugin loader
│   │   │   ├── stt/            # Whisper plugins
│   │   │   ├── tts/            # Piper, edge-tts
│   │   │   ├── llm/            # Ollama, OpenAI, etc.
│   │   │   ├── activation/     # Wake word, clap, PTT, gesture
│   │   │   └── vision/         # Face tracker
│   │   ├── audio/
│   │   │   ├── mic_stream.py
│   │   │   ├── speaker_output.py
│   │   │   └── vad.py
│   │   └── ws_server.py
│   └── tests/
│
├── frontend/                   # Electron + TypeScript
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
│   │       │   └── state-manager.ts
│   │       ├── hud/
│   │       │   ├── arc-reactor.ts
│   │       │   ├── waveform.ts
│   │       │   ├── particles.ts
│   │       │   ├── helmet-boot.ts
│   │       │   ├── gaze-parallax.ts
│   │       │   └── panels/
│   │       │       ├── chat.ts
│   │       │       ├── settings.ts
│   │       │       └── status.ts
│   │       ├── sfx/
│   │       │   └── synthesizer.ts
│   │       └── themes/
│   │           └── loader.ts
│   └── tests/
│
├── config/                     # Defaults
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
{"type": "state_change", "state": "listening"}
{"type": "transcript_partial", "text": "Hey Jarvis what's the"}
{"type": "transcript_final", "text": "Hey Jarvis, what's the weather?"}
{"type": "llm_token", "token": "The"}
{"type": "llm_token", "token": " temperature"}
{"type": "response_complete", "full_text": "The temperature is 72°F."}
{"type": "audio_level", "level": 0.73}
{"type": "face_data", "gaze": [0.4, 0.6], "pose": {"pitch": 5, "yaw": -2}}
{"type": "plugin_loaded", "name": "whisper_local", "type": "stt"}
{"type": "error", "message": "Ollama connection refused"}
```

### Frontend → Backend

```json
{"type": "command", "action": "activate"}
{"type": "command", "action": "deactivate"}
{"type": "config_update", "plugin": "llm", "key": "model", "value": "llama3"}
{"type": "settings_request"}
{"type": "ping"}
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

- **Unit tests**: plugin interface, event bus, config loader
- **Integration tests**: voice pipeline end-to-end (mock audio)
- **E2E tests**: WebSocket message flow between Python and Electron
- **Manual tests**: HUD animations, sound sync, activation methods
- **Performance tests**: memory profiling, CPU usage over time

---

## Implementation Order

1. **Phase 1 — Skeleton**: Electron app + Python WebSocket server + basic HUD
2. **Phase 2 — Plugin system**: Plugin interface, manager, config loader
3. **Phase 3 — Voice core**: STT + TTS + LLM plugins (Ollama + Piper + Whisper)
4. **Phase 4 — Activation**: All four methods (PTT, hotword, clap, gesture)
5. **Phase 5 — HUD polish**: ARC reactor, particles, waveforms, themes
6. **Phase 6 — Face tracking**: MediaPipe integration, gaze, helmet boot
7. **Phase 7 — SFX & settings**: Sound synthesis, settings panel, theme system
8. **Phase 8 — Packaging**: electron-builder, setup script, README
