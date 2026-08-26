from __future__ import annotations
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from jarvis.core.bus import Event, EventBus
    from jarvis.core.config import Config
else:
    from jarvis.core.bus import Event


class PluginType(str, Enum):
    STT = "stt"
    TTS = "tts"
    LLM = "llm"
    WAKE_WORD = "wake_word"
    ACTIVATION = "activation"
    VISION = "vision"


class Plugin(ABC):
    name: str = "unnamed"
    plugin_type: PluginType = PluginType.STT

    def __init__(
        self,
        bus: Optional[EventBus] = None,
        config: Optional[Config] = None,
    ) -> None:
        self.bus = bus
        self.config = config

    @abstractmethod
    async def start(self, config: Optional[dict[str, Any]] = None) -> None:
        """Start the plugin with optional configuration dict."""
        ...

    @abstractmethod
    async def stop(self) -> None:
        """Stop the plugin and release resources."""
        ...

    @abstractmethod
    async def on_event(self, event: Event) -> Optional[Event]:
        """Handle incoming event and optionally return a response event."""
        ...

    @abstractmethod
    def get_schema(self) -> dict[str, Any]:
        """Return JSON schema describing configuration options for UI generation."""
        ...
