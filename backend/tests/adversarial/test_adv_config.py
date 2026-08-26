import asyncio
import json
import os
from pathlib import Path
import pytest
from jarvis.core.config import Config


def test_corrupt_files_variations(tmp_path: Path):
    """Adversarial test: config gracefully handles invalid UTF-8, binary garbage, empty files, truncated JSON."""
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    # 1. Truncated JSON
    (config_dir / "truncated.json").write_text('{"key": "val", "arr": [1, 2,', encoding="utf-8")
    # 2. Raw binary garbage
    (config_dir / "binary.json").write_bytes(b"\x80\x81\xff\xfe\x00\x01\x02\x03\xaa\xbb")
    # 3. Empty file
    (config_dir / "empty.json").write_text("", encoding="utf-8")
    # 4. JSON array instead of object
    (config_dir / "array.json").write_text("[1, 2, 3]", encoding="utf-8")

    cfg = Config(tmp_path)
    assert cfg.get_all("truncated") == {}
    assert cfg.get_all("binary") == {}
    assert cfg.get_all("empty") == {}
    arr_val = cfg.get("array")
    assert arr_val == [1, 2, 3] or arr_val == {}


@pytest.mark.asyncio
async def test_concurrent_writes_same_namespace(tmp_path: Path):
    """Stress test: 50 concurrent tasks writing different keys to the same namespace."""
    cfg = Config(tmp_path)
    num_tasks = 50

    async def write_worker(idx: int):
        for i in range(20):
            cfg.set("stress_ns", f"key_{idx}_{i}", i * 100)
            await asyncio.sleep(0.001)

    tasks = [asyncio.create_task(write_worker(t)) for t in range(num_tasks)]
    await asyncio.gather(*tasks)

    # Verify that file on disk is valid JSON
    config_path = tmp_path / "config" / "stress_ns.json"
    assert config_path.exists()
    raw = config_path.read_text(encoding="utf-8")
    data = json.loads(raw)
    assert isinstance(data, dict)

    # Verify reading via new Config instance
    cfg2 = Config(tmp_path)
    all_data = cfg2.get_all("stress_ns")
    assert len(all_data) > 0


@pytest.mark.asyncio
async def test_concurrent_reads_and_writes_under_load(tmp_path: Path):
    """Stress test: Concurrent reading while continuous writing is happening."""
    cfg = Config(tmp_path)
    stop_event = asyncio.Event()
    read_errors = []

    async def writer():
        counter = 0
        while not stop_event.is_set():
            cfg.set("rapid_ns", "counter", counter)
            counter += 1
            await asyncio.sleep(0.002)

    async def reader(reader_id: int):
        while not stop_event.is_set():
            try:
                val = cfg.get("rapid_ns", "counter", default=-1)
                assert isinstance(val, int)
            except Exception as e:
                read_errors.append((reader_id, e))
            await asyncio.sleep(0.001)

    write_task = asyncio.create_task(writer())
    read_tasks = [asyncio.create_task(reader(i)) for i in range(10)]

    await asyncio.sleep(0.5)
    stop_event.set()
    await write_task
    await asyncio.gather(*read_tasks)

    assert len(read_errors) == 0, f"Read errors encountered during concurrent writes: {read_errors}"


def test_list_namespaces_nested_and_deduplication(tmp_path: Path):
    """Test namespace discovery with nested and deep paths."""
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "core.json").write_text("{}", encoding="utf-8")
    (config_dir / "plugins").mkdir(parents=True, exist_ok=True)
    (config_dir / "plugins" / "whisper.json").write_text("{}", encoding="utf-8")
    (config_dir / "plugins" / "sub").mkdir(parents=True, exist_ok=True)
    (config_dir / "plugins" / "sub" / "deep.json").write_text("{}", encoding="utf-8")

    cfg = Config(tmp_path)
    namespaces = cfg.list_namespaces()
    assert "core" in namespaces
    assert "plugins/whisper" in namespaces
    assert "plugins/sub/deep" in namespaces
