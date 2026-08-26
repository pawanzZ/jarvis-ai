## 2026-08-26T19:53:03Z

You are the Worker for Milestone 1 Remediations.
Your working directory is: /home/pawan/Projects/jarvis-ai/.agents/worker_m1_fix
Original Request: /home/pawan/Projects/jarvis-ai/.agents/ORIGINAL_REQUEST.md
Master Project Spec: /home/pawan/Projects/jarvis-ai/.agents/PROJECT.md
Reviewer 1 Report: /home/pawan/Projects/jarvis-ai/.agents/reviewer_m1_1/handoff.md
Challenger 1 Report: /home/pawan/Projects/jarvis-ai/.agents/challenger_m1_1/handoff.md
Challenger 2 Report: /home/pawan/Projects/jarvis-ai/.agents/challenger_m1_2/handoff.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your Tasks:
Apply the targeted, high-reliability remediations across the backend files:
1. `backend/jarvis/core/bus.py`: In `EventBus.process()`, wrap `await handler(event)` in a `try...except Exception as e:` block with logging/print so an exception in an individual subscriber handler never kills the background queue processor.
2. `backend/jarvis/plugins/manager.py`: In `PluginManager.deactivate(name)` and `stop_all()`, ensure error isolation: if an individual plugin throws an error in `stop()`, log/capture the exception, mark it as stopped/inactive, and allow remaining plugins to stop cleanly without aborting.
3. `backend/jarvis/ws_server.py`:
   - In `_handle(ws)`, wrap incoming message parsing in `try...except json.JSONDecodeError:` and send `{"type": "error", "data": {"code": "JSON_DECODE_ERROR", "message": "Malformed JSON format"}}` and for other exceptions send `SERVER_ERROR` without crashing the handler. Validate `isinstance(payload, dict)`.
   - In `_on_message(ws, msg)`, support:
     - Direct `{"type": "activate"}` and `{"type": "deactivate"}` as well as command envelopes `{"type": "command", "action": "activate"}`.
     - `{"type": "config_update", "data": {"namespace": "...", "key": "...", "value": ...}}` as well as flat payloads.
     - `{"type": "ping", "data": {"timestamp": ...}}` by sending unicast response to `ws`: `{"type": "pong", "data": {"timestamp": ...}}` (or `{"type": "pong"}` if timestamp omitted).
     - `{"type": "settings_request"}` by emitting `Event(type="settings_request", source="hud")`.
4. `backend/jarvis/core/config.py`: In `list_namespaces()`, cleanly return existing namespace names from `.json` files in `config_dir` without generating duplicate phantom relative path stems.
5. Update unit tests in `backend/tests/` to cover these new behaviors and edge cases. Run `cd backend && python3 -m pytest tests/ -v`. Ensure 100% tests pass. Also run the challenger harnesses if desired to verify.
6. Write your changes and execution log to `/home/pawan/Projects/jarvis-ai/.agents/worker_m1_fix/changes.md` and complete handoff report to `/home/pawan/Projects/jarvis-ai/.agents/worker_m1_fix/handoff.md`.
7. Send a message to parent when complete.
