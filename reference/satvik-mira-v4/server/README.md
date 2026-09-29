# Mira scorer

> **Read [`../CAUTION.md`](../CAUTION.md) before changing anything in this
> directory.** The scoring pipeline is fragile in ways that don't show up
> just from reading the code.

The pronunciation-scoring engine (`mira_core.py`, `scorer.py`, `policy.py`,
`insights.py`, `calibrate.py`) is merged in **verbatim** from
[HimanshuKGP007/mira-app](https://github.com/HimanshuKGP007/mira-app), built
from that project's Module 1 notebooks — one confirmed bug fix aside (see
"What changed in this merge" below). `app.py`, `auth.py` and `db.py` are
Mira's own addition on top: real parent accounts, child profiles, and a
session cookie gating `/score` and `/insights`, none of which exist in the
upstream fork (it's a single-user process with no accounts at all). See the
root [`README.md`](../README.md) for how the two fit together.

```bash
./run.sh          # http://localhost:8000
PORT=9000 ./run.sh
```

First start creates a virtualenv (~2 GB of wheels) and downloads the acoustic
model (~1.26 GB) into `~/.cache/huggingface`. After that, startup is ~10-15s.

---

## What this is, and what it is not

This is the **GOP baseline** — the `post_max alone` rung of the Stage 2 ablation:

| | this service | trained ensemble |
|---|---|---|
| AUC (ranks good vs poor) | **0.734** | 0.843 |
| PCC (predicts the exact rating) | **0.176** | 0.376 |
| Confidence | raw CTC posterior, **uncalibrated** | Platt-calibrated |
| Needs artifacts | no | yes |

**Why not the trained ensemble.** It needs four Stage 2 artifacts that are not in
this repo: `mira_scorer.joblib`, `mira_sequence_model.pt`, `calibrator.json` and
`phone_token_map.json`. The blocker is the last one — the trained model's 193
feature columns include 74 `lpr_<phone>` columns whose phone labels exist only in
that file (they were derived from Speechocean762's MFA output). Without it the
feature frame cannot even be constructed, so the ensemble is unreachable at any
effort. Download those four files from the Kaggle output to upgrade.

**Why the confidence is not calibrated.** The published operating point —
`confidence < 0.86`, from Platt `a=4.2632, b=-5.8443` — belongs to the trained
ensemble's 0–2 output. Those parameters do not transfer to a raw posterior.
Applying them anyway would produce a confident, precise, entirely wrong number.
So `score` is `null`, `confidence` is the raw `post_max`, and the flag threshold
is a plain `MIRA_FLAG_THRESHOLD` (default `0.50`) that you should tune on your
own data before treating it as meaningful.

---

## API

### `POST /score`  — requires a signed-in parent (`mira_session` cookie)

`multipart/form-data`: `audio` (wav), `prompt_word`, `speaker_age_years` (optional)

Gate failure — returned **before** any scoring:

```json
{ "status": "retry", "reason": "low_snr", "snr_db": 8.4, "duration_s": 1.2 }
```

`reason` ∈ `low_snr | too_short | alignment | bad_audio | empty_audio`.

Scored:

```json
{
  "utterance_id": "live-sun-23921443",
  "prompt_word": "sun",
  "phones": [
    { "target": "s", "target_arpabet": "S", "position": "initial",
      "marking": "correct", "score": null,
      "confidence": 0.9635, "confidence_kind": "raw_posterior",
      "duration_ms": 120.0, "flags": [] },
    { "target": "ʌ", "position": "medial", "marking": "substituted",
      "confidence": 0.45, "substitute": "a5", "duration_ms": 160.0 }
  ],
  "quality_gate": { "passed": true, "snr_db": 26.6, "alignment_quality": 0.855 },
  "summary": { "total": 3, "scored": 3, "not_scored": 0 },
  "provenance": { "...": "model, aligner, threshold set, tier, latency_ms" }
}
```

`marking` ∈ `correct | substituted | omitted | assimilated | not_scored`.
A `not_scored` phone carries a `reason` and stays in the denominator — it is
withheld, not passed.

### `GET /health`  — public

Device, model, tier, expected AUC/PCC, thresholds, and the withheld phoneme list.

### `POST /insights`  — requires a signed-in parent

See "`POST /insights`" below.

---

## How it works

1. **Decode** → 16 kHz mono float32.
2. **SNR gate** (`MIRA_MIN_SNR_DB`, default 12 dB) — rejects before spending a forward pass.
3. **Canonical phones** from **CMUdict** for the prompt word. Absent word ⇒ everything
   `not_scored`, never a guessed target.
4. **Phone → vocabulary token** via `mira_core.build_phone_token_map`
   (override → exact → MFA table → normalised → diacritic-stripped).
5. **One forward pass** through `facebook/wav2vec2-lv-60-espeak-cv-ft` → log-softmax.
6. **CTC forced alignment** (`mira_core.ctc_forced_align`). **No Montreal Forced
   Aligner** — no subprocess, no conda. Too few frames ⇒ `retry`.
7. **Span expansion** — see the note below.
8. **GOP** per phone (`mira_core.gop_variants`), scored against the best-fitting
   spelling of the target (see below).
9. **Withholding** — phones with Stage 2 MAE > 0.25 (`u`, `t̪`, `ɫ`, `e`) are declined.
10. **Marking cascade** → the response above, optionally softened by the
    corroboration gate (see below).

### Two places this departs from the notebooks, on purpose

**Span expansion.** MFA returns true phone boundaries; CTC is peaky and parks most
frames on blank, giving each token one or two spike frames. Measuring GOP over a
single 20 ms frame is noisy, and against the 30 ms floor calibrated on MFA
durations it is indistinguishable from an omission — in testing it made *every*
phone unscorable. So every frame is attributed to a phone: blank runs between two
tokens split down the middle, leading/trailing blanks go to the nearest.

**Phone equivalence classes.** The espeak vocabulary spells one phone several
ways (`ɑ` also appears as `ɑː`, `a` as `a5`). Scoring against a single bare symbol
put the model's probability mass on a variant we weren't looking at, so correct
vowels read as near-zero posteriors. Each target now gets an equivalence class and
GOP is taken against its best member; the GOP denominator (max over the whole
vocabulary) is untouched, so a genuinely wrong production still scores low.
Consonants keep their exact identity — that is where this method separates
(59.7% vs 29.5% for vowels in the Stage 2 decode analysis).

### The corroboration gate

`post_max` alone can flag a phone on one bad frame even when the rest of the
window and the model's own discriminability both looked fine. Before honoring
a `post_max`-driven `substituted` verdict, `decide_marking()` requires it to
be corroborated by `post_mean` (was the *whole* window weak) or `gop_renorm`
(did the model actually prefer this phone over its competitors). If neither
corroborates, the phone is marked `correct` instead — this can only reduce
false positives, never add one. Disable with `MIRA_COMBINE_GOP=0`.
Uncalibrated, same as `MIRA_FLAG_THRESHOLD` — tune on real data.

### Known weak spots

Consonants score reliably; `/s/` measured 0.91–0.99 across every test word.
Voiced stops (`b`, `ɡ`) sit low because the burst is brief relative to the window,
and vowels are variable — both are consistent with the published per-phoneme
error table, where vowels carry the highest MAE. This is why the tier and its
limits are stated in every response and on both adult screens.

---

## What changed in this merge

One confirmed bug fix, made after unit-testing `decide_marking()` in
isolation both before and after (see `CAUTION.md`): the `omitted` marking was
unreachable. It checked `30 <= duration_ms < 40`, but `duration_ms` is always
an exact multiple of the 20 ms frame size (0, 20, 40, 60, ...), so no real
span could ever land in that window — and a 20 ms span was already caught by
the "too short to measure" → `not_scored` gate one line above, before the
omission check even ran. Fixed by moving the omission check ahead of that
gate and making its boundary `duration_ms <= 40.0`, so a genuinely
near-absent (one- or two-frame, low-confidence) span is now marked `omitted`
rather than silently swallowed as `not_scored`. Nothing else in the marking
cascade, thresholds, or withheld-phoneme list was touched.

---

## Files

| | |
|---|---|
| `mira_core.py` | ported **verbatim** from Stage 2 cell 3. Do not paraphrase it — a prior reimplementation of the same logic got several details wrong, and it has zero cell outputs (it was never executed). |
| `policy.py` | gates, withheld set, marking cascade, provenance |
| `scorer.py` | model load, span expansion, equivalence classes, the pipeline |
| `insights.py` | `/insights` — session-history arithmetic + optional Groq narration |
| `calibrate.py` | CLI: score a folder of labeled recordings, check `MIRA_FLAG_THRESHOLD` |
| `auth.py`, `db.py` | Mira's own — parent accounts, child profiles, sessions. Not part of the upstream fork; not part of the scoring path either (see `CAUTION.md`). |
| `app.py` | FastAPI; mounts `core/`, `views/`, `design/` explicitly so `server/` (and its virtualenv) is never web-reachable |

## Environment

See [`.env.example`](.env.example) for the full list with defaults. The two
you're most likely to touch:

| var | default | |
|---|---|---|
| `MIRA_FLAG_THRESHOLD` | `0.50` | **uncalibrated** — tune on your own data before a demo |
| `GROQ_API_KEY` | unset | optional. Powers the `/insights` narration; without it, that endpoint falls back to a template sentence built from the same numbers. Never required for scoring. |

---

## Manual calibration (`calibrate.py`)

`MIRA_FLAG_THRESHOLD` is the one number that separates `correct` from
`substituted`. It ships uncalibrated (see above), so before a demo, check it
against real recordings instead of trusting the default:

1. Record a handful of takes of your demo words — some said correctly, some
   deliberately wrong. Name them `<word>__correct__1.wav`, `<word>__wrong__1.wav`, etc.
2. `cd server && python calibrate.py path/to/recordings/`
3. It prints the confidence each take scored and tells you whether
   `correct`/`wrong` takes separate cleanly at the current threshold, and if
   not, what value would. Set `MIRA_FLAG_THRESHOLD` to that and restart.

No model weights change — this is picking a number, not training.

---

## `POST /insights`

Body: `{"child_name": str|null, "target_phone": "s", "sessions": [...], "word_bank": [...]}`
where `sessions` is `store.sessions` from `core/rewards.js`, oldest first — the same
session history the parent screen's tickers are already built from, sent by
the client rather than looked up server-side.

Computes ordinary aggregate figures (accuracy %, by word position, trend
across sessions — `insights.compute_analysis`, no model involved) and, if
`GROQ_API_KEY` is set, asks Groq for 2-3 sentences describing *only* those
numbers. The response is screened for clinical-claim language before it's
returned; any failure — no key, network error, timeout, a forbidden word —
falls back to a template sentence built from the same figures.

```json
{ "text": "...", "source": "llm", "analysis": { "...": "the numbers behind it" } }
```
# mira-v4
