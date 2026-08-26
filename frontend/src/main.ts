/**
 * Jarvis AI - Electron Main Process
 * Creates frameless fullscreen HUD window with alpha transparency,
 * global keyboard shortcut hooks, IPC window controls, and lifecycle handlers.
 */

import { app, BrowserWindow, ipcMain, globalShortcut } from "electron";
import path from "path";
import fs from "fs";

let mainWindow: BrowserWindow | null = null;

function createWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1920,
    height: 1080,
    fullscreen: true,
    frame: false,
    transparent: true,
    backgroundColor: "#00000000",
    hasShadow: false,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  // Resolve index.html from dist/ or fallback to src/
  const distHtmlPath = path.join(__dirname, "renderer", "index.html");
  const srcHtmlPath = path.join(__dirname, "..", "src", "renderer", "index.html");

  if (fs.existsSync(distHtmlPath)) {
    mainWindow.loadFile(distHtmlPath);
  } else if (fs.existsSync(srcHtmlPath)) {
    mainWindow.loadFile(srcHtmlPath);
  } else {
    console.error("[Main] Failed to locate index.html");
  }

  // Register developer shortcuts
  mainWindow.webContents.on("before-input-event", (event, input) => {
    if (input.key === "F12" || (input.control && input.shift && input.key.toLowerCase() === "i")) {
      mainWindow?.webContents.toggleDevTools();
      event.preventDefault();
    }
  });

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

// IPC Window Control Handlers
ipcMain.on("window-minimize", () => {
  mainWindow?.minimize();
});

ipcMain.on("window-toggle-fullscreen", () => {
  if (mainWindow) {
    mainWindow.setFullScreen(!mainWindow.isFullScreen());
  }
});

ipcMain.on("app-quit", () => {
  app.quit();
});

app.whenReady().then(() => {
  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("will-quit", () => {
  globalShortcut.unregisterAll();
});
