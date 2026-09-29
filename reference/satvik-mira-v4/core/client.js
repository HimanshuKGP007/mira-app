/* ============================================================================
   client.js — the only path to a score.

   POST {endpoint}/score
     multipart/form-data: audio (wav), prompt_word, speaker_age_years
   [Stage 4 §13, B2B/B2C §15]

   Three response classes, all handled explicitly:
     1. {status:"retry", reason, snr_db}   -> gate failed BEFORE scoring
     2. a scored contract                  -> render it
     3. transport / HTTP error             -> surface plainly

   There is no offline or replay path. A failure is never converted into a
   score — if the scorer cannot be reached, the app says so.
   ========================================================================== */

import { normalizeResponse } from './policy.js';

const LS_ENDPOINT = 'mira_endpoint';
const DEFAULT_ENDPOINT = 'http://localhost:8000';

export const config = {
  get endpoint() {
    const stored = localStorage.getItem(LS_ENDPOINT);
    if (stored === null) return DEFAULT_ENDPOINT;      // server/run.sh default
    return stored.replace(/\/+$/, '');
  },
  set endpoint(v) {
    const s = (v || '').trim().replace(/\/+$/, '');
    if (s) localStorage.setItem(LS_ENDPOINT, s);
    else localStorage.removeItem(LS_ENDPOINT);          // back to the default
  },
  get configured() { return !!this.endpoint; },
  defaultEndpoint: DEFAULT_ENDPOINT,
};

export const OUTCOME = {
  SCORED: 'scored',
  RETRY: 'retry',
  ERROR: 'error',
  NO_ENDPOINT: 'no_endpoint',
  AUTH_REQUIRED: 'auth_required',
};

/**
 * Score one prompted word.
 * @param {Blob}   wavBlob   16 kHz mono PCM16 WAV
 * @param {object} opts      { promptWord, targetPhone, ageYears, timeoutMs }
 */
export async function score(wavBlob, opts = {}) {
  const { promptWord, targetPhone, ageYears = null, timeoutMs = 30000 } = opts;

  if (!config.configured) return { outcome: OUTCOME.NO_ENDPOINT };
  if (!wavBlob) {
    return { outcome: OUTCOME.ERROR, error: 'No audio was captured to send.' };
  }

  const form = new FormData();
  form.append('audio', wavBlob, `${promptWord || 'utterance'}.wav`);
  form.append('prompt_word', promptWord ?? '');
  if (ageYears != null) form.append('speaker_age_years', String(ageYears));

  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  let res;
  try {
    res = await fetch(`${config.endpoint}/score`, {
      method: 'POST', body: form, signal: ctrl.signal, credentials: 'include',
    });
  } catch (e) {
    clearTimeout(timer);
    return {
      outcome: OUTCOME.ERROR,
      error: e.name === 'AbortError'
        ? `The scorer did not respond within ${Math.round(timeoutMs / 1000)}s.`
        : `Could not reach the scorer at ${config.endpoint}. Is it running?`,
    };
  }
  clearTimeout(timer);

  if (res.status === 401) {
    return { outcome: OUTCOME.AUTH_REQUIRED, error: 'Your session has ended. Please sign in again.' };
  }
  if (!res.ok) {
    let body = '';
    try { body = (await res.text()).slice(0, 200); } catch {}
    return { outcome: OUTCOME.ERROR, error: `Scorer returned HTTP ${res.status}. ${body}`.trim() };
  }

  let raw;
  try { raw = await res.json(); }
  catch { return { outcome: OUTCOME.ERROR, error: 'Scorer returned a response that was not JSON.' }; }

  return interpret(raw, promptWord, targetPhone);
}

function interpret(raw, promptWord, targetPhone) {
  if (raw?.status === 'retry') {
    return {
      outcome: OUTCOME.RETRY,
      retry: {
        reason: raw.reason || 'quality',
        snrDb: raw.snr_db ?? null,
        message: retryMessage(raw.reason, raw.snr_db),
      },
    };
  }
  if (raw?.error) {
    return { outcome: OUTCOME.ERROR, error: `${raw.error}. ${raw.detail || ''}`.trim() };
  }

  const result = normalizeResponse(raw, { promptWord, targetPhone });
  result.scorer = raw?.provenance?.scorer ?? null;
  result.unscorableReason = raw?.unscorable_reason ?? null;

  if (!result.quality.passed) {
    return {
      outcome: OUTCOME.RETRY,
      retry: {
        reason: result.quality.reason || 'quality',
        snrDb: result.quality.snrDb,
        message: retryMessage(result.quality.reason, result.quality.snrDb),
      },
    };
  }
  return { outcome: OUTCOME.SCORED, result };
}

export function retryMessage(reason, snrDb) {
  switch (reason) {
    case 'low_snr':
      return snrDb != null
        ? `It was a bit noisy there (${snrDb} dB). Let's try that again somewhere quieter.`
        : `It was a bit noisy there. Let's try that again.`;
    case 'alignment':
      return `Mira could not line that recording up with the word. Say the whole word and try again.`;
    case 'too_short':
      return `That was very short. Say the whole word and try again.`;
    case 'empty_audio':
      return `Nothing was recorded. Tap the mic and say the word out loud.`;
    case 'bad_audio':
      return `Mira could not read that recording. Let's try again.`;
    default:
      return `Let's record that one again.`;
  }
}

/** Health probe for the settings panel and the status chip. */
export async function ping() {
  if (!config.configured) return { ok: false, message: 'No endpoint configured.' };
  try {
    const r = await fetch(`${config.endpoint}/health`);
    if (!r.ok) return { ok: false, message: `Endpoint responded HTTP ${r.status}.` };
    const h = await r.json();
    return {
      ok: true,
      health: h,
      message: `Connected · ${h.tier} on ${h.device} · AUC ${h.expected_auc} (uncalibrated)`,
    };
  } catch {
    return { ok: false, message: `Could not reach ${config.endpoint}. Is the server running?` };
  }
}
