/**
 * Jarvis AI - Electron Preload Script
 * Exposes safe, typed IPC APIs to the renderer process via ContextBridge.
 */

import { contextBridge, ipcRenderer } from "electron";

contextBridge.exposeInMainWorld("jarvis", {
  platform: process.platform,
  version: "0.1.0",
  minimizeWindow: () => ipcRenderer.send("window-minimize"),
  toggleFullscreen: () => ipcRenderer.send("window-toggle-fullscreen"),
  quitApp: () => ipcRenderer.send("app-quit"),
});
