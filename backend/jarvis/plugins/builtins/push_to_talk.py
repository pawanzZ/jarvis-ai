from __future__ import annotations
from typing import Any, Optional
from jarvis.core.bus import Event, EventBus
from jarvis.core.config import Config
from jarvis.plugins.base import Plugin, PluginType


class PushToTalkPlugin(Plugin):
    """Push-to-Talk (PTT) Activation Plugin.

    Translates keyboard press and release events into assistant activation/deactivation triggers.
    Supports hold-to-speak and toggle modes.
    """

    name = "push_to_talk"
    plugin_type = PluginType.ACTIVATION

    def __init__(
        self,
        bus: Optional[EventBus] = None,
        config: Optional[Config] = None,
    ) -> None:
        super().__init__(bus=bus, config=config)
        self._key = "space"
        self._mode = "hold"
        self._pressed = False
        self._active = False
        self._running = False

    @property
    def is_pressed(self) -> bool:
        """Return True if the configured PTT key is currently held down."""
        return self._pressed

    @property
    def is_active(self) -> bool:
        """Return True if PTT has triggered active listening mode."""
        return self._active

    async def start(self, config: Optional[dict[str, Any]] = None) -> None:
        """Start and configure Push-to-Talk."""
        cfg = config or {}
        self._key = cfg.get("key", "space").lower()
        self._mode = cfg.get("mode", "hold").lower()
        self._pressed = False
        self._active = False
        self._running = True

    async def stop(self) -> None:
        """Stop Push-to-Talk."""
        self._running = False
        self._pressed = False
        self._active = False

    async def on_event(self, event: Event) -> Optional[Event]:
        """Handle key events and toggle or hold listening state."""
        if not self._running:
            return None

        event_key = str(event.data.get("key", "")).lower()

        # Handle Key Down / Press
        if event.type in ("key_down", "keydown", "ptt_down"):
            if event_key == self._key or not event_key:
                if self._mode == "hold":
                    if not self._pressed:
                        self._pressed = True
                        self._active = True
                        act_event = Event(
                            type="activate",
                            data={"source": self.name, "mode": "hold"},
                            source=self.name,
                        )
                        ret_event = Event(
                            type="activation",
                            data={"source": self.name},
                            source=self.name,
                        )
                        if self.bus:
                            await self.bus.emit(act_event)
                        return ret_event
                elif self._mode == "toggle":
                    self._active = not self._active
                    action = "activate" if self._active else "deactivate"
                    target_type = "activation" if self._active else "deactivation"
                    bus_event = Event(
                        type=action,
                        data={"source": self.name, "mode": "toggle"},
                        source=self.name,
                    )
                    ret_event = Event(
                        type=target_type,
                        data={"source": self.name},
                        source=self.name,
                    )
                    if self.bus:
                        await self.bus.emit(bus_event)
                    return ret_event

        # Handle Key Up / Release
        elif event.type in ("key_up", "keyup", "ptt_up"):
            if event_key == self._key or not event_key:
                if self._mode == "hold":
                    if self._pressed:
                        self._pressed = False
                        self._active = False
                        deact_event = Event(
                            type="deactivate",
                            data={"source": self.name, "mode": "hold"},
                            source=self.name,
                        )
                        ret_event = Event(
                            type="deactivation",
                            data={"source": self.name},
                            source=self.name,
                        )
                        if self.bus:
                            await self.bus.emit(deact_event)
                        return ret_event

        return None

    def get_schema(self) -> dict[str, Any]:
        """Return schema for settings UI generation."""
        return {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "default": "space",
                },
                "mode": {
                    "type": "string",
                    "enum": ["hold", "toggle"],
                    "default": "hold",
                },
            },
        }


plugin_class = PushToTalkPlugin
