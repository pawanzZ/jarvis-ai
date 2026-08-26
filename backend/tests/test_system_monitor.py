import pytest
from jarvis.system.monitor import SystemMonitor


def test_system_monitor_initialization():
    monitor = SystemMonitor()
    assert monitor.session_start_time > 0
    assert isinstance(monitor._os_info, dict)
    assert "distro" in monitor._os_info
    assert "kernel" in monitor._os_info
    assert isinstance(monitor._gpu_info, str)


def test_cpu_telemetry():
    monitor = SystemMonitor()
    cpu = monitor.get_cpu_telemetry()
    assert "usage_percent" in cpu
    assert 0.0 <= cpu["usage_percent"] <= 100.0
    assert cpu["cores"] >= 1
    assert len(cpu["load_avg"]) == 3


def test_memory_telemetry():
    monitor = SystemMonitor()
    mem = monitor.get_memory_telemetry()
    assert "total_mb" in mem
    assert "used_mb" in mem
    assert "usage_percent" in mem
    assert mem["total_mb"] >= 0
    assert 0.0 <= mem["usage_percent"] <= 100.0


def test_disk_telemetry():
    monitor = SystemMonitor()
    disk = monitor.get_disk_telemetry("/")
    assert "total_gb" in disk
    assert "used_gb" in disk
    assert "free_gb" in disk
    assert 0.0 <= disk["usage_percent"] <= 100.0


def test_network_telemetry():
    monitor = SystemMonitor()
    net = monitor.get_network_telemetry()
    assert "rx_kbps" in net
    assert "tx_kbps" in net
    assert net["rx_kbps"] >= 0.0
    assert net["tx_kbps"] >= 0.0


def test_uptime_telemetry():
    monitor = SystemMonitor()
    uptime = monitor.get_uptime_telemetry()
    assert "session_seconds" in uptime
    assert "session_str" in uptime
    assert "system_seconds" in uptime
    assert "system_uptime_str" in uptime
    assert uptime["session_seconds"] >= 0


def test_telemetry_snapshot():
    monitor = SystemMonitor()
    snap = monitor.get_telemetry_snapshot()
    assert "cpu" in snap
    assert "gpu" in snap
    assert "memory" in snap
    assert "disk" in snap
    assert "network" in snap
    assert "uptime" in snap
    assert "os" in snap
    assert "weather" in snap
    assert "timestamp" in snap


@pytest.mark.asyncio
async def test_weather_fallback():
    monitor = SystemMonitor()
    weather = await monitor.fetch_weather_and_location()
    assert "city" in weather
    assert "temp_c" in weather
    assert "condition" in weather
    assert "humidity" in weather
