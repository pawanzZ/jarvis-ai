from __future__ import annotations
import asyncio
import pytest
from jarvis.core.bus import Event, EventBus
from jarvis.plugins.base import PluginType
from jarvis.plugins.builtins.ollama_llm import OllamaLLMPlugin


@pytest.mark.asyncio
async def test_ollama_plugin_metadata_and_schema():
    plugin = OllamaLLMPlugin()
    assert plugin.name == "ollama_llm"
    assert plugin.plugin_type == PluginType.LLM

    schema = plugin.get_schema()
    assert "properties" in schema
    assert "model" in schema["properties"]
    assert "base_url" in schema["properties"]
    assert "temperature" in schema["properties"]
    assert "system_prompt" in schema["properties"]


@pytest.mark.asyncio
async def test_ollama_start_stop():
    plugin = OllamaLLMPlugin()
    await plugin.start(
        {
            "model": "mistral",
            "base_url": "http://127.0.0.1:11434",
            "temperature": 0.5,
            "system_prompt": "Custom Jarvis prompt",
        }
    )
    assert plugin._running is True
    assert plugin._model == "mistral"
    assert plugin._base_url == "http://127.0.0.1:11434"
    assert plugin._temperature == 0.5
    assert plugin._system_prompt == "Custom Jarvis prompt"

    await plugin.stop()
    assert plugin._running is False


@pytest.mark.asyncio
async def test_ollama_mock_response_override():
    plugin = OllamaLLMPlugin()
    await plugin.start({})

    plugin.set_mock_response("arm suit", "Suit deployment sequence activated, sir.")
    tokens = []
    async for token in plugin.generate_stream("Please arm suit now"):
        tokens.append(token)

    full = "".join(tokens).strip()
    assert full == "Suit deployment sequence activated, sir."

    await plugin.stop()


@pytest.mark.asyncio
async def test_ollama_offline_conversational_queries():
    plugin = OllamaLLMPlugin()
    await plugin.start({})

    # Test status query
    status_tokens = [t async for t in plugin.generate_stream("system status")]
    assert "ARC reactor" in "".join(status_tokens) or "online" in "".join(status_tokens).lower()

    # Test identity query
    who_tokens = [t async for t in plugin.generate_stream("who are you")]
    assert "JARVIS" in "".join(who_tokens)

    # Test greeting query
    hello_tokens = [t async for t in plugin.generate_stream("hello jarvis")]
    assert "Greetings" in "".join(hello_tokens) or "assist" in "".join(hello_tokens).lower()

    # Test real-time weather query using OS location and weather API
    weather_tokens = [t async for t in plugin.generate_stream("what is the weather outside?")]
    weather_resp = "".join(weather_tokens).lower()
    assert any(w in weather_resp for w in ("atmospheric", "conditions", "temperature", "°c", "degrees", "humidity", "wind"))

    # Test OS location query
    loc_tokens = [t async for t in plugin.generate_stream("where am i right now?")]
    loc_resp = "".join(loc_tokens).lower()
    assert any(w in loc_resp for w in ("geolocation", "stationed", "india", "hyderabad", "coordinates", "sector"))

    await plugin.stop()


@pytest.mark.asyncio
async def test_ollama_event_handling_and_token_streaming():
    bus = EventBus()
    bus_task = asyncio.create_task(bus.process())
    plugin = OllamaLLMPlugin(bus=bus)
    await plugin.start({})

    streamed_tokens = []
    emitted_responses = []

    async def _on_token(ev: Event):
        streamed_tokens.append(ev.data["token"])

    async def _on_resp(ev: Event):
        emitted_responses.append(ev)

    bus.on("llm_token", _on_token)
    bus.on("llm_response", _on_resp)
    bus.on("response_complete", _on_resp)

    # Request via llm_request event
    result = await plugin.on_event(
        Event(type="llm_request", data={"prompt": "System check"})
    )

    assert result is not None
    assert result.type == "response_complete"
    assert "text" in result.data

    # Allow bus to dispatch
    await asyncio.sleep(0.05)

    assert len(streamed_tokens) > 0
    assert len(emitted_responses) == 2

    # Check llm_response event
    assert emitted_responses[0].type == "llm_response"
    assert emitted_responses[0].data["model"] == "llama3"

    await plugin.stop()
    bus_task.cancel()
    try:
        await bus_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_ollama_ignores_when_stopped():
    plugin = OllamaLLMPlugin()
    resp = await plugin.on_event(Event(type="llm_request", data={"prompt": "hello"}))
    assert resp is None
