from __future__ import annotations
import asyncio
import json
import re
import time
import urllib.error
import urllib.request
from typing import Any, AsyncIterator, Optional
from jarvis.core.bus import Event, EventBus
from jarvis.core.config import Config
from jarvis.plugins.base import Plugin, PluginType


class OllamaLLMPlugin(Plugin):
    """Local Large Language Model (LLM) Plugin using Ollama.

    Connects to Ollama's local HTTP API with streaming token generation,
    and provides a conversational offline fallback when Ollama is unreachable.
    """

    name = "ollama_llm"
    plugin_type = PluginType.LLM

    def __init__(
        self,
        bus: Optional[EventBus] = None,
        config: Optional[Config] = None,
    ) -> None:
        super().__init__(bus=bus, config=config)
        self._model = "llama3"
        self._base_url = "http://localhost:11434"
        self._temperature = 0.7
        self._system_prompt = (
            "You are Jarvis, an advanced AI desktop assistant. "
            "You are witty, concise, loyal, and efficient."
        )
        self._running = False
        self._mock_responses: dict[str, str] = {}
        self._default_mock: Optional[str] = None

    async def start(self, config: Optional[dict[str, Any]] = None) -> None:
        """Initialize and configure the Ollama LLM client."""
        cfg = config or {}
        self._model = cfg.get("model", "llama3")
        self._base_url = cfg.get("base_url", "http://localhost:11434").rstrip("/")
        self._temperature = float(cfg.get("temperature", 0.7))
        self._system_prompt = cfg.get("system_prompt", self._system_prompt)
        self._running = True

    async def stop(self) -> None:
        """Stop the LLM plugin."""
        self._running = False

    def set_mock_response(self, pattern: str, response: str) -> None:
        """Register a canned mock response for testing."""
        self._mock_responses[pattern.lower()] = response

    def set_default_mock(self, response: Optional[str]) -> None:
        """Set fallback mock response."""
        self._default_mock = response

    async def generate_stream(self, prompt: str) -> AsyncIterator[str]:
        """Stream tokens from Ollama API or conversational offline fallback."""
        # 1. Check custom test mocks
        lower_prompt = prompt.lower().strip()
        for pattern, resp in self._mock_responses.items():
            if pattern in lower_prompt:
                words = resp.split(" ")
                for i, word in enumerate(words):
                    token = word if i == 0 else f" {word}"
                    yield token
                    await asyncio.sleep(0.01)
                return

        if self._default_mock is not None:
            words = self._default_mock.split(" ")
            for i, word in enumerate(words):
                token = word if i == 0 else f" {word}"
                yield token
                await asyncio.sleep(0.01)
            return

        # 2. Attempt real Ollama HTTP streaming
        api_url = f"{self._base_url}/api/generate"
        payload = json.dumps(
            {
                "model": self._model,
                "prompt": prompt,
                "system": self._system_prompt,
                "stream": True,
                "options": {"temperature": self._temperature},
            }
        ).encode("utf-8")

        ollama_succeeded = False
        try:
            req = urllib.request.Request(
                api_url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            # Run network call in executor to keep event loop unblocked
            loop = asyncio.get_running_loop()

            def _open_url():
                return urllib.request.urlopen(req, timeout=3.0)

            response = await loop.run_in_executor(None, _open_url)

            while self._running:
                line = await loop.run_in_executor(None, response.readline)
                if not line:
                    break
                data = json.loads(line.decode("utf-8"))
                token = data.get("response", "")
                if token:
                    ollama_succeeded = True
                    yield token
                if data.get("done", False):
                    break
        except Exception:
            ollama_succeeded = False

        # 3. Fallback to conversational Jarvis responses if Ollama is unreachable
        if not ollama_succeeded:
            fallback_text = self._get_offline_response(prompt)
            words = fallback_text.split(" ")
            for i, word in enumerate(words):
                token = word if i == 0 else f" {word}"
                yield token
                await asyncio.sleep(0.02)

    def _get_offline_response(self, prompt: str) -> str:
        """Generate a contextual offline response with Jarvis personality."""
        clean = prompt.lower()
        if "status" in clean or "system" in clean:
            return "All core subsystems online, sir. ARC reactor operating at nominal efficiency."
        if "time" in clean:
            now_str = time.strftime("%I:%M %p")
            return f"The current time is {now_str}, sir."
        if "weather" in clean:
            return "Atmospheric conditions are clear with zero turbulence detected."
        if "who are you" in clean or "what are you" in clean:
            return "I am JARVIS — Just A Rather Very Intelligent System, at your service."
        if "hello" in clean or "hey" in clean or "hi" in clean:
            return "Greetings, sir. How may I assist you today?"
        if "thank" in clean:
            return "Always a pleasure to be of service, sir."
        return f"Understood, sir. Processing request for: {prompt}"

    async def on_event(self, event: Event) -> Optional[Event]:
        """Handle LLM prompt requests."""
        if not self._running:
            return None

        # Accept llm_request, stt_result, or transcript_final
        if event.type in ("llm_request", "stt_result", "transcript_final"):
            prompt = (
                event.data.get("prompt")
                or event.data.get("text")
                or ""
            )
            if not prompt:
                return None

            full_tokens: list[str] = []
            async for token in self.generate_stream(prompt):
                full_tokens.append(token)
                token_event = Event(
                    type="llm_token",
                    data={"token": token},
                    source=self.name,
                )
                if self.bus:
                    await self.bus.emit(token_event)

            full_response = "".join(full_tokens).strip()

            llm_response_event = Event(
                type="llm_response",
                data={"text": full_response, "model": self._model},
                source=self.name,
            )
            complete_event = Event(
                type="response_complete",
                data={"text": full_response, "full_text": full_response},
                source=self.name,
            )

            if self.bus:
                await self.bus.emit(llm_response_event)
                await self.bus.emit(complete_event)

            return complete_event

        return None

    def get_schema(self) -> dict[str, Any]:
        """Return schema for settings UI generation."""
        return {
            "type": "object",
            "properties": {
                "model": {
                    "type": "string",
                    "default": "llama3",
                },
                "base_url": {
                    "type": "string",
                    "default": "http://localhost:11434",
                },
                "temperature": {
                    "type": "number",
                    "default": 0.7,
                },
                "system_prompt": {
                    "type": "string",
                    "default": self._system_prompt,
                },
            },
        }


plugin_class = OllamaLLMPlugin
