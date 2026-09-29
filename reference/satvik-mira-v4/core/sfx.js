/* ============================================================================
   sfx.js — short sound effects, generated at runtime (no audio files, same
   reasoning as core/music.js: nothing fetched, nothing to license).

   Used to be five cues defined inline in index.html with their own private
   AudioContext. Now: nineteen cues on the shared context from core/audio.js
   (so they duck the same way music does), a real mute that survives a
   reload (mira_sfx_on — the old voice.muted-gated version reset every
   time), and volume follows the settings screen's one music-volume slider
   so there's a single dial rather than two the child never sees.

   Three small synthesis primitives cover all nineteen cues:
     tone()        oscillator + linear/exponential envelope (the original five)
     sweep()       a tone whose frequency ramps — pitch bends, whooshes
     noiseBurst()  filtered white noise with an envelope — footsteps, pops,
                   soft textures a pure oscillator can't make
   ========================================================================== */
import { getContext, getMaster } from './audio.js';
import { music } from './music.js';

const LS_ENABLED = 'mira_sfx_on';

let bus = null;
let noiseBuffer = null;

function ready() {
  const a = getContext();
  if (!bus) {
    bus = a.createGain();
    bus.gain.value = 1;
    bus.connect(getMaster());
  }
  return a;
}

function level() {
  // One volume dial for the whole app (the settings screen's music slider);
  // SFX just rides on top of it rather than needing a second control.
  return sfx.enabled ? Math.max(0.15, music.volume) : 0;
}

/** A single oscillator with a short attack/hold/release envelope. */
function tone(freq, at, dur, { type = 'sine', peak = 1, attack = 0.02, release = 0.12, detune = 0 } = {}) {
  if (!sfx.enabled) return;
  const a = ready();
  const t = a.currentTime + at;
  const o = a.createOscillator(), g = a.createGain();
  o.type = type; o.frequency.value = freq; o.detune.value = detune;
  const vol = peak * 0.16 * level();
  g.gain.setValueAtTime(0, t);
  g.gain.linearRampToValueAtTime(vol, t + attack);
  g.gain.setValueAtTime(vol, Math.max(t + attack, t + dur - release));
  g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
  o.connect(g).connect(bus);
  o.start(t); o.stop(t + dur + 0.05);
}

/** A tone whose pitch slides from `f0` to `f1` over `dur` — pitch bends,
 * whooshes, the little "boop-doop" greeting. */
function sweep(f0, f1, at, dur, opts = {}) {
  if (!sfx.enabled) return;
  const { type = 'sine', peak = 1 } = opts;
  const a = ready();
  const t = a.currentTime + at;
  const o = a.createOscillator(), g = a.createGain();
  o.type = type;
  o.frequency.setValueAtTime(Math.max(1, f0), t);
  o.frequency.exponentialRampToValueAtTime(Math.max(1, f1), t + dur);
  const vol = peak * 0.16 * level();
  g.gain.setValueAtTime(0, t);
  g.gain.linearRampToValueAtTime(vol, t + Math.min(0.02, dur / 4));
  g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
  o.connect(g).connect(bus);
  o.start(t); o.stop(t + dur + 0.05);
}

/** Filtered white noise — the texture a pure oscillator can't give you:
 * footsteps, a soft "pop", a whoosh. */
function noiseBurst(at, dur, { filterFreq = 900, q = 0.7, type = 'bandpass', peak = 1 } = {}) {
  if (!sfx.enabled) return;
  const a = ready();
  if (!noiseBuffer) {
    const len = a.sampleRate * 0.5;
    noiseBuffer = a.createBuffer(1, len, a.sampleRate);
    const d = noiseBuffer.getChannelData(0);
    for (let i = 0; i < len; i++) d[i] = Math.random() * 2 - 1;
  }
  const t = a.currentTime + at;
  const src = a.createBufferSource();
  src.buffer = noiseBuffer;
  const filt = a.createBiquadFilter();
  filt.type = type; filt.frequency.value = filterFreq; filt.Q.value = q;
  const g = a.createGain();
  const vol = peak * 0.18 * level();
  g.gain.setValueAtTime(0, t);
  g.gain.linearRampToValueAtTime(vol, t + 0.01);
  g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
  src.connect(filt).connect(g).connect(bus);
  src.start(t); src.stop(t + dur + 0.05);
}

// --------------------------------------------------------------------------
// the cue library
// --------------------------------------------------------------------------
const CUES = {
  // --- original five, unchanged frequencies (kept for continuity — kid.js
  //     already calls these by name on correct/flagged/crown/trail-complete) ---
  chime:   () => { tone(659, 0, .16); tone(880, .1, .3); },
  sparkle: () => { tone(1047, 0, .09); tone(1319, .07, .09); tone(1568, .14, .22); },
  soft:    () => { tone(494, 0, .2); tone(554, .12, .25); },
  crown:   () => { tone(784, 0, .12); tone(1047, .1, .22); },
  tada:    () => { tone(523, 0, .14); tone(659, .11, .14); tone(784, .22, .14); tone(1047, .33, .4); },

  // --- UI taps ---
  tap:      () => tone(880, 0, .07, { type: 'triangle', attack: .005, release: .06 }),
  nodeTap:  () => { tone(660, 0, .1, { type: 'sine', attack: .005, release: .09 }); tone(990, .03, .08, { peak: .6 }); },
  dockTap:  () => tone(740, 0, .06, { type: 'triangle', attack: .004, release: .05 }),

  // --- progress / reward ---
  unlock:   () => { tone(523, 0, .1); tone(659, .08, .1); tone(784, .16, .16); },
  sticker:  () => { tone(880, 0, .08); tone(1109, .06, .08); tone(1319, .12, .08); tone(1760, .18, .28); },
  streak:   () => { tone(587, 0, .1); tone(740, .09, .1); tone(880, .18, .1); tone(1175, .27, .3); },
  coin:     () => { tone(1319, 0, .05, { attack: .002, release: .04 }); tone(1760, .04, .12, { peak: .7 }); },
  chapter:  () => { tone(392, 0, .18, { type: 'triangle' }); tone(523, .14, .18, { type: 'triangle' }); tone(659, .28, .34, { type: 'triangle' }); },

  // --- ambience / texture (noise-based) ---
  footstep: () => noiseBurst(0, .09, { filterFreq: 260, q: .9, type: 'lowpass', peak: .55 }),
  whoosh:   () => noiseBurst(0, .32, { filterFreq: 1400, q: .5, type: 'bandpass', peak: .5 }),
  pop:      () => { noiseBurst(0, .06, { filterFreq: 1800, q: 1.2, peak: .5 }); tone(700, .01, .07, { peak: .5, attack: .005 }); },

  // --- feedback ---
  uhoh:     () => { tone(440, 0, .16, { type: 'sine' }); tone(370, .11, .22, { type: 'sine', peak: .8 }); },

  // --- Mira / mic moments ---
  miraHello:   () => sweep(520, 780, 0, .18, { type: 'sine' }),
  recordStart: () => sweep(440, 880, 0, .12, { type: 'triangle', peak: .8 }),
  recordStop:  () => sweep(880, 440, 0, .12, { type: 'triangle', peak: .7 }),
};

// --------------------------------------------------------------------------
// public API
// --------------------------------------------------------------------------
export const sfx = {
  get enabled() { return localStorage.getItem(LS_ENABLED) !== '0'; },   // on by default
  set enabled(v) { localStorage.setItem(LS_ENABLED, v ? '1' : '0'); },
  play,
  /** Escape hatch for one-off pitches that don't deserve a named cue (the
   * PIN keypad's per-digit rising blip). */
  blip: (freq, opts) => tone(freq, 0, opts?.dur ?? 0.07, opts),
  keys: Object.keys(CUES),
};

/** Play a named cue. Unknown keys and a disabled/muted state both silently
 * no-op — callers never need to guard this themselves. */
export function play(key) {
  const fn = CUES[key];
  if (fn) try { fn(); } catch {}
}
