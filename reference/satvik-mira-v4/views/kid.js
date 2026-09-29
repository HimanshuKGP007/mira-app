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
import { LEVELS, WORDS, newSession, current, isComplete, TARGET_PHONE, TARGET_LABEL } from '../core/exercise.js';
import * as rewards from '../core/rewards.js';
import { store, BADGES } from '../core/rewards.js';
import { score, OUTCOME } from '../core/client.js';
import { Recorder } from '../core/capture.js';
import { GATES } from '../core/policy.js';
import { drift, parallax, stagger } from '../core/motion.js';
import { runTour } from '../core/onboarding.js';

const $ = s => document.querySelector(s);
const REC_MS = 3000;

let ctx = null;              // { go, say, sfx }
let session = null;
let recorder = null;
let busy = false;
let raf = null;
let recTimer = null;
let _mapParallax = null;   // must be stopped before each renderMap() re-wires it, or
                            // pointermove listeners pile up on #mapWorld across visits
let _mapDrifts = [];       // same reason: drift()'s iterations:Infinity animations never
                            // resolve .finished on their own, so their handles in
                            // motion.js's live-handle set must be stopped explicitly

export function init(context) {
  ctx = context;
  // #mira-ex / #mira-done are the two static mascot slots; the map's
  // mascot is the dynamically-created .map-marker (see renderMap below) —
  // there used to be a third static "#mira-map" div here too, but it was
  // always display:none and nothing ever showed it.
  ['#mira-ex', '#mira-done'].forEach((sel, i) => {
    const el = $(sel);
    if (el) el.innerHTML = miraSVG([112, 160][i]);
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
  return `
    <div class="lvl-ring"><svg viewBox="0 0 44 44">
      <circle cx="22" cy="22" r="${r}" fill="none" stroke="#D9DEEC" stroke-width="5"/>
      <circle cx="22" cy="22" r="${r}" fill="none" stroke="#7A6CF0" stroke-width="5"
        stroke-linecap="round" stroke-dasharray="${c}" stroke-dashoffset="${c * (1 - p)}"/>
    </svg><b>${rewards.explorerLevel()}</b></div>
    <div class="stat">${icon('star', 18)}<span>${store.stars}</span></div>
    <div class="stat">${icon('crown', 18)}<span>${crowns}/${LEVELS.length * 3}</span></div>`;
}

/* ---------------- map ---------------- */
// One entry per LEVELS entry — MUST stay the same length as core/exercise.js's
// LEVELS array (renderMap indexes NODE_POS[i] by level index; Phase 4's
// 6->7 level expansion is exactly the kind of change that silently breaks
// this if the two arrays drift). y is compressed into the top ~68% of the
// 620-tall viewBox (max 420, not the old 524) so the lowest node never lands
// under the floating dock (Phase 2a) — on a short viewport the dock's
// ~100px footprint would otherwise sit directly on top of the very node
// (the "current" one) a child needs to tap first. x zigzags for the trail's
// winding-path look.
const NODE_POS = [
  { x: 170, y: 420 }, { x: 96, y: 362 }, { x: 212, y: 304 },
  { x: 100, y: 246 }, { x: 220, y: 188 }, { x: 110, y: 130 }, { x: 200, y: 72 },
];
const lvState = id => store.levels[id] || { done: false, crowns: 0 };
const currentIndex = () => {
  for (let i = 0; i < LEVELS.length; i++) if (!lvState(LEVELS[i].id).done) return i;
  return LEVELS.length;
};
/** Deterministic per-level seed for core/music.js — same trail, same key every time. */
export function currentLevelSeed() { return Math.min(currentIndex(), LEVELS.length - 1); }

function trailPath() {
  let d = `M ${NODE_POS[0].x} ${NODE_POS[0].y}`;
  for (let i = 1; i < NODE_POS.length; i++) {
    const a = NODE_POS[i - 1], b = NODE_POS[i];
    const cy = (a.y + b.y) / 2;
    d += ` Q ${a.x} ${cy} ${(a.x + b.x) / 2} ${cy} T ${b.x} ${b.y}`;
  }
  return d;
}

/* ---------------- mascot dialogue — pooled, no immediate repeats ---------- */
const DIALOGUE = {
  firstEver: [
    "Welcome to the Snake Trail! I'll walk it with you.",
    "This is our trail! Tap a glowing spot to start.",
  ],
  arriveAfterLevel: [
    'That was great! Onward!',
    'Look how far we have come!',
    'The trail keeps going — ready?',
    "You're getting so good at this!",
  ],
  arriveAfterBreak: [
    'You came back! I missed you.',
    'Welcome back, explorer!',
    "Ready to pick up where we left off?",
  ],
  arriveIdleDay: [
    'Ready for today\'s trail?',
    "Let's go find some snake sounds!",
  ],
  idleNudge: [
    'Tap a glowing spot when you\'re ready!',
    "I'm right here whenever you want to play.",
    'Whenever you like — no rush!',
  ],
  lockedNode: [
    'Not yet — let\'s finish this trail first!',
    'That one\'s still asleep. Onward first!',
  ],
};
const _lastLine = {};
function sayPool(pool) {
  const lines = DIALOGUE[pool];
  if (!lines || !lines.length) return;
  let line = lines[Math.floor(Math.random() * lines.length)];
  if (lines.length > 1 && line === _lastLine[pool]) {
    line = lines[(lines.indexOf(line) + 1) % lines.length];
  }
  _lastLine[pool] = line;
  mapBubble(line);
}

/** The map screen's own speech bubble — separate from the exercise screen's
 *  #exBubble, which lives on a different (inactive) screen and would never be
 *  visible while the child is looking at the trail. */
let mapBubbleTimer = null;
function mapBubble(text) {
  const el = $('#mapBubble');
  if (!el) { ctx.say(text); return; }
  el.style.display = 'block';
  el.style.animation = 'none'; void el.offsetWidth; el.style.animation = '';
  el.textContent = text;
  ctx.say(text);
  clearTimeout(mapBubbleTimer);
  mapBubbleTimer = setTimeout(() => { el.style.display = 'none'; }, 6000);
}

let idleTimer = null;
function armIdleNudge() {
  clearTimeout(idleTimer);
  idleTimer = setTimeout(() => {
    if ($('#s-map').classList.contains('active')) sayPool('idleNudge');
  }, 16000);
}
function disarmIdleNudge() { clearTimeout(idleTimer); }

/* ---------------- Mira walking the trail between nodes -------------------- */
let _nodeFracCache = null;
function nodeLengthFractions(pathEl) {
  if (_nodeFracCache) return _nodeFracCache;
  const total = pathEl.getTotalLength();
  const SAMPLES = 500;
  const samples = [];
  for (let i = 0; i <= SAMPLES; i++) samples.push(pathEl.getPointAtLength((i / SAMPLES) * total));
  _nodeFracCache = NODE_POS.map(node => {
    let best = 0, bestDist = Infinity;
    samples.forEach((pt, i) => {
      const d = (pt.x - node.x) ** 2 + (pt.y - node.y) ** 2;
      if (d < bestDist) { bestDist = d; best = i / SAMPLES; }
    });
    return best;
  });
  return _nodeFracCache;
}

function placeMarkerPct(marker, x, y) {
  marker.style.left = `${(x / 340) * 100}%`;
  marker.style.top = `${(y / 620) * 100}%`;
}

let walkRaf = null;
function walkMarker(marker, pathEl, fromIdx, toIdx, onDone) {
  const fracs = nodeLengthFractions(pathEl);
  const total = pathEl.getTotalLength();
  const f0 = fracs[Math.min(fromIdx, fracs.length - 1)];
  const f1 = fracs[Math.min(toIdx, fracs.length - 1)];
  const durMs = Math.max(500, Math.abs(toIdx - fromIdx) * 650);
  const t0 = performance.now();
  cancelAnimationFrame(walkRaf);
  marker.classList.add('walking');
  function step(now) {
    const p = Math.min(1, (now - t0) / durMs);
    const eased = p < 0.5 ? 2 * p * p : 1 - ((-2 * p + 2) ** 2) / 2;
    const frac = f0 + (f1 - f0) * eased;
    const pt = pathEl.getPointAtLength(frac * total);
    placeMarkerPct(marker, pt.x, pt.y);
    if (p < 1) { walkRaf = requestAnimationFrame(step); }
    else { marker.classList.remove('walking'); onDone && onDone(); }
  }
  walkRaf = requestAnimationFrame(step);
}

/* Trail friends (Phase 5) — purely decorative, same footing as the tree
   scatter: they never speak, never gate anything, just make the woods feel
   inhabited. pointer-events:none so they can never steal a tap meant for a
   node or the dock underneath. */
const TRAIL_FRIENDS = [
  { key: 'fox', x: 296, y: 372, size: 46 },
  { key: 'otter', x: 36, y: 470, size: 42 },
  { key: 'bunny', x: 278, y: 156, size: 40 },
];
function friendsHTML() {
  return TRAIL_FRIENDS.map(f => `<div style="position:absolute;pointer-events:none;
    left:${(f.x / 340) * 100}%;top:${(f.y / 620) * 100}%;transform:translate(-50%,-50%);
    width:${f.size}px;height:${f.size}px;z-index:4">${icon(f.key, f.size)}</div>`).join('');
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
    <g class="map-clouds">
      <ellipse class="map-cloud" cx="60" cy="80" rx="40" ry="18" fill="#fff" opacity=".6"/>
      <ellipse class="map-cloud" cx="270" cy="130" rx="46" ry="20" fill="#fff" opacity=".55"/>
    </g>
    <g class="map-far">
      <path d="M0 600 Q90 520 180 590 T340 560 V620 H0 Z" fill="#CDE9BE"/>
      ${bushes}
    </g>
    <path d="${d}" fill="none" stroke="#D9B382" stroke-width="26" stroke-linecap="round" stroke-linejoin="round" opacity=".5"/>
    <path d="${d}" fill="none" stroke="#EBD3AC" stroke-width="16" stroke-linecap="round" stroke-linejoin="round" opacity=".9"/>
    <path id="trailPathEl" d="${d}" fill="none" stroke="#8ED97F" stroke-width="9" stroke-linecap="round"
      stroke-dasharray="1400" stroke-dashoffset="${1400 - 1400 * frac}" opacity=".85"/>
    <g class="map-near">${trees}</g></svg>
    <div class="map-near-snake" style="position:absolute;left:${(160 / 340) * 100}%;top:${(28 / 620) * 100}%;
      transform:translate(-50%,-50%);width:60px;height:60px">${ICONS.snake}</div>
    ${friendsHTML()}`;

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

  for (let i = 0; i < 6; i++) {
    html += `<div class="firefly" style="left:${10 + Math.random() * 80}%;top:${20 + Math.random() * 70}%;
      animation-delay:${(Math.random() * 4).toFixed(1)}s"></div>`;
  }

  const world = $('#mapWorld');
  world.innerHTML = html;

  // Ambient motion budget (Phase 2c): nothing on the map sits perfectly
  // still. Clouds drift independently, the sky/mid/near layers separate on
  // pointer parallax, and the trail nodes pop in staggered rather than
  // appearing all at once. renderMap() re-runs on every visit (after each
  // level, from the dock, etc.), and innerHTML just detached the previous
  // layer elements — the old parallax listener must be stopped, not left
  // running against nodes that no longer exist.
  if (_mapParallax) { _mapParallax.stop(); _mapParallax = null; }
  _mapDrifts.forEach(h => h && h.stop());
  _mapDrifts = [...world.querySelectorAll('.map-cloud')].map(c =>
    drift(c, { amp: 10 + Math.random() * 8, period: 9 + Math.random() * 5 }));
  _mapParallax = parallax([
    { el: world.querySelector('.map-clouds'), depth: 3 },
    { el: world.querySelector('.map-far'), depth: 6 },
    { el: world.querySelector('.map-near'), depth: 10 },
    { el: world.querySelector('.map-near-snake'), depth: 10 },
  ], { root: world });
  stagger(world.querySelectorAll('.node'),
    { transform: ['scale(0)', 'scale(1)'], opacity: [0, 1] },
    { each: 0.08, duration: 0.5, bounce: 0.55 });

  world.querySelectorAll('.node').forEach(n => {
    n.addEventListener('click', () => {
      const i = +n.dataset.i;
      if (n.classList.contains('locked')) {
        n.animate([{ transform: 'translate(-50%,-50%) rotate(-4deg)' },
                   { transform: 'translate(-50%,-50%) rotate(4deg)' },
                   { transform: 'translate(-50%,-50%)' }], { duration: 280 });
        ctx.sfx('uhoh');
        sayPool('lockedNode');
        return;
      }
      ctx.sfx('nodeTap');
      disarmIdleNudge();
      clearTimeout(mapBubbleTimer);
      const mb = $('#mapBubble'); if (mb) mb.style.display = 'none';
      startLevel(LEVELS[i]);
    });
  });

  // Mira herself: walk from her last known spot to the current node when it
  // has advanced (i.e. we just returned from clearing a level); otherwise
  // place her instantly — a cold boot shouldn't animate a walk from nowhere.
  const marker = document.createElement('div');
  marker.className = 'map-marker';
  marker.innerHTML = miraSVG(42);
  world.appendChild(marker);
  const pathEl = world.querySelector('#trailPathEl');
  const endIdx = Math.min(cur, NODE_POS.length - 1);
  const shouldWalk = _mapVisited && _lastMapIndex !== null && _lastMapIndex !== endIdx && pathEl;

  if (shouldWalk) {
    const startIdx = Math.min(_lastMapIndex, NODE_POS.length - 1);
    placeMarkerPct(marker, NODE_POS[startIdx].x, NODE_POS[startIdx].y);
    walkMarker(marker, pathEl, startIdx, endIdx, () => {
      miraState('celebrating');
      sayPool('arriveAfterLevel');
      setTimeout(() => miraState(null), 1400);
      armIdleNudge();
    });
  } else {
    placeMarkerPct(marker, NODE_POS[endIdx].x, NODE_POS[endIdx].y);
    if (!_mapVisited) {
      const everPlayed = Object.keys(store.levels).length > 0;
      const today = new Date().toISOString().slice(0, 10);
      if (!everPlayed) sayPool('firstEver');
      else if (store.lastDone && store.lastDone !== today) sayPool('arriveAfterBreak');
      else sayPool('arriveIdleDay');
    }
    armIdleNudge();
  }
  _mapVisited = true;
  _lastMapIndex = endIdx;

  // First-run spotlight (Phase 6) — no-ops after the first time (runTour's
  // own hasSeen check). Delayed so it never talks over Mira's own greeting
  // line above; the delay is generous because that greeting is itself
  // spoken text with variable length.
  setTimeout(() => {
    runTour('map', [
      { anchor: '.node.current', title: 'Your trail', body: 'Tap the glowing circle to start a level!' },
      { anchor: '#dockStash', title: 'Sticker Stash', body: 'Trophies and trail chapters live here.' },
      { anchor: '#dockAdults', title: 'For grown-ups', body: 'A grown-up can check on progress here anytime.' },
    ], { say: ctx.say, sfx: ctx.sfx });
  }, 2200);
}
let _mapVisited = false;
let _lastMapIndex = null;

/* ---------------- sticker stash ----------------
   Two shelves, both reusing the div patterns from the reference art:

   Trophies — the same BADGES store rewards.js already tracks, given a real
   home instead of only flashing past as a celebration-screen toast. Built
   as "category tiles" (icon badge overlapping a colour-domed arch) rather
   than plain circles; locked trophies stay visible (greyed) rather than
   hidden, so the shelf reads as a collection to complete.

   Trail Chapters — built as "story cards" (rounded art tile, label
   outside/below it), one per level, walking the same locked/current/done
   states the map's nodes already use (lvState()). Gives the stash real
   content instead of empty space below the trophy shelf, and previews
   Phase 5's chapter naming without needing it finished first. */
const CAT_COLORS = ['var(--sky)', 'var(--grape)', 'var(--clay)', 'var(--sun)'];

export function renderStash() {
  const have = new Set(store.badges);
  const curIdx = currentIndex();
  const body = $('#stashBody');
  body.innerHTML = `
    <div class="shelf">
      <div class="t">Trophies</div>
      <div class="cat-row">
        ${BADGES.map((b, i) => `
          <div class="cat-tile ${have.has(b.id) ? 'earned' : ''}" style="--cat-color:${CAT_COLORS[i % CAT_COLORS.length]}">
            <div class="cat-icon">${icon(b.icon, 26, { animate: have.has(b.id) })}</div>
            <div class="cat-dome"><span class="n">${b.name}</span></div>
          </div>`).join('')}
      </div>
    </div>
    <div class="shelf">
      <div class="t">Trail Chapters</div>
      <div class="story-row">
        ${LEVELS.map((lvl, i) => {
          const st = lvState(lvl.id);
          const locked = i > curIdx;
          const repIcon = WORDS[lvl.words[0]].icon;
          const tint = `color-mix(in srgb, ${CAT_COLORS[i % CAT_COLORS.length]} 24%, var(--paper))`;
          return `
          <div class="story-card ${locked ? 'locked' : ''}" style="--story-color:${tint}">
            <div class="story-art">${locked ? icon('lock', 30, { animate: false }) : icon(repIcon, 52)}</div>
            <div class="story-label">${locked ? '???' : lvl.name}</div>
          </div>`;
        }).join('')}
      </div>
    </div>`;
  stagger(body.querySelectorAll('.cat-tile'),
    { transform: ['scale(0.5)', 'scale(1)'], opacity: [0, 1] },
    { each: 0.07, duration: 0.45, bounce: 0.5 });
  stagger(body.querySelectorAll('.story-card'),
    { transform: ['scale(0.85) translateY(10px)', 'scale(1) translateY(0)'], opacity: [0, 1] },
    { each: 0.06, delay: 0.2, duration: 0.4, bounce: 0.45 });
}

/* ---------------- exercise ---------------- */
export async function startLevel(level) {
  session = newSession(level);
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

  if (first) {
    setTimeout(() => {
      runTour('exercise', [
        { anchor: '#picCard', title: 'Say the word', body: 'This is the word — look at the picture and say it out loud!' },
        { anchor: '#micBtn', title: 'Tap to talk', body: 'Tap the purple button, then say the word. Mira is listening!' },
      ], { say: ctx.say, sfx: ctx.sfx });
    }, 1800);
  }
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
  ctx.sfx('recordStart');
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
  ctx.sfx('recordStop');
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
  if (res.outcome === OUTCOME.AUTH_REQUIRED) {
    miraState(null);
    bubble("Let's sign back in!");
    ctx.signOut ? ctx.signOut() : showAlert('err', res.error, false);
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
  const target = result.target;
  it.result = result;
  it.attempts++;

  // The word may be unscorable outright (not in the dictionary, no phone mapped).
  const unscorable = result.unscorableReason && !result.phones.length;
  const verdict = unscorable ? 'not_scored' : (target ? target.marking : 'not_scored');

  // Record THIS attempt before branching on what happens next — a flagged
  // first try followed by a corrected retry used to vanish entirely, since
  // `it.result` above just got overwritten by the second attempt. The parent
  // view's sound-by-sound detail reads this to show the retry pattern, not
  // just the final word.
  it.attemptHistory.push({
    attempt: it.attempts,
    verdict,
    substitute: !unscorable ? (target?.substitute ?? null) : null,
    confidence: !unscorable ? (target?.confidence ?? null) : null,
    confidenceKind: !unscorable ? (target?.confidenceKind ?? null) : null,
    reason: !unscorable ? (target?.reason ?? null) : (result.unscorableReason || null),
  });

  if (unscorable) {
    it.verdict = 'not_scored';
    paint('not_scored');
    miraState(null);
    bubble("Let's come back to that one later!");
    setTimeout(next, 1900);
    return;
  }

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

  // flagged — one retry, then move on. Never negative, never a star.
  if (it.attempts < 2) {
    paint('flagged');
    ctx.sfx('soft');
    miraState(null);
    bubble(`Almost! Listen — ${it.word.text}. Your turn!`);
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

  $('#badgePops').innerHTML = out.badges.map((b, i) =>
    `<div class="badge-pop" style="animation-delay:${0.6 + i * 0.3}s">${icon(b.icon, 31)}
      <div><div class="t">New trophy!</div><div class="n">${b.name}</div></div></div>`).join('');
  out.badges.forEach((b, i) => setTimeout(() => ctx.sfx('sticker'), (0.6 + i * 0.3) * 1000));

  const unlockedNext = currentIndex() < LEVELS.length;
  $('#doneNext').style.display = unlockedNext ? 'inline-block' : 'none';
  if (unlockedNext) setTimeout(() => ctx.sfx('unlock'), 1300);

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
