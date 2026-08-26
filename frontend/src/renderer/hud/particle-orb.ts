/**
 * Jarvis AI - Perplexity-style 3D Particle Orb Visualizer
 * Renders a 3D revolving point-cloud spherical visualizer with
 * Fibonacci distribution, 3D perspective projection, harmonic surface turbulence,
 * and audio-reactive acoustic ripple deformation.
 */

import { JarvisState } from "../core/types";

interface Point3D {
  // Unit sphere base coordinates
  nx: number;
  ny: number;
  nz: number;
  // Dynamic current coordinates
  x: number;
  y: number;
  z: number;
  // Screen projection
  px: number;
  py: number;
  scale: number;
  alpha: number;
  size: number;
  // Harmonic vibration attributes
  phase: number;
  freq: number;
  baseSize: number;
}

export class ParticleOrbVisualizer {
  private canvas: HTMLCanvasElement;
  private ctx: CanvasRenderingContext2D;
  private particles: Point3D[] = [];
  private numParticles: number = 1350;
  private baseRadius: number = 135;
  private state: JarvisState = "idle";
  private currentAudioLevel: number = 0;
  private targetAudioLevel: number = 0;
  private animFrameId: number | null = null;
  private isRunning: boolean = false;

  // 3D Rotation Angles
  private rotX: number = 0.2;
  private rotY: number = 0.0;
  private rotZ: number = 0.0;
  private time: number = 0;

  // Color configurations per state
  private stateColors: Record<JarvisState, { r: number; g: number; b: number; glow: string }> = {
    idle: { r: 210, g: 240, b: 255, glow: "rgba(0, 212, 255, 0.3)" },
    listening: { r: 0, g: 240, b: 255, glow: "rgba(0, 240, 255, 0.6)" },
    thinking: { r: 0, g: 180, b: 255, glow: "rgba(0, 180, 255, 0.7)" },
    speaking: { r: 0, g: 255, b: 220, glow: "rgba(0, 255, 200, 0.65)" },
    error: { r: 255, g: 60, b: 90, glow: "rgba(255, 50, 80, 0.6)" },
  };

  constructor(canvas: HTMLCanvasElement) {
    this.canvas = canvas;
    const context = this.canvas.getContext("2d");
    if (!context) throw new Error("Unable to obtain 2D rendering context for ParticleOrb");
    this.ctx = context;

    this.initParticles();
    this.handleResize();
    window.addEventListener("resize", () => this.handleResize());
  }

  /**
   * Generates a 3D point cloud using the Fibonacci / Golden Spiral sphere distribution.
   */
  private initParticles(): void {
    this.particles = [];
    const phi = Math.PI * (3.0 - Math.sqrt(5.0)); // Golden angle ~2.39996 rad

    for (let i = 0; i < this.numParticles; i++) {
      // y goes from 1 to -1 uniformly
      const ny = 1.0 - (i / (this.numParticles - 1)) * 2.0;
      const radiusAtY = Math.sqrt(Math.max(0.0, 1.0 - ny * ny));
      const theta = phi * i;

      const nx = Math.cos(theta) * radiusAtY;
      const nz = Math.sin(theta) * radiusAtY;

      this.particles.push({
        nx,
        ny,
        nz,
        x: nx * this.baseRadius,
        y: ny * this.baseRadius,
        z: nz * this.baseRadius,
        px: 0,
        py: 0,
        scale: 1.0,
        alpha: 1.0,
        size: 1.5,
        phase: Math.random() * Math.PI * 2.0,
        freq: 0.8 + Math.random() * 0.8,
        baseSize: 1.1 + Math.random() * 1.3,
      });
    }
  }

  public handleResize(): void {
    const dpr = window.devicePixelRatio || 1;
    const rect = this.canvas.getBoundingClientRect();
    const width = rect.width || 380;
    const height = rect.height || 380;

    this.canvas.width = width * dpr;
    this.canvas.height = height * dpr;
    this.ctx.resetTransform?.();
    this.ctx.scale(dpr, dpr);

    // Responsive radius scaling
    this.baseRadius = Math.min(width, height) * 0.36;
  }

  public setState(state: JarvisState): void {
    this.state = state;
  }

  public setAudioLevel(level: number): void {
    this.targetAudioLevel = Math.max(0.0, Math.min(1.0, level));
  }

  public start(): void {
    if (this.isRunning) return;
    this.isRunning = true;
    this.handleResize();
    this.render();
  }

  public stop(): void {
    this.isRunning = false;
    if (this.animFrameId !== null) {
      cancelAnimationFrame(this.animFrameId);
      this.animFrameId = null;
    }
    // Clear canvas when stopped
    const rect = this.canvas.getBoundingClientRect();
    this.ctx.clearRect(0, 0, rect.width || 380, rect.height || 380);
  }

  private render = (): void => {
    if (!this.isRunning) return;

    // Smooth audio level interpolation
    this.currentAudioLevel += (this.targetAudioLevel - this.currentAudioLevel) * 0.25;

    // Dynamic rotation speeds & deformation parameters by state
    let rotSpeedY = 0.008;
    let rotSpeedX = 0.002;
    let turbulenceAmp = 0.07;
    let pulseSpeed = 1.8;

    switch (this.state) {
      case "idle":
        rotSpeedY = 0.006;
        rotSpeedX = 0.0015;
        turbulenceAmp = 0.05 + this.currentAudioLevel * 0.15;
        pulseSpeed = 1.4;
        break;
      case "listening":
        rotSpeedY = 0.014;
        rotSpeedX = 0.004;
        turbulenceAmp = 0.12 + this.currentAudioLevel * 0.45;
        pulseSpeed = 2.8;
        break;
      case "thinking":
        rotSpeedY = 0.038; // Rapid energetic vortex
        rotSpeedX = 0.012;
        turbulenceAmp = 0.18;
        pulseSpeed = 5.0;
        break;
      case "speaking":
        rotSpeedY = 0.016;
        rotSpeedX = 0.003;
        turbulenceAmp = 0.14 + this.currentAudioLevel * 0.50;
        pulseSpeed = 3.5;
        break;
      case "error":
        rotSpeedY = 0.025;
        rotSpeedX = 0.015;
        turbulenceAmp = 0.25;
        pulseSpeed = 6.0;
        break;
    }

    this.time += 0.016;
    this.rotY += rotSpeedY;
    this.rotX += Math.sin(this.time * 0.5) * rotSpeedX;
    this.rotZ += 0.001;

    const rect = this.canvas.getBoundingClientRect();
    const width = rect.width || 380;
    const height = rect.height || 380;
    const cx = width / 2;
    const cy = height / 2;

    this.ctx.clearRect(0, 0, width, height);

    // Precalculate rotation matrix constants
    const cosY = Math.cos(this.rotY);
    const sinY = Math.sin(this.rotY);
    const cosX = Math.cos(this.rotX);
    const sinX = Math.sin(this.rotX);

    // Dynamic breathing radius
    const breathing = 1.0 + Math.sin(this.time * pulseSpeed) * 0.03 + this.currentAudioLevel * 0.18;
    const currentRadius = this.baseRadius * breathing;

    const cameraDist = 480;
    const color = this.stateColors[this.state] || this.stateColors.idle;

    // Ambient center core glow
    const coreGlowRadius = currentRadius * (0.45 + this.currentAudioLevel * 0.3);
    const coreGradient = this.ctx.createRadialGradient(cx, cy, 0, cx, cy, coreGlowRadius);
    coreGradient.addColorStop(0, `rgba(${color.r}, ${color.g}, ${color.b}, ${0.18 + this.currentAudioLevel * 0.2})`);
    coreGradient.addColorStop(0.5, `rgba(${color.r}, ${color.g}, ${color.b}, 0.05)`);
    coreGradient.addColorStop(1, "rgba(0, 0, 0, 0)");

    this.ctx.fillStyle = coreGradient;
    this.ctx.beginPath();
    this.ctx.arc(cx, cy, coreGlowRadius, 0, Math.PI * 2);
    this.ctx.fill();

    // 1. Transform & Project All Particles
    for (let i = 0; i < this.numParticles; i++) {
      const p = this.particles[i];

      // Multi-harmonic acoustic surface deformation
      const wave1 = Math.sin(this.time * 2.5 + p.nx * 4.0 + p.phase);
      const wave2 = Math.cos(this.time * 3.2 + p.ny * 5.0 + p.nz * 3.0);
      const acousticRipple = Math.sin(p.nz * 7.0 - this.time * 8.0) * this.currentAudioLevel * 0.35;

      const displacement = 1.0 + (wave1 * 0.6 + wave2 * 0.4) * turbulenceAmp + acousticRipple;
      const r = currentRadius * displacement;

      // 3D coordinates before rotation
      const x0 = p.nx * r;
      const y0 = p.ny * r;
      const z0 = p.nz * r;

      // Rotation around Y axis
      const x1 = x0 * cosY + z0 * sinY;
      const y1 = y0;
      const z1 = -x0 * sinY + z0 * cosY;

      // Rotation around X axis
      const x2 = x1;
      const y2 = y1 * cosX - z1 * sinX;
      const z2 = y1 * sinX + z1 * cosX;

      p.x = x2;
      p.y = y2;
      p.z = z2;

      // Perspective Projection
      const depth = cameraDist - z2;
      const scale = cameraDist / Math.max(10, depth);
      p.scale = scale;
      p.px = cx + x2 * scale;
      p.py = cy + y2 * scale;

      // Depth-attenuated alpha & point size
      // z2 goes from -currentRadius (far) to +currentRadius (near)
      const normZ = (z2 + currentRadius) / (currentRadius * 2.0); // 0 (far) to 1 (near)
      const clampedZ = Math.max(0.0, Math.min(1.0, normZ));

      p.alpha = 0.15 + clampedZ * 0.82;
      p.size = p.baseSize * scale * (0.8 + clampedZ * 0.7);
    }

    // 2. Sort by depth (far particles first, near particles in front)
    this.particles.sort((a, b) => a.z - b.z);

    // 3. Render Particles with 3D Depth
    for (let i = 0; i < this.numParticles; i++) {
      const p = this.particles[i];

      // Cull particles offscreen
      if (p.px < -20 || p.px > width + 20 || p.py < -20 || p.py > height + 20) {
        continue;
      }

      this.ctx.beginPath();
      this.ctx.arc(p.px, p.py, Math.max(0.6, p.size), 0, Math.PI * 2);

      // Near particles get brighter starlight glow
      if (p.z > currentRadius * 0.3) {
        this.ctx.fillStyle = `rgba(255, 255, 255, ${p.alpha})`;
        this.ctx.shadowBlur = 4;
        this.ctx.shadowColor = color.glow;
      } else {
        this.ctx.fillStyle = `rgba(${color.r}, ${color.g}, ${color.b}, ${p.alpha})`;
        this.ctx.shadowBlur = 0;
      }

      this.ctx.fill();
    }

    // Reset shadow state
    this.ctx.shadowBlur = 0;

    this.animFrameId = requestAnimationFrame(this.render);
  };
}
