/**
 * Jarvis AI - Subsystem Script Runner & Terminal Stream
 * Simulates autonomous background daemons, plasma regulation scripts, and diagnostic pipelines.
 * Features:
 * - Continuous auto-scrolling terminal stream with authentic Iron Man subroutines
 * - Color-coded syntax badges: [EXEC], [OK], [RUN], [SYNC], [WARN]
 * - State-reactive speedup during THINKING and SPEAKING
 */

import { JarvisState } from "../core/types";

interface ScriptLogEntry {
  tag: "EXEC" | "OK" | "RUN" | "SYNC" | "WARN";
  command: string;
  timestamp: string;
}

export class ScriptRunnerHUD {
  private container: HTMLElement;
  private logElement: HTMLElement;
  private isRunning = false;
  private intervalId: number | null = null;
  private state: JarvisState = "idle";
  private scriptPool: ScriptLogEntry[] = [];
  private poolIndex = 0;

  constructor(container: HTMLElement) {
    this.container = container;
    const logEl = container.querySelector(".script-terminal-logs") as HTMLElement;
    if (!logEl) throw new Error("Missing .script-terminal-logs container");
    this.logElement = logEl;

    this.initScriptPool();
    this.start();
  }

  private initScriptPool(): void {
    this.scriptPool = [
      { tag: "EXEC", command: "arc_flux.regulate_plasma_pressure()", timestamp: "" },
      { tag: "OK",   command: "repulsor_array.pre_fire_check -> READY", timestamp: "" },
      { tag: "RUN",  command: "neural_matrix.stream_weights(0x7F4A)", timestamp: "" },
      { tag: "SYNC", command: "satellite_link.quantum_handshake(SAT-4)", timestamp: "" },
      { tag: "OK",   command: "thermal_dissipation.coolant_flow == 98.4%", timestamp: "" },
      { tag: "EXEC", command: "airspace_tracker.query_ads_b_corridors()", timestamp: "" },
      { tag: "SYNC", command: "biometric_sensors.vital_signs == OPTIMAL", timestamp: "" },
      { tag: "RUN",  command: "vision_engine.face_mesh_triangulation()", timestamp: "" },
      { tag: "OK",   command: "defense_grid.perimeter_mesh == ONLINE", timestamp: "" },
      { tag: "EXEC", command: "quantum_bridge.allocate_subroutines(4)", timestamp: "" },
      { tag: "RUN",  command: "speech_pipeline.vad_energy_continuous()", timestamp: "" },
      { tag: "OK",   command: "avionics.flight_path_optimization == PASS", timestamp: "" },
    ];
  }

  public start(): void {
    if (this.isRunning) return;
    this.isRunning = true;
    this.scheduleNextEntry();
  }

  public stop(): void {
    this.isRunning = false;
    if (this.intervalId !== null) {
      clearTimeout(this.intervalId);
      this.intervalId = null;
    }
  }

  public setState(state: JarvisState): void {
    this.state = state;
  }

  private scheduleNextEntry(): void {
    if (!this.isRunning) return;

    let delay = 1200;
    if (this.state === "thinking") delay = 350;
    else if (this.state === "speaking") delay = 600;
    else if (this.state === "listening") delay = 800;

    this.intervalId = window.setTimeout(() => {
      this.addNextLog();
      this.scheduleNextEntry();
    }, delay);
  }

  private addNextLog(): void {
    const entry = this.scriptPool[this.poolIndex];
    this.poolIndex = (this.poolIndex + 1) % this.scriptPool.length;

    const now = new Date();
    const timeStr = `${now.getHours().toString().padStart(2, "0")}:${now.getMinutes().toString().padStart(2, "0")}:${now.getSeconds().toString().padStart(2, "0")}.${Math.floor(now.getMilliseconds() / 100)}`;

    const row = document.createElement("div");
    row.className = "script-log-row";

    let tagClass = "tag-cyan";
    if (entry.tag === "OK") tagClass = "tag-green";
    else if (entry.tag === "RUN") tagClass = "tag-gold";
    else if (entry.tag === "SYNC") tagClass = "tag-cyan";
    else if (entry.tag === "WARN") tagClass = "tag-red";

    row.innerHTML = `
      <span class="log-time">${timeStr}</span>
      <span class="log-tag ${tagClass}">[${entry.tag}]</span>
      <span class="log-cmd">${entry.command}</span>
    `;

    this.logElement.appendChild(row);

    // Keep last 15 entries
    while (this.logElement.children.length > 15) {
      this.logElement.removeChild(this.logElement.firstChild as Node);
    }

    // Auto-scroll to bottom
    this.logElement.scrollTop = this.logElement.scrollHeight;
  }

  public destroy(): void {
    this.stop();
  }
}
