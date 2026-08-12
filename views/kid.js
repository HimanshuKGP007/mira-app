/* ============================================================================
   kid.js — the game surface.

   Reward mapping is the whole point of this file:
     marking 'correct'      -> celebrate, star, green segment
     flagged (sub/om/assim) -> "almost", NO star, one retry offered
     'not_scored'           -> neutral, NO star, NO penalty, excluded from
                               the crown denominator

   The child never sees a number, a percentage or a confidence value.
   ========================================================================== */

import { ICONS, icon, miraSVG } from './icons.js';
import { LEVELS, newSession, current, isComplete, levelFromWords, TARGET_PHONE, TARGET_LABEL } from '../core/exercise.js';
import * as rewards from '../core/rewards.js';
import { store } from '../core/rewards.js';
import { score, OUTCOME } from '../core/client.js';
import { Recorder } from '../core/capture.js';
import { GATES } from '../core/policy.js';

const $ = s => document.querySelector(s);
const REC_MS = 3000;

let ctx = null;              // { go, say, sfx }
let session = null;
let recorder = null;
let busy = false;
let raf = null;
let recTimer = null;

export function init(context) {
  ctx = context;
  ['#mira-map', '#mira-ex', '#mira-done'].forEach((sel, i) => {
    const el = $(sel);
    if (el) el.innerHTML = miraSVG([44, 112, 160][i]);
  });
  $('#exBack').addEventListener('click', () => { abortRecording(); renderMap(); ctx.go('#s-map'); });
  $('#micBtn').addEventListener('pointerdown', onMic);
  $('#doneNext').addEventListener('click', onNext);
  $('#doneMap').addEventListener('click', () => { renderMap(); ctx.go('#s-map'); });
  $('#retryBtn').addEventListener('click', () => { hideAlert(); armMic(); });
}

const miras = () => [...document.querySelectorAll('.mira')];
export function miraState(cls) {
  miras().forEach(m => {
    m.classList.remove('listening', 'celebrating', 'thinking');
    if (cls) m.classList.add(cls);
  });
}
export function miraTalking(on) { miras().forEach(m => m.classList.toggle('talking', on)); }

/* ---------------- HUD ---------------- */
export function hudHTML() {
  const p = rewards.xpInLevel() / rewards.XP_PER_LEVEL;
  const r = 19, c = 2 * Math.PI * r;
  const crowns = Object.values(store.levels).reduce((a, l) => a + (l.crowns || 0), 0);
  const trailsDone = Object.values(store.levels).filter(l => l.done).length;
  return `
    <div class="lvl-ring"><svg viewBox="0 0 44 44">
      <circle cx="22" cy="22" r="${r}" fill="none" stroke="#D9DEEC" stroke-width="5"/>
      <circle cx="22" cy="22" r="${r}" fill="none" stroke="#7A6CF0" stroke-width="5"
        stroke-linecap="round" stroke-dasharray="${c}" stroke-dashoffset="${c * (1 - p)}"/>
    </svg><b>${rewards.explorerLevel()}</b></div>
    <div class="stat">${icon('trophy', 18)}<span>${trailsDone}/${LEVELS.length}</span></div>
    <div class="stat">${icon('star', 18)}<span>${store.stars}</span></div>
    <div class="stat">${icon('crown', 18)}<span>${crowns}/${LEVELS.length * 3}</span></div>`;
}

/* ---------------- map ---------------- */
const NODE_POS = [
  { x: 170, y: 524 }, { x: 96, y: 430 }, { x: 212, y: 338 },
  { x: 108, y: 248 }, { x: 226, y: 162 }, { x: 160, y: 80 }, { x: 270, y: 44 },
];
const lvState = id => store.levels[id] || { done: false, crowns: 0 };
const currentIndex = () => {
  for (let i = 0; i < LEVELS.length; i++) if (!lvState(LEVELS[i].id).done) return i;
  return LEVELS.length;
};

function trailPath() {
  let d = `M ${NODE_POS[0].x} ${NODE_POS[0].y}`;
  for (let i = 1; i < NODE_POS.length; i++) {
    const a = NODE_POS[i - 1], b = NODE_POS[i];
    const cy = (a.y + b.y) / 2;
    d += ` Q ${a.x} ${cy} ${(a.x + b.x) / 2} ${cy} T ${b.x} ${b.y}`;
  }
  return d;
}

export function renderMap() {
  const cur = currentIndex();
  $('#mapHud').innerHTML = `<span class="t">Snake Trail</span>${hudHTML()}`;

  const d = trailPath();
  const frac = Math.min(cur, NODE_POS.length - 1) / (NODE_POS.length - 1);
  const trees = [[30, 540], [300, 500], [60, 410], [280, 320], [40, 300], [300, 240],
                 [70, 180], [250, 120], [120, 150], [210, 470]]
    .map(([x, y], i) => `<g transform="translate(${x} ${y}) scale(${0.8 + (i % 3) * 0.15})">
      <path d="M0 0 L-13 22 L13 22 Z" fill="#4E9E46"/><path d="M0 -12 L-11 12 L11 12 Z" fill="#5BAF4E"/>
      <path d="M0 -22 L-9 4 L9 4 Z" fill="#6FC85F"/><rect x="-3" y="22" width="6" height="8" fill="#8A6A44"/></g>`).join('');
  const bushes = [[20, 585], [350, 560], [130, 520], [230, 540], [300, 420]]
    .map(([x, y]) => `<ellipse cx="${x}" cy="${y}" rx="24" ry="14" fill="#7FCB6E"/>`).join('');

  let html = `<svg class="map-bg" viewBox="0 0 340 620" preserveAspectRatio="xMidYMid slice">
    <defs><linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#DFF2FF"/><stop offset=".5" stop-color="#EAF6E7"/>
      <stop offset="1" stop-color="#E4F1DA"/></linearGradient></defs>
    <rect width="340" height="620" fill="url(#sky)"/>
    <ellipse cx="60" cy="80" rx="40" ry="18" fill="#fff" opacity=".6"/>
    <ellipse cx="270" cy="130" rx="46" ry="20" fill="#fff" opacity=".55"/>
    <path d="M0 600 Q90 520 180 590 T340 560 V620 H0 Z" fill="#CDE9BE"/>
    ${bushes}
    <path d="${d}" fill="none" stroke="#D9B382" stroke-width="26" stroke-linecap="round" stroke-linejoin="round" opacity=".5"/>
    <path d="${d}" fill="none" stroke="#EBD3AC" stroke-width="16" stroke-linecap="round" stroke-linejoin="round" opacity=".9"/>
    <path d="${d}" fill="none" stroke="#8ED97F" stroke-width="9" stroke-linecap="round"
      stroke-dasharray="1400" stroke-dashoffset="${1400 - 1400 * frac}" opacity=".85"/>
    ${trees}</svg>
    <div style="position:absolute;left:${(160 / 340) * 100}%;top:${(28 / 620) * 100}%;
      transform:translate(-50%,-50%);width:60px;height:60px">${ICONS.snake}</div>`;

  LEVELS.forEach((lv, i) => {
    const st = lvState(lv.id);
    const cls = st.done ? 'done' : i === cur ? 'current' : 'locked';
    const p = NODE_POS[i];
    const face = cls === 'locked'
      ? `<div class="face">${icon('lock', 26)}</div>`
      : cls === 'done'
        ? `<div class="face">${icon('crown', 26)}</div>`
        : `<div class="face"><span class="num">${lv.id}</span></div>`;
    const crowns = st.crowns
      ? `<div class="crowns">${[1, 2, 3].map(n => `<span class="${n <= st.crowns ? '' : 'off'}">${icon('crown', 11)}</span>`).join('')}</div>`
      : '';
    const name = (i === cur || st.done) ? `<div class="name">${lv.name}</div>` : '';
    html += `<button class="node ${cls}" data-i="${i}"
      style="left:${(p.x / 340) * 100}%;top:${(p.y / 620) * 100}%">${name}${face}${crowns}</button>`;
  });

  if (cur < LEVELS.length) {
    const p = NODE_POS[cur];
    html += `<div class="map-marker" style="left:${(p.x / 340) * 100}%;top:${(p.y / 620) * 100}%">${miraSVG(42)}</div>`;
  }
  for (let i = 0; i < 6; i++) {
    html += `<div class="firefly" style="left:${10 + Math.random() * 80}%;top:${20 + Math.random() * 70}%;
      animation-delay:${(Math.random() * 4).toFixed(1)}s"></div>`;
  }

  if (store.nextWords && store.nextWords.length) {
    html += `<button class="node practice" id="practiceNode"
      style="left:50%;top:6%"><div class="name">Practice Trail</div><div class="face">${icon('bulb', 26)}</div></button>`;
  }

  const world = $('#mapWorld');
  world.innerHTML = html;

  const practiceBtn = $('#practiceNode');
  if (practiceBtn) {
    practiceBtn.addEventListener('click', () => {
      startLevel(levelFromWords(store.nextWords));
      store.nextWords = null;   // consumed - Mira will offer a new one after the next pattern update
    });
  }

  world.querySelectorAll('.node').forEach(n => {
    n.addEventListener('click', () => {
      const i = +n.dataset.i;
      if (n.classList.contains('locked')) {
        n.animate([{ transform: 'translate(-50%,-50%) rotate(-4deg)' },
                   { transform: 'translate(-50%,-50%) rotate(4deg)' },
                   { transform: 'translate(-50%,-50%)' }], { duration: 280 });
        return;
      }
      startLevel(LEVELS[i]);
    });
  });
}

/* ---------------- friends ---------------- */
export function renderFriends() {
  const have = rewards.unlockedFriends().map(f => f.id);
  $('#friendsCount').textContent = `${have.length} of ${rewards.FRIENDS.length} collected`;
  $('#friendsGrid').innerHTML = rewards.FRIENDS.map(f => {
    const unlocked = have.includes(f.id);
    return `
    <div style="display:flex;flex-direction:column;align-items:center;gap:5px">
      <div style="width:64px;height:64px;border-radius:50%;background:var(--nm);
        box-shadow:${unlocked ? 'var(--raise)' : 'var(--press-sm)'};display:grid;place-items:center;
        opacity:${unlocked ? '1' : '.35'};filter:${unlocked ? 'none' : 'grayscale(1)'}">
        ${unlocked ? icon(f.icon, 46) : icon('lock', 24)}
      </div>
      <div style="font-family:var(--font-kid);font-size:12px;font-weight:600;
        color:${unlocked ? 'var(--ink)' : 'var(--ink-faint)'}">${unlocked ? f.name : '?'}</div>
      ${!unlocked ? `<div style="font-size:10px;color:var(--ink-faint)">${f.stars} stars</div>` : ''}
    </div>`;
  }).join('');
}

/* ---------------- exercise ---------------- */
export async function startLevel(level) {
  session = newSession(level);
  session.startStars = store.stars;
  busy = false;
  if (!recorder) recorder = new Recorder();
  buildVine();
  updateMini();
  ctx.go('#s-ex');
  renderWord(true);
  recorder.init();               // permission prompt on first use, non-blocking
}

function buildVine() {
  $('#vine').innerHTML = session.items.map(() => `<div class="seg"></div>`).join('');
}
function updateMini() {
  $('#exStars').innerHTML = `${icon('star', 18)}<span>${store.stars}</span>`;
}

function renderWord(first) {
  const it = current(session);
  if (!it) return;
  const card = $('#picCard');
  card.className = 'pic-card';
  $('#cardArt').innerHTML = ICONS[it.word.icon] || ICONS.star;
  $('#cardArt').style.animation = 'none';
  void $('#cardArt').offsetWidth;
  $('#cardArt').style.animation = '';
  const w = it.word.text;
  const idx = w.toLowerCase().indexOf('s');
  $('#cardWord').innerHTML = idx >= 0
    ? `${w.slice(0, idx)}<b>${w[idx]}</b>${w.slice(idx + 1)}`
    : w;
  miraState(null);
  hideAlert();
  armMic();
  const line = first ? `${session.levelName}! What is this?` : 'What is this?';
  bubble(line);
}

function bubble(text) {
  const el = $('#exBubble');
  el.style.animation = 'none'; void el.offsetWidth; el.style.animation = '';
  el.textContent = text;
  ctx.say(text);
}

function armMic() {
  const b = $('#micBtn');
  b.disabled = false;
  b.classList.remove('rec');
  $('#micHint').textContent = 'Tap and say it!';
  busy = false;
}
function disarmMic() {
  const b = $('#micBtn');
  b.disabled = true;
  b.classList.remove('rec');
  $('#micHint').textContent = '';
  $('#wave').classList.remove('on');
}

async function onMic() {
  if (busy || !$('#s-ex').classList.contains('active')) return;
  busy = true;
  const ok = await recorder.init();
  if (!ok) {
    // Live scoring genuinely needs audio; there is no path that fakes it.
    showAlert('warn',
      'Mira needs the microphone to hear you. Allow microphone access in your browser, then tap the mic again.',
      false);
    busy = false;
    return;
  }
  startRecording();
}

function startRecording() {
  recorder.start();
  const b = $('#micBtn');
  b.classList.add('rec');
  $('#micHint').textContent = 'Listening…';
  $('#wave').classList.add('on');
  miraState('listening');
  bubble("I'm listening!");

  const arc = $('#sweepArc');
  arc.style.transition = 'none';
  arc.style.strokeDashoffset = '295.3';
  void arc.getBoundingClientRect();
  arc.style.transition = `stroke-dashoffset ${REC_MS}ms linear`;
  arc.style.strokeDashoffset = '0';

  drawWave();
  clearTimeout(recTimer);
  recTimer = setTimeout(finishRecording, REC_MS);
}

function abortRecording() {
  clearTimeout(recTimer);
  cancelAnimationFrame(raf);
  if (recorder?.recording) recorder.stop();
  disarmMic();
}

function drawWave() {
  const cv = $('#wave'), c = cv.getContext('2d');
  const W = cv.width, H = cv.height, N = 22, gap = 3;
  const bw = (W - gap * (N - 1)) / N;
  const lv = recorder.levels(N) || new Array(N).fill(0.1);
  c.clearRect(0, 0, W, H);
  c.fillStyle = '#5BAF4E';
  lv.forEach((v, i) => {
    const h = Math.max(4, v * H);
    c.beginPath();
    c.roundRect(i * (bw + gap), (H - h) / 2, bw, h, 3);
    c.fill();
  });
  if (recorder.recording) raf = requestAnimationFrame(drawWave);
}

async function finishRecording() {
  cancelAnimationFrame(raf);
  const take = recorder.stop();
  disarmMic();

  if (!take || take.durationMs < 300) {
    miraState(null);
    showAlert('info', "Mira didn't hear anything. Tap the mic and say the word out loud.", true);
    return;
  }
  // pre-flight only; the server's own gate is authoritative
  if (take.snrDb != null && take.snrDb < GATES.minSnrDb) {
    miraState(null);
    showAlert('warn', `It was a bit noisy there. Let's try that again somewhere quieter.`, true);
    return;
  }

  $('#picCard').classList.add('thinking');
  miraState('thinking');
  bubble('Hmm…');
  submit(take.blob);
}

async function submit(blob) {
  const it = current(session);
  const res = await score(blob, {
    promptWord: it.word.text,
    targetPhone: TARGET_PHONE,
  });
  $('#picCard').classList.remove('thinking');
  handleOutcome(res);
}

function handleOutcome(res) {
  const it = current(session);

  if (res.outcome === OUTCOME.NO_ENDPOINT) {
    miraState(null);
    showAlert('err',
      'No scorer is connected. Start the Mira scorer, then add its address in settings.',
      false);
    return;
  }
  if (res.outcome === OUTCOME.ERROR) {
    miraState(null);
    showAlert('err', res.error, true);
    return;
  }
  if (res.outcome === OUTCOME.RETRY) {
    miraState(null);
    showAlert('warn', res.retry.message, true);
    return;
  }

  // scored
  const result = res.result;
  const targets = result.targets || [];
  it.result = result;
  it.attempts++;

  // The word may be unscorable outright (not in the dictionary, no phone mapped).
  if (result.unscorableReason && !result.phones.length) {
    it.verdict = 'not_scored';
    paint('not_scored');
    miraState(null);
    bubble("Let's come back to that one later!");
    setTimeout(next, 1900);
    return;
  }

  // A word can contain /s/ more than once ("sausage", "socks"). It only
  // counts as correct when every instance does; the position graph still
  // tracks each instance's own outcome separately (see core/rewards.js).
  const verdict = targets.length
    ? (targets.every(t => t.marking === 'correct') ? 'correct'
       : targets.some(t => t.marking !== 'not_scored') ? 'substituted'
       : 'not_scored')
    : 'not_scored';

  const attemptConfidences = targets.map(t => t.confidence).filter(c => c != null);
  const worstThisAttempt = attemptConfidences.length ? Math.min(...attemptConfidences) : null;
  it.confidenceHistory.push(worstThisAttempt);

  if (verdict === 'correct') {
    it.verdict = 'correct';
    paint('correct');
    ctx.sfx('chime');
    miraState('celebrating');
    bubble(praise(it.word.text));
    flyStar();
    store.stars += rewards.STAR_PER_CORRECT;
    updateMini();
    setTimeout(next, 1750);
    return;
  }

  if (verdict === 'not_scored') {
    it.verdict = 'not_scored';
    paint('not_scored');
    miraState(null);
    bubble("Let's come back to that one later!");
    setTimeout(next, 1900);
    return;
  }

  // Flagged: retry only while attempts remain AND (this is the very first
  // retry, or the child is measurably improving). Hard cap at 3 attempts,
  // no exceptions — Mira is never allowed to get stuck on one word.
  const [prevConf, curConf] = it.confidenceHistory.slice(-2);
  const improving = prevConf != null && curConf != null && curConf > prevConf;
  const offerRetry = it.attempts < 3 && (it.attempts === 1 || improving);

  if (offerRetry) {
    paint('flagged');
    ctx.sfx('soft');
    miraState(null);
    bubble(`Almost! Listen: ${it.word.text}. Your turn!`);
    setTimeout(() => {
      $('#picCard').className = 'pic-card';
      armMic();
      $('#micHint').textContent = 'Try it again!';
    }, 2200);
    return;
  }

  it.verdict = verdict;
  paint('flagged');
  miraState(null);
  bubble('Good trying! We will practise that one again.');
  setTimeout(next, 1900);
}

const PRAISE = ['Clear! Lovely snake sound!', 'Perfect!', 'That was a great one!',
                'Beautiful sssound!', 'Lovely!'];
const praise = () => PRAISE[Math.floor(Math.random() * PRAISE.length)];

const FUN_FACTS = [
  "Lots of kids practice their sounds every single day, just like you!",
  "Snakes don't have ears, but they can feel sound through the ground!",
  "Your mouth makes hundreds of different sounds without you even thinking about it.",
  "The more you practice a sound, the easier it gets, like riding a bike!",
  "Some words have the same sound hiding in them more than once, like 'sausage'!",
];
const funFact = () => FUN_FACTS[Math.floor(Math.random() * FUN_FACTS.length)];

function paint(kind) {
  $('#picCard').className = `pic-card ring-${kind}`;
  const seg = $('#vine').children[session.index];
  if (seg) seg.className = `seg ${kind}`;
}

function next() {
  session.index++;
  if (isComplete(session) || session.index >= session.items.length) finish();
  else renderWord(false);
}

function flyStar() {
  const from = $('#picCard').getBoundingClientRect();
  const to = $('#exStars').getBoundingClientRect();
  const ph = $('#phone').getBoundingClientRect();
  const el = document.createElement('div');
  el.className = 'fly-star';
  el.innerHTML = icon('star', 28);
  el.style.left = `${from.left + from.width / 2 - ph.left - 14}px`;
  el.style.top = `${from.top + from.height / 2 - ph.top - 14}px`;
  $('#phone').appendChild(el);
  const dx = (to.left + to.width / 2) - (from.left + from.width / 2);
  const dy = (to.top + to.height / 2) - (from.top + from.height / 2);
  requestAnimationFrame(() => requestAnimationFrame(() => {
    el.style.transform = `translate(${dx}px,${dy}px) scale(.42) rotate(280deg)`;
    el.style.opacity = '.15';
  }));
  setTimeout(() => { el.remove(); ctx.sfx('sparkle'); }, 780);
}

function showAlert(kind, message, retryable, opts = {}) {
  const box = $('#exAlert');
  box.className = `alert ${kind}`;
  box.textContent = message;
  box.style.display = 'block';
  $('#retryBtn').style.display = retryable ? 'inline-block' : 'none';
  disarmMic();
  miraState(null);
  // don't leave Mira mid-thought while an alert explains what happened
  const el = $('#exBubble');
  el.textContent = retryable ? 'Let’s try that one again!' : 'We can try in a moment.';
  busy = false;
  ctx.say(message);
}
function hideAlert() {
  $('#exAlert').style.display = 'none';
  $('#retryBtn').style.display = 'none';
}

/* ---------------- celebration ---------------- */
function finish() {
  const out = rewards.commitSession({
    levelId: session.levelId,
    levelName: session.levelName,
    targetPhone: TARGET_PHONE,
    items: session.items,
    starsAlreadyCredited: true,   // each star was credited as it flew to the jar
  });

  const notScored = session.items.filter(i => i.verdict === 'not_scored').length;

  $('#doneTitle').textContent = out.crowns === 3 ? 'Perfect trail!' : 'Trail cleared!';
  $('#doneSub').textContent = notScored
    ? `Great work, ${store.name}! We'll come back to ${notScored === 1 ? 'one word' : `${notScored} words`} another day.`
    : `Great snake sounds, ${store.name}!`;

  $('#crownsBig').innerHTML = [1, 2, 3]
    .map(() => `<div class="crown-slot">${icon('crown', 31)}</div>`).join('');
  [...$('#crownsBig').children].forEach((s, i) => {
    if (i < out.crowns) setTimeout(() => { s.classList.add('on'); ctx.sfx('crown'); }, 400 + i * 260);
  });

  $('#rewardRow').innerHTML =
    `<div class="reward-pill">${icon('star', 20)}<span>+${out.earnedStars}</span></div>
     <div class="reward-pill">${icon('flame', 20)}<span>+${out.earnedXp} XP</span></div>`;

  $('#xpLabel').textContent = `Explorer Lv ${rewards.explorerLevel()}`;
  $('#xpPct').textContent = `${rewards.xpInLevel()}/${rewards.XP_PER_LEVEL} XP`;
  const fill = $('#xpFill');
  fill.style.width = '0';
  setTimeout(() => { fill.style.width = `${(rewards.xpInLevel() / rewards.XP_PER_LEVEL) * 100}%`; }, 300);

  const newFriends = rewards.friendsUnlockedBetween(session.startStars ?? store.stars, store.stars);
  $('#badgePops').innerHTML = [
    ...out.badges.map((b, i) =>
      `<div class="badge-pop" style="animation-delay:${0.6 + i * 0.3}s">${icon(b.icon, 31)}
        <div><div class="t">New trophy!</div><div class="n">${b.name}</div></div></div>`),
    ...newFriends.map((f, i) =>
      `<div class="badge-pop" style="animation-delay:${0.6 + (out.badges.length + i) * 0.3}s">${icon(f.icon, 31)}
        <div><div class="t">New friend!</div><div class="n">${f.name}</div></div></div>`),
  ].join('');

  const factEl = $('#doneFact');
  if (factEl) factEl.textContent = funFact();

  $('#doneNext').style.display = currentIndex() < LEVELS.length ? 'inline-block' : 'none';

  ctx.go('#s-done');
  miraState('celebrating');
  ctx.sfx('tada');
  confetti();
  ctx.say(`${out.crowns === 3 ? 'Perfect trail!' : 'Trail cleared!'} You earned ${out.earnedStars} stars.`);
}

function onNext() {
  const i = currentIndex();
  if (i < LEVELS.length) startLevel(LEVELS[i]);
  else { renderMap(); ctx.go('#s-map'); }
}

const CONF = ['#7A6CF0', '#43C06B', '#F5A93B', '#35C6C0', '#FFC93C', '#F0616A', '#FF9EC0'];
function confetti() {
  const c = $('#confetti');
  c.innerHTML = '';
  for (let i = 0; i < 44; i++) {
    const p = document.createElement('i');
    p.style.left = `${Math.random() * 100}%`;
    p.style.background = CONF[i % CONF.length];
    p.style.animationDuration = `${2.2 + Math.random() * 2.2}s`;
    p.style.animationDelay = `${Math.random() * 1.2}s`;
    p.style.transform = `rotate(${Math.random() * 360}deg)`;
    if (Math.random() < 0.3) p.style.borderRadius = '50%';
    c.appendChild(p);
  }
}

export { TARGET_LABEL };
