# Caution: the scoring pipeline is fragile

This file exists because it's easy to touch something adjacent to the
pronunciation scorer — the UI, the reward layer, the insights narration — and
break the actual scoring without realizing it. Read this before making changes
anywhere near the files listed below, whether you're the original author or
someone who just cloned this from GitHub.

Ported from the upstream fork's own `CAUTION.md`
([HimanshuKGP007/mira-app](https://github.com/HimanshuKGP007/mira-app)) —
the scoring engine (`server/mira_core.py`, `server/scorer.py`,
`server/policy.py`) was merged into this repo verbatim from that fork; this
file's warnings apply just as much here.

## What "the scoring pipeline" means

The chain that turns a recording into `correct` / `substituted` / `omitted` /
`assimilated` / `not_scored`:

- `server/mira_core.py` — the GOP math, span expansion, phone equivalence
  classes. Ported **verbatim** from the original Stage 2 notebook cell.
  **Do not paraphrase or "clean up" this file.** A prior reimplementation of
  the same logic got several details wrong in ways that weren't obvious from
  reading the code — only from comparing scores against known recordings.
- `server/scorer.py` — model load, the forward pass, wiring `mira_core.py`
  into a response.
- `server/policy.py` — quality gates (SNR/duration), the withheld-phoneme
  list, the marking cascade, `MIRA_FLAG_THRESHOLD`.
- `server/app.py`'s `/score` route — the only place these are called from
  (gated by `auth.current_parent()`, added when this was merged into Mira's
  account system — the gate is new, the scoring call inside it is not).
- `core/client.js` — interprets the scorer's HTTP response on the frontend.
- `core/policy.js` — the frontend's copy of the retry/quality gates.

If a change you're making doesn't need to touch one of these six files,
**it shouldn't** — and if it turns out it does, stop and reconsider the
approach before proceeding.

## Why this keeps breaking

The confidence number is an **uncalibrated raw posterior**, not a
probability. `MIRA_FLAG_THRESHOLD` (default `0.50`) is the one number
separating "correct" from "wrong," and it was never tuned against this
project's actual demo recordings (see `server/README.md` → *Manual
calibration*). That means the model's behavior on any given recording can
look inconsistent or surprising even when nothing in the code changed —
before assuming a code change caused a scoring regression, rule that out
first.

Separately, this app has a service worker (`sw.js`) that aggressively caches
every JS module for offline use. More than once, a real fix has looked
"broken" purely because a browser tab was still running stale cached code.
**Bump `CACHE` in `sw.js`** whenever you ship a change, and verify in a
fresh/incognito window before concluding a change is actually wrong.

## Before changing anything in the scoring path

1. Read `server/README.md` in full first — it documents the pipeline, the
   two intentional departures from the notebooks (span expansion, phone
   equivalence classes), and the known weak spots (vowels, voiced stops).
2. Record a small set of real takes — some correct, some deliberately wrong
   — and run them through `server/calibrate.py` **before** your change, and
   again **after**. If the before/after separation between correct and wrong
   takes shifts in a way you didn't intend, that's a regression, not noise.
3. Never change `MIRA_FLAG_THRESHOLD`, the withheld-phoneme list, or the GOP
   math in the same change as an unrelated feature. Keep scoring changes in
   their own isolated commit so a regression is easy to find and revert.
4. If you're adding a UI feature that reads scoring data (like the parent
   view's per-attempt history, or `/insights`) — copy the data outward
   (additive fields, new arrays) rather than modifying how `verdict`,
   `byPosition`, or any existing aggregate is computed. `core/rewards.js`'s
   `attemptHistory` field is exactly this pattern: it records every attempt
   alongside the existing final-verdict fields, and changes nothing about how
   those fields themselves are computed.

## One fix that already landed here, as a worked example

`server/policy.py`'s `decide_marking()` had an unreachable `omitted` branch:
it checked `duration_ms < 40.0` for a value that, given the scorer's 20 ms
frame size, can only ever be an exact multiple of 20 — so no real span could
land in the intended `[30, 40)` window, and a 20 ms span was already caught by
the "too short to measure" gate one line above. `omitted` could never fire.
The fix (reorder the check ahead of that gate, make the boundary `<= 40.0`)
was verified with `python3 -c "import policy; print(policy.decide_marking(...))"`
against several duration/confidence pairs **before** touching the live
server, the same discipline point 2 above describes.
