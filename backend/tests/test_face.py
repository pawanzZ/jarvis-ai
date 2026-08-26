from __future__ import annotations
import asyncio
import pytest
from jarvis.core.bus import Event, EventBus
from jarvis.plugins.base import PluginType
from jarvis.plugins.builtins.face_tracker import FaceTrackerPlugin


@pytest.mark.asyncio
async def test_face_plugin_metadata_and_schema():
    plugin = FaceTrackerPlugin()
    assert plugin.name == "face_tracker"
    assert plugin.plugin_type == PluginType.VISION

    schema = plugin.get_schema()
    assert "properties" in schema
    assert "camera" in schema["properties"]
    assert "min_confidence" in schema["properties"]


@pytest.mark.asyncio
async def test_face_start_stop():
    plugin = FaceTrackerPlugin()
    await plugin.start({"camera": 1, "min_confidence": 0.7})
    assert plugin._running is True
    assert plugin._camera_index == 1
    assert plugin._min_confidence == 0.7

    await plugin.stop()
    assert plugin._running is False
    assert plugin.is_face_detected is False


@pytest.mark.asyncio
async def test_face_telemetry_emission_and_data_structure():
    bus = EventBus()
    bus_task = asyncio.create_task(bus.process())
    plugin = FaceTrackerPlugin(bus=bus)
    await plugin.start({})

    emissions = []

    async def _capture(ev: Event):
        emissions.append(ev)

    bus.on("face_telemetry", _capture)
    bus.on("face_data", _capture)

    resp = await plugin.on_event(Event(type="vision_tick", data={}))
    assert resp is not None
    assert resp.type == "face_data"
    assert "gaze" in resp.data
    assert "head_pose" in resp.data
    assert "attention" in resp.data
    assert "detected" in resp.data

    await asyncio.sleep(0.05)

    assert len(emissions) >= 2
    types = [e.type for e in emissions]
    assert "face_telemetry" in types
    assert "face_data" in types

    await plugin.stop()
    bus_task.cancel()
    try:
        await bus_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_face_state_transitions_detected_and_lost():
    bus = EventBus()
    bus_task = asyncio.create_task(bus.process())
    plugin = FaceTrackerPlugin(bus=bus)
    await plugin.start({})

    transitions = []

    async def _capture(ev: Event):
        transitions.append(ev)

    bus.on("face_detected", _capture)
    bus.on("face_lost", _capture)

    # 1. Face detected
    plugin.set_mock_face_state(detected=True, gaze=[0.5, 0.5], pose={"yaw": 0.0, "pitch": 0.0, "roll": 0.0})
    await plugin.on_event(Event(type="poll_face", data={}))

    await asyncio.sleep(0.05)
    assert len(transitions) == 1
    assert transitions[0].type == "face_detected"
    assert transitions[0].data["attention"] is True

    # 2. Sustained detection (no redundant face_detected transition)
    await plugin.on_event(Event(type="poll_face", data={}))
    await asyncio.sleep(0.05)
    assert len(transitions) == 1

    # 3. Face lost
    plugin.set_mock_face_state(detected=False)
    await plugin.on_event(Event(type="poll_face", data={}))

    await asyncio.sleep(0.05)
    assert len(transitions) == 2
    assert transitions[1].type == "face_lost"

    await plugin.stop()
    bus_task.cancel()
    try:
        await bus_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_face_attention_calculation():
    plugin = FaceTrackerPlugin()
    await plugin.start({})

    # Case A: Looking straight at HUD -> Attention True
    plugin.set_mock_face_state(detected=True, gaze=[0.5, 0.5], pose={"yaw": 5.0, "pitch": -2.0, "roll": 0.0})
    resp_a = await plugin.on_event(Event(type="poll_face", data={}))
    assert resp_a.data["attention"] is True

    # Case B: Looking away (gaze far off to the side) -> Attention False
    plugin.set_mock_face_state(detected=True, gaze=[0.95, 0.5], pose={"yaw": 0.0, "pitch": 0.0, "roll": 0.0})
    resp_b = await plugin.on_event(Event(type="poll_face", data={}))
    assert resp_b.data["attention"] is False

    # Case C: Head turned far away (yaw = 45 deg) -> Attention False
    plugin.set_mock_face_state(detected=True, gaze=[0.5, 0.5], pose={"yaw": 45.0, "pitch": 0.0, "roll": 0.0})
    resp_c = await plugin.on_event(Event(type="poll_face", data={}))
    assert resp_c.data["attention"] is False

    await plugin.stop()


@pytest.mark.asyncio
async def test_face_ignores_when_stopped():
    plugin = FaceTrackerPlugin()
    resp = await plugin.on_event(Event(type="vision_tick", data={}))
    assert resp is None
