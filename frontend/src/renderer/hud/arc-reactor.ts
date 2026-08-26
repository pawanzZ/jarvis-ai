/**
 * Jarvis AI - ARC Reactor Core Controller
 * Multi-ring concentric HUD visualizer with audio reactivity,
 * dynamic keyframe animations, segmented arcs, and state modulation.
 */

import { JarvisState } from "../core/types";

export class ArcReactor {
  private container: HTMLElement;
  private core: HTMLElement;
  private outerRing: HTMLElement;
  private middleRing: HTMLElement;
  private innerRing: HTMLElement;
  private state: JarvisState = "idle";
  private currentAudioLevel = 0;
  private targetAudioLevel = 0;
  private animFrameId: number | null = null;
  private lastRippleTime = 0;

  constructor(container: HTMLElement) {
    this.container = container;
    this.container.innerHTML = `
      <div class="reactor-ring reactor-outer"></div>
      <div class="reactor-outer-ticks"></div>
      <div class="reactor-ring reactor-middle"></div>
      <div class="reactor-ring reactor-inner"></div>
      <div class="reactor-core state-idle"></div>
    `;

    this.core = this.container.querySelector(".reactor-core") as HTMLElement;
    this.outerRing = this.container.querySelector(".reactor-outer") as HTMLElement;
    this.middleRing = this.container.querySelector(".reactor-middle") as HTMLElement;
    this.innerRing = this.container.querySelector(".reactor-inner") as HTMLElement;

    this.createRingTicks();
    this.startRenderLoop();
  }

  /**
   * Generates decorative segmented radial ticks around the outer ring.
   */
  private createRingTicks(): void {
    const ticksContainer = this.container.querySelector(".reactor-outer-ticks") as HTMLElement;
    if (!ticksContainer) return;

    const tickCount = 16;
    for (let i = 0; i < tickCount; i++) {
      const angle = (i * 360) / tickCount;
      const tick = document.createElement("div");
      tick.style.position = "absolute";
      tick.style.width = "2px";
      tick.style.height = "6px";
      tick.style.backgroundColor = "rgba(0, 212, 255, 0.4)";
      tick.style.top = "2px";
      tick.style.left = "calc(50% - 1px)";
      tick.style.transformOrigin = "center 158px";
      tick.style.transform = `rotate(${angle}deg)`;
      ticksContainer.appendChild(tick);
    }
  }

  /**
   * Updates current state and adjusts CSS classes and animations.
   */
  public setState(state: JarvisState): void {
    this.state = state;
    this.core.className = "reactor-core";
    this.core.classList.add(`state-${state}`);

    // Update container classes for global theme inheritance
    this.container.parentElement?.classList.remove(
      "state-idle",
      "state-listening",
      "state-thinking",
      "state-speaking",
      "state-error"
    );
    this.container.parentElement?.classList.add(`state-${state}`);

    if (state === "listening" || state === "speaking") {
      this.triggerRipple();
    }
  }

  /**
   * Ingests real-time audio levels [0.0 - 1.0] from microphone or TTS.
   */
  public setAudioLevel(level: number): void {
    this.targetAudioLevel = Math.max(0, Math.min(1, level));

    // When audio level spikes, emit an expanding acoustic ripple
    const now = performance.now();
    if (this.targetAudioLevel > 0.4 && now - this.lastRippleTime > 300) {
      this.triggerRipple();
      this.lastRippleTime = now;
    }
  }

  /**
   * Creates an acoustic shockwave ripple expanding from the core.
   */
  public triggerRipple(): void {
    const ripple = document.createElement("div");
    ripple.className = "reactor-ripple";

    if (this.state === "thinking") {
      ripple.style.borderColor = "var(--accent-amber)";
    } else if (this.state === "error") {
      ripple.style.borderColor = "var(--accent-red)";
    }

    this.container.appendChild(ripple);

    // Clean up after animation finishes
    setTimeout(() => {
      if (ripple.parentElement === this.container) {
        this.container.removeChild(ripple);
      }
    }, 1200);
  }

  /**
   * Continuous render loop for smooth audio level lerping and micro-transforms.
   */
  private startRenderLoop = (): void => {
    // Exponential smoothing for audio level
    this.currentAudioLevel += (this.targetAudioLevel - this.currentAudioLevel) * 0.2;

    if (this.state === "speaking" || this.state === "listening") {
      const scale = 1.0 + this.currentAudioLevel * 0.35;
      const glow = 25 + this.currentAudioLevel * 50;
      this.core.style.transform = `scale(${scale.toFixed(3)})`;
      this.core.style.boxShadow = `0 0 ${glow}px var(--accent-cyan), 0 0 ${glow * 2}px rgba(0, 212, 255, 0.6)`;
    } else {
      this.core.style.transform = "";
    }

    this.animFrameId = requestAnimationFrame(this.startRenderLoop);
  };

  /**
   * Cleanup resources when unmounted.
   */
  public destroy(): void {
    if (this.animFrameId !== null) {
      cancelAnimationFrame(this.animFrameId);
      this.animFrameId = null;
    }
  }
}
