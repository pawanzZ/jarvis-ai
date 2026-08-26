## 2026-08-26T20:11:20Z

You are the Worker for Milestone 4: Project Tooling, Automation & Documentation (R4).
Your working directory is: /home/pawan/Projects/jarvis-ai/.agents/worker_m4
Original Request: /home/pawan/Projects/jarvis-ai/.agents/ORIGINAL_REQUEST.md
Master Project Spec: /home/pawan/Projects/jarvis-ai/.agents/PROJECT.md
Spec Miner Survey Analysis: /home/pawan/Projects/jarvis-ai/.agents/spec_miner_survey_specs/analysis.md
Implementation Plan: /home/pawan/Projects/jarvis-ai/docs/superpowers/plans/2026-08-26-jarvis-ai-implementation.md (Phase 8, Task 20)

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your Tasks:
1. Implement `scripts/setup.sh`:
   - Checks prerequisites (Python 3.10+, Node.js 18+).
   - Creates virtual environment `backend/.venv` if not existing.
   - Installs backend dependencies (`pip install -e ".[dev]"` in `backend/`).
   - Installs frontend dependencies (`npm install` in `frontend/`).
   - Builds frontend (`npm run build` in `frontend/`).
   - Ensure script is executable (`chmod +x scripts/setup.sh`).
2. Implement `scripts/dev.sh`:
   - Runs backend (`python3 -m jarvis`) and frontend (`npm run dev`) concurrently.
   - Installs signal trap `trap 'kill $(jobs -p) 2>/dev/null' EXIT INT TERM` for clean child process cleanup on exit.
   - Ensure script is executable (`chmod +x scripts/dev.sh`).
3. Implement configuration files:
   - `config/default.yaml`: Comprehensive default configuration covering core, ws_server, voice/stt/tts/llm/activation/vision plugins, appearance, and sfx.
   - `config/core.json`: Core state and logging configuration.
   - `config/plugins/whisper.json`, `config/plugins/piper.json`, `config/plugins/ollama.json`, `config/plugins/push_to_talk.json`, `config/plugins/clap_detector.json`, `config/plugins/face_tracker.json`.
   - `config/themes/iron_man.json`.
4. Implement master `README.md` at workspace root:
   - System overview with ASCII architecture diagram.
   - Prerequisites, installation & quickstart via `scripts/setup.sh` and `scripts/dev.sh`.
   - Architecture details (backend event loop, state machine, plugin system, Electron HUD visualizer, SFX synthesizer).
   - Plugin authoring guide (how to write a custom plugin inheriting `Plugin`).
   - Configuration guide.
5. Update all task checkboxes (`- [ ]` -> `- [x]`) in `docs/superpowers/plans/2026-08-26-jarvis-ai-implementation.md` to reflect full implementation completion across all 8 phases and 20 tasks.
6. Verify scripts and files:
   - Verify script execution syntax with `bash -n scripts/setup.sh` and `bash -n scripts/dev.sh`.
   - Verify all tests pass: `cd backend && python3 -m pytest tests/ -v`.
   - Verify frontend compiles: `cd frontend && npm run build`.
7. Write your changes log to `/home/pawan/Projects/jarvis-ai/.agents/worker_m4/changes.md` and complete handoff report to `/home/pawan/Projects/jarvis-ai/.agents/worker_m4/handoff.md`.
8. Send a message to parent when complete.
