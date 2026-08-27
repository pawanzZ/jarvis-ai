/**
 * Jarvis AI - Tactical Holographic Radar & Sonar Sweep
 * Features:
 * - Concentric calibrated range rings with cardinal crosshairs (N, E, S, W)
 * - Continuous 360-degree rotating phosphor radar sweep with trailing luminescence
 * - Detected target blips with pulse rings, target lock brackets, and range/azimuth telemetry
 * - Dynamic azimuth angle readouts and audio-reactive target tracking
 */

import { JarvisState } from "../core/types";

interface RadarTarget {
  id: string;
  distNorm: number; // 0.1 to 0.95
  angle: number;    // Radians
  label: string;
  speed: number;    // Angular drift speed
  type: "hostile" | "friendly" | "satellite";
  lastPingTime: number;
}

export class TacticalRadar {
  private canvas: HTMLCanvasElement;
  private ctx: CanvasRenderingContext2D;
  private animFrameId: number | null = null;
  private isRunning = false;
  private state: JarvisState = "idle";
  private sweepAngle = 0;
  private targets: RadarTarget[] = [];
  private audioLevel = 0;

  constructor(canvas: HTMLCanvasElement) {
    this.canvas = canvas;
    const context = canvas.getContext("2d");
    if (!context) throw new Error("Could not get 2D context for TacticalRadar");
    this.ctx = context;

    this.initTargets();
    this.resize();
    window.addEventListener("resize", this.handleResize);
    this.start();
  }

  private initTargets(): void {
    this.targets = [
      { id: "TGT-01", distNorm: 0.68, angle: 1.1, label: "LOCKED", speed: 0.0012, type: "hostile", lastPingTime: 0 },
      { id: "SAT-4", distNorm: 0.88, angle: 3.8, label: "GEO-SYNC", speed: -0.0008, type: "satellite", lastPingTime: 0 },
      { id: "NODE-L", distNorm: 0.38, angle: 5.2, label: "SECURE", speed: 0.0015, type: "friendly", lastPingTime: 0 },
      { id: "SIG-09", distNorm: 0.52, angle: 2.4, label: "TRACKING", speed: -0.0018, type: "friendly", lastPingTime: 0 },
    ];
  }

  private handleResize = (): void => {
    this.resize();
  };

  public resize(): void {
    const dpr = window.devicePixelRatio || 1;
    const rect = this.canvas.getBoundingClientRect();
    const width = rect.width || 280;
    const height = rect.height || 180;

    this.canvas.width = width * dpr;
    this.canvas.height = height * dpr;
    this.ctx.resetTransform?.();
    this.ctx.scale(dpr, dpr);
  }

  public start(): void {
    if (this.isRunning) return;
    this.isRunning = true;
    this.startRenderLoop();
  }

  public stop(): void {
    this.isRunning = false;
    if (this.animFrameId !== null) {
      cancelAnimationFrame(this.animFrameId);
      this.animFrameId = null;
    }
  }

  public setState(state: JarvisState): void {
    this.state = state;
  }

  public setAudioLevel(level: number): void {
    this.audioLevel = Math.max(0, Math.min(1, level));
  }

  private startRenderLoop = (): void => {
    if (!this.isRunning) return;

    let sweepSpeed = 0.024;
    if (this.state === "listening") sweepSpeed = 0.038;
    else if (this.state === "thinking") sweepSpeed = 0.065;
    else if (this.state === "speaking") sweepSpeed = 0.042;
    else if (this.state === "error") sweepSpeed = 0.032;

    this.sweepAngle = (this.sweepAngle + sweepSpeed) % (Math.PI * 2);

    // Update targets drift
    for (const tgt of this.targets) {
      tgt.angle = (tgt.angle + tgt.speed) % (Math.PI * 2);

      // Check if sweep line passed over target to trigger ping flash
      const angleDiff = Math.abs((this.sweepAngle - tgt.angle + Math.PI * 3) % (Math.PI * 2) - Math.PI);
      if (angleDiff < 0.08) {
        tgt.lastPingTime = Date.now();
      }
    }

    this.render();
    this.animFrameId = requestAnimationFrame(this.startRenderLoop);
  };

  private render(): void {
    const rect = this.canvas.getBoundingClientRect();
    const width = rect.width || 280;
    const height = rect.height || 180;
    const cx = width * 0.5;
    const cy = height * 0.5;
    const radarRadius = Math.min(width, height) * 0.44;

    this.ctx.clearRect(0, 0, width, height);

    // 1. Radar Circular Mask & Background Grid
    this.ctx.save();

    // Subtle dark radial background
    const bgGrad = this.ctx.createRadialGradient(cx, cy, 0, cx, cy, radarRadius);
    bgGrad.addColorStop(0, "rgba(0, 25, 45, 0.5)");
    bgGrad.addColorStop(0.85, "rgba(0, 18, 32, 0.7)");
    bgGrad.addColorStop(1, "rgba(0, 10, 20, 0.9)");

    this.ctx.beginPath();
    this.ctx.arc(cx, cy, radarRadius, 0, Math.PI * 2);
    this.ctx.fillStyle = bgGrad;
    this.ctx.fill();

    // 2. Concentric Range Rings (25km, 50km, 75km, 100km)
    const numRings = 4;
    for (let r = 1; r <= numRings; r++) {
      const ringR = (r / numRings) * radarRadius;
      this.ctx.beginPath();
      this.ctx.arc(cx, cy, ringR, 0, Math.PI * 2);
      this.ctx.lineWidth = r === numRings ? 1.5 : 0.8;
      this.ctx.strokeStyle = r === numRings
        ? "rgba(0, 212, 255, 0.6)"
        : "rgba(0, 180, 255, 0.2)";
      if (r < numRings) {
        this.ctx.setLineDash([3, 4]);
      } else {
        this.ctx.setLineDash([]);
      }
      this.ctx.stroke();
      this.ctx.setLineDash([]);
    }

    // 3. Crosshairs & Cardinal Degree Indices
    this.ctx.beginPath();
    this.ctx.moveTo(cx - radarRadius, cy);
    this.ctx.lineTo(cx + radarRadius, cy);
    this.ctx.moveTo(cx, cy - radarRadius);
    this.ctx.lineTo(cx, cy + radarRadius);
    this.ctx.lineWidth = 0.8;
    this.ctx.strokeStyle = "rgba(0, 180, 255, 0.25)";
    this.ctx.stroke();

    // Cardinal Labels (N, E, S, W)
    this.ctx.font = "bold 8px 'Fira Code', 'Roboto Mono', monospace";
    this.ctx.fillStyle = "rgba(0, 212, 255, 0.8)";
    this.ctx.textAlign = "center";
    this.ctx.textBaseline = "middle";
    this.ctx.fillText("N", cx, cy - radarRadius + 7);
    this.ctx.fillText("S", cx, cy + radarRadius - 7);
    this.ctx.fillText("E", cx + radarRadius - 7, cy);
    this.ctx.fillText("W", cx - radarRadius + 7, cy);

    // 4. Rotating Phosphor Radar Sweep Beam (Pie Slice with Gradient Decay)
    this.ctx.save();
    const beamAngle = Math.PI * 0.28; // ~50 degrees
    const startAngle = this.sweepAngle - beamAngle;
    const endAngle = this.sweepAngle;

    this.ctx.beginPath();
    this.ctx.moveTo(cx, cy);
    this.ctx.arc(cx, cy, radarRadius, startAngle, endAngle);
    this.ctx.closePath();

    const sweepGrad = this.ctx.createRadialGradient(cx, cy, 0, cx, cy, radarRadius);
    sweepGrad.addColorStop(0, "rgba(0, 255, 200, 0.45)");
    sweepGrad.addColorStop(0.7, "rgba(0, 212, 255, 0.2)");
    sweepGrad.addColorStop(1, "rgba(0, 150, 255, 0.0)");
    this.ctx.fillStyle = sweepGrad;
    this.ctx.fill();

    // Bright Leading Sweep Ray
    this.ctx.beginPath();
    this.ctx.moveTo(cx, cy);
    this.ctx.lineTo(cx + Math.cos(endAngle) * radarRadius, cy + Math.sin(endAngle) * radarRadius);
    this.ctx.lineWidth = 1.6;
    this.ctx.strokeStyle = "#ffffff";
    this.ctx.shadowBlur = 6;
    this.ctx.shadowColor = "rgba(0, 255, 200, 0.8)";
    this.ctx.stroke();
    this.ctx.restore();

    // 5. Target Blips with Pulsing Pings & Tracking Brackets
    const now = Date.now();
    for (const tgt of this.targets) {
      const tx = cx + Math.cos(tgt.angle) * (tgt.distNorm * radarRadius);
      const ty = cy + Math.sin(tgt.angle) * (tgt.distNorm * radarRadius);

      const timeSincePing = (now - tgt.lastPingTime) / 1000;
      const pingAlpha = Math.max(0.2, Math.exp(-timeSincePing * 1.5));

      let blipColor = "rgba(0, 212, 255,";
      if (tgt.type === "hostile") blipColor = "rgba(255, 80, 80,";
      else if (tgt.type === "satellite") blipColor = "rgba(255, 200, 0,";

      // Blip Dot
      this.ctx.beginPath();
      this.ctx.arc(tx, ty, 2.5 + this.audioLevel * 2, 0, Math.PI * 2);
      this.ctx.fillStyle = `${blipColor} ${pingAlpha})`;
      this.ctx.fill();

      // Expanding Ripple Ring on Recent Ping
      if (timeSincePing < 1.0) {
        const rippleR = 4 + timeSincePing * 14;
        this.ctx.beginPath();
        this.ctx.arc(tx, ty, rippleR, 0, Math.PI * 2);
        this.ctx.lineWidth = 1.0;
        this.ctx.strokeStyle = `${blipColor} ${(1.0 - timeSincePing) * 0.7})`;
        this.ctx.stroke();
      }

      // Target Tracking Bracket [ ]
      const bracketSize = 5;
      this.ctx.lineWidth = 1.0;
      this.ctx.strokeStyle = `${blipColor} ${pingAlpha * 0.85})`;
      this.ctx.beginPath();
      // Left bracket
      this.ctx.moveTo(tx - bracketSize, ty - bracketSize);
      this.ctx.lineTo(tx - bracketSize, ty + bracketSize);
      // Right bracket
      this.ctx.moveTo(tx + bracketSize, ty - bracketSize);
      this.ctx.lineTo(tx + bracketSize, ty + bracketSize);
      this.ctx.stroke();

      // Mini Target ID Label
      this.ctx.font = "7px 'Fira Code', 'Roboto Mono', monospace";
      this.ctx.fillStyle = `${blipColor} ${Math.min(1.0, pingAlpha + 0.3)})`;
      this.ctx.fillText(tgt.id, tx + 8, ty - 2);
    }

    // 6. Live Telemetry Readouts (Azimuth & Status Ticker)
    const deg = Math.round((this.sweepAngle / (Math.PI * 2)) * 360);
    this.ctx.font = "bold 9px 'Fira Code', 'Roboto Mono', monospace";
    this.ctx.textAlign = "left";
    this.ctx.fillStyle = "rgba(0, 212, 255, 0.9)";
    this.ctx.fillText(`AZ: ${deg.toString().padStart(3, "0")}°`, 12, height - 10);

    this.ctx.textAlign = "right";
    this.ctx.fillStyle = "rgba(0, 245, 212, 0.85)";
    this.ctx.fillText(`CONTACTS: ${this.targets.length}`, width - 12, height - 10);

    this.ctx.restore();
  }

  public destroy(): void {
    this.stop();
    window.removeEventListener("resize", this.handleResize);
  }
}
