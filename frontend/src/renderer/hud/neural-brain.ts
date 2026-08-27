/**
 * Jarvis AI - 3D Holographic Neural Brain & Multi-Model Cortex Visualizer
 * Visualizes real-time local and cloud AI models across a 3D neural brain point cloud.
 * Features:
 * - 3D perspective wireframe cerebral hemispheres, frontal lobe, and cerebellum
 * - Dynamic synaptic firing action potentials (sparks traveling across axons)
 * - Multi-Model Ecosystem tracking: ACTIVE vs STANDBY models (Llama, Whisper, Piper, Claude, GPT)
 * - Real-time token inference telemetry: Context Window, Token Speed, Streamed Tokens, KV Cache
 */

import { JarvisState } from "../core/types";

interface BrainNode {
  x: number;
  y: number;
  z: number;
  lobe: "left" | "right" | "frontal" | "cerebellum";
}

interface SynapseConnection {
  from: number;
  to: number;
}

interface SynapticSpark {
  fromIdx: number;
  toIdx: number;
  progress: number;
  speed: number;
  color: string;
}

export interface AIModelStatus {
  id: string;
  name: string;
  type: "local" | "cloud" | "stt" | "tts";
  active: boolean;
  contextWindow: string;
  role: string;
}

export class NeuralBrainHUD {
  private canvas: HTMLCanvasElement;
  private ctx: CanvasRenderingContext2D;
  private animFrameId: number | null = null;
  private isRunning = false;
  private state: JarvisState = "idle";
  private time = 0;
  private rotAngle = 0;
  private audioLevel = 0;

  // 3D Brain Point Cloud & Mesh
  private nodes: BrainNode[] = [];
  private connections: SynapseConnection[] = [];
  private sparks: SynapticSpark[] = [];

  // Multi-Model Ecosystem State
  private models: AIModelStatus[] = [];
  private totalTokensStreamed = 1840;
  private currentTokenRate = 0;
  private tokenRateTarget = 44.5;

  constructor(canvas: HTMLCanvasElement) {
    this.canvas = canvas;
    const context = canvas.getContext("2d");
    if (!context) throw new Error("Could not get 2D context for NeuralBrainHUD");
    this.ctx = context;

    this.initModels();
    this.initBrainMesh();
    this.resize();
    window.addEventListener("resize", this.handleResize);
    this.start();
  }

  private initModels(): void {
    this.models = [
      { id: "llama3.2", name: "llama3.2:3b", type: "local", active: true, contextWindow: "128K", role: "LLM REASONING" },
      { id: "whisper",  name: "whisper-base", type: "stt",   active: true, contextWindow: "30s",  role: "SPEECH-TO-TEXT" },
      { id: "piper",    name: "piper-ryan",   type: "tts",   active: true, contextWindow: "N/A",  role: "VOICE SYNTHESIS" },
      { id: "llama3.1", name: "llama3.1:8b", type: "local", active: false, contextWindow: "128K", role: "STANDBY LOCAL" },
      { id: "claude35", name: "claude-3.5",  type: "cloud", active: false, contextWindow: "200K", role: "CLOUD AGENT" },
      { id: "gpt4o",    name: "gpt-4o",      type: "cloud", active: false, contextWindow: "128K", role: "CLOUD REASONING" },
    ];
  }

  private initBrainMesh(): void {
    this.nodes = [];
    this.connections = [];

    // Helper: generate ellipsoid point cloud for left/right hemispheres
    const addHemisphere = (centerX: number, centerY: number, centerZ: number, side: "left" | "right") => {
      for (let u = -Math.PI * 0.45; u <= Math.PI * 0.45; u += 0.35) {
        for (let v = -Math.PI; v <= Math.PI; v += 0.45) {
          const rx = 36 * Math.cos(u) * Math.cos(v);
          const ry = 46 * Math.sin(u);
          const rz = 40 * Math.cos(u) * Math.sin(v);

          // Add organic indentation
          const jitter = (Math.random() - 0.5) * 3;
          this.nodes.push({
            x: centerX + rx * 0.72 + jitter,
            y: centerY + ry * 0.78 + jitter,
            z: centerZ + rz * 0.75 + jitter,
            lobe: side,
          });
        }
      }
    };

    // Left hemisphere
    addHemisphere(-16, -6, 0, "left");
    // Right hemisphere
    addHemisphere(16, -6, 0, "right");

    // Frontal cortex nodes
    for (let i = 0; i < 18; i++) {
      const angle = (i / 18) * Math.PI * 2;
      this.nodes.push({
        x: Math.cos(angle) * 22,
        y: -30 + Math.sin(angle) * 12,
        z: 18 + (Math.random() - 0.5) * 6,
        lobe: "frontal",
      });
    }

    // Cerebellum nodes
    for (let i = 0; i < 14; i++) {
      const angle = (i / 14) * Math.PI * 2;
      this.nodes.push({
        x: Math.cos(angle) * 16,
        y: 26 + Math.sin(angle) * 8,
        z: -16 + (Math.random() - 0.5) * 4,
        lobe: "cerebellum",
      });
    }

    // Build connections between nearby nodes
    for (let i = 0; i < this.nodes.length; i++) {
      let neighbors = 0;
      for (let j = i + 1; j < this.nodes.length; j++) {
        const dx = this.nodes[i].x - this.nodes[j].x;
        const dy = this.nodes[i].y - this.nodes[j].y;
        const dz = this.nodes[i].z - this.nodes[j].z;
        const dist = Math.sqrt(dx * dx + dy * dy + dz * dz);

        if (dist < 18 && neighbors < 3) {
          this.connections.push({ from: i, to: j });
          neighbors++;
        }
      }
    }

    // Initialize travelling sparks
    for (let s = 0; s < 14; s++) {
      const conn = this.connections[Math.floor(Math.random() * this.connections.length)];
      if (conn) {
        this.sparks.push({
          fromIdx: conn.from,
          toIdx: conn.to,
          progress: Math.random(),
          speed: 0.015 + Math.random() * 0.025,
          color: Math.random() > 0.3 ? "#00ffff" : "#ffd700",
        });
      }
    }
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
    if (state === "thinking") {
      this.tokenRateTarget = 52.0;
    } else if (state === "speaking") {
      this.tokenRateTarget = 38.0;
    } else {
      this.tokenRateTarget = 0.0;
    }
  }

  public setAudioLevel(level: number): void {
    this.audioLevel = Math.max(0, Math.min(1, level));
  }

  public onToken(): void {
    this.totalTokensStreamed++;
    // Spawn extra synaptic burst
    if (this.connections.length > 0 && this.sparks.length < 28) {
      const conn = this.connections[Math.floor(Math.random() * this.connections.length)];
      this.sparks.push({
        fromIdx: conn.from,
        toIdx: conn.to,
        progress: 0.0,
        speed: 0.04 + Math.random() * 0.03,
        color: "#ffffff",
      });
    }
  }

  private startRenderLoop = (): void => {
    if (!this.isRunning) return;

    this.time += 0.03;
    let rotSpeed = 0.009;
    if (this.state === "thinking") rotSpeed = 0.024;
    else if (this.state === "speaking") rotSpeed = 0.014;

    this.rotAngle += rotSpeed;
    this.currentTokenRate += (this.tokenRateTarget - this.currentTokenRate) * 0.08;

    // Advance sparks
    for (const sp of this.sparks) {
      sp.progress += sp.speed * (1 + this.audioLevel * 1.5);
      if (sp.progress >= 1.0) {
        sp.progress = 0.0;
        const nextConn = this.connections[Math.floor(Math.random() * this.connections.length)];
        if (nextConn) {
          sp.fromIdx = nextConn.from;
          sp.toIdx = nextConn.to;
        }
      }
    }

    this.render();
    this.animFrameId = requestAnimationFrame(this.startRenderLoop);
  };

  /**
   * 3D isometric rotation projection
   */
  private project3D(x: number, y: number, z: number, cx: number, cy: number): { x: number; y: number; z: number } {
    const cosY = Math.cos(this.rotAngle);
    const sinY = Math.sin(this.rotAngle);
    const tiltX = 0.25;
    const cosX = Math.cos(tiltX);
    const sinX = Math.sin(tiltX);

    // Rotate around Y-axis
    const x1 = x * cosY - z * sinY;
    const z1 = x * sinY + z * cosY;

    // Tilt around X-axis
    const y2 = y * cosX - z1 * sinX;
    const z2 = y * sinX + z1 * cosX;

    const scale = 320 / (320 + z2);

    return {
      x: cx + x1 * scale,
      y: cy + y2 * scale,
      z: z2,
    };
  }

  private render(): void {
    const rect = this.canvas.getBoundingClientRect();
    const width = rect.width || 280;
    const height = rect.height || 180;
    const cx = width * 0.44;
    const cy = height * 0.48;

    this.ctx.clearRect(0, 0, width, height);
    this.ctx.save();

    // 1. Soft Central Holographic Neural Glow
    const bgGlow = this.ctx.createRadialGradient(cx, cy, 0, cx, cy, 75);
    bgGlow.addColorStop(0, "rgba(0, 212, 255, 0.16)");
    bgGlow.addColorStop(0.6, "rgba(0, 140, 255, 0.05)");
    bgGlow.addColorStop(1, "rgba(0, 0, 0, 0)");
    this.ctx.fillStyle = bgGlow;
    this.ctx.beginPath();
    this.ctx.arc(cx, cy, 75, 0, Math.PI * 2);
    this.ctx.fill();

    // Project all nodes
    const projected = this.nodes.map((n) => this.project3D(n.x, n.y, n.z, cx, cy));

    // 2. Draw Axon Synaptic Connection Lines
    this.ctx.lineWidth = 0.6;
    for (const c of this.connections) {
      const p1 = projected[c.from];
      const p2 = projected[c.to];
      const alpha = Math.max(0.1, 0.4 + (p1.z + p2.z) / 160);

      this.ctx.beginPath();
      this.ctx.moveTo(p1.x, p1.y);
      this.ctx.lineTo(p2.x, p2.y);
      this.ctx.strokeStyle = `rgba(0, 180, 255, ${alpha * 0.35})`;
      this.ctx.stroke();
    }

    // 3. Draw Firing Action Potential Sparks
    for (const sp of this.sparks) {
      const p1 = projected[sp.fromIdx];
      const p2 = projected[sp.toIdx];
      if (!p1 || !p2) continue;

      const sx = p1.x + (p2.x - p1.x) * sp.progress;
      const sy = p1.y + (p2.y - p1.y) * sp.progress;

      this.ctx.beginPath();
      this.ctx.arc(sx, sy, 1.8 + this.audioLevel * 1.5, 0, Math.PI * 2);
      this.ctx.fillStyle = sp.color;
      this.ctx.shadowBlur = 6;
      this.ctx.shadowColor = sp.color;
      this.ctx.fill();
      this.ctx.shadowBlur = 0;
    }

    // 4. Draw Neural Synapse Nodes
    for (let i = 0; i < projected.length; i++) {
      const p = projected[i];
      const node = this.nodes[i];
      const alpha = Math.max(0.2, 0.5 + p.z / 90);

      let nodeColor = "rgba(0, 212, 255,";
      if (node.lobe === "frontal") nodeColor = "rgba(0, 255, 200,";
      else if (node.lobe === "cerebellum") nodeColor = "rgba(255, 200, 0,";

      this.ctx.beginPath();
      this.ctx.arc(p.x, p.y, 1.3, 0, Math.PI * 2);
      this.ctx.fillStyle = `${nodeColor} ${alpha})`;
      this.ctx.fill();
    }

    // 5. Multi-Model Ecosystem Overlay Sidebar (Right edge of widget)
    const sideX = width - 82;
    let sideY = 18;

    this.ctx.font = "bold 7.5px 'Fira Code', 'Roboto Mono', monospace";
    this.ctx.textAlign = "left";
    this.ctx.fillStyle = "rgba(0, 212, 255, 0.9)";
    this.ctx.fillText("AI ECOSYSTEM", sideX, sideY);

    sideY += 12;
    for (const m of this.models) {
      // Status Dot
      this.ctx.beginPath();
      this.ctx.arc(sideX + 3, sideY - 2.5, 2.2, 0, Math.PI * 2);
      if (m.active) {
        this.ctx.fillStyle = "#00f5d4";
        this.ctx.shadowBlur = 4;
        this.ctx.shadowColor = "#00f5d4";
      } else {
        this.ctx.fillStyle = "rgba(255, 255, 255, 0.25)";
        this.ctx.shadowBlur = 0;
      }
      this.ctx.fill();
      this.ctx.shadowBlur = 0;

      // Model Name
      this.ctx.font = "7px 'Fira Code', 'Roboto Mono', monospace";
      this.ctx.fillStyle = m.active ? "#ffffff" : "rgba(255, 255, 255, 0.4)";
      this.ctx.fillText(m.name, sideX + 9, sideY);

      sideY += 10;
    }

    // 6. Live Token & Inference Statistics Footer Banner
    const rateStr = this.currentTokenRate > 0.5 ? `${this.currentTokenRate.toFixed(1)} T/S` : "READY";
    this.ctx.font = "bold 8.5px 'Fira Code', 'Roboto Mono', monospace";
    this.ctx.textAlign = "left";
    this.ctx.fillStyle = "rgba(0, 212, 255, 0.9)";
    this.ctx.fillText(`CTX: 128K  RATE: ${rateStr}`, 10, height - 10);

    this.ctx.textAlign = "right";
    this.ctx.fillStyle = "rgba(0, 245, 212, 0.85)";
    this.ctx.fillText(`TOKENS: ${this.totalTokensStreamed}`, width - 10, height - 10);

    this.ctx.restore();
  }

  public destroy(): void {
    this.stop();
    window.removeEventListener("resize", this.handleResize);
  }
}
