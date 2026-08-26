# Milestone 1: Core Backend & Plugin Architecture — Challenger 1 Handoff Report

**Agent:** Challenger 1  
**Target:** Parent / Orchestrator  
**Handoff Type:** Hard  
**Working Directory:** `/home/pawan/Projects/jarvis-ai/.agents/challenger_m1_1`  
**Verdict:** **REQUEST_CHANGES**  
**Timestamp:** 2026-08-26T20:00:00Z  

---

## 1. Observation

Adversarial stress harnesses and protocol conformance tests were executed against all Milestone 1 components (`EventBus`, `StateMachine`, `Config`, `PluginManager`, `WSServer`, and `__main__.py`).

### Observation 1.1: `EventBus.process()` Terminates Permanently on Handler Exception
- **File:** `backend/jarvis/core/bus.py:34-39`
- **Code:**
  ```python
  async def process(self) -> None:
      while True:
          event = await self._queue.get()
          handlers = self._handlers.get(event.type, [])
          for handler in handlers:
              await handler(event)
  ```
- **Observed Behavior:** When any handler raises an exception during `process()`, the exception escapes the `while True` loop without being caught. The `bus.process()` background task dies permanently. Subsequent handlers registered for that event are skipped, and all subsequent events placed into `bus._queue` are never processed by the system.
- **Empirical Execution:**
  ```bash
  python3 -c '
  import asyncio
  from jarvis.core.bus import EventBus, Event
  async def run():
      bus = EventBus()
      bus.on("e", lambda ev: (_ for _ in ()).throw(ValueError("boom")))
      t = asyncio.create_task(bus.process())
      await bus.emit(Event(type="e"))
      await asyncio.sleep(0.05)
      print("Task done:", t.done(), "Exception:", t.exception())
  asyncio.run(run())
  '
  # Output: Task done: True Exception: boom
  ```

### Observation 1.2: `PluginManager.stop_all()` Aborts on First Plugin Failure
- **File:** `backend/jarvis/plugins/manager.py:91-105`
- **Code:**
  ```python
  async def deactivate(self, name: str) -> bool:
      if name not in self._active:
          return False
      plugin = self._active[name]
      try:
          await plugin.stop()
      finally:
          self._active.pop(name, None)
      return True

  async def stop_all(self) -> None:
      for name in list(self._active.keys()):
          await self.deactivate(name)
  ```
- **Observed Behavior:** `deactivate()` re-raises any exception thrown by `plugin.stop()`. In `stop_all()`, if the first active plugin raises an exception in `stop()`, the loop immediately terminates. Subsequent active plugins are never stopped and remain running / uncleaned.
- **Empirical Execution:**
  ```bash
  python3 -c '
  import asyncio
  from jarvis.core.bus import EventBus
  from jarvis.core.config import Config
  from jarvis.plugins.base import Plugin
  from jarvis.plugins.manager import PluginManager

  class P1(Plugin):
      name = "p1"
      async def start(self, c=None): pass
      async def stop(self): raise RuntimeError("P1 stop error")
      async def on_event(self, e): pass
      def get_schema(self): return {}

  class P2(Plugin):
      name = "p2"
      stopped = False
      async def start(self, c=None): pass
      async def stop(self): self.stopped = True
      async def on_event(self, e): pass
      def get_schema(self): return {}

  async def run():
      mgr = PluginManager(EventBus(), Config("/tmp"))
      p1, p2 = P1(), P2()
      mgr.register(p1); mgr.register(p2)
      await mgr.activate("p1"); await mgr.activate("p2")
      try: await mgr.stop_all()
      except Exception: pass
      print("P2 stopped?", p2.stopped, "Active:", list(mgr.get_active_plugins().keys()))
  asyncio.run(run())
  '
  # Output: P2 stopped? False Active: ['p2']
  ```

### Observation 1.3: `WSServer` Ignores Frontend Messages Specified in `PROJECT.md` Contract
- **File:** `backend/jarvis/ws_server.py:42-61` vs `PROJECT.md:93-97`
- **Spec Contract (`PROJECT.md` line 93-97):**
  - `{"type": "activate"}`
  - `{"type": "deactivate"}`
  - `{"type": "config_update", "data": {"namespace": "...", "key": "...", "value": ...}}`
- **Implementation in `ws_server.py`:**
  ```python
  async def _on_message(self, msg: dict[str, Any]) -> None:
      msg_type = msg.get("type")
      if msg_type == "command":
          action = msg.get("action")
          if action == "activate": ...
          elif action == "deactivate": ...
      elif msg_type == "config_update":
          await self.bus.emit(Event(..., data={
              "plugin": msg.get("plugin"),
              "key": msg.get("key"),
              "value": msg.get("value")
          }))
  ```
- **Observed Behavior:**
  1. `{"type": "activate"}` and `{"type": "deactivate"}` messages from HUD are ignored because `_on_message` only looks for `msg_type == "command"`.
  2. `{"type": "config_update", "data": {...}}` fails to parse `namespace`/`plugin`, `key`, and `value` because it looks at the top-level dictionary (`msg.get("plugin")`) rather than `msg.get("data")`.
  3. Non-JSON payloads in `_handle` cause an uncaught `JSONDecodeError`, abruptly closing client connection without error isolation.

### Observation 1.4: `Config.list_namespaces()` Generates Phantom Namespaces for Subdirectories
- **File:** `backend/jarvis/core/config.py:31-41`
- **Code:**
  ```python
  def list_namespaces(self) -> list[str]:
      namespaces: set[str] = set()
      if self._config_dir.exists() and self._config_dir.is_dir():
          for p in self._config_dir.rglob("*.json"):
              rel = p.relative_to(self._config_dir).with_suffix("").as_posix()
              namespaces.add(rel)
              namespaces.add(p.stem)
  ```
- **Observed Behavior:** For nested config files such as `config/plugins/whisper.json`, `list_namespaces()` returns both `plugins/whisper` and `whisper`. Calling `config.get("whisper")` attempts to read `config/whisper.json` (which does not exist), returning `{}`.

---

## 2. Logic Chain

1. **Step 1 (Event Loop Robustness):**
   - Observation 1.1 shows that any unhandled exception in any event handler causes `EventBus.process()` to terminate permanently.
   - In production, audio/STT/TTS/LLM plugins or UI listeners may raise transient network, format, or I/O exceptions.
   - If `process()` terminates, the entire event bus ceases operation, hanging the assistant.
   - Mitigation required: In `EventBus.process()`, wrap handler invocations in `try...except Exception:` with logging/error reporting so that one failing handler does not abort the bus or skip other handlers.

2. **Step 2 (Plugin Lifecycle Resilience):**
   - Observation 1.2 shows that `PluginManager.stop_all()` and `deactivate()` allow exceptions in `plugin.stop()` to abort shutdown iteration.
   - In production, if one plugin encounters an error during cleanup, subsequent plugins (e.g. microphone stream, speaker audio hardware, background threads) will not be stopped.
   - Mitigation required: `PluginManager.stop_all()` and `deactivate()` must catch exceptions during `plugin.stop()`, ensure removal from `_active`, and ensure all active plugins are given an opportunity to stop.

3. **Step 3 (Protocol Gateway Alignment):**
   - Observation 1.3 shows that `WSServer` does not handle the message format defined in `PROJECT.md` (`{"type": "activate"}`, `{"type": "deactivate"}`, and `{"type": "config_update", "data": {"namespace": ...}}`).
   - When the Electron HUD connects and emits activation commands or config changes using the project standard protocol, the backend will discard them.
   - Mitigation required: Update `WSServer._on_message` to support both direct type (`activate`/`deactivate`) and legacy command format, and parse nested `data` dict in `config_update`. In `_handle`, wrap `json.loads` in `try...except json.JSONDecodeError`.

4. **Step 4 (Config Namespace Integrity):**
   - Observation 1.4 shows `namespaces.add(p.stem)` introduces invalid phantom namespace keys for nested configurations.
   - Mitigation required: Remove `namespaces.add(p.stem)` and keep `namespaces.add(rel)` so that listed namespaces cleanly map 1:1 to disk paths.

---

## 3. Caveats

- StateMachine transitions under valid and invalid conditions performed with 100% correctness across the full 5x5 state transition matrix.
- Config atomic persistence under high-volume concurrent writes (50 tasks, 1000 writes) and concurrent reads passed without data corruption or read failures.
- Plugin discovery and fault isolation during `route_event()` (`on_event` exceptions) passed.

---

## 4. Conclusion

**Verdict: REQUEST_CHANGES**

Milestone 1 implements the foundational architecture well, but requires four targeted fixes before passing verification:
1. **EventBus:** Add `try...except Exception:` around handler execution in `EventBus.process()` to prevent event loop termination.
2. **PluginManager:** In `stop_all()` / `deactivate()`, isolate exceptions during `plugin.stop()` so that all active plugins are reliably cleaned up.
3. **WSServer:** Align `_on_message` with `PROJECT.md` specification (support `{"type": "activate"}`, `{"type": "deactivate"}`, parse `data` payload for `config_update`, and catch `JSONDecodeError`).
4. **Config:** In `list_namespaces()`, remove `namespaces.add(p.stem)` to avoid phantom namespace keys.

---

## 5. Verification Method

1. **Run Full Test Suite (Unit + Adversarial):**
   ```bash
   cd /home/pawan/Projects/jarvis-ai/backend && python3 -m pytest tests/ -v
   ```
   *Expected Result after changes:* All unit and adversarial tests (60+ tests) pass with 0 failures.

2. **Verify EventBus Crash Resilience:**
   ```bash
   python3 -c '
   import asyncio
   from jarvis.core.bus import EventBus, Event
   async def test():
       bus = EventBus()
       results = []
       async def bad_h(e): raise ValueError("err")
       async def good_h(e): results.append(e.data["val"])
       bus.on("test", bad_h); bus.on("test", good_h)
       task = asyncio.create_task(bus.process())
       await bus.emit(Event(type="test", data={"val": 1}))
       await asyncio.sleep(0.05)
       assert 1 in results and not task.done()
       task.cancel()
       print("EventBus Resilience: OK")
   asyncio.run(test())
   '
   ```

3. **Verify WSServer Spec Compliance:**
   ```bash
   python3 -c '
   import asyncio
   from jarvis.core.bus import EventBus, Event
   from jarvis.core.state import StateMachine
   from jarvis.ws_server import WSServer
   async def test():
       bus = EventBus(); state = StateMachine(); server = WSServer(bus, state)
       received = []
       bus.on("activate", lambda e: received.append(e.type))
       bus.on("config_update", lambda e: received.append(e.type))
       await server._on_message({"type": "activate"})
       await server._on_message({"type": "config_update", "data": {"namespace": "tts", "key": "k", "value": "v"}})
       assert len(received) == 2
       print("WSServer Spec Compliance: OK")
   asyncio.run(test())
   '
   ```
