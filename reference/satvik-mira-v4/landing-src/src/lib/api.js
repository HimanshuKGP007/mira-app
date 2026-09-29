/* Thin client for the existing account API — same contract core/auth.js and
   the old landing.js used. No backend changes: every path/field here already
   exists in server/auth.py and server/app.py. */

async function req(path, opts = {}) {
  const res = await fetch(path, {
    credentials: 'include',
    headers: opts.body ? { 'Content-Type': 'application/json' } : undefined,
    ...opts,
  });
  let body = null;
  try { body = await res.json(); } catch { /* no body */ }
  if (!res.ok) {
    const err = new Error((body && body.detail) || `HTTP ${res.status}`);
    err.status = res.status;
    throw err;
  }
  return body;
}

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
};

export function enterApp(childId, name) {
  localStorage.setItem('mira_child_id', String(childId));
  localStorage.setItem('mira_child_name', name || '');
  window.location.href = '/app/';
}
