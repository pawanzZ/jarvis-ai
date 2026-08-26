from __future__ import annotations
import asyncio
from typing import Any, Optional, Sequence


class SpeakerOutput:
    """Speaker Audio Output.

    Handles audio buffer playback with volume attenuation, playback cancellation,
    and automatic fallback to timed simulation if sounddevice or hardware is missing.
    """

    def __init__(
        self,
        sample_rate: int = 24000,
        channels: int = 1,
        volume: float = 1.0,
        device: Optional[int | str] = None,
        simulate: bool = False,
    ) -> None:
        self.sample_rate = int(sample_rate)
        self.channels = int(channels)
        self._volume = max(0.0, min(1.0, float(volume)))
        self.device = device
        self._simulate = bool(simulate)

        self._playing: bool = False
        self._playback_task: Optional[asyncio.Task] = None
        self._sd_stream: Any = None

    @property
    def is_playing(self) -> bool:
        """Return True if audio playback is currently in progress."""
        return self._playing

    @property
    def volume(self) -> float:
        """Get the current output volume (0.0 to 1.0)."""
        return self._volume

    @volume.setter
    def volume(self, val: float) -> None:
        """Set the output volume (clamped between 0.0 and 1.0)."""
        self._volume = max(0.0, min(1.0, float(val)))

    def set_volume(self, val: float) -> None:
        """Explicit setter for output volume."""
        self.volume = val

    def get_volume(self) -> float:
        """Explicit getter for output volume."""
        return self._volume

    async def play(self, audio: Any, sample_rate: Optional[int] = None) -> None:
        """Play an audio buffer (list of floats, numpy array, or bytes).

        Attenuates samples by current volume and handles playback duration.
        """
        # Stop any ongoing playback
        self.stop()

        sr = sample_rate or self.sample_rate
        self._playing = True

        # Extract sample count
        num_samples = 0
        if isinstance(audio, (list, tuple)):
            num_samples = len(audio)
        elif hasattr(audio, "__len__"):
            num_samples = len(audio)
        elif hasattr(audio, "shape"):
            num_samples = audio.shape[0]

        duration = max(0.001, num_samples / max(1, sr)) if num_samples > 0 else 0.01

        self._playback_task = asyncio.create_task(self._execute_playback(audio, sr, duration))
        try:
            await self._playback_task
        except asyncio.CancelledError:
            pass
        finally:
            self._playing = False

    async def _execute_playback(self, audio: Any, sr: int, duration: float) -> None:
        """Internal playback execution with sounddevice / simulation."""
        if not self._simulate:
            try:
                import sounddevice as sd  # type: ignore

                # Attempt sounddevice playback if available
                scaled_audio = audio
                if isinstance(audio, list):
                    scaled_audio = [s * self._volume for s in audio]
                elif hasattr(audio, "__mul__"):
                    scaled_audio = audio * self._volume

                sd.play(scaled_audio, samplerate=sr, device=self.device)
                await asyncio.sleep(duration)
                sd.stop()
                return
            except Exception:
                self._simulate = True

        # Simulation mode: accurately wait for playback duration in increments
        elapsed = 0.0
        step = 0.05
        while elapsed < duration and self._playing:
            wait_time = min(step, duration - elapsed)
            await asyncio.sleep(wait_time)
            elapsed += wait_time

    def stop(self) -> None:
        """Immediately stop and cancel any ongoing playback."""
        self._playing = False
        if self._playback_task and not self._playback_task.done():
            self._playback_task.cancel()
            self._playback_task = None
        try:
            import sounddevice as sd  # type: ignore

            sd.stop()
        except Exception:
            pass
