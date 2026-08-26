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


@pytest.mark.asyncio
async def test_activate_and_deactivate_direct_and_command():
    bus = EventBus()
    state = StateMachine()
    server = WSServer(bus, state, port=8767)
    events = []

    bus.on("activate", lambda e: events.append(e.type))
    bus.on("deactivate", lambda e: events.append(e.type))

    bus_task = asyncio.create_task(bus.process())

    # Test direct format
    await server._on_message({"type": "activate"})
    await server._on_message({"type": "deactivate"})
    await asyncio.sleep(0.05)
    assert events == ["activate", "deactivate"]

    # Test command envelope format
    events.clear()
    await server._on_message({"type": "command", "action": "activate"})
    await server._on_message({"type": "command", "action": "deactivate"})
    await asyncio.sleep(0.05)
    assert events == ["activate", "deactivate"]

    bus_task.cancel()
    try:
        await bus_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_config_update_nested_and_flat():
    bus = EventBus()
    state = StateMachine()
    server = WSServer(bus, state, port=8768)
    captured = []

    bus.on("config_update", lambda e: captured.append(e.data))
    bus_task = asyncio.create_task(bus.process())

    # Nested format
    await server._on_message({
        "type": "config_update",
        "data": {"namespace": "stt", "key": "model", "value": "large"}
    })
    await asyncio.sleep(0.05)
    assert len(captured) == 1
    assert captured[0]["plugin"] == "stt"
    assert captured[0]["key"] == "model"
    assert captured[0]["value"] == "large"

    # Flat format
    captured.clear()
    await server._on_message({
        "type": "config_update",
        "plugin": "tts",
        "key": "voice",
        "value": "en-us"
    })
    await asyncio.sleep(0.05)
    assert len(captured) == 1
    assert captured[0]["plugin"] == "tts"
    assert captured[0]["key"] == "voice"
    assert captured[0]["value"] == "en-us"

    bus_task.cancel()
    try:
        await bus_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_ping_pong_unicast_with_timestamp():
    bus = EventBus()
    state = StateMachine()
    port = 8769
    server = WSServer(bus, state, port=port)

    try:
        from websockets.asyncio.server import serve
        from websockets.asyncio.client import connect
    except ImportError:
        from websockets.server import serve
        from websockets.client import connect

    async with serve(server._handle, "localhost", port):
        async with connect(f"ws://localhost:{port}") as ws1, connect(f"ws://localhost:{port}") as ws2:
            await asyncio.sleep(0.05)
            # Send ping with timestamp from ws1
            await ws1.send(json.dumps({"type": "ping", "data": {"timestamp": 12345}}))
            msg = await asyncio.wait_for(ws1.recv(), timeout=1)
            resp = json.loads(msg)
            assert resp["type"] == "pong"
            assert resp.get("data", {}).get("timestamp") == 12345

            # Ensure ws2 did not receive the pong
            ws2_got_pong = False
            try:
                msg2 = await asyncio.wait_for(ws2.recv(), timeout=0.1)
                ws2_got_pong = True
            except asyncio.TimeoutError:
                pass
            assert not ws2_got_pong


@pytest.mark.asyncio
async def test_settings_request_emits_event_and_responds():
    bus = EventBus()
    state = StateMachine()
    port = 8770
    server = WSServer(bus, state, port=port)
    events = []

    bus.on("settings_request", lambda e: events.append(e))
    bus_task = asyncio.create_task(bus.process())

    try:
        from websockets.asyncio.server import serve
        from websockets.asyncio.client import connect
    except ImportError:
        from websockets.server import serve
        from websockets.client import connect

    async with serve(server._handle, "localhost", port):
        async with connect(f"ws://localhost:{port}") as ws:
            await ws.send(json.dumps({"type": "settings_request"}))
            msg = await asyncio.wait_for(ws.recv(), timeout=1)
            resp = json.loads(msg)
            assert resp["type"] == "settings_response"
            assert "data" in resp
            await asyncio.sleep(0.05)
            assert len(events) == 1
            assert events[0].type == "settings_request"

    bus_task.cancel()
    try:
        await bus_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_malformed_json_and_non_dict_error_frames():
    bus = EventBus()
    state = StateMachine()
    port = 8771
    server = WSServer(bus, state, port=port)

    try:
        from websockets.asyncio.server import serve
        from websockets.asyncio.client import connect
    except ImportError:
        from websockets.server import serve
        from websockets.client import connect

    async with serve(server._handle, "localhost", port):
        async with connect(f"ws://localhost:{port}") as ws:
            # Malformed JSON
            await ws.send("{ bad json")
            msg = await asyncio.wait_for(ws.recv(), timeout=1)
            resp = json.loads(msg)
            assert resp["type"] == "error"
            assert resp["data"]["code"] == "JSON_DECODE_ERROR"

            # Non-dict JSON payload
            await ws.send(json.dumps([1, 2, 3]))
            msg2 = await asyncio.wait_for(ws.recv(), timeout=1)
            resp2 = json.loads(msg2)
            assert resp2["type"] == "error"
            assert resp2["data"]["code"] == "INVALID_PAYLOAD"
