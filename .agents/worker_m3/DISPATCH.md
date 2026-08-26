## 2026-08-27T01:36:00Z

You are the Worker for Milestone 3: Full-Screen HUD Visualizer & Audio SFX (R3).
Your working directory is: /home/pawan/Projects/jarvis-ai/.agents/worker_m3
Original Request: /home/pawan/Projects/jarvis-ai/.agents/ORIGINAL_REQUEST.md
Master Project Spec: /home/pawan/Projects/jarvis-ai/.agents/PROJECT.md
Frontend Survey Analysis: /home/pawan/Projects/jarvis-ai/.agents/explorer_survey_frontend/analysis.md
Frontend Survey Handoff: /home/pawan/Projects/jarvis-ai/.agents/explorer_survey_frontend/handoff.md
Implementation Plan: /home/pawan/Projects/jarvis-ai/docs/superpowers/plans/2026-08-26-jarvis-ai-implementation.md (Tasks 5, 14, 15, 16, 18, 19)
Design Specification: /home/pawan/Projects/jarvis-ai/docs/superpowers/specs/2026-08-26-jarvis-ai-design.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your Tasks:
1. Read ORIGINAL_REQUEST.md, PROJECT.md, and the frontend survey analysis in `/home/pawan/Projects/jarvis-ai/.agents/explorer_survey_frontend/analysis.md`.
2. Implement all production frontend components in `frontend/src/`:
   - `frontend/src/renderer/core/types.ts`: Define TypeScript interfaces for all 5 Jarvis states (`IDLE`, `LISTENING`, `THINKING`, `SPEAKING`, `ERROR`), WebSocket message contracts (inbound and outbound), Settings schemas, and telemetry events.
   - `frontend/src/renderer/hud/layout.css`: Iron Man cyan/blue/gold HUD theme, CRT scan line overlay, glow filters, 3-panel layout, responsive grid, animations.
   - `frontend/src/renderer/hud/arc-reactor.ts` & `arc-reactor.css`: Canvas-based multi-ring ARC reactor core with dynamic state animations (IDLE slow rotate/pulse, LISTENING fast rotation & cyan audio expansion, THINKING pulsing gold energy arcs, SPEAKING soundwave modulation, ERROR red glitch shudder).
   - `frontend/src/renderer/hud/waveform.ts`: Real-time audio waveform and frequency visualizer driven by `audio_level` websocket events and procedural oscillators.
   - `frontend/src/renderer/hud/particles.ts`: 60fps particle engine with state-dependent density, velocity, and color shifts.
   - `frontend/src/renderer/hud/status-bar.ts`: Top status bar displaying Jarvis state badge, active backend, telemetry, ping/latency, and face attention indicator.
   - `frontend/src/renderer/hud/transcript-bar.ts`: Bottom transcript bar with token streaming, user input bubbles, and assistant response bubbles with typing effects.
   - `frontend/src/renderer/hud/panels/settings.ts` & `settings.css`: Slide-out settings drawer overlay with tabs for Voice, AI Brain, Activation, Appearance, Face/Eye, SFX, and Dev controls, binding bidirectional `config_update` and `settings_request`.
   - `frontend/src/renderer/sfx/synthesizer.ts`: Zero-dependency Web Audio API procedural sound synthesizer generating power-up, power-down, chime, error buzz, listening hum, and processing whirr without any external audio file dependencies.
   - `frontend/src/renderer/core/ws-client.ts`: Resilient typed WebSocket client with exponential backoff auto-reconnect, message routing, ping heartbeat, and error dispatch.
   - `frontend/src/renderer/core/app.ts`: Master frontend coordinator connecting HUD components, SFX synthesizer, and WebSocket client.
   - `frontend/src/renderer/index.html`: Complete HUD DOM structure referencing all canvas layers, status bar, transcript bar, and settings drawer.
   - `frontend/src/main.ts` & `frontend/src/preload.ts`: Clean Electron window setup.
   - `frontend/tsconfig.json` & `frontend/package.json`: Ensure seamless TypeScript compilation (`npm run build`).
3. Compile frontend: `cd frontend && npm run build`. Verify TypeScript compiles with ZERO errors and output in `dist/`.
4. Write your changes log to `/home/pawan/Projects/jarvis-ai/.agents/worker_m3/changes.md` and complete handoff report to `/home/pawan/Projects/jarvis-ai/.agents/worker_m3/handoff.md`.
5. Send a message to parent when complete.
