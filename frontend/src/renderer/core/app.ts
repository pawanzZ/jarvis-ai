/**
 * Jarvis AI - Master Frontend Coordinator
 * Integrates ARC reactor core, canvas waveform visualizer, particle engine,
 * status bar, transcript streaming, procedural Web Audio SFX, and typed WebSocket client.
 */

import { WSClient } from "./ws-client";
import {
  JarvisState,
  InboundWSMessage,
  StateChangeEvent,
  TranscriptPartialEvent,
  TranscriptStreamEvent,
  TranscriptFinalEvent,
  LLMTokenEvent,
  ResponseCompleteEvent,
  AudioLevelEvent,
  FaceDataEvent,
  PluginLoadedEvent,
  SettingsResponseEvent,
  ConfigUpdatedEvent,
  SystemTelemetryEvent,
  WeatherTelemetryEvent,
  BackendErrorEvent,
  SettingsConfig,
  CoreVisualizerVariant,
} from "./types";
import { ArcReactor } from "../hud/arc-reactor";
import { Waveform } from "../hud/waveform";
import { ParticleSystem } from "../hud/particles";
import { StatusBar } from "../hud/status-bar";
import { TranscriptBar } from "../hud/transcript-bar";
import { SettingsPanel } from "../hud/panels/settings";
import { SystemMonitorHUD } from "../hud/system-monitor";
import { ParticleOrbVisualizer } from "../hud/particle-orb";
import { FusionCoreVisualizer } from "../hud/fusion-core";
import { CyberGauges } from "../hud/cyber-gauges";
import { NeuralBrainHUD } from "../hud/neural-brain";
import { SpinningGlobe } from "../hud/spinning-globe";
import { IronMan3DModelHUD } from "../hud/ironman-3d";
import { CameraHUD } from "../hud/camera-hud";
import { ScriptRunnerHUD } from "../hud/script-runner";
import { FlightTrackerHUD } from "../hud/flight-tracker";
import { SFXSynthesizer } from "../sfx/synthesizer";

export class JarvisApp {
  private ws: WSClient;
  private sfx: SFXSynthesizer;
  private reactor: ArcReactor;
  private fusionCore: FusionCoreVisualizer;
  private orbVisualizer: ParticleOrbVisualizer;
  private currentVariant: CoreVisualizerVariant = "arc_reactor";
  private waveform: Waveform;
  private particles: ParticleSystem;
  private cyberGauges: CyberGauges | null = null;
  private neuralBrain: NeuralBrainHUD | null = null;
  private spinningGlobe: SpinningGlobe | null = null;
  private ironman3D: IronMan3DModelHUD | null = null;
  private cameraHud: CameraHUD | null = null;
  private scriptRunner: ScriptRunnerHUD | null = null;
  private flightTracker: FlightTrackerHUD | null = null;
  private statusBar: StatusBar;
  private transcriptBar: TranscriptBar;
  private settingsPanel: SettingsPanel;
  private systemMonitor: SystemMonitorHUD;
  private state: JarvisState = "idle";
  private isVisionMode = false;
  private activePlugins: Set<string> = new Set();

  constructor() {
    console.log("[JarvisApp] Initializing Iron Man HUD Visualizer...");

    // 1. Initialize procedural audio synthesizer
    this.sfx = new SFXSynthesizer(0.5);

    // 2. Initialize WebSocket Client
    this.ws = new WSClient();

    // 3. Initialize HUD visualizers
    const coreContainer = document.getElementById("core-container");
    if (!coreContainer) throw new Error("Missing #core-container");
    this.reactor = new ArcReactor(coreContainer);

    const fusionCanvas = document.getElementById("fusion-core-canvas") as HTMLCanvasElement;
    if (!fusionCanvas) throw new Error("Missing #fusion-core-canvas");
    this.fusionCore = new FusionCoreVisualizer(fusionCanvas);

    const orbCanvas = document.getElementById("orb-canvas") as HTMLCanvasElement;
    if (!orbCanvas) throw new Error("Missing #orb-canvas");
    this.orbVisualizer = new ParticleOrbVisualizer(orbCanvas);

    const waveformCanvas = document.getElementById("waveform-canvas") as HTMLCanvasElement;
    if (!waveformCanvas) throw new Error("Missing #waveform-canvas");
    this.waveform = new Waveform(waveformCanvas);

    const particleCanvas = document.getElementById("particle-canvas") as HTMLCanvasElement;
    if (!particleCanvas) throw new Error("Missing #particle-canvas");
    this.particles = new ParticleSystem(particleCanvas);

    // 4. Initialize Cyber Futuristic Widgets (Gauges, Tactical Radar, 3D Globe)
    const gaugesCanvas = document.getElementById("cyber-gauges-canvas") as HTMLCanvasElement;
    if (gaugesCanvas) this.cyberGauges = new CyberGauges(gaugesCanvas);

    const brainCanvas = document.getElementById("neural-brain-canvas") as HTMLCanvasElement;
    if (brainCanvas) this.neuralBrain = new NeuralBrainHUD(brainCanvas);

    const globeCanvas = document.getElementById("spinning-globe-canvas") as HTMLCanvasElement;
    if (globeCanvas) this.spinningGlobe = new SpinningGlobe(globeCanvas);

    // 5. Initialize Center Corner Pods (Tony Stark Battle-Station)
    try {
      const ironmanCanvas = document.getElementById("ironman-3d-canvas") as HTMLCanvasElement;
      if (ironmanCanvas) {
        this.ironman3D = new IronMan3DModelHUD(ironmanCanvas);
      }

      const toggleArmorBtn = document.getElementById("btn-toggle-armor-view");
      if (toggleArmorBtn && this.ironman3D) {
        toggleArmorBtn.addEventListener("click", () => {
          const newMode = this.ironman3D?.toggleViewMode();
          toggleArmorBtn.textContent = newMode === "helmet" ? "HELMET" : "ARMOR";
        });
      }
    } catch (err) {
      console.error("[JarvisApp] Failed to initialize IronMan3DModelHUD:", err);
    }

    try {
      const cameraVideo = document.getElementById("hud-camera-video") as HTMLVideoElement;
      const cameraCanvas = document.getElementById("camera-hud-canvas") as HTMLCanvasElement;
      if (cameraVideo && cameraCanvas) this.cameraHud = new CameraHUD(cameraVideo, cameraCanvas);
    } catch (err) {
      console.error("[JarvisApp] Failed to initialize CameraHUD:", err);
    }

    try {
      const scriptContainer = document.querySelector(".hud-corner-pod.pod-bottom-left") as HTMLElement;
      if (scriptContainer) this.scriptRunner = new ScriptRunnerHUD(scriptContainer);
    } catch (err) {
      console.error("[JarvisApp] Failed to initialize ScriptRunnerHUD:", err);
    }

    try {
      const flightCanvas = document.getElementById("flight-tracker-canvas") as HTMLCanvasElement;
      if (flightCanvas) this.flightTracker = new FlightTrackerHUD(flightCanvas);
    } catch (err) {
      console.error("[JarvisApp] Failed to initialize FlightTrackerHUD:", err);
    }

    // 6. Initialize Status & Transcript bars
    const statusBarEl = document.getElementById("status-bar");
    if (!statusBarEl) throw new Error("Missing #status-bar");
    this.statusBar = new StatusBar(statusBarEl, {
      onSettingsClick: () => this.settingsPanel.toggle(),
      onActivateClick: () => this.toggleActivation(),
    });

    const transcriptBarEl = document.getElementById("transcript-bar");
    if (!transcriptBarEl) throw new Error("Missing #transcript-bar");
    this.transcriptBar = new TranscriptBar(transcriptBarEl);

    // 5. Initialize Settings Drawer & System Monitor
    this.settingsPanel = new SettingsPanel(this.ws, {
      onSettingsChange: (newCfg) => this.handleSettingsChange(newCfg),
      onForceState: (state) => this.handleStateTransition(state),
    });
    this.systemMonitor = new SystemMonitorHUD();

    // 6. Setup Event Handlers & Subscriptions
    this.setupWSSubscriptions();
    this.setupKeyboardShortcuts();
    this.setupQuickControls();

    // 7. Load saved Core Visualizer variant preference
    const savedVariant = (localStorage.getItem("jarvis_core_variant") as CoreVisualizerVariant) || "arc_reactor";
    this.setCoreVariant(savedVariant, false);

    // 8. Connect to Python backend
    this.ws.connect();
  }

  private setupWSSubscriptions(): void {
    // Connection & Latency Events
    this.ws.on("connection", (data: { connected: boolean }) => {
      this.statusBar.setConnectionStatus(data.connected);
      if (data.connected) {
        this.ws.requestSettings();
      }
    });

    this.ws.on("latency", (data: { latencyMs: number }) => {
      this.statusBar.setConnectionStatus(true, data.latencyMs);
    });

    // State Change Event
    this.ws.on("state_change", (msg: StateChangeEvent) => {
      const newState = msg.state || msg.data?.state || "idle";
      this.handleStateTransition(newState);
    });

    // Partial Transcripts
    this.ws.on("transcript_partial", (msg: TranscriptPartialEvent) => {
      const text = msg.text || msg.data?.text || "";
      this.transcriptBar.setPartialTranscript(text);
    });

    this.ws.on("transcript_stream", (msg: TranscriptStreamEvent) => {
      const token = msg.token || msg.data?.token || "";
      this.transcriptBar.appendToken(token);
      this.neuralBrain?.onToken();
    });

    // Final Transcripts
    this.ws.on("transcript_final", (msg: TranscriptFinalEvent) => {
      const text = msg.text || msg.data?.text || "";
      const speaker = msg.speaker || msg.data?.speaker || "user";
      this.transcriptBar.setFinalTranscript(text, speaker);
    });

    // LLM Streamed Tokens
    this.ws.on("llm_token", (msg: LLMTokenEvent) => {
      const token = msg.token || msg.data?.token || "";
      this.transcriptBar.appendToken(token);
      this.neuralBrain?.onToken();
    });

    // Response Complete
    this.ws.on("response_complete", (msg: ResponseCompleteEvent) => {
      const fullText = msg.full_text || msg.data?.full_text || "";
      this.transcriptBar.completeResponse(fullText);
    });

    // Real-time Flight Telemetry (OpenSky Network Open API)
    this.ws.on("flight_telemetry", (msg: any) => {
      const flights = msg.data || [];
      this.flightTracker?.updateRealFlights(flights);
    });

    // Audio Level Telemetry
    this.ws.on("audio_level", (msg: AudioLevelEvent) => {
      const level = msg.level !== undefined ? msg.level : msg.data?.level || 0;
      this.waveform.updateLevel(level);
      this.reactor.setAudioLevel(level);
      this.fusionCore?.setAudioLevel(level);
      this.orbVisualizer.setAudioLevel(level);
      this.cyberGauges?.setAudioLevel(level);
      this.neuralBrain?.setAudioLevel(level);
      this.spinningGlobe?.setAudioLevel(level);
      this.ironman3D?.setAudioLevel(level);
      this.cameraHud?.setAudioLevel(level);
      this.flightTracker?.setAudioLevel(level);
    });

    // Face Tracking Telemetry
    this.ws.on("face_data", (msg: FaceDataEvent) => this.handleFaceTelemetry(msg));
    this.ws.on("face_telemetry", (msg: FaceDataEvent) => this.handleFaceTelemetry(msg));

    // Plugin Loaded Event
    this.ws.on("plugin_loaded", (msg: PluginLoadedEvent) => {
      const name = msg.name || msg.data?.name || "";
      if (name) {
        this.activePlugins.add(name);
        this.updatePluginListUI();
      }
    });

    // Settings Response
    this.ws.on("settings_response", (msg: SettingsResponseEvent) => {
      const settings = msg.settings || msg.data?.settings;
      if (settings) {
        this.settingsPanel.updateSettings(settings);
        if (settings.appearance?.coreVariant) {
          this.setCoreVariant(settings.appearance.coreVariant, false);
        }
      }
    });

    // Config Updated
    this.ws.on("config_updated", (msg: ConfigUpdatedEvent) => {
      const namespace = msg.namespace || msg.data?.namespace || "";
      const key = msg.key || msg.data?.key || "";
      const val = msg.value !== undefined ? msg.value : msg.data?.value;
      console.log(`[JarvisApp] Config updated: ${namespace}.${key} =`, val);
      if (namespace === "appearance" && key === "core_variant" && val) {
        this.setCoreVariant(val as CoreVisualizerVariant, false);
      }
    });

    // System Telemetry (Hardware resources, OS, Screen time)
    this.ws.on("system_telemetry", (msg: SystemTelemetryEvent) => {
      const data = msg.data;
      if (data) {
        this.systemMonitor.update(data);
        if (data.cpu && data.cpu.usage_percent !== undefined) {
          this.cyberGauges?.updateTelemetry(data.cpu.usage_percent);
        }
        if (data.weather) {
          this.statusBar.setWeather(data.weather);
        }
        if (data.flights) {
          this.flightTracker?.updateRealFlights(data.flights);
        }
      }
    });

    // Weather & Location Telemetry
    this.ws.on("weather_telemetry", (msg: WeatherTelemetryEvent) => {
      const weather = msg.data;
      if (weather) {
        this.statusBar.setWeather(weather);
      }
    });

    // Backend Errors
    this.ws.on("error", (msg: BackendErrorEvent) => {
      const message = msg.message || msg.data?.message || "Unknown error";
      console.error("[JarvisApp] Backend error:", message);
      this.transcriptBar.setFinalTranscript(`[ERROR] ${message}`, "jarvis");
      this.sfx.errorBuzz();
    });
  }

  private handleStateTransition(newState: JarvisState): void {
    if (this.state === newState) return;

    console.log(`[JarvisApp] State transition: ${this.state} -> ${newState}`);
    this.state = newState;

    document.title = `Jarvis AI [${newState.toUpperCase()}]`;

    // 1. Update visualizers
    this.reactor.setState(newState);
    this.fusionCore?.setState(newState);
    this.orbVisualizer.setState(newState);
    this.waveform.setState(newState);
    this.particles.setState(newState);
    this.cyberGauges?.setState(newState);
    this.neuralBrain?.setState(newState);
    this.spinningGlobe?.setState(newState);
    this.ironman3D?.setState(newState);
    this.cameraHud?.setState(newState);
    this.scriptRunner?.setState(newState);
    this.flightTracker?.setState(newState);
    this.statusBar.setState(newState);
    this.transcriptBar.setState(newState);

    // 2. Play procedural sound effect
    this.sfx.playStateSound(newState);
  }

  /**
   * Switches active core visualizer between Celestial Fusion Core and 3D Particle Orb.
   */
  public setCoreVariant(variant: CoreVisualizerVariant, notify: boolean = true): void {
    this.currentVariant = variant;
    try {
      localStorage.setItem("jarvis_core_variant", variant);
    } catch {
      // Ignored
    }

    const coreContainer = document.getElementById("core-container");
    const fusionCanvas = document.getElementById("fusion-core-canvas");
    const orbCanvas = document.getElementById("orb-canvas");
    const btnReactor = document.getElementById("btn-variant-reactor");
    const btnOrb = document.getElementById("btn-variant-orb");

    if (variant === "particle_orb") {
      coreContainer?.classList.add("inactive-variant");
      fusionCanvas?.classList.add("inactive-variant");
      fusionCanvas?.classList.remove("active-variant");
      orbCanvas?.classList.add("active-variant");
      orbCanvas?.classList.remove("inactive-variant");
      btnReactor?.classList.remove("active");
      btnOrb?.classList.add("active");
      this.fusionCore?.stop();
      this.orbVisualizer.start();
      this.orbVisualizer.setState(this.state);
    } else {
      coreContainer?.classList.add("inactive-variant");
      fusionCanvas?.classList.remove("inactive-variant");
      fusionCanvas?.classList.add("active-variant");
      orbCanvas?.classList.remove("active-variant");
      orbCanvas?.classList.add("inactive-variant");
      btnReactor?.classList.add("active");
      btnOrb?.classList.remove("active");
      this.orbVisualizer.stop();
      this.fusionCore?.start();
      this.fusionCore?.setState(this.state);
    }

    if (notify) {
      this.ws.updateConfig("appearance", "core_variant", variant);
      this.sfx.chime();
    }
  }

  /**
   * Toggles between standard Core Agent Mode and Vision Mode (Center Stage camera targeting feed).
   */
  public toggleVisionMode(): boolean {
    this.setVisionMode(!this.isVisionMode);
    return this.isVisionMode;
  }

  public setVisionMode(enabled: boolean): void {
    this.isVisionMode = enabled;

    const centerArea = document.getElementById("center-area");
    centerArea?.classList.toggle("vision-mode-active", enabled);

    const toggleBtn = document.getElementById("btn-toggle-vision-mode");
    if (toggleBtn) {
      toggleBtn.textContent = enabled ? "CORE MODE" : "VISION MODE";
      toggleBtn.classList.toggle("vision-active", enabled);
    }

    const titleEl = document.getElementById("pod-top-right-title");
    if (titleEl) {
      titleEl.textContent = enabled ? "OPTICAL SENSOR // TARGETING" : "OPTICAL SENSOR 01";
    }

    const statusEl = document.getElementById("pod-top-right-status");
    if (statusEl) {
      statusEl.textContent = enabled ? "LOCK" : "LIVE";
    }

    const quickLabel = document.getElementById("btn-quick-vision-label");
    if (quickLabel) {
      quickLabel.textContent = enabled ? "CORE MODE (O)" : "VISION MODE (O)";
    }

    // Notify camera HUD to expand/collapse targeting reticles & mesh
    this.cameraHud?.setVisionMode(enabled);

    // Audio acoustic feedback
    this.sfx.chime();

    // Broadcast over WebSocket to backend
    this.ws.send({ type: "vision_mode", enabled });

    // Show tactical feedback in transcript bar
    this.transcriptBar.setFinalTranscript(
      enabled
        ? "Optical neural visual input engaged. Consuming real-time spatial and facial telemetry."
        : "Optical neural visual input disengaged. Returning to central reactor core.",
      "jarvis"
    );
  }

  private handleFaceTelemetry(msg: FaceDataEvent): void {
    const detected = msg.face_detected !== undefined
      ? msg.face_detected
      : msg.data?.detected !== undefined
      ? msg.data.detected
      : true;

    const attention = msg.attention !== undefined
      ? msg.attention
      : msg.data?.attention !== undefined
      ? msg.data.attention
      : detected;

    this.statusBar.setAttention(attention, detected);

    // Update telemetry panel values
    const pose = msg.pose || msg.data?.pose || msg.head_pose || msg.data?.head_pose;
    if (pose) {
      const pitchEl = document.getElementById("telem-pitch");
      const yawEl = document.getElementById("telem-yaw");
      const rollEl = document.getElementById("telem-roll");
      if (pitchEl) pitchEl.textContent = `${pose.pitch.toFixed(1)}°`;
      if (yawEl) yawEl.textContent = `${pose.yaw.toFixed(1)}°`;
      if (rollEl) rollEl.textContent = `${pose.roll.toFixed(1)}°`;
    }

    const gaze = msg.gaze || msg.data?.gaze;
    if (gaze) {
      const gazeEl = document.getElementById("telem-gaze");
      if (gazeEl) gazeEl.textContent = `[${gaze[0].toFixed(2)}, ${gaze[1].toFixed(2)}]`;
    }

    // Forward to Settings Panel live telemetry card
    this.settingsPanel.updateVisionTelemetry(msg.data || msg);
  }

  private updatePluginListUI(): void {
    const listEl = document.getElementById("plugin-list");
    if (!listEl) return;

    listEl.innerHTML = "";
    this.activePlugins.forEach((pluginName) => {
      const tag = document.createElement("span");
      tag.className = "plugin-tag";
      tag.textContent = pluginName;
      listEl.appendChild(tag);
    });
  }

  private handleSettingsChange(settings: SettingsConfig): void {
    this.sfx.setVolume(settings.sfx.masterVolume);
    this.sfx.setEnabled(settings.sfx.powerUpEnabled);
    this.statusBar.setModel(settings.brain.model);

    if (settings.appearance?.coreVariant && settings.appearance.coreVariant !== this.currentVariant) {
      this.setCoreVariant(settings.appearance.coreVariant, false);
    }

    // Theme update
    const crtEl = document.querySelector(".crt-overlay") as HTMLElement;
    if (crtEl) {
      crtEl.style.display = settings.appearance.crtScanlines ? "block" : "none";
    }

    // Vision / Face Tracking update
    if (settings.vision?.faceTrackingEnabled === false) {
      this.statusBar.setAttention(false, false);
      const pitchEl = document.getElementById("telem-pitch");
      const yawEl = document.getElementById("telem-yaw");
      const rollEl = document.getElementById("telem-roll");
      if (pitchEl) pitchEl.textContent = "OFF";
      if (yawEl) yawEl.textContent = "OFF";
      if (rollEl) rollEl.textContent = "OFF";
    }
  }

  private toggleActivation(): void {
    if (this.state === "listening") {
      this.ws.deactivate();
      this.handleStateTransition("idle");
    } else {
      this.ws.activate();
      this.handleStateTransition("listening");
    }
  }

  private setupKeyboardShortcuts(): void {
    window.addEventListener("keydown", (e: KeyboardEvent) => {
      // Space: Toggle Push-to-Talk / Listening
      if (e.code === "Space" && (e.target === document.body || (e.target as HTMLElement).tagName === "BUTTON")) {
        e.preventDefault();
        this.toggleActivation();
      }

      // KeyV: Toggle Core Visualizer Variant (ARC Reactor <-> Particle Orb)
      if (e.code === "KeyV" && (e.target === document.body || (e.target as HTMLElement).tagName === "BUTTON")) {
        e.preventDefault();
        const nextVariant: CoreVisualizerVariant =
          this.currentVariant === "arc_reactor" ? "particle_orb" : "arc_reactor";
        this.setCoreVariant(nextVariant);
      }

      // KeyM: Toggle Iron Man 3D Model Mode (Helmet <-> Suit Blueprint)
      if (e.code === "KeyM" && (e.target === document.body || (e.target as HTMLElement).tagName === "BUTTON")) {
        e.preventDefault();
        const newMode = this.ironman3D?.toggleViewMode();
        const btn = document.getElementById("btn-toggle-armor-view");
        if (btn && newMode) btn.textContent = newMode === "helmet" ? "HELMET" : "ARMOR";
        this.sfx.chime();
      }

      // KeyO: Toggle Vision Mode (Center Stage Camera Targeting <-> Minimized Core)
      if (e.code === "KeyO" && (e.target === document.body || (e.target as HTMLElement).tagName === "BUTTON")) {
        e.preventDefault();
        this.toggleVisionMode();
      }

      // Escape: Close Settings or toggle Fullscreen
      if (e.code === "Escape") {
        this.settingsPanel.close();
      }

      // F2 or KeyS: Open Settings
      if (e.code === "F2" || (e.ctrlKey && e.code === "KeyS")) {
        e.preventDefault();
        this.settingsPanel.toggle();
      }
    });
  }

  private setupQuickControls(): void {
    const pttBtn = document.getElementById("btn-quick-ptt");
    pttBtn?.addEventListener("click", () => this.toggleActivation());

    const quickVisionBtn = document.getElementById("btn-quick-vision");
    quickVisionBtn?.addEventListener("click", () => this.toggleVisionMode());

    const toggleVisionBtn = document.getElementById("btn-toggle-vision-mode");
    toggleVisionBtn?.addEventListener("click", () => this.toggleVisionMode());

    const clearBtn = document.getElementById("btn-quick-clear");
    clearBtn?.addEventListener("click", () => {
      this.transcriptBar.clear();
      this.waveform.clear();
    });

    const btnReactor = document.getElementById("btn-variant-reactor");
    btnReactor?.addEventListener("click", () => this.setCoreVariant("arc_reactor"));

    const btnOrb = document.getElementById("btn-variant-orb");
    btnOrb?.addEventListener("click", () => this.setCoreVariant("particle_orb"));
  }
}

// Bootstrap application on DOM load in browser environment
if (typeof window !== "undefined") {
  window.addEventListener("DOMContentLoaded", () => {
    new JarvisApp();
  });
}

