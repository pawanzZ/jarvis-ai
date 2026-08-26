# Milestone 1: Core Backend & Plugin Architecture — Review & Adversarial Report

**Reviewer:** Reviewer 1 (reviewer, critic)  
**Milestone:** Milestone 1: Core Backend & Plugin Architecture  
**Working Directory:** `/home/pawan/Projects/jarvis-ai/.agents/reviewer_m1_1`  
**Timestamp:** 2026-08-26T19:56:00Z  
**Verdict:** `REQUEST_CHANGES`

---

## 1. Observation

### 1.1 Test Suite Execution
1. Executing standard Milestone 1 unit tests:
   ```bash
   python3 -m pytest tests/test_bus.py tests/test_state.py tests/test_config.py tests/test_plugin_base.py tests/test_plugin_manager.py tests/test_ws_server.py -v
   ```
   Output:
   ```
   ============================== 41 passed in 0.30s ==============================
   ```

2. Executing full pytest discovery (`python3 -m pytest tests/ -v`):
   ```
   FAILED tests/adversarial/test_adv_bus.py::test_handler_exception_fault_isolation
   FAILED tests/adversarial/test_adv_plugin_manager.py::test_stop_all_resilience_when_plugin_throws
   ========================= 3 failed, 50 passed in 1.99s =========================
   ```

### 1.2 Static Code & Resilience Observations
1. **`backend/jarvis/core/bus.py:35-40` (`EventBus.process`)**:
   ```python
   async def process(self) -> None:
       while True:
           event = await self._queue.get()
           handlers = self._handlers.get(event.type, [])
           for handler in handlers:
               await handler(event)
   ```
   *Observation:* When an event handler raises an unhandled exception (e.g. `RuntimeError` or `ValueError`), the exception propagates out of `process()`, permanently killing the background `bus_task = asyncio.create_task(bus.process())` spawned in `backend/jarvis/__main__.py:62`. Subsequent handlers for that event and all future events queued on the bus will never be dispatched.

2. **`backend/jarvis/plugins/manager.py:92-106` (`PluginManager.deactivate` & `PluginManager.stop_all`)**:
   ```python
   async def deactivate(self, name: str) -> bool:
       """Deactivate an active plugin by name and invoke stop()."""
       if name not in self._active:
           return False
       plugin = self._active[name]
       try:
           await plugin.stop()
       finally:
           self._active.pop(name, None)
       return True

   async def stop_all(self) -> None:
       """Stop all active plugins."""
       for name in list(self._active.keys()):
           await self.deactivate(name)
   ```
   *Observation:* If `plugin.stop()` raises an exception during `await self.deactivate(name)`, the exception propagates out of `deactivate` and abruptly terminates `stop_all()`. Any plugins remaining in `self._active` will not have `deactivate` or `stop` called on them.

3. **`backend/jarvis/plugins/base.py` & `backend/jarvis/core/config.py`**:
   *Observation:* Fully compliant with ABC interface requirements (`start`, `stop`, `on_event`, `get_schema`), `PluginType` enum values match spec, `Config` implements atomic `.tmp` replace and handles corrupt JSON gracefully.

4. **Integrity Check**:
   *Observation:* No hardcoded test responses, dummy facade implementations, shortcuts, or fabricated outputs were detected. Code is genuine and adheres to specifications.

---

## 2. Logic Chain

1. **Step 1 (Event Loop Robustness):**
   - Observation 1.2.1 demonstrates that an unhandled exception inside any registered event subscriber crashes the asynchronous event dispatch loop task `bus.process()`.
   - In Milestone 2, background ML plugins (Whisper STT, Piper TTS, Ollama LLM, MediaPipe Vision) will emit and listen to continuous audio and vision events. Runtime exceptions (e.g. GPU OOM, audio buffer underrun, socket disconnect) in one plugin's handler must not crash the entire core event bus.
   - Deduction: `EventBus.process()` must isolate handler execution in a `try...except Exception:` block with error logging.

2. **Step 2 (Plugin Lifecycle & Graceful Teardown):**
   - Observation 1.2.2 demonstrates that if one plugin throws an exception during `stop()`, `stop_all()` aborts immediately, leaving remaining active plugins un-stopped and resources unreleased.
   - Deduction: `PluginManager.deactivate()` should catch exceptions from `plugin.stop()` (or `PluginManager.stop_all()` must catch exceptions per plugin) to ensure all active plugins are given the opportunity to shut down.

3. **Step 3 (Specification Conformance & Overall Quality):**
   - The remaining core components (`Plugin`, `PluginType`, `Config`, `StateMachine`, `WSServer`) are well-designed, strictly typed, and cleanly structured. Addressing the two fault-isolation items above will guarantee backend resilience for Milestone 2.

---

## 3. Caveats

1. Builtin plugins (`Whisper`, `Piper`, `Ollama`, `PTT`, `Clap`, `FaceTracker`) will be developed under Milestone 2; their absence in Milestone 1 is expected and by design.
2. The failure in `tests/adversarial/test_adv_config.py:100` was caused by a missing `mkdir` call in the adversarial test itself rather than an issue in `Config.py`.

---

## 4. Conclusion & Required Changes

**Verdict:** `REQUEST_CHANGES`

### Required Changes for Worker M1:

#### 1. [MAJOR] Fault Isolation in `EventBus.process` (`backend/jarvis/core/bus.py`)
- **Issue:** An exception in an event handler crashes `bus.process()`, killing the background dispatch loop.
- **Remediation:** Wrap `await handler(event)` inside `EventBus.process()` in a `try...except Exception as e:` block and log the failure so subsequent handlers and future events continue processing unimpeded.

```python
    async def process(self) -> None:
        while True:
            event = await self._queue.get()
            handlers = list(self._handlers.get(event.type, []))
            for handler in handlers:
                try:
                    await handler(event)
                except Exception as e:
                    print(f"Error in event handler for {event.type}: {e}")
```

#### 2. [MAJOR] Fault Isolation in `PluginManager.deactivate` / `stop_all` (`backend/jarvis/plugins/manager.py`)
- **Issue:** If `plugin.stop()` raises an exception, `deactivate` re-raises and halts `stop_all()` before stopping other active plugins.
- **Remediation:** Catch `Exception` in `PluginManager.deactivate()`, log the error, and return `False`, ensuring `self._active.pop(name, None)` occurs and `stop_all()` continues iterating through all active plugins.

```python
    async def deactivate(self, name: str) -> bool:
        """Deactivate an active plugin by name and invoke stop()."""
        if name not in self._active:
            return False
        plugin = self._active[name]
        try:
            await plugin.stop()
            return True
        except Exception:
            return False
        finally:
            self._active.pop(name, None)
```

---

## 5. Verification Method

1. Run the test suite:
   ```bash
   cd /home/pawan/Projects/jarvis-ai/backend && python3 -m pytest tests/ -v
   ```
2. Verify that `test_handler_exception_fault_isolation` and `test_stop_all_resilience_when_plugin_throws` pass.
3. Verify all 41 core unit tests continue to pass.
