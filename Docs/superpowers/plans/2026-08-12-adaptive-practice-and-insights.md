# Adaptive Practice & Mira Insights Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand Mira's `/s/` word bank to ~20 words (including multi-instance words), fix the bug that drops all but the first `/s/` in a word, add improvement-aware retry logic, give Groq a second job (guarded next-word selection) alongside its existing narration, and add the parent/child UI pieces agreed in the design spec.

**Architecture:** No backend model or scoring changes — `server/scorer.py` already measures every phone instance correctly. All fixes are in the client's consumption of that data (`core/policy.js`, `core/rewards.js`, `views/kid.js`, `views/clinician.js`) plus additive changes to `server/insights.py` (structured prompt, guarded word selection) and new UI in `views/parent.js` / `views/icons.js`.

**Tech Stack:** Vanilla JS (no build step, ES modules), FastAPI/Python backend, Groq `llama-3.1-8b-instant`. No test framework exists in this repo (confirmed: no pytest/jest config) — verification follows the project's existing pattern of `curl` against the running server and manual/browser checks (matches `calibrate.py`'s approach), not a new test framework.

## Global Constraints

- No word "Groq" anywhere in frontend-visible strings (`views/*.js`, `index.html`).
- No word "suggest"/"suggestion" in any parent-facing copy; use descriptive framing ("practice has leaned toward...") never prescriptive framing.
- `/s/` only — no other target phones in this pass.
- Groq's word selection must validate against the actual word bank server-side; any invalid/malformed response falls back to the existing deterministic `worstPos` rule in `core/policy.js`'s `feedbackForSession`.
- Retry cap is hard: 3 attempts per word, always, no exceptions.
- Backend changes require a server restart to take effect (no `--reload`); frontend changes are live on refresh.
- Spec source of truth: `Docs/superpowers/specs/2026-08-12-adaptive-practice-and-insights-design.md`.

---

### Task 1: Word bank expansion

**Files:**
- Modify: `core/exercise.js` (WORDS, LEVELS)
- Modify: `views/icons.js` (ICONS — add new word icons)

**Interfaces:**
- Produces: `WORDS` array of `{ text, position, icon, phones }` — `position` is now descriptive metadata only (Task 2 stops using it for scoring aggregation). A word may legitimately contain `/s/` twice; `position` reflects where the *first* instance falls, for level-curation purposes only.
- Produces: `LEVELS` array of `{ id, name, words: [index,...] }`, unchanged shape.

- [ ] **Step 1: Add 12 new icons to `views/icons.js`**

Insert after the existing `glass:` entry (before `/* --- theme --- */`), keeping the same 100x100 viewBox and flat-palette style as the existing word icons:

```js
  soap: `<svg viewBox="0 0 100 100"><rect x="18" y="34" width="64" height="34" rx="17" fill="#8FE3D3"/>
    <rect x="18" y="34" width="64" height="34" rx="17" fill="none" stroke="#4FBFA8" stroke-width="2.5"/>
    <ellipse cx="38" cy="46" rx="10" ry="5" fill="#fff" opacity=".5"/></svg>`,

  spoon: `<svg viewBox="0 0 100 100"><ellipse cx="50" cy="32" rx="18" ry="22" fill="#CFD5E6"/>
    <ellipse cx="46" cy="26" rx="7" ry="10" fill="#fff" opacity=".5"/>
    <rect x="46" y="50" width="8" height="42" rx="4" fill="#CFD5E6"/></svg>`,

  house: `<svg viewBox="0 0 100 100"><path d="M50 16 L88 46 H12 Z" fill="#F0616A"/>
    <rect x="22" y="46" width="56" height="40" fill="#FFE8B8"/>
    <rect x="42" y="62" width="16" height="24" fill="#7A6CF0"/>
    <rect x="30" y="54" width="12" height="12" fill="#CFE9FF"/><rect x="58" y="54" width="12" height="12" fill="#CFE9FF"/></svg>`,

  mouse: `<svg viewBox="0 0 100 100"><circle cx="34" cy="30" r="12" fill="#B9C0D4"/><circle cx="66" cy="30" r="12" fill="#B9C0D4"/>
    <ellipse cx="50" cy="56" rx="30" ry="24" fill="#D5D9E8"/>
    <path d="M78 60 Q94 66 90 80" stroke="#D5D9E8" stroke-width="5" fill="none" stroke-linecap="round"/>
    <circle cx="40" cy="52" r="3" fill="#3C4666"/><ellipse cx="52" cy="60" rx="4" ry="3" fill="#FF9EC0"/></svg>`,

  castle: `<svg viewBox="0 0 100 100">
    <rect x="14" y="50" width="20" height="34" fill="#B9C0D4"/>
    <rect x="66" y="50" width="20" height="34" fill="#B9C0D4"/>
    <rect x="34" y="60" width="32" height="24" fill="#CFD5E6"/>
    <rect x="14" y="44" width="6" height="8" fill="#B9C0D4"/><rect x="28" y="44" width="6" height="8" fill="#B9C0D4"/>
    <rect x="66" y="44" width="6" height="8" fill="#B9C0D4"/><rect x="80" y="44" width="6" height="8" fill="#B9C0D4"/>
    <rect x="42" y="68" width="16" height="16" fill="#7A6CF0"/>
    <path d="M50 24 v18" stroke="#8A93AD" stroke-width="3"/><path d="M50 24 l12 5 l-12 5 Z" fill="#F0616A"/></svg>`,

  basket: `<svg viewBox="0 0 100 100"><path d="M24 46 h52 l-6 34 a6 6 0 0 1 -6 5 h-28 a6 6 0 0 1 -6 -5 Z" fill="#E0A81E"/>
    <path d="M28 54 h44 M25 64 h50 M27 74 h46" stroke="#B5820F" stroke-width="2.5"/>
    <path d="M36 46 a14 18 0 0 1 28 0" fill="none" stroke="#8A5A12" stroke-width="4"/></svg>`,

  whistle: `<svg viewBox="0 0 100 100"><ellipse cx="46" cy="50" rx="26" ry="18" fill="#F5A93B"/>
    <circle cx="30" cy="50" r="6" fill="#3C4666"/>
    <rect x="70" y="42" width="14" height="16" rx="7" fill="#F5A93B"/>
    <circle cx="20" cy="34" r="7" fill="none" stroke="#8A93AD" stroke-width="3"/></svg>`,

  dinosaur: `<svg viewBox="0 0 100 100"><path d="M20 78 C16 60 24 46 40 44 C40 34 48 24 58 26 C56 32 56 36 60 40
    C74 40 82 50 80 62 C88 62 92 68 90 74 L80 74 C80 80 74 84 68 82 L66 78 L34 78 C32 84 22 84 20 78 Z" fill="#5BAF4E"/>
    <circle cx="52" cy="36" r="3" fill="#3C4666"/>
    <path d="M46 30 l6 -8 M56 28 l4 -9 M64 32 l4 -8" stroke="#3E8C42" stroke-width="4" stroke-linecap="round"/>
    <rect x="30" y="78" width="6" height="10" fill="#3E8C42"/><rect x="64" y="78" width="6" height="10" fill="#3E8C42"/></svg>`,

  seven: `<svg viewBox="0 0 100 100"><path d="M22 22 H78 L44 84" fill="none" stroke="#7A6CF0" stroke-width="14"
    stroke-linecap="round" stroke-linejoin="round"/></svg>`,

  sunglasses: `<svg viewBox="0 0 100 100"><rect x="14" y="38" width="30" height="24" rx="10" fill="#3C4666"/>
    <rect x="56" y="38" width="30" height="24" rx="10" fill="#3C4666"/>
    <path d="M44 46 h12" stroke="#3C4666" stroke-width="5"/>
    <path d="M14 46 L4 42 M86 46 L96 42" stroke="#3C4666" stroke-width="4" stroke-linecap="round"/>
    <ellipse cx="24" cy="46" rx="7" ry="5" fill="#8FE3D3" opacity=".7"/><ellipse cx="66" cy="46" rx="7" ry="5" fill="#8FE3D3" opacity=".7"/></svg>`,

  sausage: `<svg viewBox="0 0 100 100"><g fill="#D2434C">
    <ellipse cx="28" cy="50" rx="16" ry="13"/><ellipse cx="52" cy="50" rx="16" ry="13"/><ellipse cx="76" cy="50" rx="14" ry="12"/></g>
    <line x1="40" y1="40" x2="40" y2="60" stroke="#8B2530" stroke-width="3"/>
    <line x1="64" y1="40" x2="64" y2="60" stroke="#8B2530" stroke-width="3"/>
    <ellipse cx="24" cy="44" rx="5" ry="3" fill="#fff" opacity=".3"/></svg>`,

  biscuits: `<svg viewBox="0 0 100 100"><rect x="16" y="40" width="40" height="40" rx="8" fill="#E0A81E" transform="rotate(-8 36 60)"/>
    <rect x="44" y="36" width="40" height="40" rx="8" fill="#F5A93B" transform="rotate(6 64 56)"/>
    <circle cx="58" cy="48" r="2.4" fill="#B5820F"/><circle cx="70" cy="56" r="2.4" fill="#B5820F"/>
    <circle cx="60" cy="64" r="2.4" fill="#B5820F"/><circle cx="72" cy="68" r="2.4" fill="#B5820F"/></svg>`,
```

`socks` and `horse` deliberately reuse existing art: `socks` gets `icon: 'sock'` in the word bank (Step 2), and `horse` gets no `icon` key at all — `views/kid.js:186`'s `ICONS[it.word.icon] || ICONS.star` already falls back to the star icon gracefully, which is an existing, intentional degrade path, not a bug.

- [ ] **Step 2: Replace `WORDS` in `core/exercise.js`**

```js
export const WORDS = [
  { text: 'sun',        position: 'initial', icon: 'sun',
    phones: ['s', 'ʌ', 'n'] },
  { text: 'sock',       position: 'initial', icon: 'sock',
    phones: ['s', 'ɒ', 'k'] },
  { text: 'soap',       position: 'initial', icon: 'soap',
    phones: ['s', 'oʊ', 'p'] },
  { text: 'seven',      position: 'initial', icon: 'seven',
    phones: ['s', 'ɛ', 'v', 'ə', 'n'] },
  { text: 'spoon',      position: 'initial', icon: 'spoon',
    phones: ['s', 'p', 'u', 'n'] },
  { text: 'pencil',     position: 'medial',  icon: 'pencil',
    phones: ['p', 'ɛ', 'n', 's', 'ɪ', 'ɫ'] },   // ɛ->e and ɫ are withheld
  { text: 'bicycle',    position: 'medial',  icon: 'bicycle',
    phones: ['b', 'aɪ', 's', 'ɪ', 'k', 'ɫ'] },  // ɫ withheld
  { text: 'castle',     position: 'medial',  icon: 'castle',
    phones: ['k', 'æ', 's', 'ɫ'] },             // ɫ withheld
  { text: 'basket',     position: 'medial',  icon: 'basket',
    phones: ['b', 'æ', 's', 'k', 'ə', 't'] },
  { text: 'whistle',    position: 'medial',  icon: 'whistle',
    phones: ['w', 'ɪ', 's', 'ɫ'] },             // ɫ withheld
  { text: 'dinosaur',   position: 'medial',  icon: 'dinosaur',
    phones: ['d', 'aɪ', 'n', 'ə', 's', 'ɔ', 'r'] },
  { text: 'bus',        position: 'final',   icon: 'bus',
    phones: ['b', 'ʌ', 's'] },
  { text: 'glass',      position: 'final',   icon: 'glass',
    phones: ['g', 'ɫ', 'æ', 's'] },             // ɫ withheld
  { text: 'house',      position: 'final',   icon: 'house',
    phones: ['h', 'aʊ', 's'] },
  { text: 'mouse',      position: 'final',   icon: 'mouse',
    phones: ['m', 'aʊ', 's'] },
  { text: 'horse',      position: 'final',   icon: null,
    phones: ['h', 'ɔ', 'r', 's'] },
  // multi-instance: /s/ appears twice, at different positions in the same word
  { text: 'sunglasses', position: 'initial', icon: 'sunglasses',
    phones: ['s', 'ʌ', 'n', 'g', 'l', 'æ', 's', 'ɪ', 'z'] },   // s: initial + medial
  { text: 'sausage',    position: 'initial', icon: 'sausage',
    phones: ['s', 'ɔ', 's', 'ɪ', 'dʒ'] },                      // s: initial + medial
  { text: 'biscuits',   position: 'medial',  icon: 'biscuits',
    phones: ['b', 'ɪ', 's', 'k', 'ɪ', 't', 's'] },              // s: medial + final
  { text: 'socks',      position: 'initial', icon: 'sock',
    phones: ['s', 'ɒ', 'k', 's'] },                             // s: initial + final
];
```

- [ ] **Step 3: Rebuild `LEVELS` in `core/exercise.js` around the larger bank**

Keep the existing progression shape (single-position levels first, then mixed), just reference the new indices (0-19 in array order above):

```js
export const LEVELS = [
  { id: 1, name: 'Whispering Woods', words: [0, 1, 2] },     // initial: sun, sock, soap
  { id: 2, name: 'Pebble Creek',     words: [5, 6, 8] },     // medial: pencil, bicycle, basket
  { id: 3, name: "Snake's Hollow",   words: [11, 12, 13] },  // final: bus, glass, house
  { id: 4, name: 'Fern Gully',       words: [3, 7, 9] },     // initial+medial mix: seven, castle, whistle
  { id: 5, name: 'Mossy Ridge',      words: [4, 10, 14] },   // initial+medial+final mix: spoon, dinosaur, mouse
  { id: 6, name: 'Sunlit Summit',    words: [16, 17, 18, 19] }, // multi-instance: sunglasses, sausage, biscuits, socks
  { id: 7, name: 'Highland Trail',   words: [0, 5, 11, 15] }, // review mix, includes horse
];
```

- [ ] **Step 4: Verify the word bank loads without syntax errors**

Run: `node --check core/exercise.js && node --check views/icons.js`
Expected: no output (both files parse cleanly as valid JS — `node --check` only parses, it doesn't execute, so ES module imports elsewhere don't matter here).

- [ ] **Step 5: Commit**

```bash
git add core/exercise.js views/icons.js
git commit -m "$(cat <<'EOF'
Expand /s/ word bank to 20 words, including multi-instance words

Adds 14 words across all three positions plus four words where /s/
appears twice at different positions (sunglasses, sausage, biscuits,
socks), giving the adaptive-practice work in later tasks real words to
select between instead of the previous 2-per-position bank.
EOF
)"
```

---

### Task 2: Fix the first-instance-only bug (multi-`/s/` tracking)

**Files:**
- Modify: `core/policy.js:236-249` (`normalizeResponse`)
- Modify: `core/rewards.js` (`byPosition`, `commitSession`)
- Modify: `views/kid.js` (`handleOutcome`)
- Modify: `views/clinician.js` (`itemBlock`)

**Interfaces:**
- Consumes: server `/score` response shape (`phones[]` with `position`, `marking`, `confidence` per phone — already correct, from Task 1's spec investigation).
- Produces: `result.targets` (array, replaces singular `result.target`) — every phone in `result.phones` where `isTarget` is true, in phone order.
- Produces: `session record.items[i].instances` (array of `{ position, verdict, confidence }`, one per `/s/` occurrence in that word) alongside the existing single `verdict` (still present, computed as "correct only if every instance is correct" — see Step 3).

- [ ] **Step 1: Change `core/policy.js`'s `normalizeResponse` to keep every target instance**

Current (`core/policy.js:234-249`):
```js
  return {
    utteranceId: raw?.utterance_id ?? raw?.utteranceId ?? null,
    promptWord: raw?.prompt_word ?? promptWord ?? null,
    targetPhone: targetPhone ?? null,
    phones,
    target: phones.find(p => p.isTarget) ?? null,
    quality: {
```

Replace with:
```js
  return {
    utteranceId: raw?.utterance_id ?? raw?.utteranceId ?? null,
    promptWord: raw?.prompt_word ?? promptWord ?? null,
    targetPhone: targetPhone ?? null,
    phones,
    // every /s/-family instance in the word, in phone order — a word like
    // "sausage" has two. Never collapse to one: that silently drops data
    // the scorer already measured.
    targets: phones.filter(p => p.isTarget),
    quality: {
```

- [ ] **Step 2: Update every caller of the old singular `result.target`**

Run: `grep -rn "\.target\b" views/*.js core/*.js` and fix each hit found (as of this plan, the callers are `views/kid.js:339,340,353` and `views/parent.js` does not use `.target` directly). For `views/kid.js`, this is handled in Step 4 below as part of the outcome-handling rewrite — don't patch it separately here, to avoid two conflicting edits landing on the same lines.

- [ ] **Step 3: Make `core/rewards.js`'s position aggregation read per-instance positions**

Find the `byPosition` function (`core/rewards.js:159-168` in the current file) and `commitSession`'s `items:` mapping (`core/rewards.js:145-151`). Replace the item-shape stored in a session record so it carries per-instance data:

```js
    items: done.map(i => ({
      word: i.word.text, position: i.word.position, verdict: i.verdict,
      substitute: i.result?.target?.substitute ?? null,
      confidence: i.result?.target?.confidence ?? null,
      confidenceKind: i.result?.target?.confidenceKind ?? null,
      reason: i.result?.target?.reason ?? null,
    })),
```
becomes:
```js
    items: done.map(i => {
      const targets = i.result?.targets ?? [];
      return {
        word: i.word.text, position: i.word.position, verdict: i.verdict,
        struggling: i.attempts >= 3 && i.verdict !== 'correct',
        // one row per /s/ instance actually measured in this word
        instances: targets.map(t => ({
          position: t.position, marking: t.marking,
          confidence: t.confidence, confidenceKind: t.confidenceKind,
          substitute: t.substitute ?? null, reason: t.reason ?? null,
        })),
      };
    }),
```

Then update `byPosition` to bucket by each instance's own position instead of the word-level tag:
```js
function byPosition(items) {
  const out = {};
  for (const item of items) {
    const rows = item.instances && item.instances.length ? item.instances
      : [{ position: item.position, marking: item.verdict }];  // pre-migration records without `instances`
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
```
(Adjust the exact field names to match what's already in the surrounding `byPosition`/aggregation code in `core/rewards.js` — read the file first; the shape above must match the `{scored, clear, notScored}` contract `views/parent.js`'s `positionCard` already consumes.)

- [ ] **Step 4: Rewrite `views/kid.js`'s outcome decision to use every target instance**

Current (`views/kid.js:337-353`):
```js
  // scored
  const result = res.result;
  const target = result.target;
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

  const verdict = target ? target.marking : 'not_scored';
```

Replace with:
```js
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
```

The rest of `handleOutcome` (the `if (verdict === 'correct')` / `not_scored` / flagged branches) is unchanged — it already switches on the `verdict` local variable, which is now computed correctly from all instances instead of just the first.

- [ ] **Step 5: Show one row per instance in the clinician tab**

In `views/clinician.js`'s `itemBlock` (currently renders one `<tr>` per word using `it.confidence`/`it.substitute` directly), branch on whether the stored item has multiple instances:

```js
function itemBlock(it, key) {
  const c = corrections.get(key);
  const rows = (it.instances && it.instances.length ? it.instances : [it]).map((inst, idx) => {
    const shown = idx === 0 && c ? c.clinician_said : (inst.marking || inst.verdict);
    return `
    <tr>
      <td style="width:34px"><span class="tgt">s</span><span class="p" style="font-size:10px;display:block">${inst.position || ''}</span></td>
      <td>
        <span class="pill ${shown}">${label(shown)}</span>
        ${inst.substitute && shown === 'substituted' ? `<span class="sub"> &rarr; ${inst.substitute}</span>` : ''}
        ${inst.reason && shown === 'not_scored' ? `<div class="why">${inst.reason}</div>` : ''}
      </td>
      <td style="width:52px;text-align:right">
        <span class="conf">${inst.confidence != null ? inst.confidence.toFixed(2) : '-'}</span>
      </td>
    </tr>`;
  }).join('');
  return `
  <div class="wordblock" data-key="${key}">
    <div class="wh"><span class="w">${it.word}</span><span class="p">${it.position}</span></div>
    <table class="sheet"><tbody>${rows}</tbody></table>
    ${c ? `<div class="audit">clinician override &middot; Mira said <s>${label(c.mira_said)}</s>,
           you marked <b>${label(c.clinician_said)}</b></div>` : ''}
    <div class="override">
      ${MARKINGS.map(m => `<button data-m="${m}" class="${m === it.verdict ? 'on' : ''}">${label(m)}</button>`).join('')}
    </div>
  </div>`;
}
```

This keeps the existing override mechanism working against the word's overall `verdict` (unchanged behavior) while making every individually-scored `/s/` visible.

- [ ] **Step 6: Manual verification (no test framework in this repo — verify via the running app)**

Run: `cd server && ./run.sh` (restart if already running — backend didn't change in this task, but do this to also pick up Task 1's data changes on the client, which need only a browser refresh, not a server restart).

In the browser: play through a level containing "sausage" or "socks" (Level 6, "Sunlit Summit," added in Task 1). Say the word once clearly and once with a deliberately wrong second `/s/` if possible. Open the clinician tab and confirm **two** rows appear for that word, each with its own position label and confidence — this is the concrete, observable proof the bug is fixed.

- [ ] **Step 7: Commit**

```bash
git add core/policy.js core/rewards.js views/kid.js views/clinician.js
git commit -m "$(cat <<'EOF'
Fix silent loss of all but the first /s/ instance in a word

core/policy.js's normalizeResponse() picked exactly one target phone via
Array.find(), discarding every other /s/ in words like "sausage" or
"socks" even though the scorer already measured each one. Now every
matching instance survives through to the star decision, the position
graph, and the clinician sheet.
EOF
)"
```

---

### Task 3: Improvement-aware retry logic and struggle tagging

**Files:**
- Modify: `views/kid.js` (`handleOutcome`, item shape in `core/exercise.js`'s `newSession`)
- Modify: `core/exercise.js` (`newSession` — add `confidenceHistory` to each item)

**Interfaces:**
- Consumes: `it.attempts` (existing), `targets` (from Task 2).
- Produces: `it.confidenceHistory` (array of numbers, one push per attempt) used to decide whether to offer a third attempt.

- [ ] **Step 1: Track confidence per attempt in `core/exercise.js`'s `newSession`**

Current item shape (`core/exercise.js:57-63`):
```js
    items: wordsForLevel(level).map(w => ({
      word: w,
      verdict: null,     // 'correct' | 'substituted' | 'omitted' | 'assimilated' | 'not_scored'
      result: null,      // the normalised contract object
      attempts: 0,
      demo: false,
    })),
```
Add one field:
```js
    items: wordsForLevel(level).map(w => ({
      word: w,
      verdict: null,     // 'correct' | 'substituted' | 'omitted' | 'assimilated' | 'not_scored'
      result: null,      // the normalised contract object
      attempts: 0,
      confidenceHistory: [],   // lowest target-instance confidence per attempt, oldest first
      demo: false,
    })),
```

- [ ] **Step 2: Record each attempt's worst-instance confidence and cap retries at 3 with an improvement check**

In `views/kid.js`'s `handleOutcome`, right after computing `verdict` (from Task 2, Step 4), record this attempt's confidence before the branch that decides retry vs. move-on:

```js
  const attemptConfidences = targets.map(t => t.confidence).filter(c => c != null);
  const worstThisAttempt = attemptConfidences.length ? Math.min(...attemptConfidences) : null;
  it.confidenceHistory.push(worstThisAttempt);
```

Then replace the existing flagged-retry block (`views/kid.js:377-389`):
```js
  // flagged — one retry, then move on. Never negative, never a star.
  if (it.attempts < 2) {
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
```
with:
```js
  // Flagged: retry only while attempts remain AND (this is the very first
  // retry, or the child is measurably improving). Hard cap at 3 attempts,
  // no exceptions — Mira is never allowed to get stuck on one word.
  const [prev, cur] = it.confidenceHistory.slice(-2);
  const improving = prev != null && cur != null && cur > prev;
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
```

The final fallthrough block right after (`it.verdict = verdict; paint('flagged'); ...`) already handles "stop and move on" — no change needed there, it now triggers correctly whether the child hit the 3-attempt cap or simply wasn't improving.

- [ ] **Step 3: Manual verification**

In the browser, deliberately mispronounce a word twice in a row (same rough mistake both times, so confidence doesn't meaningfully improve) and confirm Mira moves on after the 2nd attempt (not offering a 3rd). Then try a word where the 2nd attempt is clearly better than the 1st (e.g., mumble then say clearly) and confirm a 3rd attempt is offered, and that after the 3rd attempt — regardless of outcome — it always moves on (no 4th attempt, ever).

- [ ] **Step 4: Commit**

```bash
git add core/exercise.js views/kid.js
git commit -m "$(cat <<'EOF'
Add improvement-aware retry logic with a hard 3-attempt cap

A flagged word now gets a second attempt unconditionally, and a third
only if the second attempt's confidence improved over the first.
Otherwise Mira moves on immediately rather than repeating a word the
child is not making progress on — never blocks the child.
EOF
)"
```

---

### Task 4: Groq's dual role — structured narration + guarded exercise selection

**Files:**
- Modify: `server/insights.py` (`narrate`, new `select_next_words`)
- Modify: `server/app.py` (`/insights` route — pass word bank, return selection)

**Interfaces:**
- Consumes: `core/exercise.js`'s word bank shape, sent from the client as `word_bank: [{index, text, position}, ...]` in the `/insights` POST body.
- Produces: `/insights` response gains two fields: `next_words` (array of valid word-bank indices, guardrailed) and `why` (one sentence, descriptive not prescriptive). `text` (existing narration) keeps its current key but is now generated with a fixed 3-sentence structure.

- [ ] **Step 1: Restructure the narration prompt for a fixed, parseable shape**

In `server/insights.py`, replace the existing `prompt` construction inside `narrate()`:

```python
    prompt = (
        "Write 2-3 short, warm sentences for a parent summarizing their "
        "child's speech sound practice. Use ONLY the numbers given below - "
        "never invent a number, never suggest what to practice next, never "
        "use clinical language (no diagnosis, severity, disorder, condition, "
        "treatment, therapy, or recommendations to see a specialist). Just "
        "describe the numbers factually and encouragingly. Output ONLY the "
        "sentences themselves - no preamble, no \"Here are...\", no heading, "
        "no meta-commentary about the task.\n\n"
        "Child's name: %s\nData: %s"
        % (child_name or "the child", analysis)
    )
```
with:
```python
    prompt = (
        "Write exactly 3 short sentences for a parent, in this fixed order, "
        "each on its own line with no numbering or labels:\n"
        "1. Practice count - how many sessions and words attempted, using "
        "only the numbers given.\n"
        "2. The pattern - name the specific word position (start / middle / "
        "end of words) where practice has been hardest, using only the "
        "numbers given. Phrase it as a plain observation, never as advice: "
        "say 'practice has leaned toward...' or 'X has been trickiest at "
        "the ...', never 'should', 'recommend', or 'suggest'.\n"
        "3. One sentence connecting today's word choices to that pattern - "
        "why practice today includes more of that kind of word.\n\n"
        "Use ONLY the numbers given below - never invent a number, never "
        "use clinical language (no diagnosis, severity, disorder, condition, "
        "treatment, therapy, or recommendations to see a specialist). Output "
        "ONLY the 3 sentences themselves - no preamble, no \"Here are...\", "
        "no heading, no meta-commentary about the task.\n\n"
        "Child's name: %s\nData: %s"
        % (child_name or "the child", analysis)
    )
```

- [ ] **Step 2: Add a guarded exercise-selection function**

Add a new function below `narrate()` in `server/insights.py`:

```python
def select_next_words(analysis, word_bank):
    """Ask Groq which word-bank indices the next level should weight toward,
    validated against the real bank. Any failure, timeout, or invalid index
    falls back to the deterministic worst-position rule below - Groq can
    never hand back a word that isn't in the bank, and never touches an
    in-progress session, only the *next* one."""
    fallback = _fallback_selection(analysis, word_bank)

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return fallback, "rule"

    valid_indices = {w["index"] for w in word_bank}
    prompt = (
        "A child is practicing the /s/ sound. Here is their practice data: "
        "%s\n\nHere is the full list of available practice words, each with "
        "an index and the word position of its /s/ sound: %s\n\n"
        "Reply with ONLY a JSON array of 4-6 word indices (integers from the "
        "list above) that would give the most useful next practice session, "
        "weighted toward whichever position has been hardest. Reply with "
        "ONLY the JSON array, nothing else - no explanation, no markdown."
        % (analysis, word_bank)
    )

    try:
        resp = requests.post(
            GROQ_URL,
            headers={"Authorization": "Bearer %s" % api_key},
            json={
                "model": GROQ_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "max_tokens": 100,
            },
            timeout=GROQ_TIMEOUT_S,
        )
        resp.raise_for_status()
        raw = resp.json()["choices"][0]["message"]["content"].strip()
        indices = json.loads(raw)
    except Exception:                                  # noqa: BLE001
        return fallback, "rule"

    if not isinstance(indices, list) or not indices:
        return fallback, "rule"
    clean = [i for i in indices if isinstance(i, int) and i in valid_indices]
    if not clean:
        return fallback, "rule"
    return clean[:6], "llm"


def _fallback_selection(analysis, word_bank):
    """Deterministic: weight toward the worst-scoring position, same signal
    core/policy.js's feedbackForSession already surfaces on the frontend."""
    position_pct = analysis.get("position_pct") or {}
    if not position_pct:
        return [w["index"] for w in word_bank[:4]]
    worst = min(position_pct, key=lambda p: position_pct[p] if position_pct[p] is not None else 100)
    matches = [w["index"] for w in word_bank if w.get("position") == worst]
    return (matches or [w["index"] for w in word_bank])[:6]
```

Add `import json` to the top of `server/insights.py` alongside the existing `import os`.

- [ ] **Step 3: Wire the new fields into `/insights`**

In `server/app.py`, update the `/insights` handler:

```python
@app.post("/insights")
async def get_insights(payload: dict = Body(...)):
    """Turns session history the app already has into a parent-facing note,
    plus a guarded pick of which words the next level should weight toward.

    Body: {"child_name": str|None, "target_phone": str, "sessions": [...],
    "word_bank": [{"index": int, "text": str, "position": str}, ...]}
    where `sessions` is store.sessions from core/rewards.js, oldest first,
    and `word_bank` mirrors core/exercise.js's WORDS. Never scores anything
    itself; ordinary arithmetic plus an optional, verified LLM sentence and
    an optional, guardrailed word selection on top. Falls back to a
    template/rule if Groq is unavailable, so this endpoint always returns
    something.
    """
    sessions = payload.get("sessions") or []
    target_phone = payload.get("target_phone") or "s"
    child_name = payload.get("child_name")
    word_bank = payload.get("word_bank") or []

    analysis = insights.compute_analysis(sessions, target_phone)
    text, source = insights.narrate(analysis, child_name)
    next_words, selection_source = insights.select_next_words(analysis, word_bank) if word_bank else ([], "rule")
    return {
        "text": text, "source": source,
        "next_words": next_words, "selection_source": selection_source,
        "analysis": analysis,
    }
```

- [ ] **Step 4: Verify with curl against the running server**

Run: restart the server (`cd server && ./run.sh`, killing any process already on port 8000 first), then:
```bash
curl -s -X POST http://localhost:8000/insights -H "Content-Type: application/json" -d '{
  "child_name": "Priya", "target_phone": "s",
  "sessions": [{"at":"2026-08-12T09:00:00Z","levelId":1,"levelName":"Whispering Woods","targetPhone":"s","total":3,"scored":3,"notScored":0,"clear":1,"flagged":2,"byPosition":{"initial":{"scored":3,"clear":1,"notScored":0}},"items":[]}],
  "word_bank": [{"index":0,"text":"sun","position":"initial"},{"index":11,"text":"bus","position":"final"},{"index":13,"text":"house","position":"final"}]
}' | python3 -m json.tool
```
Expected: HTTP 200, a JSON body with `text` (3 sentences, no preamble), `next_words` (a list drawn only from indices 0/11/13 — since the sample's only position data is "initial" at 33%, `next_words` should reasonably include index 0), and `selection_source` of `"llm"` or `"rule"`.

- [ ] **Step 5: Commit**

```bash
git add server/insights.py server/app.py
git commit -m "$(cat <<'EOF'
Give Groq a second job: guarded next-word selection alongside narration

Groq's narration prompt is now a fixed 3-sentence structure (practice
count, pattern by position, why today's words were chosen) so output
shape is consistent. A new select_next_words() lets Groq pick which
bank words the next level should weight toward, validated against the
real word bank server-side - any invalid response, or no key, falls
back to the existing deterministic worst-position rule.
EOF
)"
```

---

### Task 5: Wire word selection into the next level + parent transparency section

**Files:**
- Modify: `views/parent.js` (`loadInsights`, new transparency section, word-bank payload)
- Modify: `core/exercise.js` (support for an ad-hoc "next practice" level built from selected indices)
- Modify: `views/kid.js` (use the ad-hoc level when one is pending)

**Interfaces:**
- Consumes: `/insights` response's `next_words` (from Task 4).
- Produces: `store` gains a `nextWords` field (array of word-bank indices, or `null`); `core/exercise.js` exports `levelFromWords(indices)` building a level-shaped object from arbitrary indices.

- [ ] **Step 1: Add `levelFromWords` to `core/exercise.js`**

```js
/** Build a level-shaped object from arbitrary word-bank indices (used for
 * the practice set Mira assembles after enough sessions to detect a
 * pattern). Falls back to nothing usable if the indices are empty/invalid -
 * callers must check the returned words.length before using it. */
export function levelFromWords(indices) {
  const valid = (indices || []).filter(i => Number.isInteger(i) && i >= 0 && i < WORDS.length);
  return {
    id: 'practice',
    name: 'Practice Trail',
    words: valid,
  };
}
```

- [ ] **Step 2: Send the word bank and store the response in `views/parent.js`**

Replace `loadInsights` (`views/parent.js:67-89`):
```js
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
      }),
    });
    if (!res.ok) throw new Error('bad status');
    const data = await res.json();
    el.textContent = data.text;
  } catch {
    // The tickers above already show the real numbers; losing the note is
    // a cosmetic failure, never a blocking one.
    const body = $('#insightsCard');
    if (body) body.remove();
  }
}
```
with:
```js
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
        word_bank: WORDS.map((w, i) => ({ index: i, text: w.text, position: w.position })),
      }),
    });
    if (!res.ok) throw new Error('bad status');
    const data = await res.json();
    el.textContent = data.text;
    if (Array.isArray(data.next_words) && data.next_words.length) {
      store.nextWords = data.next_words;
    }
  } catch {
    // The tickers above already show the real numbers; losing the note is
    // a cosmetic failure, never a blocking one.
    const body = $('#insightsCard');
    if (body) body.remove();
  }
}
```
Add `import { WORDS } from '../core/exercise.js';` to `views/parent.js`'s existing imports (alongside the existing `LEVELS` import).

`store.nextWords` needs a getter/setter in `core/rewards.js`'s `store` object, following the same `localStorage`-backed pattern already used for `store.reward`/`store.levels` — read that section of `core/rewards.js` first and add `nextWords` the same way (default `null`, JSON-serialized).

- [ ] **Step 3: Offer the practice trail on the map screen**

In `views/kid.js`'s `renderMap()`, after building the normal level nodes, check for a pending practice set and surface it as an extra, clearly-labeled node/button rather than silently replacing the curriculum:

```js
  if (store.nextWords && store.nextWords.length) {
    html += `<button class="node practice" id="practiceNode"
      style="left:50%;top:8%">${icon('bulb', 22)}<div class="name">Practice Trail</div></button>`;
  }
```
Bind it in `renderMap()`'s existing node-binding block (where `.node` click handlers are attached):
```js
  const practiceBtn = $('#practiceNode');
  if (practiceBtn) {
    practiceBtn.addEventListener('click', () => {
      startLevel(levelFromWords(store.nextWords));
      store.nextWords = null;   // consumed - Mira will offer a new one after the next pattern update
    });
  }
```
Add `levelFromWords` to `views/kid.js`'s existing import from `../core/exercise.js`.

- [ ] **Step 4: Add the parent-facing transparency section**

In `views/parent.js`, add a new small card function after `insightsCardShell` and wire it into `render()`'s body assembly (after the insights card, before `positionCard`):

```js
function whyExercisesCard() {
  return `
  <div class="card" id="whyCard" style="display:none">
    <h3>${icon('target')}Why today's practice looks this way</h3>
    <div class="note" id="whyBody"></div>
  </div>`;
}
```
In `loadInsights`, after setting `el.textContent = data.text;`, also populate this card if the response included one (extend Task 4's response to carry a `why` field derived from the narration's third sentence — split `data.text` on newlines and use the last non-empty line, since the prompt in Task 4 Step 1 guarantees sentence 3 is the "why" sentence on its own line):
```js
    const lines = data.text.split('\n').map(s => s.trim()).filter(Boolean);
    if (lines.length >= 3) {
      const whyCard = $('#whyCard');
      const whyBody = $('#whyBody');
      if (whyCard && whyBody) { whyBody.textContent = lines[2]; whyCard.style.display = ''; }
    }
```
Add `${whyExercisesCard()}` to the template literal in `render()` (`views/parent.js:45-51`), between `${insightsCardShell()}` and `${positionCard(agg)}`.

- [ ] **Step 5: Manual verification**

Run: `cd server && ./run.sh` (restart, since Task 4 touched the backend). In the browser, complete at least 2 sessions with some flagged words, open the parent tab, and confirm: the "Why today's practice looks this way" card appears with a non-empty sentence containing no "suggest"/"Groq"/"recommend" wording; back on the map screen, a "Practice Trail" node appears; tapping it starts a session using only words that were in the original 20-word bank.

- [ ] **Step 6: Commit**

```bash
git add core/exercise.js views/kid.js views/parent.js core/rewards.js
git commit -m "$(cat <<'EOF'
Surface Groq's word selection as an optional Practice Trail

Adds a parent-facing "why today's practice looks this way" card (never
the word "suggest") and a map-screen Practice Trail node built from
Groq's guarded next_words selection - entirely additive, the normal
curriculum is untouched, and the trail always draws from the real word
bank only.
EOF
)"
```

---

### Task 6: Graphical Sound Map (replaces the plain position bars)

**Files:**
- Modify: `views/parent.js` (`positionCard`)
- Modify: `views/icons.js` (three small zone icons)

**Interfaces:**
- Consumes: `agg.byPosition` (existing shape from `core/rewards.js`'s `lifetime()`, unchanged by this task).

- [ ] **Step 1: Add three small illustrated zone icons to `views/icons.js`**

Insert alongside the other word/theme icons:

```js
  zoneStart: `<svg viewBox="0 0 100 100"><ellipse cx="50" cy="70" rx="38" ry="16" fill="#D9EFC9"/>
    <path d="M50 62 C40 62 34 52 34 42 C34 30 42 22 50 22 C58 22 66 30 66 42 C66 52 60 62 50 62 Z" fill="#7FCB6E"/>
    <circle cx="42" cy="40" r="3" fill="#3E8C42"/><circle cx="58" cy="40" r="3" fill="#3E8C42"/></svg>`,
  zoneMiddle: `<svg viewBox="0 0 100 100"><ellipse cx="50" cy="70" rx="38" ry="16" fill="#D9EFC9"/>
    <path d="M50 62 C36 62 28 50 28 38 C28 24 38 16 50 16 C62 16 72 24 72 38 C72 50 64 62 50 62 Z" fill="#5BAF4E"/>
    <circle cx="40" cy="36" r="3.2" fill="#fff"/><circle cx="60" cy="36" r="3.2" fill="#fff"/></svg>`,
  zoneEnd: `<svg viewBox="0 0 100 100"><ellipse cx="50" cy="70" rx="38" ry="16" fill="#D9EFC9"/>
    <path d="M50 62 C34 62 24 48 24 34 C24 18 36 8 50 8 C64 8 76 18 76 34 C76 48 66 62 50 62 Z" fill="#3E8C42"/>
    <circle cx="38" cy="32" r="3.4" fill="#FFC93C"/><circle cx="62" cy="32" r="3.4" fill="#FFC93C"/>
    <path d="M40 46 Q50 54 60 46" stroke="#FFC93C" stroke-width="3" fill="none" stroke-linecap="round"/></svg>`,
```
(Three "plant" stages — sprout/bush/tree — reusing the app's existing forest visual language from the map screen, growing taller and gaining detail as a stand-in for "clearer." Deliberately not a face or body diagram, per the design spec.)

- [ ] **Step 2: Replace `positionCard`'s bar rows with the illustrated version**

Current (`views/parent.js`, the `positionCard` function) renders plain `<div class="track">` bars. Keep the same data computation (percentages, labels) but change the row markup to lead with the zone icon:

```js
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
            <span class="ex">${v.clear} clear &middot; ${v.scored - v.clear} flagged${v.notScored ? ` &middot; ${v.notScored} not scored` : ''}</span></div>
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
```

- [ ] **Step 3: Manual verification**

In the browser, open the parent tab after at least one session and confirm the "Across word positions" card shows a small illustration next to each position row, and the existing bar/percentage data is unchanged (this is a visual addition, not a data change).

- [ ] **Step 4: Commit**

```bash
git add views/icons.js views/parent.js
git commit -m "$(cat <<'EOF'
Illustrate the position breakdown as a small Sound Map

Adds three growth-stage icons (sprout/bush/tree, matching the map
screen's existing forest visual language) alongside each position row
in the parent tab, in place of a plain bar. Same underlying data,
more character - deliberately not a face or body diagram.
EOF
)"
```

---

### Task 7: Kid-facing fun fact

**Files:**
- Modify: `views/kid.js` (`finish()` — done screen)

**Interfaces:**
- Produces: a small, static, rotating fact list — no dependency on Groq or session data (kept simple, offline, and never about the specific child, per the design spec).

- [ ] **Step 1: Add a small fact list and render it on the level-complete screen**

In `views/kid.js`, add near the other constant arrays (alongside `PRAISE`):

```js
const FUN_FACTS = [
  "Lots of kids practice their sounds every single day, just like you!",
  "Snakes don't have ears, but they can feel sound through the ground!",
  "Your mouth makes hundreds of different sounds without you even thinking about it.",
  "The more you practice a sound, the easier it gets, like riding a bike!",
  "Some words have the same sound hiding in them more than once, like 'sausage'!",
];
const funFact = () => FUN_FACTS[Math.floor(Math.random() * FUN_FACTS.length)];
```

In `finish()`, after the existing `$('#badgePops').innerHTML = ...` block, add:
```js
  const factEl = $('#doneFact');
  if (factEl) factEl.textContent = funFact();
```

- [ ] **Step 2: Add the element to the done screen in `index.html`**

In the `#s-done` section, after `<div id="badgePops"></div>`:
```html
      <div id="doneFact" class="note" style="margin-top:8px;text-align:center;font-family:var(--font-kid);
        font-size:13px;color:var(--ink-soft)"></div>
```

- [ ] **Step 3: Manual verification**

In the browser, complete any level and confirm the done screen shows a fact sentence below the badges/trophies, and that it changes on repeated completions (random selection).

- [ ] **Step 4: Commit**

```bash
git add views/kid.js index.html
git commit -m "$(cat <<'EOF'
Add a kid-facing fun fact to the level-complete screen

A small rotating fact, shown only to the child on the done screen -
never a number about their own practice, kept separate from anything
parent-facing.
EOF
)"
```

---

### Task 8: Nav cleanup — flat icons, back button, wording audit

**Files:**
- Modify: `app.css` (`.icon-btn` → flat variant)
- Modify: `index.html` (topbar buttons)
- Modify: `views/icons.js` (add a simple `back` glyph if not covered by an existing icon)

**Interfaces:** none beyond DOM/CSS — purely presentational.

- [ ] **Step 1: Add a flat icon-button style alongside the existing circular one**

In `app.css`, near `.icon-btn` (around line 72), add:
```css
.icon-flat{width:38px;height:38px;border:none;background:none;cursor:pointer;color:var(--ink);
  display:grid;place-items:center;flex:0 0 auto;opacity:.85}
.icon-flat:active{opacity:1;transform:scale(.92)}
```
Leave `.icon-btn` itself untouched (it's still used by `#muteBtn`, unaffected by this task).

- [ ] **Step 2: Switch the settings button to the flat style and add a back button in the topbar**

In `index.html`, replace:
```html
    <div class="topbar">
      <button class="icon-btn" id="muteBtn" title="Sound on / off">🔊</button>
      <button class="icon-btn" id="settingsBtn" title="Settings"></button>
    </div>
```
with:
```html
    <div class="topbar">
      <button class="icon-flat" id="settingsBtn" title="Settings"></button>
    </div>
```
(Removing the mute button entirely, per the earlier UI discussion — its function-less circular badge was one of the two things called out; muting is a minor feature not otherwise requested to be preserved elsewhere in this plan, so it is dropped rather than relocated, keeping the topbar to the one flat settings glyph.)

In the same file's `<script>` block, remove the now-dead mute wiring (`$('#muteBtn').addEventListener(...)`, around the `/* ---------- mute ---------- */` comment) since the button no longer exists.

- [ ] **Step 3: Add a consistent flat back button wherever a screen needs one**

The app already has back buttons on every adult/settings screen (`#adultBack`, `#setBack`, `#pinBack`, `#exBack`, `#mapAdults`) using `.btn-ghost` or `.icon-btn`. Standardize them on the new flat style: in `index.html`, change each of `#adultBack`, `#setBack`, and `#exBack` from their current classes to `class="icon-flat"` with a left-arrow icon instead of text, using the existing pattern already present for `#exBack`:
```html
<button class="icon-flat" id="exBack" title="Back">${/* left-arrow glyph, see below */}</button>
```
Since these buttons render static HTML (not built from `icon()` calls), add a reusable inline SVG directly in each button matching the existing minimal glyph style:
```html
<svg viewBox="0 0 24 24" width="22" height="22"><path d="M15 5 L8 12 L15 19" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg>
```
Apply this same inner SVG to `#adultBack` and `#setBack`, replacing their current `← Back` text content, and keep `#pinBack`/`#mapAdults`/`#doneMap` as they are (`.quiet` text links — these are intentionally textual "For grown-ups"/"Back to map" exits, a different, already-consistent pattern from the icon-based in-screen back button).

- [ ] **Step 4: Audit for "Groq" and "suggest"/"suggestion" in frontend-visible strings**

Run:
```bash
grep -rniE "groq" index.html views/*.js core/*.js
grep -rniE "suggest" index.html views/*.js core/*.js
```
Expected: no matches (or, if `writing-plans` review at Task 4/5 introduced any in code comments only, confirm none are inside a rendered string/template literal that reaches the DOM — comments are fine, rendered copy is not). Fix any real hits found before proceeding.

- [ ] **Step 5: Manual verification**

Restart nothing (frontend-only) — refresh the browser and confirm: no speaker icon in the top-right, the settings gear has no circular background, back buttons on the exercise/adult/settings screens are small flat arrows, and navigation between all screens still works.

- [ ] **Step 6: Commit**

```bash
git add app.css index.html
git commit -m "$(cat <<'EOF'
Flatten nav icons, drop the mute button, add consistent back arrows

Settings gear and screen-level back buttons move from circular
neumorphic badges to small flat SVG glyphs; the speaker/mute button is
removed as unused chrome. No theme toggle is added (confirmed not
wanted).
EOF
)"
```

---

### Task 9: Final restart, visual pass, and handoff

**Files:** none (verification only).

- [ ] **Step 1: Restart the backend** (Tasks 4 picked up server-side changes)

```bash
PID=$(lsof -nP -iTCP:8000 -sTCP:LISTEN | grep Python | awk '{print $2}' | sort -u)
[ -n "$PID" ] && kill "$PID"
cd server && ./run.sh &
```
Wait for `curl -s http://localhost:8000/health` to return 200 before continuing.

- [ ] **Step 2: Screenshot-based visual check of the new/changed screens**

Using the Playwright browser tools (already available in this environment): navigate to `http://localhost:8000`, click through to the exercise screen to see the new word icons render (Task 1), the parent tab for the Sound Map (Task 6) and the "why" card (Task 5), and the done screen for the fun fact (Task 7). Take a screenshot at each stop. Fix anything that renders visibly broken (a malformed SVG shows as nothing or a broken-image glyph — if any new icon from Task 1/6 doesn't render, re-check its `<svg>` markup for unclosed tags before moving on).

- [ ] **Step 3: Report the URL**

Per standing instruction, do not open or reload the browser automatically — state that the server is up at `http://localhost:8000` and let the user open it themselves.

---

## Notes for whoever executes this plan

- No task in this plan changes `server/scorer.py`, `server/mira_core.py`, or the model itself — confirm this stays true; if any task's implementation seems to require a scorer change, stop and re-check Task 2's premise (the per-instance data already exists in `phones[]`).
- `core/rewards.js`'s exact current field names in `byPosition`/`commitSession` should be re-read at Task 2 Step 3 time, since this plan was written from a snapshot of that file — match the plan's intent (per-instance position bucketing) to whatever the live field names are, not the other way around.
- Every backend-touching task (4) requires a server restart to verify; every frontend-only task (1, 2 client side, 3, 5 client side, 6, 7, 8) is visible on a plain browser refresh.
