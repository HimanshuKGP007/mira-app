# Mira

Speech scoring, sound by sound, plus the clinical analytics on top of it.
Module 1 and Module 2 in one runnable package.

```
pip install -e ".[serve,dev]"
python -m mira_app demo            # end to end, no model, no network, no GPU
python -m mira_app serve --synthetic
```

`demo` is the one to run first. It exercises the whole chain from audio
conditioning through to the HTML report using a synthetic decoder, so it needs no
model download and no GPU. If it works, every part of Mira except the acoustic
model itself is working on this machine.

---

## What it does

Someone is shown a word and asked to say it. Mira takes the recording, plus the
fact that the word was known in advance, and returns one record per sound: how
well it was produced, how sure the system is, what came out instead when
something else did, and where in the recording it happened. Then Module 2 turns
those records into an inventory grid, accuracy figures, a phonological process
analysis, and a report.

**Mira measures. It does not decide.** There is no field in the output for a
diagnosis, a severity, a prognosis or a therapy plan, and a check refuses any
payload that grows one.

```
audio ──▶ condition ──▶ acoustic model ──▶ align ──▶ score ──┐
                                              │              │
                                              └─ free decode ┤
                                                             ▼
                                            per-sound records (Module 1)
                                                             │
                                          ┌──────────────────┴──────────────┐
                                          ▼                                 ▼
                              Module 2A: computes                Module 2B: writes
                              grids, rates, accuracy             sentences, verified
                              (ordinary code, no model)          against 2A's figures
                                          │                                 │
                                          └──────────────┬──────────────────┘
                                                         ▼
                                                    HTML report
```

Module 2B may only restate what Module 2A computed. Anything it writes goes
through a verifier: a sentence containing a number that is not in the analysis,
or a word from the forbidden vocabulary, is dropped, and if too many sentences
fail the whole narrative is discarded and the tables stand alone. **Deleting
Module 2B entirely still leaves a complete report.** That is the test of whether
the split is real, and it is in the test suite.

---

## Current status, plainly

**Preview mode.** There is no trained scorer in this repo. Scores come from a
crude monotone map over goodness of pronunciation and the confidence is
uncalibrated. That is roughly the published binary baseline: it ranks bad sounds
above good ones about 65% of the time where the trained scorer manages 84%.

Good enough to demonstrate the product. Not good enough to show a clinician.
`uncalibrated` is stamped on every phone result, every response, every analysis,
the report header and the provenance block, and there is no flag to turn it off.

**To leave preview mode:** run Stage 2 of the Module 1 notebook, then

```
python -m mira_app session recordings/ --bundle path/to/stage2_output
```

The loader verifies the bundle before it serves: it checks the measurement code
hash against the manifest, confirms the calibrator is present, and refuses to
start if the scorer cannot be fed the features it was trained on.

**Never validated on:** child speech, disordered speech. Neither has touched any
part of this system. Every figure it produces came from adult and adolescent
second-language English learners saying prompted words.

**Wired but unvalidated:** the correlate path (formants, spectral moments, voice
onset time). The extractors are real; the reference ranges are adult
native-English anchors from the literature. Its fusion weight is zero, so it
cannot move a score. `--correlates` turns the measurement on and the ranges stay
unvalidated.

**Empty on purpose:** the accent allow-list. The mechanism is live and the list
has no rules in it. Deciding that a realisation is acceptable rather than
erroneous is a clinical judgement and the code does not make it.

---

## Commands

```
python -m mira_app check                       what this install can do
python -m mira_app words                       the protocol and its coverage gaps
python -m mira_app demo                        the whole chain, synthetically
python -m mira_app demo --clean                the control: a speaker with no errors
python -m mira_app score sun.wav --word sun    one recording
python -m mira_app session recordings/         a folder of <word>.wav
python -m mira_app serve                       the browser interface
```

`session` reads a folder where each file is named for the word it contains
(`sun.wav`, `rabbit_2.wav`). Words outside the protocol are skipped rather than
guessed, because a guessed pronunciation makes every sound in the word look
wrong.

To score real audio you need the acoustic model:

```
pip install -e ".[audio]"
```

It downloads about 1 GB once, then runs offline on CPU.

---

## The protocol

Mira only listens to words it already asked for. `mira_app/protocol.py` holds 45
items with their ARPABET targets, chosen for the adult intelligibility case:
sibilants, rhotics, stop voicing and the clusters that break down first.

`python -m mira_app words` prints the coverage and the holes. There are holes.
A sound with no medial item cannot be reported on medially, and the report must
not imply otherwise. Filling them is linguistic work and needs no model, which
makes it the highest-value task in the project that is not blocked on anything.

---

## Layout

```
mira_app/
  protocol.py        the words, targets, position and cluster tags
  acoustics.py       the ONLY part needing a GPU or a download, behind one interface
  score.py           Module 1: one recording to per-sound records
  session.py         the Module 1 to Module 2 seam, and the narration layer
  report.py          the HTML report
  bundle_loader.py   turns a Stage 2 output folder into a live scorer
  cli.py, server.py  terminal and browser
  mira_core.py       the measurement code. Imports no torch. 214 assertions
  contracts.py       the response schema and the gates. 32 assertions
  mira_module2a.py   deterministic clinical analytics. 46 assertions
  mira_module2b.py   the narration verifier. 25 assertions
tests/               23 end-to-end tests, 0.9 seconds, no model needed
```

The acoustic model sits behind one small interface with two implementations, the
real one and a synthetic one. That is what makes the test suite fast: the
expensive component is a swappable object rather than a dependency threaded
through every function.

---

## Three bugs worth knowing about

All three were the same shape: a gate that held exactly the recordings containing
errors, so Mira would have reported near-perfect accuracy by declining to score
anything that went wrong. All three are in the test suite now.

**Alignment quality was goodness of pronunciation.** Computing it as the mean
posterior on each target inside its own window means gating the score on the
score. A speaker who says [t] for /s/ failed the gate and the whole item was
held. `mira_core.alignment_confidence` measures the model's peak posterior over
the whole vocabulary instead, which asks whether the audio was confidently
*something*. A clear substitution now scores high on alignment and low on the
sound, and both halves reach the report.

**Confidence was target match.** Same failure one level down. A confident error
read as low confidence, so the per-phone gate withheld it. Confidence now
measures how cleanly the window was measured; the score says whether it was
right.

**The word-identity gate fired on short words.** It exists to catch someone
naming the picture with a different word. On a two-sound target like "shoe" a
single substitution drops the similarity below the threshold, so it held a good
recording of a real error. It now applies only to targets of four sounds or more,
because below that there is no information separating "different word" from "one
mistake".
