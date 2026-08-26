from __future__ import annotations
from jarvis.plugins.builtins.whisper_local import WhisperLocalPlugin
from jarvis.plugins.builtins.piper_tts import PiperTTSPlugin
from jarvis.plugins.builtins.ollama_llm import OllamaLLMPlugin
from jarvis.plugins.builtins.push_to_talk import PushToTalkPlugin
from jarvis.plugins.builtins.clap_detector import ClapDetectorPlugin
from jarvis.plugins.builtins.face_tracker import FaceTrackerPlugin

__all__ = [
    "WhisperLocalPlugin",
    "PiperTTSPlugin",
    "OllamaLLMPlugin",
    "PushToTalkPlugin",
    "ClapDetectorPlugin",
    "FaceTrackerPlugin",
]
