/* ============================================================================
   voice.js — one speaker, never two.

   Every utterance cancels the previous one before starting, and an identical
   line inside 450 ms is dropped. Both guards exist because overlapping speech
   was a real defect in the earlier build.

   ElevenLabs is used when a key is present; otherwise the built-in Web Speech
   voice, pitched only slightly above neutral (1.12 — not the chipmunk 1.35).
   ========================================================================== */

const LS_KEY = 'mira_eleven_key';
const LS_VOICE = 'mira_eleven_voice';
const DEFAULT_VOICE = 'EXAVITQu4vr4xnSDxMaL';

let muted = false;
let lastText = '', lastAt = 0;
const cache = new Map();
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

export function say(raw) {
  stop();
  if (muted) return;
  const text = String(raw ?? '')
    .replace(/<[^>]*>/g, '')
    .replace(/[*_—]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
  if (!text) return;

  const now = Date.now();
  if (text === lastText && now - lastAt < 450) return;
  lastText = text; lastAt = now;

  if (voice.elevenKey) eleven(text).catch(() => web(text));
  else web(text);
}

async function eleven(text) {
  if (cache.has(text)) return play(cache.get(text));
  const res = await fetch(
    `https://api.elevenlabs.io/v1/text-to-speech/${voice.elevenVoice}?optimize_streaming_latency=3`,
    {
      method: 'POST',
      headers: {
        'xi-api-key': voice.elevenKey,
        'Content-Type': 'application/json',
        Accept: 'audio/mpeg',
      },
      body: JSON.stringify({
        text,
        model_id: 'eleven_turbo_v2_5',
        voice_settings: { stability: 0.45, similarity_boost: 0.75, style: 0.35 },
      }),
    }
  );
  if (!res.ok) throw new Error(`elevenlabs ${res.status}`);
  const url = URL.createObjectURL(await res.blob());
  cache.set(text, url);
  play(url);
}

function play(url) {
  if (!audio) return;
  audio.src = url;
  onTalk(true);
  audio.onended = audio.onerror = () => onTalk(false);
  audio.play().catch(() => onTalk(false));
}

function web(text) {
  if (!('speechSynthesis' in window)) return;
  const u = new SpeechSynthesisUtterance(text);
  u.rate = 0.98;
  u.pitch = 1.12;
  const vs = speechSynthesis.getVoices();
  u.voice =
    vs.find(v => /Samantha|Google UK English Female|Google US English|Microsoft Aria|Microsoft Jenny|Karen|Moira/i.test(v.name) && v.lang.startsWith('en')) ||
    vs.find(v => v.lang.startsWith('en')) || null;
  u.onstart = () => onTalk(true);
  u.onend = u.onerror = () => onTalk(false);
  speechSynthesis.speak(u);
}

if (typeof speechSynthesis !== 'undefined') speechSynthesis.getVoices();
