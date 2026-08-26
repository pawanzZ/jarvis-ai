import asyncio
import json
import os
import shutil
import sys
import tempfile
import traceback
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path("/home/pawan/Projects/jarvis-ai/backend")
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from jarvis.core.bus import Event, EventBus
from jarvis.core.state import StateMachine, JarvisState
from jarvis.core.config import Config
from jarvis.plugins.base import Plugin, PluginType
from jarvis.plugins.manager import PluginManager


results = []

def record(name: str, passed: bool, details: str = ""):
    status = "PASS" if passed else "FAIL"
    results.append({"name": name, "status": status, "details": details})
    print(f"[{status}] {name}: {details}")


# -------------------------------------------------------------
# Check 1: Config Atomic Persistence & Integrity
# -------------------------------------------------------------
def test_config_forensics():
    temp_dir = tempfile.mkdtemp(prefix="jarvis_cfg_audit_")
    try:
        cfg = Config(temp_dir)
        # 1.1 Atomic write & disk validation
        cfg.set("system", "theme", "iron_man")
        target_file = Path(temp_dir) / "config" / "system.json"
        assert target_file.exists(), "Target config file does not exist on disk"
        with open(target_file, "r", encoding="utf-8") as f:
            disk_data = json.load(f)
        assert disk_data == {"theme": "iron_man"}, f"Disk data mismatch: {disk_data}"
        
        # Verify no .tmp files linger
        tmp_files = list((Path(temp_dir) / "config").glob("*.tmp"))
        assert len(tmp_files) == 0, f"Lingering .tmp files found: {tmp_files}"
        
        # 1.2 Corrupt JSON recovery
        corrupt_file = Path(temp_dir) / "config" / "corrupt.json"
        corrupt_file.write_text("{{INVALID_JSON:::", encoding="utf-8")
        assert cfg.get_all("corrupt") == {}, "Corrupt file did not fallback to empty dict"
        assert cfg.get("corrupt", "key", "default_val") == "default_val", "Corrupt file fallback failed"
        
        # 1.3 Binary garbage recovery
        bin_file = Path(temp_dir) / "config" / "binary.json"
        bin_file.write_bytes(b"\x80\xFF\xFE\x00\x01\x02")
        assert cfg.get_all("binary") == {}, "Binary garbage did not fallback to empty dict"

        # 1.4 Nested namespaces
        cfg.set("plugins/llm/deep", "temperature", 0.7)
        nested_file = Path(temp_dir) / "config" / "plugins" / "llm" / "deep.json"
        assert nested_file.exists(), "Nested namespace directory/file not created"
        with open(nested_file, "r", encoding="utf-8") as f:
            nested_data = json.load(f)
        assert nested_data == {"temperature": 0.7}, f"Nested data mismatch: {nested_data}"

        # 1.5 Cache isolation
        data_copy = cfg.get_all("system")
        data_copy["theme"] = "hacked_theme"
        assert cfg.get("system", "theme") == "iron_man", "Cache leaked mutable reference"

        # 1.6 Namespace enumeration
        namespaces = cfg.list_namespaces()
        assert "system" in namespaces, "system namespace missing"
        assert "plugins/llm/deep" in namespaces or "deep" in namespaces, "nested namespace missing"

        record("Config Forensics (Atomic Writes, Corrupt Recovery, Nested Paths, Cache Isolation)", True, "All operations verified on disk")
    except Exception as e:
        record("Config Forensics (Atomic Writes, Corrupt Recovery, Nested Paths, Cache Isolation)", False, f"Exception: {traceback.format_exc()}")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


# -------------------------------------------------------------
# Check 2: Plugin Base ABC & Type Integrity
# -------------------------------------------------------------
def test_plugin_base_forensics():
    try:
        # 2.1 Enum values
        assert PluginType.STT.value == "stt"
        assert PluginType.TTS.value == "tts"
        assert PluginType.LLM.value == "llm"
        assert PluginType.WAKE_WORD.value == "wake_word"
        assert PluginType.ACTIVATION.value == "activation"
        assert PluginType.VISION.value == "vision"

        # 2.2 ABC instantiation prohibition
        try:
            Plugin()  # type: ignore
            instantiated = True
        except TypeError:
            instantiated = False
        assert not instantiated, "Abstract Plugin class was instantiated without error"

        # 2.3 Partial subclass instantiation prohibition
        class BadPlugin(Plugin):
            async def start(self, config=None): pass
            # missing stop, on_event, get_schema

        try:
            BadPlugin()  # type: ignore
            bad_instantiated = True
        except TypeError:
            bad_instantiated = False
        assert not bad_instantiated, "Incomplete Plugin subclass was instantiated without error"

        record("Plugin Base Forensics (ABC Contract, Enum Conformity)", True, "Abstract contracts strictly enforced by runtime")
    except Exception as e:
        record("Plugin Base Forensics (ABC Contract, Enum Conformity)", False, f"Exception: {traceback.format_exc()}")


# -------------------------------------------------------------
# Check 3: PluginManager Dynamic Discovery & Isolation
# -------------------------------------------------------------
async def test_plugin_manager_discovery_forensics():
    temp_dir = tempfile.mkdtemp(prefix="jarvis_plugins_audit_")
    try:
        p_dir = Path(temp_dir) / "plugins"
        p_dir.mkdir(parents=True, exist_ok=True)

        # 3.1 Normal plugin with plugin_class
        p1_code = """
from jarvis.plugins.base import Plugin, PluginType
from jarvis.core.bus import Event
from typing import Any, Optional

class CustomSTT(Plugin):
    name = "custom_stt"
    plugin_type = PluginType.STT
    def __init__(self, bus=None, config=None):
        super().__init__(bus, config)
        self.started = False
    async def start(self, config: Optional[dict[str, Any]] = None) -> None:
        self.started = True
    async def stop(self) -> None:
        self.started = False
    async def on_event(self, event: Event) -> Optional[Event]:
        if event.type == "audio_input":
            return Event(type="stt_result", data={"text": "hello jarvis"}, source=self.name)
        return None
    def get_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {"model": {"type": "string"}}}

plugin_class = CustomSTT
"""
        (p_dir / "custom_stt.py").write_text(p1_code, encoding="utf-8")

        # 3.2 Plugin without plugin_class variable (class inspection fallback)
        p2_code = """
from jarvis.plugins.base import Plugin, PluginType
from jarvis.core.bus import Event
from typing import Any, Optional

class DirectLLM(Plugin):
    name = "direct_llm"
    plugin_type = PluginType.LLM
    async def start(self, config: Optional[dict[str, Any]] = None) -> None: pass
    async def stop(self) -> None: pass
    async def on_event(self, event: Event) -> Optional[Event]: return None
    def get_schema(self) -> dict[str, Any]: return {"type": "object"}
"""
        (p_dir / "direct_llm.py").write_text(p2_code, encoding="utf-8")

        # 3.3 Broken syntax plugin (fault isolation)
        (p_dir / "broken_syntax.py").write_text("class Broken :::: def ??? invalid", encoding="utf-8")

        # 3.4 Private / dunder files (should be ignored)
        (p_dir / "__init__.py").write_text("# init", encoding="utf-8")
        (p_dir / "_internal.py").write_text("class Hidden: pass", encoding="utf-8")

        bus = EventBus()
        cfg = Config(temp_dir)
        mgr = PluginManager(bus, cfg)

        discovered = mgr.discover(p_dir)
        assert "custom_stt" in discovered, "custom_stt not discovered"
        assert "direct_llm" in discovered, "direct_llm not discovered via fallback"
        assert len(discovered) == 2, f"Expected exactly 2 discovered plugins, got: {discovered}"

        # Verify registration & DI
        p_stt = mgr.get_plugin("custom_stt")
        assert p_stt is not None, "custom_stt not in manager._plugins"
        assert p_stt.bus is bus, "EventBus not injected"
        assert p_stt.config is cfg, "Config not injected"

        record("PluginManager Dynamic Discovery & Fault Isolation", True, f"Discovered {discovered}, isolated broken syntax")
    except Exception as e:
        record("PluginManager Dynamic Discovery & Fault Isolation", False, f"Exception: {traceback.format_exc()}")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


# -------------------------------------------------------------
# Check 4: PluginManager Lifecycle & Event Routing Forensics
# -------------------------------------------------------------
async def test_plugin_manager_lifecycle_and_routing_forensics():
    temp_dir = tempfile.mkdtemp(prefix="jarvis_mgr_audit_")
    try:
        bus = EventBus()
        cfg = Config(temp_dir)
        mgr = PluginManager(bus, cfg)

        class EchoPlugin(Plugin):
            name = "echo_plugin"
            plugin_type = PluginType.TTS
            def __init__(self, bus=None, config=None):
                super().__init__(bus, config)
                self.started = False
                self.stopped = False
                self.cfg = None
            async def start(self, config=None):
                self.started = True
                self.cfg = config
            async def stop(self):
                self.stopped = True
                self.started = False
            async def on_event(self, event: Event) -> Optional[Event]:
                if event.type == "speak_cmd":
                    return Event(type="tts_done", data={"echo": event.data.get("text")}, source=self.name)
                return None
            def get_schema(self):
                return {"type": "object", "properties": {"rate": {"type": "number"}}}

        class CrashingPlugin(Plugin):
            name = "crashing_plugin"
            plugin_type = PluginType.VISION
            async def start(self, config=None): pass
            async def stop(self): pass
            async def on_event(self, event: Event) -> Optional[Event]:
                raise RuntimeError("Explosive vision crash")
            def get_schema(self):
                raise ValueError("Schema generation exploded")

        p_echo = EchoPlugin()
        p_crash = CrashingPlugin()
        mgr.register(p_echo)
        mgr.register(p_crash)

        # 4.1 Schema aggregation with error isolation
        schemas = mgr.get_schemas()
        assert "echo_plugin" in schemas, "echo_plugin schema missing"
        assert schemas["echo_plugin"]["properties"]["rate"]["type"] == "number"
        assert "crashing_plugin" in schemas, "crashing_plugin missing from schemas"
        assert schemas["crashing_plugin"] == {}, "Crashing schema did not fallback to empty dict"

        # 4.2 Activation & Config passing
        cfg.set("plugins", "echo_plugin", {"rate": 1.25})
        act_res = await mgr.activate("echo_plugin")
        assert act_res is True, "echo_plugin activation failed"
        assert p_echo.started is True, "echo_plugin start() was not called"
        assert p_echo.cfg == {"rate": 1.25}, f"Config not passed to start(): {p_echo.cfg}"
        assert mgr.get_active(PluginType.TTS) is p_echo
        assert mgr.get_active("tts") is p_echo

        await mgr.activate("crashing_plugin")

        # 4.3 Event routing & bus dispatch & fault isolation
        bus_received = []
        async def on_bus_tts_done(event: Event):
            bus_received.append(event)
        bus.on("tts_done", on_bus_tts_done)

        cmd_event = Event(type="speak_cmd", data={"text": "System operational"})
        responses = await mgr.route_event(cmd_event)

        assert len(responses) == 1, f"Expected 1 response, got {len(responses)}"
        assert responses[0].type == "tts_done"
        assert responses[0].data["echo"] == "System operational"

        # Check that event was put onto bus._queue
        bus_item = await asyncio.wait_for(bus._queue.get(), timeout=1.0)
        assert bus_item.type == "tts_done"
        assert bus_item.data["echo"] == "System operational"
        await on_bus_tts_done(bus_item)
        assert len(bus_received) == 1

        # 4.4 Deactivation & stop_all
        deact_res = await mgr.deactivate("echo_plugin")
        assert deact_res is True, "Deactivation failed"
        assert p_echo.stopped is True, "stop() not called on deactivation"
        assert mgr.get_active(PluginType.TTS) is None

        # Re-activate and stop_all
        await mgr.activate("echo_plugin")
        assert len(mgr.get_active_plugins()) == 2
        await mgr.stop_all()
        assert len(mgr.get_active_plugins()) == 0
        assert p_echo.stopped is True

        record("PluginManager Lifecycle, Event Routing & Fault Isolation", True, "Complete lifecycle, routing, bus emission, and fault isolation verified")
    except Exception as e:
        record("PluginManager Lifecycle, Event Routing & Fault Isolation", False, f"Exception: {traceback.format_exc()}")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


# -------------------------------------------------------------
# Check 5: Main Entry Point & WebSocket Command Wiring
# -------------------------------------------------------------
async def test_main_wiring_forensics():
    try:
        from jarvis.ws_server import WSServer
        bus = EventBus()
        state = StateMachine()
        server = WSServer(bus, state, port=8767)

        # Wire handlers as in __main__.py
        async def broadcast_state(old: JarvisState, new: JarvisState) -> None:
            await server.broadcast({
                "type": "state_change",
                "state": new.value,
                "data": {"state": new.value, "previous": old.value},
            })

        state.on_change(broadcast_state)

        async def handle_activate(event: Event) -> None:
            if state.state == JarvisState.IDLE:
                await state.transition(JarvisState.LISTENING)

        async def handle_deactivate(event: Event) -> None:
            if state.state != JarvisState.IDLE:
                await state.transition(JarvisState.IDLE)

        bus.on("activate", handle_activate)
        bus.on("deactivate", handle_deactivate)

        bus_task = asyncio.create_task(bus.process())

        # Simulate WS Client command: activate
        await server._on_message({"type": "command", "action": "activate"})
        await asyncio.sleep(0.05)
        assert state.state == JarvisState.LISTENING, f"Expected LISTENING, got {state.state}"

        # Simulate WS Client command: deactivate
        await server._on_message({"type": "command", "action": "deactivate"})
        await asyncio.sleep(0.05)
        assert state.state == JarvisState.IDLE, f"Expected IDLE, got {state.state}"

        bus_task.cancel()
        record("Main Architecture & WS Command Wiring Forensics", True, "WebSocket commands correctly trigger bus events and state machine transitions")
    except Exception as e:
        record("Main Architecture & WS Command Wiring Forensics", False, f"Exception: {traceback.format_exc()}")


async def main():
    print("=== STARTING FORENSIC INTEGRITY AUDIT ===")
    test_config_forensics()
    test_plugin_base_forensics()
    await test_plugin_manager_discovery_forensics()
    await test_plugin_manager_lifecycle_and_routing_forensics()
    await test_main_wiring_forensics()
    print("=== AUDIT COMPLETE ===")

    all_passed = all(r["status"] == "PASS" for r in results)
    print(f"\nFinal Forensic Verdict: {'CLEAN' if all_passed else 'INTEGRITY VIOLATION'}")
    return 0 if all_passed else 1

if __name__ == "__main__":
    code = asyncio.run(main())
    sys.exit(code)
