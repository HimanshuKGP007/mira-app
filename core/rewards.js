/* ============================================================================
   rewards.js — the game layer, driven by real markings.

   The rule that keeps the reward honest [PRD US-018]:
     "Stars are not added for incorrect productions even if the child tries
      hard. This preserves the clinical integrity of the reward."

   And the rule that keeps it honest about the model's own limits:
     a `not_scored` item is NEUTRAL. It earns no star, costs nothing, and is
     excluded from the crown denominator. It is never counted as a success.
   ========================================================================== */

import { CONTENT_VERSION } from './exercise.js';

const LS = {
  name: 'mira_name', stars: 'mira_stars', xp: 'mira_xp',
  levels: 'mira_levels', badges: 'mira_badges', reward: 'mira_reward',
  lastDone: 'mira_lastDone', sessions: 'mira_sessions', nextWords: 'mira_nextWords',
  contentVersion: 'mira_content_version', resetVersion: 'mira_reset_version',
};

// One-time full wipe for a fresh testing pass, requested 2026-08-12. Bump
// RESET_VERSION again in the future to force another full wipe.
const RESET_VERSION = 1;
(function resetOnce() {
  if (localStorage.getItem(LS.resetVersion) !== String(RESET_VERSION)) {
    Object.values(LS).forEach(k => localStorage.removeItem(k));
    localStorage.setItem(LS.resetVersion, String(RESET_VERSION));
  }
})();

// If the word bank / level list has changed shape since this browser last
// saved data, cached word-bank-index pointers (nextWords, per-level done/
// crown state keyed by level id) can point at different content than what
// the child actually played — e.g. a "Practice Trail" built from indices
// that used to mean one /s/ word and now mean another, or no longer exist.
// Clear only that derived cache on a version mismatch. Real user data
// (name, stars, xp, sessions, badges, lastDone, reward) is never touched.
(function invalidateStaleContentCache() {
  const stored = localStorage.getItem(LS.contentVersion);
  if (stored !== String(CONTENT_VERSION)) {
    localStorage.removeItem(LS.nextWords);
    localStorage.removeItem(LS.levels);
    localStorage.setItem(LS.contentVersion, String(CONTENT_VERSION));
  }
})();

export const STAR_PER_CORRECT = 5;
export const XP_PER_ITEM = 10;
export const XP_TRAIL_BONUS = 50;
export const XP_CLEAN_BONUS = 25;
export const XP_PER_LEVEL = 200;

export const store = {
  get name() { return localStorage.getItem(LS.name) || ''; },
  set name(v) { localStorage.setItem(LS.name, v); },
  get stars() { return +(localStorage.getItem(LS.stars) || 0); },
  set stars(v) { localStorage.setItem(LS.stars, String(v)); },
  get xp() { return +(localStorage.getItem(LS.xp) || 0); },
  set xp(v) { localStorage.setItem(LS.xp, String(v)); },
  get lastDone() { return localStorage.getItem(LS.lastDone) || ''; },
  set lastDone(v) { localStorage.setItem(LS.lastDone, v); },
  get levels() { return safeJSON(LS.levels, {}); },
  set levels(v) { localStorage.setItem(LS.levels, JSON.stringify(v)); },
  get badges() { return safeJSON(LS.badges, []); },
  set badges(v) { localStorage.setItem(LS.badges, JSON.stringify(v)); },
  get sessions() { return safeJSON(LS.sessions, []); },
  set sessions(v) { localStorage.setItem(LS.sessions, JSON.stringify(v.slice(-30))); },
  get reward() { return safeJSON(LS.reward, { label: 'Trip to the park', target: 250 }); },
  set reward(v) { localStorage.setItem(LS.reward, JSON.stringify(v)); },
  // Word-bank indices Mira has picked out for the next Practice Trail, or
  // null when there's no pending one. Cleared once the child plays it.
  get nextWords() { return safeJSON(LS.nextWords, null); },
  set nextWords(v) { localStorage.setItem(LS.nextWords, JSON.stringify(v)); },
  reset() { Object.values(LS).forEach(k => localStorage.removeItem(k)); },
};
function safeJSON(k, fallback) {
  try { const v = JSON.parse(localStorage.getItem(k)); return v ?? fallback; }
  catch { return fallback; }
}

export const explorerLevel = () => 1 + Math.floor(store.xp / XP_PER_LEVEL);
export const xpInLevel = () => store.xp % XP_PER_LEVEL;

/** Star only for a `correct` target. Nothing for flagged, nothing for withheld. */
export function starsFor(verdict) {
  return verdict === 'correct' ? STAR_PER_CORRECT : 0;
}

/**
 * Crowns from the session.
 * `not_scored` items are removed from the denominator entirely — a gated
 * item can never inflate a run into looking perfect.
 */
export function crownsFor(items) {
  const done = items.filter(i => i.verdict);
  const scored = done.filter(i => i.verdict !== 'not_scored');
  if (!done.length) return 0;
  if (!scored.length) return 1;                    // showed up, nothing measurable
  const clear = scored.filter(i => i.verdict === 'correct').length;
  // Proportion, not an absolute miss count: trails are 2–6 words long, so
  // "one miss" means very different things on a 2-word and a 6-word trail.
  const ratio = clear / scored.length;
  if (ratio === 1) return 3;
  if (ratio >= 0.5) return 2;
  return 1;
}

/** XP rewards effort, so a rough session still moves forward. */
export function xpFor(items) {
  const done = items.filter(i => i.verdict).length;
  const scored = items.filter(i => i.verdict && i.verdict !== 'not_scored');
  const clean = scored.length > 0 && scored.every(i => i.verdict === 'correct');
  return done * XP_PER_ITEM + XP_TRAIL_BONUS + (clean ? XP_CLEAN_BONUS : 0);
}

export const BADGES = [
  { id: 'first_trail', name: 'First Trail', icon: 'paw',
    when: s => Object.values(s.levels).some(l => l.done) },
  { id: 'clean_trail', name: 'Clean Trail', icon: 'medal',
    when: s => Object.values(s.levels).some(l => l.crowns >= 3) },
  { id: 'trailblazer', name: 'Trailblazer', icon: 'flame',
    when: s => (s.sessions || []).length >= 3 },
  { id: 'sound_tamer', name: 'Sound Tamer', icon: 'trophy',
    when: s => s.stars >= 100 },
];

/** Collectible friends, unlocked by cumulative stars — the same currency
 * everything else already runs on, so this doesn't introduce a second
 * economy. Thresholds are spread so a clean session (~20-30 stars) makes
 * steady, visible progress toward the next one. */
export const FRIENDS = [
  { id: 'mira', name: 'Mira', icon: 'friendMira', stars: 0 },
  { id: 'rabbit', name: 'Hoppy', icon: 'friendRabbit', stars: 25 },
  { id: 'fox', name: 'Ember', icon: 'friendFox', stars: 50 },
  { id: 'panda', name: 'Bamboo', icon: 'friendPanda', stars: 80 },
  { id: 'bear', name: 'Honey', icon: 'friendBear', stars: 120 },
  { id: 'lion', name: 'Leo', icon: 'friendLion', stars: 160 },
  { id: 'owl', name: 'Hoot', icon: 'friendOwl', stars: 210 },
  { id: 'penguin', name: 'Waddles', icon: 'friendPenguin', stars: 270 },
  { id: 'frog', name: 'Ribbit', icon: 'friendFrog', stars: 340 },
  { id: 'turtle', name: 'Shelly', icon: 'friendTurtle', stars: 420 },
  { id: 'deer', name: 'Willow', icon: 'friendDeer', stars: 520 },
  { id: 'dolphin', name: 'Splash', icon: 'friendDolphin', stars: 650 },
];

export const unlockedFriends = () => FRIENDS.filter(f => store.stars >= f.stars);

/** Friends whose threshold sits strictly between a before/after star count —
 * used right after a session commits its stars, to know what to celebrate. */
export function friendsUnlockedBetween(starsBefore, starsAfter) {
  return FRIENDS.filter(f => f.stars > starsBefore && f.stars <= starsAfter);
}

export function checkBadges() {
  const have = store.badges;
  const snapshot = { levels: store.levels, sessions: store.sessions, stars: store.stars };
  const gained = [];
  for (const b of BADGES) {
    if (!have.includes(b.id) && b.when(snapshot)) { have.push(b.id); gained.push(b); }
  }
  store.badges = have;
  return gained;
}

/**
 * Commit a finished trail. Returns everything the celebration screen needs.
 * Also appends an honest session record for the adult views — including the
 * not-scored count, which must never disappear from the denominator.
 */
export function commitSession({ levelId, levelName, targetPhone, items, starsAlreadyCredited = false }) {
  const done = items.filter(i => i.verdict);
  const scored = done.filter(i => i.verdict !== 'not_scored');
  const clear = scored.filter(i => i.verdict === 'correct');
  const notScored = done.filter(i => i.verdict === 'not_scored');

  const earnedStars = clear.length * STAR_PER_CORRECT;
  const crowns = crownsFor(items);
  const earnedXp = xpFor(items);

  // The kid view credits each star the moment it flies into the jar, so the
  // animation and the total never disagree. In that case do not add twice.
  if (!starsAlreadyCredited) store.stars = store.stars + earnedStars;
  store.xp = store.xp + earnedXp;
  store.lastDone = new Date().toISOString().slice(0, 10);

  const levels = store.levels;
  const prev = levels[levelId] || {};
  levels[levelId] = { done: true, crowns: Math.max(crowns, prev.crowns || 0) };
  store.levels = levels;

  // Which scorer produced these markings — carried so the adult views can
  // state the tier and its measured limits rather than implying authority.
  const scorer = done.map(i => i.result?.scorer).find(Boolean) || null;
  // The real per-utterance provenance (model/aligner/protocol/threshold
  // version), for the clinician tab. Never fabricate this if it's missing.
  const provenance = done.map(i => i.result?.provenance).find(Boolean) || null;

  const record = {
    at: new Date().toISOString(),
    levelId, levelName, targetPhone, scorer, provenance,
    total: done.length,
    scored: scored.length,
    notScored: notScored.length,
    clear: clear.length,
    flagged: scored.length - clear.length,
    byPosition: byPosition(done),
    items: done.map(i => {
      const targets = i.result?.targets ?? [];
      return {
        word: i.word.text, position: i.word.position, verdict: i.verdict,
        struggling: i.attempts >= 3 && i.verdict !== 'correct',
        alignmentQuality: i.result?.quality?.alignmentQuality ?? null,
        // one row per /s/ instance actually measured in this word, on the
        // FINAL attempt. Kept for continuity with older records; `attempts`
        // below is the full picture and is what the reports read.
        instances: targets.map(t => ({
          position: t.position, marking: t.marking,
          confidence: t.confidence, confidenceKind: t.confidenceKind,
          substitute: t.substitute ?? null, reason: t.reason ?? null,
          durationMs: t.durationMs ?? null, gop: t.gop ?? null,
          recognized: t.recognized ?? null,
        })),
        // Every attempt at this word, oldest first — a word tried three times
        // holds three sets of markings, and they are frequently different
        // ones. Storing only the last hid the substitution the child made on
        // the way to getting it right, which is the part worth reading.
        attemptCount: i.attempts,
        attempts: i.attemptLog ?? [],
      };
    }),
  };
  store.sessions = [...store.sessions, record];

  const badges = checkBadges();
  return { earnedStars, earnedXp, crowns, badges, record };
}

/** Buckets by each /s/ instance's own position, not the word's overall tag —
 * a word like "sausage" contributes to two buckets (initial and medial). */
function byPosition(items) {
  const out = {};
  for (const i of items) {
    const targets = i.result?.targets;
    const rows = (targets && targets.length)
      ? targets.map(t => ({ position: t.position, marking: t.marking }))
      : [{ position: i.word.position, marking: i.verdict }];
    for (const r of rows) {
      const p = r.position;
      if (!p) continue;
      out[p] ||= { scored: 0, clear: 0, notScored: 0 };
      if (r.marking === 'not_scored') out[p].notScored++;
      else { out[p].scored++; if (r.marking === 'correct') out[p].clear++; }
    }
  }
  return out;
}

/** Aggregate across stored sessions, for the parent view. */
export function lifetime() {
  const s = store.sessions;
  const agg = { sessions: s.length, scored: 0, notScored: 0, clear: 0, flagged: 0, byPosition: {} };
  for (const r of s) {
    agg.scored += r.scored; agg.notScored += r.notScored;
    agg.clear += r.clear; agg.flagged += r.flagged;
    for (const [pos, v] of Object.entries(r.byPosition || {})) {
      agg.byPosition[pos] ||= { scored: 0, clear: 0, notScored: 0 };
      agg.byPosition[pos].scored += v.scored;
      agg.byPosition[pos].clear += v.clear;
      agg.byPosition[pos].notScored += v.notScored;
    }
  }
  return agg;
}
