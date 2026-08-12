<p align="center">
  <img src="icon.svg" width="88" alt="Mira">
</p>

<h1 align="center">Mira</h1>
<p align="center"><b>Per-sound pronunciation measurement for children's speech practice — built to measure, not diagnose.</b></p>

---

## What it is

Mira shows a child a word, records them saying it, and returns **one measurement
per sound**: was it produced correctly, what came out instead if not, and how
confident the measurement is. A kid-facing practice game ("Snake Sound Trail")
sits on top, with separate parent and clinician views onto the same data.

The design constraint that shapes everything else: **Mira measures, it does not
decide.** There is no field anywhere in the response for a diagnosis, a
severity, or a therapy plan — that boundary is enforced structurally, not just
by convention, and it's the reason the project is organized into two layers:

| Layer | Question it answers | Output |
|---|---|---|
| **Module 1** — measurement | How well was each sound produced? | Per-phone score, confidence, error type, provenance |
| **Module 2** — clinical analytics | What does the pattern across sounds mean? | Inventory grid, accuracy figures, phonological process analysis |

Module 2 only ever restates numbers Module 1 already computed — deleting its
narration layer entirely still leaves a report a clinician could read and sign.
That split, and why it matters, is documented in full in
[`Docs/MIRA.md`](Docs/MIRA.md).

## Why a known target changes the problem

A conventional speech recognizer is built to figure out *which word you said*,
so it's optimized to be robust to mispronunciation — the error gets corrected
away before it's ever visible. Mira already knows the word; the question flips
to *how well was each sound in it produced*, which only becomes answerable once
you stop trying to be robust to the thing you're trying to measure.

That single flip is why Mira scores two things a standard ASR pipeline can't:

| Path | Asks | Catches | Blind to |
|---|---|---|---|
| **Broad** (goodness of pronunciation) | How much of the model's probability went to the intended sound, versus everything else? | Swaps, drops | Distortions — a lateral /s/ still reads as /s/ |
| **Correlate** (direct acoustic measurement) | What does the physics of this segment look like? (F3 for /r/, spectral centroid for /s/, VOT for stops) | Distortions: right sound, produced badly | Anything without a known acoustic signature |

## Validated results

Measured against **Speechocean762** during Stage 2 development, holding out
speakers between folds:

| Metric | Result | Baseline | What it means |
|---|---|---|---|
| Scorer ranking (AUC) | **0.843** | 0.653 (binary baseline) | How reliably a poor sound is ranked below a good one |
| Correlation with human raters (PCC) | **0.376** | — vs. 0.612 published / 16.2% annotator disagreement ceiling | How well the score tracks a rater's actual number |
| Confidence calibration (ECE) | **0.390 → 0.036** | — | Whether "confident" actually means correct |
| Indian-English false-alarm rate | **11.2%** | 16.0% (corpus floor) | Fluent non-American English isn't penalized as error — the strongest evidence of clinical validity so far |
| Recall on genuinely poor sounds | **51%**, biased generous | — | The most important open weakness — being lenient is the dangerous failure direction |

These are offline, notebook-validated numbers for the full designed pipeline
(trained scorer + Platt calibration). **They are not the numbers the server in
this repo produces right now** — see Status below.

## Status: what's actually running vs. what's been validated

Honesty about this distinction is a hard rule in this codebase (an
uncalibrated number that *looks* validated is treated as the most dangerous
artifact it can produce), so it gets its own section instead of fine print.

| | `server/` (live in this repo) | Validated research pipeline |
|---|---|---|
| Scorer | GOP baseline — `post_max` alone | Trained ensemble (scorer + sequence model + calibrator) |
| AUC | 0.734 | 0.843 |
| PCC | 0.176 | 0.376 |
| Confidence | Raw CTC posterior, **uncalibrated** | Platt-calibrated |
| Needs extra artifacts | No | Yes — 4 Stage 2 output files not in this repo |

The gap is one missing file: `phone_token_map.json`, which carries phone
labels derived from Speechocean762's MFA output and isn't reproducible without
re-running that alignment. Every response the live server returns is stamped
`uncalibrated` end to end — response body, provenance block, and (in the
clinician view) the report header — and there's no flag to turn that off.

`Docs/mira-4/` is an in-progress rewrite of the whole measurement chain
(protocol-driven word set, a verified narration layer, a synthetic acoustic
backend for sub-second tests) — the intended next step, not yet wired into the
running app.

## Architecture

```
audio ──▶ condition ──▶ acoustic model ──▶ align ──▶ score ──┐
                                              │              │
                                              └─ free decode ┤
                                                             ▼
                                          per-sound records (Module 1)
                                                             │
                                        ┌────────────────────┴───────────────┐
                                        ▼                                    ▼
                            Module 2A: computes                   Module 2B: writes
                            grids, rates, accuracy                sentences — verified
                            (ordinary code, no model)              against 2A's figures
                                        │                                    │
                                        └────────────────┬───────────────────┘
                                                          ▼
                                                     clinician report
```

One FastAPI process (`server/app.py`) serves both the scoring API and the
static frontend, so there's nothing to run separately:

- `index.html`, `app.css`, `core/`, `views/` — the frontend (vanilla JS, no build step, PWA-installable)
- `server/` — the FastAPI scoring service; see [`server/README.md`](server/README.md) for the full API contract
- `Docs/MIRA.md` — the engineering log: the mental model, ten hard invariants, and a catalogued list of bugs that passed every test and were wrong anyway
- `Docs/mira-4/` — the in-progress next-generation rewrite

## Quick start

```bash
./start-mira.command
```

Double-click it in Finder, or run it from a terminal — either way it starts
the server and opens `http://localhost:8000` once it's ready. First run
creates a Python virtualenv, installs dependencies (~2 GB of wheels), and
downloads the acoustic model (~1.26 GB) into `~/.cache/huggingface`; that
only happens once. Every run after that is ready in well under 10 seconds.

```bash
cd server && PORT=9000 ./run.sh   # manual start, custom port
```

`server/run.sh` hashes `requirements.txt` on every launch and only reinstalls
dependencies when it's actually changed, so pulling updates is just:

```bash
git pull && ./start-mira.command
```

Requirements: Python 3.10+ and network access for the first-run downloads. No
API keys or external services.

## Engineering principles

A sample of the invariants this codebase holds itself to (the full list, with
the bugs each one exists because of, is in
[`Docs/MIRA.md`](Docs/MIRA.md#2-hard-rules)):

- **A gate must never be computed from the thing it gates.** Three separate,
  invisible bugs came from exactly this shape — each one would have made
  Mira refuse to score the recordings that contained errors, then report
  near-perfect accuracy on what survived.
- **Held is not correct.** A sound that fails a gate is excluded from every
  numerator *and* denominator, and counted separately as coverage.
- **An unresolvable symbol is held, never guessed.** Guessing produces
  confidently wrong output with no symptom.
- **Uncalibrated output is stamped everywhere and cannot be un-stamped.**
- **The measurement module never imports torch** — it takes
  log-probabilities as plain arrays, which is what keeps 200+ assertions
  runnable in under a second with no GPU.
