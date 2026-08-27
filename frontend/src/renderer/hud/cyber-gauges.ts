/**
 * Jarvis AI - Dynamic Cyber Arc & Dial Gauges
 * Renders dual futuristic circular arc dials for Arc Power Flux and Core Frequency.
 * Features:
 * - Sweeping animated needles with inertia and elastic overshoot
 * - Segmented measurement tick marks and colored graduated zones (cyan -> gold -> red)
 * - Dynamic digital readouts with pulsating units
 * - Audio-reactive surge and system compute load tracking
 */

import { JarvisState } from "../core/types";

export class CyberGauges {
  private canvas: HTMLCanvasElement;
  private ctx: CanvasRenderingContext2D;
  private animFrameId: number | null = null;
  private isRunning = false;
  private state: JarvisState = "idle";
  private time = 0;

  // Gauge 1: Arc Power Flux [0 - 100%]
  private fluxTarget = 84.5;
  private fluxCurrent = 84.5;
  private fluxNeedleAngle = 0;

  // Gauge 2: Quantum Core Freq [0 - 6.0 GHz]
  private freqTarget = 4.2;
  private freqCurrent = 4.2;
  private freqNeedleAngle = 0;

  private audioLevel = 0;

  constructor(canvas: HTMLCanvasElement) {
    this.canvas = canvas;
    const context = canvas.getContext("2d");
    if (!context) throw new Error("Could not get 2D context for CyberGauges");
    this.ctx = context;

    this.resize();
    window.addEventListener("resize", this.handleResize);
    this.start();
  }

  private handleResize = (): void => {
    this.resize();
  };

  public resize(): void {
    const dpr = window.devicePixelRatio || 1;
    const rect = this.canvas.getBoundingClientRect();
    const width = rect.width || 280;
    const height = rect.height || 120;

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

  public updateTelemetry(cpuPercent: number): void {
    // Dynamically modulate target values from system telemetry
    this.fluxTarget = 75 + (cpuPercent * 0.22);
    this.freqTarget = 3.6 + (cpuPercent * 0.02);
  }

  private startRenderLoop = (): void => {
    if (!this.isRunning) return;

    this.time += 0.04;

    // Organic fluctuation
    const noise1 = Math.sin(this.time * 2.1) * 3.5 + Math.cos(this.time * 4.3) * 1.5;
    const noise2 = Math.cos(this.time * 1.8) * 0.15 + Math.sin(this.time * 3.7) * 0.08;

    const audioBoostFlux = this.audioLevel * 14.0;
    const audioBoostFreq = this.audioLevel * 0.75;

    const currentFluxTarget = Math.min(100, Math.max(10, this.fluxTarget + noise1 + audioBoostFlux));
    const currentFreqTarget = Math.min(6.0, Math.max(1.0, this.freqTarget + noise2 + audioBoostFreq));

    // Smooth inertia interpolation
    this.fluxCurrent += (currentFluxTarget - this.fluxCurrent) * 0.12;
    this.freqCurrent += (currentFreqTarget - this.freqCurrent) * 0.12;

    this.render();
    this.animFrameId = requestAnimationFrame(this.startRenderLoop);
  };

  private render(): void {
    const rect = this.canvas.getBoundingClientRect();
    const width = rect.width || 280;
    const height = rect.height || 120;

    this.ctx.clearRect(0, 0, width, height);

    const gaugeRadius = 42;
    const cy = height * 0.52;
    const cx1 = width * 0.27;
    const cx2 = width * 0.73;

    // 1. Draw Gauge 1: ARC POWER FLUX
    this.drawArcDial(
      cx1,
      cy,
      gaugeRadius,
      this.fluxCurrent / 100,
      "ARC FLUX",
      `${this.fluxCurrent.toFixed(1)}%`,
      "rgba(0, 212, 255,",
      "rgba(255, 170, 0,"
    );

    // 2. Draw Gauge 2: QUANTUM CORE FREQ
    this.drawArcDial(
      cx2,
      cy,
      gaugeRadius,
      this.freqCurrent / 6.0,
      "CORE FREQ",
      `${this.freqCurrent.toFixed(2)} GHz`,
      "rgba(0, 245, 212,",
      "rgba(255, 60, 90,"
    );
  }

  private drawArcDial(
    cx: number,
    cy: number,
    radius: number,
    valueNorm: number, // 0.0 to 1.0
    label: string,
    valText: string,
    primaryColorPrefix: string,
    accentColorPrefix: string
  ): void {
    this.ctx.save();

    // Gauge arc spans from 135 deg to 405 deg (270 degree sweep)
    const startAngle = Math.PI * 0.75;
    const totalSweep = Math.PI * 1.5;
    const endAngle = startAngle + totalSweep;
    const currentAngle = startAngle + Math.min(1.0, Math.max(0.0, valueNorm)) * totalSweep;

    // 1. Background Arc Track
    this.ctx.beginPath();
    this.ctx.arc(cx, cy, radius, startAngle, endAngle);
    this.ctx.lineWidth = 4;
    this.ctx.strokeStyle = "rgba(0, 180, 255, 0.15)";
    this.ctx.stroke();

    // 2. Segmented Graduation Ticks
    const numTicks = 28;
    for (let i = 0; i <= numTicks; i++) {
      const tickAngle = startAngle + (i / numTicks) * totalSweep;
      const isMajor = i % 7 === 0;
      const tickLen = isMajor ? 6 : 3.5;
      const innerR = radius - tickLen;
      const outerR = radius;

      const x1 = cx + Math.cos(tickAngle) * innerR;
      const y1 = cy + Math.sin(tickAngle) * innerR;
      const x2 = cx + Math.cos(tickAngle) * outerR;
      const y2 = cy + Math.sin(tickAngle) * outerR;

      this.ctx.beginPath();
      this.ctx.moveTo(x1, y1);
      this.ctx.lineTo(x2, y2);
      this.ctx.lineWidth = isMajor ? 1.4 : 0.8;
      this.ctx.strokeStyle = tickAngle <= currentAngle
        ? (valueNorm > 0.85 ? `${accentColorPrefix} 0.9)` : `${primaryColorPrefix} 0.85)`)
        : "rgba(255, 255, 255, 0.2)";
      this.ctx.stroke();
    }

    // 3. Active Glowing Filled Arc
    if (valueNorm > 0.02) {
      this.ctx.beginPath();
      this.ctx.arc(cx, cy, radius, startAngle, currentAngle);
      this.ctx.lineWidth = 4.5;
      this.ctx.strokeStyle = valueNorm > 0.85 ? `${accentColorPrefix} 0.95)` : `${primaryColorPrefix} 0.95)`;
      this.ctx.shadowBlur = 8;
      this.ctx.shadowColor = valueNorm > 0.85 ? `${accentColorPrefix} 0.9)` : `${primaryColorPrefix} 0.9)`;
      this.ctx.stroke();
      this.ctx.shadowBlur = 0;
    }

    // 4. Sweeping Needle
    const needleR = radius - 8;
    const nx = cx + Math.cos(currentAngle) * needleR;
    const ny = cy + Math.sin(currentAngle) * needleR;

    this.ctx.beginPath();
    this.ctx.moveTo(cx, cy);
    this.ctx.lineTo(nx, ny);
    this.ctx.lineWidth = 1.8;
    this.ctx.strokeStyle = "#ffffff";
    this.ctx.shadowBlur = 6;
    this.ctx.shadowColor = `${primaryColorPrefix} 0.9)`;
    this.ctx.stroke();
    this.ctx.shadowBlur = 0;

    // Needle Center Pivot Pin
    this.ctx.beginPath();
    this.ctx.arc(cx, cy, 3.5, 0, Math.PI * 2);
    this.ctx.fillStyle = "#ffffff";
    this.ctx.fill();

    this.ctx.beginPath();
    this.ctx.arc(cx, cy, 5.5, 0, Math.PI * 2);
    this.ctx.strokeStyle = `${primaryColorPrefix} 0.8)`;
    this.ctx.lineWidth = 1.2;
    this.ctx.stroke();

    // 5. Digital Value Readout & Label
    this.ctx.font = "bold 10px 'Fira Code', 'Roboto Mono', monospace";
    this.ctx.textAlign = "center";
    this.ctx.fillStyle = "#ffffff";
    this.ctx.fillText(valText, cx, cy + 16);

    this.ctx.font = "8px 'Fira Code', 'Roboto Mono', monospace";
    this.ctx.fillStyle = `${primaryColorPrefix} 0.75)`;
    this.ctx.fillText(label, cx, cy + 28);

    this.ctx.restore();
  }

  public destroy(): void {
    this.stop();
    window.removeEventListener("resize", this.handleResize);
  }
}
