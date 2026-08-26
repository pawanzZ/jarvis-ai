# Milestone 1: Core Backend & Plugin Architecture — Handoff Report

**Agent:** Explorer M1  
**Target:** Worker M1 / Orchestrator  
**Handoff Type:** Hard  
**Working Directory:** `/home/pawan/Projects/jarvis-ai/.agents/explorer_m1`

---

## 1. Observation

1. **Existing Backend Files and Directory Structure:**
   - `backend/jarvis/core/bus.py`: Contains `Event` dataclass (lines 7–12) and `EventBus` class with `on`, `off`, `emit`, `process` (lines 17–39).
   - `backend/jarvis/core/state.py`: Contains `JarvisState` enum (lines 6–12), `TRANSITIONS` dictionary (lines 14–20), and `StateMachine` class (lines 23–43).
   - `backend/jarvis/core/config.py`: Contains `Config` class with `get`, `set`, `_load`, `_save` (lines 7–38), but currently lacks `list_namespaces()` and `get_all(namespace)` methods, and does not use atomic `.tmp` rename for writes.
   - `backend/jarvis/ws_server.py`: Contains `WSServer` class (lines 15–72) binding to port `8765`, handling `command` (`activate`/`deactivate`), `config_update`, `ping`, and broadcast.
   - `backend/jarvis/__main__.py`: Contains `main()` (lines 9–22) which initializes `EventBus`, `StateMachine`, `Config`, `WSServer`, but does NOT start `bus.process()` background task, does not initialize `PluginManager`, and does not discover builtins.
   - Missing target files: `backend/jarvis/plugins/base.py`, `backend/jarvis/plugins/manager.py`, `backend/tests/test_plugin_base.py`, `backend/tests/test_plugin_manager.py`, `backend/tests/test_config.py`.

2. **Test Baseline:**
   - Command `cd /home/pawan/Projects/jarvis-ai/backend && python3 -m pytest tests/ -v` executed with code 0:
     ```
     tests/test_bus.py::test_emit_and_receive PASSED [ 14%]
     tests/test_bus.py::test_off_removes_handler PASSED [ 28%]
     tests/test_state.py::test_initial_state PASSED [ 42%]
     tests/test_state.py::test_valid_transition PASSED [ 57%]
     tests/test_state.py::test_invalid_transition PASSED [ 71%]
     tests/test_state.py::test_on_change_callback PASSED [ 85%]
     tests/test_ws_server.py::test_server_broadcast PASSED [100%]
     7 passed in 0.14s
     ```

3. **Specification & Plan Contracts:**
   - `PROJECT.md` lines 112–124 define the `Plugin` contract (`__init__(bus, config)`, `start`, `stop`, `on_event`, `get_schema`).
   - `PROJECT.md` lines 162–163 list `test_plugin_base.py`, `test_plugin_manager.py`, `test_config.py`.
   - `docs/superpowers/plans/2026-08-26-jarvis-ai-implementation.md` Tasks 1, 3, 4, 6, 7 detail requirements for base plugin classes, dynamic discovery, activation/deactivation, event routing, schema querying, and config namespace support.

---

## 2. Logic Chain

1. **Step 1 (Base Plugin Contract):**
   - Observation 1 & 3: Plugins in subsequent milestones (Whisper, Piper, Ollama, PTT, Clap, Face Tracker) need a common polymorphic interface.
   - Deduction: `backend/jarvis/plugins/base.py` must define `PluginType(str, Enum)` and `Plugin(ABC)` with `start(config: dict | None)`, `stop()`, `on_event(event: Event) -> Optional[Event]`, `get_schema() -> dict`, and accept optional `bus` and `config` in `__init__`.

2. **Step 2 (Plugin Lifecycle & Manager):**
   - Observation 1 & 3: Plugins need to be discovered from directories, registered manually or dynamically, started with namespace configuration, stopped safely, queried for schemas, and have events routed to them with fault isolation.
   - Deduction: `backend/jarvis/plugins/manager.py` must implement `PluginManager` with `register(plugin)`, `discover(plugins_dir)`, `activate(name)`, `deactivate(name)`, `stop_all()`, `get_plugin(name)`, `get_active(plugin_type)`, `get_active_plugins()`, `list_all()`, `get_schemas()`, and `route_event(event)`.

3. **Step 3 (Config Resilience):**
   - Observation 1: `Config` in `backend/jarvis/core/config.py` only implements simple `get` and `set`.
   - Deduction: Adding `list_namespaces()` and `get_all(namespace)` fulfills Task 7. Implementing atomic writing (`.tmp` file + `Path.replace`) and handling `json.JSONDecodeError` prevents corrupted configuration files and system crashes.

4. **Step 4 (Main Loop Event Dispatch):**
   - Observation 1: In `backend/jarvis/__main__.py`, `bus.emit(...)` puts events into `asyncio.Queue`, but `bus.process()` is not scheduled, so events are never dequeued and handlers never run.
   - Deduction: `__main__.py` must spawn `asyncio.create_task(bus.process())`, initialize `PluginManager`, discover plugins, register state change broadcasting and WebSocket command listeners (`activate`, `deactivate`, `config_update`), and cleanly cancel tasks on shutdown.

5. **Step 5 (Verification Suite):**
   - Observation 2 & 3: Full test suites must be created for `test_plugin_base.py`, `test_plugin_manager.py`, and `test_config.py`.
   - Deduction: Implementing these 3 test files with comprehensive feature, boundary, fault-tolerance, and scenario cases ensures total verification.

---

## 3. Caveats

1. Builtin plugins (Whisper, Piper, Ollama, etc.) are scheduled for Milestone 2 and are not implemented in Milestone 1; stub plugins should be used for testing dynamic discovery and lifecycle.
2. The WebSocket server port defaults to `8765`, while unit tests use alternate ports (e.g. `8766` or dynamically assigned ports) to avoid port collision.
3. In `__main__.py`, `server.start()` runs indefinitely until cancelled; integration tests should test components unit-by-unit with test fixtures.

---

## 4. Conclusion

Milestone 1 is ready for immediate, deterministic execution by the Worker. The full technical code specifications, exact file layouts, and exhaustive test cases are documented in `/home/pawan/Projects/jarvis-ai/.agents/explorer_m1/analysis.md`.

The Worker should implement:
1. `backend/jarvis/plugins/base.py`
2. `backend/jarvis/plugins/manager.py`
3. `backend/jarvis/core/config.py` (enhanced with `list_namespaces`, `get_all`, atomic writes, JSON error handling)
4. `backend/jarvis/__main__.py` (updated with `bus.process()` task and `PluginManager` wiring)
5. `backend/tests/test_plugin_base.py`
6. `backend/tests/test_plugin_manager.py`
7. `backend/tests/test_config.py`

---

## 5. Verification Method

1. **Run Pytest Suite:**
   ```bash
   cd /home/pawan/Projects/jarvis-ai/backend && python3 -m pytest tests/ -v
   ```
   *Expected Result:* All tests in `test_bus.py`, `test_state.py`, `test_ws_server.py`, `test_plugin_base.py`, `test_plugin_manager.py`, and `test_config.py` must pass with 0 failures and 0 errors.

2. **Syntax and Import Sanity Check:**
   ```bash
   cd /home/pawan/Projects/jarvis-ai/backend && python3 -c "import jarvis; from jarvis.plugins.base import Plugin, PluginType; from jarvis.plugins.manager import PluginManager; from jarvis.core.config import Config; print('M1 Imports OK')"
   ```
   *Expected Result:* Prints `M1 Imports OK`.
