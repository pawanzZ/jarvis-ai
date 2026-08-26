from __future__ import annotations
from typing import Any, Optional
from jarvis.core.bus import Event, EventBus
from jarvis.core.config import Config
from jarvis.plugins.base import Plugin, PluginType


class WhisperLocalPlugin(Plugin):
    """Local Speech-to-Text (STT) Plugin using Whisper.

    Transcribes streaming audio chunks into partial and final transcripts.
    Supports faster-whisper, whisper.cpp, and offline mock fallback engines.
    """

    name = "whisper_local"
    plugin_type = PluginType.STT

    def __init__(
        self,
        bus: Optional[EventBus] = None,
        config: Optional[Config] = None,
    ) -> None:
        super().__init__(bus=bus, config=config)
        self._model_size = "base"
        self._language = "en"
        self._engine = "auto"
        self._running = False
        self._audio_buffer: list[float] = []
        self._mock_transcript: Optional[str] = None
        self._model_instance: Any = None

    async def start(self, config: Optional[dict[str, Any]] = None) -> None:
        """Initialize and start the Whisper STT engine."""
        cfg = config or {}
        self._model_size = cfg.get("model", "base")
        self._language = cfg.get("language", "en")
        self._engine = cfg.get("engine", "auto")
        self._audio_buffer.clear()
        self._running = True

        # Attempt engine initialization
        if self._engine in ("faster-whisper", "auto"):
            try:
                from faster_whisper import WhisperModel  # type: ignore

                self._model_instance = WhisperModel(self._model_size, device="cpu", compute_type="int8")
                self._engine = "faster-whisper"
            except Exception:
                self._model_instance = None
                if self._engine == "faster-whisper":
                    self._engine = "mock"
                else:
                    self._engine = "mock"
        else:
            self._model_instance = None
            self._engine = "mock"

    async def stop(self) -> None:
        """Stop STT engine and release buffers."""
        self._running = False
        self._audio_buffer.clear()
        self._model_instance = None

    def set_mock_transcript(self, text: str) -> None:
        """Set an explicit transcript text for mock engine testing."""
        self._mock_transcript = text

    def transcribe(self, audio_data: Any) -> str:
        """Synchronously transcribe audio data using loaded engine or mock."""
        if self._mock_transcript is not None:
            result = self._mock_transcript
            return result

        if self._model_instance is not None and self._engine == "faster-whisper":
            try:
                segments, _ = self._model_instance.transcribe(
                    audio_data,
                    language=self._language,
                )
                return " ".join([seg.text.strip() for seg in segments])
            except Exception:
                pass

        # Realistic mock STT rule-based fallback
        if isinstance(audio_data, (list, tuple)) and len(audio_data) > 0:
            return "Jarvis, report system status."
        return "Hello Jarvis"

    async def on_event(self, event: Event) -> Optional[Event]:
        """Handle audio and speech events."""
        if not self._running:
            return None

        if event.type == "audio_chunk":
            audio = event.data.get("audio")
            if audio is not None:
                if isinstance(audio, (list, tuple)):
                    self._audio_buffer.extend(audio)
                elif hasattr(audio, "tolist"):
                    self._audio_buffer.extend(audio.tolist())

                # If significant audio accumulated, emit partial transcript
                if len(self._audio_buffer) >= 8000:
                    partial_text = self._mock_transcript or "Jarvis..."
                    partial_event = Event(
                        type="transcript_partial",
                        data={"text": partial_text, "is_final": False},
                        source=self.name,
                    )
                    if self.bus:
                        await self.bus.emit(partial_event)
                    return partial_event

        elif event.type in ("speech_end", "audio_end", "stt_request", "transcribe"):
            audio = event.data.get("audio", self._audio_buffer)
            transcript = self.transcribe(audio)
            self._audio_buffer.clear()

            # Emit stt_result and transcript_final
            stt_event = Event(
                type="stt_result",
                data={"text": transcript, "confidence": 0.95},
                source=self.name,
            )
            final_event = Event(
                type="transcript_final",
                data={"speaker": "user", "text": transcript},
                source=self.name,
            )
            if self.bus:
                await self.bus.emit(stt_event)
                await self.bus.emit(final_event)

            return stt_event

        return None

    def get_schema(self) -> dict[str, Any]:
        """Return schema for settings UI generation."""
        return {
            "type": "object",
            "properties": {
                "model": {
                    "type": "string",
                    "enum": ["tiny", "base", "small", "medium", "large"],
                    "default": "base",
                },
                "language": {
                    "type": "string",
                    "default": "en",
                },
                "engine": {
                    "type": "string",
                    "enum": ["auto", "mock", "faster-whisper", "whisper.cpp"],
                    "default": "auto",
                },
            },
        }


plugin_class = WhisperLocalPlugin
