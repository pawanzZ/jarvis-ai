import asyncio
import json
import pytest
from jarvis.core.bus import Event, EventBus
from jarvis.core.state import StateMachine, JarvisState
from jarvis.ws_server import WSServer

try:
    from websockets.asyncio.server import serve
    from websockets.asyncio.client import connect
except ImportError:
    from websockets.server import serve
    from websockets.client import connect


@pytest.mark.asyncio
async def test_concurrent_clients_broadcast():
    """Stress test: 20 concurrent WebSocket clients receiving broadcasts."""
    bus = EventBus()
    state = StateMachine()
    port = 8780
    server = WSServer(bus, state, port=port)

    num_clients = 20
    received_counts = [0] * num_clients

    async def client_worker(idx: int):
        async with connect(f"ws://localhost:{port}") as ws:
            for _ in range(5):
                msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
                data = json.loads(msg)
                if data.get("type") == "broadcast_test":
                    received_counts[idx] += 1

    async with serve(server._handle, "localhost", port):
        client_tasks = [asyncio.create_task(client_worker(i)) for i in range(num_clients)]
        await asyncio.sleep(0.1)

        # Broadcast 5 messages
        for i in range(5):
            await server.broadcast({"type": "broadcast_test", "seq": i})
            await asyncio.sleep(0.01)

        await asyncio.gather(*client_tasks)

    assert all(c == 5 for c in received_counts), f"Not all clients received 5 messages: {received_counts}"


@pytest.mark.asyncio
async def test_client_disconnect_during_broadcast():
    """Adversarial test: A client disconnects abruptly while server broadcasts."""
    bus = EventBus()
    state = StateMachine()
    port = 8781
    server = WSServer(bus, state, port=port)

    surviving_received = []

    async def persistent_client():
        async with connect(f"ws://localhost:{port}") as ws:
            while True:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    surviving_received.append(json.loads(msg))
                except (asyncio.TimeoutError, Exception):
                    break

    async with serve(server._handle, "localhost", port):
        pers_task = asyncio.create_task(persistent_client())
        await asyncio.sleep(0.05)

        # Connect a fleeting client and abruptly close it
        ws_fleeting = await connect(f"ws://localhost:{port}")
        await asyncio.sleep(0.02)
        await ws_fleeting.close()

        # Broadcast message — should handle dead client cleanly and deliver to persistent client
        await server.broadcast({"type": "post_disconnect", "status": "ok"})
        await asyncio.sleep(0.1)

        pers_task.cancel()
        try:
            await pers_task
        except asyncio.CancelledError:
            pass

    assert len(surviving_received) >= 1
    assert surviving_received[0]["type"] == "post_disconnect"


@pytest.mark.asyncio
async def test_ping_pong_protocol():
    """Verify ping message triggers pong response."""
    bus = EventBus()
    state = StateMachine()
    port = 8782
    server = WSServer(bus, state, port=port)

    async with serve(server._handle, "localhost", port):
        async with connect(f"ws://localhost:{port}") as ws:
            await ws.send(json.dumps({"type": "ping"}))
            msg = await asyncio.wait_for(ws.recv(), timeout=1.0)
            data = json.loads(msg)
            assert data["type"] == "pong"


@pytest.mark.asyncio
async def test_malformed_json_client_resilience():
    """Adversarial test: Server receives invalid JSON string and unexpected payloads."""
    bus = EventBus()
    state = StateMachine()
    port = 8783
    server = WSServer(bus, state, port=port)

    async with serve(server._handle, "localhost", port):
        # Client sends invalid JSON
        try:
            async with connect(f"ws://localhost:{port}") as ws:
                await ws.send("NON_JSON_CORRUPTED_STRING_<<<>>>")
                await asyncio.sleep(0.05)
        except Exception:
            pass

        # Server should still be accepting new healthy connections
        async with connect(f"ws://localhost:{port}") as ws2:
            await ws2.send(json.dumps({"type": "ping"}))
            msg = await asyncio.wait_for(ws2.recv(), timeout=1.0)
            assert json.loads(msg)["type"] == "pong"
