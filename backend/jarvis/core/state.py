from __future__ import annotations
from enum import Enum
from typing import Callable, Awaitable


class JarvisState(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    ERROR = "error"


TRANSITIONS: dict[JarvisState, set[JarvisState]] = {
    JarvisState.IDLE: {JarvisState.LISTENING, JarvisState.ERROR},
    JarvisState.LISTENING: {JarvisState.THINKING, JarvisState.IDLE, JarvisState.ERROR},
    JarvisState.THINKING: {JarvisState.SPEAKING, JarvisState.IDLE, JarvisState.ERROR},
    JarvisState.SPEAKING: {JarvisState.LISTENING, JarvisState.IDLE, JarvisState.ERROR},
    JarvisState.ERROR: {JarvisState.IDLE},
}


class StateMachine:
    def __init__(self) -> None:
        self._state = JarvisState.IDLE
        self._listeners: list[Callable[[JarvisState, JarvisState], Awaitable[None]]] = []

    @property
    def state(self) -> JarvisState:
        return self._state

    def on_change(self, callback: Callable[[JarvisState, JarvisState], Awaitable[None]]) -> None:
        self._listeners.append(callback)

    async def transition(self, new_state: JarvisState) -> bool:
        if new_state not in TRANSITIONS.get(self._state, set()):
            return False
        old = self._state
        self._state = new_state
        for cb in self._listeners:
            await cb(old, new_state)
        return True
