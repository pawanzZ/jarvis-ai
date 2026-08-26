/**
 * Jarvis AI - Real-Time Audio Waveform & Frequency Visualizer
 * High-performance 2D Canvas visualizer rendering dynamic mirrored frequency bars
 * driven by incoming audio_level telemetry and harmonic procedural oscillators.
 */

import { JarvisState } from "../core/types";

export class Waveform {
  private canvas: HTMLCanvasElement;
  private ctx: CanvasRenderingContext2D;
  private barCount = 64;
  private bars: number[];
  private targetBars: number[];
  private currentLevel = 0;
  private targetLevel = 0;
  private state: JarvisState = "idle";
  private animFrameId: number | null = null;
  private phase = 0;

  constructor(canvas: HTMLCanvasElement) {
    this.canvas = canvas;
    const context = canvas.getContext("2d");
    if (!context) {
      throw new Error("Could not get 2D rendering context for Waveform canvas");
    }
    this.ctx = context;
    this.bars = new Array(this.barCount).fill(0);
    this.targetBars = new Array(this.barCount).fill(0);

    this.resize();
    window.addEventListener("resize", this.handleResize);
    this.startRenderLoop();
  }

  private handleResize = (): void => {
    this.resize();
  };

  public resize(): void {
    const dpr = window.devicePixelRatio || 1;
    const rect = this.canvas.getBoundingClientRect();
    this.canvas.width = (rect.width || window.innerWidth) * dpr;
    this.canvas.height = (rect.height || 180) * dpr;
    this.ctx.scale(dpr, dpr);
  }

  public setState(state: JarvisState): void {
    this.state = state;
  }

  /**
   * Updates audio level [0.0 - 1.0].
   */
  public updateLevel(level: number): void {
    this.targetLevel = Math.max(0, Math.min(1, level));

    // Synthesize harmonic frequency distribution around audio level
    const center = this.barCount / 2;
    for (let i = 0; i < this.barCount; i++) {
      const distFromCenter = Math.abs(i - center) / center;
      const bellCurve = Math.exp(-distFromCenter * distFromCenter * 3.5);
      const randomJitter = 0.7 + Math.random() * 0.6;
      const waveMod = Math.sin(this.phase * 4 + i * 0.3) * 0.25;

      this.targetBars[i] = Math.max(
        0.02,
        Math.min(1.0, this.targetLevel * (bellCurve + waveMod) * randomJitter)
      );
    }
  }

  public clear(): void {
    this.targetLevel = 0;
    this.currentLevel = 0;
    this.targetBars.fill(0);
    this.bars.fill(0);
  }

  private startRenderLoop = (): void => {
    this.phase += 0.04;

    // Exponential smoothing for master audio level
    this.currentLevel += (this.targetLevel - this.currentLevel) * 0.25;

    // If in idle or thinking mode and no audio input, render gentle ambient harmonic ripples
    const isAmbient = this.currentLevel < 0.05 && (this.state === "listening" || this.state === "thinking" || this.state === "idle");

    for (let i = 0; i < this.barCount; i++) {
      if (isAmbient) {
        const ambientHeight = this.state === "listening"
          ? 0.08 * (Math.sin(this.phase * 2 + i * 0.2) * 0.5 + 0.5)
          : this.state === "thinking"
          ? 0.12 * (Math.sin(this.phase * 5 + i * 0.4) * 0.5 + 0.5)
          : 0.03 * (Math.sin(this.phase * 0.8 + i * 0.1) * 0.5 + 0.5);
        this.bars[i] += (ambientHeight - this.bars[i]) * 0.15;
      } else {
        // Smoothly interpolate towards target level with natural gravity decay
        this.bars[i] += (this.targetBars[i] - this.bars[i]) * 0.3;
        this.targetBars[i] *= 0.92; // Decay target
      }
    }

    this.draw();
    this.animFrameId = requestAnimationFrame(this.startRenderLoop);
  };

  private draw(): void {
    const rect = this.canvas.getBoundingClientRect();
    const width = rect.width || this.canvas.width;
    const height = rect.height || this.canvas.height;

    this.ctx.clearRect(0, 0, width, height);

    const totalBars = this.barCount;
    const spacing = 3;
    const barWidth = Math.max(2, (width - (totalBars - 1) * spacing) / totalBars);
    const centerY = height / 2;

    for (let i = 0; i < totalBars; i++) {
      const barHeight = Math.max(3, this.bars[i] * (height * 0.85));
      const x = i * (barWidth + spacing);
      const y = centerY - barHeight / 2;

      // Color scheme based on state
      const gradient = this.ctx.createLinearGradient(x, y, x, y + barHeight);

      if (this.state === "thinking") {
        gradient.addColorStop(0, "rgba(255, 170, 0, 0.2)");
        gradient.addColorStop(0.5, "rgba(255, 215, 0, 0.9)");
        gradient.addColorStop(1, "rgba(255, 170, 0, 0.2)");
      } else if (this.state === "error") {
        gradient.addColorStop(0, "rgba(255, 51, 68, 0.2)");
        gradient.addColorStop(0.5, "rgba(255, 80, 100, 0.9)");
        gradient.addColorStop(1, "rgba(255, 51, 68, 0.2)");
      } else if (this.state === "speaking") {
        gradient.addColorStop(0, "rgba(0, 180, 255, 0.3)");
        gradient.addColorStop(0.5, "rgba(255, 255, 255, 1)");
        gradient.addColorStop(1, "rgba(0, 180, 255, 0.3)");
      } else {
        // Idle / Listening
        gradient.addColorStop(0, "rgba(0, 136, 255, 0.2)");
        gradient.addColorStop(0.5, "rgba(0, 212, 255, 0.85)");
        gradient.addColorStop(1, "rgba(0, 136, 255, 0.2)");
      }

      this.ctx.fillStyle = gradient;
      this.ctx.fillRect(x, y, barWidth, barHeight);

      // Glowing cap on active bars
      if (this.bars[i] > 0.15) {
        this.ctx.fillStyle = this.state === "thinking" ? "#ffd700" : "#ffffff";
        this.ctx.fillRect(x, y, barWidth, 2);
        this.ctx.fillRect(x, y + barHeight - 2, barWidth, 2);
      }
    }
  }

  public destroy(): void {
    if (this.animFrameId !== null) {
      cancelAnimationFrame(this.animFrameId);
      this.animFrameId = null;
    }
    window.removeEventListener("resize", this.handleResize);
  }
}
