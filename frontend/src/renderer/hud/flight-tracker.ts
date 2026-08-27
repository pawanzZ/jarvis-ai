/**
 * Jarvis AI - Tactical Airspace & Real-Time Flight Tracker
 * Renders live aircraft vectors, airway corridors, radar sweep, and flight data blocks.
 * Features:
 * - Airway sector grid with 10NM, 20NM, and 30NM distance rings
 * - Dynamic aircraft flights: STARK-01 (Quinjet), AF-402, UAL-819, BA-117
 * - Vector heading tails, altitude blocks, speed, and destination callouts
 * - Rotating airspace radar sweep beam and ADS-B transponder telemetry
 */

import { JarvisState } from "../core/types";

interface TrackedFlight {
  callsign: string;
  xNorm: number;    // -1.0 to 1.0
  yNorm: number;    // -1.0 to 1.0
  heading: number;  // Radians
  speedKnots: number;
  altitudeFL: number;
  isStark: boolean;
  trail: { x: number; y: number }[];
}

export class FlightTrackerHUD {
  private canvas: HTMLCanvasElement;
  private ctx: CanvasRenderingContext2D;
  private animFrameId: number | null = null;
  private isRunning = false;
  private state: JarvisState = "idle";
  private sweepAngle = 0;
  private flights: TrackedFlight[] = [];
  private audioLevel = 0;

  constructor(canvas: HTMLCanvasElement) {
    this.canvas = canvas;
    const context = canvas.getContext("2d");
    if (!context) throw new Error("Could not get 2D context for FlightTrackerHUD");
    this.ctx = context;

    this.initFlights();
    this.resize();
    window.addEventListener("resize", this.handleResize);
    this.start();
  }

  private initFlights(): void {
    this.flights = [
      {
        callsign: "STARK-01",
        xNorm: -0.35,
        yNorm: 0.15,
        heading: 0.75,
        speedKnots: 540,
        altitudeFL: 410,
        isStark: true,
        trail: [],
      },
      {
        callsign: "AF-402",
        xNorm: 0.55,
        yNorm: -0.45,
        heading: 3.8,
        speedKnots: 480,
        altitudeFL: 360,
        isStark: false,
        trail: [],
      },
      {
        callsign: "UAL-819",
        xNorm: 0.25,
        yNorm: 0.55,
        heading: 2.2,
        speedKnots: 420,
        altitudeFL: 280,
        isStark: false,
        trail: [],
      },
      {
        callsign: "BA-117",
        xNorm: -0.65,
        yNorm: -0.35,
        heading: 5.4,
        speedKnots: 460,
        altitudeFL: 320,
        isStark: false,
        trail: [],
      },
    ];
  }

  private handleResize = (): void => {
    this.resize();
  };

  public resize(): void {
    const dpr = window.devicePixelRatio || 1;
    const rect = this.canvas.getBoundingClientRect();
    const width = rect.width || 240;
    const height = rect.height || 150;

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

  public updateRealFlights(data: any[]): void {
    if (!Array.isArray(data) || data.length === 0) return;

    // Keep the Stark Industries VIP Quinjet flight
    const starkFlight = this.flights.find((f) => f.isStark) || {
      callsign: "STARK-01",
      xNorm: -0.35,
      yNorm: 0.15,
      heading: 0.75,
      speedKnots: 540,
      altitudeFL: 410,
      isStark: true,
      trail: [],
    };

    const updated: TrackedFlight[] = [starkFlight];

    for (const f of data.slice(0, 6)) {
      const existing = this.flights.find((old) => old.callsign === f.callsign);
      updated.push({
        callsign: f.callsign || "AIR-01",
        xNorm: f.xNorm !== undefined ? f.xNorm : (Math.random() * 1.6 - 0.8),
        yNorm: f.yNorm !== undefined ? f.yNorm : (Math.random() * 1.6 - 0.8),
        heading: f.heading !== undefined ? f.heading : Math.random() * Math.PI * 2,
        speedKnots: f.speedKnots || 450,
        altitudeFL: f.altitudeFL || 340,
        isStark: false,
        trail: existing ? existing.trail : [],
      });
    }

    this.flights = updated;
  }

  private startRenderLoop = (): void => {
    if (!this.isRunning) return;

    this.sweepAngle = (this.sweepAngle + 0.028) % (Math.PI * 2);

    // Update flight positions along heading
    for (const flight of this.flights) {
      const step = 0.0014;
      flight.xNorm += Math.cos(flight.heading) * step;
      flight.yNorm += Math.sin(flight.heading) * step;

      // Wrap around bounds
      if (flight.xNorm > 1.1) flight.xNorm = -1.1;
      if (flight.xNorm < -1.1) flight.xNorm = 1.1;
      if (flight.yNorm > 1.1) flight.yNorm = -1.1;
      if (flight.yNorm < -1.1) flight.yNorm = 1.1;
    }

    this.render();
    this.animFrameId = requestAnimationFrame(this.startRenderLoop);
  };

  private render(): void {
    const rect = this.canvas.getBoundingClientRect();
    const width = rect.width || 240;
    const height = rect.height || 150;
    const cx = width * 0.5;
    const cy = height * 0.5;
    const radius = Math.min(width, height) * 0.44;

    this.ctx.clearRect(0, 0, width, height);
    this.ctx.save();

    // 1. Airspace Distance Rings (10NM, 20NM, 30NM)
    const numRings = 3;
    for (let r = 1; r <= numRings; r++) {
      const ringR = (r / numRings) * radius;
      this.ctx.beginPath();
      this.ctx.arc(cx, cy, ringR, 0, Math.PI * 2);
      this.ctx.lineWidth = r === numRings ? 1.2 : 0.6;
      this.ctx.strokeStyle = r === numRings ? "rgba(0, 212, 255, 0.5)" : "rgba(0, 180, 255, 0.16)";
      if (r < numRings) this.ctx.setLineDash([3, 4]);
      this.ctx.stroke();
      this.ctx.setLineDash([]);
    }

    // 2. Airway Corridors (Diagonal Vector Lines)
    this.ctx.lineWidth = 0.6;
    this.ctx.strokeStyle = "rgba(0, 180, 255, 0.12)";
    this.ctx.beginPath();
    this.ctx.moveTo(10, cy - radius * 0.7);
    this.ctx.lineTo(width - 10, cy + radius * 0.7);
    this.ctx.moveTo(10, cy + radius * 0.7);
    this.ctx.lineTo(width - 10, cy - radius * 0.7);
    this.ctx.stroke();

    // 3. Rotating Airspace Radar Sweep Beam
    this.ctx.save();
    const beamAngle = Math.PI * 0.22;
    this.ctx.beginPath();
    this.ctx.moveTo(cx, cy);
    this.ctx.arc(cx, cy, radius, this.sweepAngle - beamAngle, this.sweepAngle);
    this.ctx.closePath();

    const sweepGrad = this.ctx.createRadialGradient(cx, cy, 0, cx, cy, radius);
    sweepGrad.addColorStop(0, "rgba(0, 212, 255, 0.3)");
    sweepGrad.addColorStop(1, "rgba(0, 140, 255, 0.0)");
    this.ctx.fillStyle = sweepGrad;
    this.ctx.fill();
    this.ctx.restore();

    // 4. Render Active Aircraft Flights
    for (const flight of this.flights) {
      const fx = cx + flight.xNorm * radius;
      const fy = cy + flight.yNorm * radius;

      // Maintain breadcrumb trail
      flight.trail.push({ x: fx, y: fy });
      if (flight.trail.length > 8) flight.trail.shift();

      // Draw breadcrumb trail dots
      this.ctx.save();
      for (let i = 0; i < flight.trail.length - 1; i++) {
        const pt = flight.trail[i];
        const alpha = (i / flight.trail.length) * 0.5;
        this.ctx.beginPath();
        this.ctx.arc(pt.x, pt.y, 1.0, 0, Math.PI * 2);
        this.ctx.fillStyle = flight.isStark ? `rgba(255, 215, 0, ${alpha})` : `rgba(0, 245, 212, ${alpha})`;
        this.ctx.fill();
      }

      // Aircraft Chevron Symbol
      this.ctx.translate(fx, fy);
      this.ctx.rotate(flight.heading);

      this.ctx.beginPath();
      this.ctx.moveTo(7, 0);       // Nose
      this.ctx.lineTo(-5, -4);     // Left wing
      this.ctx.lineTo(-3, 0);      // Center tail notch
      this.ctx.lineTo(-5, 4);      // Right wing
      this.ctx.closePath();

      if (flight.isStark) {
        this.ctx.fillStyle = "#ffd700";
        this.ctx.shadowBlur = 6;
        this.ctx.shadowColor = "#ffd700";
      } else {
        this.ctx.fillStyle = "#00d4ff";
        this.ctx.shadowBlur = 4;
        this.ctx.shadowColor = "#00d4ff";
      }
      this.ctx.fill();
      this.ctx.shadowBlur = 0;

      // Heading Vector Line ahead of nose
      this.ctx.beginPath();
      this.ctx.moveTo(7, 0);
      this.ctx.lineTo(16, 0);
      this.ctx.lineWidth = 1.0;
      this.ctx.strokeStyle = flight.isStark ? "rgba(255, 215, 0, 0.8)" : "rgba(0, 212, 255, 0.8)";
      this.ctx.stroke();

      this.ctx.restore();

      // Flight Data Tag Block (Callsign, FL, Speed)
      this.ctx.font = "bold 7px 'Fira Code', 'Roboto Mono', monospace";
      this.ctx.fillStyle = flight.isStark ? "#ffd700" : "#ffffff";
      this.ctx.fillText(flight.callsign, fx + 10, fy - 6);

      this.ctx.font = "6.5px 'Fira Code', 'Roboto Mono', monospace";
      this.ctx.fillStyle = "rgba(0, 212, 255, 0.85)";
      this.ctx.fillText(`FL${flight.altitudeFL}  ${flight.speedKnots}KT`, fx + 10, fy + 4);
    }

    // 5. Airspace Banner & ADS-B Readout
    this.ctx.font = "bold 8px 'Fira Code', 'Roboto Mono', monospace";
    this.ctx.textAlign = "left";
    this.ctx.fillStyle = "rgba(0, 212, 255, 0.85)";
    this.ctx.fillText("AIRSPACE: ADS-B LIVE", 10, height - 8);

    this.ctx.textAlign = "right";
    this.ctx.fillStyle = "rgba(0, 255, 200, 0.85)";
    this.ctx.fillText("SQUAWK: 7700 OK", width - 10, height - 8);

    this.ctx.restore();
  }

  public destroy(): void {
    this.stop();
    window.removeEventListener("resize", this.handleResize);
  }
}
