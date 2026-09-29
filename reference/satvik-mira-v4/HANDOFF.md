# Mira — Handoff

Speech-sound practice PWA for children (from `mira_prd_v1.docx`). Landing page →
real accounts → gamified map → word scored live by an on-device pronunciation
model. Git-initialized; see root [`README.md`](README.md) for the quick-start
and the current frontend/backend split — **this file is the detailed session
history**, read it for *why* things are the way they are, not *how to run it*.

## Run it

See root [`README.md`](README.md). Short version:

```bash
cd /Users/satviksingh/MIRA/server && ./run.sh
```

## Directory map

See root [`README.md`](README.md)'s directory map — kept there now so there's
one copy, not two that drift. The short version: `index.html`/`app.css`/
`core/`/`views/` are the gamified `/app/` PWA (vanilla JS); `landing.html`/
`.js`/`.css` are a **build output** of `landing-src/` (React+Vite); `server/`
is FastAPI, split between this project's own accounts layer (`auth.py`,
`db.py`) and a scoring engine merged in from a teammate's fork (`mira_core.py`,
`scorer.py`, `policy.py`, `insights.py`, `calibrate.py` — see
[`server/README.md`](server/README.md)).

Note: `views/clinician.js` **no longer exists** — its scored-sheet content
(per-item override table, provenance, stated limits) was folded into
`views/parent.js` as a single merged parent view. There is no separate
clinician screen anymore.

## What's real vs scripted

Nothing is scripted. Every score comes from a live forward pass through a real
acoustic model — currently `facebook/wav2vec2-lv-60-espeak-cv-ft` (CTC, 20ms
frames, eSpeak IPA vocabulary), merged in from the upstream fork. The earlier
`charsiu/en_w2v2_fc_10ms` dual-backend setup (frame-classification, 10ms,
ARPAbet) that a prior session added was **removed** in the backend-merge
session below, in favor of taking "the backend of the repo" as-is per the
user's explicit request — `server/charsiu_model.py` and the
`MIRA_SCORER_BACKEND` switch are both gone. If you want charsiu_fc back, it's
in git history (before the backend-merge commit), but note it never had a
measured accuracy figure at all, while the current backend's 0.734/0.176
AUC/PCC are real, measured numbers (Stage 2 test split, 15,559 phones).

## The one exercise

`/s/` ("snake sound"), 16 words across 7 levels/nodes on the forest map (grew
from an original 6 words/6 levels — see the "merge teammate fork" work
below). Word list + level layout: `core/exercise.js`. The upstream fork's
word bank additionally has 4 *multi-instance* words (the target phone
appearing twice, e.g. "sunglasses") — deliberately **not** ported; see
"Not started" below.

## Scorer honesty contract (do not weaken these)

- Never display the raw model score anywhere (frontend or API docs) — it's
  compressed/uninformative on its own. Only `marking` + `confidence` (labeled
  `raw_posterior`, explicitly **uncalibrated**).
- `not_scored` phones stay in every denominator shown to parents/clinicians —
  never silently dropped.
- Clinician overrides never overwrite the model's original marking — both
  values are kept (`{mira_said, clinician_said}`).
- `policy.py`'s `WITHHELD_PHONEMES` (currently `e, t̪, u, ɫ`, MAE>0.25 or n<50
  in the Stage-2 error table) get `not_scored` unconditionally, regardless of
  what the model outputs.

## Known numbers (current, `server/policy.py`)

| | value |
|---|---|
| Model | `facebook/wav2vec2-lv-60-espeak-cv-ft` (CTC, 20ms frames, eSpeak IPA) |
| `FLAG_THRESHOLD` | 0.50 — **uncalibrated**, run `server/calibrate.py` on real recordings before trusting it |
| Corroboration gate | on by default (`MIRA_COMBINE_GOP=1`) — softens `post_max`-only flags that neither `post_mean` nor `gop_renorm` corroborate. Can only reduce false positives, never add one |
| Expected AUC/PCC | **0.734 / 0.176** — real, measured (Stage-2 test split, 15,559 phones). This is the `post_max alone` ablation rung, not the trained ensemble (0.843/0.376, needs artifacts not in this repo — see `server/README.md`) |
| Alignment | `mira_core.ctc_forced_align` + `expand_spans` |

Licensing: `facebook/wav2vec2-lv-60-espeak-cv-ft` is confirmed apache-2.0.

## Accounts (prototype-grade, said explicitly in `server/auth.py`)

bcrypt cost-12, Starlette `SessionMiddleware`, httpOnly + samesite=lax cookie,
30-day expiry. No email verification, no password reset, no CSRF token beyond
SameSite, brute-force counter is in-memory (resets on restart). Gated routes:
`/app/*`, `/score`, `/children`, `/progress/*`, `/sessions/*`. Consent
checkboxes at signup: service-data required, training-data **opt-in, off by
default**.

Env vars: `MIRA_SECRET_KEY` (else auto-generated into `server/.secret`),
`MIRA_COOKIE_SECURE=1` (set this behind TLS), `MIRA_DB_PATH`.

## Bugs found + fixed, early accounts/scoring session

1. **Route-ordering 404.** A generic `@app.get("/{name}")` catch-all was
   registered *before* the explicit `/app` routes in `app.py`. Starlette
   matches routes in registration order — specific paths must be registered
   before wildcards, always. Fixed by reordering; the comment in `app.py`
   flags this explicitly.
2. **Silent stale-JS bug.** Starlette's `StaticFiles`/`FileResponse` set no
   `Cache-Control` by default, so a plain browser `fetch()`/`import()` could
   serve an old cached module with **zero revalidation** — no error, no log,
   just old code silently running. Cost significant debugging time (symptoms
   looked like the fix "wasn't landing"). Fixed with a blanket
   `Cache-Control: no-cache` middleware in `app.py` (also correct here since
   API responses are session-specific and shouldn't be cached anyway). If you
   ever see "I fixed it but it's still broken" on this codebase, hard-reload
   / clear site data first.
3. **`music.start`/`.stop`/`.duck` were separate named exports**, not methods
   on the exported `music` object — but `index.html` called them as
   `music.start(...)`. Crashed the whole map render with `music.duck is not a
   function`. Fixed via `Object.assign(music, {start, stop, duck})` at the
   bottom of `core/music.js`.
4. **Mascot dialogue was invisible.** `sayPool()` (map dialogue) was writing
   into `#exBubble`, which lives on the *exercise* screen — invisible while
   on the map. Added a dedicated `#mapBubble` element; `views/kid.js` now has
   a separate `mapBubble()` renderer distinct from the exercise's `bubble()`.

## Verified, early accounts/scoring session

- Full auth flow via curl: signup sets httpOnly+samesite cookie, wrong
  password → 401, `/score` without session → 401 / with session → 200, child
  isolation (other parent's child → 404), password stored as bcrypt hash.
- Full scoring pipeline with real audio (macOS `say` + ffmpeg → 16kHz wav),
  both backends, matched-word and deliberate-mismatch cases (mismatch
  correctly produces `substituted`/`not_scored`, not a false `correct`).
- Browser: landing → signup → child picker → `/app/` → map renders with
  mascot dialogue bubble visible → real authenticated `/score` call through
  `core/client.js` end-to-end (audio injected as base64 fixture, see below).
- Server internals (`server/.venv`, `server/mira.db`) confirmed NOT
  web-reachable — only `core/` and `views/` are mounted under `/app/`.

## Not verified (be skeptical, test these first)

- **Real microphone capture through the actual UI, still.** Every session so
  far — including the backend-merge session below — has used a Browser-pane
  tool that blocks `getUserMedia`. `core/capture.js`'s WAV encoding was
  verified in isolation and the *submission* path was verified by injecting
  a pre-recorded WAV (repeatedly, across sessions), but nobody has spoken
  into this app on a real device and watched it score in real time. This is
  the single most important thing to test before trusting this app works.
- **PWA install prompt.** `beforeinstallprompt` is browser-heuristic-gated;
  never fired in testing. The iOS fallback instructions are unverified on a
  real device.

## v3 redesign + backend-merge session

Two large, separate pieces of work landed in one session:

**1. Frontend redesign.** New design language (X-Method-blend palette/type,
no-straight-lines geometry, floating dock, poppy gradient backgrounds),
React+Vite landing page rebuild (zero backend changes — the build outputs
directly into the three static filenames `server/app.py` already whitelists),
an animal cast + sticker stash, and a first-run spotlight onboarding tour
(`core/onboarding.js`, localStorage-only). The clinician screen was removed
and folded into a single parent view.

**2. Backend merge.** `server/mira_core.py`, `scorer.py`, `policy.py`,
`insights.py`, `calibrate.py` were replaced **verbatim** with a teammate's
fork ([HimanshuKGP007/mira-app](https://github.com/HimanshuKGP007/mira-app)),
per explicit user instruction to use "the backend of the repo" while keeping
this project's own UI and accounts layer. This is a real behavior change from
the prior charsiu_fc-default setup — see "What's real vs scripted" above.
`server/auth.py` and `server/db.py` (accounts) were **not** touched; the
fork has no accounts of its own, so `/insights` was wired in gated behind the
same `auth.current_parent()` check `/score` already uses.

**Confirmed bug found and fixed during this merge** (see `CAUTION.md` and
`server/README.md` → *What changed in this merge* for the full writeup):
`decide_marking()`'s `omitted` branch was unreachable dead code. It checked
`duration_ms < 40.0` after a `duration_ms < MIN_DURATION_MS (30)` gate had
already run — but `duration_ms` is always an exact multiple of the 20ms frame
size, so no value could ever land in `[30, 40)`, and a 20ms span was already
caught by the earlier gate regardless. Fixed by reordering the checks and
changing the boundary to `<= 40.0`; verified with a standalone
`python3 -c "import policy; ..."` unit test against several duration/
confidence pairs before touching the live server (before: every case in the
intended omission range fell through to `not_scored` or `substituted`; after:
short + low-confidence spans correctly return `omitted`, everything else is
unchanged).

**Also added:** `core/rewards.js` items now carry an `attemptHistory` array —
every attempt on a word, oldest first, not just the final one that used to
silently overwrite `it.result`. A flagged first try followed by a corrected
retry used to vanish entirely from the parent view; now the "sound-by-sound
detail" accordion shows the full retry trail (only rendered when there was
more than one attempt). This is purely additive — `verdict`, `byPosition`,
and every other existing aggregate compute exactly as before; see
`CAUTION.md` point 4 for why that mattered.

**Deliberately not ported:** the fork's multi-instance word schema (a target
phone appearing twice in one word) and its `levelFromWords()` adaptive
practice feature — both need a schema change threading through
`core/client.js`, `core/rewards.js`, the exercise loop, and the parent view
simultaneously, and that was judged too risky to rush. Telemetry and OAuth
were also out of scope for this session (explicit "frontend only, no
backend" instruction was in effect before the backend-merge request arrived).

**Verified working end-to-end:** `/health`, `/score` with real `say`-generated
audio through the new backend (curl and via `core/client.js`), `/insights`
with no `GROQ_API_KEY` set (falls back to template narration correctly,
`"source": "template"`), auth gating on both new and existing endpoints
(401 without a session, real response with one), and the full browser flow
signup → child → map (all 7 nodes render, matching `core/exercise.js`'s
`LEVELS.length` — a real bug was caught and fixed here too: `views/kid.js`'s
`NODE_POS` array was still hardcoded to 6 entries from an earlier session,
one short of the current 7 levels, which would have thrown on the 7th node).

## Testing recipe

Generate real test audio (macOS only):
```bash
say -v Samantha -o /tmp/x.aiff "sun" && \
  ffmpeg -y -i /tmp/x.aiff -ar 16000 -ac 1 -c:a pcm_s16le /tmp/sun.wav
```

Score it via curl (need a session cookie first):
```bash
curl -c /tmp/jar -X POST localhost:8000/auth/login -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"yourpass"}'
curl -b /tmp/jar -F audio=@/tmp/sun.wav -F prompt_word=sun localhost:8000/score
```

To inject real audio through the browser (since the Browser pane can't use a
live mic): base64-encode a wav, write it to a throwaway module under `core/`,
`import()` it from a `javascript_exec` call, decode to a Blob, and call
`core/client.js`'s exported `score()` directly. Delete the throwaway file
after — don't leave test fixtures in `core/`.

**If something you just fixed doesn't seem to take effect: it's probably the
browser cache, not your fix.** Hard-reload, or navigate with a cache-busting
query string (`?cb=<random>`), or open a genuinely new tab. Server-side,
confirm with `curl` (bypasses browser caching entirely) before assuming your
code is wrong.

**Specifically: `sw.js`'s own re-registration can outlive a hard reload.**
`index.html` re-runs `navigator.serviceWorker.register('sw.js')` on every
`load` event, so even after you `unregister()` + `caches.delete('mira-v5')`
by hand, the very next navigation installs a brand-new SW instance that
re-fetches its whole `SHELL` list (including every `core/`/`views/` module)
into a fresh cache — and there's a real install/activate race where a page
that started loading just before the new SW claims clients can still end up
executing module bytes from a half-torn-down previous state. Hit this for
real once: fixed a bug in `views/icons.js`, confirmed via `curl` the server
was serving the fix, hard-reloaded twice, and the browser tab kept throwing
the *old* stack trace anyway. **Opening a genuinely new tab** (not just
reloading the existing one) was what actually cleared it — the SW's
network-first `fetch` handler is correct, so a truly fresh tab's first
request always resolves through it to the current server bytes, no manual
cache surgery required.

## Logical next steps (not started)

- **Verify mic capture + PWA install on a real device.** Still the single
  biggest untested gap — see "Not verified" above.
- Recalibrate `FLAG_THRESHOLD` on a real labeled sample (`server/calibrate.py`
  exists for exactly this now).
- Port the multi-instance word schema (see "v3 redesign + backend-merge
  session" above) if the word bank needs to grow past 16 single-instance words.
- Telemetry (AAARRR analytics) and OAuth (Google/Apple) — both scoped out,
  both need real backend routes; ask for them explicitly.
- Password reset / email verification if this goes anywhere near real users.
- Second exercise / second target phoneme (currently hardcoded to /s/ in
  `core/exercise.js` — the scoring pipeline itself is phoneme-agnostic).
