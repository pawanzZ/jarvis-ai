from __future__ import annotations
import asyncio
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine


@dataclass
class Event:
    type: str
    data: dict[str, Any] = field(default_factory=dict)
    source: str = ""


EventHandler = Callable[[Event], Coroutine[Any, Any, None]]


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = {}
        self._queue: asyncio.Queue[Event] = asyncio.Queue()

    def on(self, event_type: str, handler: EventHandler) -> None:
        self._handlers.setdefault(event_type, []).append(handler)

    def off(self, event_type: str, handler: EventHandler) -> None:
        if event_type in self._handlers:
            self._handlers[event_type] = [
                h for h in self._handlers[event_type] if h != handler
            ]

    async def emit(self, event: Event) -> None:
        await self._queue.put(event)

    async def process(self) -> None:
        while True:
            event = await self._queue.get()
            handlers = self._handlers.get(event.type, [])
            for handler in handlers:
                await handler(event)
