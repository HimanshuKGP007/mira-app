/* ============================================================================
   clinician.js — the scored sheet.

   "Mira produces inputs to a clinician's judgement, never outputs to a
    patient. It scores, it does not interpret."

   Design constraints taken directly from the docs:
     - markings only: correct | substituted | omitted | assimilated | not_scored
     - distortion is a FLAG on a marking, never a marking of its own
     - not_scored carries a reason and stays in the summary denominator
     - an override NEVER overwrites: mira_said and clinician_said both persist
     - raw mira_score is not rendered; confidence is
     - provenance travels with the record, and it must be the REAL record —
       this file used to hardcode a fake provenance block (including the
       trained ensemble's threshold, which this baseline tier never uses).
       Never fabricate a technical value here again; if it wasn't captured,
       say so instead of inventing one.
   ========================================================================== */

import { icon } from './icons.js';
import { store } from '../core/rewards.js';
import { MARKINGS } from '../core/policy.js';

const $ = s => document.querySelector(s);
const LS_CORRECTIONS = 'mira_corrections';

const corrections = {
  all() { try { return JSON.parse(localStorage.getItem(LS_CORRECTIONS) || '{}'); } catch { return {}; } },
  get(key) { return this.all()[key] || null; },
  set(key, rec) {
    const a = this.all();
    a[key] = rec;
    localStorage.setItem(LS_CORRECTIONS, JSON.stringify(a));
  },
};

export function render() {
  const sessions = store.sessions;
  const last = sessions[sessions.length - 1] || null;
  const body = $('#clinBody');

  if (!last) {
    body.innerHTML = `
      <div class="card"><h3>${icon('clipboard')}Scored sheet</h3>
      <div class="note">No recorded session yet. Complete a trail and the scored sheet appears here.</div></div>
      ${limitsCard()}`;
    return;
  }

  const totals = last.items.reduce((a, i) => {
    if (i.verdict === 'not_scored') a.notScored++;
    else { a.scored++; if (i.verdict === 'correct') a.correct++; }
    return a;
  }, { scored: 0, notScored: 0, correct: 0 });

  body.innerHTML = `
    <div class="card">
      <h3>${icon('clipboard')}Scored sheet · /s/ · ${last.levelName}</h3>
      <div class="denom">
        <div class="box scored"><div class="n">${totals.scored}</div><div class="l">scored</div></div>
        <div class="box notscored"><div class="n">${totals.notScored}</div><div class="l">not scored</div></div>
        <div class="box clear"><div class="n">${totals.correct}</div><div class="l">correct</div></div>
        <div class="box flagged"><div class="n">${totals.scored - totals.correct}</div><div class="l">in error</div></div>
      </div>
      <div class="note" style="margin-top:10px">Target sound <b>/s/</b>, single-word citation forms.
      Items marked <b>not scored</b> remain in the denominator; they are withheld, not passed.</div>
    </div>
    ${positionBreakdownCard(last)}
    <div class="card">
      <h3>${icon('target')}Items</h3>
      ${last.items.map((it, i) => itemBlock(it, `${last.at}#${i}`)).join('')}
    </div>
    ${sessionHistoryCard(sessions)}
    ${provenanceCard(last)}
    ${limitsCard(last.scorer)}`;

  bindOverrides(last);
}

/* --- per position, this session: numbers are fine in this register ------- */
function positionBreakdownCard(session) {
  const order = ['initial', 'medial', 'final'];
  const rows = order.filter(p => session.byPosition?.[p]).map(p => {
    const v = session.byPosition[p];
    const pct = v.scored ? Math.round((v.clear / v.scored) * 100) : null;
    return `<tr><td>${p}</td><td>${v.clear}/${v.scored}</td><td>${v.notScored}</td>
      <td>${pct == null ? '-' : pct + '%'}</td></tr>`;
  }).join('');
  if (!rows) return '';
  return `
  <div class="card">
    <h3>${icon('chart')}By position, this session</h3>
    <table class="sheet"><thead><tr>
      <th style="text-align:left">position</th><th style="text-align:left">clear/scored</th>
      <th style="text-align:left">not scored</th><th style="text-align:left">%</th>
    </tr></thead><tbody>${rows}</tbody></table>
  </div>`;
}

function itemBlock(it, key) {
  const c = corrections.get(key);
  const shown = c ? c.clinician_said : it.verdict;
  const rows = (it.instances && it.instances.length ? it.instances : [it]).map(inst => {
    const marking = inst.marking || inst.verdict;
    const gop = inst.gop;
    return `
    <tr>
      <td style="width:34px"><span class="tgt">s</span><span class="p" style="font-size:10px;display:block">${inst.position || ''}</span></td>
      <td>
        <span class="pill ${marking}">${label(marking)}</span>
        ${inst.substitute && marking === 'substituted' ? `<span class="sub"> &rarr; ${inst.substitute}</span>` : ''}
        ${inst.reason && marking === 'not_scored' ? `<div class="why">${inst.reason}</div>` : ''}
        ${gop ? `<div style="margin-top:4px;font-size:10.5px;color:var(--ink-faint);font-family:var(--font-ui)">
          post_max ${fmt(gop.post_max)} &middot; post_mean ${fmt(gop.post_mean)} &middot;
          gop_max ${fmt(gop.gop_max)} &middot; gop_mean ${fmt(gop.gop_mean)} &middot; gop_renorm ${fmt(gop.gop_renorm)}
          ${inst.durationMs != null ? ` &middot; window ${inst.durationMs}ms` : ''}</div>` : ''}
      </td>
      <td style="width:52px;text-align:right">
        <span class="conf">${inst.confidence != null ? inst.confidence.toFixed(2) : '-'}</span>
      </td>
    </tr>`;
  }).join('');
  return `
  <div class="wordblock" data-key="${key}">
    <div class="wh"><span class="w">${it.word}</span><span class="p">${it.position}${it.struggling ? ' &middot; <span style="color:var(--amber-d)">no improvement across attempts</span>' : ''}</span></div>
    <table class="sheet"><tbody>${rows}</tbody></table>
    ${c ? `<div class="audit">clinician override &middot; Mira said <s>${label(c.mira_said)}</s>,
           you marked <b>${label(c.clinician_said)}</b></div>` : ''}
    <div class="override">
      ${MARKINGS.map(m => `<button data-m="${m}" class="${m === shown ? 'on' : ''}">${label(m)}</button>`).join('')}
    </div>
  </div>`;
}

function fmt(n) { return n == null ? '-' : n.toFixed(3); }

const label = m => ({
  correct: 'correct', substituted: 'substituted', omitted: 'omitted',
  assimilated: 'assimilated', not_scored: 'not scored',
}[m] || m);

function bindOverrides(session) {
  $('#clinBody').querySelectorAll('.wordblock').forEach(block => {
    const key = block.dataset.key;
    const idx = +key.split('#')[1];
    const item = session.items[idx];
    block.querySelectorAll('.override button').forEach(btn => {
      btn.addEventListener('click', () => {
        const chosen = btn.dataset.m;
        const existing = corrections.get(key);
        // never overwrite Mira's original: the first recorded value is kept
        const miraSaid = existing ? existing.mira_said : item.verdict;
        if (chosen === miraSaid) {
          const all = corrections.all();
          delete all[key];
          localStorage.setItem(LS_CORRECTIONS, JSON.stringify(all));
        } else {
          corrections.set(key, {
            mira_said: miraSaid,
            clinician_said: chosen,
            word: item.word,
            position: item.position,
            target: 's',
            confidence: item.confidence,
            at: new Date().toISOString(),
          });
        }
        render();
      });
    });
  });
}

/* --- across sessions: trend, not just the latest run ---------------------- */
function sessionHistoryCard(sessions) {
  if (sessions.length < 2) return '';
  const rows = sessions.slice(-10).reverse().map(s => {
    const pct = s.scored ? Math.round((s.clear / s.scored) * 100) : null;
    const when = new Date(s.at);
    return `<tr><td>${when.toLocaleDateString()}</td><td>${s.levelName}</td>
      <td>${s.clear}/${s.scored}</td><td>${s.notScored}</td>
      <td>${pct == null ? '-' : pct + '%'}</td></tr>`;
  }).join('');
  return `
  <div class="card">
    <h3>${icon('chart')}Session history (last ${Math.min(sessions.length, 10)})</h3>
    <table class="sheet"><thead><tr>
      <th style="text-align:left">date</th><th style="text-align:left">trail</th>
      <th style="text-align:left">clear/scored</th><th style="text-align:left">not scored</th>
      <th style="text-align:left">%</th>
    </tr></thead><tbody>${rows}</tbody></table>
  </div>`;
}

/* --- the real provenance for this exact session, never fabricated -------- */
function provenanceCard(session) {
  const p = session.provenance;
  return `
  <div class="card">
    <h3>${icon('shield')}Provenance</h3>
    ${p ? `
    <div class="prov">
      <div><b>model_version</b><br>${p.model_version || '-'}</div>
      <div><b>aligner_version</b><br>${p.aligner_version || '-'}</div>
      <div><b>protocol_version</b><br>${p.protocol_version || '-'}</div>
      <div><b>threshold_set_version</b><br>${p.threshold_set_version || '-'}</div>
      <div><b>device</b><br>${p.device || '-'}</div>
      <div style="margin-top:6px"><b>recorded</b><br>${new Date(session.at).toLocaleString()}</div>
    </div>` : `
    <div class="note">Provenance was not captured with this session (recorded before this
    field was added). Nothing here is fabricated to fill the gap.</div>`}
  </div>`;
}

function limitsCard(scorer) {
  const baseline = scorer && scorer.tier === 'gop_baseline';
  return `
  <div class="card">
    <h3>${icon('shield')}Stated limits</h3>
    ${scorer ? `
    <div class="note">
      <b>Scorer in use:</b> <code>${scorer.tier}</code>${scorer.calibrated === false ? ' · uncalibrated' : ''}<br>
      ${scorer.description || ''}
      ${baseline ? `<br><br>Measured on the official test split:
        <b>AUC ${scorer.expected_auc}</b>, PCC ${scorer.expected_pcc}. The trained ensemble
        reaches AUC 0.843 / PCC 0.376 but requires artifacts that are not installed here.` : ''}
      ${scorer.confidence_kind === 'raw_posterior' ? `<br><br>The confidence column is a
        <b>raw CTC posterior</b> (post_max), not a calibrated probability — a ranking signal,
        not a chance-of-correct estimate.` : ''}
    </div>` : `<div class="note">No scorer metadata on this session.</div>`}
    <div class="note" style="margin-top:9px;color:var(--ink-faint);font-size:12px">
      No ground truth exists for disordered or child speech in this model's training data.
      Overrides are stored locally with both values retained.
    </div>
  </div>`;
}

/** Exposed so the settings screen can show/export what has been corrected. */
export function exportCorrections() {
  return corrections.all();
}
