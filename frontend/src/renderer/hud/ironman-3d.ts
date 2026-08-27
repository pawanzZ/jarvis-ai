/**
 * Jarvis AI - Interactive 3D Holographic Iron Man Model
 * Fully rotatable, zoomable 3D wireframe & holographic armor visualizer.
 * Supports:
 * - Direct mouse/touch drag orbit (360° yaw & pitch with inertial momentum)
 * - Mouse wheel zoom (0.6x to 2.4x) & double-click view reset
 * - Auto-orbit turntable rotation when idle
 * - Dual view modes: HELMET (Reference 1) & FULL SUIT BLUEPRINT (Reference 2)
 * - Dynamic glowing eye slits and chest Arc Reactor pulsing with Jarvis state and vocal audio
 * - Holographic leader lines and armor diagnostics
 */

import { JarvisState } from "../core/types";

interface Point3D {
  x: number;
  y: number;
  z: number;
}

interface Edge3D {
  p1: number;
  p2: number;
  color?: string;
  width?: number;
}

interface Polygon3D {
  indices: number[];
  fill?: string;
  stroke?: string;
  glow?: boolean;
}

interface DiagnosticCallout {
  anchorIdx: number;
  label: string;
  sub: string;
  dir: "left" | "right";
}

export type IronManViewMode = "helmet" | "suit";

export class IronMan3DModelHUD {
  private canvas: HTMLCanvasElement;
  private ctx: CanvasRenderingContext2D;
  private animFrameId: number | null = null;
  private isRunning = false;
  private state: JarvisState = "idle";
  private audioLevel = 0;
  private viewMode: IronManViewMode = "helmet";

  // Camera & Interaction
  private yaw = 0.25;          // Horizontal rotation
  private pitch = -0.08;       // Vertical tilt
  private zoom = 1.0;          // Zoom scale
  private yawVel = 0;
  private pitchVel = 0;
  private isDragging = false;
  private lastMouseX = 0;
  private lastMouseY = 0;
  private lastInteractionTime = 0;
  private targetYaw = 0;
  private targetPitch = 0;
  private targetZoom = 1.0;
  private isResetting = false;

  // Geometry: Helmet
  private helmetVertices: Point3D[] = [];
  private helmetEdges: Edge3D[] = [];
  private helmetPolygons: Polygon3D[] = [];
  private helmetEyeLeft: number[] = [];
  private helmetEyeRight: number[] = [];

  // Geometry: Full Suit
  private suitVertices: Point3D[] = [];
  private suitEdges: Edge3D[] = [];
  private suitPolygons: Polygon3D[] = [];
  private suitCallouts: DiagnosticCallout[] = [];
  private chestReactorCenterIdx = 0;

  constructor(canvas: HTMLCanvasElement) {
    this.canvas = canvas;
    const context = canvas.getContext("2d");
    if (!context) throw new Error("Could not get 2D context for IronMan3DModelHUD");
    this.ctx = context;

    this.buildHelmetGeometry();
    this.buildSuitGeometry();
    this.setupInteractions();

    this.resize();
    window.addEventListener("resize", this.handleResize);
    this.start();
  }

  public setViewMode(mode: IronManViewMode): void {
    this.viewMode = mode;
    this.resetView();
  }

  public toggleViewMode(): IronManViewMode {
    this.viewMode = this.viewMode === "helmet" ? "suit" : "helmet";
    this.resetView();
    return this.viewMode;
  }

  public getViewMode(): IronManViewMode {
    return this.viewMode;
  }

  public setState(state: JarvisState): void {
    this.state = state;
  }

  public setAudioLevel(level: number): void {
    this.audioLevel = Math.max(0, Math.min(1, level));
  }

  public resetView(): void {
    this.targetYaw = 0.0;
    this.targetPitch = -0.05;
    this.targetZoom = 1.0;
    this.isResetting = true;
  }

  /**
   * Builds high-fidelity 3D Iron Man Helmet geometry from Reference 1 (media_1787834180861.png)
   */
  private buildHelmetGeometry(): void {
    const v: Point3D[] = [];
    const e: Edge3D[] = [];
    const poly: Polygon3D[] = [];

    const addV = (x: number, y: number, z: number): number => {
      v.push({ x, y, z });
      return v.length - 1;
    };

    const addEdge = (p1: number, p2: number, color?: string, width?: number) => {
      e.push({ p1, p2, color, width });
    };

    // --- Cranium & Forehead ---
    const topCrown = addV(0, -68, 8);
    const topCrownL = addV(-22, -64, 4);
    const topCrownR = addV(22, -64, 4);
    const templeL = addV(-38, -48, -4);
    const templeR = addV(38, -48, -4);

    // Trapezoid Forehead Inset Plate
    const fhTL = addV(-12, -60, 16);
    const fhTR = addV(12, -60, 16);
    const fhBL = addV(-8, -42, 22);
    const fhBR = addV(8, -42, 22);

    // Brow Ridge (Prominent chamfered ridge)
    const browCenter = addV(0, -32, 28);
    const browMidL = addV(-18, -31, 26);
    const browMidR = addV(18, -31, 26);
    const browOuterL = addV(-36, -30, 16);
    const browOuterR = addV(36, -30, 16);

    // Left Eye Slit (Angular polygon)
    const eL1 = addV(-12, -26, 26);
    const eL2 = addV(-32, -24, 18);
    const eL3 = addV(-30, -21, 19);
    const eL4 = addV(-12, -23, 26);
    this.helmetEyeLeft = [eL1, eL2, eL3, eL4];

    // Right Eye Slit (Angular polygon)
    const eR1 = addV(12, -26, 26);
    const eR2 = addV(32, -24, 18);
    const eR3 = addV(30, -21, 19);
    const eR4 = addV(12, -23, 26);
    this.helmetEyeRight = [eR1, eR2, eR3, eR4];

    // Nose bridge & Faceplate Upper Center
    const noseBridge = addV(0, -20, 29);
    const noseLower = addV(0, -8, 28);

    // Cheekbone Chamfers
    const cheekTopL = addV(-36, -18, 16);
    const cheekTopR = addV(36, -18, 16);
    const cheekMidL = addV(-28, 4, 20);
    const cheekMidR = addV(28, 4, 20);

    // Faceplate Lower Taper / Mouth Slit
    const mouthTL = addV(-14, 16, 24);
    const mouthTR = addV(14, 16, 24);
    const mouthBL = addV(-12, 22, 23);
    const mouthBR = addV(12, 22, 23);

    // Chin Plate (Chamfered trapezoid base)
    const chinTL = addV(-10, 32, 22);
    const chinTR = addV(10, 32, 22);
    const chinBL = addV(-7, 44, 16);
    const chinBR = addV(7, 44, 16);
    const chinBase = addV(0, 48, 14);

    // Jawline & Ear Pods
    const jawAngleL = addV(-32, 24, 6);
    const jawAngleR = addV(32, 24, 6);
    const earTopL = addV(-42, -18, -4);
    const earTopR = addV(42, -18, -4);
    const earBotL = addV(-42, 6, -6);
    const earBotR = addV(42, 6, -6);

    // Back / Crown Base (Depth contour)
    const skullBack = addV(0, -35, -34);
    const occipitalL = addV(-28, -10, -28);
    const occipitalR = addV(28, -10, -28);

    // --- Edges Connection ---
    // Dome contours
    addEdge(topCrown, topCrownL); addEdge(topCrown, topCrownR);
    addEdge(topCrownL, templeL); addEdge(topCrownR, templeR);
    addEdge(templeL, browOuterL); addEdge(templeR, browOuterR);
    addEdge(topCrown, skullBack); addEdge(skullBack, occipitalL); addEdge(skullBack, occipitalR);

    // Forehead Plate
    addEdge(fhTL, fhTR); addEdge(fhTR, fhBR); addEdge(fhBR, fhBL); addEdge(fhBL, fhTL);
    addEdge(topCrown, fhTL); addEdge(topCrown, fhTR);
    addEdge(fhBL, browMidL); addEdge(fhBR, browMidR);

    // Brow Line
    addEdge(browOuterL, browMidL); addEdge(browMidL, browCenter);
    addEdge(browCenter, browMidR); addEdge(browMidR, browOuterR);

    // Left Eye Ring
    addEdge(eL1, eL2); addEdge(eL2, eL3); addEdge(eL3, eL4); addEdge(eL4, eL1);
    // Right Eye Ring
    addEdge(eR1, eR2); addEdge(eR2, eR3); addEdge(eR3, eR4); addEdge(eR4, eR1);

    // Nose & Faceplate Center
    addEdge(browCenter, noseBridge); addEdge(noseBridge, noseLower);
    addEdge(eL4, noseBridge); addEdge(eR4, noseBridge);
    addEdge(noseLower, mouthTL); addEdge(noseLower, mouthTR);

    // Cheeks
    addEdge(browOuterL, cheekTopL); addEdge(browOuterR, cheekTopR);
    addEdge(eL3, cheekTopL); addEdge(eR3, cheekTopR);
    addEdge(cheekTopL, cheekMidL); addEdge(cheekTopR, cheekMidR);
    addEdge(cheekMidL, mouthTL); addEdge(cheekMidR, mouthTR);

    // Mouth
    addEdge(mouthTL, mouthTR); addEdge(mouthTR, mouthBR);
    addEdge(mouthBR, mouthBL); addEdge(mouthBL, mouthTL);

    // Chin Plate
    addEdge(mouthBL, chinTL); addEdge(mouthBR, chinTR);
    addEdge(chinTL, chinTR); addEdge(chinTR, chinBR);
    addEdge(chinBR, chinBase); addEdge(chinBase, chinBL); addEdge(chinBL, chinTL);

    // Jawline & Ears
    addEdge(cheekTopL, earTopL); addEdge(earTopL, earBotL); addEdge(earBotL, jawAngleL);
    addEdge(cheekTopR, earTopR); addEdge(earTopR, earBotR); addEdge(earBotR, jawAngleR);
    addEdge(cheekMidL, jawAngleL); addEdge(cheekMidR, jawAngleR);
    addEdge(jawAngleL, chinBL); addEdge(jawAngleR, chinBR);

    this.helmetVertices = v;
    this.helmetEdges = e;
  }

  /**
   * Builds 3D Full Suit Architecture from Reference 2 (media_1787834207642.png)
   */
  private buildSuitGeometry(): void {
    const v: Point3D[] = [];
    const e: Edge3D[] = [];

    const addV = (x: number, y: number, z: number): number => {
      v.push({ x, y, z });
      return v.length - 1;
    };

    const addEdge = (p1: number, p2: number, color?: string, width?: number) => {
      e.push({ p1, p2, color, width });
    };

    // Head
    const headTop = addV(0, -78, 4);
    const headJaw = addV(0, -62, 8);
    const headL = addV(-9, -70, 4);
    const headR = addV(9, -70, 4);
    addEdge(headTop, headL); addEdge(headL, headJaw); addEdge(headJaw, headR); addEdge(headR, headTop);

    // Neck
    const neckBase = addV(0, -56, 6);
    addEdge(headJaw, neckBase);

    // Shoulders & Pauldrons
    const shL = addV(-34, -50, 4);
    const shR = addV(34, -50, 4);
    const clavL = addV(-16, -52, 10);
    const clavR = addV(16, -52, 10);
    addEdge(neckBase, clavL); addEdge(neckBase, clavR);
    addEdge(clavL, shL); addEdge(clavR, shR);

    // Chestplate
    const chestCenter = addV(0, -38, 14);
    this.chestReactorCenterIdx = chestCenter;
    const pecTL = addV(-14, -44, 12);
    const pecTR = addV(14, -44, 12);
    const pecBL = addV(-18, -32, 12);
    const pecBR = addV(18, -32, 12);

    addEdge(clavL, pecTL); addEdge(clavR, pecTR);
    addEdge(pecTL, chestCenter); addEdge(pecTR, chestCenter);
    addEdge(pecTL, pecBL); addEdge(pecTR, pecBR);
    addEdge(pecBL, chestCenter); addEdge(pecBR, chestCenter);

    // Ribs & Abdomen
    const ab1L = addV(-14, -22, 10);
    const ab1R = addV(14, -22, 10);
    const ab2L = addV(-11, -12, 9);
    const ab2R = addV(11, -12, 9);
    const waistL = addV(-13, -2, 8);
    const waistR = addV(13, -2, 8);

    addEdge(pecBL, ab1L); addEdge(pecBR, ab1R);
    addEdge(chestCenter, ab1L); addEdge(chestCenter, ab1R);
    addEdge(ab1L, ab1R); addEdge(ab1L, ab2L); addEdge(ab1R, ab2R);
    addEdge(ab2L, ab2R); addEdge(ab2L, waistL); addEdge(ab2R, waistR);
    addEdge(waistL, waistR);

    // Arms: Bicep, Elbow, Forearm, Hands
    const elbL = addV(-38, -26, 0);
    const elbR = addV(38, -26, 0);
    const wristL = addV(-44, -2, 4);
    const wristR = addV(44, -2, 4);
    const handL = addV(-48, 12, 6);
    const handR = addV(48, 12, 6);

    addEdge(shL, elbL); addEdge(shR, elbR);
    addEdge(elbL, wristL); addEdge(elbR, wristR);
    addEdge(wristL, handL); addEdge(wristR, handR);

    // Pelvis / Codpiece
    const pelvisCenter = addV(0, 10, 8);
    const hipL = addV(-16, 8, 4);
    const hipR = addV(16, 8, 4);
    addEdge(waistL, hipL); addEdge(waistR, hipR);
    addEdge(hipL, pelvisCenter); addEdge(hipR, pelvisCenter);

    // Thighs & Knees
    const kneeL = addV(-14, 38, 6);
    const kneeR = addV(14, 38, 6);
    addEdge(hipL, kneeL); addEdge(hipR, kneeR);

    // Calves & Boots
    const ankleL = addV(-13, 68, 2);
    const ankleR = addV(13, 68, 2);
    const bootL = addV(-14, 78, 8);
    const bootR = addV(14, 78, 8);

    addEdge(kneeL, ankleL); addEdge(kneeR, ankleR);
    addEdge(ankleL, bootL); addEdge(ankleR, bootR);

    this.suitVertices = v;
    this.suitEdges = e;

    // Diagnostic Hologram Callouts
    this.suitCallouts = [
      { anchorIdx: headTop, label: "CRANIAL HUD", sub: "MK-85 TARGETING", dir: "left" },
      { anchorIdx: chestCenter, label: "ARC REACTOR", sub: "3.2 GJ/S OUTPUT", dir: "right" },
      { anchorIdx: handL, label: "REPULSOR ARRAY", sub: "ARMED // READY", dir: "left" },
      { anchorIdx: kneeR, label: "THRUSTER VECTORS", sub: "STABILIZERS 100%", dir: "right" },
    ];
  }

  private setupInteractions(): void {
    let startX = 0;
    let startY = 0;

    const onPointerDown = (e: PointerEvent) => {
      this.isDragging = true;
      this.isResetting = false;
      this.canvas.setPointerCapture(e.pointerId);
      this.lastMouseX = e.clientX;
      this.lastMouseY = e.clientY;
      startX = e.clientX;
      startY = e.clientY;
      this.lastInteractionTime = Date.now();
      this.canvas.style.cursor = "grabbing";
    };

    const onPointerMove = (e: PointerEvent) => {
      if (!this.isDragging) return;
      const dx = e.clientX - this.lastMouseX;
      const dy = e.clientY - this.lastMouseY;
      this.lastMouseX = e.clientX;
      this.lastMouseY = e.clientY;

      this.yawVel = dx * 0.012;
      this.pitchVel = dy * 0.012;

      this.yaw += this.yawVel;
      this.pitch = Math.max(-1.1, Math.min(1.1, this.pitch + this.pitchVel));
      this.lastInteractionTime = Date.now();
    };

    const onPointerUp = (e: PointerEvent) => {
      if (!this.isDragging) return;
      this.isDragging = false;
      try { this.canvas.releasePointerCapture(e.pointerId); } catch {}
      this.canvas.style.cursor = "grab";
      this.lastInteractionTime = Date.now();
    };

    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const zoomDelta = e.deltaY * -0.0015;
      this.zoom = Math.max(0.65, Math.min(2.3, this.zoom + zoomDelta));
      this.lastInteractionTime = Date.now();
    };

    const onDblClick = () => {
      this.resetView();
    };

    this.canvas.addEventListener("pointerdown", onPointerDown);
    this.canvas.addEventListener("pointermove", onPointerMove);
    this.canvas.addEventListener("pointerup", onPointerUp);
    this.canvas.addEventListener("pointercancel", onPointerUp);
    this.canvas.addEventListener("wheel", onWheel, { passive: false });
    this.canvas.addEventListener("dblclick", onDblClick);
    this.canvas.style.cursor = "grab";
  }

  private handleResize = (): void => {
    this.resize();
  };

  public resize(): void {
    const dpr = window.devicePixelRatio || 1;
    const rect = this.canvas.getBoundingClientRect();
    const width = rect.width || 220;
    const height = rect.height || 140;

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

  private startRenderLoop = (): void => {
    if (!this.isRunning) return;

    const now = Date.now();

    // 1. Smooth reset transition
    if (this.isResetting) {
      this.yaw += (this.targetYaw - this.yaw) * 0.12;
      this.pitch += (this.targetPitch - this.pitch) * 0.12;
      this.zoom += (this.targetZoom - this.zoom) * 0.12;
      if (Math.abs(this.yaw - this.targetYaw) < 0.002 && Math.abs(this.pitch - this.targetPitch) < 0.002) {
        this.yaw = this.targetYaw;
        this.pitch = this.targetPitch;
        this.zoom = this.targetZoom;
        this.isResetting = false;
      }
    } else if (!this.isDragging) {
      // 2. Momentum damping
      this.yaw += this.yawVel;
      this.pitch = Math.max(-1.1, Math.min(1.1, this.pitch + this.pitchVel));
      this.yawVel *= 0.91;
      this.pitchVel *= 0.91;

      // 3. Auto-orbit turntable rotation if idle > 2.0s
      if (now - this.lastInteractionTime > 2000) {
        const autoSpeed = this.state === "thinking" ? 0.024 : 0.008;
        this.yaw += autoSpeed;
      }
    }

    this.render();
    this.animFrameId = requestAnimationFrame(this.startRenderLoop);
  };

  /**
   * Projects a 3D point to 2D screen coordinates with full yaw and pitch rotation
   */
  private projectPoint(pt: Point3D, cx: number, cy: number, scaleFactor: number): { x: number; y: number; z: number } {
    const cosY = Math.cos(this.yaw);
    const sinY = Math.sin(this.yaw);
    const cosP = Math.cos(this.pitch);
    const sinP = Math.sin(this.pitch);

    // Rotate around Y-axis (Yaw)
    const x1 = pt.x * cosY - pt.z * sinY;
    const z1 = pt.x * sinY + pt.z * cosY;

    // Rotate around X-axis (Pitch)
    const y2 = pt.y * cosP - z1 * sinP;
    const z2 = pt.y * sinP + z1 * cosP;

    // Perspective projection with camera distance
    const dist = 280;
    const pScale = (dist / (dist + z2)) * this.zoom * scaleFactor;

    return {
      x: cx + x1 * pScale,
      y: cy + y2 * pScale,
      z: z2,
    };
  }

  private render(): void {
    const rect = this.canvas.getBoundingClientRect();
    const width = rect.width || 220;
    const height = rect.height || 140;
    const cx = width * 0.5;
    const cy = height * 0.5;

    this.ctx.clearRect(0, 0, width, height);
    this.ctx.save();

    // 1. Holographic Vignette Aura
    const auraGrad = this.ctx.createRadialGradient(cx, cy, 0, cx, cy, Math.min(width, height) * 0.55);
    auraGrad.addColorStop(0, "rgba(0, 212, 255, 0.12)");
    auraGrad.addColorStop(0.7, "rgba(0, 140, 255, 0.04)");
    auraGrad.addColorStop(1, "rgba(0, 0, 0, 0)");
    this.ctx.fillStyle = auraGrad;
    this.ctx.beginPath();
    this.ctx.arc(cx, cy, Math.min(width, height) * 0.55, 0, Math.PI * 2);
    this.ctx.fill();

    // 2. Render Selected View Mode
    if (this.viewMode === "helmet") {
      this.renderHelmet(cx, cy);
    } else {
      this.renderSuit(cx, cy);
    }

    // 3. Technical HUD Coordinates Overlay
    this.ctx.font = "7.5px 'Fira Code', 'Roboto Mono', monospace";
    this.ctx.fillStyle = "rgba(0, 212, 255, 0.6)";
    this.ctx.textAlign = "left";
    const degYaw = Math.round(((this.yaw % (Math.PI * 2)) * 180) / Math.PI);
    const degPitch = Math.round((this.pitch * 180) / Math.PI);
    this.ctx.fillText(`3D YAW:${degYaw}° PITCH:${degPitch}° [${this.zoom.toFixed(1)}X]`, 8, height - 8);

    this.ctx.textAlign = "right";
    this.ctx.fillStyle = "rgba(255, 215, 0, 0.75)";
    this.ctx.fillText(this.viewMode === "helmet" ? "HELMET // MK-85" : "ARMOR BLUEPRINT", width - 8, height - 8);

    this.ctx.restore();
  }

  private renderHelmet(cx: number, cy: number): void {
    const scale = 0.95;
    const projected = this.helmetVertices.map((v) => this.projectPoint(v, cx, cy, scale));

    // Sort edges by average depth for wireframe rendering
    this.ctx.lineWidth = 1.1;

    // Draw Edges
    for (const e of this.helmetEdges) {
      const p1 = projected[e.p1];
      const p2 = projected[e.p2];
      const avgZ = (p1.z + p2.z) * 0.5;

      // Depth alpha fading
      const alpha = Math.max(0.18, Math.min(0.9, 0.65 + avgZ / 80));

      this.ctx.beginPath();
      this.ctx.moveTo(p1.x, p1.y);
      this.ctx.lineTo(p2.x, p2.y);
      this.ctx.strokeStyle = e.color || `rgba(0, 212, 255, ${alpha})`;
      this.ctx.stroke();
    }

    // Glowing Eye Optics
    this.renderGlowingEye(projected, this.helmetEyeLeft);
    this.renderGlowingEye(projected, this.helmetEyeRight);
  }

  private renderGlowingEye(projected: { x: number; y: number; z: number }[], indices: number[]): void {
    if (indices.length === 0) return;

    this.ctx.beginPath();
    this.ctx.moveTo(projected[indices[0]].x, projected[indices[0]].y);
    for (let i = 1; i < indices.length; i++) {
      this.ctx.lineTo(projected[indices[i]].x, projected[indices[i]].y);
    }
    this.ctx.closePath();

    // Determine glow color based on state
    let eyeColor = "#00ffff";
    let glowColor = "rgba(0, 255, 255, 0.8)";
    if (this.state === "listening") {
      eyeColor = "#ffd700";
      glowColor = "rgba(255, 215, 0, 0.9)";
    } else if (this.state === "error") {
      eyeColor = "#ff4757";
      glowColor = "rgba(255, 71, 87, 0.9)";
    }

    const eyePulse = 1.0 + this.audioLevel * 1.6;

    this.ctx.save();
    this.ctx.shadowBlur = 10 * eyePulse;
    this.ctx.shadowColor = glowColor;
    this.ctx.fillStyle = eyeColor;
    this.ctx.fill();

    this.ctx.lineWidth = 1.2;
    this.ctx.strokeStyle = "#ffffff";
    this.ctx.stroke();
    this.ctx.restore();
  }

  private renderSuit(cx: number, cy: number): void {
    const scale = 0.72;
    const projected = this.suitVertices.map((v) => this.projectPoint(v, cx, cy, scale));

    // Draw suit wireframe edges
    this.ctx.lineWidth = 1.0;
    for (const e of this.suitEdges) {
      const p1 = projected[e.p1];
      const p2 = projected[e.p2];
      const avgZ = (p1.z + p2.z) * 0.5;
      const alpha = Math.max(0.15, Math.min(0.85, 0.55 + avgZ / 60));

      this.ctx.beginPath();
      this.ctx.moveTo(p1.x, p1.y);
      this.ctx.lineTo(p2.x, p2.y);
      this.ctx.strokeStyle = `rgba(0, 212, 255, ${alpha})`;
      this.ctx.stroke();
    }

    // Glowing Chest Arc Reactor
    const rc = projected[this.chestReactorCenterIdx];
    if (rc) {
      const pulse = 1.0 + this.audioLevel * 1.5;
      const radius = 5.5 * this.zoom * pulse;

      this.ctx.save();
      this.ctx.beginPath();
      this.ctx.arc(rc.x, rc.y, radius, 0, Math.PI * 2);
      this.ctx.fillStyle = "#ffffff";
      this.ctx.shadowBlur = 14 * pulse;
      this.ctx.shadowColor = "#00f5d4";
      this.ctx.fill();

      // Outer reactor ring
      this.ctx.beginPath();
      this.ctx.arc(rc.x, rc.y, radius * 1.7, 0, Math.PI * 2);
      this.ctx.lineWidth = 1.2;
      this.ctx.strokeStyle = "#00d4ff";
      this.ctx.stroke();
      this.ctx.restore();
    }

    // Diagnostic Hologram Callouts (Blueprint Leader Lines)
    this.ctx.font = "6.5px 'Fira Code', 'Roboto Mono', monospace";
    for (const c of this.suitCallouts) {
      const p = projected[c.anchorIdx];
      if (!p) continue;

      const lineLen = c.dir === "left" ? -28 : 28;
      const tagX = p.x + lineLen;
      const tagY = p.y - 12;

      this.ctx.beginPath();
      this.ctx.moveTo(p.x, p.y);
      this.ctx.lineTo(p.x + lineLen * 0.5, tagY);
      this.ctx.lineTo(tagX, tagY);
      this.ctx.lineWidth = 0.7;
      this.ctx.strokeStyle = "rgba(0, 212, 255, 0.65)";
      this.ctx.stroke();

      // Callout Anchor Dot
      this.ctx.beginPath();
      this.ctx.arc(p.x, p.y, 1.8, 0, Math.PI * 2);
      this.ctx.fillStyle = "#00f5d4";
      this.ctx.fill();

      // Label Text
      this.ctx.textAlign = c.dir === "left" ? "right" : "left";
      this.ctx.fillStyle = "#ffffff";
      this.ctx.fillText(c.label, tagX + (c.dir === "left" ? -3 : 3), tagY - 2);

      this.ctx.fillStyle = "rgba(0, 212, 255, 0.75)";
      this.ctx.fillText(c.sub, tagX + (c.dir === "left" ? -3 : 3), tagY + 7);
    }
  }

  public destroy(): void {
    this.stop();
    window.removeEventListener("resize", this.handleResize);
  }
}
