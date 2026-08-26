/**
 * Jarvis AI - Resilient Typed WebSocket Client
 * Manages WebSocket connection to Python backend (ws://localhost:8765),
 * exponential backoff auto-reconnect, ping/pong heartbeat latency tracking,
 * and typed message dispatch.
 */

import {
  InboundWSMessage,
  OutboundWSMessage,
  JarvisState,
  SettingsConfig,
} from "./types";

export type WSHandler<T = any> = (data: T) => void;

export class WSClient {
  private ws: WebSocket | null = null;
  private url: string;
  private handlers: Map<string, WSHandler[]> = new Map();
  private reconnectDelay = 1000;
  private maxReconnectDelay = 10000;
  private reconnectTimer: number | null = null;
  private heartbeatTimer: number | null = null;
  private lastPingTime = 0;
  private isExplicitlyClosed = false;

  constructor(url = "ws://localhost:8765") {
    this.url = url;
  }

  public connect(): void {
    this.isExplicitlyClosed = false;
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        console.log(`[WSClient] Connected to backend at ${this.url}`);
        this.reconnectDelay = 1000;
        this.startHeartbeat();
        this.emitInternal("connection", { connected: true });
      };

      this.ws.onmessage = (event: MessageEvent) => {
        try {
          const raw = typeof event.data === "string" ? JSON.parse(event.data) : event.data;
          const msg = raw as InboundWSMessage;

          // Latency calculation on pong
          if (msg.type === "pong") {
            const now = Date.now();
            const latency = this.lastPingTime > 0 ? now - this.lastPingTime : 0;
            this.emitInternal("latency", { latencyMs: latency });
          }

          // Dispatch typed event
          const registered = this.handlers.get(msg.type) || [];
          registered.forEach((handler) => {
            try {
              handler(msg);
            } catch (err) {
              console.error(`[WSClient] Handler error for event '${msg.type}':`, err);
            }
          });

          // Dispatch to wildcard handler if any
          const wildcards = this.handlers.get("*") || [];
          wildcards.forEach((handler) => handler(msg));
        } catch (e) {
          console.error("[WSClient] Failed to parse message:", e, event.data);
        }
      };

      this.ws.onclose = () => {
        this.stopHeartbeat();
        this.emitInternal("connection", { connected: false });
        if (!this.isExplicitlyClosed) {
          this.scheduleReconnect();
        }
      };

      this.ws.onerror = (err) => {
        console.warn("[WSClient] WebSocket connection error:", err);
        this.emitInternal("error", { error: err });
      };
    } catch (err) {
      console.warn("[WSClient] Error instantiating WebSocket:", err);
      this.scheduleReconnect();
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer !== null) return;

    console.log(`[WSClient] Reconnecting in ${this.reconnectDelay}ms...`);
    this.reconnectTimer = window.setTimeout(() => {
      this.reconnectTimer = null;
      this.reconnectDelay = Math.min(this.reconnectDelay * 1.5, this.maxReconnectDelay);
      this.connect();
    }, this.reconnectDelay);
  }

  private startHeartbeat(): void {
    this.stopHeartbeat();
    this.heartbeatTimer = window.setInterval(() => {
      this.ping();
    }, 5000);
  }

  private stopHeartbeat(): void {
    if (this.heartbeatTimer !== null) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  public ping(): void {
    if (this.isConnected()) {
      this.lastPingTime = Date.now();
      this.send({ type: "ping", data: { timestamp: this.lastPingTime } });
    }
  }

  public activate(): void {
    this.send({ type: "command", action: "activate" });
  }

  public deactivate(): void {
    this.send({ type: "command", action: "deactivate" });
  }

  public requestSettings(): void {
    this.send({ type: "settings_request" });
  }

  public updateConfig(namespace: string, key: string, value: any): void {
    this.send({
      type: "config_update",
      namespace,
      plugin: namespace,
      key,
      value,
      data: { namespace, key, value },
    });
  }

  public on<T = any>(type: string, handler: WSHandler<T>): void {
    if (!this.handlers.has(type)) {
      this.handlers.set(type, []);
    }
    this.handlers.get(type)!.push(handler);
  }

  public off(type: string, handler: WSHandler): void {
    const list = this.handlers.get(type);
    if (list) {
      this.handlers.set(
        type,
        list.filter((h) => h !== handler)
      );
    }
  }

  private emitInternal(type: string, data: any): void {
    const list = this.handlers.get(type) || [];
    list.forEach((h) => h(data));
  }

  public send(msg: OutboundWSMessage | object): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(msg));
    }
  }

  public isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  public close(): void {
    this.isExplicitlyClosed = true;
    this.stopHeartbeat();
    if (this.reconnectTimer !== null) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}
