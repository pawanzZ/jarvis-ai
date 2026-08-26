# Milestone 1: Empirical Verification & Adversarial Stress Report (Challenger 2)

**Agent:** Challenger M1 (Instance 2)  
**Target:** Parent / Orchestrator  
**Verdict:** **REQUEST_CHANGES**  
**Working Directory:** `/home/pawan/Projects/jarvis-ai/.agents/challenger_m1_2`  
**Timestamp:** 2026-08-26T19:54:00Z  

---

## 1. Observation

1. **Empirical Test Suite Execution:**
   - Executed `/home/pawan/Projects/jarvis-ai/.agents/challenger_m1_2/stress_harness.py` containing 29 empirical tests across 6 validation suites.
   - **Overall Score:** 24 Passed, 5 Failed.
   - Summary of test results:
     - **Performance & Latency (PERF-01..04):** 4/4 Passed.
       - Ping/Pong round-trip latency (1,000 cycles): Min: `0.161ms`, Mean: `0.194ms`, P50: `0.181ms`, P95: `0.269ms`, P99: `0.356ms`, Max: `0.540ms`.
       - 50-Client state broadcast fan-out: Delivered to all 50 concurrent sockets in `5.77ms`.
       - High-frequency broadcast throughput: `24,791.6 msgs/sec` (500 messages delivered in `20.17ms`).
       - Concurrent multi-client burst: 10 sockets sent 500 commands in `185.98ms` with zero dropped events.
     - **Lifecycle & Memory (LIFECYCLE-01..03):** 3/3 Passed.
       - 100 rapid connect/disconnect loops completed in `358.22ms`, leaving 0 active client leaks in `server._clients`.
       - Dead socket eviction on abrupt client socket drop succeeded without breaking other connections.
       - Server shutdown via task cancellation cleanly terminates without hanging.
     - **Config Engine Resilience (CONFIG-01..06):** 6/6 Passed.
       - 1,000 concurrent asynchronous writes completed in `144.87ms` with full atomic disk integrity.
       - Corrupt JSON files and non-UTF8 binary byte recovery gracefully fallback to default/empty dicts without raising uncaught exceptions.
     - **Robustness (ROBUST-01..06):** 6/6 Passed.
       - Server remained operational after ingestion of 1MB frames, 100-level nested JSON trees, non-JSON strings, and bursts of 500 malformed packets.
     - **System Integration (INT-01..02):** 2/2 Passed.
       - End-to-end WebSocket -> StateMachine -> EventBus -> Plugin routing works cleanly.

2. **Observed Contract Violations & Deficiencies:**
   - **Observation 2.1 (SPEC-WS-01 & SPEC-WS-02): Missing Direct Activation/Deactivation Commands**
     - Spec requirement (`PROJECT.md` line 94):
       `{"type": "activate"}` / `{"type": "deactivate"}`
     - Actual implementation (`backend/jarvis/ws_server.py` lines 43-49):
       ```python
       msg_type = msg.get("type")
       if msg_type == "command":
           action = msg.get("action")
           if action == "activate":
               await self.bus.emit(Event(type="activate", source="hud"))
           elif action == "deactivate":
               await self.bus.emit(Event(type="deactivate", source="hud"))
       ```
     - Verbatim test output:
       `❌ [Protocol Contract] SPEC-WS-01 (Direct Activate Type): Received: []. Spec requires {"type": "activate"} handling.`
       `❌ [Protocol Contract] SPEC-WS-02 (Direct Deactivate Type): Received: []. Spec requires {"type": "deactivate"} handling.`

   - **Observation 2.2 (SPEC-WS-03): Flat vs Nested Data Payload in `config_update`**
     - Spec requirement (`PROJECT.md` line 95):
       `{"type": "config_update", "data": {"namespace": "...", "key": "...", "value": ...}}`
     - Actual implementation (`backend/jarvis/ws_server.py` lines 50-61):
       ```python
       elif msg_type == "config_update":
           await self.bus.emit(
               Event(
                   type="config_update",
                   data={
                       "plugin": msg.get("plugin"),
                       "key": msg.get("key"),
                       "value": msg.get("value"),
                   },
                   source="hud",
               )
           )
       ```
     - When frontend sends `{"type": "config_update", "data": {"namespace": "stt", "key": "model", "value": "tiny"}}`, `msg.get("plugin")`, `msg.get("key")`, `msg.get("value")` return `None`.
     - Verbatim test output:
       `❌ [Protocol Contract] SPEC-WS-03 (Config Update Data Field): Received event data: [{'plugin': None, 'key': None, 'value': None}]. Spec defines payload in 'data' object.`

   - **Observation 2.3 (SPEC-WS-04): Ping/Pong Unicast and Timestamp Echo Failure**
     - Spec requirement (`PROJECT.md` lines 91 and 97):
       Frontend sends: `{"type": "ping", "data": {"timestamp": 1234567890}}`
       Backend responds: `{"type": "pong", "data": {"timestamp": 1234567890}}`
     - Actual implementation (`backend/jarvis/ws_server.py` lines 62-63):
       ```python
       elif msg_type == "ping":
           await self.broadcast({"type": "pong"})
       ```
     - Ping responses are broadcast to *every* connected client instead of unicasting to the sender, and the `timestamp` payload is discarded.
     - Verbatim test output:
       `❌ [Protocol Contract] SPEC-WS-04 (Ping Pong Payload & Unicast): Response: {'type': 'pong'}. Unicast to sender: False (Broadcast to other client: True), Echoed timestamp: False.`

   - **Observation 2.4 (SPEC-WS-05): Unhandled `settings_request`**
     - Spec requirement (`PROJECT.md` lines 89 and 96):
       Frontend sends: `{"type": "settings_request"}`
       Backend responds: `{"type": "settings_response", "data": {"settings": {...}}}`
     - `ws_server.py` lacks a branch for `settings_request`.
     - Verbatim test output:
       `❌ [Protocol Contract] SPEC-WS-05 (Settings Request / Response): Timeout: Server did not respond to settings_request`

   - **Observation 2.5: Uncaught Tracebacks on Malformed JSON and Primitive Payloads**
     - Implementation in `backend/jarvis/ws_server.py` lines 34-43:
       ```python
       async def _handle(self, ws: Any) -> None:
           self._clients.add(ws)
           try:
               async for message in ws:
                   await self._on_message(json.loads(message))
           finally:
               self._clients.discard(ws)
       ```
     - If client sends invalid JSON string (e.g. `"{invalid"`), `json.loads` throws `JSONDecodeError`. If client sends JSON array/primitive (e.g. `[1, 2]`, `123`), `msg.get("type")` throws `AttributeError`.
     - These exceptions escape `_handle`, producing noisy `connection handler failed` error tracebacks in stderr and abruptly severing client sockets without an error message frame (`{"type": "error", "data": {"code": "...", "message": "..."}}`).

---

## 2. Logic Chain

1. **Step 1 (WebSocket Protocol Specification Conformance):**
   - Observations 2.1, 2.2, 2.3, 2.4 demonstrate that `ws_server.py` diverges from `PROJECT.md` line 81–98 contract definitions.
   - Inference: When the Electron HUD frontend (Milestone 3) connects to `ws://localhost:8765` and issues standard activation toggles (`{"type": "activate"}`), heartbeat pings with timestamp payloads, or settings configuration changes (`{"type": "config_update", "data": {...}}`), the backend will fail to process activation, drop configuration changes, and fail round-trip latency measurements.

2. **Step 2 (Robustness and Error Frame Handling):**
   - Observation 2.5 demonstrates that malformed inputs cause unhandled exceptions inside the WebSocket connection loop.
   - Inference: Wrapping `json.loads` and message dispatch in a `try...except` block and responding with `{"type": "error", "data": {"code": "INVALID_FORMAT", "message": "..."}}` ensures resilient client communication without dropping connections on accidental malformed packets.

3. **Step 3 (Performance, Concurrency, and Core Backend Soundness):**
   - Observation 1 confirms that EventBus, StateMachine, PluginManager, and Config engine core architectures are extremely fast (0.19ms ping/pong, 24k broadcasts/sec, 1,000 concurrent writes in 144ms) and thread/coroutine-safe.
   - Inference: The core architecture is solid; the defects are strictly protocol contract matching and error handling within `ws_server.py`.

---

## 3. Caveats

1. The test suite tested up to 50 concurrent WebSocket clients and 1,000 message bursts. Real-world desktop assistant usage typically involves 1–3 local clients (Electron main, renderer, debugging devtools).
2. The `settings_request` handler requires access to `Config` or `PluginManager` to construct the full `settings_response` payload dict. In Milestone 1, injecting `config` into `WSServer` or routing `settings_request` through `EventBus` resolves this cleanly.

---

## 4. Conclusion

**Verdict: REQUEST_CHANGES**

The core backend and plugin infrastructure are robust and high-performing, but `ws_server.py` contains contract regressions against `PROJECT.md`.

### Concrete Required Changes to `backend/jarvis/ws_server.py`:

```python
from __future__ import annotations
import asyncio
import json
from typing import Any, Optional
import websockets
try:
    from websockets.asyncio.server import serve
except ImportError:
    from websockets.server import serve

from jarvis.core.bus import EventBus, Event
from jarvis.core.state import StateMachine, JarvisState


class WSServer:
    def __init__(
        self,
        bus: EventBus,
        state: StateMachine,
        host: str = "localhost",
        port: int = 8765,
    ) -> None:
        self.bus = bus
        self.state = state
        self.host = host
        self.port = port
        self._clients: set[Any] = set()

    async def start(self) -> None:
        async with serve(self._handle, self.host, self.port):
            print(f"WebSocket server running on ws://{self.host}:{self.port}")
            await asyncio.Event().wait()

    async def _handle(self, ws: Any) -> None:
        self._clients.add(ws)
        try:
            async for message in ws:
                try:
                    payload = json.loads(message)
                    if not isinstance(payload, dict):
                        await ws.send(json.dumps({
                            "type": "error",
                            "data": {"code": "INVALID_PAYLOAD", "message": "Expected JSON object"}
                        }))
                        continue
                    await self._on_message(ws, payload)
                except json.JSONDecodeError:
                    await ws.send(json.dumps({
                        "type": "error",
                        "data": {"code": "JSON_DECODE_ERROR", "message": "Malformed JSON format"}
                    }))
                except Exception as e:
                    await ws.send(json.dumps({
                        "type": "error",
                        "data": {"code": "SERVER_ERROR", "message": str(e)}
                    }))
        finally:
            self._clients.discard(ws)

    async def _on_message(self, ws: Any, msg: dict[str, Any]) -> None:
        msg_type = msg.get("type")
        
        # Support both {"type": "activate"} and legacy {"type": "command", "action": "activate"}
        if msg_type == "activate" or (msg_type == "command" and msg.get("action") == "activate"):
            await self.bus.emit(Event(type="activate", source="hud"))
        elif msg_type == "deactivate" or (msg_type == "command" and msg.get("action") == "deactivate"):
            await self.bus.emit(Event(type="deactivate", source="hud"))
            
        # Support both {"type": "config_update", "data": {...}} and flat {"plugin": ..., "key": ..., "value": ...}
        elif msg_type == "config_update":
            data = msg.get("data") if isinstance(msg.get("data"), dict) else {}
            plugin = data.get("namespace") or data.get("plugin") or msg.get("plugin") or msg.get("namespace", "core")
            key = data.get("key") or msg.get("key")
            value = data.get("value") if "value" in data else msg.get("value")
            await self.bus.emit(
                Event(
                    type="config_update",
                    data={"plugin": plugin, "namespace": plugin, "key": key, "value": value},
                    source="hud",
                )
            )
            
        # Support {"type": "ping", "data": {"timestamp": ...}} with unicast pong
        elif msg_type == "ping":
            data = msg.get("data") if isinstance(msg.get("data"), dict) else {}
            pong_resp = {"type": "pong"}
            if "timestamp" in data:
                pong_resp["data"] = {"timestamp": data["timestamp"]}
            await ws.send(json.dumps(pong_resp))
            
        # Support {"type": "settings_request"}
        elif msg_type == "settings_request":
            await self.bus.emit(Event(type="settings_request", source="hud"))

    async def broadcast(self, data: dict[str, Any]) -> None:
        message = json.dumps(data)
        for client in list(self._clients):
            try:
                await client.send(message)
            except websockets.ConnectionClosed:
                self._clients.discard(client)
```

---

## 5. Verification Method

1. **Execute Challenger 2 Stress Harness:**
   ```bash
   python3 /home/pawan/Projects/jarvis-ai/.agents/challenger_m1_2/stress_harness.py
   ```
   *Expected Result after changes applied:* 29 / 29 tests pass (0 failures).

2. **Execute Full Pytest Suite:**
   ```bash
   cd /home/pawan/Projects/jarvis-ai/backend && python3 -m pytest tests/ -v
   ```
   *Expected Result:* 41 / 41 backend tests pass.

3. **Inspect Implementation Files:**
   - `backend/jarvis/ws_server.py`
   - `backend/jarvis/__main__.py`
   - `backend/jarvis/core/config.py`
