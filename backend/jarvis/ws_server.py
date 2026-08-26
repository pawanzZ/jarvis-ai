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
                        await ws.send(
                            json.dumps(
                                {
                                    "type": "error",
                                    "data": {
                                        "code": "INVALID_PAYLOAD",
                                        "message": "Expected JSON object",
                                    },
                                }
                            )
                        )
                        continue
                    await self._on_message(ws, payload)
                except json.JSONDecodeError:
                    try:
                        await ws.send(
                            json.dumps(
                                {
                                    "type": "error",
                                    "data": {
                                        "code": "JSON_DECODE_ERROR",
                                        "message": "Malformed JSON format",
                                    },
                                }
                            )
                        )
                    except websockets.ConnectionClosed:
                        break
                except websockets.ConnectionClosed:
                    break
                except Exception as e:
                    try:
                        await ws.send(
                            json.dumps(
                                {
                                    "type": "error",
                                    "data": {
                                        "code": "SERVER_ERROR",
                                        "message": str(e),
                                    },
                                }
                            )
                        )
                    except websockets.ConnectionClosed:
                        break
        except websockets.ConnectionClosed:
            pass
        finally:
            self._clients.discard(ws)

    async def _on_message(self, arg1: Any, arg2: Optional[Any] = None) -> None:
        if arg2 is not None:
            if isinstance(arg1, dict):
                msg, ws = arg1, arg2
            else:
                ws, msg = arg1, arg2
        else:
            if isinstance(arg1, dict):
                msg, ws = arg1, None
            else:
                msg, ws = {}, arg1

        msg_type = msg.get("type")
        if msg_type == "activate" or (
            msg_type == "command" and msg.get("action") == "activate"
        ):
            await self.bus.emit(Event(type="activate", source="hud"))
        elif msg_type == "deactivate" or (
            msg_type == "command" and msg.get("action") == "deactivate"
        ):
            await self.bus.emit(Event(type="deactivate", source="hud"))
        elif msg_type == "config_update":
            data = msg.get("data") if isinstance(msg.get("data"), dict) else {}
            plugin = (
                data.get("namespace")
                or data.get("plugin")
                or msg.get("plugin")
                or msg.get("namespace", "core")
            )
            key = data.get("key") or msg.get("key")
            value = data.get("value") if "value" in data else msg.get("value")
            await self.bus.emit(
                Event(
                    type="config_update",
                    data={
                        "plugin": plugin,
                        "namespace": plugin,
                        "key": key,
                        "value": value,
                    },
                    source="hud",
                )
            )
        elif msg_type == "ping":
            data = msg.get("data") if isinstance(msg.get("data"), dict) else {}
            pong_resp: dict[str, Any] = {"type": "pong"}
            if "timestamp" in data:
                pong_resp["data"] = {"timestamp": data["timestamp"]}
            if ws is not None:
                try:
                    await ws.send(json.dumps(pong_resp))
                except websockets.ConnectionClosed:
                    pass
            else:
                await self.broadcast(pong_resp)
        elif msg_type == "settings_request":
            await self.bus.emit(Event(type="settings_request", source="hud"))
            if ws is not None:
                try:
                    await ws.send(
                        json.dumps(
                            {"type": "settings_response", "data": {"settings": {}}}
                        )
                    )
                except websockets.ConnectionClosed:
                    pass

    async def broadcast(self, data: dict[str, Any]) -> None:
        message = json.dumps(data)
        for client in list(self._clients):
            try:
                await client.send(message)
            except websockets.ConnectionClosed:
                self._clients.discard(client)
