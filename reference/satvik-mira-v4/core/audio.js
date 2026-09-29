/* ============================================================================
   audio.js — the one shared AudioContext for music + sound effects.

   Before this file, three separate AudioContexts existed in the app: the
   inline SFX block in index.html, core/music.js's own context, and
   core/capture.js's mic-input context. This unifies music + SFX onto a
   single context and a single master gain so they can duck each other and
   share one mute/volume story without three independent lifecycles.

   core/capture.js deliberately keeps its own context — it's microphone
   INPUT, gated by a different browser permission and created fresh per
   recording, not something that belongs on a shared playback graph.
   ========================================================================== */

let ctx = null;
let master = null;

/** The shared context, created (or resumed, if the browser suspended it —
 * e.g. after a tab was backgrounded) on first/next call. */
export function getContext() {
  if (!ctx) {
    ctx = new (window.AudioContext || window.webkitAudioContext)();
    master = ctx.createGain();
    master.gain.value = 1;
    master.connect(ctx.destination);
  }
  if (ctx.state === 'suspended') ctx.resume();
  return ctx;
}

/** The single node everything (music bus, sfx bus) should connect into
 * before the real destination. */
export function getMaster() {
  getContext();
  return master;
}

/** Call from inside a user-gesture handler (tap/click) before anything
 * tries to play — satisfies the browser autoplay policy. Safe to call any
 * number of times. */
export function unlock() {
  getContext();
}
