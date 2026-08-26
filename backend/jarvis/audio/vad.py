from __future__ import annotations
import math
import struct
from typing import Any, Sequence


class VAD:
    """Voice Activity Detector (VAD).

    Calculates audio frame energy / RMS amplitude and detects speech vs silence boundaries
    with configurable thresholding, speech-onset verification, and hangover frame smoothing.
    """

    def __init__(
        self,
        threshold: float = 0.02,
        sample_rate: int = 16000,
        frame_size: int = 512,
        hangover_frames: int = 10,
        min_speech_frames: int = 2,
    ) -> None:
        self.threshold = float(threshold)
        self.sample_rate = int(sample_rate)
        self.frame_size = int(frame_size)
        self.hangover_frames = int(hangover_frames)
        self.min_speech_frames = int(min_speech_frames)

        # Stateful tracking
        self._in_speech: bool = False
        self._consecutive_speech: int = 0
        self._consecutive_silence: int = 0

    @property
    def in_speech(self) -> bool:
        """Return whether currently in an active speech segment."""
        return self._in_speech

    def calculate_energy(self, chunk: Any) -> float:
        """Calculate normalized RMS energy (0.0 to 1.0) of an audio chunk.

        Supports numpy arrays, lists/iterables of floats/ints, and PCM bytes.
        """
        if chunk is None:
            return 0.0

        # Case 1: numpy array or array-like object with .size / .mean / .astype
        if hasattr(chunk, "__array__") or type(chunk).__name__ == "ndarray":
            try:
                import numpy as np  # type: ignore

                arr = np.asarray(chunk, dtype=np.float32)
                if arr.size == 0:
                    return 0.0
                # If int16 scale (e.g. max > 1.0)
                max_val = np.max(np.abs(arr))
                if max_val > 1.0:
                    arr = arr / 32768.0
                rms = float(np.sqrt(np.mean(arr**2)))
                return min(1.0, max(0.0, rms))
            except Exception:
                pass

        # Case 2: bytes / bytearray (assume 16-bit signed integer PCM by default)
        if isinstance(chunk, (bytes, bytearray, memoryview)):
            raw_bytes = bytes(chunk)
            if len(raw_bytes) < 2:
                return 0.0
            num_samples = len(raw_bytes) // 2
            try:
                samples = struct.unpack(f"<{num_samples}h", raw_bytes[: num_samples * 2])
                sum_sq = sum((s / 32768.0) ** 2 for s in samples)
                rms = math.sqrt(sum_sq / num_samples)
                return min(1.0, max(0.0, rms))
            except Exception:
                return 0.0

        # Case 3: Sequence of numbers (float or int)
        if isinstance(chunk, (list, tuple)):
            if not chunk:
                return 0.0
            length = len(chunk)
            # Detect scale
            first_vals = chunk[: min(10, length)]
            is_int16 = any(abs(v) > 1.5 for v in first_vals if isinstance(v, (int, float)))
            scale = 32768.0 if is_int16 else 1.0

            sum_sq = 0.0
            for val in chunk:
                try:
                    norm_val = float(val) / scale
                    sum_sq += norm_val * norm_val
                except (ValueError, TypeError):
                    continue
            rms = math.sqrt(sum_sq / max(1, length))
            return min(1.0, max(0.0, rms))

        # Case 4: Single numeric scalar
        if isinstance(chunk, (int, float)):
            val = float(chunk)
            if abs(val) > 1.5:
                val /= 32768.0
            return min(1.0, max(0.0, abs(val)))

        return 0.0

    def is_speech(self, chunk: Any) -> bool:
        """Determine if an audio chunk contains speech based on energy threshold."""
        energy = self.calculate_energy(chunk)
        return energy >= self.threshold

    def process_frame(self, chunk: Any) -> dict[str, Any]:
        """Process a single audio frame and return speech boundary detection metrics.

        Returns:
            dict containing:
            - is_speech (bool): Current frame is voiced
            - energy (float): Normalized RMS energy
            - in_speech (bool): System is currently in a sustained speech segment
            - speech_started (bool): Transitioned into speech on this frame
            - speech_ended (bool): Transitioned out of speech on this frame
        """
        energy = self.calculate_energy(chunk)
        frame_voiced = energy >= self.threshold

        speech_started = False
        speech_ended = False

        if frame_voiced:
            self._consecutive_speech += 1
            self._consecutive_silence = 0
            if not self._in_speech and self._consecutive_speech >= self.min_speech_frames:
                self._in_speech = True
                speech_started = True
        else:
            self._consecutive_silence += 1
            self._consecutive_speech = 0
            if self._in_speech and self._consecutive_silence >= self.hangover_frames:
                self._in_speech = False
                speech_ended = True

        return {
            "is_speech": frame_voiced,
            "energy": energy,
            "in_speech": self._in_speech,
            "speech_started": speech_started,
            "speech_ended": speech_ended,
        }

    def reset(self) -> None:
        """Reset state tracking."""
        self._in_speech = False
        self._consecutive_speech = 0
        self._consecutive_silence = 0
