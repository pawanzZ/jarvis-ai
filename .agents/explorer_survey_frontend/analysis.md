# Frontend & HUD Architectural Survey Report — Jarvis AI

**Date:** 2026-08-27  
**Explorer:** Frontend & HUD Explorer  
**Scope:** Electron HUD Visualizer, UI Architecture, Canvas Renderers, Procedural Audio SFX, WebSocket State Synchronization, TypeScript Configuration  
**Target Specification:** `docs/superpowers/specs/2026-08-26-jarvis-ai-design.md`  
**Target Roadmap:** `docs/superpowers/plans/2026-08-26-jarvis-ai-implementation.md` (Tasks 2, 4, 5, 14, 15, 16, 18, 19)

---

## 1. Executive Summary

This survey provides a comprehensive architectural and codebase analysis for the **Jarvis AI Frontend & HUD Visualizer (Requirement R3)**. The frontend delivers an immersive, full-screen, Iron Man-inspired desktop interface running inside Electron 30+ / TypeScript, with real-time state synchronization to the Python backend via WebSocket on `ws://localhost:8765`.

The frontend visualizes AI states through a multi-ring ARC reactor core, audio waveform visualizer, dynamic particle background system, live streaming transcript bar, status bar, glassmorphism settings overlay, and a zero-dependency Web Audio API procedural sound synthesizer.

---

## 2. Current Workspace State vs. Required Architecture

### 2.1 Existing Files in `frontend/`

| File Path | Status | Analysis |
|---|---|---|
| `frontend/package.json` | **Exists** | Contains `"name": "jarvis-ai"`, scripts (`build: "tsc"`, `dev`, `start`), `electron: ^44.0.0`, `typescript: ^5.4.0`. |
| `frontend/tsconfig.json` | **Exists** | Configured with `ES2022`, `CommonJS` module target, `DOM` + `ES2022` libs, `outDir: dist`, `strict: true`. |
| `frontend/src/main.ts` | **Exists (Skeleton)** | Launches full-screen borderless window (`width: 1920, height: 1080, frame: false, transparent: true, contextIsolation: true, nodeIntegration: false`). |
| `frontend/src/preload.ts` | **Exists (Skeleton)** | Exposes `window.jarvis.platform` via `contextBridge`. |
| `frontend/src/renderer/index.html` | **Exists (Minimal)** | Minimal HTML with `#status-bar`, `#main-area`, `#transcript-bar`. Missing HUD stylesheets, canvas elements, reactor containers, and settings markup. |
| `frontend/src/renderer/core/app.ts` | **Exists (Minimal)** | Listens to `state_change` and `pong` events. Needs expansion to orchestrate all visualizer subsystems, transcript streaming, and audio SFX. |
| `frontend/src/renderer/core/ws-client.ts` | **Exists (Basic)** | Basic browser WebSocket client with event subscription and exponential backoff reconnection. |

### 2.2 Missing Files & Modules to Create (R3 Scope)

```
frontend/src/
├── main.ts                          [Enhance: shortcut handling / window management]
├── preload.ts                       [Enhance: IPC for window controls]
└── renderer/
    ├── index.html                   [Enhance: 3-panel layout, canvas layers, settings modal]
    ├── core/
    │   ├── app.ts                   [Enhance: Master orchestrator & lifecycle manager]
    │   ├── ws-client.ts             [Enhance: Complete protocol typing & command methods]
    │   └── types.ts                 [CREATE: TypeScript interface definitions for all WS messages & UI state]
    ├── hud/
    │   ├── layout.css               [CREATE: HUD grid layout, color tokens, glowing borders, typography]
    │   ├── arc-reactor.ts           [CREATE: Multi-ring ARC reactor controller & state visualizer]
    │   ├── arc-reactor.css          [CREATE: Concentric ring keyframe rotations & glowing core animations]
    │   ├── waveform.ts              [CREATE: Canvas audio amplitude visualizer (64 gradient bars)]
    │   ├── particles.ts             [CREATE: Canvas Iron Man HUD triangular particle system]
    │   ├── status-bar.ts            [CREATE: Model/mode/state indicator controller]
    │   ├── transcript-bar.ts        [CREATE: Real-time partial transcript & LLM streaming token bar]
    │   └── panels/
    │       ├── settings.ts          [CREATE: Configuration drawer/overlay controller]
    │       ├── settings.css         [CREATE: Glassmorphism styling for settings panel & form controls]
    │       └── chat.ts              [OPTIONAL/CREATE: Collapsible conversation history log]
    └── sfx/
        └── synthesizer.ts           [CREATE: Procedural Web Audio API sound effect generator]
```

---

## 3. Subsystem Architecture & Detailed Specifications

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Electron Main Process                              │
│  (Window creation: 1920x1080, Fullscreen, Frameless, Transparent, IPC)      │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Preload Bridge
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                    Electron Renderer Process (DOM & Canvas)                 │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                              JarvisApp                                │  │
│  │                        (Master Orchestrator)                          │  │
│  └──────┬──────────────┬──────────────┬──────────────┬──────────────┬────┘  │
│         │              │              │              │              │       │
│  ┌──────▼──────┐┌──────▼──────┐┌──────▼──────┐┌──────▼──────┐┌──────▼────┐  │
│  │   WSClient  ││  ArcReactor ││   Waveform  ││  Particles  ││    SFX    │  │
│  │  (ws:8765)  ││ (Ring Core) ││   (Canvas)  ││   (Canvas)  ││(WebAudio)│  │
│  └──────┬──────┘└─────────────┘└─────────────┘└─────────────┘└───────────┘  │
│         │                                                                   │
│  ┌──────┴────────────────────────────────────────────────────────────────┐  │
│  │                         HUD UI Components                             │  │
│  │  ┌──────────────┐  ┌────────────────────────┐  ┌───────────────────┐  │  │
│  │  │  Status Bar  │  │ Streaming Transcript   │  │  Settings Panel   │  │  │
│  │  └──────────────┘  └────────────────────────┘  └───────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 3.1 Electron Main & Preload Architecture

- **Main Process (`frontend/src/main.ts`)**:
  - Fullscreen frameless window with `transparent: true` for HUD overlays.
  - Secure renderer configuration: `contextIsolation: true`, `nodeIntegration: false`, `sandbox: true`.
  - Handles window lifecycle events (`window-all-closed`, `activate`).
  - Key bindings: Escape key to toggle fullscreen/exit or minimize window.

- **Preload Bridge (`frontend/src/preload.ts`)**:
  - Exposes minimal, typed API via `contextBridge.exposeInMainWorld("jarvis", { ... })`:
    - `platform: string`
    - `minimizeWindow(): void`
    - `toggleFullscreen(): void`
    - `quitApp(): void`

- **Renderer Module Resolution Note**:
  - Because `tsconfig.json` compiles to CommonJS by default, the renderer should ensure browser-compatible execution (e.g. bundling via `tsc` with ES modules `<script type="module">` or bundled scripts) so `require` and `exports` are properly handled in Chromium without Node integration.

---

### 3.2 Full-Screen HUD Layout & Theme Engine

#### Layout Structure (`frontend/src/renderer/index.html` & `layout.css`):
- **Top Status Bar (`#status-bar`)**: `height: 40px`, horizontal flexbox. Displays:
  - Active AI Model (e.g., `Model: llama3 / gpt-4o`)
  - Interaction Mode (e.g., `Mode: Voice / PTT`)
  - State Badge with glowing indicator dot (`● Idle`, `● Listening`, `● Thinking`, `● Speaking`, `● Error`)
  - Connection indicator (`⚡ Online` / `⚠ Reconnecting`)
- **Main Area (`#main-area`)**: 3-column CSS Grid (`1fr 2fr 1fr`):
  - **Left Panel (`#left-panel`)**: Chat history, command transcript history, collapsible diagnostic logs.
  - **Center Viewport (`#center-area`)**:
    - `#particle-canvas`: Full-bleed background canvas.
    - `#core-container`: Centered multi-ring ARC reactor.
    - `#waveform-canvas`: Lower/overlaid audio visualizer canvas.
  - **Right Panel (`#right-panel`)**: Live system metrics, active plugin badges, audio input level gauge, face tracking telemetry widget.
- **Bottom Transcript Bar (`#transcript-bar`)**: `height: 60px`, large typography (`18px`), displays:
  - Real-time partial speech recognition (`transcript_partial`) in cyan italic.
  - Final recognized user prompt (`transcript_final`) in bold white.
  - Streaming LLM response tokens (`llm_token`) with typing cursor pulse.
- **Settings Overlay (`#settings-panel`)**: Sliding right-hand glassmorphism drawer.

#### Color Tokens & Theme Definition:
```css
:root {
  --bg-primary: #0a0a0f;
  --bg-panel: rgba(10, 15, 30, 0.85);
  --border-glow: rgba(0, 180, 255, 0.3);
  --text-primary: #e0e8f0;
  --text-secondary: #6a7a8a;
  
  /* State Colors */
  --state-idle: #1a3a5c;
  --state-listening: #00d4ff;
  --state-thinking: #ff9500;
  --state-speaking: #ffffff;
  --state-error: #ff3b30;

  /* Accents */
  --accent-blue: #00b4ff;
  --accent-cyan: #00d4ff;
  --accent-amber: #ff9500;
  --accent-white: #ffffff;
  --accent-red: #ff3b30;
}
```

---

### 3.3 Multi-Ring ARC Reactor Core (`arc-reactor.ts` & `arc-reactor.css`)

The center-stage visualizer represents Jarvis's living core:
- **Geometry**:
  - Outer Ring (`.reactor-outer`): 300px diameter, segmented circular border, rotates clockwise (20s period).
  - Middle Ring (`.reactor-middle`): 210px diameter (70%), cyan border with tick accents, rotates counter-clockwise (15s period).
  - Inner Ring (`.reactor-inner`): 120px diameter (40%), white/cyan border, rotates clockwise (10s period).
  - Core (`.reactor-core`): 60px diameter (20%), radial gradient with dual-layer intense glow (`box-shadow: 0 0 30px, 0 0 60px`).
- **State-Driven Dynamics**:
  - `IDLE`: Dim blue glow, gentle 2s breathing pulse (`scale(1.0)` -> `scale(1.1)`), slow rotation.
  - `LISTENING`: Cyan shift (`#00d4ff`), rapid 0.5s breathing pulse, responsive ripple rings.
  - `THINKING`: Amber/gold shift (`#ff9500`), fast 1s spinning orbit, intense central concentration.
  - `SPEAKING`: Bright white/blue shift (`#ffffff` / `#00b4ff`), 0.3s voice-responsive pulse, expanding energy rings.
  - `ERROR`: Red alert pulse (`#ff3b30`), erratic flash animation.

---

### 3.4 Waveform Audio Visualizer (`waveform.ts`)

- **Canvas Rendering**: 64 vertical bars rendered across dynamic width.
- **Audio Modulation**: Ingests `audio_level` float values `[0.0, 1.0]` broadcast from backend.
- **Visual Styling**:
  - Linear gradient: `rgba(0, 180, 255, 0.8)` at top/bottom -> `rgba(0, 212, 255, 1)` at center.
  - Mirrored or vertical center-aligned bars: `y = (height - barHeight) / 2`.
  - Smooth exponential decay filter to prevent jagged visual artifacts during speech pauses.

---

### 3.5 Dynamic Particle Background System (`particles.ts`)

- **Canvas Particle Engine**: High-performance 2D canvas simulation updating at 60 FPS.
- **HUD Marker Geometry**: Particles drawn as Iron Man HUD triangular chevron markers (`moveTo(x, y)`, `lineTo(x + size*3, y)`, `lineTo(x + size*1.5, y - size*2)`).
- **Dynamic Density by State**:
  - `idle`: 30 particles (slow ambient drift)
  - `listening`: 60 particles (accelerated drift towards center)
  - `thinking`: 80 particles (swirling vortex pattern)
  - `speaking`: 100 particles (radiating outward in acoustic shockwaves)
  - `error`: jittering red particles
- **Particle Lifecycles**: Position calculation, speed damping, boundary recycling, alpha fading (`Math.min(alpha, life / 50)`).

---

### 3.6 Procedural Web Audio API SFX Synthesizer (`synthesizer.ts`)

**Zero External Audio Files**: Synthesizes all acoustic feedback mathematically using the Web Audio API.

| Sound Effect | Trigger Event | Synthesis Parameters |
|---|---|---|
| **Power-Up / Wake (`powerUp`)** | Activation / `activate` | Sawtooth wave sweeping 100Hz -> 800Hz in 300ms, exponential gain envelope (0.5 -> 0.01 in 500ms). |
| **Power-Down (`powerDown`)** | Deactivation / `deactivate` | Sawtooth wave sweeping 800Hz -> 100Hz in 500ms, exponential decay. |
| **Chime (`chime`)** | Speaking start / acknowledgment | Pure sine wave at 880Hz (A5) decaying exponentially over 200ms. |
| **Error Buzz (`errorBuzz`)** | State `error` / backend error | Square wave sweeping 200Hz -> 100Hz over 300ms with sharp decay. |
| **Listening Hum (`startListeningHum`)**| State `listening` | Continuous 60Hz low sine oscillator with subtle lowpass filter modulation. |
| **Processing Whirr (`thinkingWhirr`)** | State `thinking` | Short rhythmic sequence of high-pitched micro-clicks (2kHz, 10ms pulses). |

---

### 3.7 Settings Overlay Panel (`panels/settings.ts` & `settings.css`)

- **Interactive Drawer**: Slide-in glassmorphism panel (`backdrop-filter: blur(12px)`).
- **Sections**:
  1. **Voice Configuration**: STT plugin select (Whisper.cpp, faster-whisper), TTS voice select (Piper British Butler, edge-tts), volume slider.
  2. **AI Brain Configuration**: LLM plugin select (Ollama, OpenAI, Gemini), model name input/dropdown, temperature slider.
  3. **Activation Methods**: Toggle checkboxes for Wake Word ("Hey Jarvis"), Push-to-Talk, Double-Clap Detector, Gesture.
  4. **Appearance & HUD**: Theme picker (Arc Reactor, Matrix, Synthwave), particle density slider, CRT scanlines toggle.
  5. **Face/Eye Vision**: Camera index input, gaze tracking toggle, helmet boot effect toggle.
  6. **Audio SFX**: SFX master volume slider, individual sound toggles.
- **WebSocket Synchronization**:
  - Sends `config_update`: `{"type": "config_update", "plugin": "<namespace>", "key": "<key>", "value": <val>}`
  - Queries configuration: `{"type": "settings_request"}`

---

## 4. WebSocket Protocol & State Synchronization

### 4.1 Protocol Message Specification

```typescript
// frontend/src/renderer/core/types.ts

export type JarvisState = "idle" | "listening" | "thinking" | "speaking" | "error";

export interface StateChangeEvent {
  type: "state_change";
  state: JarvisState;
}

export interface TranscriptPartialEvent {
  type: "transcript_partial";
  text: string;
}

export interface TranscriptFinalEvent {
  type: "transcript_final";
  text: string;
}

export interface LLMTokenEvent {
  type: "llm_token";
  token: string;
}

export interface ResponseCompleteEvent {
  type: "response_complete";
  full_text: string;
}

export interface AudioLevelEvent {
  type: "audio_level";
  level: number; // 0.0 to 1.0
}

export interface FaceDataEvent {
  type: "face_data";
  gaze: [number, number];
  pose: { pitch: number; yaw: number; roll: number };
  blink: boolean;
  face_detected: boolean;
}

export interface PluginLoadedEvent {
  type: "plugin_loaded";
  name: string;
  plugin_type: string;
}

export interface BackendErrorEvent {
  type: "error";
  message: string;
}

export type InboundWSMessage =
  | StateChangeEvent
  | TranscriptPartialEvent
  | TranscriptFinalEvent
  | LLMTokenEvent
  | ResponseCompleteEvent
  | AudioLevelEvent
  | FaceDataEvent
  | PluginLoadedEvent
  | BackendErrorEvent
  | { type: "pong" };

export interface CommandMessage {
  type: "command";
  action: "activate" | "deactivate";
}

export interface ConfigUpdateMessage {
  type: "config_update";
  plugin: string;
  key: string;
  value: any;
}

export interface SettingsRequestMessage {
  type: "settings_request";
}

export interface PingMessage {
  type: "ping";
}

export type OutboundWSMessage =
  | CommandMessage
  | ConfigUpdateMessage
  | SettingsRequestMessage
  | PingMessage;
```

---

## 5. Verification & Acceptance Criteria Alignment

| Acceptance Criteria | Status | Verification Path |
|---|---|---|
| **Zero TypeScript Compilation Errors** | Pending Implementation | `cd frontend && npm run build` (`tsc` generates `dist/` without type errors). |
| **Full-Screen HUD Display** | Pending Implementation | Status bar with model/mode/state, transcript bar, side panels, and glassmorphism settings overlay. |
| **ARC Reactor Core & Animations** | Pending Implementation | Concentric rotating rings with CSS/Canvas animations reacting immediately to `state_change` (`idle`, `listening`, `thinking`, `speaking`, `error`). |
| **Audio Waveform & Particle Visualizers** | Pending Implementation | Canvas renderers reacting to `audio_level` and particle density state maps. |
| **Web Audio SFX Synthesizer** | Pending Implementation | Pure mathematical sound synthesis without `.wav`/`.mp3` asset dependencies. |

---

## 6. Recommended Implementation Sequence for Frontend Developer

1. **Step 1: Protocol Types & Build Configuration** (`frontend/src/renderer/core/types.ts`, `tsconfig.json`)
   - Establish strict TypeScript interfaces for all inbound and outbound WebSocket messages.
   - Ensure module bundling / ES module loading configuration so renderer scripts load seamlessly in Chromium.
2. **Step 2: HUD Layout & Styles** (`frontend/src/renderer/hud/layout.css`, `index.html`)
   - Create 3-panel CSS grid layout with status bar, center viewport, transcript bar, and settings modal.
3. **Step 3: Procedural Audio SFX** (`frontend/src/renderer/sfx/synthesizer.ts`)
   - Implement `SFXSynthesizer` using Web Audio API oscillators and gain envelopes.
4. **Step 4: ARC Reactor Core** (`frontend/src/renderer/hud/arc-reactor.ts`, `arc-reactor.css`)
   - Build multi-ring SVG/DOM structure with rotation animations and state glow shifts.
5. **Step 5: Waveform & Particle Visualizers** (`frontend/src/renderer/hud/waveform.ts`, `particles.ts`)
   - Implement canvas-based frequency/amplitude bars and Iron Man HUD particle chevrons.
6. **Step 6: Status & Transcript Bars** (`frontend/src/renderer/hud/status-bar.ts`, `transcript-bar.ts`)
   - Render real-time partial transcripts, final transcripts, and LLM streaming tokens.
7. **Step 7: Settings Overlay Panel** (`frontend/src/renderer/hud/panels/settings.ts`, `settings.css`)
   - Build sliding drawer for plugin and HUD configuration.
8. **Step 8: App Orchestration & WebSocket Wiring** (`frontend/src/renderer/core/app.ts`, `ws-client.ts`)
   - Bind all HUD components to WebSocket message stream, test state transitions, verify build with `npm run build`.
