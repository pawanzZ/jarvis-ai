/**
 * Jarvis AI - Iron Man Holographic Helmet / Mask HUD
 * Renders an authentic Mark 85 holographic helmet wireframe.
 * Features:
 * - Geometric facial contours, brow ridges, cheek chamfers, and jaw vents
 * - Glowing eye slit optics that pulse dynamically with Jarvis state and vocal audio
 * - Cranial alignment axes, holographic crosshairs, and armor diagnostics
 */

import { JarvisState } from "../core/types";

export class IronManMaskHUD {
  private canvas: HTMLCanvasElement;
  private ctx: CanvasRenderingContext2D;
  private animFrameId: number | null = null;
  private isRunning = false;
  private state: JarvisState = "idle";
  private time = 0;
  private audioLevel = 0;

  constructor(canvas: HTMLCanvasElement) {
    this.canvas = canvas;
    const context = canvas.getContext("2d");
    if (!context) throw new Error("Could not get 2D context for IronManMaskHUD");
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
    const width = rect.width || 220;
    const height = rect.height || 160;

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

    this.time += 0.035;
    this.render();
    this.animFrameId = requestAnimationFrame(this.startRenderLoop);
  };

  private render(): void {
    const rect = this.canvas.getBoundingClientRect();
    const width = rect.width || 220;
    const height = rect.height || 160;
    const cx = width * 0.5;
    const cy = height * 0.52;

    this.ctx.clearRect(0, 0, width, height);
    this.ctx.save();

    // 1. Subtle Cranial Alignment Axes & Tech Crosshairs
    this.ctx.lineWidth = 0.8;
    this.ctx.strokeStyle = "rgba(0, 212, 255, 0.16)";

    // Vertical symmetry axis
    this.ctx.beginPath();
    this.ctx.setLineDash([4, 4]);
    this.ctx.moveTo(cx, cy - 65);
    this.ctx.lineTo(cx, cy + 65);
    this.ctx.stroke();

    // Horizontal eye level axis
    this.ctx.beginPath();
    this.ctx.moveTo(cx - 75, cy - 8);
    this.ctx.lineTo(cx + 75, cy - 8);
    this.ctx.stroke();
    this.ctx.setLineDash([]);

    // 2. Holographic Helmet Wireframe Contours (Normalized scale ~ 1.0)
    const scale = 0.85;

    // Color logic based on state
    let baseColor = "rgba(0, 212, 255,";
    let eyeColor = "#00ffff";
    let eyeGlow = "rgba(0, 245, 212,";

    if (this.state === "listening") {
      baseColor = "rgba(255, 215, 0,";
      eyeColor = "#ffffff";
      eyeGlow = "rgba(255, 230, 100,";
    } else if (this.state === "thinking") {
      baseColor = "rgba(0, 230, 255,";
      eyeColor = "#00f0ff";
      eyeGlow = "rgba(0, 200, 255,";
    } else if (this.state === "speaking") {
      baseColor = "rgba(0, 245, 212,";
      eyeColor = "#ffffff";
      eyeGlow = "rgba(0, 255, 200,";
    } else if (this.state === "error") {
      baseColor = "rgba(255, 60, 80,";
      eyeColor = "#ff2244";
      eyeGlow = "rgba(255, 40, 60,";
    }

    // Outer Cranium / Helmet Shell Contour
    this.ctx.beginPath();
    this.ctx.lineWidth = 1.4;
    this.ctx.strokeStyle = `${baseColor} 0.65)`;
    // Top skull arc
    this.ctx.moveTo(cx - 38 * scale, cy - 45 * scale);
    this.ctx.quadraticCurveTo(cx, cy - 65 * scale, cx + 38 * scale, cy - 45 * scale);
    // Temples
    this.ctx.lineTo(cx + 48 * scale, cy - 20 * scale);
    this.ctx.lineTo(cx + 50 * scale, cy + 10 * scale);
    // Cheekbones
    this.ctx.lineTo(cx + 42 * scale, cy + 35 * scale);
    // Jawline
    this.ctx.lineTo(cx + 24 * scale, cy + 58 * scale);
    // Chin
    this.ctx.lineTo(cx - 24 * scale, cy + 58 * scale);
    // Left jawline
    this.ctx.lineTo(cx - 42 * scale, cy + 35 * scale);
    this.ctx.lineTo(cx - 50 * scale, cy + 10 * scale);
    this.ctx.lineTo(cx - 48 * scale, cy - 20 * scale);
    this.ctx.closePath();
    this.ctx.stroke();

    // Brow Ridge & Forehead Plate
    this.ctx.beginPath();
    this.ctx.lineWidth = 1.2;
    this.ctx.strokeStyle = `${baseColor} 0.75)`;
    this.ctx.moveTo(cx - 34 * scale, cy - 22 * scale);
    this.ctx.lineTo(cx - 10 * scale, cy - 14 * scale);
    this.ctx.lineTo(cx, cy - 20 * scale);
    this.ctx.lineTo(cx + 10 * scale, cy - 14 * scale);
    this.ctx.lineTo(cx + 34 * scale, cy - 22 * scale);
    this.ctx.stroke();

    // Faceplate Cheek Chamfers
    this.ctx.beginPath();
    this.ctx.lineWidth = 1.0;
    this.ctx.strokeStyle = `${baseColor} 0.5)`;
    // Right cheek
    this.ctx.moveTo(cx + 34 * scale, cy - 12 * scale);
    this.ctx.lineTo(cx + 32 * scale, cy + 18 * scale);
    this.ctx.lineTo(cx + 14 * scale, cy + 36 * scale);
    this.ctx.lineTo(cx + 14 * scale, cy + 48 * scale);
    // Left cheek
    this.ctx.moveTo(cx - 34 * scale, cy - 12 * scale);
    this.ctx.lineTo(cx - 32 * scale, cy + 18 * scale);
    this.ctx.lineTo(cx - 14 * scale, cy + 36 * scale);
    this.ctx.lineTo(cx - 14 * scale, cy + 48 * scale);
    this.ctx.stroke();

    // Mouth / Jaw Vent Slots
    this.ctx.beginPath();
    this.ctx.lineWidth = 1.2;
    this.ctx.strokeStyle = `${baseColor} 0.6)`;
    this.ctx.moveTo(cx - 10 * scale, cy + 44 * scale);
    this.ctx.lineTo(cx + 10 * scale, cy + 44 * scale);
    this.ctx.moveTo(cx - 8 * scale, cy + 50 * scale);
    this.ctx.lineTo(cx + 8 * scale, cy + 50 * scale);
    this.ctx.stroke();

    // 3. Glowing Eye Slit Optics (Tony Stark Iconic Angled Eyes)
    const eyePulse = Math.sin(this.time * 3.5) * 0.2 + 0.8 + this.audioLevel * 0.6;
    const eyeY = cy - 6 * scale;

    // Left Eye Slit
    this.ctx.save();
    this.ctx.beginPath();
    this.ctx.moveTo(cx - 32 * scale, eyeY - 2 * scale);
    this.ctx.lineTo(cx - 12 * scale, eyeY + 2 * scale);
    this.ctx.lineTo(cx - 15 * scale, eyeY + 6 * scale);
    this.ctx.lineTo(cx - 33 * scale, eyeY + 1 * scale);
    this.ctx.closePath();

    this.ctx.fillStyle = eyeColor;
    this.ctx.shadowBlur = 12 * eyePulse;
    this.ctx.shadowColor = `${eyeGlow} 1.0)`;
    this.ctx.fill();

    // Right Eye Slit
    this.ctx.beginPath();
    this.ctx.moveTo(cx + 32 * scale, eyeY - 2 * scale);
    this.ctx.lineTo(cx + 12 * scale, eyeY + 2 * scale);
    this.ctx.lineTo(cx + 15 * scale, eyeY + 6 * scale);
    this.ctx.lineTo(cx + 33 * scale, eyeY + 1 * scale);
    this.ctx.closePath();

    this.ctx.fillStyle = eyeColor;
    this.ctx.shadowBlur = 12 * eyePulse;
    this.ctx.shadowColor = `${eyeGlow} 1.0)`;
    this.ctx.fill();
    this.ctx.restore();

    // 4. Circular HUD Target Reticle around face
    this.ctx.beginPath();
    this.ctx.arc(cx, cy, 68 * scale, -Math.PI * 0.7, -Math.PI * 0.3);
    this.ctx.lineWidth = 1.0;
    this.ctx.strokeStyle = `${baseColor} 0.4)`;
    this.ctx.stroke();

    this.ctx.beginPath();
    this.ctx.arc(cx, cy, 68 * scale, Math.PI * 0.3, Math.PI * 0.7);
    this.ctx.stroke();

    // 5. Diagnostics Telemetry Labels
    this.ctx.font = "bold 8px 'Fira Code', 'Roboto Mono', monospace";
    this.ctx.textAlign = "left";
    this.ctx.fillStyle = `${baseColor} 0.85)`;
    this.ctx.fillText("MK-LXXXV", 10, height - 10);

    this.ctx.textAlign = "right";
    this.ctx.fillStyle = "rgba(0, 255, 200, 0.85)";
    this.ctx.fillText("INTEGRITY: 100%", width - 10, height - 10);

    this.ctx.restore();
  }

  public destroy(): void {
    this.stop();
    window.removeEventListener("resize", this.handleResize);
  }
}
