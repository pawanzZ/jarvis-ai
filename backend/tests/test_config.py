import json
from pathlib import Path
from jarvis.core.config import Config


def test_config_get_default(tmp_path: Path):
    config = Config(tmp_path)
    val = config.get("test_ns", "missing_key", default=100)
    assert val == 100


def test_config_get_all_missing_namespace(tmp_path: Path):
    config = Config(tmp_path)
    data = config.get_all("missing_ns")
    assert data == {}


def test_config_set_and_get(tmp_path: Path):
    config = Config(tmp_path)
    config.set("core", "volume", 0.8)
    config.set("core", "enabled", True)

    assert config.get("core", "volume") == 0.8
    assert config.get("core", "enabled") is True

    # Reload in a separate instance to verify disk persistence
    config2 = Config(tmp_path)
    assert config2.get("core", "volume") == 0.8
    assert config2.get("core", "enabled") is True


def test_list_namespaces(tmp_path: Path):
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "llm.json").write_text('{"model": "llama3"}', encoding="utf-8")
    (config_dir / "tts.json").write_text('{"voice": "british"}', encoding="utf-8")

    config = Config(tmp_path)
    # Also add in-memory namespace
    config.set("memory_only", "key", "val")

    namespaces = config.list_namespaces()
    assert "llm" in namespaces
    assert "tts" in namespaces
    assert "memory_only" in namespaces


def test_list_namespaces_empty(tmp_path: Path):
    config = Config(tmp_path)
    assert config.list_namespaces() == []


def test_get_all(tmp_path: Path):
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "audio.json").write_text('{"sample_rate": 16000, "channels": 1}', encoding="utf-8")

    config = Config(tmp_path)
    all_data = config.get_all("audio")
    assert all_data == {"sample_rate": 16000, "channels": 1}

    # Verify mutation of returned dict does not mutate internal cache
    all_data["sample_rate"] = 48000
    assert config.get("audio", "sample_rate") == 16000


def test_atomic_save(tmp_path: Path):
    config = Config(tmp_path)
    config.set("stt", "model", "whisper-base")

    config_dir = tmp_path / "config"
    assert (config_dir / "stt.json").exists()

    # Ensure no leftover temporary files
    tmp_files = list(config_dir.glob("*.tmp"))
    assert len(tmp_files) == 0

    content = json.loads((config_dir / "stt.json").read_text(encoding="utf-8"))
    assert content == {"model": "whisper-base"}


def test_corrupt_json_file(tmp_path: Path):
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "broken.json").write_text("{ broken json content ::: ", encoding="utf-8")

    config = Config(tmp_path)
    # Should not throw JSONDecodeError; should return empty dict or default
    assert config.get_all("broken") == {}
    assert config.get("broken", "key", default="fallback") == "fallback"


def test_nested_namespace(tmp_path: Path):
    config = Config(tmp_path)
    config.set("plugins/whisper", "threads", 4)

    assert config.get("plugins/whisper", "threads") == 4
    config_dir = tmp_path / "config"
    assert (config_dir / "plugins" / "whisper.json").exists()

    config2 = Config(tmp_path)
    assert config2.get("plugins/whisper", "threads") == 4


def test_list_namespaces_no_phantom_stems(tmp_path: Path):
    config_dir = tmp_path / "config"
    (config_dir / "plugins").mkdir(parents=True, exist_ok=True)
    (config_dir / "plugins" / "whisper.json").write_text('{"threads": 4}', encoding="utf-8")
    (config_dir / "audio.json").write_text('{"rate": 16000}', encoding="utf-8")

    cfg = Config(tmp_path)
    namespaces = cfg.list_namespaces()
    assert namespaces == ["audio", "plugins/whisper"]
    assert "whisper" not in namespaces
