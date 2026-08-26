/**
 * Jarvis AI - Top Status Bar Controller
 * Manages model badges, interaction mode indicators, state dots,
 * ping/latency telemetry, live digital clock, weather & location, and screen time.
 */

import { JarvisState, WeatherTelemetryData } from "../core/types";

export interface StatusBarOptions {
  onSettingsClick?: () => void;
  onActivateClick?: () => void;
}

export class StatusBar {
  private container: HTMLElement;
  private stateIndicator: HTMLElement;
  private stateDot: HTMLElement;
  private modelIndicator: HTMLElement;
  private modeIndicator: HTMLElement;
  private pingIndicator: HTMLElement;
  private attentionIndicator: HTMLElement;
  private clockEl: HTMLElement;
  private dateEl: HTMLElement;
  private screenTimeValEl: HTMLElement;
  private locationEl: HTMLElement;
  private temperatureEl: HTMLElement;
  private conditionEl: HTMLElement;
  private settingsBtn: HTMLElement;
  private activateBtn: HTMLElement;
  private state: JarvisState = "idle";
  private isConnected = false;
  private sessionStartTime: number = Date.now();
  private clockTimer: any = null;

  constructor(container: HTMLElement, options: StatusBarOptions = {}) {
    this.container = container;
    this.container.innerHTML = `
      <div class="status-left">
        <div class="status-logo">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
            <polyline points="2 17 12 22 22 17"></polyline>
            <polyline points="2 12 12 17 22 12"></polyline>
          </svg>
          <span>JARVIS</span>
        </div>
        <div class="status-badge" id="state-badge">
          <div class="status-dot"></div>
          <span id="state-label">STANDBY</span>
        </div>
        <div class="hud-clock-widget">
          <span class="hud-time" id="hud-clock">00:00:00</span>
          <span class="hud-date" id="hud-date">THU, 27 AUG</span>
        </div>
        <div class="hud-screentime-widget" title="Active Session Screen Time">
          <span class="hud-st-label">SESSION:</span>
          <span class="hud-st-val" id="hud-screentime-val">00:00:00</span>
        </div>
      </div>

      <div class="status-center">
        <div class="status-item">
          <span class="label">AI BRAIN:</span>
          <span class="val" id="model-indicator">llama3</span>
        </div>
        <div class="status-item">
          <span class="label">MODE:</span>
          <span class="val" id="mode-indicator">VOICE + PTT</span>
        </div>
        <div class="status-item">
          <span class="label">ATTENTION:</span>
          <span class="val" id="attention-indicator">--</span>
        </div>
        <div class="hud-weather-pill" id="hud-weather-widget" title="Local Atmospheric Telemetry">
          <span class="weather-icon">📍</span>
          <span class="weather-loc" id="hud-location">HYDERABAD, IN</span>
          <span class="weather-temp" id="hud-temp">26°C</span>
          <span class="weather-cond" id="hud-cond">RAIN</span>
        </div>
      </div>

      <div class="status-right">
        <div class="status-item">
          <span class="label">LATENCY:</span>
          <span class="val" id="ping-indicator">OFFLINE</span>
        </div>
        <button class="status-btn" id="activate-btn">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"></path>
            <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
            <line x1="12" y1="19" x2="12" y2="22"></line>
          </svg>
          <span>ACTIVATE</span>
        </button>
        <button class="status-btn" id="settings-btn" title="Configuration Drawer">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="3"></circle>
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
          </svg>
          <span>CONFIG</span>
        </button>
      </div>
    `;

    this.stateIndicator = this.container.querySelector("#state-label") as HTMLElement;
    this.stateDot = this.container.querySelector(".status-dot") as HTMLElement;
    this.modelIndicator = this.container.querySelector("#model-indicator") as HTMLElement;
    this.modeIndicator = this.container.querySelector("#mode-indicator") as HTMLElement;
    this.pingIndicator = this.container.querySelector("#ping-indicator") as HTMLElement;
    this.attentionIndicator = this.container.querySelector("#attention-indicator") as HTMLElement;
    this.clockEl = this.container.querySelector("#hud-clock") as HTMLElement;
    this.dateEl = this.container.querySelector("#hud-date") as HTMLElement;
    this.screenTimeValEl = this.container.querySelector("#hud-screentime-val") as HTMLElement;
    this.locationEl = this.container.querySelector("#hud-location") as HTMLElement;
    this.temperatureEl = this.container.querySelector("#hud-temp") as HTMLElement;
    this.conditionEl = this.container.querySelector("#hud-cond") as HTMLElement;
    this.settingsBtn = this.container.querySelector("#settings-btn") as HTMLElement;
    this.activateBtn = this.container.querySelector("#activate-btn") as HTMLElement;

    if (options.onSettingsClick) {
      this.settingsBtn.addEventListener("click", options.onSettingsClick);
    }
    if (options.onActivateClick) {
      this.activateBtn.addEventListener("click", options.onActivateClick);
    }

    this.startClock();
  }

  private startClock(): void {
    const updateTime = () => {
      const now = new Date();
      const h = String(now.getHours()).padStart(2, "0");
      const m = String(now.getMinutes()).padStart(2, "0");
      const s = String(now.getSeconds()).padStart(2, "0");
      this.clockEl.textContent = `${h}:${m}:${s}`;

      const days = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"];
      const months = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"];
      this.dateEl.textContent = `${days[now.getDay()]}, ${now.getDate()} ${months[now.getMonth()]} ${now.getFullYear()}`;

      // Screen time
      const elapsedSec = Math.floor((Date.now() - this.sessionStartTime) / 1000);
      const sh = String(Math.floor(elapsedSec / 3600)).padStart(2, "0");
      const sm = String(Math.floor((elapsedSec % 3600) / 60)).padStart(2, "0");
      const ss = String(elapsedSec % 60).padStart(2, "0");
      this.screenTimeValEl.textContent = `${sh}:${sm}:${ss}`;
    };

    updateTime();
    this.clockTimer = setInterval(updateTime, 1000);
  }

  public setWeather(weather: WeatherTelemetryData): void {
    if (!weather) return;
    if (this.locationEl && weather.city) {
      const locStr = weather.region ? `${weather.city}, ${weather.country}` : weather.city;
      this.locationEl.textContent = locStr.slice(0, 24);
    }
    if (this.temperatureEl && weather.temp_c !== undefined) {
      this.temperatureEl.textContent = `${weather.temp_c}°C`;
    }
    if (this.conditionEl && weather.condition) {
      this.conditionEl.textContent = weather.condition.slice(0, 16);
    }
  }

  public setState(state: JarvisState): void {
    this.state = state;
    const labels: Record<JarvisState, string> = {
      idle: "IDLE / STANDBY",
      listening: "LISTENING",
      thinking: "PROCESSING",
      speaking: "TRANSMITTING",
      error: "ALERT / ERROR",
    };

    this.stateIndicator.textContent = labels[state] || state.toUpperCase();

    // Update state styling
    this.container.className = `status-bar-container state-${state}`;

    if (state === "listening") {
      this.activateBtn.classList.add("active");
      this.activateBtn.querySelector("span")!.textContent = "STOP";
    } else {
      this.activateBtn.classList.remove("active");
      this.activateBtn.querySelector("span")!.textContent = "ACTIVATE";
    }
  }

  public setConnectionStatus(connected: boolean, latencyMs?: number): void {
    this.isConnected = connected;
    if (!connected) {
      this.pingIndicator.textContent = "OFFLINE";
      this.pingIndicator.style.color = "var(--accent-red)";
    } else {
      this.pingIndicator.textContent = latencyMs !== undefined ? `${latencyMs}ms` : "ONLINE";
      this.pingIndicator.style.color = "var(--accent-green)";
    }
  }

  public setModel(model: string): void {
    this.modelIndicator.textContent = model;
  }

  public setMode(mode: string): void {
    this.modeIndicator.textContent = mode;
  }

  public setAttention(attention: boolean, detected = true): void {
    if (!detected) {
      this.attentionIndicator.textContent = "NO TARGET";
      this.attentionIndicator.style.color = "var(--text-muted)";
    } else if (attention) {
      this.attentionIndicator.textContent = "LOCKED ON";
      this.attentionIndicator.style.color = "var(--accent-cyan)";
    } else {
      this.attentionIndicator.textContent = "PASSIVE";
      this.attentionIndicator.style.color = "var(--text-secondary)";
    }
  }

  public destroy(): void {
    if (this.clockTimer) {
      clearInterval(this.clockTimer);
      this.clockTimer = null;
    }
  }
}
