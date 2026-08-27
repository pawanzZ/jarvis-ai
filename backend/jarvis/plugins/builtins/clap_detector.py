from __future__ import annotations
import math
import time
from typing import Any, Optional
from jarvis.core.bus import Event, EventBus
from jarvis.core.config import Config
from jarvis.plugins.base import Plugin, PluginType


class ClapDetectorPlugin(Plugin):
    """Double-Clap Activation Plugin.

    Analyzes audio energy spikes to detect distinct double clap acoustic patterns
    within a temporal window for hands-free activation.
    """

    name = "clap_detector"
    plugin_type = PluginType.ACTIVATION

    def __init__(
        self,
        bus: Optional[EventBus] = None,
        config: Optional[Config] = None,
    ) -> None:
        super().__init__(bus=bus, config=config)
        self._threshold = 0.82
        self._window_ms = 500
        self._min_interval_ms = 50
        self._last_clap_time = 0.0
        self._clap_count = 0
        self._running = False

    @property
    def clap_count(self) -> int:
        """Return the current count of claps detected in the active window."""
        return self._clap_count

    async def start(self, config: Optional[dict[str, Any]] = None) -> None:
        """Start and configure Clap Detector."""
        cfg = config or {}
        self._threshold = float(cfg.get("threshold", 0.82))
        self._window_ms = int(cfg.get("window_ms", 500))
        self._min_interval_ms = int(cfg.get("min_interval_ms", 50))
        self._last_clap_time = 0.0
        self._clap_count = 0
        self._running = True

    async def stop(self) -> None:
        """Stop Clap Detector."""
        self._running = False
        self._clap_count = 0
        self._last_clap_time = 0.0

    def calculate_energy(self, chunk: Any) -> float:
        """Calculate RMS energy of an audio chunk."""
        if chunk is None:
            return 0.0
        if isinstance(chunk, (list, tuple)):
            if not chunk:
                return 0.0
            sum_sq = sum(float(x) ** 2 for x in chunk)
            return min(1.0, math.sqrt(sum_sq / len(chunk)))
        if isinstance(chunk, (int, float)):
            return min(1.0, max(0.0, float(chunk)))
        return 0.0

    async def on_event(self, event: Event) -> Optional[Event]:
        """Process incoming audio energy or raw audio chunk events."""
        if not self._running:
            return None

        energy = 0.0
        now = time.monotonic()

        if event.type == "audio_energy":
            energy = float(event.data.get("energy", 0.0))
        elif event.type in ("audio_chunk", "audio_frame"):
            chunk = event.data.get("audio") or event.data.get("frame")
            energy = self.calculate_energy(chunk)
        elif event.type == "test_clap":
            # For testing: allows manual timestamp simulation
            energy = 1.0
            now = float(event.data.get("timestamp", now))
        else:
            return None

        # Check energy threshold
        if energy >= self._threshold:
            dt = now - self._last_clap_time
            min_dt = self._min_interval_ms / 1000.0
            max_dt = self._window_ms / 1000.0

            if self._clap_count > 0 and (dt < min_dt):
                # Debounce: ignore reverberation/echo of same clap
                return None

            if self._clap_count > 0 and (min_dt <= dt <= max_dt):
                # Second clap within valid temporal window!
                self._clap_count += 1
                if self._clap_count >= 2:
                    self._clap_count = 0
                    self._last_clap_time = 0.0

                    act_event = Event(
                        type="activate",
                        data={"source": self.name, "pattern": "double_clap"},
                        source=self.name,
                    )
                    ret_event = Event(
                        type="activation",
                        data={"source": self.name, "pattern": "double_clap"},
                        source=self.name,
                    )
                    if self.bus:
                        await self.bus.emit(act_event)
                    return ret_event
            else:
                # First clap or expired window -> start new window
                self._clap_count = 1
                self._last_clap_time = now

        return None

    def get_schema(self) -> dict[str, Any]:
        """Return schema for settings UI generation."""
        return {
            "type": "object",
            "properties": {
                "threshold": {
                    "type": "number",
                    "default": 0.82,
                },
                "window_ms": {
                    "type": "integer",
                    "default": 500,
                },
                "min_interval_ms": {
                    "type": "integer",
                    "default": 50,
                },
            },
        }


plugin_class = ClapDetectorPlugin
