from __future__ import annotations
import asyncio
import math
import time
from typing import Any, AsyncIterator, Optional, Sequence


class MicStream:
    """Microphone Audio Stream.

    Provides streaming audio chunk capture with automatic hardware detection
    and fallback to synthetic audio simulation if sounddevice or hardware is unavailable.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        chunk_size: int = 1024,
        channels: int = 1,
        device: Optional[int | str] = None,
        simulate: bool = False,
    ) -> None:
        self.sample_rate = int(sample_rate)
        self.chunk_size = int(chunk_size)
        self.channels = int(channels)
        self.device = device
        self._simulate = bool(simulate)

        self._running: bool = False
        self._queue: asyncio.Queue[list[float]] = asyncio.Queue(maxsize=100)
        self._sd_stream: Any = None
        self._sim_task: Optional[asyncio.Task] = None
        self._phase: float = 0.0

    @property
    def is_recording(self) -> bool:
        """Return True if the microphone stream is actively recording."""
        return self._running

    def get_is_recording(self) -> bool:
        """Compatibility getter for is_recording."""
        return self._running

    async def start(self) -> None:
        """Start capturing audio chunks."""
        if self._running:
            return

        self._running = True
        # Clear queue
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break

        if not self._simulate:
            try:
                import sounddevice as sd  # type: ignore

                loop = asyncio.get_running_loop()

                def _callback(indata: Any, frames: int, time_info: Any, status: Any) -> None:
                    if not self._running:
                        return
                    # Convert to flat float list
                    flat = indata[:, 0].tolist() if indata.ndim > 1 else indata.tolist()
                    try:
                        loop.call_soon_threadsafe(
                            lambda: self._queue.put_nowait(flat)
                            if not self._queue.full()
                            else None
                        )
                    except Exception:
                        pass

                self._sd_stream = sd.InputStream(
                    samplerate=self.sample_rate,
                    blocksize=self.chunk_size,
                    channels=self.channels,
                    dtype="float32",
                    device=self.device,
                    callback=_callback,
                )
                self._sd_stream.start()
            except Exception:
                # Hardware / driver unavailable -> fallback to simulation
                self._sd_stream = None
                self._simulate = True

        if self._simulate:
            self._sim_task = asyncio.create_task(self._sim_loop())

    async def stop(self) -> None:
        """Stop capturing audio chunks."""
        self._running = False

        if self._sim_task:
            self._sim_task.cancel()
            try:
                await self._sim_task
            except (asyncio.CancelledError, Exception):
                pass
            self._sim_task = None

        if self._sd_stream:
            try:
                self._sd_stream.stop()
                self._sd_stream.close()
            except Exception:
                pass
            self._sd_stream = None

    async def feed_chunk(self, chunk: Sequence[float]) -> None:
        """Manually inject an audio chunk into the stream (useful for testing and pipeline wiring)."""
        if not self._running:
            self._running = True
        try:
            self._queue.put_nowait(list(chunk))
        except asyncio.QueueFull:
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
            self._queue.put_nowait(list(chunk))

    async def read_chunk(self, timeout: Optional[float] = 0.5) -> list[float]:
        """Read a single audio chunk from the stream.

        Returns a list of float audio samples of length chunk_size.
        """
        if not self._running:
            return [0.0] * self.chunk_size

        try:
            if timeout is not None:
                return await asyncio.wait_for(self._queue.get(), timeout=timeout)
            return await self._queue.get()
        except asyncio.TimeoutError:
            # Generate ambient low-noise simulated chunk on timeout
            return self._generate_simulated_chunk(amplitude=0.001)

    async def chunks(self) -> AsyncIterator[list[float]]:
        """Async iterator yielding chunks continuously while recording."""
        while self._running:
            chunk = await self.read_chunk(timeout=0.2)
            yield chunk

    def _generate_simulated_chunk(self, amplitude: float = 0.005) -> list[float]:
        """Generate a synthetic chunk with slight oscillation/noise."""
        chunk = []
        freq = 440.0
        delta = (2.0 * math.pi * freq) / self.sample_rate
        for _ in range(self.chunk_size):
            sample = math.sin(self._phase) * amplitude
            self._phase = (self._phase + delta) % (2.0 * math.pi)
            chunk.append(sample)
        return chunk

    async def _sim_loop(self) -> None:
        """Background generator feeding simulated audio frames at real-time intervals."""
        frame_interval = self.chunk_size / self.sample_rate
        while self._running:
            chunk = self._generate_simulated_chunk(amplitude=0.002)
            if not self._queue.full():
                self._queue.put_nowait(chunk)
            await asyncio.sleep(frame_interval)
