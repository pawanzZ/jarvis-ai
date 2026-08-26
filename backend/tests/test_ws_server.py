import asyncio
import json
import pytest
import websockets
from jarvis.core.bus import EventBus
from jarvis.core.state import StateMachine
from jarvis.ws_server import WSServer


@pytest.mark.asyncio
async def test_server_broadcast():
    bus = EventBus()
    state = StateMachine()
    server = WSServer(bus, state, port=8766)

    try:
        from websockets.asyncio.server import serve
        from websockets.asyncio.client import connect
    except ImportError:
        from websockets.server import serve
        from websockets.client import connect

    async with serve(server._handle, "localhost", 8766):
        async with connect("ws://localhost:8766") as ws:
            await asyncio.sleep(0.05)
            await server.broadcast({"type": "test", "data": "hello"})
            msg = await asyncio.wait_for(ws.recv(), timeout=1)
            data = json.loads(msg)
            assert data["type"] == "test"
            assert data["data"] == "hello"
