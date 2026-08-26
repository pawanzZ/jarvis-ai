/**
 * Jarvis AI - Zero-Dependency Procedural Web Audio SFX Synthesizer
 * Generates Iron Man HUD soundscapes purely through mathematical synthesis
 * (sawtooth sweeps, harmonic chords, square buzzes, and continuous filtered hums)
 * without any external audio asset dependencies.
 */

import { JarvisState } from "../core/types";

export class SFXSynthesizer {
  private ctx: AudioContext | null = null;
  private masterGain: GainNode | null = null;
  private humOsc: OscillatorNode | null = null;
  private humGain: GainNode | null = null;
  private volume = 0.5;
  private enabled = true;

  constructor(initialVolume = 0.5) {
    this.volume = initialVolume;
  }

  /**
   * Lazy-initializes AudioContext upon user interaction.
   */
  private ensureContext(): AudioContext | null {
    if (!this.enabled) return null;

    if (!this.ctx) {
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      if (!AudioCtx) {
        console.warn("Web Audio API not supported in this environment");
        return null;
      }
      this.ctx = new AudioCtx();
      this.masterGain = this.ctx.createGain();
      this.masterGain.gain.setValueAtTime(this.volume, this.ctx.currentTime);
      this.masterGain.connect(this.ctx.destination);
    }

    if (this.ctx.state === "suspended") {
      this.ctx.resume().catch((err) => console.warn("AudioContext resume failed:", err));
    }

    return this.ctx;
  }

  public setVolume(vol: number): void {
    this.volume = Math.max(0, Math.min(1, vol));
    if (this.masterGain && this.ctx) {
      this.masterGain.gain.setValueAtTime(this.volume, this.ctx.currentTime);
    }
  }

  public setEnabled(enabled: boolean): void {
    this.enabled = enabled;
    if (!enabled) {
      this.stopListeningHum();
    }
  }

  /**
   * Power-up activation acoustic sweep (100Hz -> 850Hz).
   */
  public powerUp(): void {
    const ctx = this.ensureContext();
    if (!ctx || !this.masterGain) return;

    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    const filter = ctx.createBiquadFilter();

    filter.type = "lowpass";
    filter.frequency.setValueAtTime(1500, ctx.currentTime);

    osc.type = "sawtooth";
    osc.frequency.setValueAtTime(120, ctx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(880, ctx.currentTime + 0.35);

    gain.gain.setValueAtTime(0.4, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.5);

    osc.connect(filter);
    filter.connect(gain);
    gain.connect(this.masterGain);

    osc.start(ctx.currentTime);
    osc.stop(ctx.currentTime + 0.52);

    // Complementary high chime burst
    setTimeout(() => this.chime(), 200);
  }

  /**
   * Power-down deactivation sweep (850Hz -> 90Hz).
   */
  public powerDown(): void {
    const ctx = this.ensureContext();
    if (!ctx || !this.masterGain) return;

    this.stopListeningHum();

    const osc = ctx.createOscillator();
    const gain = ctx.createGain();

    osc.type = "sawtooth";
    osc.frequency.setValueAtTime(800, ctx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(90, ctx.currentTime + 0.45);

    gain.gain.setValueAtTime(0.35, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.48);

    osc.connect(gain);
    gain.connect(this.masterGain);

    osc.start(ctx.currentTime);
    osc.stop(ctx.currentTime + 0.5);
  }

  /**
   * Dual-harmonic acknowledgment chime (880Hz A5 + 1320Hz E6).
   */
  public chime(): void {
    const ctx = this.ensureContext();
    if (!ctx || !this.masterGain) return;

    const t = ctx.currentTime;

    [880, 1320].forEach((freq, idx) => {
      if (!ctx || !this.masterGain) return;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = "sine";
      osc.frequency.setValueAtTime(freq, t);

      gain.gain.setValueAtTime(0.25 / (idx + 1), t);
      gain.gain.exponentialRampToValueAtTime(0.001, t + 0.3);

      osc.connect(gain);
      gain.connect(this.masterGain);

      osc.start(t);
      osc.stop(t + 0.32);
    });
  }

  /**
   * Alert error buzz (filtered harsh square sweep).
   */
  public errorBuzz(): void {
    const ctx = this.ensureContext();
    if (!ctx || !this.masterGain) return;

    const t = ctx.currentTime;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    const filter = ctx.createBiquadFilter();

    filter.type = "bandpass";
    filter.frequency.setValueAtTime(350, t);
    filter.Q.setValueAtTime(3, t);

    osc.type = "square";
    osc.frequency.setValueAtTime(220, t);
    osc.frequency.exponentialRampToValueAtTime(80, t + 0.35);

    gain.gain.setValueAtTime(0.4, t);
    gain.gain.exponentialRampToValueAtTime(0.001, t + 0.38);

    osc.connect(filter);
    filter.connect(gain);
    gain.connect(this.masterGain);

    osc.start(t);
    osc.stop(t + 0.4);
  }

  /**
   * Continuous low-frequency listening hum (60Hz sine + sub-oscillator).
   */
  public startListeningHum(): void {
    if (this.humOsc) return; // Already running

    const ctx = this.ensureContext();
    if (!ctx || !this.masterGain) return;

    this.humOsc = ctx.createOscillator();
    this.humGain = ctx.createGain();

    this.humOsc.type = "sine";
    this.humOsc.frequency.setValueAtTime(60, ctx.currentTime);

    this.humGain.gain.setValueAtTime(0.001, ctx.currentTime);
    this.humGain.gain.linearRampToValueAtTime(0.08, ctx.currentTime + 0.2);

    this.humOsc.connect(this.humGain);
    this.humGain.connect(this.masterGain);

    this.humOsc.start();
  }

  public stopListeningHum(): void {
    if (this.humOsc && this.humGain && this.ctx) {
      const t = this.ctx.currentTime;
      this.humGain.gain.linearRampToValueAtTime(0.0001, t + 0.15);
      setTimeout(() => {
        try {
          this.humOsc?.stop();
          this.humOsc?.disconnect();
          this.humGain?.disconnect();
        } catch {
          // Ignore already stopped
        }
        this.humOsc = null;
        this.humGain = null;
      }, 160);
    }
  }

  /**
   * High-frequency micro-clicks / processing whirr for thinking state.
   */
  public thinkingWhirr(): void {
    const ctx = this.ensureContext();
    if (!ctx || !this.masterGain) return;

    const t = ctx.currentTime;
    for (let i = 0; i < 3; i++) {
      const clickTime = t + i * 0.08;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = "triangle";
      osc.frequency.setValueAtTime(2400 + i * 300, clickTime);

      gain.gain.setValueAtTime(0.12, clickTime);
      gain.gain.exponentialRampToValueAtTime(0.001, clickTime + 0.03);

      osc.connect(gain);
      gain.connect(this.masterGain);

      osc.start(clickTime);
      osc.stop(clickTime + 0.035);
    }
  }

  /**
   * Automatically dispatches sound for state transitions.
   */
  public playStateSound(state: JarvisState): void {
    switch (state) {
      case "listening":
        this.powerUp();
        this.startListeningHum();
        break;
      case "thinking":
        this.stopListeningHum();
        this.thinkingWhirr();
        break;
      case "speaking":
        this.stopListeningHum();
        this.chime();
        break;
      case "error":
        this.stopListeningHum();
        this.errorBuzz();
        break;
      case "idle":
      default:
        this.stopListeningHum();
        break;
    }
  }
}
