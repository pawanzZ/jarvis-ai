from __future__ import annotations
import asyncio
import json
from typing import Any
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
                await self._on_message(json.loads(message))
        finally:
            self._clients.discard(ws)

    async def _on_message(self, msg: dict[str, Any]) -> None:
        msg_type = msg.get("type")
        if msg_type == "command":
            action = msg.get("action")
            if action == "activate":
                await self.bus.emit(Event(type="activate", source="hud"))
            elif action == "deactivate":
                await self.bus.emit(Event(type="deactivate", source="hud"))
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
        elif msg_type == "ping":
            await self.broadcast({"type": "pong"})

    async def broadcast(self, data: dict[str, Any]) -> None:
        message = json.dumps(data)
        for client in list(self._clients):
            try:
                await client.send(message)
            except websockets.ConnectionClosed:
                self._clients.discard(client)
