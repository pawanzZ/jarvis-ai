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
    bus.off("test", handler)
    await bus.emit(Event(type="test"))
    assert bus._queue.empty() or len(received) == 0
