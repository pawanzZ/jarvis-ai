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
from jarvis.system.monitor import get_system_monitor


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

    def _is_weather_query(self, prompt: str) -> bool:
        clean = prompt.lower()
        keywords = (
            "weather", "forecast", "temperature", "rain", "raining", "snow",
            "sunny", "cloudy", "overcast", "climate", "outside", "hot outside",
            "cold outside", "humidity", "wind speed", "precipitation", "umbrella",
            "how warm", "how cold", "degrees"
        )
        return any(w in clean for w in keywords)

    def _is_location_query(self, prompt: str) -> bool:
        clean = prompt.lower()
        keywords = (
            "where am i", "where are we", "my location", "current location",
            "what city", "current city", "what country", "our coordinates"
        )
        return any(w in clean for w in keywords)

    async def _resolve_weather_data(self, prompt: str) -> dict[str, Any]:
        """Fetch real-time weather using OS location and weather Open APIs."""
        monitor = get_system_monitor()

        # Check if user mentioned a specific other city, e.g. "weather in Tokyo"
        clean = prompt.lower()
        city_match = None
        match = re.search(r"\b(?:in|for|at)\s+([a-zA-Z\s]+?)(?:\?|\.|$|\s+today|\s+now|\s+tomorrow)", clean)
        if match:
            cand = match.group(1).strip()
            if cand not in (
                "the area", "my area", "my city", "the city", "here",
                "the world", "this location", "this city", "now", "today"
            ) and len(cand) >= 3:
                city_match = cand

        if city_match:
            try:
                data = await monitor.fetch_weather_for_city(city_match)
                if data and data.get("city"):
                    return data
            except Exception:
                pass

        # Use OS location and Open-Meteo API
        cached = monitor.get_weather_telemetry()
        if not cached.get("last_updated") or (time.time() - cached.get("last_updated", 0)) > 60:
            try:
                fresh = await monitor.fetch_weather_and_location()
                if fresh:
                    cached = fresh
            except Exception:
                pass

        return cached

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

        # Check if this query is about weather or location and resolve live data
        weather_data: Optional[dict[str, Any]] = None
        if self._is_weather_query(lower_prompt) or self._is_location_query(lower_prompt):
            weather_data = await self._resolve_weather_data(lower_prompt)
            # Emit live weather event so HUD updates in real-time
            if self.bus and weather_data:
                try:
                    await self.bus.emit(Event(type="weather_telemetry", data=weather_data, source="weather_query"))
                except Exception:
                    pass

        # 2. Attempt real Ollama HTTP streaming (skip in pytest automated test suite)
        ollama_succeeded = False
        if not os.environ.get("PYTEST_CURRENT_TEST"):
            system_prompt = self._system_prompt
            if weather_data:
                city = weather_data.get("city", "HYDERABAD").title()
                region = weather_data.get("region", "TELANGANA").title()
                country = weather_data.get("country", "INDIA").title()
                t_c = weather_data.get("temp_c", 28)
                t_f = weather_data.get("temp_f", 82)
                feels_like = weather_data.get("feels_like_c", t_c)
                cond = weather_data.get("condition", "OVERCAST").title()
                hum = weather_data.get("humidity", 65)
                wind = weather_data.get("wind_kmph", 10)

                system_prompt += (
                    f"\n[Real-Time OS Geolocation & Weather Telemetry]\n"
                    f"- Location: {city}, {region}, {country}\n"
                    f"- Weather Condition: {cond}\n"
                    f"- Temperature: {t_c}°C ({t_f}°F) (Feels like {feels_like}°C)\n"
                    f"- Relative Humidity: {hum}%\n"
                    f"- Wind Speed: {wind} km/h\n"
                    f"- Rule: Answer the user's weather/location question with these exact real-time numbers, "
                    f"in Jarvis's concise, polite, and witty persona."
                )

            api_url = f"{self._base_url}/api/generate"
            payload = json.dumps(
                {
                    "model": self._model,
                    "prompt": prompt,
                    "system": system_prompt,
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
                    return urllib.request.urlopen(req, timeout=30.0)

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
            fallback_text = self._get_offline_response(prompt, weather_data=weather_data)
            words = fallback_text.split(" ")
            for i, word in enumerate(words):
                token = word if i == 0 else f" {word}"
                yield token
                await asyncio.sleep(0.02)

    def _get_offline_response(self, prompt: str, weather_data: Optional[dict[str, Any]] = None) -> str:
        """Generate an intelligent contextual offline response with Jarvis personality."""
        clean = prompt.lower().strip()

        # Real-time weather and OS geolocation queries (prioritized over general date/time)
        if self._is_weather_query(clean) or self._is_location_query(clean):
            w = weather_data or get_system_monitor().get_weather_telemetry()
            city = w.get("city", "HYDERABAD").title()
            region = w.get("region", "TELANGANA").title()
            country = w.get("country", "INDIA").title()
            t_c = w.get("temp_c", 28)
            t_f = w.get("temp_f", 82)
            feels_like = w.get("feels_like_c", t_c)
            cond = w.get("condition", "OVERCAST").title()
            hum = w.get("humidity", 65)
            wind = w.get("wind_kmph", 10)

            if self._is_weather_query(clean):
                return (
                    f"Atmospheric telemetry for {city}, {region} ({country}) reports {cond} conditions "
                    f"at {t_c}°C ({t_f}°F) with a feels-like of {feels_like}°C, {hum}% relative humidity, "
                    f"and wind speeds of {wind} km/h, sir."
                )
            if self._is_location_query(clean):
                return (
                    f"OS geolocation telemetry indicates we are currently stationed in {city}, {region}, {country}, sir."
                )

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
        if any(w in clean for w in ("what date", "today's date", "current date", "what day is it", "day of the week", "date is it")) or clean in ("date", "today"):
            now_date = datetime.datetime.now().strftime("%A, %B %d, %Y")
            return f"Today is {now_date}, sir."

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
