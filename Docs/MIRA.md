# MIRA.md

Everything learned building Module 1 and connecting it to Module 2, written for
whoever works on this next, human or Claude Code.

Read sections 1, 2 and 4 before changing anything. Section 4 is the bug catalog
and it is the most valuable part of this file: every bug in it was invisible,
passed all tests, and would have made the product silently claim near-perfect
accuracy.

---

## 1. The mental model

Someone is shown a word and asked to say it. Mira takes the recording plus the
fact that the word was known in advance, and returns one record per sound.

**Because the target is known, the question changes.** A speech recogniser is
built to work out which word you meant, so it is optimised to be robust to
mispronunciation, corrects the error on the way, and the error disappears. Mira
needs the opposite. The word is already known, so the question becomes "how well
was each sound produced", which is the only question that can be answered per
sound.

**Mira measures. It does not decide.** There is no field in the output for a
diagnosis, a severity, a prognosis or a therapy plan. This is enforced
structurally: `assert_no_clinical_claims` walks the response and refuses any
field whose name is a clinical claim. Module 2 is where measurements become
something a person reads, and it is a separate layer with a separate contract for
exactly that reason.

### The two scoring paths

| Path | Question | Catches | Blind to |
|---|---|---|---|
| **Broad** (goodness of pronunciation) | How much probability went to the sound we asked for, against every other sound? | Swaps, drops | **Distortions.** A lateral /s/ is still recognised as /s/ |
| **Correlate** (direct acoustic measurement) | What is the physics of this segment? F3 for /r/, spectral centroid for /s/, VOT for stops | Distortions: right sound, produced badly | Anything without a known acoustic signature |

The broad path is what the published literature scores. The correlate path is the
one that answers *"am I producing this sound correctly"* rather than *"do I sound
native"*, and it is the difference between the product and a pronunciation
scoring commodity.

**Status: the correlate path is implemented and its reference ranges are not
validated.** Fusion weight is 0. See section 6.

---

## 2. Hard rules

These are invariants. Breaking any of them produces a system that looks correct
and is not. If a change requires breaking one, that is a conversation, not a
commit.

1. **The measurement module must never import torch.** It takes log-probabilities
   as input and does arithmetic on them. This is what makes 200+ assertions
   runnable on a laptop in under a second, and it is the single biggest reason
   iteration is fast. Keep the acoustic model behind one small interface.

2. **The assertion count never decreases.** Every new function gets assertions in
   `self_test()`. Current: core 214, contracts 32, module 2A 46, module 2B 25.

3. **No field in the response schema may name a clinical claim.** `severity`,
   `diagnosis`, `condition`, `prognosis`, `treatment`, `therapy_plan`,
   `recommendation`, `duration_estimate`, `disorder`. The check is recursive and
   runs at the response boundary.

4. **A gate must never be computed from the thing it gates.** See section 4.1.
   This produced three separate bugs, all of the same shape, all invisible.

5. **Every score carries either a value or a reason it has none.** Never both,
   never neither. Enforced in `PhoneResult.__post_init__`.

6. **Held is not correct.** A sound that failed a gate must be excluded from
   every numerator *and* every denominator, and counted separately as coverage.
   Conflating them inflates apparent accuracy.

7. **An unresolvable symbol is held, never guessed.** A phone with no token id, a
   substitute with no ARPABET equivalent, a word not in the protocol. Guessing
   produces confidently wrong output with no symptom.

8. **Provenance travels with every score.** Model version, aligner version,
   protocol version, threshold set version, code hash, bundle version. The
   stamping function refuses rather than filling a blank with "unknown".

9. **Uncalibrated output is stamped everywhere and cannot be un-stamped.** On the
   phone result, the response, the analysis, the report banner and the provenance
   string. No flag turns it off. A preview number that looks like a validated
   number is the most dangerous artefact this codebase can produce.

10. **The narration layer may only restate computed figures.** It never receives
    audio, raw goodness scores, a knowledge base, prior reports or diagnostic
    criteria. Everything it writes is verified against the computed analysis and
    fails closed.

---

## 3. The measurement chain

Order matters. Steps 1 and 4 exist so the expensive parts only run on recordings
worth spending them on, which is a cost argument as much as a safety one.

| # | Step | What it does | Status |
|---|---|---|---|
| 01 | Condition | Trim silence, measure SNR, refuse audio too dirty to measure | wired |
| 02 | Represent | One forward pass of a phone-level CTC model. Every reading from identical frames | validated |
| 03 | Align | Where each target sound starts and ends | wired |
| 04 | Score broadly | Probability given to the intended sound versus everything else | **validated, AUC 0.843** |
| 04b | Decode freely | Unconstrained pass reporting what was actually heard, so a substitution can be **named** | wired |
| 05 | Measure physics | F3, spectral moments, VOT, normalised where norms exist | wired, ranges unvalidated |
| 06 | Fuse | One rating from both paths | wired, weight 0 |
| 07 | Calibrate | Make the confidence figure mean what it says | **validated, ECE 0.390 → 0.036** |
| 08 | Type the error | Score becomes a category, in a fixed order | wired |
| 09 | Tag position | Initial, medial, final, from the lexicon, never inferred | validated |
| 10 | Excuse the accent | Normal variety realisations forgiven before scoring, every excusal logged | wired, list EMPTY |
| 11 | Withhold | Refuse to score sounds the model is measurably bad at | wired |
| 12 | Gate | Four checks deciding whether anything may be said | wired |
| 13 | Stamp provenance | Versions travel with every score | validated |
| 14 | Serve | One surface running the identical measurement code | wired |

**Status vocabulary, and it matters:**
- `validated` measured against labels, with a number attached
- `wired` runs end to end, thresholds or ranges NOT validated
- `scaffold` correct code that has only ever seen synthetic input
- `absent` deliberately not built

### The error typing order

Fixed, because a label that depends on which test happened to run first is not a
label. Two people reading the same record must see the same category.

1. **Held** a gate failed. Overrides everything: a measurement that was not
   permitted has no error type
2. **Excused** the accent allow-list matched. Scored correct, logged with the
   rule, never reaches the later tests
3. **Omission** no segment produced in the aligned region
4. **Addition** a segment with no counterpart in the target
5. **Substitution** a different phone, with adequate confidence
6. **Assimilation** as substitution, but the substitute shares a feature with an
   adjacent segment. Different clinical implication, so reported separately
7. **Distortion** category right, a correlate outside its reference range
8. **Correct** everything else. Last, so it is what remains rather than something
   asserted

**Distortion is currently unreachable.** It needs the correlate path, and the
ranges are unvalidated, so `classify_error_type` returns `correct` where a
distortion would sit and records that it had no correlate evidence. This is a
real hole: distortion is the most common residual error in adults.

---

## 4. The bug catalog

Every one of these passed all tests. Every one had every component individually
correct. The connections were wrong.

### 4.1 The gate-computed-from-the-thing-it-gates family

**This is the most important thing in this file.** Three separate bugs, one
shape. Each would have made Mira refuse to score exactly the recordings
containing errors, then report near-perfect accuracy on what survived.

**Bug A: alignment quality was goodness of pronunciation.**
The obvious implementation of "how well do these boundaries fit" is the mean
posterior the model gives each *target* inside its own window. That number is
goodness of pronunciation. Using it as the gate on the score is circular. A
speaker who says [t] for /s/ gets a low target posterior, fails the alignment
gate, and the whole item is held.

Fix: `alignment_confidence` takes the model's **peak posterior over the whole
vocabulary** in each window. It asks whether the audio is confidently
*something*, which is what a defensible boundary means. A clear substitution
scores high, correctly: the boundaries are right and the sound is wrong, and
those are different findings that belong in different parts of the report.
Garbled audio still scores low. A target the aligner could not place at all
pulls the number down structurally.

**Bug B: confidence was target match.** Same failure one level down. Deriving
per-phone confidence from the target posterior makes a confident error read as
low confidence, so the per-phone gate withholds it.

Fix: confidence measures **how cleanly the window was measured** (peak posterior
in the window). The score says whether it was right. A window that is confidently
[t] when /s/ was asked for is a HIGH confidence measurement of a LOW score, and
both halves must survive into the record.

**Bug C: the word-identity gate fired on short words.** The gate exists to catch
someone naming the picture with a completely different word, which would
otherwise align to the wrong target and score every sound as an error. On a
two-sound target like "shoe", one substitution drops the similarity to 0.25 and
the gate held a good recording of a real error.

Fix: apply the gate only to targets of four sounds or more. Below that there is
no information separating "said a different word" from "made one mistake".

**The general lesson.** Before adding any gate, ask: *would this gate fire more
often on a speaker with the condition we are trying to detect?* If yes, it is
measuring the thing it is supposed to protect, and it will produce a system that
looks safe and is blind.

### 4.2 The serving path loaded a model and did not use it

`bundle.py` loaded the trained scorer, the calibrator, the feature list, the
sequence model and the hidden projection. `pipeline.py` then used none of them.
It took raw `gop_mean`, mapped it with `2.0 + gop/2.0`, and passed a bare sigmoid
off as a confidence.

That is roughly the AUC 0.653 binary baseline the whole training effort exists to
beat, behind a manifest advertising the calibrated threshold set. Every gate
downstream (confidence floor, per-phoneme error table, flag threshold) was
calibrated against a completely different number than the one being produced.

**Nothing failed. Every test passed.** The bundle loaded, the response validated,
the gates fired, the provenance stamped. Every piece was correct and they were
not connected.

Fix: one function is the only place a score is produced, and a wiring assertion
reads the serving source and checks the loaded artifacts are actually referenced.
Crude, and it is the kind of test that catches this class of bug, which unit
tests structurally cannot.

**Rule that follows: after loading any artifact, assert it is reachable from the
code path that produces output.**

### 4.3 Feature-set drift served silently

A model fed a different feature set than it was trained on returns confident
nonsense, and there is no symptom: the numbers look exactly like scores.

Fix: the scoring function **refuses** rather than imputing a missing feature.
Common cause is a bundle built from a run with different feature flags. Never
relax the strict check on anything clinical.

### 4.4 `'AE1'.isalpha()` is False

The IPA-to-ARPABET converter tested `s.isalpha()` to detect ARPABET. Stressed
vowels contain a digit, so the **entire vowel inventory** arrived at Module 2A as
unconvertible and was held. It presented as a coverage problem and was a
one-character predicate bug.

Fix: strip digits before the alphabetic test.

**Lesson: when a whole category goes missing, suspect a predicate, not the
model.** The symptom looked like a data problem for an hour.

### 4.5 `ctc_forced_align` returns a tuple

It returns `(path, score)`. Code treating it as one value passes a two-element
tuple to `spans_from_path`, which iterates it happily and produces spans that are
silently wrong. Always unpack.

### 4.6 SNR read 0 dB on clean short words

A short single word with no pause anywhere has no background to measure. A naive
percentile ratio reports roughly 0 dB and rejects a perfectly clean recording,
which is the dangerous direction for a gate.

Fix: detect that case and assume the clip is clean. **A gate that silently
discards good audio is far harder to notice than one that occasionally admits
bad audio.**

---

## 5. The Module 1 to Module 2 seam

This is where the two halves join and it is the thing that was missing for
months. Module 2A was complete, well written, 46 assertions passing, and
connected to nothing, because Module 1 emitted no produced phone and no error
type. That is the expensive kind of gap: nothing is broken and nothing works.

### The contract

Module 2A consumes a flat list of records:

```python
{
  "target_arpabet":   "S",              # required
  "produced_arpabet": "T",              # None for omission or when unnamed
  "error_type":       "substitution",   # from the fixed order in section 3
  "position":         "initial",        # initial | medial | final | None for vowels
  "in_cluster":       False,            # cluster reduction needs its own denominator
  "word":             "sun",
  "held":             False,            # excluded from numerator AND denominator
  "held_reason":      None,
  # optional, carried through for the clinician
  "start_s": 0.02, "end_s": 0.11, "confidence": 0.71, "score": 0.8,
  "excused_by": None,
}
```

### Two real mismatches to resolve

**Alphabet.** Module 1 works in IPA because the acoustic model and the aligner
do. Module 2A works in ARPABET because the clinical literature and the
phonological process tables do. Where the conversion fails, **hold the item**. A
process analysis that silently drops what it could not convert reports a lower
process rate than the truth and reads as clinical improvement.

**Held items.** A whole item that never got scored still has to reach Module 2A
as held rows, or coverage will not know it was attempted.

### The check that proves the seam works

A /s/ produced as [t] must arrive at Module 2A and come out as **stopping**. That
is a fricative realised as a stop, the textbook example. If it does not appear,
`produced_arpabet` is not arriving. Assert this in the test suite. Also assert
the control: a clean speaker produces **no** processes, otherwise a table that
always fires proves nothing.

---

## 6. Module 2A and 2B

**2A computes. 2B writes sentences.** Every clinical figure comes out of ordinary
code, is unit testable, and is reproducible by rerunning the same function on the
same input. The language model is downstream of all of it and cannot change a
number.

**The test of whether the split is real: deleting 2B entirely still leaves a
report a clinician can read and sign.** Put that in the test suite. If it fails,
clinical content has leaked into the narration layer and has to move back.

### 2B rules

- Receives the analysis object only. Never audio, raw goodness scores, a
  knowledge base, prior reports or diagnostic criteria. **Strip the per-sound
  record list before handing it over**: timings and confidences are not a
  narration layer's business.
- Every number it writes must appear in the analysis. The verifier admits
  sensible roundings with a tolerance under one percentage point, which is not a
  licence to approximate.
- A forbidden vocabulary screen catches condition names, severity words,
  recommendations, prognoses and causal explanations.
- **Fails closed.** Sentences that fail are dropped; if fewer than 70% survive,
  the whole narrative is discarded and the caller prints the tables. That
  fallback is what makes the language model optional, and optional is what makes
  it safe.
- A template narrator that fills sentences from the analysis passes by
  construction and needs no model. Ship it as the default so 2B is never a
  dependency.

### What Module 2 must never do

Stated as data so a test can assert against it:

| Prohibited | Why |
|---|---|
| Select a therapy approach | The most consequential decision in a case. The clinician's |
| Select a target sound | Depends on stimulability, intelligibility impact, generalisation potential, family circumstances |
| Write placement instructions | A physical instruction without judgement of oral structure is treatment |
| State a diagnosis | A regulated professional act |
| State severity as a verdict | The figure and the band are facts; the verdict is a clinical judgement wearing a number as a costume |
| Estimate therapy duration | The clinician's judgement and the basis of their fee |
| Explain why progress stalled | Adherence, approach, target choice, hearing, motivation and family circumstances all produce the same flat line |

---

## 7. Numbers, and what they mean

Quote these exactly. Do not re-derive them from memory.

| Figure | Value | What it means |
|---|---|---|
| Baseline reproduction | **0.6103** vs published 0.612 | The environment computes what the field computes. Teaches nothing about the product |
| Scorer ranking | **AUC 0.843** vs 0.653 binary | Ranks bad sounds above good ones |
| Correlation with humans | **0.376** | Against a published 0.612 target and a 16.2% annotator disagreement ceiling |
| Calibration | **0.390 → 0.036** ECE | The confidence figure means what it says |
| Indian English false alarms | **11.2%** vs a **16.0%** floor | Complains *less* about fluent Indian English than about the corpus it trained on. No accent penalty to fix. **The strongest clinical-validity evidence in the project** |
| Recall on poor sounds | **51%**, biased generous | The most important weakness. Invisible in every headline number |
| Pairing loss | 63% discarded, 7.6% of survivors implausible | Open |

### The class-imbalance trap

The training corpus is roughly **96% correct**. A model that says "correct" to
everything scores 96% accuracy and is worthless. **Never report accuracy on this
data.** Report recall on the poor class, precision, and flag rate.

Being generous is the dangerous direction: telling someone a wrong sound was
right sends them away to practise the error. The reverse is annoying and self
correcting.

Three fixes, none of them a model change: class weights (clipped, or one
mislabelled row dominates the gradient), synthetic negatives, and an operating
point chosen against a stated cost ratio.

**Synthetic negatives from real audio:** take a sound produced *correctly* and
score it against a *different* target. Goodness of pronunciation measures how
well audio matches the sound asked for, so a clean /s/ scored against target /t/
is a genuine mismatch with real audio and a known label. No synthesis artefacts.
**Caveat that must travel with it:** these are substitution-shaped negatives.
They manufacture no distortions, because a distortion is the right category
produced badly and there is no way to fake that from correct audio.

**The operating point is a clinical decision.** A 4:1 cost ratio (a missed error
costs four times a false alarm) is an assertion about consequence, not a fact. It
exists so the conversation with an SLP has something concrete to argue with.

### The trade nobody should make quietly

Any change that raises recall on the training corpus raises the false-alarm rate
on fluent Indian English by roughly the same amount. The 11.2% result took a
whole stage to establish and is the strongest evidence the product has. **Re-run
the accent check before accepting any recall improvement.**

---

## 8. Traps specific to this domain

**The alignment trap.** Distorted speech causes silent misalignment, which
corrupts every downstream feature with no symptom. Carry alignment confidence as
an explicit field all the way into Module 2's input schema. Never let it be
implicit.

**Decoding isolated clips fails.** CTC models need continuous context. Decoding a
phoneme clip in isolation produces garbage. Full-utterance decoding with
frame-level timing read-off is the validated approach.

**Accent-neutral design is a hard constraint.** Western-pretrained models miscall
normal Indian English phonology as errors: retroflex /t d/, dental /θ/, the /v/
and /w/ merger, epenthesis breaking up clusters. The allow-list mechanism and the
accent validation exist specifically to prevent this. Letting epenthesis reach
the process table manufactures a phonological disorder out of an accent.

**The allow-list must ship empty.** Deciding that a realisation is acceptable
rather than erroneous is a clinical judgement and the code must not make it.
What the code owes is the mechanism plus an audit trail. Every rule carries who
approved it and when; an unattributed rule is refused at load, because the
liability argument rests on being able to say a year later which clinician
accepted which excusal. Every excusal is logged so a clinician can review what
was forgiven on their behalf.

**Adult first is the correct engineering sequence.** Adults are the easier target
across every acoustic feature family. Children need age-banded norms and child
speech data that does not exist at scale for this population. A child's formants
sit 20 to 50 percent higher and every adult reference range is wrong for them.

**Norms must refuse rather than approximate.** `norm_z` returns None for anyone
under 18 rather than a plausible-looking number. A wrong z score printed next to
a correct-looking decimal is exactly how an automated system produces something
that reads as rigorous and is not.

**A fixed protocol beats grapheme-to-phoneme.** Letting a user type any word
introduces a second invisible error source: when the pronunciation guess is
wrong, every sound in the word scores as an error and the recording looks like a
severe articulation problem. Only score words you asked for.

---

## 9. Key API surface

The measurement module (`mira_core`, v2.2.0, 214 assertions, no torch import).

**Conditioning**
- `condition_audio(audio, sr, do_trim, min_snr_db) -> (audio, report)`
- `estimate_snr_db(audio)` fails safe on gap-free clips
- `trim_silence`, `preemphasis`, `cmvn`, `frame_energy`

**Alignment and decode**
- `ctc_forced_align(logprobs, targets, blank_id) -> (path, score)` **unpack it**
- `spans_from_path(path, n_targets)` returns `(None, None)` for unplaced targets
- `alignment_confidence(logprobs, spans, target_ids) -> (quality, detail)`
- `free_decode(logprobs, blank_id, inv_vocab) -> {segments, string, n_segments}`
- `attribute_produced_phones(targets, segments) -> (per_target, insertions)`

**Scoring**
- `gop_variants(logprobs, lo, hi, target_id, blank_id)`
- `lpp_lpr_features`, `pool_hidden`, `add_context_features`
- `PlattCalibrator`, `expected_calibration_error`, `reliability_table`
- `fuse_broad_and_correlate(broad, z, weight=0.0)`

**Clinical**
- `classify_error_type(...) -> (type, why)` the reason travels with the label
- `AccentAllowList` with `.match`, `.excuse`, `.log`, `.to_json`
- `measure_correlates`, `norm_z`, `spectral_moments`, `formant_correlates`,
  `voice_onset_time`

**Class balance**
- `class_weights_from_labels`, `sample_weights_from_labels`
- `synthetic_mismatch_features`, `choose_distractor`
- `recall_operating_point`, `cost_weighted_threshold`

**Validation**
- `speaker_grouped_folds` the same speaker must never appear in both splits
- `wilson_ci`, `mean_ci`, `roc_auc`, `pearson_r`, `point_biserial`
- `self_test()` returns the assertion count

---

## 10. Working practices that paid off

**Negative controls before batch application.** Validate a new approach on a
control before applying it at scale. Label-shuffle permutations: if the headline
number survives shuffling the labels, the signal is not real. The clean-speaker
control for the process table: a table that always fires proves nothing.

**A traceability map as executable data, not prose.** A table of what exists,
where, and how far it can be trusted, printed by a cell that runs on CPU with no
data attached. Prose drifts. A structure the notebook checks itself against does
not.

**Test the wiring, not just the components.** Every bug in section 4 had correct
components. Assert that loaded artifacts are reachable from the output path, that
a substitution survives every conversion, that the clean control produces nothing.

**Keep the expensive dependency behind one interface.** The acoustic model is one
swappable object. A synthetic implementation that fabricates frames from a phone
sequence lets the entire chain be tested in under a second with no GPU and no
network. This is worth more than any other single decision in the codebase.

**Status vocabulary with four values.** `validated`, `wired`, `scaffold`,
`absent`. "It's done" hides the difference between "measured against labels" and
"runs without crashing".

**Limitations travel with the artifact.** A limitation in a document nobody
re-reads is not a limitation. Put it in the bundle manifest, the response
provenance and the report header.

---

## 11. What to do next, in order

1. **Train and wire a real scorer.** One training run ends preview mode. Until
   then the deployed scorer is roughly the baseline the whole effort exists to
   beat. Verify the bundle actually reaches the scoring path (section 4.2).

2. **Apply the cheap fixes.** Dictionary-derived targets (measured worth +0.04,
   never applied) and pairing recovery (63% discarded). An afternoon each, no
   GPU, together likely worth more than any remaining modelling work.

3. **Fix recall on poor sounds.** 51%, biased generous, in the dangerous
   direction. Class weights and synthetic negatives, then re-run the accent check
   before accepting the result.

4. **Fill the protocol coverage holes.** Phoneme balanced and position balanced,
   with pictures and accepted alternates. Linguistic work, needs no model, blocked
   on nothing. This is the highest-value task not blocked by anything else.

5. **Show hand-laid output to three practising SLPs.** Requires zero further
   code and is the highest-information action available.

6. **Get the allow-list written.** Blocked on a clinician, so start the
   conversation now. The mechanism is ready.

7. **Start consent and ethics paperwork.** The only item whose timeline is set by
   approval rather than engineering. Blocks the entire age axis and every
   clinical claim.

**Deliberately not next:** correlate range validation (needs consented age-banded
recordings), child speech, disordered speech, fine-tuning the acoustic model,
fluency, voice quality, prosody. Adding any of these now is scope creep.

---

## 12. The sentence that goes on every number

> Everything here was measured on adult and adolescent second-language English
> learners saying prompted words, on the subset of recordings that survived
> pairing. No disordered speech and no child speech has touched any of it. The
> pipeline has been shown to tell correct speech from correct speech, which is a
> necessary condition for a clinical claim and nowhere near a sufficient one.

If a deck, a demo or a pitch says something that contradicts this, one of the two
is wrong and it is not this paragraph.

---

## 13. Instructions for Claude Code

```
## Before changing anything
- Read sections 2 and 4 of MIRA.md.
- Run the test suite. It should take under two seconds. If it is slow, the
  acoustic model has leaked into the test path; fix that first.

## Hard rules
- The measurement module must never import torch.
- The assertion count never decreases.
- No response field may name a clinical claim.
- Never compute a gate from the thing it gates (MIRA.md 4.1).
- Held is not correct. Unresolvable is held, never guessed.
- Never remove or weaken an uncalibrated / preview stamp.

## When adding a gate
State explicitly whether it fires more often on a speaker with the condition
being detected. If it does, it is measuring the thing it is supposed to protect.

## When adding a feature or artifact
Assert it is reachable from the code path that produces output. Loading an
artifact and not using it passes every test (MIRA.md 4.2).

## When touching the Module 1 to Module 2 seam
Two assertions must hold: a /s/ produced as [t] comes out of Module 2A as
stopping, and a clean speaker produces no processes at all.

## Reporting results
Never report accuracy on the training corpus; it is 96% correct. Report recall on
the poor class, precision, and flag rate. Any recall improvement requires
re-running the accent check before it is accepted.

## Tone in code comments
Explain why, not what. Plain register, no em dashes. State a limitation directly
rather than hedging around it.
```
