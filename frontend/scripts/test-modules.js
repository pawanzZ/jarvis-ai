/**
 * Jarvis AI - Frontend Module Verification Suite
 * Tests class exports, initialization, and method contracts in dist/
 */

const assert = require('assert');

// 1. Verify types module loads
const types = require('../dist/renderer/core/types');
assert(types.DEFAULT_SETTINGS, 'DEFAULT_SETTINGS must be exported');
assert.strictEqual(types.DEFAULT_SETTINGS.brain.model, 'llama3');
assert.strictEqual(types.DEFAULT_SETTINGS.appearance.theme, 'arc');
console.log('✓ types.js exports verified');

// 2. Verify ws-client module loads
const { WSClient } = require('../dist/renderer/core/ws-client');
assert(WSClient, 'WSClient class must be exported');
const ws = new WSClient('ws://localhost:8765');
assert.strictEqual(typeof ws.connect, 'function');
assert.strictEqual(typeof ws.send, 'function');
assert.strictEqual(typeof ws.on, 'function');
assert.strictEqual(typeof ws.off, 'function');
assert.strictEqual(typeof ws.activate, 'function');
assert.strictEqual(typeof ws.deactivate, 'function');
assert.strictEqual(typeof ws.updateConfig, 'function');
assert.strictEqual(typeof ws.requestSettings, 'function');
console.log('✓ ws-client.js verified');

// 3. Verify SFXSynthesizer class
const { SFXSynthesizer } = require('../dist/renderer/sfx/synthesizer');
assert(SFXSynthesizer, 'SFXSynthesizer class must be exported');
const sfx = new SFXSynthesizer(0.6);
assert.strictEqual(typeof sfx.powerUp, 'function');
assert.strictEqual(typeof sfx.powerDown, 'function');
assert.strictEqual(typeof sfx.chime, 'function');
assert.strictEqual(typeof sfx.errorBuzz, 'function');
assert.strictEqual(typeof sfx.startListeningHum, 'function');
assert.strictEqual(typeof sfx.stopListeningHum, 'function');
assert.strictEqual(typeof sfx.thinkingWhirr, 'function');
assert.strictEqual(typeof sfx.playStateSound, 'function');
console.log('✓ synthesizer.js verified');

// 4. Verify DOM-dependent modules exports
const { ArcReactor } = require('../dist/renderer/hud/arc-reactor');
assert(ArcReactor, 'ArcReactor class must be exported');

const { Waveform } = require('../dist/renderer/hud/waveform');
assert(Waveform, 'Waveform class must be exported');

const { ParticleSystem } = require('../dist/renderer/hud/particles');
assert(ParticleSystem, 'ParticleSystem class must be exported');

const { StatusBar } = require('../dist/renderer/hud/status-bar');
assert(StatusBar, 'StatusBar class must be exported');

const { TranscriptBar } = require('../dist/renderer/hud/transcript-bar');
assert(TranscriptBar, 'TranscriptBar class must be exported');

const { SettingsPanel } = require('../dist/renderer/hud/panels/settings');
assert(SettingsPanel, 'SettingsPanel class must be exported');

const { JarvisApp } = require('../dist/renderer/core/app');
assert(JarvisApp, 'JarvisApp class must be exported');

console.log('✓ All frontend component classes and interfaces successfully verified!');
