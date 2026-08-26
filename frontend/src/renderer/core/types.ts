/**
 * Jarvis AI - Frontend Core Type Definitions
 * Complete TypeScript interfaces for Jarvis states, WebSocket protocols,
 * telemetry schemas, HUD models, and configuration.
 */

export type JarvisState = "idle" | "listening" | "thinking" | "speaking" | "error";

export type AudioSource = "mic" | "tts";

export interface HeadPose {
  pitch: number;
  yaw: number;
  roll: number;
}

export interface FaceTelemetry {
  detected: boolean;
  attention: boolean;
  head_pose?: HeadPose;
  pose?: HeadPose;
  gaze?: [number, number];
  blink?: boolean;
}

// Inbound WebSocket Events (Backend -> Frontend)

export interface StateChangeEvent {
  type: "state_change";
  state: JarvisState;
  previous?: JarvisState;
  data?: {
    state: JarvisState;
    previous?: JarvisState;
  };
}

export interface TranscriptPartialEvent {
  type: "transcript_partial";
  text: string;
  data?: {
    text: string;
  };
}

export interface TranscriptStreamEvent {
  type: "transcript_stream";
  token?: string;
  is_final?: boolean;
  data?: {
    token: string;
    is_final?: boolean;
  };
}

export interface TranscriptFinalEvent {
  type: "transcript_final";
  text?: string;
  speaker?: "user" | "jarvis";
  data?: {
    speaker: "user" | "jarvis";
    text: string;
  };
}

export interface LLMTokenEvent {
  type: "llm_token";
  token: string;
  data?: {
    token: string;
  };
}

export interface ResponseCompleteEvent {
  type: "response_complete";
  full_text: string;
  data?: {
    full_text: string;
  };
}

export interface AudioLevelEvent {
  type: "audio_level";
  level?: number;
  source?: AudioSource;
  data?: {
    level: number;
    source?: AudioSource;
  };
}

export interface FaceDataEvent {
  type: "face_data" | "face_telemetry";
  gaze?: [number, number];
  pose?: HeadPose;
  blink?: boolean;
  face_detected?: boolean;
  attention?: boolean;
  head_pose?: HeadPose;
  data?: {
    detected?: boolean;
    attention?: boolean;
    head_pose?: HeadPose;
    pose?: HeadPose;
    gaze?: [number, number];
    blink?: boolean;
  };
}

export interface PluginLoadedEvent {
  type: "plugin_loaded";
  name: string;
  plugin_type?: string;
  data?: {
    name: string;
    plugin_type: string;
  };
}

export interface SettingsResponseEvent {
  type: "settings_response";
  settings?: Partial<SettingsConfig>;
  data?: {
    settings: Partial<SettingsConfig>;
  };
}

export interface ConfigUpdatedEvent {
  type: "config_updated";
  namespace?: string;
  plugin?: string;
  key?: string;
  value?: any;
  data?: {
    namespace?: string;
    plugin?: string;
    key: string;
    value: any;
  };
}

export interface PongEvent {
  type: "pong";
  timestamp?: number;
  data?: {
    timestamp: number;
  };
}

export interface BackendErrorEvent {
  type: "error";
  message?: string;
  code?: string;
  data?: {
    code?: string;
    message: string;
  };
}

export interface WeatherTelemetryData {
  city: string;
  region: string;
  country: string;
  temp_c: number;
  temp_f: number;
  feels_like_c: number;
  condition: string;
  humidity: number;
  wind_kmph: number;
  last_updated: number;
}

export interface SystemTelemetryData {
  cpu: {
    usage_percent: number;
    cores: number;
    load_avg: number[];
  };
  gpu: {
    name: string;
    status: string;
  };
  memory: {
    total_mb: number;
    used_mb: number;
    free_mb: number;
    total_gb: number;
    used_gb: number;
    usage_percent: number;
  };
  disk: {
    total_gb: number;
    used_gb: number;
    free_gb: number;
    usage_percent: number;
  };
  network: {
    rx_kbps: number;
    tx_kbps: number;
    rx_mbps: number;
    tx_mbps: number;
    total_rx_mb: number;
    total_tx_mb: number;
  };
  uptime: {
    session_seconds: number;
    session_str: string;
    system_seconds: number;
    system_uptime_str: string;
  };
  os: {
    distro: string;
    kernel: string;
    arch: string;
    hostname: string;
  };
  weather: WeatherTelemetryData;
  timestamp: number;
}

export interface SystemTelemetryEvent {
  type: "system_telemetry";
  data: SystemTelemetryData;
}

export interface WeatherTelemetryEvent {
  type: "weather_telemetry";
  data: WeatherTelemetryData;
}

export type InboundWSMessage =
  | StateChangeEvent
  | TranscriptPartialEvent
  | TranscriptStreamEvent
  | TranscriptFinalEvent
  | LLMTokenEvent
  | ResponseCompleteEvent
  | AudioLevelEvent
  | FaceDataEvent
  | PluginLoadedEvent
  | SettingsResponseEvent
  | ConfigUpdatedEvent
  | SystemTelemetryEvent
  | WeatherTelemetryEvent
  | PongEvent
  | BackendErrorEvent;

// Outbound WebSocket Messages (Frontend -> Backend)

export interface CommandMessage {
  type: "command";
  action: "activate" | "deactivate";
}

export interface ActivateMessage {
  type: "activate";
}

export interface DeactivateMessage {
  type: "deactivate";
}

export interface ConfigUpdateMessage {
  type: "config_update";
  namespace?: string;
  plugin?: string;
  key: string;
  value: any;
  data?: {
    namespace?: string;
    plugin?: string;
    key: string;
    value: any;
  };
}

export interface SettingsRequestMessage {
  type: "settings_request";
}

export interface PingMessage {
  type: "ping";
  data?: {
    timestamp: number;
  };
}

export type OutboundWSMessage =
  | CommandMessage
  | ActivateMessage
  | DeactivateMessage
  | ConfigUpdateMessage
  | SettingsRequestMessage
  | PingMessage;

// Settings & Config Schemas

export interface VoiceSettings {
  sttPlugin: string;
  ttsPlugin: string;
  ttsVoice: string;
  ttsRate: number;
  micSensitivity: number;
  volume: number;
}

export interface BrainSettings {
  llmPlugin: string;
  model: string;
  temperature: number;
  maxTokens: number;
  systemPrompt: string;
}

export interface ActivationSettings {
  wakeWordEnabled: boolean;
  wakeWord: string;
  pttEnabled: boolean;
  pttKey: string;
  clapEnabled: boolean;
  clapSensitivity: number;
  gestureEnabled: boolean;
}

export interface AppearanceSettings {
  theme: "arc" | "matrix" | "synthwave" | "stealth";
  particleDensity: number;
  crtScanlines: boolean;
  glowIntensity: number;
  uiScale: number;
}

export interface VisionSettings {
  cameraIndex: number;
  faceTrackingEnabled: boolean;
  gazeParallax: boolean;
  helmetBootOverlay: boolean;
}

export interface SFXSettings {
  masterVolume: number;
  powerUpEnabled: boolean;
  chimesEnabled: boolean;
  humEnabled: boolean;
  errorBuzzEnabled: boolean;
  thinkingWhirrEnabled: boolean;
}

export interface SettingsConfig {
  voice: VoiceSettings;
  brain: BrainSettings;
  activation: ActivationSettings;
  appearance: AppearanceSettings;
  vision: VisionSettings;
  sfx: SFXSettings;
}

export const DEFAULT_SETTINGS: SettingsConfig = {
  voice: {
    sttPlugin: "whisper_local",
    ttsPlugin: "piper_tts",
    ttsVoice: "en_GB-alan-medium",
    ttsRate: 1.0,
    micSensitivity: 0.8,
    volume: 0.8,
  },
  brain: {
    llmPlugin: "ollama_llm",
    model: "llama3",
    temperature: 0.7,
    maxTokens: 512,
    systemPrompt: "You are JARVIS, a helpful, witty, and concise AI assistant.",
  },
  activation: {
    wakeWordEnabled: true,
    wakeWord: "Hey Jarvis",
    pttEnabled: true,
    pttKey: "Space",
    clapEnabled: true,
    clapSensitivity: 0.7,
    gestureEnabled: false,
  },
  appearance: {
    theme: "arc",
    particleDensity: 60,
    crtScanlines: true,
    glowIntensity: 1.0,
    uiScale: 1.0,
  },
  vision: {
    cameraIndex: 0,
    faceTrackingEnabled: true,
    gazeParallax: true,
    helmetBootOverlay: false,
  },
  sfx: {
    masterVolume: 0.5,
    powerUpEnabled: true,
    chimesEnabled: true,
    humEnabled: true,
    errorBuzzEnabled: true,
    thinkingWhirrEnabled: true,
  },
};
