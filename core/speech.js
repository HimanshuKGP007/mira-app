/* ============================================================================
   speech.js — say ONE word, on request.

   Not the same thing as voice.js, which narrated every screen and was removed
   for being an unnecessary robotic voice over text the child can already read.
   This module never speaks on its own: it only fires when someone taps a
   listen button, and it only ever says a single prompt word. That is a model
   of the target, which is the one thing a practice tool genuinely needs to
   speak, and it is the same word the scorer is about to be asked to judge.

   Two routes, in order:
     1. ElevenLabs, when a key has been saved in settings (mira_eleven_key) —
        a real voice, and the closest thing to an "ideal" production available.
        Results are cached per word so a repeated tap costs nothing.
     2. The browser's own speech synthesis, slowed slightly (0.8) so the target
        consonant is audible rather than swallowed, on the best English voice
        the device offers.

   If neither is available the button reports that plainly; it never silently
   does nothing.
   ========================================================================== */

const LS_KEY = 'mira_eleven_key';
const LS_VOICE = 'mira_eleven_voice';
const DEFAULT_VOICE = 'EXAVITQu4vr4xnSDxMaL';

const cache = new Map();                       // word -> object URL
const audio = typeof Audio !== 'undefined' ? new Audio() : null;
let speaking = null;                           // the word currently playing
let listeners = new Set();

export const RATE = 0.8;                       // deliberately below natural speed

export const speech = {
  get elevenKey() { return localStorage.getItem(LS_KEY) || ''; },
  get elevenVoice() { return localStorage.getItem(LS_VOICE) || DEFAULT_VOICE; },
  get available() {
    return !!(this.elevenKey || (typeof speechSynthesis !== 'undefined'));
  },
  get speaking() { return speaking; },
};

/** Notified with (word|null) whenever playback starts and stops, so a button
 *  can show that it is playing without every view polling. */
export function onSpeaking(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}
function emit(word) {
  speaking = word;
  listeners.forEach(fn => { try { fn(word); } catch {} });
}

export function stop() {
  try { if (typeof speechSynthesis !== 'undefined') speechSynthesis.cancel(); } catch {}
  try { if (audio) { audio.pause(); audio.currentTime = 0; } } catch {}
  emit(null);
}

/**
 * Say one word out loud. Returns a promise that resolves when playback has
 * been handed off (not when it finishes), or rejects with a reason the caller
 * can show.
 */
export async function sayWord(raw) {
  const word = String(raw ?? '').trim();
  if (!word) return;
  stop();

  if (speech.elevenKey) {
    try { return await eleven(word); }
    catch { /* fall through to the built-in voice */ }
  }
  return web(word);
}

async function eleven(word) {
  if (!audio) throw new Error('no audio element');
  if (cache.has(word)) return play(word, cache.get(word));

  const res = await fetch(
    `https://api.elevenlabs.io/v1/text-to-speech/${speech.elevenVoice}`,
    {
      method: 'POST',
      headers: {
        'xi-api-key': speech.elevenKey,
        'Content-Type': 'application/json',
        Accept: 'audio/mpeg',
      },
      body: JSON.stringify({
        text: word,
        model_id: 'eleven_turbo_v2_5',
        // Low style / high stability: this is a pronunciation model, not a
        // performance. The word should come out the same way every time.
        voice_settings: { stability: 0.75, similarity_boost: 0.85, style: 0.0 },
      }),
    }
  );
  if (!res.ok) throw new Error(`elevenlabs ${res.status}`);
  const url = URL.createObjectURL(await res.blob());
  cache.set(word, url);
  return play(word, url);
}

function play(word, url) {
  audio.src = url;
  audio.playbackRate = 0.9;
  emit(word);
  audio.onended = audio.onerror = () => emit(null);
  return audio.play().catch(() => emit(null));
}

function web(word) {
  if (typeof speechSynthesis === 'undefined') {
    throw new Error('This browser cannot speak the word out loud.');
  }
  const u = new SpeechSynthesisUtterance(word);
  u.rate = RATE;
  u.pitch = 1.0;
  u.lang = 'en-GB';
  u.voice = pickVoice();
  u.onstart = () => emit(word);
  u.onend = u.onerror = () => emit(null);
  speechSynthesis.speak(u);
}

function pickVoice() {
  const vs = speechSynthesis.getVoices() || [];
  const en = vs.filter(v => /^en/i.test(v.lang || ''));
  // Prefer the clearest built-in voices, then any English one at all.
  return en.find(v => /Samantha|Serena|Karen|Daniel|Google UK English|Microsoft Aria|Microsoft Sonia/i.test(v.name))
      || en.find(v => /^en-GB/i.test(v.lang))
      || en[0] || null;
}

// Chrome populates the voice list asynchronously; ask early so the first tap
// is not the one that has to wait for it.
if (typeof speechSynthesis !== 'undefined') {
  speechSynthesis.getVoices();
  speechSynthesis.onvoiceschanged = () => speechSynthesis.getVoices();
}

/* --- the button ----------------------------------------------------------
   One markup helper and one delegated listener, so every surface that shows
   a practice word gets the same control with the same behaviour. Any element
   carrying data-say="<word>" becomes a listen button.                      */

export const SPEAKER_SVG = `<svg viewBox="0 0 24 24" aria-hidden="true">
  <path d="M4 9.5 h3.2 L12 5.5 v13 L7.2 14.5 H4 Z" fill="currentColor"/>
  <path d="M15.4 9.2 a4 4 0 0 1 0 5.6" fill="none" stroke="currentColor"
    stroke-width="2" stroke-linecap="round"/>
  <path d="M17.9 6.6 a7.6 7.6 0 0 1 0 10.8" fill="none" stroke="currentColor"
    stroke-width="2" stroke-linecap="round"/></svg>`;

/**
 * Markup for a listen button.
 * @param {string} word   the word to say
 * @param {object} opts   { label, size: 'sm'|'md'|'lg', className }
 */
export function listenButton(word, opts = {}) {
  const { label = '', size = 'md', className = '' } = opts;
  const w = String(word ?? '').replace(/"/g, '&quot;');
  return `<button type="button" class="say-btn say-${size} ${className}" data-say="${w}"
    title="Hear ${w}" aria-label="Hear the word ${w}">${SPEAKER_SVG}${
      label ? `<span>${label}</span>` : ''}</button>`;
}

let installed = false;
/** Install the one delegated click handler. Safe to call more than once. */
export function installSpeechButtons() {
  if (installed || typeof document === 'undefined') return;
  installed = true;

  document.addEventListener('click', ev => {
    const btn = ev.target.closest?.('[data-say]');
    if (!btn) return;
    ev.preventDefault();
    ev.stopPropagation();
    const word = btn.dataset.say;
    if (speech.speaking === word) { stop(); return; }
    sayWord(word).catch(() => {});
  });

  onSpeaking(word => {
    document.querySelectorAll('[data-say]').forEach(b => {
      b.classList.toggle('playing', !!word && b.dataset.say === word);
    });
  });
}
