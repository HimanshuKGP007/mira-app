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
     - provenance travels with the record
   ========================================================================== */

import { icon } from './icons.js';
import { store } from '../core/rewards.js';
import { MARKINGS, HONEST_PITCH, OPERATING_POINT } from '../core/policy.js';

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
    <div class="card">
      <h3>${icon('target')}Items</h3>
      ${last.items.map((it, i) => itemBlock(it, `${last.at}#${i}`)).join('')}
    </div>
    ${provenanceCard(last)}
    ${limitsCard(last.scorer)}`;

  bindOverrides(last);
}

function itemBlock(it, key) {
  const c = corrections.get(key);
  const shown = c ? c.clinician_said : it.verdict;
  const rows = (it.instances && it.instances.length ? it.instances : [it]).map(inst => `
    <tr>
      <td style="width:34px"><span class="tgt">s</span><span class="p" style="font-size:10px;display:block">${inst.position || ''}</span></td>
      <td>
        <span class="pill ${inst.marking || inst.verdict}">${label(inst.marking || inst.verdict)}</span>
        ${inst.substitute && (inst.marking || inst.verdict) === 'substituted' ? `<span class="sub"> &rarr; ${inst.substitute}</span>` : ''}
        ${inst.reason && (inst.marking || inst.verdict) === 'not_scored' ? `<div class="why">${inst.reason}</div>` : ''}
      </td>
      <td style="width:52px;text-align:right">
        <span class="conf">${inst.confidence != null ? inst.confidence.toFixed(2) : '-'}</span>
      </td>
    </tr>`).join('');
  return `
  <div class="wordblock" data-key="${key}">
    <div class="wh"><span class="w">${it.word}</span><span class="p">${it.position}</span></div>
    <table class="sheet"><tbody>${rows}</tbody></table>
    ${c ? `<div class="audit">clinician override &middot; Mira said <s>${label(c.mira_said)}</s>,
           you marked <b>${label(c.clinician_said)}</b></div>` : ''}
    <div class="override">
      ${MARKINGS.map(m => `<button data-m="${m}" class="${m === shown ? 'on' : ''}">${label(m)}</button>`).join('')}
    </div>
  </div>`;
}

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

function provenanceCard(session) {
  const p = {
    model_version: 'facebook/wav2vec2-lv-60-espeak-cv-ft',
    aligner_version: '3.4.1',
    protocol_version: 'speechocean762_official_split_stage2_v7_accuracy',
    threshold_set_version: 'platt_a4.2632_b-5.8443_t0.86',
  };
  return `
  <div class="card">
    <h3>${icon('shield')}Provenance</h3>
    <div class="prov">
      ${Object.entries(p).map(([k, v]) => `<div><b>${k}</b><br>${v}</div>`).join('')}
      <div style="margin-top:6px"><b>recorded</b><br>${new Date(session.at).toLocaleString()}</div>
    </div>
  </div>`;
}

function limitsCard(scorer) {
  const baseline = scorer && scorer.tier === 'gop_baseline';
  return `
  <div class="card">
    <h3>${icon('shield')}Stated limits</h3>
    ${scorer ? `
    <div class="note" style="margin-bottom:10px">
      <b>Scorer in use:</b> <code>${scorer.tier}</code>${scorer.calibrated === false ? ' · uncalibrated' : ''}<br>
      ${scorer.description || ''}
      ${baseline ? `<br><br>Measured on the official test split:
        <b>AUC ${scorer.expected_auc}</b>, PCC ${scorer.expected_pcc}. The trained ensemble
        reaches AUC 0.843 / PCC 0.376 but requires artifacts that are not installed here,
        so <b>these markings are weaker than the published figures below</b>.` : ''}
      ${scorer.confidence_kind === 'raw_posterior' ? `<br><br>The confidence column is a
        <b>raw CTC posterior</b>, not a calibrated probability. It orders productions;
        it does not estimate the chance of being correct, and it is not comparable to the
        calibrated confidences the trained model emits.` : ''}
    </div>` : ''}
    <div class="pitch">${HONEST_PITCH}</div>
    <div class="note" style="margin-top:10px">
      Figures for the <b>fully trained</b> ensemble on the official test split (15,559 phones,
      125 unseen speakers): detection <b>${(OPERATING_POINT.recallOnPoor * 100).toFixed(1)}%</b>
      of poorly-rated sounds, false alarm <b>${(OPERATING_POINT.falsePositiveRate * 100).toFixed(1)}%</b>
      on well-rated sounds, AUC <b>${OPERATING_POINT.testAUC}</b>. Ranking is what the tool runs on.
    </div>
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
