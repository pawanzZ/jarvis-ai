/**
 * Jarvis AI - 3D Holographic Spinning Planetary Globe
 * Inspired by Tony Stark's global orbital holographic displays.
 * Features:
 * - 3D perspective wireframe meridians with 23.5-degree axial inclination
 * - Procedural continent dot-matrix points rotating across spherical coordinates
 * - Orbiting satellites circling along inclined orbital planes with pulsing beacon nodes
 * - Great-circle flight/telemetry trajectory arcs with traveling energy pulses
 * - Twilight atmospheric limb glow and real-time planetary coordinate telemetry
 */

import { JarvisState } from "../core/types";

interface GlobeSatellite {
  orbitRadius: number;
  inclination: number; // Tilt angle in radians
  speed: number;
  angle: number;
  label: string;
}

interface TrajectoryArc {
  lat1: number;
  lon1: number;
  lat2: number;
  lon2: number;
  progress: number;
  speed: number;
}

export class SpinningGlobe {
  private canvas: HTMLCanvasElement;
  private ctx: CanvasRenderingContext2D;
  private animFrameId: number | null = null;
  private isRunning = false;
  private state: JarvisState = "idle";
  private rotationAngle = 0;
  private axialTilt = 23.5 * (Math.PI / 180); // Earth axial tilt ~23.5 degrees
  private radius = 54;
  private audioLevel = 0;

  // Continent stardust points (lat, lon in radians)
  private landPoints: { lat: number; lon: number }[] = [];
  private satellites: GlobeSatellite[] = [];
  private trajectoryArcs: TrajectoryArc[] = [];

  constructor(canvas: HTMLCanvasElement) {
    this.canvas = canvas;
    const context = canvas.getContext("2d");
    if (!context) throw new Error("Could not get 2D context for SpinningGlobe");
    this.ctx = context;

    this.initLandmassPoints();
    this.initSatellites();
    this.initArcs();
    this.resize();
    window.addEventListener("resize", this.handleResize);
    this.start();
  }

  private initLandmassPoints(): void {
    // Generate approximate continental point clusters
    this.landPoints = [];

    // Helper to generate a clustered landmass
    const addLandmass = (centerLat: number, centerLon: number, spreadLat: number, spreadLon: number, count: number) => {
      for (let i = 0; i < count; i++) {
        const u = (Math.random() - 0.5) * spreadLat;
        const v = (Math.random() - 0.5) * spreadLon;
        this.landPoints.push({
          lat: (centerLat + u) * (Math.PI / 180),
          lon: (centerLon + v) * (Math.PI / 180),
        });
      }
    };

    // North America
    addLandmass(40, -100, 25, 45, 65);
    // South America
    addLandmass(-15, -60, 35, 25, 55);
    // Europe
    addLandmass(50, 15, 20, 30, 50);
    // Africa
    addLandmass(5, 20, 35, 30, 70);
    // Asia
    addLandmass(45, 90, 30, 60, 95);
    // Australia
    addLandmass(-25, 135, 20, 25, 35);
  }

  private initSatellites(): void {
    this.satellites = [
      { orbitRadius: 66, inclination: 0.45, speed: 0.018, angle: 0.0, label: "SAT-1" },
      { orbitRadius: 72, inclination: -0.65, speed: -0.014, angle: 1.8, label: "SAT-2" },
      { orbitRadius: 62, inclination: 0.95, speed: 0.022, angle: 3.5, label: "ISS" },
    ];
  }

  private initArcs(): void {
    this.trajectoryArcs = [
      // New York -> London
      { lat1: 40.7 * (Math.PI / 180), lon1: -74.0 * (Math.PI / 180), lat2: 51.5 * (Math.PI / 180), lon2: -0.1 * (Math.PI / 180), progress: 0.0, speed: 0.012 },
      // London -> Tokyo
      { lat1: 51.5 * (Math.PI / 180), lon1: -0.1 * (Math.PI / 180), lat2: 35.6 * (Math.PI / 180), lon2: 139.6 * (Math.PI / 180), progress: 0.35, speed: 0.009 },
      // San Francisco -> Sydney
      { lat1: 37.7 * (Math.PI / 180), lon1: -122.4 * (Math.PI / 180), lat2: -33.8 * (Math.PI / 180), lon2: 151.2 * (Math.PI / 180), progress: 0.7, speed: 0.010 },
    ];
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
  }

  public setAudioLevel(level: number): void {
    this.audioLevel = Math.max(0, Math.min(1, level));
  }

  private startRenderLoop = (): void => {
    if (!this.isRunning) return;

    let rotSpeed = 0.008;
    if (this.state === "listening") rotSpeed = 0.014;
    else if (this.state === "thinking") rotSpeed = 0.035;
    else if (this.state === "speaking") rotSpeed = 0.018;

    this.rotationAngle += rotSpeed;

    // Advance satellites
    for (const sat of this.satellites) {
      sat.angle = (sat.angle + sat.speed) % (Math.PI * 2);
    }

    // Advance trajectory pulse arcs
    for (const arc of this.trajectoryArcs) {
      arc.progress = (arc.progress + arc.speed) % 1.0;
    }

    this.render();
    this.animFrameId = requestAnimationFrame(this.startRenderLoop);
  };

  /**
   * 3D Sphere projection with axial tilt
   */
  private project3D(lat: number, lon: number, r: number, cx: number, cy: number): { x: number; y: number; z: number; visible: boolean } {
    // Spherical coordinates
    const worldLon = lon + this.rotationAngle;
    const x0 = r * Math.cos(lat) * Math.sin(worldLon);
    const y0 = -r * Math.sin(lat);
    const z0 = r * Math.cos(lat) * Math.cos(worldLon);

    // Apply axial tilt rotation around X-axis
    const cosTilt = Math.cos(this.axialTilt);
    const sinTilt = Math.sin(this.axialTilt);

    const x = x0;
    const y = y0 * cosTilt - z0 * sinTilt;
    const z = y0 * sinTilt + z0 * cosTilt;

    return {
      x: cx + x,
      y: cy + y,
      z: z,
      visible: z > -r * 0.1, // Front hemisphere
    };
  }

  private render(): void {
    const rect = this.canvas.getBoundingClientRect();
    const width = rect.width || 280;
    const height = rect.height || 180;
    const cx = width * 0.5;
    const cy = height * 0.5;
    const r = this.radius + this.audioLevel * 6;

    this.ctx.clearRect(0, 0, width, height);

    // 1. Atmospheric Limb Glow (Soft outer aura)
    const limbGrad = this.ctx.createRadialGradient(cx, cy, r * 0.85, cx, cy, r * 1.35);
    limbGrad.addColorStop(0, "rgba(0, 212, 255, 0.22)");
    limbGrad.addColorStop(0.5, "rgba(0, 140, 255, 0.08)");
    limbGrad.addColorStop(1, "rgba(0, 0, 0, 0)");

    this.ctx.beginPath();
    this.ctx.arc(cx, cy, r * 1.35, 0, Math.PI * 2);
    this.ctx.fillStyle = limbGrad;
    this.ctx.fill();

    // 2. Base Wireframe Meridians (Latitude & Longitude)
    this.ctx.save();
    this.ctx.lineWidth = 0.8;

    // Latitude Parallels
    const latitudes = [-50, -25, 0, 25, 50];
    for (const degLat of latitudes) {
      const latRad = degLat * (Math.PI / 180);
      this.ctx.beginPath();
      let first = true;
      for (let lonDeg = 0; lonDeg <= 360; lonDeg += 10) {
        const p = this.project3D(latRad, lonDeg * (Math.PI / 180), r, cx, cy);
        if (p.visible) {
          if (first) {
            this.ctx.moveTo(p.x, p.y);
            first = false;
          } else {
            this.ctx.lineTo(p.x, p.y);
          }
        } else {
          first = true;
        }
      }
      this.ctx.strokeStyle = degLat === 0 ? "rgba(0, 212, 255, 0.45)" : "rgba(0, 180, 255, 0.18)";
      this.ctx.stroke();
    }

    // Longitude Meridians
    const longitudes = [0, 45, 90, 135, 180, 225, 270, 315];
    for (const degLon of longitudes) {
      const lonRad = degLon * (Math.PI / 180);
      this.ctx.beginPath();
      let first = true;
      for (let latDeg = -80; latDeg <= 80; latDeg += 8) {
        const p = this.project3D(latDeg * (Math.PI / 180), lonRad, r, cx, cy);
        if (p.visible) {
          if (first) {
            this.ctx.moveTo(p.x, p.y);
            first = false;
          } else {
            this.ctx.lineTo(p.x, p.y);
          }
        } else {
          first = true;
        }
      }
      this.ctx.strokeStyle = "rgba(0, 180, 255, 0.16)";
      this.ctx.stroke();
    }
    this.ctx.restore();

    // 3. Continent Stardust Points
    this.ctx.save();
    for (const pt of this.landPoints) {
      const p = this.project3D(pt.lat, pt.lon, r, cx, cy);
      if (p.visible) {
        const depthAlpha = Math.max(0.15, (p.z + r) / (2 * r));
        this.ctx.beginPath();
        this.ctx.arc(p.x, p.y, 1.2, 0, Math.PI * 2);
        this.ctx.fillStyle = `rgba(0, 245, 212, ${depthAlpha * 0.9})`;
        this.ctx.fill();
      }
    }
    this.ctx.restore();

    // 4. Great-Circle Trajectory Arcs with Traveling Light Packets
    this.ctx.save();
    for (const arc of this.trajectoryArcs) {
      const p1 = this.project3D(arc.lat1, arc.lon1, r, cx, cy);
      const p2 = this.project3D(arc.lat2, arc.lon2, r, cx, cy);

      if (p1.visible || p2.visible) {
        // Interpolate along arc
        const midLat = (arc.lat1 + arc.lat2) * 0.5;
        const midLon = (arc.lon1 + arc.lon2) * 0.5;
        const pMid = this.project3D(midLat, midLon, r * 1.15, cx, cy);

        // Curve trajectory
        this.ctx.beginPath();
        this.ctx.moveTo(p1.x, p1.y);
        this.ctx.quadraticCurveTo(pMid.x, pMid.y, p2.x, p2.y);
        this.ctx.lineWidth = 1.2;
        this.ctx.strokeStyle = "rgba(0, 212, 255, 0.35)";
        this.ctx.stroke();

        // Traveling Light Packet
        const t = arc.progress;
        const packetX = (1 - t) * (1 - t) * p1.x + 2 * (1 - t) * t * pMid.x + t * t * p2.x;
        const packetY = (1 - t) * (1 - t) * p1.y + 2 * (1 - t) * t * pMid.y + t * t * p2.y;

        this.ctx.beginPath();
        this.ctx.arc(packetX, packetY, 2.5, 0, Math.PI * 2);
        this.ctx.fillStyle = "#ffffff";
        this.ctx.shadowBlur = 6;
        this.ctx.shadowColor = "#00ffff";
        this.ctx.fill();
        this.ctx.shadowBlur = 0;
      }
    }
    this.ctx.restore();

    // 5. Orbiting Satellites on Inclined Orbital Rings
    this.ctx.save();
    for (const sat of this.satellites) {
      const satX0 = sat.orbitRadius * Math.cos(sat.angle);
      const satY0 = sat.orbitRadius * Math.sin(sat.angle) * Math.sin(sat.inclination);
      const satZ0 = sat.orbitRadius * Math.sin(sat.angle) * Math.cos(sat.inclination);

      // Tilt
      const satY = satY0 * Math.cos(this.axialTilt) - satZ0 * Math.sin(this.axialTilt);
      const satZ = satY0 * Math.sin(this.axialTilt) + satZ0 * Math.cos(this.axialTilt);

      const sx = cx + satX0;
      const sy = cy + satY;
      const isFront = satZ > 0;

      // Draw Orbit Ellipse
      this.ctx.beginPath();
      this.ctx.ellipse(cx, cy, sat.orbitRadius, sat.orbitRadius * 0.45, sat.inclination, 0, Math.PI * 2);
      this.ctx.lineWidth = 0.6;
      this.ctx.strokeStyle = "rgba(0, 212, 255, 0.18)";
      this.ctx.stroke();

      // Satellite Beacon Node
      this.ctx.beginPath();
      this.ctx.arc(sx, sy, isFront ? 3.0 : 1.8, 0, Math.PI * 2);
      this.ctx.fillStyle = isFront ? "#ffd700" : "rgba(255, 215, 0, 0.4)";
      this.ctx.shadowBlur = isFront ? 6 : 0;
      this.ctx.shadowColor = "#ffd700";
      this.ctx.fill();
      this.ctx.shadowBlur = 0;

      if (isFront) {
        this.ctx.font = "7px 'Fira Code', 'Roboto Mono', monospace";
        this.ctx.fillStyle = "rgba(255, 215, 0, 0.9)";
        this.ctx.fillText(sat.label, sx + 5, sy - 2);
      }
    }
    this.ctx.restore();

    // 6. Real-Time Telemetry Coordinates Banner
    const currentLonDeg = (((this.rotationAngle * (180 / Math.PI)) % 360) - 180).toFixed(1);
    this.ctx.font = "bold 9px 'Fira Code', 'Roboto Mono', monospace";
    this.ctx.textAlign = "left";
    this.ctx.fillStyle = "rgba(0, 212, 255, 0.85)";
    this.ctx.fillText(`ORBIT: GEO-SYNC`, 12, height - 10);

    this.ctx.textAlign = "right";
    this.ctx.fillStyle = "rgba(0, 245, 212, 0.85)";
    this.ctx.fillText(`LON: ${currentLonDeg}°`, width - 12, height - 10);
  }

  public destroy(): void {
    this.stop();
    window.removeEventListener("resize", this.handleResize);
  }
}
