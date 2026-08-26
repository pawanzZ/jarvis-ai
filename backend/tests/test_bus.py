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


@pytest.mark.asyncio
async def test_handler_exception_isolation_in_process():
    bus = EventBus()
    received = []

    async def faulty_handler(event: Event) -> None:
        raise ValueError("Handler error")

    async def normal_handler(event: Event) -> None:
        received.append(event.data.get("v"))

    bus.on("calc", faulty_handler)
    bus.on("calc", normal_handler)

    task = asyncio.create_task(bus.process())
    await bus.emit(Event(type="calc", data={"v": 1}))
    await bus.emit(Event(type="calc", data={"v": 2}))
    await asyncio.sleep(0.05)

    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    assert received == [1, 2]
