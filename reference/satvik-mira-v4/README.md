# Mira

A speech-sound practice game for kids, scored live by a real on-device
pronunciation model — with an honest grown-up view that shows what was
measured *and* what wasn't. Landing page → real parent accounts → a child
profile → a gamified forest trail where saying a word out loud gets scored
phone-by-phone in real time.

## Quick start

```bash
cd server && ./run.sh
```

Opens on **http://localhost:8000/**. First run creates a Python virtualenv
(~2 GB of wheels) and downloads the acoustic model (~1.26 GB) into
`~/.cache/huggingface`; after that, startup is ~10–15 s.

Flow: landing page → sign up (email/password + consent checkboxes) → add a
child → redirected to `/app/`. `server/mira.db` (sqlite) and `server/.secret`
(session signing key) are gitignored and created on first run — delete
`mira.db` to reset all accounts.

No build step for the `/app/` PWA — plain ES modules, no bundler. The landing
page (`landing.html`/`.js`/`.css`) *is* a build output (Vite + React); see
[Rebuilding the landing page](#rebuilding-the-landing-page) if you need to
change it.

**Optional:** copy `server/.env.example` to `server/.env` and set
`GROQ_API_KEY` to get LLM-written parent notes from `/insights` instead of
the built-in template — nothing breaks either way.

## What this is architecturally

Two things were merged into one app, kept deliberately separate:

- **Frontend** — entirely this project's own: the gamified `/app/` PWA
  (vanilla JS, no framework) and the marketing/auth landing page (React,
  built with Vite). Neither came from anywhere else.
- **Backend scoring engine** — `server/mira_core.py`, `server/scorer.py`,
  `server/policy.py`, `server/insights.py`, `server/calibrate.py` are merged
  in **verbatim** from a teammate's fork,
  [HimanshuKGP007/mira-app](https://github.com/HimanshuKGP007/mira-app). One
  confirmed bug fix landed on top (see [`server/README.md`](server/README.md)
  → *What changed in this merge*) — no other behavior was altered.
- **Accounts** — `server/auth.py` + `server/db.py` are this project's own
  addition. The upstream fork has no accounts at all (single-user, no
  login); real parent accounts, child profiles, and session-gated
  `/score`/`/insights` are what let the two halves work together.

Read **[`server/README.md`](server/README.md)** before touching anything in
`server/` — it documents the scoring pipeline, its known weak spots, and the
manual calibration procedure. Read **[`CAUTION.md`](CAUTION.md)** before
changing anything *near* the scoring pipeline (the reward layer, the
insights narration) — it's easier than it looks to break scoring without
touching a scoring file directly.

## Directory map

```
index.html / app.css              the gamified kid+parent app (served at /app/)
landing.html / landing.css / landing.js    BUILD OUTPUT — see landing-src/
landing-src/                       the React+Vite+Tailwind source for the landing page
sw.js / manifest.webmanifest       PWA, scope /app/
design/tokens.css                  shared design tokens (colors/type/radii) — both
                                    app.css and landing-src's Tailwind theme read this

core/
  client.js     POST /score wrapper — the ONLY path to a score, no offline/demo mode
  policy.js     frontend mirror of server marking/withholding rules (server is authoritative)
  capture.js    mic -> 16kHz mono PCM16 WAV, with silence-trimming
  rewards.js    localStorage game state (stars/xp/levels/badges/sessions) + server sync
  auth.js       thin client for /auth/*, /children, /progress/*, /sessions/*
  music.js      procedural Web Audio soundtrack (map screen only)
  sfx.js        procedural sound effects, shares core/audio.js's AudioContext
  voice.js      single-speaker TTS (Web Speech default, optional ElevenLabs key)
  motion.js     WAAPI motion primitives (spring/stagger/float/drift/parallax/...)
  onboarding.js first-run spotlight walkthrough (localStorage-only, no server sync)
  exercise.js   the one exercise: /s/ "snake sound", 16 words, 7 levels

views/
  kid.js        map, mascot, exercise loop, celebration, sticker stash
  parent.js     honest progress view — denominators, sound-by-sound detail
                (per-attempt trail, overrides), stated limits. Folds in what
                used to be a separate clinician screen.
  icons.js      all SVG art, layered for independent per-part animation

server/
  app.py         FastAPI: routing, auth gating, no-cache middleware, static mounts
  auth.py        signup/login/logout/me, bcrypt, session cookie, child CRUD
  db.py          sqlite schema (parents/children/progress/practice_sessions)
  policy.py      scorer constants: gates, withheld phonemes, marking cascade  [merged]
  scorer.py      the /score pipeline: decode -> align -> GOP -> markings      [merged]
  mira_core.py   GOP math, span expansion, phone equivalence classes          [merged]
  insights.py    /insights: session-history arithmetic + optional Groq note   [merged]
  calibrate.py   CLI to check MIRA_FLAG_THRESHOLD against real recordings     [merged]
  README.md      scorer-specific docs — read this before changing server/
```

## What's real vs scripted

Nothing is scripted. Every score comes from a live forward pass through a
real acoustic model (`facebook/wav2vec2-lv-60-espeak-cv-ft`, CTC forced
alignment, goodness-of-pronunciation scoring). See
[`server/README.md`](server/README.md) for exactly what it measures, what it
doesn't, and the honest AUC/PCC numbers behind it — **0.734 / 0.176**, the
`post_max alone` rung of a larger ablation, not a trained ensemble.

## Rebuilding the landing page

`landing.html`/`.js`/`.css` at the project root are a **build output**, not
hand-written — the source lives in `landing-src/`.

```bash
cd landing-src
npm install        # first time only
npm run dev         # live dev server at :5173, proxies API calls to :8000
npm run build        # writes landing-src/dist/{landing.html,js,css}
```

The build deliberately outputs exactly those three unhashed filenames (no
`/assets` subfolder, no chunk splitting) because `server/app.py`'s static
file whitelist only serves those three names at the root — after `npm run
build`, copy them into place:

```bash
cp landing-src/dist/landing.html landing-src/dist/landing.js landing-src/dist/landing.css .
```

No backend changes are needed for this — it's a pure static-file swap.

## Known gaps (read before assuming something works)

- **Real microphone capture has never been verified end-to-end on a real
  device in this session** — testing here has used a browser pane that
  blocks `getUserMedia`, and audio was injected via pre-recorded WAV fixtures
  instead. Test on an actual phone/laptop before trusting it.
- **Multi-instance words** (a target phone appearing twice in one word, e.g.
  "sunglasses") are in the upstream fork's word bank but were **not**
  ported — it needs a schema change through `core/client.js`,
  `core/rewards.js`, the exercise loop, and the parent view all at once, and
  that was deliberately deferred rather than rushed.
- **Telemetry (AAARRR analytics) and OAuth (Google/Apple sign-in)** are not
  implemented. Both need real backend routes/tables; ask for them explicitly
  when you're ready to scope that work.
- `MIRA_FLAG_THRESHOLD` (0.50) is **uncalibrated** — see
  [`server/README.md`](server/README.md) → *Manual calibration* before
  trusting individual flags in a demo.

## Full history

[`HANDOFF.md`](HANDOFF.md) has the detailed session-by-session history,
bugs found and fixed, and the honesty-contract rules that govern this
codebase (never show a raw score, `not_scored` always stays in the
denominator, clinician/parent overrides never erase Mira's original
marking, ...).
# mira-v4
# mira-v4
