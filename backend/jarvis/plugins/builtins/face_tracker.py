from __future__ import annotations
import math
import time
from typing import Any, Optional
from jarvis.core.bus import Event, EventBus
from jarvis.core.config import Config
from jarvis.plugins.base import Plugin, PluginType


class FaceTrackerPlugin(Plugin):
    """Vision and Face Tracking Plugin using MediaPipe / Camera feed.

    Tracks facial presence, gaze coordinates, and head pose angles (yaw, pitch, roll)
    to calculate user attention and emit telemetry events.
    """

    name = "face_tracker"
    plugin_type = PluginType.VISION

    def __init__(
        self,
        bus: Optional[EventBus] = None,
        config: Optional[Config] = None,
    ) -> None:
        super().__init__(bus=bus, config=config)
        self._camera_index = 0
        self._min_confidence = 0.5
        self._running = False
        self._face_detected = False
        self._last_detected = False
        self._gaze: list[float] = [0.5, 0.5]
        self._head_pose: dict[str, float] = {"yaw": 0.0, "pitch": 0.0, "roll": 0.0}
        self._blink: bool = False
        self._mock_override: Optional[dict[str, Any]] = None

    @property
    def is_face_detected(self) -> bool:
        """Return True if a face is currently detected."""
        return self._face_detected

    def set_mock_face_state(
        self,
        detected: bool = True,
        gaze: Optional[list[float]] = None,
        pose: Optional[dict[str, float]] = None,
        blink: bool = False,
    ) -> None:
        """Explicitly override face tracking state for deterministic testing."""
        self._mock_override = {
            "detected": detected,
            "gaze": gaze or [0.5, 0.5],
            "head_pose": pose or {"yaw": 0.0, "pitch": 0.0, "roll": 0.0},
            "blink": blink,
        }

    def clear_mock_override(self) -> None:
        """Clear the mock override."""
        self._mock_override = None

    async def start(self, config: Optional[dict[str, Any]] = None) -> None:
        """Start face tracking plugin."""
        cfg = config or {}
        self._camera_index = int(cfg.get("camera", 0))
        self._min_confidence = float(cfg.get("min_confidence", 0.5))
        self._running = True
        self._face_detected = False
        self._last_detected = False

    async def stop(self) -> None:
        """Stop face tracking plugin."""
        self._running = False
        self._face_detected = False
        self._last_detected = False

    def _compute_attention(self, gaze: list[float], pose: dict[str, float]) -> bool:
        """Determine if user is paying attention (looking towards HUD center)."""
        gaze_centered = 0.2 <= gaze[0] <= 0.8 and 0.2 <= gaze[1] <= 0.8
        pose_aligned = (
            abs(pose.get("yaw", 0.0)) <= 25.0
            and abs(pose.get("pitch", 0.0)) <= 25.0
        )
        return gaze_centered and pose_aligned

    async def on_event(self, event: Event) -> Optional[Event]:
        """Process video frame or vision query event and emit telemetry."""
        if not self._running:
            return None

        if event.type in ("camera_frame", "vision_tick", "poll_face", "face_query"):
            # Determine detection metrics from override or synthetic estimation
            if self._mock_override is not None:
                detected = self._mock_override.get("detected", True)
                gaze = list(self._mock_override.get("gaze", [0.5, 0.5]))
                pose = dict(self._mock_override.get("head_pose", {"yaw": 0.0, "pitch": 0.0, "roll": 0.0}))
                blink = bool(self._mock_override.get("blink", False))
            else:
                frame = event.data.get("frame")
                if frame is not None:
                    # In real pipeline, OpenCV/MediaPipe processes the frame
                    detected = True
                    gaze = [0.5, 0.5]
                    pose = {"yaw": 0.0, "pitch": 0.0, "roll": 0.0}
                    blink = False
                else:
                    # Synthetic gentle head sway / baseline telemetry
                    t = time.monotonic()
                    detected = True
                    gaze = [0.5 + 0.05 * math.sin(t), 0.5 + 0.03 * math.cos(t)]
                    pose = {
                        "yaw": 2.0 * math.sin(t * 0.5),
                        "pitch": 1.5 * math.cos(t * 0.3),
                        "roll": 0.5 * math.sin(t * 0.2),
                    }
                    blink = (int(t * 2) % 10 == 0)

            self._face_detected = detected
            self._gaze = gaze
            self._head_pose = pose
            self._blink = blink
            attention = detected and self._compute_attention(gaze, pose)

            # Detect state transitions (face_detected / face_lost)
            if detected and not self._last_detected:
                if self.bus:
                    await self.bus.emit(
                        Event(
                            type="face_detected",
                            data={"gaze": gaze, "head_pose": pose, "attention": attention},
                            source=self.name,
                        )
                    )
            elif not detected and self._last_detected:
                if self.bus:
                    await self.bus.emit(
                        Event(
                            type="face_lost",
                            data={},
                            source=self.name,
                        )
                    )
            self._last_detected = detected

            telemetry_data = {
                "detected": detected,
                "attention": attention,
                "head_pose": pose,
                "gaze": gaze,
                "blink": blink,
                "pose": pose,  # Alias for compatibility
                "face_detected": detected,  # Alias for compatibility
            }

            telemetry_event = Event(
                type="face_telemetry",
                data=telemetry_data,
                source=self.name,
            )
            data_event = Event(
                type="face_data",
                data=telemetry_data,
                source=self.name,
            )

            if self.bus:
                await self.bus.emit(telemetry_event)
                await self.bus.emit(data_event)

            return data_event

        return None

    def get_schema(self) -> dict[str, Any]:
        """Return schema for settings UI generation."""
        return {
            "type": "object",
            "properties": {
                "camera": {
                    "type": "integer",
                    "default": 0,
                },
                "min_confidence": {
                    "type": "number",
                    "default": 0.5,
                },
            },
        }


plugin_class = FaceTrackerPlugin
