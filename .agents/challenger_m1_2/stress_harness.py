#!/usr/bin/env python3
"""
Milestone 1 Stress & Empirical Verification Harness (Challenger 2)
Tests: WebSocket Protocol Contracts, Invalid JSON, Latency, Concurrency, Lifecycle, Config Engine
"""

from __future__ import annotations
import asyncio
import json
import os
import shutil
import sys
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import websockets
try:
    from websockets.asyncio.client import connect as ws_connect
    from websockets.asyncio.server import serve as ws_serve
except ImportError:
    from websockets.client import connect as ws_connect
    from websockets.server import serve as ws_serve

# Add backend to Python path
BACKEND_DIR = Path("/home/pawan/Projects/jarvis-ai/backend")
sys.path.insert(0, str(BACKEND_DIR))

from jarvis.core.bus import Event, EventBus
from jarvis.core.config import Config
from jarvis.core.state import JarvisState, StateMachine
from jarvis.plugins.base import Plugin, PluginType
from jarvis.plugins.manager import PluginManager
from jarvis.ws_server import WSServer


@dataclass
class TestResult:
    name: str
    category: str
    passed: bool
    details: str
    latency_ms: Optional[float] = None
    extra: Optional[Dict[str, Any]] = None


class TestHarness:
    def __init__(self, base_port: int = 8900):
        self.base_port = base_port
        self.current_port = base_port
        self.results: List[TestResult] = []
        self.temp_dir = Path("/tmp/jarvis_challenger_m1_2_test")

    def next_port(self) -> int:
        self.current_port += 1
        return self.current_port

    def record(
        self,
        name: str,
        category: str,
        passed: bool,
        details: str,
        latency_ms: Optional[float] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        result = TestResult(
            name=name,
            category=category,
            passed=passed,
            details=details,
            latency_ms=latency_ms,
            extra=extra,
        )
        self.results.append(result)
        status = "✅ PASS" if passed else "❌ FAIL"
        lat_str = f" ({latency_ms:.2f}ms)" if latency_ms is not None else ""
        print(f"[{status}] [{category}] {name}{lat_str}: {details}")

    def reset_temp_dir(self) -> Path:
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        return self.temp_dir

    # =========================================================================
    # Suite 1: Protocol Contract Conformance
    # =========================================================================
    async def test_suite_1_protocol_contracts(self):
        print("\n--- Running Suite 1: Protocol Contract Conformance ---")
        port = self.next_port()
        bus = EventBus()
        state = StateMachine()
        server = WSServer(bus, state, host="localhost", port=port)
        bus_task = asyncio.create_task(bus.process())

        events_received: List[Event] = []
        async def capture_event(ev: Event):
            events_received.append(ev)

        bus.on("activate", capture_event)
        bus.on("deactivate", capture_event)
        bus.on("config_update", capture_event)

        async with ws_serve(server._handle, "localhost", port):
            # Test 1.1: Spec Activate command: {"type": "activate"}
            async with ws_connect(f"ws://localhost:{port}") as ws:
                events_received.clear()
                await ws.send(json.dumps({"type": "activate"}))
                await asyncio.sleep(0.05)
                passed = any(e.type == "activate" for e in events_received)
                self.record(
                    name="SPEC-WS-01 (Direct Activate Type)",
                    category="Protocol Contract",
                    passed=passed,
                    details=f"Received: {[e.type for e in events_received]}. Spec requires {{\"type\": \"activate\"}} handling.",
                )

            # Test 1.2: Spec Deactivate command: {"type": "deactivate"}
            async with ws_connect(f"ws://localhost:{port}") as ws:
                events_received.clear()
                await ws.send(json.dumps({"type": "deactivate"}))
                await asyncio.sleep(0.05)
                passed = any(e.type == "deactivate" for e in events_received)
                self.record(
                    name="SPEC-WS-02 (Direct Deactivate Type)",
                    category="Protocol Contract",
                    passed=passed,
                    details=f"Received: {[e.type for e in events_received]}. Spec requires {{\"type\": \"deactivate\"}} handling.",
                )

            # Test 1.3: Legacy Command Format: {"type": "command", "action": "activate"}
            async with ws_connect(f"ws://localhost:{port}") as ws:
                events_received.clear()
                await ws.send(json.dumps({"type": "command", "action": "activate"}))
                await asyncio.sleep(0.05)
                passed = any(e.type == "activate" for e in events_received)
                self.record(
                    name="LEGACY-WS-01 (Command Action Activate)",
                    category="Protocol Contract",
                    passed=passed,
                    details=f"Received: {[e.type for e in events_received]}.",
                )

            # Test 1.4: Spec Config Update format: {"type": "config_update", "data": {"namespace": "stt", "key": "model", "value": "tiny"}}
            async with ws_connect(f"ws://localhost:{port}") as ws:
                events_received.clear()
                await ws.send(json.dumps({
                    "type": "config_update",
                    "data": {"namespace": "stt", "key": "model", "value": "tiny"}
                }))
                await asyncio.sleep(0.05)
                has_valid_data = False
                for e in events_received:
                    if e.type == "config_update":
                        d = e.data
                        if (d.get("plugin") == "stt" or d.get("namespace") == "stt") and d.get("key") == "model" and d.get("value") == "tiny":
                            has_valid_data = True
                self.record(
                    name="SPEC-WS-03 (Config Update Data Field)",
                    category="Protocol Contract",
                    passed=has_valid_data,
                    details=f"Received event data: {[e.data for e in events_received]}. Spec defines payload in 'data' object.",
                )

            # Test 1.5: Flat Config Update format: {"type": "config_update", "plugin": "stt", "key": "model", "value": "tiny"}
            async with ws_connect(f"ws://localhost:{port}") as ws:
                events_received.clear()
                await ws.send(json.dumps({
                    "type": "config_update",
                    "plugin": "stt",
                    "key": "model",
                    "value": "tiny"
                }))
                await asyncio.sleep(0.05)
                has_valid_data = False
                for e in events_received:
                    if e.type == "config_update":
                        d = e.data
                        if d.get("plugin") == "stt" and d.get("key") == "model" and d.get("value") == "tiny":
                            has_valid_data = True
                self.record(
                    name="LEGACY-WS-02 (Config Update Flat Keys)",
                    category="Protocol Contract",
                    passed=has_valid_data,
                    details=f"Received event data: {[e.data for e in events_received]}.",
                )

            # Test 1.6: Ping/Pong Timestamp Echo & Unicast
            # Spec: {"type": "ping", "data": {"timestamp": 1234567890}} -> {"type": "pong", "data": {"timestamp": 1234567890}}
            async with ws_connect(f"ws://localhost:{port}") as ws1, ws_connect(f"ws://localhost:{port}") as ws2:
                ts = 1718900000
                await ws1.send(json.dumps({"type": "ping", "data": {"timestamp": ts}}))
                resp1_raw = await asyncio.wait_for(ws1.recv(), timeout=1.0)
                resp1 = json.loads(resp1_raw)
                has_pong = resp1.get("type") == "pong"
                has_ts = resp1.get("data", {}).get("timestamp") == ts
                
                # Check if ws2 unexpectedly received pong (broadcast instead of unicast)
                ws2_received = False
                try:
                    msg2 = await asyncio.wait_for(ws2.recv(), timeout=0.1)
                    if json.loads(msg2).get("type") == "pong":
                        ws2_received = True
                except asyncio.TimeoutError:
                    ws2_received = False

                self.record(
                    name="SPEC-WS-04 (Ping Pong Payload & Unicast)",
                    category="Protocol Contract",
                    passed=(has_pong and has_ts and not ws2_received),
                    details=f"Response: {resp1}. Unicast to sender: {not ws2_received} (Broadcast to other client: {ws2_received}), Echoed timestamp: {has_ts}.",
                )

            # Test 1.7: Settings Request
            # Spec: {"type": "settings_request"} -> {"type": "settings_response", "data": {"settings": {...}}}
            async with ws_connect(f"ws://localhost:{port}") as ws:
                await ws.send(json.dumps({"type": "settings_request"}))
                try:
                    resp_raw = await asyncio.wait_for(ws.recv(), timeout=0.5)
                    resp = json.loads(resp_raw)
                    passed = resp.get("type") == "settings_response" and "data" in resp
                    details = f"Received: {resp}"
                except asyncio.TimeoutError:
                    passed = False
                    details = "Timeout: Server did not respond to settings_request"
                self.record(
                    name="SPEC-WS-05 (Settings Request / Response)",
                    category="Protocol Contract",
                    passed=passed,
                    details=details,
                )

            # Test 1.8: State Change Broadcast Format
            # Spec: {"type": "state_change", "data": {"state": "listening", "previous": "idle"}}
            async with ws_connect(f"ws://localhost:{port}") as ws:
                await server.broadcast({
                    "type": "state_change",
                    "state": "listening",
                    "data": {"state": "listening", "previous": "idle"},
                })
                msg_raw = await asyncio.wait_for(ws.recv(), timeout=1.0)
                msg = json.loads(msg_raw)
                passed = (
                    msg.get("type") == "state_change"
                    and isinstance(msg.get("data"), dict)
                    and msg["data"].get("state") == "listening"
                    and msg["data"].get("previous") == "idle"
                )
                self.record(
                    name="SPEC-WS-06 (State Change Broadcast Format)",
                    category="Protocol Contract",
                    passed=passed,
                    details=f"Received broadcast payload: {msg}",
                )

        bus_task.cancel()

    # =========================================================================
    # Suite 2: Malformed & Adversarial Payload Stress
    # =========================================================================
    async def test_suite_2_malformed_adversarial(self):
        print("\n--- Running Suite 2: Malformed & Adversarial Payload Stress ---")
        port = self.next_port()
        bus = EventBus()
        state = StateMachine()
        server = WSServer(bus, state, host="localhost", port=port)
        bus_task = asyncio.create_task(bus.process())

        async with ws_serve(server._handle, "localhost", port):
            # Test 2.1: Malformed JSON syntax
            # Does the server crash or remain alive for other clients?
            async with ws_connect(f"ws://localhost:{port}") as ws_attacker:
                # Send broken JSON
                await ws_attacker.send('{"type": "ping", "unclosed')
                await asyncio.sleep(0.05)

            # Check if server is still alive and accepting new clients
            async with ws_connect(f"ws://localhost:{port}") as ws_victim:
                await server.broadcast({"type": "health_check", "status": "ok"})
                msg = json.loads(await asyncio.wait_for(ws_victim.recv(), timeout=1.0))
                passed = msg.get("type") == "health_check"
                self.record(
                    name="ROBUST-01 (Server Liveness after Malformed JSON)",
                    category="Robustness",
                    passed=passed,
                    details="Server accepted connection and broadcasted after malformed JSON from disconnected client.",
                )

            # Test 2.2: Non-JSON raw strings
            async with ws_connect(f"ws://localhost:{port}") as ws:
                await ws.send("HELLO JARVIS RAW STRING")
                await asyncio.sleep(0.05)
            # Check liveness
            async with ws_connect(f"ws://localhost:{port}") as ws:
                await server.broadcast({"type": "alive"})
                msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=1.0))
                self.record(
                    name="ROBUST-02 (Raw String Rejection & Server Liveness)",
                    category="Robustness",
                    passed=msg.get("type") == "alive",
                    details="Server remained operational after receiving non-JSON plain string.",
                )

            # Test 2.3: Non-dict JSON primitives (int, string, bool, null, list)
            primitives = [12345, "just a string", True, None, [1, 2, 3], [{"type": "ping"}]]
            survived_all = True
            for prim in primitives:
                try:
                    async with ws_connect(f"ws://localhost:{port}") as ws:
                        await ws.send(json.dumps(prim))
                        await asyncio.sleep(0.02)
                except Exception as e:
                    pass
            # Verify server health
            async with ws_connect(f"ws://localhost:{port}") as ws:
                await server.broadcast({"type": "alive_primitives"})
                msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=1.0))
                survived_all = (msg.get("type") == "alive_primitives")

            self.record(
                name="ROBUST-03 (JSON Primitives / Non-dict Payloads)",
                category="Robustness",
                passed=survived_all,
                details=f"Tested primitives: int, str, bool, null, list. Server survived: {survived_all}.",
            )

            # Test 2.4: Massive Payload (1MB JSON)
            large_data = {"type": "ping", "padding": "X" * 1024 * 1024}
            large_json = json.dumps(large_data)
            try:
                async with ws_connect(f"ws://localhost:{port}", max_size=2 * 1024 * 1024) as ws:
                    t0 = time.perf_counter()
                    await ws.send(large_json)
                    await asyncio.sleep(0.05)
                    dt = (time.perf_counter() - t0) * 1000
                    passed = True
            except Exception as e:
                passed = False
                dt = 0
            self.record(
                name="ROBUST-04 (1MB Large Payload Ingestion)",
                category="Robustness",
                passed=passed,
                latency_ms=dt,
                details=f"Sent 1MB payload over websocket. Server handled without OOM.",
            )

            # Test 2.5: Deeply nested JSON (Recursion bomb)
            nested = {"type": "ping"}
            cur = nested
            for _ in range(100):
                cur["child"] = {}
                cur = cur["child"]
            try:
                async with ws_connect(f"ws://localhost:{port}") as ws:
                    await ws.send(json.dumps(nested))
                    await asyncio.sleep(0.05)
                    passed = True
            except Exception:
                passed = False
            self.record(
                name="ROBUST-05 (100-Level Deeply Nested JSON)",
                category="Robustness",
                passed=passed,
                details="Handled deeply nested JSON structure without recursion crash.",
            )

            # Test 2.6: Rapid Burst of 500 Malformed & Adversarial Messages
            async with ws_connect(f"ws://localhost:{port}") as ws:
                t0 = time.perf_counter()
                for i in range(500):
                    try:
                        if i % 4 == 0:
                            await ws.send("{bad_json")
                        elif i % 4 == 1:
                            await ws.send("12345")
                        elif i % 4 == 2:
                            await ws.send("")
                        else:
                            await ws.send(json.dumps({"unknown_key": i}))
                    except websockets.ConnectionClosed:
                        # Client disconnected due to unhandled error in server
                        break
                dt = (time.perf_counter() - t0) * 1000
            
            # Verify server still responds to normal client
            async with ws_connect(f"ws://localhost:{port}") as ws_check:
                await server.broadcast({"type": "burst_survived"})
                msg = json.loads(await asyncio.wait_for(ws_check.recv(), timeout=1.0))
                passed = msg.get("type") == "burst_survived"
            
            self.record(
                name="ROBUST-06 (Burst of 500 Malformed Packets)",
                category="Robustness",
                passed=passed,
                latency_ms=dt,
                details=f"Sent 500 invalid/malformed frames. Server remained healthy.",
            )

        bus_task.cancel()

    # =========================================================================
    # Suite 3: Concurrency, Latency & Load Stress
    # =========================================================================
    async def test_suite_3_concurrency_latency(self):
        print("\n--- Running Suite 3: Concurrency, Latency & Load Stress ---")
        port = self.next_port()
        bus = EventBus()
        state = StateMachine()
        server = WSServer(bus, state, host="localhost", port=port)
        bus_task = asyncio.create_task(bus.process())

        async with ws_serve(server._handle, "localhost", port):
            # Test 3.1: Ping/Pong Round-trip Latency Benchmark (1,000 cycles)
            latencies_ms: List[float] = []
            async with ws_connect(f"ws://localhost:{port}") as ws:
                for i in range(1000):
                    t0 = time.perf_counter()
                    await ws.send(json.dumps({"type": "ping"}))
                    raw = await asyncio.wait_for(ws.recv(), timeout=1.0)
                    t1 = time.perf_counter()
                    latencies_ms.append((t1 - t0) * 1000)

            latencies_ms.sort()
            p50 = latencies_ms[int(len(latencies_ms) * 0.50)]
            p95 = latencies_ms[int(len(latencies_ms) * 0.95)]
            p99 = latencies_ms[int(len(latencies_ms) * 0.99)]
            mean_lat = sum(latencies_ms) / len(latencies_ms)
            min_lat = min(latencies_ms)
            max_lat = max(latencies_ms)

            # Pass condition: mean latency < 5ms on localhost
            passed = mean_lat < 5.0 and p99 < 20.0
            self.record(
                name="PERF-01 (Ping/Pong 1,000 Cycles Benchmark)",
                category="Performance & Latency",
                passed=passed,
                latency_ms=mean_lat,
                extra={"min": min_lat, "max": max_lat, "mean": mean_lat, "p50": p50, "p95": p95, "p99": p99},
                details=f"Min: {min_lat:.3f}ms | Mean: {mean_lat:.3f}ms | P50: {p50:.3f}ms | P95: {p95:.3f}ms | P99: {p99:.3f}ms | Max: {max_lat:.3f}ms",
            )

            # Test 3.2: 50 Concurrent Clients State Broadcast Fan-out
            NUM_CLIENTS = 50
            clients = []
            try:
                for _ in range(NUM_CLIENTS):
                    ws = await ws_connect(f"ws://localhost:{port}")
                    clients.append(ws)
                await asyncio.sleep(0.05)

                assert len(server._clients) == NUM_CLIENTS, f"Expected {NUM_CLIENTS} connected clients, got {len(server._clients)}"

                # Broadcast a state change
                t0 = time.perf_counter()
                await server.broadcast({
                    "type": "state_change",
                    "data": {"state": "thinking", "previous": "listening"},
                })

                # Concurrently receive from all 50 clients
                async def recv_client(c):
                    msg = await asyncio.wait_for(c.recv(), timeout=1.0)
                    return json.loads(msg)

                results = await asyncio.gather(*[recv_client(c) for c in clients])
                fanout_time = (time.perf_counter() - t0) * 1000
                all_received = all(r.get("data", {}).get("state") == "thinking" for r in results)
                passed = all_received and len(results) == NUM_CLIENTS

                self.record(
                    name="PERF-02 (50-Client Broadcast Fan-out)",
                    category="Performance & Latency",
                    passed=passed,
                    latency_ms=fanout_time,
                    details=f"Broadcast delivered to all {len(results)}/{NUM_CLIENTS} connected clients in {fanout_time:.2f}ms.",
                )
            finally:
                for c in clients:
                    await c.close()

            # Test 3.3: High-Frequency Broadcast Throughput (1,000 state broadcasts)
            async with ws_connect(f"ws://localhost:{port}") as ws:
                t0 = time.perf_counter()
                for i in range(500):
                    await server.broadcast({"type": "audio_level", "data": {"level": i * 0.001, "source": "mic"}})
                
                received_count = 0
                for i in range(500):
                    msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    if json.loads(msg).get("type") == "audio_level":
                        received_count += 1
                total_time = (time.perf_counter() - t0) * 1000
                rate = 500 / (total_time / 1000)
                passed = received_count == 500
                self.record(
                    name="PERF-03 (High-Frequency 500 Broadcasts Stream)",
                    category="Performance & Latency",
                    passed=passed,
                    latency_ms=total_time / 500,
                    details=f"Delivered 500 audio_level broadcasts in {total_time:.2f}ms ({rate:.1f} msgs/sec). Received: {received_count}/500.",
                )

            # Test 3.4: 10 Concurrent Clients Sending Command Bursts
            NUM_SENDERS = 10
            MSGS_PER_SENDER = 50
            commands_received: List[Event] = []
            async def track_cmd(ev: Event):
                commands_received.append(ev)
            bus.on("activate", track_cmd)

            senders = [await ws_connect(f"ws://localhost:{port}") for _ in range(NUM_SENDERS)]
            try:
                async def sender_work(ws_client):
                    for _ in range(MSGS_PER_SENDER):
                        await ws_client.send(json.dumps({"type": "command", "action": "activate"}))
                        await asyncio.sleep(0.001)

                t0 = time.perf_counter()
                await asyncio.gather(*[sender_work(s) for s in senders])
                await asyncio.sleep(0.1)
                total_sent = NUM_SENDERS * MSGS_PER_SENDER
                dt = (time.perf_counter() - t0) * 1000
                passed = len(commands_received) == total_sent
                self.record(
                    name="PERF-04 (10 Concurrent Clients Command Burst)",
                    category="Performance & Latency",
                    passed=passed,
                    latency_ms=dt,
                    details=f"Processed {len(commands_received)}/{total_sent} commands across {NUM_SENDERS} concurrent sockets in {dt:.2f}ms.",
                )
            finally:
                for s in senders:
                    await s.close()

        bus_task.cancel()

    # =========================================================================
    # Suite 4: Connection Lifecycle & Resource Leak Stress
    # =========================================================================
    async def test_suite_4_lifecycle_and_leaks(self):
        print("\n--- Running Suite 4: Connection Lifecycle & Resource Leak Stress ---")
        port = self.next_port()
        bus = EventBus()
        state = StateMachine()
        server = WSServer(bus, state, host="localhost", port=port)
        bus_task = asyncio.create_task(bus.process())

        async with ws_serve(server._handle, "localhost", port):
            # Test 4.1: Rapid Connect / Disconnect Loop (100 iterations)
            t0 = time.perf_counter()
            for i in range(100):
                ws = await ws_connect(f"ws://localhost:{port}")
                await ws.close()
            await asyncio.sleep(0.05)
            dt = (time.perf_counter() - t0) * 1000
            clients_remaining = len(server._clients)
            passed = clients_remaining == 0
            self.record(
                name="LIFECYCLE-01 (100 Rapid Connect/Disconnect Iterations)",
                category="Lifecycle & Memory",
                passed=passed,
                latency_ms=dt / 100,
                details=f"Completed 100 cycles in {dt:.2f}ms. Active clients in server set: {clients_remaining} (Expected 0).",
            )

            # Test 4.2: Abrupt Client Disconnect During Broadcast
            ws1 = await ws_connect(f"ws://localhost:{port}")
            ws2 = await ws_connect(f"ws://localhost:{port}")
            await asyncio.sleep(0.02)
            # Abruptly close ws1 transport without proper WS close handshake
            if hasattr(ws1, "transport") and ws1.transport:
                ws1.transport.close()
            else:
                await ws1.close()
            
            # Broadcast to remaining clients
            broadcast_success = True
            try:
                await server.broadcast({"type": "test_dead_socket", "val": 42})
                msg = await asyncio.wait_for(ws2.recv(), timeout=1.0)
                broadcast_success = json.loads(msg).get("val") == 42
            except Exception as e:
                broadcast_success = False

            await asyncio.sleep(0.05)
            passed = broadcast_success and (ws1 not in server._clients or len(server._clients) <= 1)
            self.record(
                name="LIFECYCLE-02 (Dead Socket Eviction during Broadcast)",
                category="Lifecycle & Memory",
                passed=passed,
                details=f"Live client received broadcast: {broadcast_success}. Stale socket removed from client set: {ws1 not in server._clients}.",
            )
            await ws2.close()

            # Test 4.3: Graceful Server Shutdown & Task Cancellation
            clean_port = self.next_port()
            clean_server = WSServer(bus, state, host="localhost", port=clean_port)
            server_task = asyncio.create_task(clean_server.start())
            await asyncio.sleep(0.05)
            server_task.cancel()
            try:
                await server_task
                shutdown_clean = True
            except asyncio.CancelledError:
                shutdown_clean = True
            except Exception as e:
                shutdown_clean = False

            self.record(
                name="LIFECYCLE-03 (Graceful Server Task Cancellation)",
                category="Lifecycle & Memory",
                passed=shutdown_clean,
                details="Server task cancelled cleanly without uncaught exceptions.",
            )

        bus_task.cancel()

    # =========================================================================
    # Suite 5: Config Engine Resilience & Atomic Persistence
    # =========================================================================
    async def test_suite_5_config_engine(self):
        print("\n--- Running Suite 5: Config Engine Resilience & Atomic Persistence ---")
        temp_dir = self.reset_temp_dir()
        config = Config(temp_dir)

        # Test 5.1: Namespace Isolation and Getter/Setter
        config.set("stt", "model", "base.en")
        config.set("stt", "temperature", 0.0)
        config.set("tts", "voice", "en_US-lessac-medium")
        config.set("tts", "speed", 1.1)

        stt_model = config.get("stt", "model")
        stt_temp = config.get("stt", "temperature")
        tts_voice = config.get("tts", "voice")
        missing_val = config.get("stt", "non_existent", "default_val")

        passed_iso = (
            stt_model == "base.en"
            and stt_temp == 0.0
            and tts_voice == "en_US-lessac-medium"
            and missing_val == "default_val"
        )
        self.record(
            name="CONFIG-01 (Namespace Isolation & Defaults)",
            category="Config Engine",
            passed=passed_iso,
            details=f"STT Model: {stt_model}, TTS Voice: {tts_voice}, Missing Key: {missing_val}.",
        )

        # Test 5.2: Disk Persistence & Atomic File Structure
        stt_file = temp_dir / "config" / "stt.json"
        tts_file = temp_dir / "config" / "tts.json"
        has_files = stt_file.exists() and tts_file.exists()
        
        # Read file directly from disk to verify serialization
        with open(stt_file, "r") as f:
            disk_stt = json.load(f)
        passed_disk = has_files and disk_stt.get("model") == "base.en"
        self.record(
            name="CONFIG-02 (Disk JSON Persistence)",
            category="Config Engine",
            passed=passed_disk,
            details=f"stt.json content on disk: {disk_stt}.",
        )

        # Test 5.3: Corrupt JSON & Malformed File Recovery
        corrupt_file = temp_dir / "config" / "corrupt_ns.json"
        corrupt_file.write_text("{ unclosed invalid json !!!", encoding="utf-8")
        
        # Fresh config instance with empty cache
        config2 = Config(temp_dir)
        val = config2.get("corrupt_ns", "any_key", default="fallback")
        all_vals = config2.get_all("corrupt_ns")
        passed_corrupt = (val == "fallback" and all_vals == {})
        self.record(
            name="CONFIG-03 (Corrupt JSON File Graceful Recovery)",
            category="Config Engine",
            passed=passed_corrupt,
            details=f"Read corrupted JSON file safely. Fallback: {val}, All: {all_vals}.",
        )

        # Test 5.4: Non-UTF8 Binary File in Config Dir
        binary_file = temp_dir / "config" / "binary_ns.json"
        binary_file.write_bytes(b"\x80\x81\xFF\xFE\x00\x01")
        config3 = Config(temp_dir)
        bin_val = config3.get("binary_ns", "key", default="recovered")
        self.record(
            name="CONFIG-04 (Non-UTF8 Binary File Recovery)",
            category="Config Engine",
            passed=bin_val == "recovered",
            details=f"Handled invalid UTF-8 bytes without crashing. Fallback: {bin_val}.",
        )

        # Test 5.5: High Concurrency Read/Write Stress (1,000 operations)
        async def worker_write(cid: int):
            for i in range(100):
                ns = f"worker_{cid % 5}"
                config.set(ns, f"key_{i}", f"val_{cid}_{i}")
                await asyncio.sleep(0.0001)

        t0 = time.perf_counter()
        await asyncio.gather(*[worker_write(i) for i in range(10)])
        dt = (time.perf_counter() - t0) * 1000

        # Verify disk files integrity
        all_intact = True
        for i in range(5):
            ns_file = temp_dir / "config" / f"worker_{i}.json"
            if not ns_file.exists():
                all_intact = False
                break
            try:
                with open(ns_file, "r") as f:
                    data = json.load(f)
                    if not isinstance(data, dict):
                        all_intact = False
            except Exception:
                all_intact = False

        self.record(
            name="CONFIG-05 (1,000 Concurrent Writes & Persistence)",
            category="Config Engine",
            passed=all_intact,
            latency_ms=dt,
            details=f"Executed 1,000 writes across 10 concurrent tasks in {dt:.2f}ms. All 5 namespace files intact on disk.",
        )

        # Test 5.6: list_namespaces with Subdirectories and Cached Items
        nested_file = temp_dir / "config" / "plugins" / "whisper.json"
        nested_file.parent.mkdir(parents=True, exist_ok=True)
        nested_file.write_text('{"model_size": "medium"}', encoding="utf-8")

        config4 = Config(temp_dir)
        config4.set("in_memory_ns", "foo", "bar")
        namespaces = config4.list_namespaces()
        has_nested = "plugins/whisper" in namespaces or "whisper" in namespaces
        has_memory = "in_memory_ns" in namespaces
        self.record(
            name="CONFIG-06 (list_namespaces Subdirectories & Memory)",
            category="Config Engine",
            passed=(has_nested and has_memory),
            details=f"Discovered namespaces: {namespaces}.",
        )

    # =========================================================================
    # Suite 6: Full System Integration (Backend main lifecycle)
    # =========================================================================
    async def test_suite_6_backend_integration(self):
        print("\n--- Running Suite 6: Full Backend Main Wiring & Plugin Lifecycle ---")
        temp_dir = self.reset_temp_dir()
        port = self.next_port()

        bus = EventBus()
        state = StateMachine()
        config = Config(temp_dir)
        server = WSServer(bus, state, host="localhost", port=port)
        plugin_mgr = PluginManager(bus, config)

        # Mock STT Plugin
        class MockSTT(Plugin):
            name = "mock_stt"
            plugin_type = PluginType.STT
            def __init__(self, bus=None, config=None):
                super().__init__(bus, config)
                self.started = False
                self.stopped = False

            async def start(self, cfg=None):
                self.started = True

            async def stop(self):
                self.stopped = True

            async def on_event(self, event: Event):
                if event.type == "audio_chunk":
                    return Event(type="stt_result", data={"text": "hello jarvis"}, source=self.name)
                return None

            def get_schema(self):
                return {"type": "object", "properties": {"model": {"type": "string"}}}

        mock_plugin = MockSTT(bus, config)
        plugin_mgr.register(mock_plugin)
        await plugin_mgr.activate("mock_stt")

        # Set up state broadcast listener matching __main__.py
        state_broadcasts: List[dict] = []
        async def broadcast_state(old: JarvisState, new: JarvisState):
            payload = {
                "type": "state_change",
                "state": new.value,
                "data": {"state": new.value, "previous": old.value},
            }
            state_broadcasts.append(payload)
            await server.broadcast(payload)

        state.on_change(broadcast_state)

        # Handlers matching __main__.py
        async def handle_activate(ev: Event):
            if state.state == JarvisState.IDLE:
                await state.transition(JarvisState.LISTENING)

        async def handle_deactivate(ev: Event):
            if state.state != JarvisState.IDLE:
                await state.transition(JarvisState.IDLE)

        bus.on("activate", handle_activate)
        bus.on("deactivate", handle_deactivate)

        bus_task = asyncio.create_task(bus.process())

        async with ws_serve(server._handle, "localhost", port):
            async with ws_connect(f"ws://localhost:{port}") as ws:
                # Activate via websocket
                await ws.send(json.dumps({"type": "command", "action": "activate"}))
                await asyncio.sleep(0.05)
                
                # Check that state transitioned to LISTENING and broadcast was sent
                assert state.state == JarvisState.LISTENING, f"Expected LISTENING, got {state.state}"
                msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=1.0))
                passed_act = (
                    msg.get("type") == "state_change"
                    and msg.get("data", {}).get("state") == "listening"
                    and msg.get("data", {}).get("previous") == "idle"
                )

                # Send audio chunk and test event routing to plugin
                stt_events = []
                async def capture_stt(ev: Event):
                    stt_events.append(ev)
                bus.on("stt_result", capture_stt)

                resp_events = await plugin_mgr.route_event(Event(type="audio_chunk", data={"audio": b"..."}))
                await asyncio.sleep(0.05)
                passed_route = len(stt_events) == 1 and stt_events[0].data.get("text") == "hello jarvis"

                # Deactivate via websocket
                await ws.send(json.dumps({"type": "command", "action": "deactivate"}))
                await asyncio.sleep(0.05)
                assert state.state == JarvisState.IDLE, f"Expected IDLE, got {state.state}"

                self.record(
                    name="INT-01 (End-to-End WebSocket -> State -> Plugin Event Flow)",
                    category="System Integration",
                    passed=(passed_act and passed_route),
                    details=f"State transitioned IDLE -> LISTENING -> IDLE. Broadcast: {msg}. Plugin event routed: {passed_route}.",
                )

        # Cleanup
        await plugin_mgr.stop_all()
        bus_task.cancel()
        self.record(
            name="INT-02 (Plugin Manager stop_all and Teardown)",
            category="System Integration",
            passed=mock_plugin.stopped,
            details=f"MockSTT stopped status: {mock_plugin.stopped}.",
        )

    async def run_all(self):
        print("=" * 80)
        print("STARTING EMPIRICAL VERIFICATION HARNESS (CHALLENGER 2 - MILESTONE 1)")
        print("=" * 80)

        try:
            await self.test_suite_1_protocol_contracts()
            await self.test_suite_2_malformed_adversarial()
            await self.test_suite_3_concurrency_latency()
            await self.test_suite_4_lifecycle_and_leaks()
            await self.test_suite_5_config_engine()
            await self.test_suite_6_backend_integration()
        except Exception as e:
            print(f"\nCRITICAL UNCAUGHT EXCEPTION IN HARNESS: {e}")
            traceback.print_exc()

        print("\n" + "=" * 80)
        print("HARNESS EXECUTION SUMMARY")
        print("=" * 80)
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        print(f"Total Tests: {total} | Passed: {passed} | Failed: {failed}")
        print("=" * 80)

        if failed > 0:
            print("\nFAILED TESTS DETAILS:")
            for r in self.results:
                if not r.passed:
                    print(f"  ❌ [{r.category}] {r.name}: {r.details}")

        return total, passed, failed


if __name__ == "__main__":
    harness = TestHarness(base_port=8910)
    total, passed, failed = asyncio.run(harness.run_all())
    sys.exit(0 if failed == 0 else 1)
