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
        self._user_lat: float = 17.3843
        self._user_lon: float = 78.4583
        self._cached_flights: list[dict[str, Any]] = []
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
        """Fetch real-time location and weather conditions asynchronously using Open APIs."""
        loop = asyncio.get_running_loop()

        def _fetch_open_apis() -> Optional[dict[str, Any]]:
            # 1. IP-API: free open geolocation endpoint
            city = self._cached_weather.get("city", "HYDERABAD")
            region = self._cached_weather.get("region", "TELANGANA")
            country = self._cached_weather.get("country", "INDIA")
            lat = self._user_lat
            lon = self._user_lon

            try:
                ip_req = urllib.request.Request(
                    "http://ip-api.com/json/",
                    headers={"User-Agent": "JarvisAI-HUD/1.0"},
                )
                with urllib.request.urlopen(ip_req, timeout=2.5) as resp:
                    ip_data = json.loads(resp.read().decode("utf-8"))
                    if ip_data.get("status") == "success":
                        city = ip_data.get("city", city)
                        region = ip_data.get("regionName", region)
                        country = ip_data.get("country", country)
                        lat = float(ip_data.get("lat", lat))
                        lon = float(ip_data.get("lon", lon))
                        self._user_lat = lat
                        self._user_lon = lon
            except Exception:
                pass

            # 2. Open-Meteo: free open weather API (No API key needed)
            wmo_map = {
                0: "CLEAR SKY", 1: "MAINLY CLEAR", 2: "PARTLY CLOUDY", 3: "OVERCAST",
                45: "FOG", 48: "DEPOSITING RIME FOG", 51: "LIGHT DRIZZLE", 53: "MODERATE DRIZZLE",
                55: "DENSE DRIZZLE", 61: "SLIGHT RAIN", 63: "MODERATE RAIN", 65: "HEAVY RAIN",
                71: "SLIGHT SNOW", 73: "MODERATE SNOW", 75: "HEAVY SNOW", 80: "SLIGHT SHOWERS",
                81: "MODERATE SHOWERS", 82: "VIOLENT SHOWERS", 95: "THUNDERSTORM",
            }

            try:
                meteo_url = (
                    f"https://api.open-meteo.com/v1/forecast?latitude={lat:.4f}&longitude={lon:.4f}"
                    f"&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m"
                )
                meteo_req = urllib.request.Request(meteo_url, headers={"User-Agent": "JarvisAI-HUD/1.0"})
                with urllib.request.urlopen(meteo_req, timeout=3.0) as resp:
                    m_data = json.loads(resp.read().decode("utf-8"))
                    curr = m_data.get("current", {})
                    if curr:
                        t_c = round(float(curr.get("temperature_2m", 24)))
                        hum = round(float(curr.get("relative_humidity_2m", 50)))
                        wind = round(float(curr.get("wind_speed_10m", 10)))
                        w_code = int(curr.get("weather_code", 0))
                        cond = wmo_map.get(w_code, "FAIR")

                        return {
                            "city": city.upper(),
                            "region": region.upper(),
                            "country": country.upper(),
                            "temp_c": t_c,
                            "temp_f": round(t_c * 9 / 5 + 32),
                            "feels_like_c": t_c,
                            "condition": cond,
                            "humidity": hum,
                            "wind_kmph": wind,
                            "lat": lat,
                            "lon": lon,
                            "last_updated": time.time(),
                        }
            except Exception:
                pass

            # 3. Fallback: wttr.in
            try:
                req = urllib.request.Request(
                    "https://wttr.in/?format=j1",
                    headers={"User-Agent": "curl/8.0 (JarvisAI-HUD)"},
                )
                with urllib.request.urlopen(req, timeout=2.5) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    if data and "current_condition" in data:
                        current = data["current_condition"][0]
                        area = data.get("nearest_area", [{}])[0]
                        c_name = area.get("areaName", [{}])[0].get("value", city)
                        r_name = area.get("region", [{}])[0].get("value", region)
                        t_c = int(current.get("temp_C", 24))
                        return {
                            "city": c_name.upper(),
                            "region": r_name.upper(),
                            "country": country.upper(),
                            "temp_c": t_c,
                            "temp_f": int(current.get("temp_F", round(t_c * 9 / 5 + 32))),
                            "feels_like_c": int(current.get("FeelsLikeC", t_c)),
                            "condition": current.get("weatherDesc", [{}])[0].get("value", "Clear").upper(),
                            "humidity": int(current.get("humidity", 50)),
                            "wind_kmph": int(current.get("windspeedKmph", 10)),
                            "lat": lat,
                            "lon": lon,
                            "last_updated": time.time(),
                        }
            except Exception:
                pass

            return None

        data = await loop.run_in_executor(None, _fetch_open_apis)
        if data:
            self._cached_weather = data
        return self._cached_weather

    async def fetch_airspace_flights(self) -> list[dict[str, Any]]:
        """Fetch real-time ADS-B aircraft positions from OpenSky Network open API."""
        loop = asyncio.get_running_loop()

        def _fetch_opensky() -> list[dict[str, Any]]:
            lat = self._user_lat
            lon = self._user_lon
            # +/- 4.5 degrees bounding box around user (~500km radius)
            lamin = lat - 4.5
            lamax = lat + 4.5
            lomin = lon - 4.5
            lomax = lon + 4.5

            url = (
                f"https://opensky-network.org/api/states/all?"
                f"lamin={lamin:.2f}&lomin={lomin:.2f}&lamax={lamax:.2f}&lomax={lomax:.2f}"
            )
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "JarvisAI-HUD/1.0"})
                with urllib.request.urlopen(req, timeout=4.0) as resp:
                    payload = json.loads(resp.read().decode("utf-8"))
                    states = payload.get("states") or []
                    flights = []

                    for st in states[:16]:
                        if not st or len(st) < 15:
                            continue
                        callsign = (st[1] or "").strip()
                        if not callsign:
                            callsign = f"FLT-{st[0][-4:].upper()}"

                        f_lon = float(st[5]) if st[5] is not None else lon
                        f_lat = float(st[6]) if st[6] is not None else lat
                        alt_m = float(st[7]) if st[7] is not None else 8500.0
                        vel_ms = float(st[9]) if st[9] is not None else 210.0
                        heading_deg = float(st[10]) if st[10] is not None else 90.0
                        squawk = str(st[14]) if st[14] is not None else "7700"

                        # Normalized position relative to user position (-1.0 to 1.0)
                        x_norm = max(-0.95, min(0.95, (f_lon - lon) / 4.5))
                        y_norm = max(-0.95, min(0.95, (lat - f_lat) / 4.5))
                        heading_rad = heading_deg * (math.pi / 180.0)
                        alt_fl = max(10, int(alt_m * 3.28084 / 100))
                        speed_kts = max(120, int(vel_ms * 1.94384))

                        flights.append({
                            "callsign": callsign,
                            "xNorm": round(x_norm, 3),
                            "yNorm": round(y_norm, 3),
                            "heading": round(heading_rad, 3),
                            "altitudeFL": alt_fl,
                            "speedKnots": speed_kts,
                            "squawk": squawk,
                            "country": st[2] or "Commercial",
                            "isStark": False,
                        })

                    return flights
            except Exception:
                return []

        real_flights = await loop.run_in_executor(None, _fetch_opensky)
        if real_flights:
            self._cached_flights = real_flights
        return self._cached_flights

    def get_weather_telemetry(self) -> dict[str, Any]:
        return self._cached_weather

    def get_airspace_telemetry(self) -> list[dict[str, Any]]:
        return self._cached_flights

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
            "flights": self.get_airspace_telemetry(),
            "timestamp": time.time(),
        }
