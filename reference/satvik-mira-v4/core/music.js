/* ============================================================================
   music.js — generated at runtime, nothing to license.

   A slow pentatonic pad plus a sparse plucked arpeggio over a soft sub pulse.
   Every note is a Web Audio oscillator with an envelope; there are no audio
   files and nothing is fetched, so there is no copyright question to answer.

   Each level gets a different key and a slightly different tempo (picked
   deterministically from the level id, so the same level always sounds the
   same rather than randomly shifting every visit) so the six trails feel like
   six different places rather than one loop repeating.

   Music ducks under Mira's speech (core/voice.js) and stops outright on the
   exercise screen — it must never compete with the microphone for attention,
   and the mic is listening for the child's voice, not background music.

   Runs on the shared AudioContext from core/audio.js (see that file) rather
   than owning its own — music and SFX share one context/master gain now.
   ========================================================================== */
import { getContext, getMaster } from './audio.js';

const LS_ENABLED = 'mira_music_on';
const LS_VOLUME = 'mira_music_vol';

// pentatonic scale degrees (semitones from the tonic) — no dissonant
// intervals possible, so any note combination sounds pleasant.
const PENTATONIC = [0, 2, 4, 7, 9];
const ROOTS = [55, 58.27, 61.74, 65.41, 49, 52];      // A1..ish per level, cycling

let master = null;      // overall gain (respects mute + volume)
let duckGain = null;    // ducked under speech
let padGain = null;
let arpGain = null;
let running = false;
let levelSeed = 0;
let scheduleTimer = null;
let nextArpAt = 0;
let padVoices = [];

function actx() {
  const a = getContext();
  if (!master) {
    master = a.createGain();
    duckGain = a.createGain();
    padGain = a.createGain();
    arpGain = a.createGain();
    padGain.connect(duckGain);
    arpGain.connect(duckGain);
    duckGain.connect(master);
    master.connect(getMaster());
    padGain.gain.value = 0.05;
    arpGain.gain.value = 0.045;
    duckGain.gain.value = 1;
    master.gain.value = music.enabled ? music.volume : 0;
  }
  return a;
}

function freqFor(root, degreeIdx, octave = 0) {
  const semis = PENTATONIC[degreeIdx % PENTATONIC.length] + 12 * octave;
  return root * Math.pow(2, semis / 12);
}

function tone(freq, at, dur, gainNode, { type = 'sine', peak = 1, attack = 0.4, release = 0.6 } = {}) {
  const a = actx();
  const o = a.createOscillator(), g = a.createGain();
  o.type = type; o.frequency.value = freq;
  g.gain.setValueAtTime(0, at);
  g.gain.linearRampToValueAtTime(peak, at + attack);
  g.gain.setValueAtTime(peak, Math.max(at + attack, at + dur - release));
  g.gain.linearRampToValueAtTime(0, at + dur);
  o.connect(g).connect(gainNode);
  o.start(at); o.stop(at + dur + 0.05);
  return o;
}

function schedulePad(root, barSeconds) {
  const a = actx();
  const now = a.currentTime + 0.05;
  const chordDegrees = [[0, 2], [0, 3], [1, 3]][levelSeed % 3];
  chordDegrees.forEach((deg, i) => {
    tone(freqFor(root, deg, -1), now, barSeconds * 2, padGain,
      { type: 'triangle', peak: 0.9, attack: barSeconds * 0.6, release: barSeconds * 0.8 });
  });
}

function scheduleArp(root, stepSeconds) {
  const a = actx();
  if (a.currentTime < nextArpAt) return;
  const pattern = [0, 2, 1, 3, 0, 4, 2, 1];
  const step = Math.floor((a.currentTime / stepSeconds)) % pattern.length;
  if (Math.random() < 0.35) {                       // sparse, not a constant stream
    const deg = pattern[step];
    tone(freqFor(root, deg, 1), a.currentTime + 0.02, stepSeconds * 1.6, arpGain,
      { type: 'sine', peak: 0.8, attack: 0.02, release: stepSeconds * 1.1 });
  }
  nextArpAt = a.currentTime + stepSeconds;
}

function loop(root, tempo) {
  if (!running) return;
  const barSeconds = 60 / tempo * 4;
  schedulePad(root, barSeconds);
  scheduleArp(root, barSeconds / 8);
  scheduleTimer = setTimeout(() => loop(root, tempo), barSeconds * 1000);
}

export const music = {
  get enabled() { return localStorage.getItem(LS_ENABLED) !== '0'; },        // on by default
  set enabled(v) {
    localStorage.setItem(LS_ENABLED, v ? '1' : '0');
    if (master) master.gain.setTargetAtTime(v ? this.volume : 0, actx().currentTime, 0.2);
    if (v) start(levelSeed); else running = false;
  },
  get volume() { return Number(localStorage.getItem(LS_VOLUME) ?? 0.5); },
  set volume(v) {
    const clamped = Math.max(0, Math.min(1, v));
    localStorage.setItem(LS_VOLUME, String(clamped));
    if (master && this.enabled) master.gain.setTargetAtTime(clamped, actx().currentTime, 0.2);
  },
};

/** Start (or retune) the ambient loop for a level id. Safe to call repeatedly. */
export function start(seed = 0) {
  levelSeed = Math.abs(Number(seed) || 0);
  if (!music.enabled) return;
  const a = actx();
  master.gain.setTargetAtTime(music.volume, a.currentTime, 0.4);
  const root = ROOTS[levelSeed % ROOTS.length];
  const tempo = 62 + (levelSeed % 4) * 5;             // 62-77 bpm, per-level
  if (running) { clearTimeout(scheduleTimer); }
  running = true;
  nextArpAt = 0;
  loop(root, tempo);
}

/** Stop entirely — used on the exercise screen so nothing competes with the mic. */
export function stop() {
  running = false;
  clearTimeout(scheduleTimer);
  if (master) master.gain.setTargetAtTime(0, actx().currentTime, 0.25);
}

/** Duck under speech (Mira talking) without stopping the loop scheduler. */
export function duck(on) {
  if (!duckGain) return;
  duckGain.gain.setTargetAtTime(on ? 0.22 : 1, actx().currentTime, 0.15);
}

// Also reachable as music.start/.stop/.duck — index.html calls it that way,
// and it reads better at the call site ("music.stop()") than three separate
// named imports would.
Object.assign(music, { start, stop, duck });
