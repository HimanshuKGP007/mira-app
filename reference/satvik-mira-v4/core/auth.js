/* ============================================================================
   auth.js — thin client for the account/progress API.

   The server is the real access boundary (it gates /app on the session cookie
   and every /score, /children, /progress, /sessions call on a valid parent).
   This module just talks to it and keeps the "which child is active" concept,
   which is client-side only — the server only knows "which children belong to
   this parent"; it has no notion of an active one.
   ========================================================================== */

const LS_CHILD_ID = 'mira_child_id';
const LS_CHILD_NAME = 'mira_child_name';

// Same-origin by default (the API and the app are served from the same host),
// but this mirrors core/client.js's own endpoint so a split-origin dev setup
// (app on one port, scorer on another) still carries the session cookie.
import { config as scorerConfig } from './client.js';

function apiBase() {
  return scorerConfig.endpoint || '';
}

async function req(path, opts = {}) {
  const res = await fetch(`${apiBase()}${path}`, {
    credentials: 'include',
    headers: opts.body ? { 'Content-Type': 'application/json' } : undefined,
    ...opts,
  });
  let body = null;
  try { body = await res.json(); } catch {}
  if (!res.ok) {
    const detail = (body && body.detail) || `HTTP ${res.status}`;
    const err = new Error(detail);
    err.status = res.status;
    throw err;
  }
  return body;
}

export const account = {
  get childId() {
    const v = localStorage.getItem(LS_CHILD_ID);
    return v ? Number(v) : null;
  },
  get childName() { return localStorage.getItem(LS_CHILD_NAME) || ''; },
  setActiveChild(id, name) {
    localStorage.setItem(LS_CHILD_ID, String(id));
    localStorage.setItem(LS_CHILD_NAME, name || '');
  },
  clearActiveChild() {
    localStorage.removeItem(LS_CHILD_ID);
    localStorage.removeItem(LS_CHILD_NAME);
  },
};

export const api = {
  signup: (email, password, consentService, consentTraining) =>
    req('/auth/signup', { method: 'POST', body: JSON.stringify({
      email, password, consent_service: consentService, consent_training: consentTraining,
    }) }),
  login: (email, password) =>
    req('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }),
  logout: () => req('/auth/logout', { method: 'POST' }),
  me: () => req('/auth/me'),
  children: () => req('/children'),
  addChild: (name, ageYears) =>
    req('/children', { method: 'POST', body: JSON.stringify({ name, age_years: ageYears }) }),
  getProgress: childId => req(`/progress/${childId}`),
  putProgress: (childId, snapshot) =>
    req(`/progress/${childId}`, { method: 'PUT', body: JSON.stringify(snapshot) }),
  postSession: (childId, payload) =>
    req(`/sessions/${childId}`, { method: 'POST', body: JSON.stringify(payload) }),
};

/** Redirect to the landing page's sign-in flow. Used when a client-side check
 *  (no active child, or a 401 from the API) finds the session isn't usable
 *  even though /app itself let the request through. */
export function bounceToSignIn() {
  account.clearActiveChild();
  window.location.href = '/?auth=1';
}
