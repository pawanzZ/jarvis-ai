import { WSClient } from "./ws-client";

class JarvisApp {
  private ws: WSClient;
  private state: string = "idle";

  constructor() {
    this.ws = new WSClient();
    this.setupHandlers();
    this.ws.connect();
  }

  private setupHandlers(): void {
    this.ws.on("state_change", (msg) => {
      this.state = msg.state;
      document.title = `Jarvis AI [${this.state}]`;
      console.log(`State: ${this.state}`);
    });

    this.ws.on("error", (msg) => {
      console.error("Backend error:", msg.message);
    });
  }
}

window.addEventListener("DOMContentLoaded", () => {
  new JarvisApp();
});
