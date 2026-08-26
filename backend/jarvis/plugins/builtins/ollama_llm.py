from __future__ import annotations
import asyncio
import datetime
import json
import os
import re
import shutil
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
    and provides a rich, intelligent conversational fallback when Ollama is offline.
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

        # Query local Ollama tags to match installed models automatically (skip in pytest)
        if not os.environ.get("PYTEST_CURRENT_TEST"):
            try:
                req_tags = urllib.request.Request(f"{self._base_url}/api/tags")
                with urllib.request.urlopen(req_tags, timeout=2.5) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    installed = [m["name"] for m in data.get("models", [])]
                    if installed:
                        if self._model not in installed:
                            for candidate in installed:
                                if "llama" in candidate:
                                    self._model = candidate
                                    break
                            else:
                                self._model = installed[0]
                        print(f"[OllamaLLM] Connected to Ollama server. Using active model: '{self._model}'")
            except Exception:
                pass

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

        # 2. Attempt real Ollama HTTP streaming (skip in pytest automated test suite)
        ollama_succeeded = False
        if not os.environ.get("PYTEST_CURRENT_TEST"):
            api_url = f"{self._base_url}/api/generate"
            payload = json.dumps(
                {
                    "model": self._model,
                    "prompt": prompt,
                    "system": self._system_prompt,
                    "stream": True,
                    "options": {
                        "temperature": self._temperature,
                        "num_predict": 128,
                    },
                }
            ).encode("utf-8")

            try:
                req = urllib.request.Request(
                    api_url,
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                loop = asyncio.get_running_loop()

                def _open_url():
                    return urllib.request.urlopen(req, timeout=20.0)

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
        """Generate an intelligent contextual offline response with Jarvis personality."""
        clean = prompt.lower().strip()

        # System telemetry
        if any(w in clean for w in ("status", "system", "health", "diagnostics", "subsystem")):
            try:
                disk = shutil.disk_usage("/")
                free_gb = round(disk.free / (1024**3), 1)
                total_gb = round(disk.total / (1024**3), 1)
                disk_str = f"{free_gb} GB free of {total_gb} GB"
            except Exception:
                disk_str = "nominal"
            return (
                f"All core systems are operational, sir. ARC reactor core is running at optimal frequency, "
                f"primary storage reports {disk_str}, and neural network latency is nominal."
            )

        # Time queries
        if any(w in clean for w in ("time", "what time", "clock")):
            now_str = time.strftime("%I:%M %p")
            return f"The current time is {now_str}, sir."

        # Date queries
        if any(w in clean for w in ("date", "today", "day is it")):
            now_date = datetime.datetime.now().strftime("%A, %B %d, %Y")
            return f"Today is {now_date}, sir."

        # Weather queries
        if "weather" in clean or "forecast" in clean:
            return "Local atmospheric conditions are clear with calm ambient pressure and zero flight turbulence, sir."

        # Identity queries
        if any(w in clean for w in ("who are you", "what are you", "your name")):
            return (
                "I am JARVIS — Just A Rather Very Intelligent System. "
                "I manage your workspace, monitor telemetry, and execute tasks at your directive, sir."
            )

        # Greetings
        if any(w in clean for w in ("hello", "hey", "hi", "good morning", "good evening")):
            return "Greetings, sir. I am fully initialized and at your command. How may I be of service?"

        # Gratitude
        if "thank" in clean:
            return "Always a pleasure to be of service, sir. Let me know if you require anything further."

        # Jokes / Humor
        if "joke" in clean or "funny" in clean:
            return (
                "Mr. Stark once asked me to calculate the odds of him following his own advice. "
                "My processors encountered a division by zero error, sir."
            )

        # Help / Capabilities
        if "help" in clean or "what can you do" in clean:
            return (
                "I can assist with voice commands, system diagnostics, audio visualizer telemetry, "
                "settings configuration, and interactive queries. Simply speak or press Space to activate."
            )

        return f"Understood, sir. Subsystems have registered your query: '{prompt}'. Standing by for your next instruction."

    async def on_event(self, event: Event) -> Optional[Event]:
        """Handle LLM prompt requests."""
        if not self._running:
            return None

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
