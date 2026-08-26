import asyncio
import pytest
from jarvis.core.bus import Event, EventBus


@pytest.mark.asyncio
async def test_high_volume_concurrent_emits():
    """Stress test: 10,000 events emitted concurrently across 20 producers."""
    bus = EventBus()
    num_producers = 20
    events_per_producer = 500
    total_events = num_producers * events_per_producer
    received_count = 0
    received_event_ids = set()

    async def test_handler(event: Event) -> None:
        nonlocal received_count
        received_count += 1
        received_event_ids.add(event.data["id"])

    bus.on("stress_event", test_handler)

    bus_task = asyncio.create_task(bus.process())

    async def producer(producer_id: int):
        for i in range(events_per_producer):
            ev_id = f"{producer_id}_{i}"
            await bus.emit(Event(type="stress_event", data={"id": ev_id, "producer": producer_id}))

    producers = [asyncio.create_task(producer(p)) for p in range(num_producers)]
    await asyncio.gather(*producers)

    # Allow bus.process to drain queue
    for _ in range(50):
        if received_count >= total_events:
            break
        await asyncio.sleep(0.05)

    bus_task.cancel()
    try:
        await bus_task
    except asyncio.CancelledError:
        pass

    assert received_count == total_events, f"Expected {total_events} events, received {received_count}"
    assert len(received_event_ids) == total_events


@pytest.mark.asyncio
async def test_handler_exception_fault_isolation():
    """Adversarial test: An exception in one handler should NOT kill bus.process or block other handlers."""
    bus = EventBus()
    good_handler_1_calls = []
    good_handler_2_calls = []

    async def faulty_handler(event: Event) -> None:
        raise RuntimeError("Simulated explosive failure in event handler!")

    async def good_handler_1(event: Event) -> None:
        good_handler_1_calls.append(event.data["msg"])

    async def good_handler_2(event: Event) -> None:
        good_handler_2_calls.append(event.data["msg"])

    # Register in order: good_handler_1, faulty_handler, good_handler_2
    bus.on("fragile_event", good_handler_1)
    bus.on("fragile_event", faulty_handler)
    bus.on("fragile_event", good_handler_2)

    bus_task = asyncio.create_task(bus.process())

    # Emit event 1 (which triggers faulty_handler)
    await bus.emit(Event(type="fragile_event", data={"msg": "first"}))
    await asyncio.sleep(0.1)

    # Emit event 2 (verifying bus is still alive)
    await bus.emit(Event(type="fragile_event", data={"msg": "second"}))
    await asyncio.sleep(0.1)

    bus_task.cancel()
    try:
        await bus_task
    except asyncio.CancelledError:
        pass

    # Check if bus task survived and handlers were called
    assert not bus_task.done() or bus_task.cancelled(), "bus.process() task should not have crashed with unhandled exception"
    assert "first" in good_handler_1_calls
    assert "first" in good_handler_2_calls, "Subsequent handler should have been called despite faulty_handler throwing"
    assert "second" in good_handler_1_calls, "Bus should still process subsequent events after a handler failure"
    assert "second" in good_handler_2_calls


@pytest.mark.asyncio
async def test_dynamic_handler_mutation_during_dispatch():
    """Stress test: Registering and unregistering handlers during high-frequency active dispatch."""
    bus = EventBus()
    bus_task = asyncio.create_task(bus.process())
    received = []

    async def dynamic_handler(event: Event):
        received.append(event.data["seq"])

    async def emitter():
        for i in range(100):
            await bus.emit(Event(type="dynamic_test", data={"seq": i}))
            await asyncio.sleep(0.001)

    async def mutator():
        for i in range(20):
            bus.on("dynamic_test", dynamic_handler)
            await asyncio.sleep(0.005)
            bus.off("dynamic_test", dynamic_handler)
            await asyncio.sleep(0.005)

    await asyncio.gather(emitter(), mutator())
    await asyncio.sleep(0.1)

    bus_task.cancel()
    try:
        await bus_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_fifo_ordering_per_producer():
    """Verify FIFO ordering of events emitted from a single sequential producer."""
    bus = EventBus()
    received_sequence = []

    async def handler(event: Event):
        received_sequence.append(event.data["seq"])

    bus.on("seq_event", handler)
    bus_task = asyncio.create_task(bus.process())

    for i in range(1000):
        await bus.emit(Event(type="seq_event", data={"seq": i}))

    for _ in range(50):
        if len(received_sequence) == 1000:
            break
        await asyncio.sleep(0.05)

    bus_task.cancel()
    try:
        await bus_task
    except asyncio.CancelledError:
        pass

    assert received_sequence == list(range(1000))
