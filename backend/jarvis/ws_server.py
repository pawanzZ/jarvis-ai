from __future__ import annotations
import asyncio
import json
from typing import Any, Optional
import websockets
try:
    from websockets.asyncio.server import serve
except ImportError:
    from websockets.server import serve

from jarvis.core.bus import EventBus, Event
from jarvis.core.state import StateMachine, JarvisState
from jarvis.core.config import Config


class WSServer:
    def __init__(
        self,
        bus: EventBus,
        state: StateMachine,
        config: Optional[Config] = None,
        system_monitor: Optional[Any] = None,
        host: str = "localhost",
        port: int = 8765,
    ) -> None:
        self.bus = bus
        self.state = state
        self.config = config
        self.system_monitor = system_monitor
        self.host = host
        self.port = port
        self._clients: set[Any] = set()

    def _get_current_settings(self) -> dict[str, Any]:
        cfg = self.config
        return {
            "voice": {
                "sttPlugin": cfg.get("voice", "sttPlugin", cfg.get("voice", "stt_plugin", "whisper_local")) if cfg else "whisper_local",
                "ttsPlugin": cfg.get("voice", "ttsPlugin", cfg.get("voice", "tts_plugin", "piper_tts")) if cfg else "piper_tts",
                "ttsVoice": cfg.get("voice", "ttsVoice", cfg.get("voice", "tts_voice", "en_GB-alan-medium")) if cfg else "en_GB-alan-medium",
                "ttsRate": float(cfg.get("voice", "ttsRate", cfg.get("voice", "tts_rate", 1.0))) if cfg else 1.0,
                "micSensitivity": float(cfg.get("voice", "micSensitivity", cfg.get("voice", "mic_sensitivity", 0.8))) if cfg else 0.8,
                "volume": float(cfg.get("voice", "volume", 0.8)) if cfg else 0.8,
            },
            "brain": {
                "llmPlugin": cfg.get("brain", "llmPlugin", cfg.get("brain", "llm_plugin", "ollama_llm")) if cfg else "ollama_llm",
                "model": cfg.get("brain", "model", "llama3") if cfg else "llama3",
                "temperature": float(cfg.get("brain", "temperature", 0.7)) if cfg else 0.7,
                "maxTokens": int(cfg.get("brain", "maxTokens", cfg.get("brain", "max_tokens", 512))) if cfg else 512,
                "systemPrompt": cfg.get("brain", "systemPrompt", cfg.get("brain", "system_prompt", "You are JARVIS, a helpful, witty, and concise AI assistant.")) if cfg else "You are JARVIS, a helpful, witty, and concise AI assistant.",
            },
            "activation": {
                "wakeWordEnabled": bool(cfg.get("activation", "wakeWordEnabled", cfg.get("activation", "wake_word_enabled", True))) if cfg else True,
                "wakeWord": cfg.get("activation", "wakeWord", cfg.get("activation", "wake_word", "Hey Jarvis")) if cfg else "Hey Jarvis",
                "pttEnabled": bool(cfg.get("activation", "pttEnabled", cfg.get("activation", "ptt_enabled", True))) if cfg else True,
                "pttKey": cfg.get("activation", "pttKey", cfg.get("activation", "ptt_key", "Space")) if cfg else "Space",
                "clapEnabled": bool(cfg.get("activation", "clapEnabled", cfg.get("activation", "clap_enabled", True))) if cfg else True,
                "clapSensitivity": float(cfg.get("activation", "clapSensitivity", cfg.get("activation", "clap_sensitivity", 0.7))) if cfg else 0.7,
                "gestureEnabled": bool(cfg.get("activation", "gestureEnabled", cfg.get("activation", "gesture_enabled", False))) if cfg else False,
            },
            "appearance": {
                "theme": cfg.get("appearance", "theme", "arc") if cfg else "arc",
                "particleDensity": int(cfg.get("appearance", "particleDensity", cfg.get("appearance", "particle_density", 60))) if cfg else 60,
                "crtScanlines": bool(cfg.get("appearance", "crtScanlines", cfg.get("appearance", "crt_scanlines", True))) if cfg else True,
                "glowIntensity": float(cfg.get("appearance", "glowIntensity", cfg.get("appearance", "glow_intensity", 1.0))) if cfg else 1.0,
                "uiScale": float(cfg.get("appearance", "uiScale", cfg.get("appearance", "ui_scale", 1.0))) if cfg else 1.0,
            },
            "vision": {
                "cameraIndex": int(cfg.get("vision", "cameraIndex", cfg.get("vision", "camera_index", 0))) if cfg else 0,
                "faceTrackingEnabled": bool(cfg.get("vision", "faceTrackingEnabled", cfg.get("vision", "face_tracking_enabled", True))) if cfg else True,
                "gazeParallax": bool(cfg.get("vision", "gazeParallax", cfg.get("vision", "gaze_parallax", True))) if cfg else True,
                "helmetBootOverlay": bool(cfg.get("vision", "helmetBootOverlay", cfg.get("vision", "helmet_boot_overlay", False))) if cfg else False,
            },
            "sfx": {
                "masterVolume": float(cfg.get("sfx", "masterVolume", cfg.get("sfx", "master_volume", 0.5))) if cfg else 0.5,
                "powerUpEnabled": bool(cfg.get("sfx", "powerUpEnabled", cfg.get("sfx", "power_up_enabled", True))) if cfg else True,
                "chimesEnabled": bool(cfg.get("sfx", "chimesEnabled", cfg.get("sfx", "chimes_enabled", True))) if cfg else True,
                "humEnabled": bool(cfg.get("sfx", "humEnabled", cfg.get("sfx", "hum_enabled", True))) if cfg else True,
                "errorBuzzEnabled": bool(cfg.get("sfx", "errorBuzzEnabled", cfg.get("sfx", "error_buzz_enabled", True))) if cfg else True,
                "thinkingWhirrEnabled": bool(cfg.get("sfx", "thinkingWhirrEnabled", cfg.get("sfx", "thinking_whirr_enabled", True))) if cfg else True,
            },
        }

    async def start(self) -> None:
        async with serve(self._handle, self.host, self.port):
            print(f"WebSocket server running on ws://{self.host}:{self.port}")
            await asyncio.Event().wait()

    async def _handle(self, ws: Any) -> None:
        self._clients.add(ws)
        try:
            async for message in ws:
                try:
                    payload = json.loads(message)
                    if not isinstance(payload, dict):
                        await ws.send(
                            json.dumps(
                                {
                                    "type": "error",
                                    "data": {
                                        "code": "INVALID_PAYLOAD",
                                        "message": "Expected JSON object",
                                    },
                                }
                            )
                        )
                        continue
                    await self._on_message(ws, payload)
                except json.JSONDecodeError:
                    try:
                        await ws.send(
                            json.dumps(
                                {
                                    "type": "error",
                                    "data": {
                                        "code": "JSON_DECODE_ERROR",
                                        "message": "Malformed JSON format",
                                    },
                                }
                            )
                        )
                    except websockets.ConnectionClosed:
                        break
                except websockets.ConnectionClosed:
                    break
                except Exception as e:
                    try:
                        await ws.send(
                            json.dumps(
                                {
                                    "type": "error",
                                    "data": {
                                        "code": "SERVER_ERROR",
                                        "message": str(e),
                                    },
                                }
                            )
                        )
                    except websockets.ConnectionClosed:
                        break
        except websockets.ConnectionClosed:
            pass
        finally:
            self._clients.discard(ws)

    async def _on_message(self, arg1: Any, arg2: Optional[Any] = None) -> None:
        if arg2 is not None:
            if isinstance(arg1, dict):
                msg, ws = arg1, arg2
            else:
                ws, msg = arg1, arg2
        else:
            if isinstance(arg1, dict):
                msg, ws = arg1, None
            else:
                msg, ws = {}, arg1

        msg_type = msg.get("type")
        if msg_type == "activate" or (
            msg_type == "command" and msg.get("action") == "activate"
        ):
            await self.bus.emit(Event(type="activate", source="hud"))
        elif msg_type == "deactivate" or (
            msg_type == "command" and msg.get("action") == "deactivate"
        ):
            await self.bus.emit(Event(type="deactivate", source="hud"))
        elif msg_type == "config_update":
            data = msg.get("data") if isinstance(msg.get("data"), dict) else {}
            plugin = (
                data.get("namespace")
                or data.get("plugin")
                or msg.get("plugin")
                or msg.get("namespace", "core")
            )
            key = data.get("key") or msg.get("key")
            value = data.get("value") if "value" in data else msg.get("value")
            if self.config and plugin and key:
                self.config.set(plugin, key, value)
            await self.bus.emit(
                Event(
                    type="config_update",
                    data={
                        "plugin": plugin,
                        "namespace": plugin,
                        "key": key,
                        "value": value,
                    },
                    source="hud",
                )
            )
            await self.broadcast({
                "type": "config_updated",
                "data": {"namespace": plugin, "key": key, "value": value},
                "namespace": plugin,
                "key": key,
                "value": value,
            })
        elif msg_type == "settings_save":
            settings_data = msg.get("settings") or msg.get("data", {}).get("settings", {})
            if self.config and isinstance(settings_data, dict):
                for namespace, values in settings_data.items():
                    if isinstance(values, dict):
                        for k, v in values.items():
                            self.config.set(namespace, k, v)
                await self.broadcast({
                    "type": "config_updated",
                    "data": {"namespace": "all", "key": "all", "value": "synced"},
                })
        elif msg_type == "ping":
            data = msg.get("data") if isinstance(msg.get("data"), dict) else {}
            pong_resp: dict[str, Any] = {"type": "pong"}
            if "timestamp" in data:
                pong_resp["data"] = {"timestamp": data["timestamp"]}
            if ws is not None:
                try:
                    await ws.send(json.dumps(pong_resp))
                except websockets.ConnectionClosed:
                    pass
            else:
                await self.broadcast(pong_resp)
        elif msg_type == "settings_request":
            await self.bus.emit(Event(type="settings_request", source="hud"))
            current_settings = self._get_current_settings()
            resp = {
                "type": "settings_response",
                "data": {"settings": current_settings},
                "settings": current_settings,
            }
            if ws is not None:
                try:
                    await ws.send(json.dumps(resp))
                except websockets.ConnectionClosed:
                    pass
            else:
                await self.broadcast(resp)
        elif msg_type == "telemetry_request":
            if self.system_monitor:
                telemetry = self.system_monitor.get_telemetry_snapshot()
                resp = {"type": "system_telemetry", "data": telemetry}
                if ws is not None:
                    try:
                        await ws.send(json.dumps(resp))
                    except websockets.ConnectionClosed:
                        pass
                else:
                    await self.broadcast(resp)
        elif msg_type == "weather_request":
            if self.system_monitor:
                weather = self.system_monitor.get_weather_telemetry()
                resp = {"type": "weather_telemetry", "data": weather}
                if ws is not None:
                    try:
                        await ws.send(json.dumps(resp))
                    except websockets.ConnectionClosed:
                        pass
                else:
                    await self.broadcast(resp)

    async def broadcast(self, data: dict[str, Any]) -> None:
        message = json.dumps(data)
        for client in list(self._clients):
            try:
                await client.send(message)
            except websockets.ConnectionClosed:
                self._clients.discard(client)
