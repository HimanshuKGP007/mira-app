# Reference: Satvik's Mira v4 (not merged)

**Status: copied for reference only. Not merged. Not wired into this app.**

Nothing in this repo imports, serves, or runs code from this folder. The live app still runs from the root (`index.html`, `core/`, `views/`, `server/`). Merging is a planned next step, after review.

| | |
|---|---|
| Source repo | [`satvik-7772/mira-v4`](https://github.com/satvik-7772/mira-v4) |
| Source branch | `main` |
| Source commit | `f262624` |
| Copied on | 29 September 2026 |
| Excluded | `.git/`, `node_modules/` |

## Why this folder exists

The two repos split the work:
- **This repo** keeps the engineering: the per-sound scoring engine (Module 1, 2A, 2B in `Docs/mira-4/`) and the engineering log (`Docs/MIRA.md`). This is the part that can pinpoint a phoneme and say whether it was said correctly.
- **This folder** holds the stronger UI. We will use it to build the user-facing app.

## What this folder has that the root app does not

| Feature | Where in this folder |
|---|---|
| Parent accounts: sign up, log in, log out (bcrypt, session cookie) | `server/auth.py` |
| Child profiles and saved progress on the server (SQLite) | `server/db.py`, `server/auth.py` |
| Consent boxes at sign-up (training-data use is opt-in, off by default) | `server/auth.py`, `landing-src/src/components/AuthOverlay.jsx` |
| Landing page (React + Vite) | `landing-src/` (source), `landing.html/.js/.css` (build output) |
| Redesigned kid game: animations, music, sound effects | `core/motion.js`, `core/music.js`, `core/sfx.js`, `core/audio.js` |
| First-run onboarding tour | `core/onboarding.js` |
| Design tokens | `design/tokens.css` |
| Fix: the "omitted" result could never fire | `server/policy.py` (`decide_marking`) |
| Session-by-session handoff notes | `HANDOFF.md` |

## What the root app has that this folder does not

- The Module 1, 2A, 2B package (`Docs/mira-4/`), with 23 tests and 317 self-checks.
- The engineering log (`Docs/MIRA.md`).
- A separate clinician view with overrides that keep both Mira's mark and the clinician's mark (`views/clinician.js`).
- Words with the target sound twice (for example "sunglasses"). 20 words over 6 levels. This folder has 16 single-instance words.

## Shared, and identical

`server/mira_core.py`, `server/scorer.py`, `server/insights.py`, `server/calibrate.py` are byte-for-byte the same in both. Both run the simple scorer (AUC 0.734, uncalibrated). Neither runs the trained 0.843 model.

## Known gaps in this folder (from its own `HANDOFF.md`)

- Real microphone capture on a real phone is not verified.
- Only the /s/ sound is built.
- No password reset, no email verification.
- `MIRA_FLAG_THRESHOLD` (0.50) is uncalibrated.

## Before merging

1. Review this folder file by file against the root app.
2. Decide which clinician view to keep.
3. Port the omission fix to `server/policy.py` in its own commit (see `CAUTION.md`).
4. Keep the word bank with multi-instance words, or port that schema here.
5. Delete this folder after the merge.
