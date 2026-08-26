/**
 * Jarvis AI - Fluid Neon Ribbon Particle Mesh Waveform
 * High-performance 2D Canvas visualizer rendering multi-layered, fluid,
 * interwoven sinusoidal ribbons, glowing laser filaments, digital stardust meshes,
 * and floating crest energy sparks driven by real-time audio telemetry.
 */

import { JarvisState } from "../core/types";

interface WaveRibbon {
  freq1: number;
  freq2: number;
  speed1: number;
  speed2: number;
  ampMultiplier: number;
  phaseOffset: number;
  lineWidth: number;
  color: string;
  glowColor: string;
  glowBlur: number;
  isMesh?: boolean;
}

interface WaveSpark {
  xNorm: number; // 0.0 to 1.0
  speed: number;
  ribbonIndex: number;
  size: number;
  twinklePhase: number;
  twinkleSpeed: number;
  offsetY: number;
  color: string;
}

export class Waveform {
  private canvas: HTMLCanvasElement;
  private ctx: CanvasRenderingContext2D;
  private state: JarvisState = "idle";
  private currentLevel = 0;
  private targetLevel = 0;
  private animFrameId: number | null = null;
  private time = 0;
  private baseHeight = 35;
  private sparks: WaveSpark[] = [];
  private numSparks = 38;

  // Wave ribbons configuration
  private ribbons: WaveRibbon[] = [];

  constructor(canvas: HTMLCanvasElement) {
    this.canvas = canvas;
    const context = canvas.getContext("2d");
    if (!context) {
      throw new Error("Could not get 2D rendering context for Waveform canvas");
    }
    this.ctx = context;

    this.initRibbons();
    this.initSparks();
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
    const width = rect.width || window.innerWidth;
    const height = rect.height || 380;

    this.canvas.width = width * dpr;
    this.canvas.height = height * dpr;
    this.ctx.resetTransform?.();
    this.ctx.scale(dpr, dpr);
  }

  private initRibbons(): void {
    // 5 continuous harmonic ribbons + 2 stardust dot mesh strands
    this.ribbons = [
      // Ribbon 0: Core White/Cyan Neon Laser Filament
      {
        freq1: 0.0055,
        freq2: 0.011,
        speed1: 0.035,
        speed2: -0.022,
        ampMultiplier: 1.0,
        phaseOffset: 0.0,
        lineWidth: 2.2,
        color: "rgba(255, 255, 255, 0.95)",
        glowColor: "rgba(0, 240, 255, 0.9)",
        glowBlur: 14,
      },
      // Ribbon 1: Upper Primary Electric Cyan Wave
      {
        freq1: 0.0048,
        freq2: 0.0095,
        speed1: 0.028,
        speed2: 0.042,
        ampMultiplier: 0.88,
        phaseOffset: 1.2,
        lineWidth: 2.0,
        color: "rgba(0, 220, 255, 0.85)",
        glowColor: "rgba(0, 180, 255, 0.7)",
        glowBlur: 10,
      },
      // Ribbon 2: Lower Deep Azure Harmonic
      {
        freq1: 0.0062,
        freq2: 0.0125,
        speed1: -0.032,
        speed2: 0.025,
        ampMultiplier: 0.76,
        phaseOffset: 2.8,
        lineWidth: 1.8,
        color: "rgba(0, 130, 255, 0.75)",
        glowColor: "rgba(0, 100, 255, 0.6)",
        glowBlur: 8,
      },
      // Ribbon 3: Secondary Royal Blue Atmospheric Strand
      {
        freq1: 0.0038,
        freq2: 0.0075,
        speed1: 0.019,
        speed2: -0.031,
        ampMultiplier: 0.62,
        phaseOffset: 4.1,
        lineWidth: 1.5,
        color: "rgba(40, 110, 255, 0.6)",
        glowColor: "rgba(30, 80, 255, 0.5)",
        glowBlur: 6,
      },
      // Ribbon 4: Ambient High-Frequency Shroud
      {
        freq1: 0.0085,
        freq2: 0.016,
        speed1: -0.045,
        speed2: 0.038,
        ampMultiplier: 0.48,
        phaseOffset: 5.4,
        lineWidth: 1.2,
        color: "rgba(0, 200, 255, 0.45)",
        glowColor: "rgba(0, 200, 255, 0.4)",
        glowBlur: 5,
      },
      // Ribbon 5: Stardust Particle Dot Mesh 1
      {
        freq1: 0.0052,
        freq2: 0.0105,
        speed1: 0.026,
        speed2: -0.018,
        ampMultiplier: 0.92,
        phaseOffset: 0.7,
        lineWidth: 1.0,
        color: "rgba(0, 235, 255, 0.75)",
        glowColor: "rgba(0, 210, 255, 0.6)",
        glowBlur: 4,
        isMesh: true,
      },
      // Ribbon 6: Stardust Particle Dot Mesh 2
      {
        freq1: 0.0068,
        freq2: 0.0135,
        speed1: -0.034,
        speed2: 0.029,
        ampMultiplier: 0.72,
        phaseOffset: 3.4,
        lineWidth: 1.0,
        color: "rgba(100, 200, 255, 0.65)",
        glowColor: "rgba(70, 160, 255, 0.5)",
        glowBlur: 4,
        isMesh: true,
      },
    ];
  }

  private initSparks(): void {
    this.sparks = [];
    for (let i = 0; i < this.numSparks; i++) {
      this.sparks.push({
        xNorm: Math.random(),
        speed: 0.0008 + Math.random() * 0.0016,
        ribbonIndex: Math.floor(Math.random() * 3), // Anchor to primary ribbons
        size: 1.2 + Math.random() * 2.2,
        twinklePhase: Math.random() * Math.PI * 2,
        twinkleSpeed: 0.04 + Math.random() * 0.06,
        offsetY: (Math.random() - 0.5) * 16,
        color: Math.random() > 0.4 ? "rgba(255, 255, 255," : "rgba(0, 235, 255,",
      });
    }
  }

  public setState(state: JarvisState): void {
    this.state = state;
  }

  /**
   * Updates incoming audio level [0.0 - 1.0].
   */
  public updateLevel(level: number): void {
    this.targetLevel = Math.max(0.0, Math.min(1.0, level));
  }

  public clear(): void {
    this.targetLevel = 0.0;
    this.currentLevel = 0.0;
  }

  /**
   * Computes vertical elevation y at horizontal coordinate x for a given ribbon.
   */
  private getWaveY(x: number, width: number, centerY: number, ribbon: WaveRibbon, amplitude: number): number {
    // Smooth cosine envelope tapering to 0 at edges (vignette effect)
    const normX = x / width;
    const envelope = Math.pow(Math.sin(normX * Math.PI), 1.8);

    const w1 = Math.sin(x * ribbon.freq1 + this.time * ribbon.speed1 + ribbon.phaseOffset);
    const w2 = Math.sin(x * ribbon.freq2 + this.time * ribbon.speed2);
    const w3 = Math.cos(x * 0.0028 - this.time * 0.015);

    const waveHeight = (w1 * 0.65 + w2 * 0.35 + w3 * 0.15) * ribbon.ampMultiplier * amplitude;
    return centerY + waveHeight * envelope;
  }

  private startRenderLoop = (): void => {
    // Exponential smoothing for master audio level
    this.currentLevel += (this.targetLevel - this.currentLevel) * 0.22;
    this.targetLevel *= 0.94; // Natural audio decay

    // Dynamic phase speed by state
    let stateTimeMultiplier = 1.0;
    let stateAmpMultiplier = 1.0;

    switch (this.state) {
      case "idle":
        stateTimeMultiplier = 0.85;
        stateAmpMultiplier = 0.8;
        break;
      case "listening":
        stateTimeMultiplier = 1.4;
        stateAmpMultiplier = 1.3;
        break;
      case "thinking":
        stateTimeMultiplier = 2.4; // Rapid shimmering wave
        stateAmpMultiplier = 1.1;
        break;
      case "speaking":
        stateTimeMultiplier = 1.8;
        stateAmpMultiplier = 1.5;
        break;
      case "error":
        stateTimeMultiplier = 2.0;
        stateAmpMultiplier = 1.2;
        break;
    }

    this.time += 1.0 * stateTimeMultiplier;
    this.draw(stateAmpMultiplier);
    this.animFrameId = requestAnimationFrame(this.startRenderLoop);
  };

  private draw(stateAmpMultiplier: number): void {
    const rect = this.canvas.getBoundingClientRect();
    const width = rect.width || this.canvas.width;
    const height = rect.height || this.canvas.height;
    const centerY = height * 0.5;

    this.ctx.clearRect(0, 0, width, height);

    // Audio-reactive amplitude scaling
    const dynamicAmp = (this.baseHeight + this.currentLevel * 90.0) * stateAmpMultiplier;

    // Ambient Center Glow Aura (Soft volumetric background light)
    const glowRadiusX = width * 0.42;
    const glowRadiusY = dynamicAmp * 1.5 + 40;
    const haloGradient = this.ctx.createRadialGradient(
      width * 0.5, centerY, 0,
      width * 0.5, centerY, glowRadiusX
    );

    let haloColor = "0, 100, 255";
    if (this.state === "thinking") haloColor = "255, 180, 0";
    else if (this.state === "error") haloColor = "255, 40, 70";
    else if (this.state === "speaking") haloColor = "0, 210, 255";

    haloGradient.addColorStop(0, `rgba(${haloColor}, ${0.12 + this.currentLevel * 0.15})`);
    haloGradient.addColorStop(0.5, `rgba(${haloColor}, 0.03)`);
    haloGradient.addColorStop(1, "rgba(0, 0, 0, 0)");

    this.ctx.save();
    this.ctx.scale(1, glowRadiusY / glowRadiusX);
    this.ctx.beginPath();
    this.ctx.arc(width * 0.5, centerY * (glowRadiusX / glowRadiusY), glowRadiusX, 0, Math.PI * 2);
    this.ctx.fillStyle = haloGradient;
    this.ctx.fill();
    this.ctx.restore();

    // Enable Additive Blending for vibrant neon saturation
    this.ctx.globalCompositeOperation = "lighter";

    // 1. Render Fluid Volumetric Shrouds (Filled gradient ribbon between Ribbon 1 and 2)
    const step = 6;
    const pointsR1: { x: number; y: number }[] = [];
    const pointsR2: { x: number; y: number }[] = [];

    for (let x = 0; x <= width; x += step) {
      pointsR1.push({ x, y: this.getWaveY(x, width, centerY, this.ribbons[1], dynamicAmp) });
      pointsR2.push({ x, y: this.getWaveY(x, width, centerY, this.ribbons[2], dynamicAmp) });
    }

    if (pointsR1.length > 0 && pointsR2.length > 0) {
      this.ctx.beginPath();
      this.ctx.moveTo(pointsR1[0].x, pointsR1[0].y);
      for (let i = 1; i < pointsR1.length; i++) {
        this.ctx.lineTo(pointsR1[i].x, pointsR1[i].y);
      }
      for (let i = pointsR2.length - 1; i >= 0; i--) {
        this.ctx.lineTo(pointsR2[i].x, pointsR2[i].y);
      }
      this.ctx.closePath();

      const shroudGradient = this.ctx.createLinearGradient(0, centerY - dynamicAmp, 0, centerY + dynamicAmp);
      shroudGradient.addColorStop(0, `rgba(${haloColor}, ${0.08 + this.currentLevel * 0.12})`);
      shroudGradient.addColorStop(0.5, `rgba(0, 230, 255, ${0.15 + this.currentLevel * 0.20})`);
      shroudGradient.addColorStop(1, `rgba(${haloColor}, ${0.04 + this.currentLevel * 0.08})`);
      this.ctx.fillStyle = shroudGradient;
      this.ctx.fill();
    }

    // 2. Render Continuous Harmonic Ribbons
    for (let r = 0; r < this.ribbons.length; r++) {
      const ribbon = this.ribbons[r];

      // Dynamic color adjustments by state
      let strokeColor = ribbon.color;
      let glowColor = ribbon.glowColor;

      if (this.state === "thinking") {
        strokeColor = r === 0 ? "rgba(255, 255, 255, 0.95)" : "rgba(255, 190, 40, 0.75)";
        glowColor = "rgba(255, 180, 0, 0.8)";
      } else if (this.state === "error") {
        strokeColor = r === 0 ? "rgba(255, 255, 255, 0.95)" : "rgba(255, 50, 90, 0.75)";
        glowColor = "rgba(255, 40, 70, 0.8)";
      } else if (this.state === "speaking") {
        strokeColor = r === 0 ? "rgba(255, 255, 255, 0.98)" : "rgba(0, 245, 212, 0.85)";
        glowColor = "rgba(0, 230, 255, 0.85)";
      }

      if (ribbon.isMesh) {
        // Render Stardust Particle Mesh Dots along wave
        const dotStep = 9;
        this.ctx.shadowBlur = ribbon.glowBlur;
        this.ctx.shadowColor = glowColor;
        this.ctx.fillStyle = strokeColor;

        for (let x = 12; x < width - 12; x += dotStep) {
          const y = this.getWaveY(x, width, centerY, ribbon, dynamicAmp);
          const normX = x / width;
          const envelope = Math.pow(Math.sin(normX * Math.PI), 1.6);
          const dotSize = Math.max(0.6, 1.6 * envelope * (1.0 + this.currentLevel * 0.6));

          this.ctx.beginPath();
          this.ctx.arc(x, y, dotSize, 0, Math.PI * 2);
          this.ctx.fill();
        }
      } else {
        // Continuous Smooth Neon Ribbon Curve
        this.ctx.beginPath();
        this.ctx.lineWidth = ribbon.lineWidth * (1.0 + this.currentLevel * 0.4);
        this.ctx.strokeStyle = strokeColor;
        this.ctx.shadowBlur = ribbon.glowBlur * (1.0 + this.currentLevel * 0.5);
        this.ctx.shadowColor = glowColor;

        let prevX = 0;
        let prevY = this.getWaveY(0, width, centerY, ribbon, dynamicAmp);
        this.ctx.moveTo(prevX, prevY);

        for (let x = step; x <= width; x += step) {
          const currY = this.getWaveY(x, width, centerY, ribbon, dynamicAmp);
          const midX = (prevX + x) * 0.5;
          const midY = (prevY + currY) * 0.5;
          this.ctx.quadraticCurveTo(prevX, prevY, midX, midY);
          prevX = x;
          prevY = currY;
        }
        this.ctx.lineTo(width, this.getWaveY(width, width, centerY, ribbon, dynamicAmp));
        this.ctx.stroke();
      }
    }

    // 3. Render Floating Crest Energy Sparks (Bokeh Motes surfing the waves)
    for (let s = 0; s < this.sparks.length; s++) {
      const spark = this.sparks[s];

      // Drift horizontally
      spark.xNorm += spark.speed;
      if (spark.xNorm > 1.0) spark.xNorm = 0.0;

      const sparkX = spark.xNorm * width;
      const ribbon = this.ribbons[spark.ribbonIndex] || this.ribbons[0];
      const baseWaveY = this.getWaveY(sparkX, width, centerY, ribbon, dynamicAmp);
      const sparkY = baseWaveY + spark.offsetY;

      // Twinkle pulsation
      spark.twinklePhase += spark.twinkleSpeed;
      const twinkle = Math.sin(spark.twinklePhase) * 0.4 + 0.6;

      const normX = spark.xNorm;
      const envelope = Math.pow(Math.sin(normX * Math.PI), 1.4);
      const alpha = twinkle * envelope * (0.6 + this.currentLevel * 0.4);
      const size = spark.size * (1.0 + this.currentLevel * 0.5) * envelope;

      if (envelope > 0.08) {
        this.ctx.beginPath();
        this.ctx.arc(sparkX, sparkY, Math.max(0.8, size), 0, Math.PI * 2);
        this.ctx.fillStyle = `${spark.color} ${alpha.toFixed(2)})`;
        this.ctx.shadowBlur = 8;
        this.ctx.shadowColor = "rgba(0, 230, 255, 0.8)";
        this.ctx.fill();
      }
    }

    // Reset shadow blur and composite mode
    this.ctx.shadowBlur = 0;
    this.ctx.globalCompositeOperation = "source-over";
  }

  public destroy(): void {
    if (this.animFrameId !== null) {
      cancelAnimationFrame(this.animFrameId);
      this.animFrameId = null;
    }
    window.removeEventListener("resize", this.handleResize);
  }
}
