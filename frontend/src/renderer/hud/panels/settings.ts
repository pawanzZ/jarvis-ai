/**
 * Jarvis AI - Settings Drawer Panel Controller
 * Interactive configuration overlay with tabbed settings for Voice, Brain,
 * Activation, Appearance, Face/Eye Tracking, SFX Synthesizer, and Developer Controls.
 */

import { WSClient } from "../../core/ws-client";
import { DEFAULT_SETTINGS, SettingsConfig, JarvisState } from "../../core/types";

export interface SettingsPanelOptions {
  onSettingsChange?: (settings: SettingsConfig) => void;
  onForceState?: (state: JarvisState) => void;
}

export class SettingsPanel {
  private ws: WSClient;
  private drawerEl: HTMLElement;
  private backdropEl: HTMLElement;
  private isOpen = false;
  private settings: SettingsConfig = JSON.parse(JSON.stringify(DEFAULT_SETTINGS));
  private options: SettingsPanelOptions;

  constructor(ws: WSClient, options: SettingsPanelOptions = {}) {
    this.ws = ws;
    this.options = options;

    // Restore cached settings from localStorage if available
    const saved = typeof localStorage !== "undefined" ? localStorage.getItem("jarvis_settings") : null;
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        this.settings = {
          ...this.settings,
          ...parsed,
          voice: { ...this.settings.voice, ...(parsed.voice || {}) },
          brain: { ...this.settings.brain, ...(parsed.brain || {}) },
          activation: { ...this.settings.activation, ...(parsed.activation || {}) },
          appearance: { ...this.settings.appearance, ...(parsed.appearance || {}) },
          vision: { ...this.settings.vision, ...(parsed.vision || {}) },
          sfx: { ...this.settings.sfx, ...(parsed.sfx || {}) },
        };
      } catch (e) {
        console.error("Failed to parse saved settings from localStorage:", e);
      }
    }

    this.drawerEl = document.getElementById("settings-drawer") as HTMLElement;
    this.backdropEl = document.getElementById("settings-backdrop") as HTMLElement;

    if (!this.drawerEl || !this.backdropEl) {
      throw new Error("Settings drawer DOM elements missing");
    }

    this.render();
    this.attachEventListeners();
  }

  public toggle(): void {
    if (this.isOpen) {
      this.close();
    } else {
      this.open();
    }
  }

  public open(): void {
    this.isOpen = true;
    this.drawerEl.classList.add("open");
    this.backdropEl.classList.add("open");
    // Request fresh settings from backend
    this.ws.send({ type: "settings_request" });
  }

  public close(): void {
    this.isOpen = false;
    this.drawerEl.classList.remove("open");
    this.backdropEl.classList.remove("open");
  }

  public updateSettings(partialSettings: Partial<SettingsConfig>): void {
    if (!partialSettings || Object.keys(partialSettings).length === 0) return;
    this.settings = {
      ...this.settings,
      ...partialSettings,
      voice: { ...this.settings.voice, ...(partialSettings.voice || {}) },
      brain: { ...this.settings.brain, ...(partialSettings.brain || {}) },
      activation: { ...this.settings.activation, ...(partialSettings.activation || {}) },
      appearance: { ...this.settings.appearance, ...(partialSettings.appearance || {}) },
      vision: { ...this.settings.vision, ...(partialSettings.vision || {}) },
      sfx: { ...this.settings.sfx, ...(partialSettings.sfx || {}) },
    };
    if (typeof localStorage !== "undefined") {
      try {
        localStorage.setItem("jarvis_settings", JSON.stringify(this.settings));
      } catch (e) {}
    }
    this.populateFormValues();
    if (this.options.onSettingsChange) {
      this.options.onSettingsChange(this.settings);
    }
  }

  public updateVisionTelemetry(data: any): void {
    const statusEl = this.drawerEl.querySelector("#vision-diag-status");
    const attnEl = this.drawerEl.querySelector("#vision-diag-attention");
    const poseEl = this.drawerEl.querySelector("#vision-diag-pose");
    const gazeEl = this.drawerEl.querySelector("#vision-diag-gaze");

    const detected = data.detected ?? data.face_detected ?? true;
    const attention = data.attention ?? detected;
    const pose = data.head_pose || data.pose;
    const gaze = data.gaze;

    if (statusEl) {
      statusEl.textContent = detected ? "ONLINE // ACTIVE" : "STANDBY // NO FACE";
      (statusEl as HTMLElement).style.color = detected ? "var(--accent-green)" : "var(--accent-gold)";
    }
    if (attnEl) {
      attnEl.textContent = attention ? "ENGAGED (LOOKING AT HUD)" : "DISTRACTED (LOOKING AWAY)";
      (attnEl as HTMLElement).style.color = attention ? "var(--accent-cyan)" : "var(--accent-gold)";
    }
    if (poseEl && pose) {
      const p = typeof pose.pitch === "number" ? pose.pitch.toFixed(1) : "0.0";
      const y = typeof pose.yaw === "number" ? pose.yaw.toFixed(1) : "0.0";
      const r = typeof pose.roll === "number" ? pose.roll.toFixed(1) : "0.0";
      poseEl.textContent = `P: ${p}°  Y: ${y}°  R: ${r}°`;
    }
    if (gazeEl && gaze && Array.isArray(gaze)) {
      const gx = typeof gaze[0] === "number" ? gaze[0].toFixed(2) : "0.50";
      const gy = typeof gaze[1] === "number" ? gaze[1].toFixed(2) : "0.50";
      gazeEl.textContent = `[${gx}, ${gy}]`;
    }
  }

  private render(): void {
    this.drawerEl.innerHTML = `
      <div class="settings-header">
        <div class="settings-title">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="3"></circle>
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
          </svg>
          <span>SYSTEM CONFIGURATION</span>
        </div>
        <button class="settings-close-btn" id="close-drawer-btn" title="Close Panel">✕</button>
      </div>

      <div class="settings-tabs">
        <button class="tab-btn active" data-tab="voice">Voice</button>
        <button class="tab-btn" data-tab="brain">AI Brain</button>
        <button class="tab-btn" data-tab="activation">Activation</button>
        <button class="tab-btn" data-tab="appearance">Appearance</button>
        <button class="tab-btn" data-tab="vision">Vision</button>
        <button class="tab-btn" data-tab="sfx">SFX</button>
        <button class="tab-btn" data-tab="dev">Dev</button>
      </div>

      <div class="settings-body">
        <!-- Voice Tab -->
        <div class="tab-pane active" id="tab-voice">
          <div class="setting-group">
            <label class="setting-label">Speech-to-Text (STT) Plugin</label>
            <select class="setting-select" id="cfg-stt-plugin">
              <option value="whisper_local">Whisper Local (whisper.cpp / mock)</option>
              <option value="faster_whisper">Faster Whisper</option>
              <option value="openai_whisper">OpenAI Whisper Cloud</option>
            </select>
          </div>
          <div class="setting-group">
            <label class="setting-label">Text-to-Speech (TTS) Plugin</label>
            <select class="setting-select" id="cfg-tts-plugin">
              <option value="piper_tts">Piper Local TTS</option>
              <option value="speech_dispatcher">Speech Dispatcher (Linux native)</option>
              <option value="edge_tts">Edge TTS</option>
            </select>
          </div>
          <div class="setting-group">
            <label class="setting-label">Voice Model</label>
            <input type="text" class="setting-input" id="cfg-tts-voice" value="en_GB-alan-medium" />
          </div>
          <div class="setting-group">
            <div class="setting-label">
              <span>Speech Rate</span>
              <span class="slider-val" id="val-tts-rate">1.0x</span>
            </div>
            <div class="slider-container">
              <input type="range" min="0.5" max="2.0" step="0.1" value="1.0" class="setting-slider" id="cfg-tts-rate" />
            </div>
          </div>
        </div>

        <!-- Brain Tab -->
        <div class="tab-pane" id="tab-brain">
          <div class="setting-group">
            <label class="setting-label">LLM Brain Plugin</label>
            <select class="setting-select" id="cfg-llm-plugin">
              <option value="ollama_llm">Ollama Local LLM</option>
              <option value="openai_llm">OpenAI GPT-4o</option>
              <option value="gemini_llm">Google Gemini 2.0</option>
              <option value="anthropic_llm">Anthropic Claude 3.5</option>
            </select>
          </div>
          <div class="setting-group">
            <label class="setting-label">Model Identifier</label>
            <input type="text" class="setting-input" id="cfg-llm-model" value="llama3" />
          </div>
          <div class="setting-group">
            <div class="setting-label">
              <span>Temperature</span>
              <span class="slider-val" id="val-llm-temp">0.7</span>
            </div>
            <div class="slider-container">
              <input type="range" min="0.0" max="1.5" step="0.05" value="0.7" class="setting-slider" id="cfg-llm-temp" />
            </div>
          </div>
          <div class="setting-group">
            <label class="setting-label">System Personality Prompt</label>
            <textarea class="setting-input setting-textarea" id="cfg-system-prompt"></textarea>
          </div>
        </div>

        <!-- Activation Tab -->
        <div class="tab-pane" id="tab-activation">
          <div class="setting-group toggle-row">
            <div>
              <div class="setting-label">Wake Word Activation</div>
              <div class="setting-desc">Trigger Jarvis using vocal hotword</div>
            </div>
            <label class="toggle-switch">
              <input type="checkbox" id="cfg-wakeword-enabled" checked />
              <span class="toggle-slider"></span>
            </label>
          </div>
          <div class="setting-group">
            <label class="setting-label">Wake Phrase</label>
            <input type="text" class="setting-input" id="cfg-wakeword" value="Hey Jarvis" />
          </div>
          <div class="setting-group toggle-row">
            <div>
              <div class="setting-label">Push-to-Talk (PTT)</div>
              <div class="setting-desc">Hold or tap shortcut key to listen</div>
            </div>
            <label class="toggle-switch">
              <input type="checkbox" id="cfg-ptt-enabled" checked />
              <span class="toggle-slider"></span>
            </label>
          </div>
          <div class="setting-group toggle-row">
            <div>
              <div class="setting-label">Double-Clap Detector</div>
              <div class="setting-desc">Acoustic peak interval detection</div>
            </div>
            <label class="toggle-switch">
              <input type="checkbox" id="cfg-clap-enabled" checked />
              <span class="toggle-slider"></span>
            </label>
          </div>
        </div>

        <!-- Appearance Tab -->
        <div class="tab-pane" id="tab-appearance">
          <div class="setting-group">
            <label class="setting-label">Core Visualizer Variant</label>
            <select class="setting-select" id="cfg-core-variant">
              <option value="arc_reactor">Celestial Fusion Core (Sci-Fi)</option>
              <option value="particle_orb">Perplexity 3D Particle Orb</option>
            </select>
          </div>
          <div class="setting-group">
            <label class="setting-label">HUD Theme Preset</label>
            <select class="setting-select" id="cfg-hud-theme">
              <option value="arc">Iron Man ARC (Cyan & Gold)</option>
              <option value="matrix">Matrix Cyber (Phosphor Green)</option>
              <option value="synthwave">Synthwave (Neon Purple & Cyan)</option>
              <option value="stealth">Stealth HUD (Amber & Carbon)</option>
            </select>
          </div>
          <div class="setting-group">
            <div class="setting-label">
              <span>Particle Density</span>
              <span class="slider-val" id="val-particle-density">60</span>
            </div>
            <div class="slider-container">
              <input type="range" min="10" max="150" step="5" value="60" class="setting-slider" id="cfg-particle-density" />
            </div>
          </div>
          <div class="setting-group toggle-row">
            <div>
              <div class="setting-label">CRT Scanline Overlay</div>
              <div class="setting-desc">Retro-futuristic scanlines and vignette</div>
            </div>
            <label class="toggle-switch">
              <input type="checkbox" id="cfg-scanlines" checked />
              <span class="toggle-slider"></span>
            </label>
          </div>
        </div>

        <!-- Vision Tab -->
        <div class="tab-pane" id="tab-vision">
          <div class="setting-group toggle-row">
            <div>
              <div class="setting-label">Face Mesh Tracking</div>
              <div class="setting-desc">MediaPipe head pose & attention tracking</div>
            </div>
            <label class="toggle-switch">
              <input type="checkbox" id="cfg-face-enabled" checked />
              <span class="toggle-slider"></span>
            </label>
          </div>
          <div class="setting-group">
            <label class="setting-label">Camera Device Index</label>
            <input type="number" min="0" max="10" class="setting-input" id="cfg-camera-idx" value="0" />
          </div>

          <!-- Live Vision Telemetry & Attention Testing Card -->
          <div class="setting-group" style="background: rgba(0, 212, 255, 0.04); border: 1px solid rgba(0, 212, 255, 0.25); border-radius: 6px; padding: 14px; margin-top: 4px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
              <span style="font-family: var(--font-mono); font-size: 11px; color: var(--accent-cyan); font-weight: 700; letter-spacing: 1px;">LIVE BIOMETRIC TELEMETRY</span>
              <span id="vision-diag-status" style="font-family: var(--font-mono); font-size: 9px; color: var(--accent-green); letter-spacing: 1px;">ONLINE // ACTIVE</span>
            </div>

            <div style="display: flex; flex-direction: column; gap: 8px; font-family: var(--font-mono); font-size: 10px; color: var(--text-secondary);">
              <div style="display: flex; justify-content: space-between;">
                <span>USER ATTENTION:</span>
                <span id="vision-diag-attention" style="color: var(--accent-cyan); font-weight: 700;">ENGAGED (LOOKING AT HUD)</span>
              </div>
              <div style="display: flex; justify-content: space-between;">
                <span>HEAD POSE:</span>
                <span id="vision-diag-pose" style="color: #ffffff;">P: 0.0°  Y: 0.0°  R: 0.0°</span>
              </div>
              <div style="display: flex; justify-content: space-between;">
                <span>GAZE RETICLE:</span>
                <span id="vision-diag-gaze" style="color: var(--accent-cyan);">[0.50, 0.50]</span>
              </div>
            </div>

            <div style="margin-top: 14px; display: flex; flex-direction: column; gap: 8px;">
              <button class="dev-action-btn" id="btn-test-attention" style="width: 100%; border-color: rgba(0, 212, 255, 0.4); color: var(--accent-cyan);">
                ⚡ TEST ATTENTION SHIFT (TOGGLE ENGAGED / DISTRACTED)
              </button>
              <button class="dev-action-btn" id="btn-launch-vision" style="width: 100%; border-color: rgba(0, 245, 212, 0.5); color: var(--accent-green, #00f5d4);">
                👁 LAUNCH VISION MODE (CENTER STAGE)
              </button>
            </div>

            <div style="margin-top: 10px; font-size: 9px; color: var(--text-muted); line-height: 1.4;">
              Tracks your face presence, head orientation angles, and gaze direction. If looking away from the HUD, attention shifts to DISTRACTED. Press [O] anytime to bring the optical targeting feed to center stage.
            </div>
          </div>
        </div>

        <!-- SFX Tab -->
        <div class="tab-pane" id="tab-sfx">
          <div class="setting-group">
            <div class="setting-label">
              <span>Master SFX Volume</span>
              <span class="slider-val" id="val-sfx-vol">50%</span>
            </div>
            <div class="slider-container">
              <input type="range" min="0" max="1.0" step="0.05" value="0.5" class="setting-slider" id="cfg-sfx-vol" />
            </div>
          </div>
          <div class="setting-group toggle-row">
            <div>
              <div class="setting-label">Power-Up / Wake Sound</div>
              <div class="setting-desc">Synthesized activation sweep</div>
            </div>
            <label class="toggle-switch">
              <input type="checkbox" id="cfg-sfx-powerup" checked />
              <span class="toggle-slider"></span>
            </label>
          </div>
          <div class="setting-group toggle-row">
            <div>
              <div class="setting-label">Acoustic Chimes</div>
              <div class="setting-desc">State acknowledgment tone</div>
            </div>
            <label class="toggle-switch">
              <input type="checkbox" id="cfg-sfx-chimes" checked />
              <span class="toggle-slider"></span>
            </label>
          </div>
          <div class="setting-group toggle-row">
            <div>
              <div class="setting-label">Ambient Listening Hum</div>
              <div class="setting-desc">Subtle 60Hz harmonic backdrop</div>
            </div>
            <label class="toggle-switch">
              <input type="checkbox" id="cfg-sfx-hum" checked />
              <span class="toggle-slider"></span>
            </label>
          </div>
        </div>

        <!-- Dev Controls Tab -->
        <div class="tab-pane" id="tab-dev">
          <div class="setting-group">
            <label class="setting-label">Simulate State Transition</label>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 6px;">
              <button class="status-btn" id="dev-state-idle">IDLE</button>
              <button class="status-btn" id="dev-state-listening">LISTENING</button>
              <button class="status-btn" id="dev-state-thinking">THINKING</button>
              <button class="status-btn" id="dev-state-speaking">SPEAKING</button>
              <button class="status-btn" id="dev-state-error" style="grid-column: span 2;">ERROR</button>
            </div>
          </div>
          <div class="setting-group" style="margin-top: 12px;">
            <label class="setting-label">WebSocket Heartbeat Ping</label>
            <button class="status-btn" id="dev-ping-btn" style="width: 100%;">SEND PING</button>
          </div>
        </div>
      </div>

      <div class="settings-footer">
        <button class="btn-primary" id="save-config-btn">APPLY & SYNC</button>
      </div>
    `;

    this.populateFormValues();
  }

  private attachEventListeners(): void {
    // Backdrop click to close
    this.backdropEl.addEventListener("click", () => this.close());

    // Close button
    const closeBtn = this.drawerEl.querySelector("#close-drawer-btn");
    closeBtn?.addEventListener("click", () => this.close());

    // Tab switching
    const tabBtns = this.drawerEl.querySelectorAll(".tab-btn");
    tabBtns.forEach((btn) => {
      btn.addEventListener("click", () => {
        const targetTab = btn.getAttribute("data-tab");
        if (!targetTab) return;

        tabBtns.forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");

        const panes = this.drawerEl.querySelectorAll(".tab-pane");
        panes.forEach((p) => p.classList.remove("active"));
        const targetPane = this.drawerEl.querySelector(`#tab-${targetTab}`);
        targetPane?.classList.add("active");
      });
    });

    // Slider value labels
    const setupSlider = (sliderId: string, valId: string, format: (v: number) => string) => {
      const slider = this.drawerEl.querySelector(`#${sliderId}`) as HTMLInputElement;
      const valLabel = this.drawerEl.querySelector(`#${valId}`) as HTMLElement;
      if (slider && valLabel) {
        slider.addEventListener("input", () => {
          valLabel.textContent = format(parseFloat(slider.value));
        });
      }
    };

    setupSlider("cfg-tts-rate", "val-tts-rate", (v) => `${v.toFixed(1)}x`);
    setupSlider("cfg-llm-temp", "val-llm-temp", (v) => v.toFixed(2));
    setupSlider("cfg-particle-density", "val-particle-density", (v) => `${Math.round(v)}`);
    setupSlider("cfg-sfx-vol", "val-sfx-vol", (v) => `${Math.round(v * 100)}%`);

    const variantSelect = this.drawerEl.querySelector("#cfg-core-variant") as HTMLSelectElement;
    variantSelect?.addEventListener("change", () => {
      this.collectFormData();
      if (this.options.onSettingsChange) {
        this.options.onSettingsChange(this.settings);
      }
    });

    // Apply & Save button
    const saveBtn = this.drawerEl.querySelector("#save-config-btn") as HTMLButtonElement;
    saveBtn?.addEventListener("click", () => {
      this.collectFormData();
      this.syncWithBackend();
      const origText = saveBtn.textContent;
      saveBtn.textContent = "✓ SAVED & SYNCED!";
      saveBtn.style.background = "#00d4ff";
      saveBtn.style.color = "#0a0a0f";
      setTimeout(() => {
        saveBtn.textContent = origText;
        saveBtn.style.background = "";
        saveBtn.style.color = "";
        this.close();
      }, 600);
    });

    // Dev Controls
    const bindDevState = (btnId: string, state: JarvisState) => {
      const btn = this.drawerEl.querySelector(`#${btnId}`);
      btn?.addEventListener("click", () => {
        if (this.options.onForceState) {
          this.options.onForceState(state);
        }
      });
    };

    bindDevState("dev-state-idle", "idle");
    bindDevState("dev-state-listening", "listening");
    bindDevState("dev-state-thinking", "thinking");
    bindDevState("dev-state-speaking", "speaking");
    bindDevState("dev-state-error", "error");

    const pingBtn = this.drawerEl.querySelector("#dev-ping-btn");
    pingBtn?.addEventListener("click", () => {
      this.ws.send({ type: "ping", data: { timestamp: Date.now() } });
    });

    // Vision Live Testing Listeners
    const testAttnBtn = this.drawerEl.querySelector("#btn-test-attention");
    let testAttentionState = true;
    testAttnBtn?.addEventListener("click", () => {
      testAttentionState = !testAttentionState;
      this.ws.send({
        type: "test_attention",
        attention: testAttentionState,
      });
      const lbl = this.drawerEl.querySelector("#vision-diag-attention");
      if (lbl) {
        lbl.textContent = testAttentionState ? "ENGAGED (LOOKING AT HUD)" : "DISTRACTED (LOOKING AWAY)";
        (lbl as HTMLElement).style.color = testAttentionState ? "var(--accent-cyan)" : "var(--accent-gold)";
      }
    });

    const launchVisionBtn = this.drawerEl.querySelector("#btn-launch-vision");
    launchVisionBtn?.addEventListener("click", () => {
      this.close();
      const toggleVisionBtn = document.getElementById("btn-toggle-vision-mode");
      toggleVisionBtn?.click();
    });
  }

  private populateFormValues(): void {
    const setVal = (id: string, val: any) => {
      const el = this.drawerEl.querySelector(`#${id}`) as HTMLInputElement;
      if (el) el.value = `${val}`;
    };

    const setChecked = (id: string, val: boolean) => {
      const el = this.drawerEl.querySelector(`#${id}`) as HTMLInputElement;
      if (el) el.checked = !!val;
    };

    setVal("cfg-stt-plugin", this.settings.voice.sttPlugin);
    setVal("cfg-tts-plugin", this.settings.voice.ttsPlugin);
    setVal("cfg-tts-voice", this.settings.voice.ttsVoice);
    setVal("cfg-tts-rate", this.settings.voice.ttsRate);
    setVal("cfg-llm-plugin", this.settings.brain.llmPlugin);
    setVal("cfg-llm-model", this.settings.brain.model);
    setVal("cfg-llm-temp", this.settings.brain.temperature);
    setVal("cfg-system-prompt", this.settings.brain.systemPrompt);

    setChecked("cfg-wakeword-enabled", this.settings.activation.wakeWordEnabled);
    setVal("cfg-wakeword", this.settings.activation.wakeWord);
    setChecked("cfg-ptt-enabled", this.settings.activation.pttEnabled);
    setChecked("cfg-clap-enabled", this.settings.activation.clapEnabled);

    setVal("cfg-core-variant", this.settings.appearance.coreVariant || "arc_reactor");
    setVal("cfg-hud-theme", this.settings.appearance.theme);
    setVal("cfg-particle-density", this.settings.appearance.particleDensity);
    setChecked("cfg-scanlines", this.settings.appearance.crtScanlines);

    setChecked("cfg-face-enabled", this.settings.vision.faceTrackingEnabled);
    setVal("cfg-camera-idx", this.settings.vision.cameraIndex);

    setVal("cfg-sfx-vol", this.settings.sfx.masterVolume);
    setChecked("cfg-sfx-powerup", this.settings.sfx.powerUpEnabled);
    setChecked("cfg-sfx-chimes", this.settings.sfx.chimesEnabled);
    setChecked("cfg-sfx-hum", this.settings.sfx.humEnabled);
  }

  private collectFormData(): void {
    const getVal = (id: string) => (this.drawerEl.querySelector(`#${id}`) as HTMLInputElement)?.value;
    const getNum = (id: string) => parseFloat(getVal(id) || "0");
    const getChecked = (id: string) => (this.drawerEl.querySelector(`#${id}`) as HTMLInputElement)?.checked;

    this.settings.voice.sttPlugin = getVal("cfg-stt-plugin") || this.settings.voice.sttPlugin;
    this.settings.voice.ttsPlugin = getVal("cfg-tts-plugin") || this.settings.voice.ttsPlugin;
    this.settings.voice.ttsVoice = getVal("cfg-tts-voice") || this.settings.voice.ttsVoice;
    this.settings.voice.ttsRate = getNum("cfg-tts-rate") || 1.0;

    this.settings.brain.llmPlugin = getVal("cfg-llm-plugin") || this.settings.brain.llmPlugin;
    this.settings.brain.model = getVal("cfg-llm-model") || this.settings.brain.model;
    this.settings.brain.temperature = getNum("cfg-llm-temp") || 0.7;
    this.settings.brain.systemPrompt = getVal("cfg-system-prompt") || this.settings.brain.systemPrompt;

    this.settings.activation.wakeWordEnabled = getChecked("cfg-wakeword-enabled");
    this.settings.activation.wakeWord = getVal("cfg-wakeword") || "Hey Jarvis";
    this.settings.activation.pttEnabled = getChecked("cfg-ptt-enabled");
    this.settings.activation.clapEnabled = getChecked("cfg-clap-enabled");

    this.settings.appearance.coreVariant = (getVal("cfg-core-variant") as any) || "arc_reactor";
    this.settings.appearance.theme = (getVal("cfg-hud-theme") as any) || "arc";
    this.settings.appearance.particleDensity = getNum("cfg-particle-density") || 60;
    this.settings.appearance.crtScanlines = getChecked("cfg-scanlines");

    this.settings.vision.faceTrackingEnabled = getChecked("cfg-face-enabled");
    this.settings.vision.cameraIndex = parseInt(getVal("cfg-camera-idx") || "0", 10);

    this.settings.sfx.masterVolume = getNum("cfg-sfx-vol");
    this.settings.sfx.powerUpEnabled = getChecked("cfg-sfx-powerup");
    this.settings.sfx.chimesEnabled = getChecked("cfg-sfx-chimes");
    this.settings.sfx.humEnabled = getChecked("cfg-sfx-hum");

    if (typeof localStorage !== "undefined") {
      try {
        localStorage.setItem("jarvis_settings", JSON.stringify(this.settings));
      } catch (e) {}
    }

    if (this.options.onSettingsChange) {
      this.options.onSettingsChange(this.settings);
    }
  }

  private syncWithBackend(): void {
    // 1. Send complete settings package
    this.ws.send({
      type: "settings_save",
      settings: this.settings,
    });

    // 2. Individual config updates for backward compatibility and fine-grained reactivity
    for (const [ns, values] of Object.entries(this.settings)) {
      if (typeof values === "object" && values !== null) {
        for (const [k, v] of Object.entries(values)) {
          this.ws.send({
            type: "config_update",
            namespace: ns,
            key: k,
            value: v,
          });
        }
      }
    }
  }
}
