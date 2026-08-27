/**
 * Jarvis AI - Celestial Fusion Plasma Core & HUD Radar Visor Visualizer
 * Inspired by futuristic military/sci-fi holographic agent interfaces.
 * Features:
 * - Volumetric Solar Plasma Sphere with multi-octave turbulence and incandescent glow
 * - Dynamic Specular Crescent Flare Highlight along upper rim
 * - Rotating Radar Sweep Sector (continuous angular scanning beam)
 * - Concentric High-Precision Caliper & Degree Hash Rings (0° - 360°)
 * - Counter-rotating mechanical arc segments and dashed telemetry tracks
 * - Stepped Holographic Visor Reticle Overlay with target locks and diagnostic readouts
 * - Audio-reactive plasma expansion, corona flaring, and state-driven dynamics
 */

import { JarvisState } from "../core/types";

export class FusionCoreVisualizer {
  private canvas: HTMLCanvasElement;
  private ctx: CanvasRenderingContext2D;
  private state: JarvisState = "idle";
  private currentLevel = 0;
  private targetLevel = 0;
  private animFrameId: number | null = null;
  private isRunning = false;

  // Animation clocks
  private time = 0;
  private radarAngle = 0;
  private ringAngle1 = 0;
  private ringAngle2 = 0;
  private ringAngle3 = 0;

  // Base dimensions
  private readonly sphereRadius = 82;
  private readonly outerRadius = 168;

  constructor(canvas: HTMLCanvasElement) {
    this.canvas = canvas;
    const context = canvas.getContext("2d");
    if (!context) {
      throw new Error("Could not get 2D context for FusionCore canvas");
    }
    this.ctx = context;

    this.resize();
    window.addEventListener("resize", this.handleResize);
  }

  private handleResize = (): void => {
    this.resize();
  };

  public resize(): void {
    const dpr = window.devicePixelRatio || 1;
    const width = 440;
    const height = 440;

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
    this.targetLevel = Math.max(0, Math.min(1, level));
  }

  private startRenderLoop = (): void => {
    if (!this.isRunning) return;

    // Smooth audio tracking
    this.currentLevel += (this.targetLevel - this.currentLevel) * 0.22;

    // Speeds tuned by state
    let speedMult = 1.0;
    if (this.state === "listening") speedMult = 1.4;
    else if (this.state === "thinking") speedMult = 2.6;
    else if (this.state === "speaking") speedMult = 1.8;
    else if (this.state === "error") speedMult = 1.2;

    this.time += 0.03 * speedMult;
    this.radarAngle += 0.024 * speedMult;
    this.ringAngle1 += 0.008 * speedMult;
    this.ringAngle2 -= 0.012 * speedMult;
    this.ringAngle3 += 0.005 * speedMult;

    this.render();
    this.animFrameId = requestAnimationFrame(this.startRenderLoop);
  };

  private render(): void {
    const dpr = window.devicePixelRatio || 1;
    const width = 440;
    const height = 440;
    const cx = width * 0.5;
    const cy = height * 0.5;

    if (this.canvas.width !== width * dpr || this.canvas.height !== height * dpr) {
      this.canvas.width = width * dpr;
      this.canvas.height = height * dpr;
    }

    this.ctx.save();
    this.ctx.resetTransform?.();
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    this.ctx.scale(dpr, dpr);

    // Color palettes by state
    let primaryColor = "0, 212, 255";   // Electric Cyan
    let coreAmber = "255, 120, 20";     // Incandescent Solar Amber
    let coreGlow = "255, 180, 40";      // Golden Solar Corona
    let crescentColor = "255, 240, 180"; // Solar Flare White-Gold
    let statusText = "CORE FLUX: 100%";
    let subStatus = "TEMP NOMINAL";

    if (this.state === "listening") {
      primaryColor = "0, 245, 255";
      coreAmber = "0, 160, 255";
      coreGlow = "0, 230, 255";
      crescentColor = "200, 250, 255";
      statusText = "VOICE INPUT DETECTED";
      subStatus = "ACOUSTIC SYNC";
    } else if (this.state === "thinking") {
      primaryColor = "255, 200, 0";
      coreAmber = "255, 100, 0";
      coreGlow = "255, 220, 50";
      crescentColor = "255, 255, 220";
      statusText = "NEURAL PROCESSING";
      subStatus = "COGNITION ACTIVE";
    } else if (this.state === "speaking") {
      primaryColor = "0, 255, 210";
      coreAmber = "255, 140, 30";
      coreGlow = "0, 240, 255";
      crescentColor = "255, 255, 255";
      statusText = "VOCAL SYNTHESIS";
      subStatus = "AUDIO STREAMING";
    } else if (this.state === "error") {
      primaryColor = "255, 40, 60";
      coreAmber = "220, 20, 40";
      coreGlow = "255, 80, 80";
      crescentColor = "255, 180, 180";
      statusText = "DIAGNOSTIC FAULT";
      subStatus = "TEMP WARNING";
    }

    // Dynamic radius with audio reactivity
    const audioExpansion = this.currentLevel * 22;
    const dynamicSphereR = this.sphereRadius + audioExpansion;

    // 1. Render Deep Background Aura
    this.renderAtmosphericGlow(cx, cy, dynamicSphereR, coreGlow);

    // 2. Render Volumetric Celestial Solar Plasma Sphere
    this.renderPlasmaSphere(cx, cy, dynamicSphereR, coreAmber, coreGlow, crescentColor);

    // 3. Render Specular Crescent Highlight along Upper Rim
    this.renderCrescentHighlight(cx, cy, dynamicSphereR, crescentColor);

    // 4. Render Rotating Radar Sweep Sector
    this.renderRadarSweep(cx, cy, dynamicSphereR + 10, primaryColor);

    // 5. Render Precision Caliper Rings & Hash Graduations
    this.renderCaliperRings(cx, cy, primaryColor);

    // 6. Render Mechanical Arc Tracks & Segmented Segments
    this.renderMechanicalArcs(cx, cy, primaryColor, coreGlow);

    // 7. Render Holographic Visor Reticle Overlay & Telemetry Readouts
    this.renderVisorReticle(cx, cy, dynamicSphereR, primaryColor, coreAmber, statusText, subStatus);
  }

  /**
   * 1. Soft atmospheric luminescence behind the core
   */
  private renderAtmosphericGlow(cx: number, cy: number, radius: number, coreGlow: string): void {
    const glowR = radius * 2.1;
    const grad = this.ctx.createRadialGradient(cx, cy, radius * 0.3, cx, cy, glowR);
    grad.addColorStop(0, `rgba(${coreGlow}, ${0.28 + this.currentLevel * 0.25})`);
    grad.addColorStop(0.5, `rgba(${coreGlow}, 0.08)`);
    grad.addColorStop(1, "rgba(0, 0, 0, 0)");

    this.ctx.save();
    this.ctx.beginPath();
    this.ctx.arc(cx, cy, glowR, 0, Math.PI * 2);
    this.ctx.fillStyle = grad;
    this.ctx.fill();
    this.ctx.restore();
  }

  /**
   * 2. Celestial Solar Plasma Sphere with animated surface turbulence
   */
  private renderPlasmaSphere(
    cx: number,
    cy: number,
    radius: number,
    coreAmber: string,
    coreGlow: string,
    crescentColor: string
  ): void {
    this.ctx.save();

    // Base spherical body gradient (dark incandescent sphere with fiery corona)
    const sphereGrad = this.ctx.createRadialGradient(
      cx - radius * 0.25,
      cy - radius * 0.35,
      radius * 0.1,
      cx,
      cy,
      radius
    );
    sphereGrad.addColorStop(0, `rgba(${crescentColor}, 0.95)`);
    sphereGrad.addColorStop(0.2, `rgba(${coreGlow}, 0.92)`);
    sphereGrad.addColorStop(0.65, `rgba(${coreAmber}, 0.85)`);
    sphereGrad.addColorStop(0.92, `rgba(40, 10, 5, 0.95)`);
    sphereGrad.addColorStop(1.0, `rgba(${coreGlow}, 0.9)`);

    this.ctx.beginPath();
    this.ctx.arc(cx, cy, radius, 0, Math.PI * 2);
    this.ctx.fillStyle = sphereGrad;
    this.ctx.shadowBlur = 24 + this.currentLevel * 20;
    this.ctx.shadowColor = `rgba(${coreGlow}, 0.95)`;
    this.ctx.fill();
    this.ctx.shadowBlur = 0;

    // Clip to sphere interior to draw procedural plasma veins and turbulence
    this.ctx.save();
    this.ctx.beginPath();
    this.ctx.arc(cx, cy, radius - 1, 0, Math.PI * 2);
    this.ctx.clip();

    // Additive blending for fiery filament veins
    this.ctx.globalCompositeOperation = "screen";

    const numVeins = 24;
    for (let i = 0; i < numVeins; i++) {
      const angle = (i / numVeins) * Math.PI * 2 + this.time * 0.4;
      const dist = (Math.sin(i * 3.7 + this.time * 1.5) * 0.5 + 0.5) * (radius * 0.78);
      const px = cx + Math.cos(angle) * dist;
      const py = cy + Math.sin(angle) * dist * 0.85;
      const veinR = 14 + Math.sin(this.time * 2.0 + i) * 8 + this.currentLevel * 10;

      const veinGrad = this.ctx.createRadialGradient(px, py, 0, px, py, veinR);
      veinGrad.addColorStop(0, `rgba(${crescentColor}, 0.65)`);
      veinGrad.addColorStop(0.4, `rgba(${coreGlow}, 0.35)`);
      veinGrad.addColorStop(1, "rgba(0, 0, 0, 0)");

      this.ctx.beginPath();
      this.ctx.arc(px, py, veinR, 0, Math.PI * 2);
      this.ctx.fillStyle = veinGrad;
      this.ctx.fill();
    }

    // Solar flare granulations (criss-crossing turbulent lines)
    this.ctx.lineWidth = 1.2;
    this.ctx.strokeStyle = `rgba(${crescentColor}, 0.25)`;
    for (let j = 0; j < 6; j++) {
      this.ctx.beginPath();
      const wavePhase = this.time * 0.8 + j * 1.1;
      const startY = cy - radius * 0.6 + j * (radius * 0.24);
      for (let x = -radius; x <= radius; x += 6) {
        const normX = x / radius;
        if (Math.abs(normX) > 0.95) continue;
        const curveY = startY + Math.sin(normX * 4.5 + wavePhase) * 9.0;
        if (x === -radius) this.ctx.moveTo(cx + x, curveY);
        else this.ctx.lineTo(cx + x, curveY);
      }
      this.ctx.stroke();
    }

    this.ctx.restore(); // Exit sphere clipping
    this.ctx.restore();
  }

  /**
   * 3. Dynamic Specular Crescent Flare Highlight along upper rim (as seen in Reference 2)
   */
  private renderCrescentHighlight(cx: number, cy: number, radius: number, crescentColor: string): void {
    this.ctx.save();
    this.ctx.globalCompositeOperation = "lighter";

    // Crescent Arc from angle -140 deg to -40 deg
    const startAngle = -Math.PI * 0.82;
    const endAngle = -Math.PI * 0.18;

    this.ctx.beginPath();
    this.ctx.arc(cx, cy, radius - 2, startAngle, endAngle);
    this.ctx.lineWidth = 4.5 + this.currentLevel * 3.5;
    this.ctx.strokeStyle = `rgba(${crescentColor}, 0.95)`;
    this.ctx.shadowBlur = 18 + this.currentLevel * 12;
    this.ctx.shadowColor = `rgba(${crescentColor}, 1.0)`;
    this.ctx.stroke();

    // Intense center flare hot spot along the top apex
    const apexX = cx;
    const apexY = cy - radius + 2;
    const flareGrad = this.ctx.createRadialGradient(apexX, apexY, 0, apexX, apexY, 32 + this.currentLevel * 16);
    flareGrad.addColorStop(0, "rgba(255, 255, 255, 1.0)");
    flareGrad.addColorStop(0.3, `rgba(${crescentColor}, 0.85)`);
    flareGrad.addColorStop(1, "rgba(255, 255, 255, 0)");

    this.ctx.beginPath();
    this.ctx.arc(apexX, apexY, 32 + this.currentLevel * 16, 0, Math.PI * 2);
    this.ctx.fillStyle = flareGrad;
    this.ctx.fill();

    this.ctx.restore();
  }

  /**
   * 4. Rotating Radar Sweep Sector
   */
  private renderRadarSweep(cx: number, cy: number, radius: number, primaryColor: string): void {
    this.ctx.save();
    this.ctx.globalCompositeOperation = "lighter";

    const sweepAngle = Math.PI * 0.24; // ~43 degrees
    const startA = this.radarAngle - sweepAngle;
    const endA = this.radarAngle;

    // Draw pie slice with angular/radial gradient
    const grad = this.ctx.createRadialGradient(cx, cy, 10, cx, cy, radius);
    grad.addColorStop(0, `rgba(${primaryColor}, 0.35)`);
    grad.addColorStop(0.85, `rgba(${primaryColor}, 0.18)`);
    grad.addColorStop(1, `rgba(${primaryColor}, 0.0)`);

    this.ctx.beginPath();
    this.ctx.moveTo(cx, cy);
    this.ctx.arc(cx, cy, radius, startA, endA);
    this.ctx.closePath();
    this.ctx.fillStyle = grad;
    this.ctx.fill();

    // Leading edge beam line
    this.ctx.beginPath();
    this.ctx.moveTo(cx, cy);
    this.ctx.lineTo(cx + Math.cos(endA) * radius, cy + Math.sin(endA) * radius);
    this.ctx.lineWidth = 1.8;
    this.ctx.strokeStyle = `rgba(255, 255, 255, 0.85)`;
    this.ctx.shadowBlur = 8;
    this.ctx.shadowColor = `rgba(${primaryColor}, 0.9)`;
    this.ctx.stroke();

    this.ctx.restore();
  }

  /**
   * 5. Precision Caliper Rings with Degree Graduation Ticks (0° - 360°)
   */
  private renderCaliperRings(cx: number, cy: number, primaryColor: string): void {
    this.ctx.save();

    const ringR = this.outerRadius;
    const totalTicks = 120; // Every 3 degrees

    this.ctx.lineWidth = 1.0;
    this.ctx.font = "8px 'Fira Code', 'Roboto Mono', monospace";
    this.ctx.textAlign = "center";
    this.ctx.textBaseline = "middle";

    for (let i = 0; i < totalTicks; i++) {
      const angle = (i / totalTicks) * Math.PI * 2 + this.ringAngle1;
      const isMajor = i % 10 === 0;
      const isSemiMajor = i % 5 === 0;

      const tickLen = isMajor ? 9 : isSemiMajor ? 6 : 3.5;
      const rInner = ringR - tickLen;
      const rOuter = ringR;

      const x1 = cx + Math.cos(angle) * rInner;
      const y1 = cy + Math.sin(angle) * rInner;
      const x2 = cx + Math.cos(angle) * rOuter;
      const y2 = cy + Math.sin(angle) * rOuter;

      this.ctx.beginPath();
      this.ctx.moveTo(x1, y1);
      this.ctx.lineTo(x2, y2);

      if (isMajor) {
        this.ctx.strokeStyle = "rgba(255, 255, 255, 0.9)";
        this.ctx.lineWidth = 1.4;
      } else {
        this.ctx.strokeStyle = `rgba(${primaryColor}, 0.45)`;
        this.ctx.lineWidth = 0.8;
      }
      this.ctx.stroke();

      // Quadrant index labels (00, 90, 180, 270)
      if (isMajor && i % 30 === 0) {
        const labelR = ringR + 11;
        const lx = cx + Math.cos(angle) * labelR;
        const ly = cy + Math.sin(angle) * labelR;
        const deg = ((i / totalTicks) * 360).toFixed(0).padStart(3, "0");
        this.ctx.fillStyle = `rgba(${primaryColor}, 0.75)`;
        this.ctx.fillText(`${deg}°`, lx, ly);
      }
    }

    // Concentric base caliper circles
    this.ctx.beginPath();
    this.ctx.arc(cx, cy, ringR, 0, Math.PI * 2);
    this.ctx.strokeStyle = `rgba(${primaryColor}, 0.35)`;
    this.ctx.lineWidth = 1.0;
    this.ctx.stroke();

    this.ctx.beginPath();
    this.ctx.arc(cx, cy, ringR - 12, 0, Math.PI * 2);
    this.ctx.strokeStyle = `rgba(255, 255, 255, 0.2)`;
    this.ctx.setLineDash([2, 5]);
    this.ctx.stroke();
    this.ctx.setLineDash([]);

    this.ctx.restore();
  }

  /**
   * 6. Mechanical Arc Segments, Stepped Slats & Telemetry Guides
   */
  private renderMechanicalArcs(cx: number, cy: number, primaryColor: string, coreGlow: string): void {
    this.ctx.save();

    // Intermediate Segmented Arc Ring (Counter-rotating)
    const midR = this.sphereRadius + 36;
    const numArcs = 4;
    const arcSpan = Math.PI * 0.32;

    for (let i = 0; i < numArcs; i++) {
      const startAngle = (i / numArcs) * Math.PI * 2 + this.ringAngle2;
      const endAngle = startAngle + arcSpan;

      this.ctx.beginPath();
      this.ctx.arc(cx, cy, midR, startAngle, endAngle);
      this.ctx.lineWidth = 3.5;
      this.ctx.strokeStyle = `rgba(${primaryColor}, 0.8)`;
      this.ctx.shadowBlur = 6;
      this.ctx.shadowColor = `rgba(${primaryColor}, 0.7)`;
      this.ctx.stroke();

      // Slotted notch markers at arc ends
      const endX = cx + Math.cos(endAngle) * midR;
      const endY = cy + Math.sin(endAngle) * midR;
      this.ctx.beginPath();
      this.ctx.arc(endX, endY, 2.5, 0, Math.PI * 2);
      this.ctx.fillStyle = "#ffffff";
      this.ctx.fill();
    }

    // Secondary Telemetry Ring (Clockwise)
    const innerR = this.sphereRadius + 18;
    this.ctx.beginPath();
    this.ctx.arc(cx, cy, innerR, 0, Math.PI * 2);
    this.ctx.lineWidth = 1.2;
    this.ctx.strokeStyle = `rgba(${coreGlow}, 0.55)`;
    this.ctx.setLineDash([8, 6, 2, 6]);
    this.ctx.stroke();
    this.ctx.setLineDash([]);

    this.ctx.restore();
  }

  /**
   * 7. Stepped Holographic Visor Reticle Overlay & Diagnostic HUD Readouts
   */
  private renderVisorReticle(
    cx: number,
    cy: number,
    radius: number,
    primaryColor: string,
    coreAmber: string,
    statusText: string,
    subStatus: string
  ): void {
    this.ctx.save();

    // Upper & Lower Stepped Visor Brackets framing the core (/ \ and \_/)
    const visorW = radius * 1.35;
    const visorH = radius * 0.85;

    this.ctx.lineWidth = 1.6;
    this.ctx.strokeStyle = `rgba(${primaryColor}, 0.85)`;
    this.ctx.shadowBlur = 8;
    this.ctx.shadowColor = `rgba(${primaryColor}, 0.6)`;

    // Top Bracket: [ ---\___/--- ]
    this.ctx.beginPath();
    this.ctx.moveTo(cx - visorW, cy - visorH * 0.5);
    this.ctx.lineTo(cx - visorW * 0.5, cy - visorH * 0.5);
    this.ctx.lineTo(cx - visorW * 0.3, cy - visorH * 0.88);
    this.ctx.lineTo(cx + visorW * 0.3, cy - visorH * 0.88);
    this.ctx.lineTo(cx + visorW * 0.5, cy - visorH * 0.5);
    this.ctx.lineTo(cx + visorW, cy - visorH * 0.5);
    this.ctx.stroke();

    // Bottom Bracket: [ ---/‾‾‾\--- ]
    this.ctx.beginPath();
    this.ctx.moveTo(cx - visorW, cy + visorH * 0.5);
    this.ctx.lineTo(cx - visorW * 0.5, cy + visorH * 0.5);
    this.ctx.lineTo(cx - visorW * 0.3, cy + visorH * 0.88);
    this.ctx.lineTo(cx + visorW * 0.3, cy + visorH * 0.88);
    this.ctx.lineTo(cx + visorW * 0.5, cy + visorH * 0.5);
    this.ctx.lineTo(cx + visorW, cy + visorH * 0.5);
    this.ctx.stroke();

    // Reticle Center Crosshair Pips (Orange/White indexing pointers)
    const pipOffset = radius + 6;
    const pipLen = 8;

    const renderPip = (angle: number) => {
      const px1 = cx + Math.cos(angle) * (pipOffset);
      const py1 = cy + Math.sin(angle) * (pipOffset);
      const px2 = cx + Math.cos(angle) * (pipOffset + pipLen);
      const py2 = cy + Math.sin(angle) * (pipOffset + pipLen);

      this.ctx.beginPath();
      this.ctx.moveTo(px1, py1);
      this.ctx.lineTo(px2, py2);
      this.ctx.lineWidth = 2.0;
      this.ctx.strokeStyle = `rgba(${coreAmber}, 0.95)`;
      this.ctx.stroke();
    };

    // 4 Diagonal Cardinal Pips
    renderPip(-Math.PI * 0.75); // Top Left
    renderPip(-Math.PI * 0.25); // Top Right
    renderPip(Math.PI * 0.75);  // Bottom Left
    renderPip(Math.PI * 0.25);  // Bottom Right

    // Diagnostic HUD Readouts (Above & Below Core)
    this.ctx.font = "bold 9px 'Fira Code', 'Roboto Mono', monospace";
    this.ctx.textAlign = "center";

    // Status Pill Top
    this.ctx.fillStyle = `rgba(${primaryColor}, 0.9)`;
    this.ctx.fillText(statusText, cx, cy - radius - 16);

    // Warning / Substatus Bottom
    if (this.state === "error") {
      this.ctx.fillStyle = "rgba(255, 50, 70, 0.95)";
      this.ctx.fillText(`▲ ${subStatus} ▲`, cx, cy + radius + 22);
    } else {
      this.ctx.fillStyle = `rgba(${coreAmber}, 0.85)`;
      this.ctx.fillText(subStatus, cx, cy + radius + 20);
    }

    this.ctx.restore();
  }

  public destroy(): void {
    this.stop();
    window.removeEventListener("resize", this.handleResize);
  }
}
