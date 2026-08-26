from __future__ import annotations
import asyncio
import json
import os
import platform
import shutil
import socket
import time
import urllib.request
from typing import Any, Optional


class SystemMonitor:
    """Collects real-time hardware, operating system, network, temporal,

    and environmental telemetry for the Jarvis HUD.
    """

    def __init__(self) -> None:
        self.session_start_time: float = time.time()
        self._prev_cpu_times: Optional[tuple[float, float]] = None
        self._prev_net_bytes: Optional[tuple[int, int, float]] = None
        self._cached_weather: dict[str, Any] = {
            "city": "LOCAL SECTOR",
            "region": "",
            "country": "EARTH",
            "temp_c": 24,
            "temp_f": 75,
            "condition": "NOMINAL",
            "humidity": 50,
            "wind_kmph": 10,
            "feels_like_c": 24,
            "last_updated": 0,
        }
        self._gpu_info: str = self._detect_gpu()
        self._os_info: dict[str, str] = self._detect_os_info()

    def _detect_os_info(self) -> dict[str, str]:
        distro = "Linux"
        if os.path.exists("/etc/os-release"):
            try:
                with open("/etc/os-release", "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("PRETTY_NAME="):
                            distro = line.split("=", 1)[1].strip().strip('"')
                            break
                        elif line.startswith("NAME=") and distro == "Linux":
                            distro = line.split("=", 1)[1].strip().strip('"')
            except Exception:
                pass

        return {
            "distro": distro,
            "kernel": platform.release(),
            "arch": platform.machine(),
            "hostname": socket.gethostname(),
        }

    def _detect_gpu(self) -> str:
        # Check lspci output
        try:
            import subprocess
            res = subprocess.run(
                ["lspci"],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=1.5,
            )
            for line in res.stdout.splitlines():
                if "VGA" in line or "3D" in line or "Display" in line:
                    parts = line.split(":", 2)
                    if len(parts) >= 3:
                        gpu_name = parts[2].strip()
                        # Shorten if long
                        if "Advanced Micro Devices" in gpu_name:
                            return "AMD Radeon Graphics"
                        if "NVIDIA" in gpu_name:
                            return "NVIDIA GeForce"
                        if "Intel" in gpu_name:
                            return "Intel Iris / UHD Graphics"
                        return gpu_name[:32]
        except Exception:
            pass

        # Fallback check DRM cards
        if os.path.exists("/sys/class/drm"):
            return "Integrated DRM Graphics"
        return "Generic GPU / Display"

    def get_cpu_telemetry(self) -> dict[str, Any]:
        """Calculate overall CPU usage percentage via /proc/stat delta."""
        cpu_count = os.cpu_count() or 1
        usage_pct = 0.0

        if os.path.exists("/proc/stat"):
            try:
                with open("/proc/stat", "r") as f:
                    first_line = f.readline()
                parts = first_line.split()
                if len(parts) >= 5 and parts[0] == "cpu":
                    user = float(parts[1])
                    nice = float(parts[2])
                    system = float(parts[3])
                    idle = float(parts[4])
                    iowait = float(parts[5]) if len(parts) > 5 else 0.0
                    irq = float(parts[6]) if len(parts) > 6 else 0.0
                    softirq = float(parts[7]) if len(parts) > 7 else 0.0

                    idle_time = idle + iowait
                    total_time = user + nice + system + idle_time + irq + softirq

                    if self._prev_cpu_times:
                        prev_idle, prev_total = self._prev_cpu_times
                        delta_idle = idle_time - prev_idle
                        delta_total = total_time - prev_total
                        if delta_total > 0:
                            usage_pct = max(0.0, min(100.0, (1.0 - delta_idle / delta_total) * 100.0))
                    self._prev_cpu_times = (idle_time, total_time)
            except Exception:
                pass

        if usage_pct == 0.0:
            try:
                # Load average fallback
                load1, _, _ = os.getloadavg()
                usage_pct = max(0.0, min(100.0, (load1 / cpu_count) * 100.0))
            except Exception:
                usage_pct = 12.5

        load_avg = [0.0, 0.0, 0.0]
        try:
            load_avg = list(os.getloadavg())
        except Exception:
            pass

        return {
            "usage_percent": round(usage_pct, 1),
            "cores": cpu_count,
            "load_avg": [round(l, 2) for l in load_avg],
        }

    def get_memory_telemetry(self) -> dict[str, Any]:
        """Read and compute memory usage from /proc/meminfo."""
        total_mb = 0.0
        avail_mb = 0.0
        used_mb = 0.0
        percent = 0.0

        if os.path.exists("/proc/meminfo"):
            try:
                mem: dict[str, float] = {}
                with open("/proc/meminfo", "r") as f:
                    for line in f:
                        parts = line.split(":")
                        if len(parts) == 2:
                            val = parts[1].strip().split()[0]
                            mem[parts[0].strip()] = float(val)

                total_kb = mem.get("MemTotal", 0.0)
                avail_kb = mem.get("MemAvailable", mem.get("MemFree", 0.0) + mem.get("Buffers", 0.0) + mem.get("Cached", 0.0))
                total_mb = round(total_kb / 1024.0, 1)
                avail_mb = round(avail_kb / 1024.0, 1)
                used_mb = round(max(0.0, total_mb - avail_mb), 1)
                if total_mb > 0:
                    percent = round((used_mb / total_mb) * 100.0, 1)
            except Exception:
                pass

        return {
            "total_mb": total_mb,
            "used_mb": used_mb,
            "free_mb": avail_mb,
            "total_gb": round(total_mb / 1024.0, 2),
            "used_gb": round(used_mb / 1024.0, 2),
            "usage_percent": percent,
        }

    def get_disk_telemetry(self, path: str = "/") -> dict[str, Any]:
        """Read filesystem storage capacity and usage."""
        try:
            usage = shutil.disk_usage(path)
            total_gb = round(usage.total / (1024.0**3), 1)
            used_gb = round(usage.used / (1024.0**3), 1)
            free_gb = round(usage.free / (1024.0**3), 1)
            percent = round((usage.used / usage.total) * 100.0, 1) if usage.total > 0 else 0.0
            return {
                "total_gb": total_gb,
                "used_gb": used_gb,
                "free_gb": free_gb,
                "usage_percent": percent,
            }
        except Exception:
            return {
                "total_gb": 100.0,
                "used_gb": 25.0,
                "free_gb": 75.0,
                "usage_percent": 25.0,
            }

    def get_network_telemetry(self) -> dict[str, Any]:
        """Calculate upload and download transfer rates via /proc/net/dev delta."""
        now = time.time()
        rx_bytes_total = 0
        tx_bytes_total = 0

        if os.path.exists("/proc/net/dev"):
            try:
                with open("/proc/net/dev", "r") as f:
                    lines = f.readlines()[2:]  # Skip headers
                for line in lines:
                    parts = line.split(":")
                    if len(parts) == 2:
                        dev = parts[0].strip()
                        if dev == "lo":
                            continue  # Ignore loopback
                        fields = parts[1].split()
                        rx_bytes_total += int(fields[0])
                        tx_bytes_total += int(fields[8])
            except Exception:
                pass

        rx_rate_kbps = 0.0
        tx_rate_kbps = 0.0

        if self._prev_net_bytes:
            prev_rx, prev_tx, prev_time = self._prev_net_bytes
            dt = max(0.1, now - prev_time)
            rx_rate_kbps = max(0.0, (rx_bytes_total - prev_rx) / 1024.0 / dt)
            tx_rate_kbps = max(0.0, (tx_bytes_total - prev_tx) / 1024.0 / dt)

        self._prev_net_bytes = (rx_bytes_total, tx_bytes_total, now)

        return {
            "rx_kbps": round(rx_rate_kbps, 1),
            "tx_kbps": round(tx_rate_kbps, 1),
            "rx_mbps": round(rx_rate_kbps / 1024.0, 2),
            "tx_mbps": round(tx_rate_kbps / 1024.0, 2),
            "total_rx_mb": round(rx_bytes_total / (1024.0**2), 1),
            "total_tx_mb": round(tx_bytes_total / (1024.0**2), 1),
        }

    def get_uptime_telemetry(self) -> dict[str, Any]:
        """Get system uptime and session screen time."""
        now = time.time()
        session_seconds = int(now - self.session_start_time)
        sh = session_seconds // 3600
        sm = (session_seconds % 3600) // 60
        ss = session_seconds % 60
        session_str = f"{sh:02d}h {sm:02d}m {ss:02d}s"

        sys_seconds = 0
        if os.path.exists("/proc/uptime"):
            try:
                with open("/proc/uptime", "r") as f:
                    sys_seconds = int(float(f.readline().split()[0]))
            except Exception:
                sys_seconds = session_seconds

        days = sys_seconds // 86400
        hours = (sys_seconds % 86400) // 3600
        minutes = (sys_seconds % 3600) // 60
        uptime_str = f"{days}d {hours:02d}h {minutes:02d}m" if days > 0 else f"{hours:02d}h {minutes:02d}m"

        return {
            "session_seconds": session_seconds,
            "session_str": session_str,
            "system_seconds": sys_seconds,
            "system_uptime_str": uptime_str,
        }

    async def fetch_weather_and_location(self) -> dict[str, Any]:
        """Fetch real-time location and weather conditions asynchronously."""
        loop = asyncio.get_running_loop()

        def _fetch() -> Optional[dict[str, Any]]:
            try:
                req = urllib.request.Request(
                    "https://wttr.in/?format=j1",
                    headers={"User-Agent": "curl/8.0 (JarvisAI-HUD)"},
                )
                with urllib.request.urlopen(req, timeout=3.5) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except Exception:
                return None

        data = await loop.run_in_executor(None, _fetch)

        if data and "current_condition" in data:
            try:
                current = data["current_condition"][0]
                area = data.get("nearest_area", [{}])[0]

                city = area.get("areaName", [{}])[0].get("value", "Local Sector")
                region = area.get("region", [{}])[0].get("value", "")
                country = area.get("country", [{}])[0].get("value", "Earth")
                temp_c = int(current.get("temp_C", 24))
                temp_f = int(current.get("temp_F", 75))
                feels_c = int(current.get("FeelsLikeC", temp_c))
                condition = current.get("weatherDesc", [{}])[0].get("value", "Clear")
                humidity = int(current.get("humidity", 50))
                wind_kmph = int(current.get("windspeedKmph", 10))

                self._cached_weather = {
                    "city": city.upper(),
                    "region": region.upper(),
                    "country": country.upper(),
                    "temp_c": temp_c,
                    "temp_f": temp_f,
                    "feels_like_c": feels_c,
                    "condition": condition.upper(),
                    "humidity": humidity,
                    "wind_kmph": wind_kmph,
                    "last_updated": time.time(),
                }
            except Exception as e:
                print(f"[SystemMonitor] Weather parsing error: {e}")

        return self._cached_weather

    def get_weather_telemetry(self) -> dict[str, Any]:
        return self._cached_weather

    def get_telemetry_snapshot(self) -> dict[str, Any]:
        """Collect a full consolidated system telemetry snapshot."""
        return {
            "cpu": self.get_cpu_telemetry(),
            "gpu": {
                "name": self._gpu_info,
                "status": "ONLINE // ACTIVE",
            },
            "memory": self.get_memory_telemetry(),
            "disk": self.get_disk_telemetry(),
            "network": self.get_network_telemetry(),
            "uptime": self.get_uptime_telemetry(),
            "os": self._os_info,
            "weather": self.get_weather_telemetry(),
            "timestamp": time.time(),
        }
