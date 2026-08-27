/**
 * Jarvis AI - Real-Time Optical / Video Capture HUD
 * Captures live webcam video and renders sci-fi targeting graphics.
 * Features:
 * - HTML5 getUserMedia video stream with fallback synthetic cyber scanner
 * - Blinking [● REC] indicator with live timestamp
 * - Face tracking bounding box with corner tick brackets and lock readouts
 * - Optical telemetry: FPS, ISO, Aperture, and state-reactive focus reticles
 */

import { JarvisState } from "../core/types";

export class CameraHUD {
  private videoEl: HTMLVideoElement;
  private canvas: HTMLCanvasElement;
  private ctx: CanvasRenderingContext2D;
  private animFrameId: number | null = null;
  private isRunning = false;
  private state: JarvisState = "idle";
  private mediaStream: MediaStream | null = null;
  private isSynthetic = false;
  private isVisionMode = false;
  private time = 0;
  private audioLevel = 0;

  // Face tracking box dynamics
  private boxX = 0;
  private boxY = 0;
  private boxW = 80;
  private boxH = 95;

  constructor(videoEl: HTMLVideoElement, canvas: HTMLCanvasElement) {
    this.videoEl = videoEl;
    this.canvas = canvas;
    const context = canvas.getContext("2d");
    if (!context) throw new Error("Could not get 2D context for CameraHUD");
    this.ctx = context;

    this.resize();
    window.addEventListener("resize", this.handleResize);
    this.initCamera();
    this.start();
  }

  public setVisionMode(enabled: boolean): void {
    this.isVisionMode = enabled;
    this.boxW = enabled ? 180 : 80;
    this.boxH = enabled ? 220 : 95;
    // Trigger progressive resize during and after CSS transition
    this.resize();
    setTimeout(() => this.resize(), 100);
    setTimeout(() => this.resize(), 400);
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

  private async initCamera(): Promise<void> {
    try {
      if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { width: { ideal: 320 }, height: { ideal: 240 } },
          audio: false,
        });
        this.mediaStream = stream;
        this.videoEl.srcObject = stream;
        await this.videoEl.play();
        this.isSynthetic = false;
        console.log("[CameraHUD] Real-time optical video stream active.");
        return;
      }
    } catch {
      // Fallback
    }

    // Fallback: render synthetic cyber thermal scanner
    this.isSynthetic = true;
    console.log("[CameraHUD] Using synthetic cyber thermal scanner fallback.");
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

    this.time += 0.04;
    this.render();
    this.animFrameId = requestAnimationFrame(this.startRenderLoop);
  };

  private render(): void {
    const rect = this.canvas.getBoundingClientRect();
    const width = rect.width || 220;
    const height = rect.height || 160;
    const cx = width * 0.5;
    const cy = height * 0.5;

    this.ctx.clearRect(0, 0, width, height);

    // 1. Synthetic Fallback Background if real camera is not active
    if (this.isSynthetic) {
      // Draw dark grid with faint thermal face wireframe
      this.ctx.fillStyle = "rgba(4, 14, 28, 0.85)";
      this.ctx.fillRect(0, 0, width, height);

      // Cyber Grid
      this.ctx.lineWidth = 0.5;
      this.ctx.strokeStyle = "rgba(0, 180, 255, 0.12)";
      for (let x = 0; x < width; x += 20) {
        this.ctx.beginPath();
        this.ctx.moveTo(x, 0);
        this.ctx.lineTo(x, height);
        this.ctx.stroke();
      }
      for (let y = 0; y < height; y += 20) {
        this.ctx.beginPath();
        this.ctx.moveTo(0, y);
        this.ctx.lineTo(width, y);
        this.ctx.stroke();
      }

      // Simulated Thermal Face Silhouette
      const facePulse = Math.sin(this.time * 2.0) * 2;
      this.ctx.save();
      this.ctx.beginPath();
      this.ctx.ellipse(cx, cy - 4, 32 + facePulse, 42 + facePulse, 0, 0, Math.PI * 2);
      this.ctx.strokeStyle = "rgba(0, 245, 212, 0.35)";
      this.ctx.lineWidth = 1.2;
      this.ctx.stroke();

      // Eye dots
      this.ctx.beginPath();
      this.ctx.arc(cx - 12, cy - 12, 2.5, 0, Math.PI * 2);
      this.ctx.arc(cx + 12, cy - 12, 2.5, 0, Math.PI * 2);
      this.ctx.fillStyle = "rgba(0, 255, 200, 0.6)";
      this.ctx.fill();
      this.ctx.restore();
    }

    // 2. HUD Targeting Bounding Box with Inertial Drift
    const targetX = cx - 40 + Math.sin(this.time * 1.2) * 4;
    const targetY = cy - 45 + Math.cos(this.time * 0.9) * 3;
    this.boxX += (targetX - this.boxX) * 0.1;
    this.boxY += (targetY - this.boxY) * 0.1;

    let reticleColor = "rgba(0, 212, 255,";
    if (this.state === "listening") reticleColor = "rgba(255, 215, 0,";
    else if (this.state === "error") reticleColor = "rgba(255, 60, 60,";

    // Corner brackets of target box
    const bw = this.boxW;
    const bh = this.boxH;
    const bx = this.boxX;
    const by = this.boxY;
    const bl = 10; // Bracket length

    this.ctx.save();
    this.ctx.lineWidth = 1.5;
    this.ctx.strokeStyle = `${reticleColor} 0.9)`;
    this.ctx.shadowBlur = 4;
    this.ctx.shadowColor = `${reticleColor} 0.8)`;

    // Top-Left
    this.ctx.beginPath();
    this.ctx.moveTo(bx, by + bl);
    this.ctx.lineTo(bx, by);
    this.ctx.lineTo(bx + bl, by);
    this.ctx.stroke();

    // Top-Right
    this.ctx.beginPath();
    this.ctx.moveTo(bx + bw - bl, by);
    this.ctx.lineTo(bx + bw, by);
    this.ctx.lineTo(bx + bw, by + bl);
    this.ctx.stroke();

    // Bottom-Left
    this.ctx.beginPath();
    this.ctx.moveTo(bx, by + bh - bl);
    this.ctx.lineTo(bx, by + bh);
    this.ctx.lineTo(bx + bl, by + bh);
    this.ctx.stroke();

    // Bottom-Right
    this.ctx.beginPath();
    this.ctx.moveTo(bx + bw - bl, by + bh);
    this.ctx.lineTo(bx + bw, by + bh);
    this.ctx.lineTo(bx + bw, by + bh - bl);
    this.ctx.stroke();

    // Center targeting crosshair
    const tcx = bx + bw * 0.5;
    const tcy = by + bh * 0.5;
    this.ctx.lineWidth = 0.8;
    this.ctx.beginPath();
    this.ctx.moveTo(tcx - 6, tcy);
    this.ctx.lineTo(tcx + 6, tcy);
    this.ctx.moveTo(tcx, tcy - 6);
    this.ctx.lineTo(tcx, tcy + 6);
    this.ctx.stroke();

    // Target label above box
    this.ctx.font = "bold 7px 'Fira Code', 'Roboto Mono', monospace";
    this.ctx.fillStyle = `${reticleColor} 0.95)`;
    this.ctx.fillText("TARGET: USER // 98.4%", bx, by - 4);
    this.ctx.restore();

    // 3. Blinking [● REC] Indicator
    const recBlink = Math.sin(this.time * 4) > 0;
    this.ctx.save();
    if (recBlink) {
      this.ctx.beginPath();
      this.ctx.arc(14, 14, 3, 0, Math.PI * 2);
      this.ctx.fillStyle = "#ff3344";
      this.ctx.shadowBlur = 6;
      this.ctx.shadowColor = "#ff2233";
      this.ctx.fill();
    }
    this.ctx.font = "bold 8px 'Fira Code', 'Roboto Mono', monospace";
    this.ctx.fillStyle = recBlink ? "#ffffff" : "rgba(255, 255, 255, 0.4)";
    this.ctx.fillText("LIVE REC", 22, 16);

    // 4. Optical Sensor Specs (Aperture, ISO, FPS)
    this.ctx.font = "7px 'Fira Code', 'Roboto Mono', monospace";
    this.ctx.textAlign = "right";
    this.ctx.fillStyle = "rgba(0, 212, 255, 0.85)";
    this.ctx.fillText("OPTICAL-01 // 30 FPS", width - 10, 16);
    this.ctx.fillText("F/1.8  ISO 400", width - 10, height - 10);
    this.ctx.restore();

    // 5. Vision Mode Expanded HUD Overlays
    if (this.isVisionMode) {
      this.ctx.save();

      // Draw Facial Mesh Triangulation Wireframe Points
      const pts = [
        [0.2, 0.25], [0.5, 0.18], [0.8, 0.25], // Brow
        [0.32, 0.38], [0.68, 0.38],            // Eyes
        [0.5, 0.52], [0.44, 0.62], [0.56, 0.62], // Nose
        [0.36, 0.76], [0.5, 0.74], [0.64, 0.76], // Upper lip
        [0.5, 0.84],                            // Chin
        [0.15, 0.5], [0.85, 0.5]                // Cheeks
      ];
      this.ctx.fillStyle = "rgba(0, 245, 212, 0.85)";
      this.ctx.strokeStyle = "rgba(0, 212, 255, 0.3)";
      this.ctx.lineWidth = 0.8;

      pts.forEach(([px, py]) => {
        const lx = bx + bw * px;
        const ly = by + bh * py;
        this.ctx.beginPath();
        this.ctx.arc(lx, ly, 2.2, 0, Math.PI * 2);
        this.ctx.fill();
      });

      // Connect jawline & nose bridge
      this.ctx.beginPath();
      this.ctx.moveTo(bx + bw * 0.15, by + bh * 0.5);
      this.ctx.lineTo(bx + bw * 0.5, by + bh * 0.84);
      this.ctx.lineTo(bx + bw * 0.85, by + bh * 0.5);
      this.ctx.stroke();

      // Top Center Banner
      this.ctx.font = "bold 9px 'Fira Code', 'Roboto Mono', monospace";
      this.ctx.textAlign = "center";
      this.ctx.fillStyle = "#00f5d4";
      this.ctx.shadowBlur = 8;
      this.ctx.shadowColor = "#00f5d4";
      this.ctx.fillText("● VISION MODE // CONSUMING VISUAL INPUT", width * 0.5, 18);
      this.ctx.shadowBlur = 0;

      // Head Pose Orientation & Gaze Vectors
      this.ctx.textAlign = "left";
      this.ctx.font = "bold 8px 'Fira Code', 'Roboto Mono', monospace";
      this.ctx.fillStyle = "rgba(0, 212, 255, 0.9)";
      this.ctx.fillText("HEAD POSE: P: -1.2°  Y: 0.8°  R: 0.0°", 14, height - 24);
      this.ctx.fillText("GAZE VECTOR: [0.50, 0.48] // RETINAL LOCK", 14, height - 12);

      this.ctx.textAlign = "right";
      this.ctx.fillStyle = "rgba(255, 215, 0, 0.9)";
      this.ctx.fillText("BIOMETRICS: OPTIMAL // 99.8%", width - 14, height - 24);
      this.ctx.fillText("FOV: 84° // NEURAL PARSING: 60 FPS", width - 14, height - 12);
      this.ctx.restore();
    }
  }

  public destroy(): void {
    this.stop();
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach((track) => track.stop());
      this.mediaStream = null;
    }
    window.removeEventListener("resize", this.handleResize);
  }
}
