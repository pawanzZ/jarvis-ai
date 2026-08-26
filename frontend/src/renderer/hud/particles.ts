/**
 * Jarvis AI - High Performance 60FPS Dynamic Particle Engine
 * Renders Iron Man HUD chevron markers, floating nodes, and state-responsive
 * kinetic vectors (ambient drift, centripetal convergence, orbital vortex, acoustic radiation).
 */

import { JarvisState } from "../core/types";

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  size: number;
  alpha: number;
  maxAlpha: number;
  life: number;
  maxLife: number;
  angle: number;
  angularSpeed: number;
  isChevron: boolean;
}

export class ParticleSystem {
  private canvas: HTMLCanvasElement;
  private ctx: CanvasRenderingContext2D;
  private particles: Particle[] = [];
  private maxParticles = 35;
  private state: JarvisState = "idle";
  private animFrameId: number | null = null;

  constructor(canvas: HTMLCanvasElement) {
    this.canvas = canvas;
    const context = canvas.getContext("2d");
    if (!context) {
      throw new Error("Could not get 2D context for Particle canvas");
    }
    this.ctx = context;

    this.resize();
    window.addEventListener("resize", this.handleResize);
    this.startLoop();
  }

  private handleResize = (): void => {
    this.resize();
  };

  public resize(): void {
    const dpr = window.devicePixelRatio || 1;
    const width = window.innerWidth;
    const height = window.innerHeight;
    this.canvas.width = width * dpr;
    this.canvas.height = height * dpr;
    this.ctx.scale(dpr, dpr);
  }

  public setState(state: JarvisState): void {
    this.state = state;
    const densityMap: Record<JarvisState, number> = {
      idle: 35,
      listening: 70,
      thinking: 95,
      speaking: 120,
      error: 60,
    };
    this.maxParticles = densityMap[state] || 35;
  }

  private spawnParticle(): Particle {
    const width = window.innerWidth;
    const height = window.innerHeight;
    const centerX = width / 2;
    const centerY = height / 2;

    let x = Math.random() * width;
    let y = Math.random() * height;
    let vx = (Math.random() - 0.5) * 0.6;
    let vy = (Math.random() - 0.5) * 0.6;

    if (this.state === "speaking") {
      // Spawn near center and blast outward
      x = centerX + (Math.random() - 0.5) * 60;
      y = centerY + (Math.random() - 0.5) * 60;
      const angle = Math.random() * Math.PI * 2;
      const speed = 1.2 + Math.random() * 2.5;
      vx = Math.cos(angle) * speed;
      vy = Math.sin(angle) * speed;
    } else if (this.state === "listening") {
      // Spawn on edges and drift towards center
      const edge = Math.floor(Math.random() * 4);
      if (edge === 0) { x = Math.random() * width; y = 0; }
      else if (edge === 1) { x = width; y = Math.random() * height; }
      else if (edge === 2) { x = Math.random() * width; y = height; }
      else { x = 0; y = Math.random() * height; }

      const angle = Math.atan2(centerY - y, centerX - x);
      const speed = 0.8 + Math.random() * 1.2;
      vx = Math.cos(angle) * speed;
      vy = Math.sin(angle) * speed;
    }

    const maxLife = 150 + Math.random() * 200;
    const maxAlpha = 0.2 + Math.random() * 0.6;

    return {
      x,
      y,
      vx,
      vy,
      size: Math.random() * 2.5 + 1.2,
      alpha: 0.05,
      maxAlpha,
      life: maxLife,
      maxLife,
      angle: Math.random() * Math.PI * 2,
      angularSpeed: (Math.random() - 0.5) * 0.04,
      isChevron: Math.random() > 0.45,
    };
  }

  private updateParticles(): void {
    const width = window.innerWidth;
    const height = window.innerHeight;
    const centerX = width / 2;
    const centerY = height / 2;

    // Maintain target particle density
    while (this.particles.length < this.maxParticles) {
      this.particles.push(this.spawnParticle());
    }

    this.particles = this.particles.filter((p) => {
      p.life--;

      if (this.state === "thinking") {
        // Swirl in orbital vortex
        const dx = p.x - centerX;
        const dy = p.y - centerY;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const orbitSpeed = 2.0 / Math.max(0.4, dist / 150);
        p.x += -dy * 0.015 * orbitSpeed + (Math.random() - 0.5) * 0.5;
        p.y += dx * 0.015 * orbitSpeed + (Math.random() - 0.5) * 0.5;
      } else if (this.state === "error") {
        // Jitter glitch
        p.x += p.vx * 1.5 + (Math.random() - 0.5) * 3;
        p.y += p.vy * 1.5 + (Math.random() - 0.5) * 3;
      } else {
        p.x += p.vx;
        p.y += p.vy;
      }

      p.angle += p.angularSpeed;

      // Smooth fade-in and fade-out envelope
      const lifeRatio = p.life / p.maxLife;
      if (lifeRatio > 0.8) {
        p.alpha = ((1 - lifeRatio) / 0.2) * p.maxAlpha;
      } else if (lifeRatio < 0.3) {
        p.alpha = (lifeRatio / 0.3) * p.maxAlpha;
      } else {
        p.alpha = p.maxAlpha;
      }

      // Check bounds
      const inBounds = p.x >= -50 && p.x <= width + 50 && p.y >= -50 && p.y <= height + 50;
      return p.life > 0 && inBounds;
    });
  }

  private draw(): void {
    const width = window.innerWidth;
    const height = window.innerHeight;
    this.ctx.clearRect(0, 0, width, height);

    // Pick color scheme based on state
    let baseColor = "0, 212, 255"; // Cyan
    if (this.state === "thinking") baseColor = "255, 170, 0"; // Amber
    else if (this.state === "speaking") baseColor = "200, 235, 255"; // White/Ice Blue
    else if (this.state === "error") baseColor = "255, 51, 68"; // Red
    else if (this.state === "idle") baseColor = "0, 136, 255"; // Blue

    this.particles.forEach((p) => {
      this.ctx.save();
      this.ctx.translate(p.x, p.y);
      this.ctx.rotate(p.angle);

      if (p.isChevron) {
        // Iron Man HUD Chevron marker
        this.ctx.beginPath();
        const s = p.size;
        this.ctx.moveTo(-s * 2, -s);
        this.ctx.lineTo(0, s);
        this.ctx.lineTo(s * 2, -s);
        this.ctx.strokeStyle = `rgba(${baseColor}, ${p.alpha.toFixed(3)})`;
        this.ctx.lineWidth = 1.2;
        this.ctx.stroke();
      } else {
        // Diamond / square node
        this.ctx.beginPath();
        const s = p.size;
        this.ctx.rect(-s, -s, s * 2, s * 2);
        this.ctx.fillStyle = `rgba(${baseColor}, ${p.alpha.toFixed(3)})`;
        this.ctx.fill();
      }

      this.ctx.restore();
    });
  }

  private startLoop = (): void => {
    this.updateParticles();
    this.draw();
    this.animFrameId = requestAnimationFrame(this.startLoop);
  };

  public destroy(): void {
    if (this.animFrameId !== null) {
      cancelAnimationFrame(this.animFrameId);
      this.animFrameId = null;
    }
    window.removeEventListener("resize", this.handleResize);
  }
}
