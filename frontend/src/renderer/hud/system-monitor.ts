/**
 * Jarvis AI - System Monitor HUD Component
 * Displays real-time hardware telemetry (CPU, GPU, Memory, Disk, Network)
 * and operating system host specifications with Iron Man HUD aesthetics.
 */

import { SystemTelemetryData } from "../core/types";

export class SystemMonitorHUD {
  private cpuValEl: HTMLElement | null = null;
  private cpuBarEl: HTMLElement | null = null;
  private cpuCoresEl: HTMLElement | null = null;
  private gpuNameEl: HTMLElement | null = null;
  private memValEl: HTMLElement | null = null;
  private memBarEl: HTMLElement | null = null;
  private diskValEl: HTMLElement | null = null;
  private diskBarEl: HTMLElement | null = null;
  private netRxEl: HTMLElement | null = null;
  private netTxEl: HTMLElement | null = null;
  private osDistroEl: HTMLElement | null = null;
  private osKernelEl: HTMLElement | null = null;
  private sysUptimeEl: HTMLElement | null = null;
  private sessionTimeEl: HTMLElement | null = null;

  constructor() {
    this.bindElements();
  }

  private bindElements(): void {
    this.cpuValEl = document.getElementById("telem-cpu-val");
    this.cpuBarEl = document.getElementById("telem-cpu-bar");
    this.cpuCoresEl = document.getElementById("telem-cpu-cores");
    this.gpuNameEl = document.getElementById("telem-gpu-name");
    this.memValEl = document.getElementById("telem-mem-val");
    this.memBarEl = document.getElementById("telem-mem-bar");
    this.diskValEl = document.getElementById("telem-disk-val");
    this.diskBarEl = document.getElementById("telem-disk-bar");
    this.netRxEl = document.getElementById("telem-net-rx");
    this.netTxEl = document.getElementById("telem-net-tx");
    this.osDistroEl = document.getElementById("telem-os-distro");
    this.osKernelEl = document.getElementById("telem-os-kernel");
    this.sysUptimeEl = document.getElementById("telem-sys-uptime");
    this.sessionTimeEl = document.getElementById("telem-session-time");
  }

  public update(telemetry: SystemTelemetryData): void {
    if (!telemetry) return;

    // 1. CPU Telemetry
    if (telemetry.cpu) {
      const cpuPct = telemetry.cpu.usage_percent ?? 0;
      if (this.cpuValEl) {
        this.cpuValEl.textContent = `${cpuPct.toFixed(1)}%`;
      }
      if (this.cpuBarEl) {
        this.cpuBarEl.style.width = `${Math.min(100, Math.max(2, cpuPct))}%`;
        this.cpuBarEl.style.background = cpuPct > 85 ? "var(--accent-red)" : cpuPct > 60 ? "var(--accent-amber)" : "var(--accent-cyan)";
      }
      if (this.cpuCoresEl) {
        this.cpuCoresEl.textContent = `${telemetry.cpu.cores} CORES`;
      }
    }

    // 2. GPU Telemetry
    if (telemetry.gpu && this.gpuNameEl) {
      this.gpuNameEl.textContent = telemetry.gpu.name || "Integrated Graphics";
    }

    // 3. Memory Telemetry
    if (telemetry.memory) {
      const memPct = telemetry.memory.usage_percent ?? 0;
      if (this.memValEl) {
        this.memValEl.textContent = `${telemetry.memory.used_gb} / ${telemetry.memory.total_gb} GB (${memPct.toFixed(0)}%)`;
      }
      if (this.memBarEl) {
        this.memBarEl.style.width = `${Math.min(100, Math.max(2, memPct))}%`;
        this.memBarEl.style.background = memPct > 85 ? "var(--accent-red)" : "var(--accent-cyan)";
      }
    }

    // 4. Disk Storage
    if (telemetry.disk) {
      const diskPct = telemetry.disk.usage_percent ?? 0;
      if (this.diskValEl) {
        this.diskValEl.textContent = `${telemetry.disk.free_gb} GB FREE (${telemetry.disk.total_gb} GB)`;
      }
      if (this.diskBarEl) {
        this.diskBarEl.style.width = `${Math.min(100, Math.max(2, diskPct))}%`;
      }
    }

    // 5. Network Throughput
    if (telemetry.network) {
      if (this.netRxEl) {
        const rxStr = telemetry.network.rx_mbps >= 1.0
          ? `${telemetry.network.rx_mbps.toFixed(2)} MB/s`
          : `${telemetry.network.rx_kbps.toFixed(1)} KB/s`;
        this.netRxEl.textContent = `▼ ${rxStr}`;
      }
      if (this.netTxEl) {
        const txStr = telemetry.network.tx_mbps >= 1.0
          ? `${telemetry.network.tx_mbps.toFixed(2)} MB/s`
          : `${telemetry.network.tx_kbps.toFixed(1)} KB/s`;
        this.netTxEl.textContent = `▲ ${txStr}`;
      }
    }

    // 6. OS & Kernel Info
    if (telemetry.os) {
      if (this.osDistroEl) {
        this.osDistroEl.textContent = telemetry.os.distro || "Linux";
      }
      if (this.osKernelEl) {
        this.osKernelEl.textContent = `${telemetry.os.kernel} (${telemetry.os.arch})`;
      }
    }

    // 7. System Uptime & Screen Time
    if (telemetry.uptime) {
      if (this.sysUptimeEl) {
        this.sysUptimeEl.textContent = telemetry.uptime.system_uptime_str;
      }
      if (this.sessionTimeEl) {
        this.sessionTimeEl.textContent = telemetry.uptime.session_str;
      }
    }
  }
}
