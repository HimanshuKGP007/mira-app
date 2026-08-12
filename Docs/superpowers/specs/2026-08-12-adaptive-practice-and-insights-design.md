# Adaptive Practice & Mira Insights — Design

Status: approved by user 2026-08-12. Scope: `/s/` only. No backend/model changes.

## Problem

1. The word bank (6 words, 3 positions) is too small for position-targeted practice to mean anything — the "next level" would just repeat the same 2 words per position.
2. When a word contains `/s/` more than once (e.g. "sunglasses"), only the *first* instance's result is used anywhere downstream (`core/policy.js:239`, `phones.find(p => p.isTarget)`). The scorer already measures every instance (`server/scorer.py:320-370`) — this is a client-side data-loss bug, not a scoring limitation.
3. Mira's parent-facing insight card only narrates raw counts; it doesn't explain *why* practice patterns exist or shape what's practiced next.
4. The retry flow (`views/kid.js`) always allows exactly one retry regardless of whether the child is improving, and there's no record of words a child genuinely cannot produce.
5. Minor UI cleanup: no theme toggle, flat (non-circular) settings icon, a back button in the same style, no visible reference to "Groq" anywhere in the frontend, no parent-facing sentence should say "suggest"/"suggestion" (matches the existing forbidden-word spirit in `insights.py`).

## Decisions

### 1. Word bank expansion
`core/exercise.js`'s `WORDS` grows from 6 to ~20 words, still `/s/`-only, still tagged `initial`/`medial`/`final`. Include several multi-instance words (e.g. "sunglasses," "biscuits," "sausages") specifically to exercise decision #2. Existing `LEVELS` curriculum stays; new levels are added/reshaped to use the larger bank. A word's stored `position` tag becomes descriptive/curriculum metadata only — see #2 for why it's no longer the scoring source of truth.

### 2. Multi-instance-per-word tracking (bug fix, not new capability)
- `core/policy.js`'s `normalizeResponse()`: replace `target: phones.find(p => p.isTarget)` with `targets: phones.filter(p => p.isTarget)` (plural, keeps every matching instance). Keep a computed `target` alias (`targets[0] ?? null`) only if something still needs a single value during transition; audit callers before removing it entirely.
- `views/kid.js`'s outcome handling: a word counts as `correct` for the star/flag decision only when **every** instance in `targets` is `correct`. If any instance is flagged, the word is flagged (existing retry flow applies to the word as a whole, not per-instance).
- `core/rewards.js`'s `byPosition()` aggregation: stop reading the word-level `position` tag; iterate every scored instance in `targets` and use *that instance's own* `position` (already returned per-phone by the server) to bucket it. A two-`/s/` word can now contribute to two different position buckets in one item.
- `views/clinician.js`'s item rendering: show one row per `/s/` instance when a word has more than one, each with its own marking/confidence, rather than collapsing to a single row.

### 3. Retry logic (`views/kid.js`)
Replace the flat "one retry" rule:
- Attempt 1 flagged → offer attempt 2.
- If attempt 2's confidence improved over attempt 1 (compare the word-level worst/lowest instance confidence, since a word can have multiple targets after #2) → offer attempt 3.
- Hard cap at 3 attempts, always. If still not correct after the allowed attempts, stop — mark the word `flagged`, tag it in the session record as a "repeated-struggle" word (a boolean or small counter, not a new marking type — `MARKINGS` stays as-is), and move on. Never blocks the child, never re-prompts beyond the cap.
- This tag feeds the parent/clinician view (a word can be flagged as "this one came up as hard to produce across attempts") without adding clinical language.

### 4. Module 2 (Groq) — dual role, same guardrails
`server/insights.py`'s `narrate()` keeps its existing safety model (numbers-only input, forbidden-word screen, template fallback, never touches audio or Module 1 internals — see the "bridge" explanation already given to the user) but gets two outputs instead of one:

**a. Structured, fixed-shape narration** (for the **"What Mira has found"** card — already named, no "Groq" anywhere in copy). Prompt is restructured so output always follows the same shape, for consistency:
1. One sentence: practice count / attendance (sessions, words attempted).
2. One sentence: the detected pattern, naming the specific position, phrased descriptively ("practice has leaned toward the end of words this week") — never "I suggest," never "recommend," never "should."
3. One sentence: what today's practice includes and *why*, in plain language ("today's words lean toward endings, since that's where practice has been trickiest") — this is the reasoning the user asked for, framed as description of what's already happening, not a prescription.

**b. Exercise selection** — a second, separate Groq call (or extend the same call to return structured JSON with both the narration and a word-index list) that picks which words from the bank the next level should weight toward. Guardrail: response is validated server-side against the actual word bank; any word not in the bank, or a malformed response, discards the selection and falls back to the existing deterministic rule (heaviest-weighted position from `feedbackForSession`'s `worstPos` logic, already in `core/policy.js`). Groq's selection is only ever applied to the *next* level's word list — it never touches an in-progress session.

Both stay behind the existing "no key → template fallback" and "any failure → fails closed" behavior — nothing about this is allowed to block or corrupt the exercise flow.

### 5. Parent-facing transparency (not "suggestions")
Add a section — after "What Mira has found," before "Adventure so far" — that shows *why* the next set of exercises looks the way it does, using the same descriptive (never prescriptive) framing as 4a's third sentence. No use of "suggest"/"suggestion" anywhere in this copy.

### 6. Graphical position profile (parent tab, end of page)
Replace/extend the existing plain progress-bar `positionCard` with an illustrated "Sound Map" — three friendly zones (matching the app's existing forest/nature visual language: leaf greens, the same iconography style as `views/icons.js`) for initial/medial/final, each visually "growing" or "clearer" based on real clear/flagged/not-scored counts for that position. Explicitly not a face or body diagram (the user was unsure themselves and it risks reading as clinical/medical) — stays in the app's existing playful-but-honest visual language. Same underlying data as today's `positionCard`, illustrated rather than a bar chart.

### 7. Kid-facing fun fact (map or done screen, not the parent tab)
A small, occasional card/bubble with a light, non-clinical fact ("lots of kids practice their sounds every day!" style) — adds warmth, never numbers about *this* child, never anything resembling the withheld clinical language. Shown on the map screen or level-complete screen, separate from any parent-facing content.

### 8. Small UI items
- No theme toggle (confirmed not needed).
- Settings button becomes a flat SVG icon, no circular badge.
- New back button, same flat-icon treatment, added wherever navigation needs it for consistency.
- Audit all frontend strings once more for "Groq" (should be zero) and "suggest"/"suggestion" in parent-facing copy (should be zero).

## Out of scope for this pass
- Expanding beyond `/s/` (e.g. `/ʃ/`) — explicitly deferred.
- Multi-profile/login switching — separate project, not started.
- Full top-bar/navigation redesign beyond items in #8 — separate project, not started.
- Live-audio verification of scoring accuracy — user to test directly in the running app; not something this session can do (no live mic access here).

## Model
Groq model stays `llama-3.1-8b-instant` (confirmed acceptable by user; already in use in `server/insights.py`).
