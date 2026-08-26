/**
 * Jarvis AI - Transcript Streaming & Response Bar
 * Real-time streaming transcription bar supporting token-by-token LLM output,
 * speech recognition partial transcripts, speaker tagging, and typing cursors.
 */

import { JarvisState } from "../core/types";

export class TranscriptBar {
  private container: HTMLElement;
  private speakerLabel: HTMLElement;
  private contentEl: HTMLElement;
  private typingCursor: HTMLElement;
  private currentSpeaker: "user" | "jarvis" | "system" = "system";
  private isTyping = false;
  private currentText = "";
  private defaultPrompt = 'Say "Hey Jarvis" or tap Space to activate...';

  constructor(container: HTMLElement) {
    this.container = container;
    this.container.innerHTML = `
      <div class="transcript-speaker">
        <span id="speaker-tag">[ SYSTEM ]</span>
      </div>
      <div class="transcript-content partial" id="transcript-body">
        ${this.defaultPrompt}
        <span class="typing-cursor" style="display: none;"></span>
      </div>
    `;

    this.speakerLabel = this.container.querySelector("#speaker-tag") as HTMLElement;
    this.contentEl = this.container.querySelector("#transcript-body") as HTMLElement;
    this.typingCursor = this.container.querySelector(".typing-cursor") as HTMLElement;
  }

  public setState(state: JarvisState): void {
    if (state === "idle" && !this.currentText) {
      this.setSpeaker("system");
      this.contentEl.className = "transcript-content partial";
      this.contentEl.textContent = this.defaultPrompt;
      this.hideCursor();
    } else if (state === "listening") {
      this.setSpeaker("user");
      this.contentEl.className = "transcript-content partial";
      this.contentEl.textContent = "Listening for audio input...";
      this.showCursor();
    } else if (state === "thinking") {
      this.setSpeaker("jarvis");
      this.contentEl.className = "transcript-content partial";
      this.contentEl.textContent = "Neural inference in progress...";
      this.showCursor();
    }
  }

  public setSpeaker(speaker: "user" | "jarvis" | "system"): void {
    this.currentSpeaker = speaker;
    const tags = {
      user: "[ USER // AUDIO IN ]",
      jarvis: "[ JARVIS // NEURAL RESPONSE ]",
      system: "[ SYSTEM // STATUS ]",
    };
    this.speakerLabel.textContent = tags[speaker] || "[ UNKNOWN ]";
    this.speakerLabel.style.color =
      speaker === "user" ? "var(--accent-cyan)" : speaker === "jarvis" ? "var(--accent-gold)" : "var(--text-muted)";
  }

  /**
   * Real-time partial speech recognition update.
   */
  public setPartialTranscript(text: string): void {
    this.setSpeaker("user");
    this.currentText = text;
    this.contentEl.className = "transcript-content partial";
    this.contentEl.textContent = text || "...";
    this.showCursor();
  }

  /**
   * Finalized user transcript prompt.
   */
  public setFinalTranscript(text: string, speaker: "user" | "jarvis" = "user"): void {
    this.setSpeaker(speaker);
    this.currentText = text;
    this.contentEl.className = speaker === "user" ? "transcript-content user-speech" : "transcript-content assistant-speech";
    this.contentEl.textContent = text;
    this.hideCursor();
  }

  /**
   * Appends streamed LLM token with typing animation.
   */
  public appendToken(token: string): void {
    if (this.currentSpeaker !== "jarvis" || this.contentEl.classList.contains("partial")) {
      this.setSpeaker("jarvis");
      this.contentEl.className = "transcript-content assistant-speech";
      this.currentText = "";
      this.contentEl.textContent = "";
    }

    this.currentText += token;
    this.contentEl.textContent = this.currentText;
    this.showCursor();
  }

  /**
   * Finalizes assistant response.
   */
  public completeResponse(fullText?: string): void {
    this.setSpeaker("jarvis");
    if (fullText) {
      this.currentText = fullText;
      this.contentEl.textContent = fullText;
    }
    this.contentEl.className = "transcript-content assistant-speech";
    this.hideCursor();
  }

  public clear(): void {
    this.currentText = "";
    this.setSpeaker("system");
    this.contentEl.className = "transcript-content partial";
    this.contentEl.textContent = this.defaultPrompt;
    this.hideCursor();
  }

  private showCursor(): void {
    if (!this.typingCursor.parentElement) {
      this.contentEl.appendChild(this.typingCursor);
    }
    this.typingCursor.style.display = "inline-block";
  }

  private hideCursor(): void {
    this.typingCursor.style.display = "none";
  }
}
