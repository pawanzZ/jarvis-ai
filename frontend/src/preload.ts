import { contextBridge } from "electron";

contextBridge.exposeInMainWorld("jarvis", {
  platform: process.platform,
});
