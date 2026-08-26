from __future__ import annotations
import asyncio
from pathlib import Path
from jarvis.core.bus import EventBus, Event
from jarvis.core.state import StateMachine, JarvisState
from jarvis.core.config import Config
from jarvis.ws_server import WSServer
from jarvis.plugins.manager import PluginManager


async def main() -> None:
    base_dir = Path(__file__).parent.parent.parent
    bus = EventBus()
    state = StateMachine()
    config = Config(base_dir)
    server = WSServer(bus, state)
    plugin_mgr = PluginManager(bus, config)

    # Discover built-in plugins
    builtins_dir = Path(__file__).parent / "plugins" / "builtins"
    if builtins_dir.exists():
        discovered = plugin_mgr.discover(builtins_dir)
        print(f"Discovered plugins: {discovered}")

    # Broadcast state transitions to HUD clients
    async def broadcast_state(old: JarvisState, new: JarvisState) -> None:
        await server.broadcast({
            "type": "state_change",
            "state": new.value,
            "data": {"state": new.value, "previous": old.value},
        })

    state.on_change(broadcast_state)

    # Core Event Handlers
    async def handle_activate(event: Event) -> None:
        if state.state == JarvisState.IDLE:
            await state.transition(JarvisState.LISTENING)

    async def handle_deactivate(event: Event) -> None:
        if state.state != JarvisState.IDLE:
            await state.transition(JarvisState.IDLE)

    async def handle_config_update(event: Event) -> None:
        plugin = event.data.get("plugin") or event.data.get("namespace", "core")
        key = event.data.get("key")
        value = event.data.get("value")
        if plugin and key:
            config.set(plugin, key, value)
            await server.broadcast({
                "type": "config_updated",
                "data": {"namespace": plugin, "key": key, "value": value},
            })

    bus.on("activate", handle_activate)
    bus.on("deactivate", handle_deactivate)
    bus.on("config_update", handle_config_update)

    print("Jarvis backend starting...")

    # Spawn background event bus processing loop
    bus_task = asyncio.create_task(bus.process())

    try:
        await server.start()
    finally:
        bus_task.cancel()
        await plugin_mgr.stop_all()


if __name__ == "__main__":
    asyncio.run(main())
