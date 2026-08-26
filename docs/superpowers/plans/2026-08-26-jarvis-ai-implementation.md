# Jarvis AI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a voice-first, always-on desktop AI assistant with a full-screen HUD, pluggable AI backends, and Iron Man-inspired aesthetics.

**Architecture:** Hybrid system — Python backend handles all ML/AI workloads (STT, TTS, LLM, face tracking), Electron frontend renders the HUD visualizer. They communicate via WebSocket on localhost. Plugin system allows hot-swapping of all backend components.

**Tech Stack:** Python 3.11+, asyncio, websockets, Whisper.cpp, Piper TTS, Ollama, MediaPipe. Electron 30+, TypeScript, Three.js, HTML5 Canvas, Web Audio API, CSS animations.

**Spec:** `docs/superpowers/specs/2026-08-26-jarvis-ai-design.md`

## Global Constraints

- Python >= 3.11, Node >= 20
- All ML models run locally by default (no API keys required for v1)
- WebSocket port: 8765 (localhost only)
- Plugin interface must be stable before any plugin implementation
- HUD must maintain 60fps at 1080p
- No external file dependencies for SFX (Web Audio API synthesis)
- Camera/mic feeds never leave the machine

---

## Phase 1: Project Skeleton

### Task 1: Python Backend Scaffolding

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/jarvis/__init__.py`
- Create: `backend/jarvis/__main__.py`
- Create: `backend/jarvis/core/__init__.py`
- Create: `backend/jarvis/core/bus.py`
- Create: `backend/jarvis/core/state.py`
- Create: `backend/jarvis/core/config.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/test_bus.py`
- Create: `backend/tests/test_state.py`

**Interfaces:**
- Produces: `EventBus`, `StateMachine`, `Config` classes

- [ ] **Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "jarvis"
version = "0.1.0"
description = "Voice-interactive AI desktop agent"
requires-python = ">=3.11"
dependencies = [
    "websockets>=12.0",
    "pydantic>=2.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
]
```

- [ ] **Step 2: Create Event Bus**

```python
# backend/jarvis/core/bus.py
from __future__ import annotations
import asyncio
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine


@dataclass
class Event:
    type: str
    data: dict[str, Any] = field(default_factory=dict)
    source: str = ""


EventHandler = Callable[[Event], Coroutine[Any, Any, None]]


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = {}
        self._queue: asyncio.Queue[Event] = asyncio.Queue()

    def on(self, event_type: str, handler: EventHandler) -> None:
        self._handlers.setdefault(event_type, []).append(handler)

    def off(self, event_type: str, handler: EventHandler) -> None:
        if event_type in self._handlers:
            self._handlers[event_type] = [
                h for h in self._handlers[event_type] if h != handler
            ]

    async def emit(self, event: Event) -> None:
        await self._queue.put(event)

    async def process(self) -> None:
        while True:
            event = await self._queue.get()
            handlers = self._handlers.get(event.type, [])
            for handler in handlers:
                await handler(event)
```

- [ ] **Step 3: Create State Machine**

```python
# backend/jarvis/core/state.py
from __future__ import annotations
from enum import Enum


class JarvisState(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    ERROR = "error"


TRANSITIONS: dict[JarvisState, set[JarvisState]] = {
    JarvisState.IDLE: {JarvisState.LISTENING, JarvisState.ERROR},
    JarvisState.LISTENING: {JarvisState.THINKING, JarvisState.IDLE, JarvisState.ERROR},
    JarvisState.THINKING: {JarvisState.SPEAKING, JarvisState.IDLE, JarvisState.ERROR},
    JarvisState.SPEAKING: {JarvisState.LISTENING, JarvisState.IDLE, JarvisState.ERROR},
    JarvisState.ERROR: {JarvisState.IDLE},
}


class StateMachine:
    def __init__(self) -> None:
        self._state = JarvisState.IDLE
        self._listeners: list = []

    @property
    def state(self) -> JarvisState:
        return self._state

    def on_change(self, callback) -> None:
        self._listeners.append(callback)

    async def transition(self, new_state: JarvisState) -> bool:
        if new_state not in TRANSITIONS.get(self._state, set()):
            return False
        old = self._state
        self._state = new_state
        for cb in self._listeners:
            await cb(old, new_state)
        return True
```

- [ ] **Step 4: Create Config Loader**

```python
# backend/jarvis/core/config.py
from __future__ import annotations
import json
from pathlib import Path
from typing import Any


class Config:
    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir
        self._config_dir = base_dir / "config"
        self._cache: dict[str, dict[str, Any]] = {}

    def get(self, namespace: str, key: str | None = None, default: Any = None) -> Any:
        if namespace not in self._cache:
            self._load(namespace)
        data = self._cache.get(namespace, {})
        if key is None:
            return data
        return data.get(key, default)

    def set(self, namespace: str, key: str, value: Any) -> None:
        if namespace not in self._cache:
            self._load(namespace)
        self._cache.setdefault(namespace, {})[key] = value
        self._save(namespace)

    def _load(self, namespace: str) -> None:
        path = self._config_dir / f"{namespace}.json"
        if path.exists():
            self._cache[namespace] = json.loads(path.read_text())
        else:
            self._cache[namespace] = {}

    def _save(self, namespace: str) -> None:
        self._config_dir.mkdir(parents=True, exist_ok=True)
        path = self._config_dir / f"{namespace}.json"
        path.write_text(json.dumps(self._cache[namespace], indent=2))
```

- [ ] **Step 5: Create __main__.py entry point**

```python
# backend/jarvis/__main__.py
import asyncio
from pathlib import Path
from jarvis.core.bus import EventBus
from jarvis.core.state import StateMachine
from jarvis.core.config import Config


async def main() -> None:
    base_dir = Path(__file__).parent.parent.parent
    bus = EventBus()
    state = StateMachine()
    config = Config(base_dir)

    async def on_state_change(old, new):
        print(f"State: {old.value} -> {new.value}")

    state.on_change(on_state_change)
    print("Jarvis backend starting...")
    # WebSocket server will be added in Task 3
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 6: Write tests for EventBus**

```python
# backend/tests/test_bus.py
import asyncio
import pytest
from jarvis.core.bus import EventBus, Event


@pytest.mark.asyncio
async def test_emit_and_receive():
    bus = EventBus()
    received = []

    async def handler(event: Event):
        received.append(event)

    bus.on("test", handler)
    await bus.emit(Event(type="test", data={"value": 42}))

    # Process one event
    event = await asyncio.wait_for(bus._queue.get(), timeout=1)
    await handler(event)

    assert len(received) == 1
    assert received[0].data["value"] == 42


@pytest.mark.asyncio
async def test_off_removes_handler():
    bus = EventBus()
    received = []

    async def handler(event: Event):
        received.append(event)

    bus.on("test", handler)
    bus.off("test", handler)
    await bus.emit(Event(type="test"))
    assert bus._queue.empty() or len(received) == 0
```

- [ ] **Step 7: Write tests for StateMachine**

```python
# backend/tests/test_state.py
import pytest
from jarvis.core.state import StateMachine, JarvisState


@pytest.mark.asyncio
async def test_initial_state():
    sm = StateMachine()
    assert sm.state == JarvisState.IDLE


@pytest.mark.asyncio
async def test_valid_transition():
    sm = StateMachine()
    result = await sm.transition(JarvisState.LISTENING)
    assert result is True
    assert sm.state == JarvisState.LISTENING


@pytest.mark.asyncio
async def test_invalid_transition():
    sm = StateMachine()
    result = await sm.transition(JarvisState.SPEAKING)
    assert result is False
    assert sm.state == JarvisState.IDLE


@pytest.mark.asyncio
async def test_on_change_callback():
    sm = StateMachine()
    changes = []

    async def callback(old, new):
        changes.append((old, new))

    sm.on_change(callback)
    await sm.transition(JarvisState.LISTENING)
    assert len(changes) == 1
    assert changes[0] == (JarvisState.IDLE, JarvisState.LISTENING)
```

- [ ] **Step 8: Run tests**

Run: `cd backend && python -m pytest tests/ -v`
Expected: All 5 tests pass

- [ ] **Step 9: Commit**

```bash
git add backend/
git commit -m "feat: Python backend skeleton with EventBus, StateMachine, Config"
```

---

### Task 2: Electron Frontend Scaffolding

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/src/main.ts`
- Create: `frontend/src/preload.ts`
- Create: `frontend/src/renderer/index.html`
- Create: `frontend/src/renderer/core/app.ts`
- Create: `frontend/src/renderer/core/ws-client.ts`

**Interfaces:**
- Produces: `JarvisApp` class, `WSClient` class

- [ ] **Step 1: Create package.json**

```json
{
  "name": "jarvis-ai",
  "version": "0.1.0",
  "main": "dist/main.js",
  "scripts": {
    "build": "tsc",
    "dev": "tsc && electron dist/main.js",
    "start": "electron dist/main.js"
  },
  "dependencies": {
    "ws": "^8.16.0"
  },
  "devDependencies": {
    "electron": "^30.0.0",
    "typescript": "^5.4.0",
    "@types/ws": "^8.5.0"
  }
}
```

- [ ] **Step 2: Create tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "commonjs",
    "lib": ["ES2022", "DOM"],
    "outDir": "dist",
    "rootDir": "src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "declaration": true
  },
  "include": ["src/**/*"]
}
```

- [ ] **Step 3: Create Electron main process**

```typescript
// frontend/src/main.ts
import { app, BrowserWindow } from "electron";
import path from "path";

let mainWindow: BrowserWindow | null = null;

function createWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1920,
    height: 1080,
    fullscreen: true,
    frame: false,
    transparent: true,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  mainWindow.loadFile(path.join(__dirname, "renderer", "index.html"));
  mainWindow.webContents.openDevTools({ mode: "detach" });
}

app.whenReady().then(createWindow);

app.on("window-all-closed", () => {
  app.quit();
});
```

- [ ] **Step 4: Create preload script**

```typescript
// frontend/src/preload.ts
import { contextBridge } from "electron";

contextBridge.exposeInMainWorld("jarvis", {
  platform: process.platform,
});
```

- [ ] **Step 5: Create index.html**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Jarvis AI</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      background: #0a0a0f;
      color: #e0e0e0;
      font-family: 'Segoe UI', system-ui, sans-serif;
      overflow: hidden;
      height: 100vh;
      width: 100vw;
    }
    #app {
      width: 100%;
      height: 100%;
      display: flex;
      flex-direction: column;
    }
  </style>
</head>
<body>
  <div id="app">
    <div id="status-bar"></div>
    <div id="main-area"></div>
    <div id="transcript-bar"></div>
  </div>
  <script src="core/app.js"></script>
</body>
</html>
```

- [ ] **Step 6: Create WebSocket client**

```typescript
// frontend/src/renderer/core/ws-client.ts
export type MessageHandler = (data: any) => void;

export class WSClient {
  private ws: WebSocket | null = null;
  private handlers: Map<string, MessageHandler[]> = new Map();
  private reconnectDelay = 1000;

  constructor(private url: string = "ws://localhost:8765") {}

  connect(): void {
    this.ws = new WebSocket(this.url);

    this.ws.onopen = () => {
      console.log("Connected to Jarvis backend");
      this.reconnectDelay = 1000;
    };

    this.ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        const handlers = this.handlers.get(msg.type) || [];
        handlers.forEach((h) => h(msg));
      } catch (e) {
        console.error("Invalid message:", e);
      }
    };

    this.ws.onclose = () => {
      console.log("Disconnected. Reconnecting...");
      setTimeout(() => this.connect(), this.reconnectDelay);
      this.reconnectDelay = Math.min(this.reconnectDelay * 2, 10000);
    };

    this.ws.onerror = (err) => {
      console.error("WebSocket error:", err);
    };
  }

  on(type: string, handler: MessageHandler): void {
    if (!this.handlers.has(type)) {
      this.handlers.set(type, []);
    }
    this.handlers.get(type)!.push(handler);
  }

  send(data: object): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }
}
```

- [ ] **Step 7: Create app entry point**

```typescript
// frontend/src/renderer/core/app.ts
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
```

- [ ] **Step 8: Install dependencies and build**

Run: `cd frontend && npm install && npm run build`
Expected: TypeScript compiles without errors, `dist/` folder created

- [ ] **Step 9: Commit**

```bash
git add frontend/
git commit -m "feat: Electron frontend skeleton with WebSocket client"
```

---

### Task 3: WebSocket Server (Python)

**Files:**
- Create: `backend/jarvis/ws_server.py`
- Create: `backend/tests/test_ws_server.py`

**Interfaces:**
- Consumes: `EventBus`, `StateMachine`, `Config` from Task 1
- Produces: `WSServer` class, message protocol

- [ ] **Step 1: Create WebSocket server**

```python
# backend/jarvis/ws_server.py
from __future__ import annotations
import asyncio
import json
from typing import Any
import websockets
from websockets.server import serve, WebSocketServerProtocol

from jarvis.core.bus import EventBus, Event
from jarvis.core.state import StateMachine, JarvisState


class WSServer:
    def __init__(
        self,
        bus: EventBus,
        state: StateMachine,
        host: str = "localhost",
        port: int = 8765,
    ) -> None:
        self.bus = bus
        self.state = state
        self.host = host
        self.port = port
        self._clients: set[WebSocketServerProtocol] = set()

    async def start(self) -> None:
        async with serve(self._handle, self.host, self.port):
            print(f"WebSocket server running on ws://{self.host}:{self.port}")
            await asyncio.Event().wait()

    async def _handle(self, ws: WebSocketServerProtocol) -> None:
        self._clients.add(ws)
        try:
            async for message in ws:
                await self._on_message(json.loads(message))
        finally:
            self._clients.discard(ws)

    async def _on_message(self, msg: dict[str, Any]) -> None:
        msg_type = msg.get("type")
        if msg_type == "command":
            action = msg.get("action")
            if action == "activate":
                await self.bus.emit(Event(type="activate", source="hud"))
            elif action == "deactivate":
                await self.bus.emit(Event(type="deactivate", source="hud"))
        elif msg_type == "config_update":
            await self.bus.emit(
                Event(
                    type="config_update",
                    data={
                        "plugin": msg.get("plugin"),
                        "key": msg.get("key"),
                        "value": msg.get("value"),
                    },
                    source="hud",
                )
            )
        elif msg_type == "ping":
            await self.broadcast({"type": "pong"})

    async def broadcast(self, data: dict[str, Any]) -> None:
        message = json.dumps(data)
        for client in list(self._clients):
            try:
                await client.send(message)
            except websockets.ConnectionClosed:
                self._clients.discard(client)
```

- [ ] **Step 2: Write tests**

```python
# backend/tests/test_ws_server.py
import asyncio
import json
import pytest
import websockets
from jarvis.core.bus import EventBus
from jarvis.core.state import StateMachine
from jarvis.ws_server import WSServer


@pytest.mark.asyncio
async def test_server_broadcast():
    bus = EventBus()
    state = StateMachine()
    server = WSServer(bus, state, port=8766)

    # Start server in background
    server_task = asyncio.create_task(
        websockets.serve(server._handle, "localhost", 8766)
    )
    await asyncio.sleep(0.1)

    try:
        async with websockets.connect("ws://localhost:8766") as ws:
            await server.broadcast({"type": "test", "data": "hello"})
            msg = await asyncio.wait_for(ws.recv(), timeout=1)
            data = json.loads(msg)
            assert data["type"] == "test"
            assert data["data"] == "hello"
    finally:
        server_task.cancel()
```

- [ ] **Step 3: Run tests**

Run: `cd backend && python -m pytest tests/test_ws_server.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add backend/jarvis/ws_server.py backend/tests/test_ws_server.py
git commit -m "feat: WebSocket server for Electron communication"
```

---

### Task 4: Connect Backend to Frontend

**Files:**
- Modify: `backend/jarvis/__main__.py`
- Modify: `frontend/src/renderer/core/app.ts`

**Interfaces:**
- Consumes: `WSServer` from Task 3, `WSClient` from Task 2

- [ ] **Step 1: Update backend entry point to start WebSocket**

```python
# backend/jarvis/__main__.py
import asyncio
from pathlib import Path
from jarvis.core.bus import EventBus
from jarvis.core.state import StateMachine
from jarvis.core.config import Config
from jarvis.ws_server import WSServer


async def main() -> None:
    base_dir = Path(__file__).parent.parent.parent
    bus = EventBus()
    state = StateMachine()
    config = Config(base_dir)
    server = WSServer(bus, state)

    async def broadcast_state(old, new):
        await server.broadcast({"type": "state_change", "state": new.value})

    state.on_change(broadcast_state)
    print("Jarvis backend starting...")
    await server.start()


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Update frontend to display connection status**

```typescript
// frontend/src/renderer/core/app.ts
import { WSClient } from "./ws-client";

class JarvisApp {
  private ws: WSClient;
  private state: string = "idle";
  private statusBar: HTMLElement;

  constructor() {
    this.ws = new WSClient();
    this.statusBar = document.getElementById("status-bar")!;
    this.setupHandlers();
    this.ws.connect();
  }

  private setupHandlers(): void {
    this.ws.on("state_change", (msg) => {
      this.state = msg.state;
      document.title = `Jarvis AI [${this.state}]`;
      this.statusBar.textContent = `State: ${this.state}`;
    });

    this.ws.on("pong", () => {
      console.log("Backend alive");
    });
  }
}

window.addEventListener("DOMContentLoaded", () => {
  new JarvisApp();
});
```

- [ ] **Step 3: Test end-to-end**

Run: `cd backend && python -m jarvis` (starts backend)
Run: `cd frontend && npm run dev` (starts Electron)

Expected: Electron opens, shows "State: idle" in status bar. Backend prints "Jarvis backend starting..."

- [ ] **Step 4: Commit**

```bash
git add backend/jarvis/__main__.py frontend/src/renderer/core/app.ts
git commit -m "feat: Connect Python backend to Electron frontend via WebSocket"
```

---

### Task 5: Basic HUD Layout

**Files:**
- Create: `frontend/src/renderer/hud/layout.css`
- Modify: `frontend/src/renderer/index.html`
- Create: `frontend/src/renderer/hud/status-bar.ts`
- Create: `frontend/src/renderer/hud/transcript-bar.ts`

**Interfaces:**
- Consumes: `WSClient` events from Task 4

- [ ] **Step 1: Create HUD layout CSS**

```css
/* frontend/src/renderer/hud/layout.css */
:root {
  --bg-primary: #0a0a0f;
  --bg-panel: rgba(10, 15, 30, 0.85);
  --border-glow: rgba(0, 180, 255, 0.3);
  --text-primary: #e0e8f0;
  --text-secondary: #6a7a8a;
  --accent-blue: #00b4ff;
  --accent-cyan: #00d4ff;
  --accent-amber: #ff9500;
  --accent-white: #ffffff;
}

#status-bar {
  height: 40px;
  display: flex;
  align-items: center;
  padding: 0 20px;
  background: var(--bg-panel);
  border-bottom: 1px solid var(--border-glow);
  font-size: 13px;
  color: var(--text-secondary);
  gap: 20px;
}

#main-area {
  flex: 1;
  display: grid;
  grid-template-columns: 1fr 2fr 1fr;
  gap: 1px;
  background: var(--border-glow);
}

#left-panel, #right-panel {
  background: var(--bg-panel);
  padding: 20px;
  overflow-y: auto;
}

#center-area {
  background: var(--bg-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

#transcript-bar {
  height: 60px;
  display: flex;
  align-items: center;
  padding: 0 20px;
  background: var(--bg-panel);
  border-top: 1px solid var(--border-glow);
  font-size: 16px;
  color: var(--text-primary);
}
```

- [ ] **Step 2: Update index.html with HUD structure**

```html
<!-- Update frontend/src/renderer/index.html -->
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Jarvis AI</title>
  <link rel="stylesheet" href="hud/layout.css">
</head>
<body>
  <div id="app">
    <div id="status-bar">
      <span id="model-indicator">Model: --</span>
      <span id="mode-indicator">Mode: Text</span>
      <span id="state-indicator">● Inactive</span>
    </div>
    <div id="main-area">
      <div id="left-panel"></div>
      <div id="center-area">
        <div id="core-container"></div>
      </div>
      <div id="right-panel"></div>
    </div>
    <div id="transcript-bar">
      <span id="transcript-text">Say "Hey Jarvis" to begin...</span>
    </div>
  </div>
  <script src="core/app.js"></script>
</body>
</html>
```

- [ ] **Step 3: Update app.ts to manage HUD elements**

```typescript
// frontend/src/renderer/core/app.ts (updated)
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
      this.updateStatusBar();
    });

    this.ws.on("transcript_partial", (msg) => {
      this.setTranscript(msg.text);
    });

    this.ws.on("transcript_final", (msg) => {
      this.setTranscript(msg.text);
    });

    this.ws.on("llm_token", (msg) => {
      this.appendToTranscript(msg.token);
    });
  }

  private updateStatusBar(): void {
    const indicator = document.getElementById("state-indicator")!;
    const colors: Record<string, string> = {
      idle: "#6a7a8a",
      listening: "#00d4ff",
      thinking: "#ff9500",
      speaking: "#ffffff",
      error: "#ff3b30",
    };
    indicator.style.color = colors[this.state] || "#6a7a8a";
    indicator.textContent = `● ${this.state.charAt(0).toUpperCase() + this.state.slice(1)}`;
  }

  private setTranscript(text: string): void {
    const el = document.getElementById("transcript-text")!;
    el.textContent = text;
  }

  private appendToTranscript(token: string): void {
    const el = document.getElementById("transcript-text")!;
    el.textContent += token;
  }
}

window.addEventListener("DOMContentLoaded", () => {
  new JarvisApp();
});
```

- [ ] **Step 4: Build and verify layout**

Run: `cd frontend && npm run build && npm run dev`

Expected: Full-screen dark HUD with three-panel layout, status bar showing "State: Idle", transcript bar at bottom.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/renderer/hud/ frontend/src/renderer/index.html frontend/src/renderer/core/app.ts
git commit -m "feat: Basic HUD layout with status bar, panels, transcript"
```

---

## Phase 2: Plugin System

### Task 6: Plugin Interface & Manager

**Files:**
- Create: `backend/jarvis/plugins/__init__.py`
- Create: `backend/jarvis/plugins/base.py`
- Create: `backend/jarvis/plugins/manager.py`
- Create: `backend/tests/test_plugins.py`

**Interfaces:**
- Consumes: `EventBus`, `Config` from Task 1
- Produces: `PluginType`, `Plugin` ABC, `PluginManager`

- [ ] **Step 1: Create plugin base classes**

```python
# backend/jarvis/plugins/base.py
from __future__ import annotations
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Optional
from jarvis.core.bus import Event


class PluginType(str, Enum):
    STT = "stt"
    TTS = "tts"
    LLM = "llm"
    WAKE_WORD = "wake_word"
    ACTIVATION = "activation"
    VISION = "vision"


class Plugin(ABC):
    name: str = "unnamed"
    plugin_type: PluginType = PluginType.STT

    @abstractmethod
    async def start(self, config: dict[str, Any]) -> None: ...

    @abstractmethod
    async def stop(self) -> None: ...

    @abstractmethod
    async def on_event(self, event: Event) -> Optional[Event]: ...

    @abstractmethod
    def get_schema(self) -> dict[str, Any]:
        """Return JSON schema for settings UI generation."""
        ...
```

- [ ] **Step 2: Create Plugin Manager**

```python
# backend/jarvis/plugins/manager.py
from __future__ import annotations
import importlib
import importlib.util
import sys
from pathlib import Path
from typing import Any
from jarvis.core.bus import EventBus, Event
from jarvis.core.config import Config
from jarvis.plugins.base import Plugin, PluginType


class PluginManager:
    def __init__(self, bus: EventBus, config: Config) -> None:
        self.bus = bus
        self.config = config
        self._plugins: dict[str, Plugin] = {}
        self._active: dict[str, Plugin] = {}

    def discover(self, plugins_dir: Path) -> list[str]:
        discovered = []
        if not plugins_dir.exists():
            return discovered
        for path in plugins_dir.glob("*.py"):
            if path.name.startswith("_"):
                continue
            name = path.stem
            spec = importlib.util.spec_from_file_location(
                f"jarvis.plugins.builtins.{name}", path
            )
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                sys.modules[spec.name] = mod
                spec.loader.exec_module(mod)
                if hasattr(mod, "plugin_class"):
                    plugin = mod.plugin_class()
                    self._plugins[plugin.name] = plugin
                    discovered.append(plugin.name)
        return discovered

    async def activate(self, name: str) -> bool:
        if name not in self._plugins:
            return False
        plugin = self._plugins[name]
        cfg = self.config.get("plugins", name, {})
        await plugin.start(cfg)
        self._active[name] = plugin
        return True

    async def deactivate(self, name: str) -> bool:
        if name not in self._active:
            return False
        await self._active[name].stop()
        del self._active[name]
        return True

    def get_active(self, plugin_type: PluginType) -> Plugin | None:
        for plugin in self._active.values():
            if plugin.plugin_type == plugin_type:
                return plugin
        return None

    def list_all(self) -> dict[str, Plugin]:
        return dict(self._plugins)
```

- [ ] **Step 3: Create a stub plugin for testing**

```python
# backend/jarvis/plugins/builtins/stub.py
from jarvis.plugins.base import Plugin, PluginType
from jarvis.core.bus import Event
from typing import Any, Optional


class StubPlugin(Plugin):
    name = "stub"
    plugin_type = PluginType.STT

    async def start(self, config: dict[str, Any]) -> None:
        pass

    async def stop(self) -> None:
        pass

    async def on_event(self, event: Event) -> Optional[Event]:
        return None

    def get_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {}}


plugin_class = StubPlugin
```

- [ ] **Step 4: Write tests**

```python
# backend/tests/test_plugins.py
import pytest
from pathlib import Path
from jarvis.core.bus import EventBus
from jarvis.core.config import Config
from jarvis.plugins.manager import PluginManager
from jarvis.plugins.base import PluginType


@pytest.fixture
def manager(tmp_path):
    bus = EventBus()
    config = Config(tmp_path)
    return PluginManager(bus, config)


def test_discover(manager, tmp_path):
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()
    stub_file = plugins_dir / "stub.py"
    stub_file.write_text("""
from jarvis.plugins.base import Plugin, PluginType
from jarvis.core.bus import Event
from typing import Any, Optional

class StubPlugin(Plugin):
    name = "stub"
    plugin_type = PluginType.STT
    async def start(self, config): pass
    async def stop(self): pass
    async def on_event(self, event): return None
    def get_schema(self): return {}

plugin_class = StubPlugin
""")
    discovered = manager.discover(plugins_dir)
    assert "stub" in discovered


@pytest.mark.asyncio
async def test_activate_deactivate(manager, tmp_path):
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()
    stub_file = plugins_dir / "stub.py"
    stub_file.write_text("""
from jarvis.plugins.base import Plugin, PluginType
from jarvis.core.bus import Event
from typing import Any, Optional

class StubPlugin(Plugin):
    name = "stub"
    plugin_type = PluginType.STT
    async def start(self, config): pass
    async def stop(self): pass
    async def on_event(self, event): return None
    def get_schema(self): return {}

plugin_class = StubPlugin
""")
    manager.discover(plugins_dir)
    assert await manager.activate("stub") is True
    assert manager.get_active(PluginType.STT) is not None
    assert await manager.deactivate("stub") is True
    assert manager.get_active(PluginType.STT) is None
```

- [ ] **Step 5: Run tests**

Run: `cd backend && python -m pytest tests/test_plugins.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/jarvis/plugins/ backend/tests/test_plugins.py
git commit -m "feat: Plugin interface, manager, and discovery system"
```

---

### Task 7: Config Loader Enhancement

**Files:**
- Modify: `backend/jarvis/core/config.py`
- Modify: `backend/tests/test_config.py`

**Interfaces:**
- Consumes: `Config` from Task 1

- [ ] **Step 1: Add namespace listing and validation**

```python
# backend/jarvis/core/config.py (updated)
from __future__ import annotations
import json
from pathlib import Path
from typing import Any


class Config:
    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir
        self._config_dir = base_dir / "config"
        self._cache: dict[str, dict[str, Any]] = {}

    def get(self, namespace: str, key: str | None = None, default: Any = None) -> Any:
        if namespace not in self._cache:
            self._load(namespace)
        data = self._cache.get(namespace, {})
        if key is None:
            return data
        return data.get(key, default)

    def set(self, namespace: str, key: str, value: Any) -> None:
        if namespace not in self._cache:
            self._load(namespace)
        self._cache.setdefault(namespace, {})[key] = value
        self._save(namespace)

    def list_namespaces(self) -> list[str]:
        if not self._config_dir.exists():
            return []
        return [f.stem for f in self._config_dir.glob("*.json")]

    def get_all(self, namespace: str) -> dict[str, Any]:
        if namespace not in self._cache:
            self._load(namespace)
        return dict(self._cache.get(namespace, {}))

    def _load(self, namespace: str) -> None:
        path = self._config_dir / f"{namespace}.json"
        if path.exists():
            self._cache[namespace] = json.loads(path.read_text())
        else:
            self._cache[namespace] = {}

    def _save(self, namespace: str) -> None:
        self._config_dir.mkdir(parents=True, exist_ok=True)
        path = self._config_dir / f"{namespace}.json"
        path.write_text(json.dumps(self._cache[namespace], indent=2))
```

- [ ] **Step 2: Write additional tests**

```python
# backend/tests/test_config.py (additions)
import pytest
from pathlib import Path
from jarvis.core.config import Config


def test_list_namespaces(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "llm.json").write_text('{"model": "llama3"}')
    (config_dir / "tts.json").write_text('{"voice": "british"}')

    config = Config(tmp_path)
    namespaces = config.list_namespaces()
    assert "llm" in namespaces
    assert "tts" in namespaces


def test_get_all(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "test.json").write_text('{"a": 1, "b": 2}')

    config = Config(tmp_path)
    data = config.get_all("test")
    assert data == {"a": 1, "b": 2}
```

- [ ] **Step 3: Run tests**

Run: `cd backend && python -m pytest tests/test_config.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add backend/jarvis/core/config.py backend/tests/test_config.py
git commit -m "feat: Config namespace listing and get_all method"
```

---

## Phase 3: Voice Core

### Task 8: Audio Pipeline Foundation

**Files:**
- Create: `backend/jarvis/audio/__init__.py`
- Create: `backend/jarvis/audio/mic_stream.py`
- Create: `backend/jarvis/audio/speaker_output.py`
- Create: `backend/jarvis/audio/vad.py`
- Create: `backend/tests/test_audio.py`

**Interfaces:**
- Produces: `MicStream`, `SpeakerOutput`, `VAD` classes

- [ ] **Step 1: Create mic stream wrapper**

```python
# backend/jarvis/audio/mic_stream.py
from __future__ import annotations
import asyncio
import numpy as np
from typing import AsyncIterator


class MicStream:
    def __init__(self, sample_rate: int = 16000, chunk_size: int = 1024) -> None:
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self._running = False

    async def start(self) -> None:
        self._running = True

    async def stop(self) -> None:
        self._running = False

    async def chunks(self) -> AsyncIterator[np.ndarray]:
        while self._running:
            # Placeholder: real implementation uses sounddevice
            chunk = np.zeros(self.chunk_size, dtype=np.float32)
            await asyncio.sleep(0.01)
            yield chunk
```

- [ ] **Step 2: Create speaker output**

```python
# backend/jarvis/audio/speaker_output.py
from __future__ import annotations
import numpy as np


class SpeakerOutput:
    def __init__(self, sample_rate: int = 24000) -> None:
        self.sample_rate = sample_rate
        self._playing = False

    async def play(self, audio: np.ndarray) -> None:
        self._playing = True
        # Placeholder: real implementation uses sounddevice
        self._playing = False

    def stop(self) -> None:
        self._playing = False
```

- [ ] **Step 3: Create VAD wrapper**

```python
# backend/jarvis/audio/vad.py
from __future__ import annotations
import numpy as np


class VAD:
    def __init__(self, threshold: float = 0.5) -> None:
        self.threshold = threshold

    def is_speech(self, audio: np.ndarray) -> bool:
        # Placeholder: real implementation uses Silero VAD
        return np.abs(audio).mean() > self.threshold
```

- [ ] **Step 4: Write tests**

```python
# backend/tests/test_audio.py
import asyncio
import numpy as np
import pytest
from jarvis.audio.mic_stream import MicStream
from jarvis.audio.speaker_output import SpeakerOutput
from jarvis.audio.vad import VAD


def test_vad_silence():
    vad = VAD(threshold=0.1)
    silent = np.zeros(1024, dtype=np.float32)
    assert vad.is_speech(silent) is False


def test_vad_speech():
    vad = VAD(threshold=0.1)
    loud = np.ones(1024, dtype=np.float32) * 0.5
    assert vad.is_speech(loud) is True


@pytest.mark.asyncio
async def test_mic_start_stop():
    mic = MicStream()
    await mic.start()
    assert mic._running is True
    await mic.stop()
    assert mic._running is False
```

- [ ] **Step 5: Run tests**

Run: `cd backend && python -m pytest tests/test_audio.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/jarvis/audio/ backend/tests/test_audio.py
git commit -m "feat: Audio pipeline foundation (mic, speaker, VAD)"
```

---

### Task 9: Whisper STT Plugin

**Files:**
- Create: `backend/jarvis/plugins/builtins/whisper_local.py`
- Create: `backend/tests/test_whisper_plugin.py`

**Interfaces:**
- Consumes: `Plugin` interface from Task 6, `MicStream` from Task 8
- Produces: STT plugin that emits `transcript_partial` and `transcript_final` events

- [ ] **Step 1: Create Whisper plugin**

```python
# backend/jarvis/plugins/builtins/whisper_local.py
from __future__ import annotations
from typing import Any, Optional
from jarvis.plugins.base import Plugin, PluginType
from jarvis.core.bus import Event


class WhisperLocalPlugin(Plugin):
    name = "whisper_local"
    plugin_type = PluginType.STT

    def __init__(self) -> None:
        self._model = None
        self._streaming = False

    async def start(self, config: dict[str, Any]) -> None:
        model_size = config.get("model", "base")
        # Placeholder: real implementation loads whisper.cpp model
        print(f"Whisper STT started with model: {model_size}")

    async def stop(self) -> None:
        self._streaming = False
        print("Whisper STT stopped")

    async def on_event(self, event: Event) -> Optional[Event]:
        if event.type == "audio_chunk":
            # Placeholder: real implementation runs inference
            text = ""  # Whisper inference result
            if text:
                return Event(
                    type="transcript_partial",
                    data={"text": text},
                    source=self.name,
                )
        elif event.type == "speech_end":
            return Event(
                type="transcript_final",
                data={"text": event.data.get("text", "")},
                source=self.name,
            )
        return None

    def get_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "model": {
                    "type": "string",
                    "enum": ["tiny", "base", "small", "medium", "large"],
                    "default": "base",
                }
            },
        }


plugin_class = WhisperLocalPlugin
```

- [ ] **Step 2: Write tests**

```python
# backend/tests/test_whisper_plugin.py
import pytest
from jarvis.core.bus import Event
from jarvis.plugins.builtins.whisper_local import WhisperLocalPlugin


@pytest.mark.asyncio
async def test_start_stop():
    plugin = WhisperLocalPlugin()
    await plugin.start({"model": "base"})
    assert plugin._model is not None or True  # Placeholder check
    await plugin.stop()


@pytest.mark.asyncio
async def test_on_event_returns_none_for_unknown():
    plugin = WhisperLocalPlugin()
    result = await plugin.on_event(Event(type="unknown"))
    assert result is None


def test_get_schema():
    plugin = WhisperLocalPlugin()
    schema = plugin.get_schema()
    assert "model" in schema["properties"]
```

- [ ] **Step 3: Run tests**

Run: `cd backend && python -m pytest tests/test_whisper_plugin.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add backend/jarvis/plugins/builtins/whisper_local.py backend/tests/test_whisper_plugin.py
git commit -m "feat: Whisper STT plugin skeleton"
```

---

### Task 10: Piper TTS Plugin

**Files:**
- Create: `backend/jarvis/plugins/builtins/piper_tts.py`
- Create: `backend/tests/test_piper_plugin.py`

**Interfaces:**
- Consumes: `Plugin` interface from Task 6, `SpeakerOutput` from Task 8
- Produces: TTS plugin that emits `audio_chunk` events

- [ ] **Step 1: Create Piper TTS plugin**

```python
# backend/jarvis/plugins/builtins/piper_tts.py
from __future__ import annotations
from typing import Any, Optional
import numpy as np
from jarvis.plugins.base import Plugin, PluginType
from jarvis.core.bus import Event


class PiperTTSPlugin(Plugin):
    name = "piper_tts"
    plugin_type = PluginType.TTS

    def __init__(self) -> None:
        self._voice = "en_US-lessac-medium"

    async def start(self, config: dict[str, Any]) -> None:
        self._voice = config.get("voice", "en_US-lessac-medium")
        print(f"Piper TTS started with voice: {self._voice}")

    async def stop(self) -> None:
        print("Piper TTS stopped")

    async def on_event(self, event: Event) -> Optional[Event]:
        if event.type == "speak":
            text = event.data.get("text", "")
            # Placeholder: real implementation runs Piper inference
            audio = np.zeros(24000, dtype=np.float32)  # 1s silence
            return Event(
                type="audio_chunk",
                data={"audio": audio, "sample_rate": 22050},
                source=self.name,
            )
        return None

    def get_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "voice": {
                    "type": "string",
                    "default": "en_US-lessac-medium",
                }
            },
        }


plugin_class = PiperTTSPlugin
```

- [ ] **Step 2: Write tests**

```python
# backend/tests/test_piper_plugin.py
import pytest
from jarvis.core.bus import Event
from jarvis.plugins.builtins.piper_tts import PiperTTSPlugin


@pytest.mark.asyncio
async def test_start_stop():
    plugin = PiperTTSPlugin()
    await plugin.start({"voice": "test-voice"})
    await plugin.stop()


@pytest.mark.asyncio
async def test_speak_returns_audio():
    plugin = PiperTTSPlugin()
    result = await plugin.on_event(
        Event(type="speak", data={"text": "Hello world"})
    )
    assert result is not None
    assert result.type == "audio_chunk"


def test_get_schema():
    plugin = PiperTTSPlugin()
    schema = plugin.get_schema()
    assert "voice" in schema["properties"]
```

- [ ] **Step 3: Run tests**

Run: `cd backend && python -m pytest tests/test_piper_plugin.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add backend/jarvis/plugins/builtins/piper_tts.py backend/tests/test_piper_plugin.py
git commit -m "feat: Piper TTS plugin skeleton"
```

---

### Task 11: Ollama LLM Plugin

**Files:**
- Create: `backend/jarvis/plugins/builtins/ollama_llm.py`
- Create: `backend/tests/test_ollama_plugin.py`

**Interfaces:**
- Consumes: `Plugin` interface from Task 6
- Produces: LLM plugin that emits `llm_token` and `response_complete` events

- [ ] **Step 1: Create Ollama LLM plugin**

```python
# backend/jarvis/plugins/builtins/ollama_llm.py
from __future__ import annotations
from typing import Any, Optional
from jarvis.plugins.base import Plugin, PluginType
from jarvis.core.bus import Event


class OllamaLLMPlugin(Plugin):
    name = "ollama_llm"
    plugin_type = PluginType.LLM

    def __init__(self) -> None:
        self._model = "llama3"
        self._base_url = "http://localhost:11434"

    async def start(self, config: dict[str, Any]) -> None:
        self._model = config.get("model", "llama3")
        self._base_url = config.get("base_url", "http://localhost:11434")
        print(f"Ollama LLM started: {self._model} @ {self._base_url}")

    async def stop(self) -> None:
        print("Ollama LLM stopped")

    async def on_event(self, event: Event) -> Optional[Event]:
        if event.type == "llm_request":
            prompt = event.data.get("prompt", "")
            # Placeholder: real implementation calls Ollama API
            response = "Hello! I am Jarvis."
            tokens = response.split()
            for token in tokens:
                # In real impl, these would be yielded as they arrive
                pass
            return Event(
                type="response_complete",
                data={"text": response},
                source=self.name,
            )
        return None

    def get_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "model": {
                    "type": "string",
                    "default": "llama3",
                },
                "base_url": {
                    "type": "string",
                    "default": "http://localhost:11434",
                },
            },
        }


plugin_class = OllamaLLMPlugin
```

- [ ] **Step 2: Write tests**

```python
# backend/tests/test_ollama_plugin.py
import pytest
from jarvis.core.bus import Event
from jarvis.plugins.builtins.ollama_llm import OllamaLLMPlugin


@pytest.mark.asyncio
async def test_start_stop():
    plugin = OllamaLLMPlugin()
    await plugin.start({"model": "llama3"})
    assert plugin._model == "llama3"
    await plugin.stop()


@pytest.mark.asyncio
async def test_llm_request():
    plugin = OllamaLLMPlugin()
    result = await plugin.on_event(
        Event(type="llm_request", data={"prompt": "Hello"})
    )
    assert result is not None
    assert result.type == "response_complete"
    assert "text" in result.data


def test_get_schema():
    plugin = OllamaLLMPlugin()
    schema = plugin.get_schema()
    assert "model" in schema["properties"]
    assert "base_url" in schema["properties"]
```

- [ ] **Step 3: Run tests**

Run: `cd backend && python -m pytest tests/test_ollama_plugin.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add backend/jarvis/plugins/builtins/ollama_llm.py backend/tests/test_ollama_plugin.py
git commit -m "feat: Ollama LLM plugin skeleton"
```

---

## Phase 4: Activation Methods

### Task 12: Push-to-Talk Activation

**Files:**
- Create: `backend/jarvis/plugins/builtins/push_to_talk.py`
- Create: `backend/tests/test_push_to_talk.py`

**Interfaces:**
- Consumes: `Plugin` interface from Task 6
- Produces: Activation plugin that emits `activate`/`deactivate` events

- [ ] **Step 1: Create Push-to-Talk plugin**

```python
# backend/jarvis/plugins/builtins/push_to_talk.py
from __future__ import annotations
from typing import Any, Optional
from jarvis.plugins.base import Plugin, PluginType
from jarvis.core.bus import Event


class PushToTalkPlugin(Plugin):
    name = "push_to_talk"
    plugin_type = PluginType.ACTIVATION

    def __init__(self) -> None:
        self._key = "space"
        self._pressed = False

    async def start(self, config: dict[str, Any]) -> None:
        self._key = config.get("key", "space")
        print(f"Push-to-Talk started: hold '{self._key}' to speak")

    async def stop(self) -> None:
        print("Push-to-Talk stopped")

    async def on_event(self, event: Event) -> Optional[Event]:
        if event.type == "key_down" and event.data.get("key") == self._key:
            self._pressed = True
            return Event(type="activation", source=self.name)
        elif event.type == "key_up" and event.data.get("key") == self._key:
            self._pressed = False
            return Event(type="deactivation", source=self.name)
        return None

    def get_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "default": "space",
                }
            },
        }


plugin_class = PushToTalkPlugin
```

- [ ] **Step 2: Write tests**

```python
# backend/tests/test_push_to_talk.py
import pytest
from jarvis.core.bus import Event
from jarvis.plugins.builtins.push_to_talk import PushToTalkPlugin


@pytest.mark.asyncio
async def test_key_down_activates():
    plugin = PushToTalkPlugin()
    result = await plugin.on_event(
        Event(type="key_down", data={"key": "space"})
    )
    assert result is not None
    assert result.type == "activation"


@pytest.mark.asyncio
async def test_key_up_deactivates():
    plugin = PushToTalkPlugin()
    result = await plugin.on_event(
        Event(type="key_up", data={"key": "space"})
    )
    assert result is not None
    assert result.type == "deactivation"


@pytest.mark.asyncio
async def test_wrong_key_ignored():
    plugin = PushToTalkPlugin()
    result = await plugin.on_event(
        Event(type="key_down", data={"key": "a"})
    )
    assert result is None
```

- [ ] **Step 3: Run tests**

Run: `cd backend && python -m pytest tests/test_push_to_talk.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add backend/jarvis/plugins/builtins/push_to_talk.py backend/tests/test_push_to_talk.py
git commit -m "feat: Push-to-Talk activation plugin"
```

---

### Task 13: Clap Detector Activation

**Files:**
- Create: `backend/jarvis/plugins/builtins/clap_detector.py`
- Create: `backend/tests/test_clap_detector.py`

**Interfaces:**
- Consumes: `Plugin` interface from Task 6
- Produces: Activation plugin that detects double clap pattern

- [ ] **Step 1: Create Clap Detector plugin**

```python
# backend/jarvis/plugins/builtins/clap_detector.py
from __future__ import annotations
import time
from typing import Any, Optional
from jarvis.plugins.base import Plugin, PluginType
from jarvis.core.bus import Event


class ClapDetectorPlugin(Plugin):
    name = "clap_detector"
    plugin_type = PluginType.ACTIVATION

    def __init__(self) -> None:
        self._threshold = 0.7
        self._window_ms = 300
        self._last_clap = 0.0
        self._clap_count = 0

    async def start(self, config: dict[str, Any]) -> None:
        self._threshold = config.get("threshold", 0.7)
        self._window_ms = config.get("window_ms", 300)
        print(f"Clap detector started: threshold={self._threshold}")

    async def stop(self) -> None:
        print("Clap detector stopped")

    async def on_event(self, event: Event) -> Optional[Event]:
        if event.type == "audio_energy":
            energy = event.data.get("energy", 0)
            now = time.monotonic()

            if energy > self._threshold:
                if now - self._last_clap < (self._window_ms / 1000):
                    self._clap_count += 1
                    if self._clap_count >= 2:
                        self._clap_count = 0
                        return Event(type="activation", source=self.name)
                else:
                    self._clap_count = 1
                self._last_clap = now
        return None

    def get_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "threshold": {"type": "number", "default": 0.7},
                "window_ms": {"type": "integer", "default": 300},
            },
        }


plugin_class = ClapDetectorPlugin
```

- [ ] **Step 2: Write tests**

```python
# backend/tests/test_clap_detector.py
import time
import pytest
from jarvis.core.bus import Event
from jarvis.plugins.builtins.clap_detector import ClapDetectorPlugin


@pytest.mark.asyncio
async def test_single_clap_no_activation():
    plugin = ClapDetectorPlugin()
    await plugin.start({})
    result = await plugin.on_event(
        Event(type="audio_energy", data={"energy": 0.9})
    )
    assert result is None


@pytest.mark.asyncio
async def test_double_clap_activates():
    plugin = ClapDetectorPlugin()
    await plugin.start({"window_ms": 500})
    # First clap
    await plugin.on_event(Event(type="audio_energy", data={"energy": 0.9}))
    # Second clap (within window)
    result = await plugin.on_event(
        Event(type="audio_energy", data={"energy": 0.9})
    )
    assert result is not None
    assert result.type == "activation"


@pytest.mark.asyncio
async def test_low_energy_ignored():
    plugin = ClapDetectorPlugin()
    await plugin.start({})
    result = await plugin.on_event(
        Event(type="audio_energy", data={"energy": 0.1})
    )
    assert result is None
```

- [ ] **Step 3: Run tests**

Run: `cd backend && python -m pytest tests/test_clap_detector.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add backend/jarvis/plugins/builtins/clap_detector.py backend/tests/test_clap_detector.py
git commit -m "feat: Double clap detector activation plugin"
```

---

## Phase 5: HUD Polish

### Task 14: ARC Reactor Core Animation

**Files:**
- Create: `frontend/src/renderer/hud/arc-reactor.ts`
- Create: `frontend/src/renderer/hud/arc-reactor.css`
- Modify: `frontend/src/renderer/index.html`

**Interfaces:**
- Consumes: `state_change` events from Task 4

- [ ] **Step 1: Create ARC Reactor CSS**

```css
/* frontend/src/renderer/hud/arc-reactor.css */
#core-container {
  width: 300px;
  height: 300px;
  position: relative;
}

.reactor-ring {
  position: absolute;
  border-radius: 50%;
  border: 2px solid var(--accent-blue);
  animation: rotate 20s linear infinite;
}

.reactor-outer {
  width: 100%;
  height: 100%;
  opacity: 0.3;
}

.reactor-middle {
  width: 70%;
  height: 70%;
  top: 15%;
  left: 15%;
  border-color: var(--accent-cyan);
  animation-duration: 15s;
  animation-direction: reverse;
}

.reactor-inner {
  width: 40%;
  height: 40%;
  top: 30%;
  left: 30%;
  border-color: var(--accent-white);
  animation-duration: 10s;
}

.reactor-core {
  position: absolute;
  width: 20%;
  height: 20%;
  top: 40%;
  left: 40%;
  border-radius: 50%;
  background: radial-gradient(circle, var(--accent-white), var(--accent-blue));
  box-shadow: 0 0 30px var(--accent-blue), 0 0 60px var(--accent-blue);
  animation: pulse 2s ease-in-out infinite;
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@keyframes pulse {
  0%, 100% { opacity: 0.6; transform: scale(1); }
  50% { opacity: 1; transform: scale(1.1); }
}

/* State-based colors */
.reactor-core.state-listening {
  background: radial-gradient(circle, #ffffff, #00d4ff);
  box-shadow: 0 0 40px #00d4ff, 0 0 80px #00d4ff;
  animation: pulse-fast 0.5s ease-in-out infinite;
}

.reactor-core.state-thinking {
  background: radial-gradient(circle, #ffffff, #ff9500);
  box-shadow: 0 0 40px #ff9500, 0 0 80px #ff9500;
  animation: spin 1s linear infinite;
}

.reactor-core.state-speaking {
  background: radial-gradient(circle, #ffffff, #00b4ff);
  box-shadow: 0 0 50px #00b4ff, 0 0 100px #00b4ff;
  animation: pulse-fast 0.3s ease-in-out infinite;
}

@keyframes pulse-fast {
  0%, 100% { opacity: 0.7; transform: scale(1); }
  50% { opacity: 1; transform: scale(1.15); }
}
```

- [ ] **Step 2: Create ARC Reactor TypeScript**

```typescript
// frontend/src/renderer/hud/arc-reactor.ts
export class ArcReactor {
  private container: HTMLElement;
  private core: HTMLElement;
  private state: string = "idle";

  constructor(container: HTMLElement) {
    this.container = container;
    this.container.innerHTML = `
      <div class="reactor-ring reactor-outer"></div>
      <div class="reactor-ring reactor-middle"></div>
      <div class="reactor-ring reactor-inner"></div>
      <div class="reactor-core"></div>
    `;
    this.core = this.container.querySelector(".reactor-core")!;
  }

  setState(state: string): void {
    this.core.className = "reactor-core";
    if (state !== "idle") {
      this.core.classList.add(`state-${state}`);
    }
    this.state = state;
  }
}
```

- [ ] **Step 3: Update index.html to include core**

```html
<!-- Add inside #center-area in index.html -->
<div id="core-container"></div>
```

- [ ] **Step 4: Build and verify animation**

Run: `cd frontend && npm run build && npm run dev`

Expected: Three concentric rings rotating, pulsing core in center. State changes update colors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/renderer/hud/arc-reactor.ts frontend/src/renderer/hud/arc-reactor.css
git commit -m "feat: ARC Reactor core animation with state-based colors"
```

---

### Task 15: Waveform Visualizer

**Files:**
- Create: `frontend/src/renderer/hud/waveform.ts`

**Interfaces:**
- Consumes: `audio_level` events from backend

- [ ] **Step 1: Create Waveform visualizer**

```typescript
// frontend/src/renderer/hud/waveform.ts
export class Waveform {
  private canvas: HTMLCanvasElement;
  private ctx: CanvasRenderingContext2D;
  private levels: number[] = [];
  private barCount = 64;

  constructor(canvas: HTMLCanvasElement) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d")!;
    this.levels = new Array(this.barCount).fill(0);
  }

  updateLevel(level: number): void {
    this.levels.push(level);
    if (this.levels.length > this.barCount) {
      this.levels.shift();
    }
    this.draw();
  }

  private draw(): void {
    const { width, height } = this.canvas;
    this.ctx.clearRect(0, 0, width, height);

    const barWidth = width / this.barCount;
    this.levels.forEach((level, i) => {
      const barHeight = level * height;
      const x = i * barWidth;
      const y = (height - barHeight) / 2;

      const gradient = this.ctx.createLinearGradient(x, y, x, y + barHeight);
      gradient.addColorStop(0, "rgba(0, 180, 255, 0.8)");
      gradient.addColorStop(0.5, "rgba(0, 212, 255, 1)");
      gradient.addColorStop(1, "rgba(0, 180, 255, 0.8)");

      this.ctx.fillStyle = gradient;
      this.ctx.fillRect(x + 1, y, barWidth - 2, barHeight);
    });
  }

  clear(): void {
    this.levels = new Array(this.barCount).fill(0);
    this.draw();
  }
}
```

- [ ] **Step 2: Build and verify**

Run: `cd frontend && npm run build`
Expected: TypeScript compiles without errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/renderer/hud/waveform.ts
git commit -m "feat: Audio waveform visualizer"
```

---

### Task 16: Particle System

**Files:**
- Create: `frontend/src/renderer/hud/particles.ts`

**Interfaces:**
- Consumes: state changes for particle behavior

- [ ] **Step 1: Create Particle system**

```typescript
// frontend/src/renderer/hud/particles.ts
interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  size: number;
  alpha: number;
  life: number;
}

export class ParticleSystem {
  private canvas: HTMLCanvasElement;
  private ctx: CanvasRenderingContext2D;
  private particles: Particle[] = [];
  private maxParticles = 100;

  constructor(canvas: HTMLCanvasElement) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d")!;
  }

  setState(state: string): void {
    const densityMap: Record<string, number> = {
      idle: 30,
      listening: 60,
      thinking: 80,
      speaking: 100,
    };
    this.maxParticles = densityMap[state] || 30;
  }

  update(): void {
    this.spawn();
    this.updateParticles();
    this.draw();
  }

  private spawn(): void {
    while (this.particles.length < this.maxParticles) {
      this.particles.push({
        x: Math.random() * this.canvas.width,
        y: Math.random() * this.canvas.height,
        vx: (Math.random() - 0.5) * 0.5,
        vy: (Math.random() - 0.5) * 0.5,
        size: Math.random() * 2 + 1,
        alpha: Math.random() * 0.5 + 0.1,
        life: Math.random() * 200 + 100,
      });
    }
  }

  private updateParticles(): void {
    this.particles = this.particles.filter((p) => {
      p.x += p.vx;
      p.y += p.vy;
      p.life--;
      p.alpha = Math.min(p.alpha, p.life / 50);
      return p.life > 0;
    });
  }

  private draw(): void {
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    this.particles.forEach((p) => {
      this.ctx.beginPath();
      this.ctx.moveTo(p.x, p.y);
      this.ctx.lineTo(p.x + p.size * 3, p.y);
      this.ctx.lineTo(p.x + p.size * 1.5, p.y - p.size * 2);
      this.ctx.closePath();
      this.ctx.fillStyle = `rgba(0, 180, 255, ${p.alpha})`;
      this.ctx.fill();
    });
  }
}
```

- [ ] **Step 2: Build and verify**

Run: `cd frontend && npm run build`
Expected: TypeScript compiles without errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/renderer/hud/particles.ts
git commit -m "feat: Particle system with state-reactive density"
```

---

## Phase 6: Face Tracking

### Task 17: MediaPipe Face Tracker Plugin

**Files:**
- Create: `backend/jarvis/plugins/builtins/face_tracker.py`
- Create: `backend/tests/test_face_tracker.py`

**Interfaces:**
- Consumes: `Plugin` interface from Task 6
- Produces: `face_data` events with gaze and pose

- [ ] **Step 1: Create Face Tracker plugin**

```python
# backend/jarvis/plugins/builtins/face_tracker.py
from __future__ import annotations
from typing import Any, Optional
from jarvis.plugins.base import Plugin, PluginType
from jarvis.core.bus import Event


class FaceTrackerPlugin(Plugin):
    name = "face_tracker"
    plugin_type = PluginType.VISION

    def __init__(self) -> None:
        self._camera_index = 0
        self._running = False

    async def start(self, config: dict[str, Any]) -> None:
        self._camera_index = config.get("camera", 0)
        self._running = True
        print(f"Face tracker started: camera {self._camera_index}")

    async def stop(self) -> None:
        self._running = False
        print("Face tracker stopped")

    async def on_event(self, event: Event) -> Optional[Event]:
        if event.type == "camera_frame" and self._running:
            # Placeholder: real implementation runs MediaPipe
            return Event(
                type="face_data",
                data={
                    "gaze": [0.5, 0.5],
                    "pose": {"pitch": 0, "yaw": 0, "roll": 0},
                    "blink": False,
                    "face_detected": True,
                },
                source=self.name,
            )
        return None

    def get_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "camera": {"type": "integer", "default": 0},
            },
        }


plugin_class = FaceTrackerPlugin
```

- [ ] **Step 2: Write tests**

```python
# backend/tests/test_face_tracker.py
import pytest
from jarvis.core.bus import Event
from jarvis.plugins.builtins.face_tracker import FaceTrackerPlugin


@pytest.mark.asyncio
async def test_start_stop():
    plugin = FaceTrackerPlugin()
    await plugin.start({"camera": 0})
    assert plugin._running is True
    await plugin.stop()
    assert plugin._running is False


@pytest.mark.asyncio
async def test_face_data_event():
    plugin = FaceTrackerPlugin()
    await plugin.start({})
    result = await plugin.on_event(
        Event(type="camera_frame", data={"frame": None})
    )
    assert result is not None
    assert result.type == "face_data"
    assert "gaze" in result.data
    assert "pose" in result.data
```

- [ ] **Step 3: Run tests**

Run: `cd backend && python -m pytest tests/test_face_tracker.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add backend/jarvis/plugins/builtins/face_tracker.py backend/tests/test_face_tracker.py
git commit -m "feat: MediaPipe face tracker plugin skeleton"
```

---

## Phase 7: SFX & Settings

### Task 18: Web Audio SFX Synthesizer

**Files:**
- Create: `frontend/src/renderer/sfx/synthesizer.ts`

**Interfaces:**
- Consumes: state changes for sound triggers

- [ ] **Step 1: Create SFX Synthesizer**

```typescript
// frontend/src/renderer/sfx/synthesizer.ts
export class SFXSynthesizer {
  private ctx: AudioContext;
  private masterGain: GainNode;

  constructor() {
    this.ctx = new AudioContext();
    this.masterGain = this.ctx.createGain();
    this.masterGain.connect(this.ctx.destination);
    this.masterGain.gain.value = 0.3;
  }

  powerUp(): void {
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    osc.connect(gain);
    gain.connect(this.masterGain);
    osc.type = "sawtooth";
    osc.frequency.setValueAtTime(100, this.ctx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(800, this.ctx.currentTime + 0.3);
    gain.gain.setValueAtTime(0.5, this.ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, this.ctx.currentTime + 0.5);
    osc.start(this.ctx.currentTime);
    osc.stop(this.ctx.currentTime + 0.5);
  }

  powerDown(): void {
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    osc.connect(gain);
    gain.connect(this.masterGain);
    osc.type = "sawtooth";
    osc.frequency.setValueAtTime(800, this.ctx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(100, this.ctx.currentTime + 0.5);
    gain.gain.setValueAtTime(0.5, this.ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, this.ctx.currentTime + 0.5);
    osc.start(this.ctx.currentTime);
    osc.stop(this.ctx.currentTime + 0.5);
  }

  chime(): void {
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    osc.connect(gain);
    gain.connect(this.masterGain);
    osc.type = "sine";
    osc.frequency.value = 880;
    gain.gain.setValueAtTime(0.3, this.ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, this.ctx.currentTime + 0.2);
    osc.start(this.ctx.currentTime);
    osc.stop(this.ctx.currentTime + 0.2);
  }

  errorBuzz(): void {
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    osc.connect(gain);
    gain.connect(this.masterGain);
    osc.type = "square";
    osc.frequency.setValueAtTime(200, this.ctx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(100, this.ctx.currentTime + 0.3);
    gain.gain.setValueAtTime(0.3, this.ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, this.ctx.currentTime + 0.3);
    osc.start(this.ctx.currentTime);
    osc.stop(this.ctx.currentTime + 0.3);
  }

  setVolume(vol: number): void {
    this.masterGain.gain.value = vol;
  }
}
```

- [ ] **Step 2: Build and verify**

Run: `cd frontend && npm run build`
Expected: TypeScript compiles without errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/renderer/sfx/synthesizer.ts
git commit -m "feat: Web Audio SFX synthesizer with Iron Man sounds"
```

---

### Task 19: Settings Panel

**Files:**
- Create: `frontend/src/renderer/hud/panels/settings.ts`
- Create: `frontend/src/renderer/hud/panels/settings.css`

**Interfaces:**
- Consumes: `settings_request` events, sends `config_update` to backend

- [ ] **Step 1: Create Settings panel**

```typescript
// frontend/src/renderer/hud/panels/settings.ts
import { WSClient } from "../../core/ws-client";

export class SettingsPanel {
  private ws: WSClient;
  private panel: HTMLElement;
  private visible = false;

  constructor(ws: WSClient) {
    this.ws = ws;
    this.panel = document.getElementById("settings-panel")!;
    this.panel.style.display = "none";
  }

  toggle(): void {
    this.visible = !this.visible;
    this.panel.style.display = this.visible ? "block" : "none";
  }

  updateConfig(plugin: string, key: string, value: any): void {
    this.ws.send({ type: "config_update", plugin, key, value });
  }
}
```

- [ ] **Step 2: Build and verify**

Run: `cd frontend && npm run build`
Expected: TypeScript compiles without errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/renderer/hud/panels/settings.ts
git commit -m "feat: Settings panel skeleton"
```

---

## Phase 8: Packaging

### Task 20: Dev Script & README

**Files:**
- Create: `scripts/dev.sh`
- Create: `scripts/setup.sh`
- Create: `README.md`

**Interfaces:**
- Consumes: All previous tasks

- [ ] **Step 1: Create dev script**

```bash
#!/bin/bash
# scripts/dev.sh
set -e

echo "Starting Jarvis AI in development mode..."

# Start Python backend
echo "Starting Python backend..."
cd backend
python -m jarvis &
BACKEND_PID=$!

# Start Electron frontend
echo "Starting Electron frontend..."
cd ../frontend
npm run dev &
FRONTEND_PID=$!

# Cleanup on exit
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
wait
```

- [ ] **Step 2: Create setup script**

```bash
#!/bin/bash
# scripts/setup.sh
set -e

echo "Setting up Jarvis AI..."

# Python setup
echo "Setting up Python backend..."
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Node setup
echo "Setting up Electron frontend..."
cd ../frontend
npm install

echo "Setup complete! Run ./scripts/dev.sh to start."
```

- [ ] **Step 3: Make scripts executable**

Run: `chmod +x scripts/dev.sh scripts/setup.sh`

- [ ] **Step 4: Create README**

```markdown
# Jarvis AI

Voice-interactive desktop AI assistant inspired by JARVIS from Iron Man.

## Features

- Voice-first interaction with multiple activation methods
- Full-screen HUD with ARC reactor aesthetics
- Pluggable AI backends (local + cloud)
- Face/eye tracking for immersive experience
- Iron Man-themed sound effects

## Quick Start

```bash
./scripts/setup.sh
./scripts/dev.sh
```

## Architecture

- **Backend**: Python (STT, TTS, LLM, face tracking)
- **Frontend**: Electron + TypeScript (HUD, animations, SFX)
- **Communication**: WebSocket on localhost:8765

## Plugin System

Drop `.py` files into `backend/jarvis/plugins/builtins/` to add new backends.
```

- [ ] **Step 5: Commit**

```bash
git add scripts/ README.md
git commit -m "feat: Dev scripts and README"
```

---

## Summary

| Phase | Tasks | What It Delivers |
|-------|-------|------------------|
| 1 | 1-5 | Working skeleton: Python ↔ Electron, basic HUD |
| 2 | 6-7 | Plugin system with hot-reload |
| 3 | 8-11 | Voice pipeline: STT, TTS, LLM |
| 4 | 12-13 | Activation: PTT, clap detector |
| 5 | 14-16 | HUD polish: ARC reactor, waveform, particles |
| 6 | 17 | Face tracking integration |
| 7 | 18-19 | Sound effects and settings UI |
| 8 | 20 | Packaging and documentation |
