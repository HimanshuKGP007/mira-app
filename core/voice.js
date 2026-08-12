/* ============================================================================
   voice.js — text-to-speech, disabled.

   Was on every screen; read as an unnecessary "robotic" voice once a child
   can read the on-screen text, so say() is now a no-op. Left in place (rather
   than deleting every ctx.say(...) call site across kid.js/index.html) so the
   API stays valid and harmless. Voice settings in the UI are similarly inert
   now but left alone, since removing them wasn't asked for.
   ========================================================================== */

const LS_KEY = 'mira_eleven_key';
const LS_VOICE = 'mira_eleven_voice';
const DEFAULT_VOICE = 'EXAVITQu4vr4xnSDxMaL';

let muted = false;
const audio = typeof Audio !== 'undefined' ? new Audio() : null;
let onTalk = () => {};

export const voice = {
  get muted() { return muted; },
  set muted(v) { muted = !!v; if (muted) stop(); },
  get elevenKey() { return localStorage.getItem(LS_KEY) || ''; },
  set elevenKey(v) {
    if (v && v.trim()) localStorage.setItem(LS_KEY, v.trim());
    else localStorage.removeItem(LS_KEY);
  },
  get elevenVoice() { return localStorage.getItem(LS_VOICE) || DEFAULT_VOICE; },
  set elevenVoice(v) {
    if (v && v.trim()) localStorage.setItem(LS_VOICE, v.trim());
    else localStorage.removeItem(LS_VOICE);
  },
  onTalking(fn) { onTalk = fn || (() => {}); },
  say, stop,
};

export function stop() {
  try { if ('speechSynthesis' in window) speechSynthesis.cancel(); } catch {}
  try { if (audio) { audio.pause(); audio.currentTime = 0; } } catch {}
  onTalk(false);
}

export function say() {
  stop();
}
