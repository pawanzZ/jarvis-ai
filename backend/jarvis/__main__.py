import asyncio
from pathlib import Path
from jarvis.core.bus import EventBus
from jarvis.core.state import StateMachine
from jarvis.core.config import Config


async def main() -> None:
    base_dir = Path(__file__).parent.parent.parent
    bus = EventBus()
    state = StateMachine()
    config = Config(base_dir)

    async def on_state_change(old, new):
        print(f"State: {old.value} -> {new.value}")

    state.on_change(on_state_change)
    print("Jarvis backend starting...")
    # WebSocket server will be added in Task 3
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
