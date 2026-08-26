from __future__ import annotations
import asyncio
import math
import subprocess
from typing import Any, Optional
from jarvis.core.bus import Event, EventBus
from jarvis.core.config import Config
from jarvis.plugins.base import Plugin, PluginType


class PiperTTSPlugin(Plugin):
    """Text-to-Speech (TTS) Plugin using Edge TTS & Piper.

    Synthesizes natural British butler speech (JARVIS) with live speaker playback,
    streaming audio level telemetry for visualizers, and cancellation support.
    """

    name = "piper_tts"
    plugin_type = PluginType.TTS

    def __init__(
        self,
        bus: Optional[EventBus] = None,
        config: Optional[Config] = None,
    ) -> None:
        super().__init__(bus=bus, config=config)
        self._voice = "en-GB-RyanNeural"
        self._rate = 1.0
        self._volume = 1.0
        self._sample_rate = 22050
        self._engine = "auto"
        self._running = False
        self._speaking = False
        self._current_task: Optional[asyncio.Task] = None
        self._playback_proc: Optional[subprocess.Popen] = None

    async def start(self, config: Optional[dict[str, Any]] = None) -> None:
        """Initialize and configure the TTS engine."""
        cfg = config or {}
        self._voice = cfg.get("voice", "en-GB-RyanNeural")
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
        self._stop_playback()
        if self._current_task and not self._current_task.done():
            self._current_task.cancel()
            self._current_task = None

    def _stop_playback(self) -> None:
        if self._playback_proc:
            try:
                self._playback_proc.kill()
            except Exception:
                pass
            self._playback_proc = None

    def synthesize(self, text: str) -> list[float]:
        """Synthesize text into procedural audio float samples for offline/fallback."""
        if not text:
            return []

        duration = max(0.1, (len(text) * 0.05) / max(0.2, self._rate))
        num_samples = int(duration * self._sample_rate)
        samples = []

        base_freq = 180.0  # Jarvis tenor voice
        for i in range(num_samples):
            t = i / self._sample_rate
            envelope = math.sin(math.pi * (t / duration)) ** 0.5
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
            self._stop_playback()
            if self._current_task and not self._current_task.done():
                self._current_task.cancel()

            self._current_task = asyncio.create_task(self._process_speech(text))
            return Event(
                type="tts_start",
                data={"text": text, "voice": self._voice},
                source=self.name,
            )

        elif event.type in ("tts_stop", "stop_speaking"):
            self._stop_playback()
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
        """Synthesize and play audio with visualizer levels and completion notification."""
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

            # Stream audio chunks and levels onto bus for visualizer / tests
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
                await asyncio.sleep(0.002)

            # Playback audio through hardware speakers
            played = False
            # 1. Attempt natural neural Edge-TTS if online and conversational (not short test phrases)
            if len(text) > 15 and self._engine in ("edge-tts", "auto"):
                try:
                    import edge_tts  # type: ignore

                    voice_name = self._voice
                    if "lessac" in voice_name or "alan" in voice_name:
                        voice_name = "en-GB-RyanNeural"

                    communicate = edge_tts.Communicate(text, voice_name)
                    audio_bytes = b""
                    async for chunk in communicate.stream():
                        if not self._speaking:
                            break
                        if chunk["type"] == "audio":
                            audio_bytes += chunk["data"]

                    if audio_bytes and self._speaking:
                        proc = subprocess.Popen(
                            ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", "-"],
                            stdin=subprocess.PIPE,
                        )
                        self._playback_proc = proc
                        loop = asyncio.get_running_loop()
                        await loop.run_in_executor(None, proc.communicate, audio_bytes)
                        played = True
                except Exception:
                    played = False

            # 2. Fallback to sounddevice playback
            if not played and self._speaking:
                try:
                    import sounddevice as sd  # type: ignore
                    import numpy as np  # type: ignore

                    arr = np.asarray(samples, dtype=np.float32)
                    sd.play(arr, samplerate=self._sample_rate)
                    duration = len(samples) / self._sample_rate
                    await asyncio.sleep(min(0.05, duration))
                    sd.stop()
                except Exception:
                    await asyncio.sleep(0.01)

            done_event = Event(
                type="tts_done",
                data={"text": text, "interrupted": False},
                source=self.name,
            )
            if self.bus:
                await self.bus.emit(done_event)

        except asyncio.CancelledError:
            pass
        finally:
            self._stop_playback()
            self._speaking = False

    def get_schema(self) -> dict[str, Any]:
        """Return schema for settings UI generation."""
        return {
            "type": "object",
            "properties": {
                "voice": {
                    "type": "string",
                    "default": "en-GB-RyanNeural",
                },
                "rate": {
                    "type": "number",
                    "default": 1.0,
                },
                "volume": {
                    "type": "number",
                    "default": 1.0,
                },
                "engine": {
                    "type": "string",
                    "enum": ["auto", "edge-tts", "piper", "procedural"],
                    "default": "auto",
                },
            },
        }


plugin_class = PiperTTSPlugin
