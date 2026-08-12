/* ============================================================================
   parent.js — the honest adult summary.

   Two rules from the docs govern this whole screen:
     "Show scored and not-scored side by side, always."
     No diagnosis, no severity, no prognosis, no goals.

   It reports what was measured and what was declined, and states the model's
   own miss rate rather than implying the absence of a flag means correctness.
   ========================================================================== */

import { icon } from './icons.js';
import { store, lifetime } from '../core/rewards.js';
import { LEVELS } from '../core/exercise.js';
import { feedbackForSession } from '../core/policy.js';
import { OPERATING_POINT, SVARAH } from '../core/policy.js';

const $ = s => document.querySelector(s);

export function render() {
  const name = store.name || 'your child';
  const sessions = store.sessions;
  const last = sessions[sessions.length - 1] || null;
  const agg = lifetime();

  $('#pName').textContent = name;
  $('#pMeta').textContent = sessions.length
    ? `Practising the /s/ "snake sound" · ${sessions.length} session${sessions.length === 1 ? '' : 's'} recorded`
    : `Practising the /s/ "snake sound" · no sessions yet`;

  const body = $('#parentBody');

  if (!last) {
    body.innerHTML = `
      <div class="card">
        <h3>${icon('chart')}Progress</h3>
        <div class="note">No practice sessions yet. Once ${name} finishes a trail,
        this page shows what was measured — and, just as importantly, what Mira declined to judge.</div>
      </div>${aboutCard()}`;
    return;
  }

  body.innerHTML = `
    ${lastSessionCard(last, name)}
    ${positionCard(agg)}
    ${rewardCard()}
    ${trophyCard()}
    ${aboutCard(last.scorer)}`;

  bindReward();
}

/* --- last session: the scored / not-scored pair leads ---------------------- */
function lastSessionCard(r, name) {
  const items = r.items.map(i => ({ word: { text: i.word, position: i.position }, verdict: i.verdict, result: null }));
  const fb = feedbackForSession(items.map(i => ({ ...i, result: {} })), 's');
  const when = new Date(r.at);

  return `
  <div class="card">
    <h3>${icon('clipboard')}Last session — ${r.levelName}</h3>
    <div class="denom">
      <div class="box clear"><div class="n">${r.clear}</div><div class="l">clear</div></div>
      <div class="box flagged"><div class="n">${r.flagged}</div><div class="l">flagged</div></div>
      <div class="box notscored"><div class="n">${r.notScored}</div><div class="l">not scored</div></div>
    </div>
    <div class="note" style="margin-top:11px">
      <b>${fb.headline}</b> ${fb.detail}
      ${fb.notScoredNote ? `<br><span style="color:var(--slate)">${fb.notScoredNote}</span>` : ''}
    </div>
    ${fb.practise.length ? `
      <div style="margin-top:11px">
        <div class="l" style="font-size:11px;font-weight:800;color:var(--ink-soft);
          text-transform:uppercase;letter-spacing:.8px;margin-bottom:7px">Worth repeating this week</div>
        <div style="display:flex;gap:7px;flex-wrap:wrap">
          ${fb.practise.map(w => `<span class="pill" style="color:var(--vio-d);font-size:13px;padding:6px 13px">${w}</span>`).join('')}
        </div>
        <div class="note" style="margin-top:8px">Slip these into ordinary conversation — no drilling required.
        If ${name} says one differently, just say the word back the right way and carry on.</div>
      </div>` : ''}
    <div class="note" style="margin-top:11px;font-size:12px;color:var(--ink-faint)">
      ${when.toLocaleDateString()} · ${when.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
    </div>
  </div>`;
}

/* --- by position: never collapsed ---------------------------------------- */
function positionCard(agg) {
  const order = ['initial', 'medial', 'final'];
  const label = { initial: 'Start of words', medial: 'Middle of words', final: 'End of words' };
  const rows = order.filter(p => agg.byPosition[p]).map(p => {
    const v = agg.byPosition[p];
    const total = v.scored + v.notScored || 1;
    const clearPct = (v.clear / total) * 100;
    const flagPct = ((v.scored - v.clear) / total) * 100;
    const nsPct = (v.notScored / total) * 100;
    return `
      <div class="posrow">
        <div class="top"><span>${label[p]}</span>
          <span class="ex">${v.clear} clear · ${v.scored - v.clear} flagged${v.notScored ? ` · ${v.notScored} not scored` : ''}</span></div>
        <div class="track">
          <div class="fill clear" style="width:${clearPct}%"></div>
          <div class="fill flag" style="width:${flagPct}%"></div>
          <div class="fill ns" style="width:${nsPct}%"></div>
        </div>
      </div>`;
  }).join('');

  if (!rows) return '';
  return `
  <div class="card">
    <h3>${icon('chart')}Across word positions</h3>
    ${rows}
    <div class="note" style="margin-top:9px">A sound can be clear at the start of a word and
    harder at the end — they are counted separately because they are genuinely different skills.</div>
  </div>`;
}

/* --- reward goal, tied to real stars ------------------------------------- */
function rewardCard() {
  const rw = store.reward;
  const cur = store.stars;
  const pct = Math.min((cur / rw.target) * 100, 100);
  return `
  <div class="card">
    <h3>${icon('gift')}Reward goal</h3>
    <div class="goal">
      <div class="gift">${icon('gift', 26)}</div>
      <div><div class="lab">${escapeHtml(rw.label)}</div>
      <div class="sub">${cur >= rw.target ? 'Unlocked!' : `${rw.target - cur} stars to go`}</div></div>
    </div>
    <div class="rc-track"><div class="rc-fill" style="width:${pct}%"></div></div>
    <div class="rc-nums"><span>${cur} stars</span><span>target ${rw.target}</span></div>
    <button class="btn-ghost" id="editGoal" style="width:100%;margin-top:11px">Set a new reward goal</button>
    <div class="note" style="margin-top:9px">A star is only given when Mira marks the sound
    <b>correct</b> — never for a word it declined to judge. The goal tracks measured practice, not screen time.</div>
  </div>`;
}

function bindReward() {
  const b = $('#editGoal');
  if (!b) return;
  b.addEventListener('click', () => {
    const rw = store.reward;
    const label = prompt('Reward name:', rw.label);
    if (label === null) return;
    const t = prompt('How many stars to earn it?', String(rw.target));
    const target = Math.max(10, parseInt(t, 10) || rw.target);
    store.reward = { label: label.trim() || rw.label, target };
    render();
  });
}

function trophyCard() {
  const crowns = Object.values(store.levels).reduce((a, l) => a + (l.crowns || 0), 0);
  const done = Object.values(store.levels).filter(l => l.done).length;
  return `
  <div class="card">
    <h3>${icon('trophy')}Adventure so far</h3>
    <div class="stat-line"><span>Trails cleared</span><span>${done} of ${LEVELS.length}</span></div>
    <div class="stat-line"><span>Crowns earned</span><span>${crowns} of ${LEVELS.length * 3}</span></div>
    <div class="stat-line"><span>Stars in the jar</span><span>${store.stars}</span></div>
    <div class="stat-line"><span>Trophies</span><span>${store.badges.length} of 4</span></div>
  </div>`;
}

/* --- the honest limits, stated plainly ----------------------------------- */
function aboutCard(scorer) {
  const baseline = scorer && scorer.tier === 'gop_baseline';
  return `
  <div class="card">
    <h3>${icon('shield')}What Mira can and cannot tell you</h3>
    <div class="pitch">
      Mira listens to each practice word and marks the sound. It is a rough guide, not a verdict:
      it misses a good share of real errors and sometimes flags a sound that was perfectly fine.
      It says <b>not scored</b> rather than guessing on the sounds it measures poorly.
    </div>
    <div class="note" style="margin-top:10px">
      This means <b>a clear result is not proof a sound was right</b>, and a flag is not proof it was wrong.
      Mira is a practice aid, not an assessment. It does not diagnose, does not rate severity,
      and does not decide what to work on next — a speech-language pathologist does that.
    </div>
    ${scorer ? `
    <div class="note" style="margin-top:10px">
      <b>Scorer:</b> ${scorer.tier === 'gop_baseline' ? 'goodness-of-pronunciation baseline' : scorer.tier}.
      ${baseline ? `Its ability to tell a good production from a poor one measures
      <b>${scorer.expected_auc}</b> (where 0.5 is a coin toss and 1.0 is perfect).
      A stronger version of this model reaches 0.843 but is not installed.` : ''}
      ${scorer.calibrated === false ? `Confidence values here are raw model output and are
      <b>not calibrated</b> — treat them as a ranking, not a probability.` : ''}
    </div>` : ''}
    <div class="note" style="margin-top:9px;font-size:12px;color:var(--ink-faint)">
      The underlying approach was tested on ${SVARAH.nUtterances.toLocaleString()} Indian-English
      recordings across 17 states and showed no accent penalty — it flagged
      ${(SVARAH.flagRate * 100).toFixed(1)}% of sounds, below its own
      ${(SVARAH.ownNoiseFloor * 100).toFixed(1)}% baseline. Figures for the fully trained
      version: detection ${(OPERATING_POINT.recallOnPoor * 100).toFixed(1)}%,
      false alarms ${(OPERATING_POINT.falsePositiveRate * 100).toFixed(1)}%.
    </div>
  </div>`;
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}
