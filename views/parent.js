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
import { LEVELS, WORDS } from '../core/exercise.js';
import { feedbackForSession } from '../core/policy.js';
import { OPERATING_POINT, SVARAH } from '../core/policy.js';
import { config } from '../core/client.js';
import { listenButton } from '../core/speech.js';

const $ = s => document.querySelector(s);

/** A practice word the parent can both read and hear. The listen button is
 *  never decoration here: saying the word correctly at home is the whole
 *  instruction, so the model of it has to be one tap away. */
function wordPill(word) {
  return `<span class="pill pill-say" style="color:var(--vio-d);font-size:13px;padding:5px 6px 5px 13px">
    ${escapeHtml(word)}${listenButton(word, { size: 'sm' })}</span>`;
}

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
        this page shows what was measured, and just as importantly, what Mira declined to judge.</div>
      </div>${aboutCard()}`;
    bindTechnicalToggle();
    return;
  }

  body.innerHTML = `
    ${lastSessionCard(last, name)}
    ${attemptStoryCard(last, name)}
    ${insightsCardShell()}
    ${whyExercisesCard()}
    ${positionCard(agg)}
    ${rewardCard()}
    ${trophyCard()}
    ${aboutCard(last.scorer)}`;

  bindReward();
  bindTechnicalToggle();
  loadInsights(last.targetPhone || 's');
}

/* --- SLM insights: a live note over numbers already shown above ---------- */
function insightsCardShell() {
  return `
  <div class="card" id="insightsCard">
    <h3>${icon('bulb')}What Mira has found</h3>
    <div class="note" id="insightsBody">Putting together a note on recent practice&hellip;</div>
  </div>`;
}

/* --- today's practice trail: which words, not a repeat of the note above -- */
function whyExercisesCard() {
  return `
  <div class="card" id="whyCard" style="display:none">
    <h3>${icon('target')}Today's practice trail</h3>
    <div class="note" id="whyBody"></div>
    <div id="whyWords" style="display:flex;flex-wrap:wrap;gap:7px;margin-top:9px"></div>
  </div>`;
}

async function loadInsights(targetPhone) {
  const el = $('#insightsBody');
  if (!el) return;
  try {
    const res = await fetch(`${config.endpoint}/insights`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        child_name: store.name || null,
        target_phone: targetPhone,
        sessions: store.sessions,
        word_bank: WORDS.map((w, i) => ({ index: i, text: w.text, position: w.position, phones: w.phones })),
      }),
    });
    if (!res.ok) throw new Error('bad status');
    const data = await res.json();
    const bullets = Array.isArray(data.bullets) ? data.bullets : [];
    el.innerHTML = bullets.length
      ? `<ul>${bullets.map(b => `<li>${renderBold(b)}</li>`).join('')}</ul>`
      : '';

    if (Array.isArray(data.next_words) && data.next_words.length) {
      store.nextWords = data.next_words;
      const whyCard = $('#whyCard');
      const whyBody = $('#whyBody');
      const whyWords = $('#whyWords');
      if (whyCard && whyBody && whyWords) {
        whyBody.textContent = 'Mira picked out these words for the next practice trail, based on recent patterns.';
        whyWords.innerHTML = data.next_words
          .map(i => WORDS[i]).filter(Boolean)
          .map(w => wordPill(w.text))
          .join('');
        whyCard.style.display = '';
      }
    }
  } catch {
    // The tickers above already show the real numbers; losing the note is
    // a cosmetic failure, never a blocking one.
    const body = $('#insightsCard');
    if (body) body.remove();
  }
}

/* --- last session: the scored / not-scored pair leads ---------------------- */
function lastSessionCard(r, name) {
  const items = r.items.map(i => ({ word: { text: i.word, position: i.position }, verdict: i.verdict, result: null }));
  const fb = feedbackForSession(items.map(i => ({ ...i, result: {} })), 's', name);
  const when = new Date(r.at);

  return `
  <div class="card">
    <h3>${icon('clipboard')}Last session: ${r.levelName}</h3>
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
          ${fb.practise.map(w => wordPill(w)).join('')}
        </div>
        <div class="note" style="margin-top:8px">Slip these into ordinary conversation, no drilling required.
        If ${name} says one differently, just say the word back the right way and carry on.</div>
      </div>` : ''}
    <div class="note" style="margin-top:11px;font-size:12px;color:var(--ink-faint)">
      ${when.toLocaleDateString()} · ${when.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
    </div>
  </div>`;
}

/* --- every attempt, in plain words ---------------------------------------
   A word gets up to three goes, and what happened on the earlier ones is
   most of the story: "clear in the end" reads very differently when the
   first two goes dropped the sound entirely. Each word is shown with its
   whole chain of attempts, in the parent register — what happened, never a
   number, never a confidence.                                             */
const ATTEMPT_WORDS = {
  correct: 'clear',
  omitted: 'sound left out',
  substituted: 'sound came out differently',
  assimilated: 'blended into the sound beside it',
  not_scored: 'not scored',
};

function attemptPhrase(a) {
  if (a.outcome === 'retry' || a.outcome === 'error') return 'recording not usable';
  const v = a.verdict || 'not_scored';
  if (v === 'substituted') {
    const sub = (a.instances || []).find(i => i.substitute)?.substitute;
    return sub ? `sounded closer to /${sub}/` : ATTEMPT_WORDS.substituted;
  }
  return ATTEMPT_WORDS[v] || v;
}

function attemptStoryCard(r, name) {
  const rows = (r.items || [])
    .filter(it => (it.attempts || []).length)
    .map(it => {
      const attempts = it.attempts;
      const chips = attempts.map(a => {
        const cls = a.outcome === 'scored' ? (a.verdict || 'not_scored') : 'retry';
        return `<span class="attempt-chip ${cls}"><span class="n">${a.n}</span>${attemptPhrase(a)}</span>`;
      }).join('<span class="attempt-arrow">&rsaquo;</span>');
      return `
      <div style="margin-bottom:11px">
        <div style="display:flex;align-items:center;gap:7px">
          <b style="font-family:var(--font-kid);font-size:15px">${escapeHtml(it.word)}</b>
          ${listenButton(it.word, { size: 'sm' })}
          <span style="font-size:11px;font-weight:800;color:var(--ink-soft);
            text-transform:uppercase;letter-spacing:.6px">${it.position}</span>
        </div>
        <div class="attempts">${chips}</div>
      </div>`;
    }).join('');

  if (!rows) return '';                        // session recorded before attempts were kept

  const multi = (r.items || []).some(it => (it.attempts || []).length > 1);
  return `
  <div class="card">
    <h3>${icon('target')}Every attempt, word by word</h3>
    ${rows}
    <div class="note">${multi
      ? `Where ${name} had more than one go at a word, each go is shown separately —
         they often differ, and the earlier ones say as much as the last.`
      : `Each word here was scored on a single recording.`}
      Tap the speaker to hear how the word sounds.</div>
  </div>`;
}

/* --- by position: never collapsed ---------------------------------------- */
function positionCard(agg) {
  const order = ['initial', 'medial', 'final'];
  const label = { initial: 'Start of words', medial: 'Middle of words', final: 'End of words' };
  const zoneIcon = { initial: 'zoneStart', medial: 'zoneMiddle', final: 'zoneEnd' };
  const rows = order.filter(p => agg.byPosition[p]).map(p => {
    const v = agg.byPosition[p];
    const total = v.scored + v.notScored || 1;
    const clearPct = (v.clear / total) * 100;
    const flagPct = ((v.scored - v.clear) / total) * 100;
    const nsPct = (v.notScored / total) * 100;
    return `
      <div class="posrow" style="display:flex;align-items:center;gap:10px">
        <div style="width:40px;height:40px;flex:0 0 auto">${icon(zoneIcon[p], 40)}</div>
        <div style="flex:1">
          <div class="top"><span>${label[p]}</span>
            <span class="ex">${v.clear} clear · ${v.scored - v.clear} flagged${v.notScored ? ` · ${v.notScored} not scored` : ''}</span></div>
          <div class="track">
            <div class="fill clear" style="width:${clearPct}%"></div>
            <div class="fill flag" style="width:${flagPct}%"></div>
            <div class="fill ns" style="width:${nsPct}%"></div>
          </div>
        </div>
      </div>`;
  }).join('');

  if (!rows) return '';
  return `
  <div class="card">
    <h3>${icon('chart')}Across word positions</h3>
    ${rows}
    <div class="note" style="margin-top:9px">A sound can be clear at the start of a word and
    harder at the end; they are counted separately because they are genuinely different skills.</div>
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
    <button class="btn-accent" id="editGoal" style="width:100%;margin-top:11px">Set a new reward goal</button>
    <div class="note" style="margin-top:9px">A star is only given when Mira marks the sound
    <b>correct</b>, never for a word it declined to judge. The goal tracks measured practice, not screen time.</div>
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

/* --- the honest limits, plain version up front, technical detail on tap -- */
function aboutCard(scorer) {
  const baseline = scorer && scorer.tier === 'gop_baseline';
  return `
  <div class="card">
    <div class="note" style="display:flex;gap:9px;align-items:flex-start">
      <span style="flex:0 0 auto">${icon('shield')}</span>
      <span>Not a diagnosis: a practice tool to help your child's pronunciation improve over time.</span>
    </div>
    <button class="btn-ghost" id="toggleTechnical" style="width:100%;margin-top:11px">Show technical details</button>
    <div class="note" id="technicalDetails" style="margin-top:10px;display:none">
      ${scorer ? `
      <div>
        <b>Scorer:</b> ${scorer.tier === 'gop_baseline' ? 'goodness-of-pronunciation baseline' : scorer.tier}.
        ${baseline ? `Its ability to tell a good production from a poor one measures
        <b>${scorer.expected_auc}</b> (where 0.5 is a coin toss and 1.0 is perfect).
        A stronger version of this model reaches 0.843 but is not installed.` : ''}
        ${scorer.calibrated === false ? `Confidence values here are raw model output and are
        <b>not calibrated</b>, treat them as a ranking, not a probability.` : ''}
      </div>` : ''}
      <div style="margin-top:9px;font-size:12px;color:var(--ink-faint)">
        The underlying approach was tested on ${SVARAH.nUtterances.toLocaleString()} Indian-English
        recordings across 17 states and showed no accent penalty: it flagged
        ${(SVARAH.flagRate * 100).toFixed(1)}% of sounds, below its own
        ${(SVARAH.ownNoiseFloor * 100).toFixed(1)}% baseline. Figures for the fully trained
        version: detection ${(OPERATING_POINT.recallOnPoor * 100).toFixed(1)}%,
        false alarms ${(OPERATING_POINT.falsePositiveRate * 100).toFixed(1)}%.
      </div>
      <div style="margin-top:9px;font-size:12px;color:var(--ink-faint)">
        Full technical detail, per-word scores and provenance live in the clinician tab.
      </div>
    </div>
  </div>`;
}

function bindTechnicalToggle() {
  const btn = $('#toggleTechnical');
  const panel = $('#technicalDetails');
  if (!btn || !panel) return;
  btn.addEventListener('click', () => {
    const show = panel.style.display === 'none';
    panel.style.display = show ? 'block' : 'none';
    btn.textContent = show ? 'Hide technical details' : 'Show technical details';
  });
}

/** Insight bullets may carry **bold** markers from the SLM. Escape first,
 *  so nothing in the model's own text can inject a tag, then convert only
 *  that one marker into <b> — no other markdown, no raw HTML ever passes
 *  through. */
function renderBold(s) {
  return escapeHtml(s).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>');
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}
