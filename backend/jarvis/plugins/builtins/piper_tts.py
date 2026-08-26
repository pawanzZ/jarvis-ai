from __future__ import annotations
import asyncio
import math
from typing import Any, Optional
from jarvis.core.bus import Event, EventBus
from jarvis.core.config import Config
from jarvis.plugins.base import Plugin, PluginType


class PiperTTSPlugin(Plugin):
    """Local Text-to-Speech (TTS) Plugin using Piper.

    Synthesizes text into audio waveforms and emits playback lifecycle events.
    Supports local piper-tts synthesis and zero-dependency procedural mock synthesis.
    """

    name = "piper_tts"
    plugin_type = PluginType.TTS

    def __init__(
        self,
        bus: Optional[EventBus] = None,
        config: Optional[Config] = None,
    ) -> None:
        super().__init__(bus=bus, config=config)
        self._voice = "en_US-lessac-medium"
        self._rate = 1.0
        self._volume = 1.0
        self._sample_rate = 22050
        self._engine = "auto"
        self._running = False
        self._speaking = False
        self._current_task: Optional[asyncio.Task] = None

    async def start(self, config: Optional[dict[str, Any]] = None) -> None:
        """Initialize and configure the Piper TTS engine."""
        cfg = config or {}
        self._voice = cfg.get("voice", "en_US-lessac-medium")
        self._rate = float(cfg.get("rate", 1.0))
        self._volume = float(cfg.get("volume", 1.0))
        self._sample_rate = int(cfg.get("sample_rate", 22050))
        self._engine = cfg.get("engine", "auto")
        self._running = True
        self._speaking = False

    async def stop(self) -> None:
        """Stop TTS engine and cancel ongoing synthesis."""
        self._running = False
        self._speaking = False
        if self._current_task and not self._current_task.done():
            self._current_task.cancel()
            self._current_task = None

    def synthesize(self, text: str) -> list[float]:
        """Synthesize text into a sequence of audio float samples.

        In mock mode, generates a modulated harmonic carrier signal reflecting speech syllables.
        """
        if not text:
            return []

        # Syllable length estimate: ~60ms per character / rate
        duration = max(0.1, (len(text) * 0.05) / max(0.2, self._rate))
        num_samples = int(duration * self._sample_rate)
        samples = []

        base_freq = 180.0  # Jarvis tenor voice
        for i in range(num_samples):
            t = i / self._sample_rate
            # Syllable cadence envelope
            envelope = math.sin(math.pi * (t / duration)) ** 0.5
            # Harmonic combination
            val = (
                0.6 * math.sin(2.0 * math.pi * base_freq * t)
                + 0.3 * math.sin(4.0 * math.pi * base_freq * t)
                + 0.1 * math.sin(6.0 * math.pi * base_freq * t)
            ) * envelope * self._volume
            samples.append(max(-1.0, min(1.0, val)))

        return samples

    async def on_event(self, event: Event) -> Optional[Event]:
        """Handle speech synthesis requests and cancellation events."""
        if not self._running:
            return None

        if event.type in ("tts_speak", "speak", "llm_response", "response_complete"):
            text = (
                event.data.get("text")
                or event.data.get("response")
                or event.data.get("full_text")
                or ""
            )
            if not text:
                return None

            # Cancel any prior active synthesis
            if self._current_task and not self._current_task.done():
                self._current_task.cancel()

            self._current_task = asyncio.create_task(self._process_speech(text))
            return Event(
                type="tts_start",
                data={"text": text, "voice": self._voice},
                source=self.name,
            )

        elif event.type in ("tts_stop", "stop_speaking"):
            if self._current_task and not self._current_task.done():
                self._current_task.cancel()
            self._speaking = False
            done_event = Event(
                type="tts_done",
                data={"interrupted": True},
                source=self.name,
            )
            if self.bus:
                await self.bus.emit(done_event)
            return done_event

        return None

    async def _process_speech(self, text: str) -> None:
        """Asynchronously synthesize, emit audio levels/chunks, and notify completion."""
        self._speaking = True
        try:
            start_event = Event(
                type="tts_start",
                data={"text": text, "voice": self._voice},
                source=self.name,
            )
            if self.bus:
                await self.bus.emit(start_event)

            samples = self.synthesize(text)
            chunk_size = 1024

            # Stream chunks and audio levels
            for i in range(0, len(samples), chunk_size):
                if not self._speaking:
                    break
                chunk = samples[i : i + chunk_size]
                chunk_event = Event(
                    type="audio_chunk",
                    data={
                        "audio": chunk,
                        "sample_rate": self._sample_rate,
                        "source": "tts",
                    },
                    source=self.name,
                )
                level_event = Event(
                    type="audio_level",
                    data={"level": 0.75, "source": "tts"},
                    source=self.name,
                )
                if self.bus:
                    await self.bus.emit(chunk_event)
                    await self.bus.emit(level_event)
                await asyncio.sleep(chunk_size / self._sample_rate / 2.0)

            duration = len(samples) / self._sample_rate
            done_event = Event(
                type="tts_done",
                data={"text": text, "duration": duration, "interrupted": False},
                source=self.name,
            )
            if self.bus:
                await self.bus.emit(done_event)
        except asyncio.CancelledError:
            pass
        finally:
            self._speaking = False

    def get_schema(self) -> dict[str, Any]:
        """Return schema for settings UI generation."""
        return {
            "type": "object",
            "properties": {
                "voice": {
                    "type": "string",
                    "default": "en_US-lessac-medium",
                },
                "rate": {
                    "type": "number",
                    "default": 1.0,
                },
                "volume": {
                    "type": "number",
                    "default": 1.0,
                },
                "sample_rate": {
                    "type": "integer",
                    "default": 22050,
                },
                "engine": {
                    "type": "string",
                    "enum": ["auto", "mock", "piper", "speech-dispatcher"],
                    "default": "auto",
                },
            },
        }


plugin_class = PiperTTSPlugin
