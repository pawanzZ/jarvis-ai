import asyncio
import json
import random
import shutil
import sys
import tempfile
from pathlib import Path

backend_dir = Path("/home/pawan/Projects/jarvis-ai/backend")
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from jarvis.core.bus import Event, EventBus
from jarvis.core.state import StateMachine, JarvisState
from jarvis.core.config import Config
from jarvis.plugins.base import Plugin, PluginType
from jarvis.plugins.manager import PluginManager


async def stress_config_concurrency():
    temp_dir = tempfile.mkdtemp(prefix="jarvis_cfg_stress_")
    try:
        cfg = Config(temp_dir)
        async def writer(task_id: int):
            for i in range(50):
                cfg.set("stress", f"key_{task_id}_{i}", f"val_{task_id}_{i}")
                await asyncio.sleep(0.001)

        async def reader(task_id: int):
            for i in range(50):
                cfg.get("stress", f"key_{random.randint(0, 4)}_{random.randint(0, 49)}")
                await asyncio.sleep(0.001)

        writers = [writer(i) for i in range(5)]
        readers = [reader(i) for i in range(5)]
        await asyncio.gather(*writers, *readers)

        # Verify on disk
        data = cfg.get_all("stress")
        assert len(data) == 250, f"Expected 250 keys, got {len(data)}"
        print("[PASS] Stress: Concurrent Config Reads and Writes")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


async def stress_plugin_manager_scale():
    temp_dir = tempfile.mkdtemp(prefix="jarvis_pm_stress_")
    try:
        bus = EventBus()
        cfg = Config(temp_dir)
        mgr = PluginManager(bus, cfg)

        class MultiPlugin(Plugin):
            def __init__(self, idx: int):
                super().__init__()
                self.name = f"plugin_{idx}"
                self.plugin_type = PluginType.ACTIVATION
                self.count = 0
            async def start(self, config=None): pass
            async def stop(self): pass
            async def on_event(self, event: Event):
                self.count += 1
                if self.count % 10 == 0:
                    return Event(type="batch_done", data={"plugin": self.name}, source=self.name)
                return None
            def get_schema(self): return {}

        plugins = [MultiPlugin(i) for i in range(50)]
        for p in plugins:
            mgr.register(p)
            await mgr.activate(p.name)

        assert len(mgr.get_active_plugins()) == 50

        # Dispatch 20 events
        for k in range(20):
            await mgr.route_event(Event(type="tick", data={"step": k}))

        for p in plugins:
            assert p.count == 20, f"Plugin {p.name} count {p.count} != 20"

        # Check emitted batch_done events on bus
        batch_events = 0
        while not bus._queue.empty():
            ev = await bus._queue.get()
            if ev.type == "batch_done":
                batch_events += 1
        assert batch_events == 100, f"Expected 100 batch events, got {batch_events}"
        print("[PASS] Stress: PluginManager 50-Plugin Fan-Out and Batch Event Routing")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


async def main():
    print("=== STARTING ADVERSARIAL STRESS AUDIT ===")
    await stress_config_concurrency()
    await stress_plugin_manager_scale()
    print("=== ADVERSARIAL STRESS AUDIT COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(main())
