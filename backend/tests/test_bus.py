import asyncio
import pytest
from jarvis.core.bus import EventBus, Event


@pytest.mark.asyncio
async def test_emit_and_receive():
    bus = EventBus()
    received = []

    async def handler(event: Event):
        received.append(event)

    bus.on("test", handler)
    await bus.emit(Event(type="test", data={"value": 42}))

    # Process one event
    event = await asyncio.wait_for(bus._queue.get(), timeout=1)
    await handler(event)

    assert len(received) == 1
    assert received[0].data["value"] == 42


@pytest.mark.asyncio
async def test_off_removes_handler():
    bus = EventBus()
    received = []

    async def handler(event: Event):
        received.append(event)

    bus.on("test", handler)

    # Emit and dispatch — handler should fire
    await bus.emit(Event(type="test", data={"round": 1}))
    event = await asyncio.wait_for(bus._queue.get(), timeout=1)
    for h in bus._handlers.get(event.type, []):
        await h(event)
    assert len(received) == 1

    # Remove handler, emit again — handler should NOT fire
    bus.off("test", handler)
    await bus.emit(Event(type="test", data={"round": 2}))
    event = await asyncio.wait_for(bus._queue.get(), timeout=1)
    for h in bus._handlers.get(event.type, []):
        await h(event)
    assert len(received) == 1, "handler should not fire after off()"
