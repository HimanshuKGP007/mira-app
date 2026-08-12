"""mira_module2a.py, Module 2A, the deterministic analytics layer.

WHAT THIS IS
------------
Module 1 (the whole of the consolidated notebook above this point) answers one
question per sound: *how well was this phoneme produced, and how sure are we?*

Module 2A answers the clinical questions that sit on top of that:
    - how many consonants were correct, out of how many attempted
    - which simplification rules explain the errors
    - did the same word come out the same way three times
    - how fast and how evenly can they repeat pa-ta-ka
    - what changed since the last probe

Every function here is ORDINARY ARITHMETIC on the Module 1 record. There is no
model, no learned threshold, no language model, and no randomness. That is the
entire architectural point: a clinician who disagrees with a number can be shown
the two integers it was divided from. A number that cannot be recomputed by hand
cannot be defended, and a clinical figure that cannot be defended should not be
printed.

THE RULE THAT SHAPES EVERY FUNCTION HERE
----------------------------------------
Every rate carries its denominator. `PCC = 84%` is not a result; `PCC = 84%,
41 of 49 consonants attempted, single-word elicitation` is. A proportion whose
denominator is invisible cannot be interpreted, and in a clinical document it
will be interpreted anyway, wrongly. So every metric in this file returns a
small object carrying the numerator, the denominator and the context, and the
percentage is derived from those rather than stored on its own.

WHAT THIS FILE DELIBERATELY DOES NOT DO
---------------------------------------
No diagnosis, no severity verdict, no therapy approach, no target selection, no
prognosis, no duration estimate. Those are the clinician's professional acts and
their professional liability. See `module2_prohibitions()` at the bottom, which
is the list stated as data so it can be asserted against in a test rather than
living only in a document nobody re-reads.

Depends only on the standard library so it can be unit-tested anywhere.
"""

MODULE2A_VERSION = "1.0.0"

import math
from collections import Counter, defaultdict

# =============================================================================
# 0. Small shared types
# =============================================================================


def rate(numerator, denominator, context=None, label=None):
    """Every proportion in this module goes through here.

    Returns the numerator, the denominator, the percentage and the elicitation
    context together, because a percentage on its own is not a clinical figure.
    A zero denominator returns `None` for the percentage rather than raising or
    silently returning 0.0, "no opportunities existed" and "zero percent" are
    completely different clinical statements and must not collapse into one.
    """
    n = int(numerator)
    d = int(denominator)
    return {
        "label": label,
        "n": n,
        "d": d,
        "pct": (100.0 * n / d) if d > 0 else None,
        "context": context,
        "reportable": d > 0,
    }


def fmt_rate(r):
    """One-line rendering used everywhere a rate is printed, so the denominator
    can never be dropped by a caller who was only after the percentage."""
    if r is None:
        return "not computed"
    if not r["reportable"]:
        return f"{r['label'] or 'rate'}: not computed (no opportunities)"
    ctx = f", {r['context']}" if r["context"] else ""
    return f"{r['label'] or 'rate'}: {r['pct']:.1f}% ({r['n']} of {r['d']}{ctx})"


# =============================================================================
# 1. Consonant and vowel accuracy, PCC, PCC-R, PVC
# =============================================================================
#
# PCC is the standard severity index for speech sound disorders. The definition
# is simple; the traps are not.
#
#   TRAP 1, held items. A phoneme Module 1 refused to score is NOT an error.
#   Counting held items as errors makes a noisy recording look like a severe
#   disorder. They leave both numerator and denominator, and the number that
#   left is reported as coverage.
#
#   TRAP 2, PCC vs PCC-R. PCC-R counts clinical distortions as correct, so only
#   substitutions and omissions are errors. The GAP between the two is exactly
#   the distortion load, which is the population Module 1's acoustic work
#   exists to detect. Reporting both makes that visible; reporting one hides it.
#
#   TRAP 3, elicitation context. The same person scores higher on a single-word
#   list than in running speech, and higher again on imitation than on
#   spontaneous naming. A PCC without its context is not comparable to anything,
#   including itself last month.

VOWEL_ARPABET = {
    "AA", "AE", "AH", "AO", "AW", "AY", "EH", "ER", "EY",
    "IH", "IY", "OW", "OY", "UH", "UW",
}

# Error types, in the fixed assignment order from the B2B specification. The
# order is what makes the typing reproducible: a production that could be read
# as both an assimilation and a substitution is always typed the same way.
ERROR_TYPES = ["excused", "omission", "addition", "substitution",
               "assimilation", "distortion", "correct"]

ERRORS_FOR_PCC = {"omission", "addition", "substitution", "assimilation", "distortion"}
ERRORS_FOR_PCC_R = {"omission", "addition", "substitution", "assimilation"}


def is_vowel(phone_arpabet):
    """ARPABET carries a stress digit on vowels; strip it before comparing."""
    if phone_arpabet is None:
        return False
    return "".join(c for c in str(phone_arpabet).upper() if not c.isdigit()) in VOWEL_ARPABET


def accuracy_metrics(phoneme_results, context="single_word"):
    """PCC, PCC-R and PVC from a list of Module 1 phoneme results.

    Each item needs: `target_arpabet`, `error_type`, and `held` (bool).
    Held items are excluded from both numerator and denominator and counted
    separately as coverage, because "we could not score this" is not "this was
    wrong" and conflating them inflates apparent severity.
    """
    scored = [p for p in phoneme_results if not p.get("held")]
    held = [p for p in phoneme_results if p.get("held")]

    cons = [p for p in scored if not is_vowel(p.get("target_arpabet"))]
    vows = [p for p in scored if is_vowel(p.get("target_arpabet"))]

    pcc_ok = sum(1 for p in cons if p.get("error_type") not in ERRORS_FOR_PCC)
    pccr_ok = sum(1 for p in cons if p.get("error_type") not in ERRORS_FOR_PCC_R)
    pvc_ok = sum(1 for p in vows if p.get("error_type") not in ERRORS_FOR_PCC)

    out = {
        "pcc": rate(pcc_ok, len(cons), context, "PCC"),
        "pcc_r": rate(pccr_ok, len(cons), context, "PCC-R"),
        "pvc": rate(pvc_ok, len(vows), context, "PVC"),
        "coverage": rate(len(scored), len(phoneme_results), context, "coverage"),
        "n_held": len(held),
        "held_reasons": dict(Counter(p.get("held_reason", "unspecified") for p in held)),
    }
    # The distortion load is the gap between the two, and it is the number the
    # acoustic half of Module 1 exists to produce. Derived rather than stored so
    # it cannot drift away from the two figures it is defined by.
    if out["pcc"]["reportable"]:
        out["distortion_load_pct"] = out["pcc_r"]["pct"] - out["pcc"]["pct"]
    else:
        out["distortion_load_pct"] = None
    return out


# =============================================================================
# 2. The inventory grid, consonant by word position
# =============================================================================
#
# This is the artefact a clinician actually reads first: every consonant down
# the side, initial / medial / final across the top, and in each cell what
# happened. It is the single-word articulation inventory they currently produce
# by hand with a photocopied word list.

POSITIONS = ["initial", "medial", "final"]


def inventory_grid(phoneme_results):
    """Consonant x position grid. Each cell carries the counts, the error types
    seen, and what was produced instead, because "the /s/ was wrong" is not a
    clinical record and "/s/ produced as [t] in initial position" is."""
    grid = defaultdict(lambda: {p: None for p in POSITIONS})
    for p in phoneme_results:
        tgt = p.get("target_arpabet")
        pos = p.get("position")
        if tgt is None or pos not in POSITIONS or is_vowel(tgt):
            continue
        cell = grid[tgt][pos]
        if cell is None:
            cell = {"n": 0, "n_correct": 0, "n_held": 0,
                    "error_types": Counter(), "produced": Counter()}
            grid[tgt][pos] = cell
        cell["n"] += 1
        if p.get("held"):
            cell["n_held"] += 1
            continue
        et = p.get("error_type")
        cell["error_types"][et] += 1
        if et in ("correct", "excused"):
            cell["n_correct"] += 1
        else:
            # Only record the substitute when the free decode was confident
            # enough to name it. A guessed identity in a clinical grid is worse
            # than an admitted blank.
            if p.get("produced_arpabet") and p.get("produced_confident", True):
                cell["produced"][p["produced_arpabet"]] += 1
    return {k: v for k, v in sorted(grid.items())}


def grid_to_rows(grid):
    """Flatten the grid for printing or for writing to CSV."""
    rows = []
    for phone, cells in grid.items():
        row = {"target": phone}
        for pos in POSITIONS:
            c = cells[pos]
            if c is None:
                row[pos] = "not administered"
            elif c["n_held"] == c["n"]:
                row[pos] = "held"
            else:
                subs = ", ".join(f"[{k}]x{v}" for k, v in c["produced"].most_common(2))
                row[pos] = f"{c['n_correct']}/{c['n'] - c['n_held']}" + (f"  {subs}" if subs else "")
        rows.append(row)
    return rows


# =============================================================================
# 3. Phonological process analysis
# =============================================================================
#
# A phonological process is a rule that generates many surface errors at once.
# Finding the rule gives a clinician ONE thing to treat instead of ten, and
# generalisation to untreated sounds is the main evidence that treating the rule
# is working.
#
# THE DENOMINATOR IS THE WHOLE GAME. "Fronting occurred 6 times" is meaningless.
# "Fronting occurred on 6 of 8 opportunities" is a clinical finding, and "6 of
# 40" is a different one entirely. So every process is defined as a pair of
# predicates: does an OPPORTUNITY for this rule exist at this target, and did
# the rule APPLY in this production.

PLACE = {
    "P": "bilabial", "B": "bilabial", "M": "bilabial",
    "F": "labiodental", "V": "labiodental",
    "TH": "dental", "DH": "dental",
    "T": "alveolar", "D": "alveolar", "N": "alveolar", "S": "alveolar",
    "Z": "alveolar", "L": "alveolar",
    "SH": "postalveolar", "ZH": "postalveolar", "CH": "postalveolar", "JH": "postalveolar",
    "R": "postalveolar", "Y": "palatal",
    "K": "velar", "G": "velar", "NG": "velar", "W": "velar", "HH": "glottal",
}
MANNER = {
    "P": "stop", "B": "stop", "T": "stop", "D": "stop", "K": "stop", "G": "stop",
    "F": "fricative", "V": "fricative", "TH": "fricative", "DH": "fricative",
    "S": "fricative", "Z": "fricative", "SH": "fricative", "ZH": "fricative",
    "HH": "fricative",
    "CH": "affricate", "JH": "affricate",
    "M": "nasal", "N": "nasal", "NG": "nasal",
    "L": "liquid", "R": "liquid",
    "W": "glide", "Y": "glide",
}
VOICED = {"B", "D", "G", "V", "DH", "Z", "ZH", "JH", "M", "N", "NG", "L", "R", "W", "Y"}


def _base(p):
    if p is None:
        return None
    return "".join(c for c in str(p).upper() if not c.isdigit()) or None


# Each process is (opportunity_predicate, applied_predicate).
# `t` is the target phone, `a` the produced phone, `ctx` the item context dict.

def _opp_fronting(t, ctx):
    return PLACE.get(t) == "velar"


def _app_fronting(t, a, ctx):
    return PLACE.get(a) == "alveolar"


def _opp_backing(t, ctx):
    return PLACE.get(t) == "alveolar"


def _app_backing(t, a, ctx):
    return PLACE.get(a) == "velar"


def _opp_stopping(t, ctx):
    return MANNER.get(t) in ("fricative", "affricate")


def _app_stopping(t, a, ctx):
    return MANNER.get(a) == "stop"


def _opp_gliding(t, ctx):
    return MANNER.get(t) == "liquid"


def _app_gliding(t, a, ctx):
    return MANNER.get(a) == "glide"


def _opp_deaffrication(t, ctx):
    return MANNER.get(t) == "affricate"


def _app_deaffrication(t, a, ctx):
    return MANNER.get(a) == "fricative"


def _opp_final_deletion(t, ctx):
    return ctx.get("position") == "final" and MANNER.get(t) is not None


def _app_final_deletion(t, a, ctx):
    return a is None


def _opp_cluster_reduction(t, ctx):
    return bool(ctx.get("in_cluster"))


def _app_cluster_reduction(t, a, ctx):
    return a is None


def _opp_final_devoicing(t, ctx):
    return ctx.get("position") == "final" and t in VOICED and MANNER.get(t) == "stop"


def _app_final_devoicing(t, a, ctx):
    return a is not None and a not in VOICED and MANNER.get(a) == "stop"


def _opp_weak_syllable_deletion(t, ctx):
    return bool(ctx.get("in_weak_syllable"))


def _app_weak_syllable_deletion(t, a, ctx):
    return a is None


PROCESSES = {
    "fronting": (_opp_fronting, _app_fronting,
                 "a sound made at the back of the mouth comes out at the front "
                 "('key' becomes 'tea')"),
    "backing": (_opp_backing, _app_backing,
                "the reverse of fronting; less common and clinically more concerning"),
    "stopping": (_opp_stopping, _app_stopping,
                 "a continuous sound becomes a stopped one ('sun' becomes 'tun')"),
    "gliding": (_opp_gliding, _app_gliding,
                "a liquid becomes a glide ('rabbit' becomes 'wabbit'); normal in "
                "young children"),
    "deaffrication": (_opp_deaffrication, _app_deaffrication,
                      "an affricate becomes a simple fricative ('chip' becomes 'ship')"),
    "final_consonant_deletion": (_opp_final_deletion, _app_final_deletion,
                                 "the last consonant is dropped ('cat' becomes 'ca')"),
    "cluster_reduction": (_opp_cluster_reduction, _app_cluster_reduction,
                          "two adjacent consonants become one ('stop' becomes 'top')"),
    "final_devoicing": (_opp_final_devoicing, _app_final_devoicing,
                        "voicing is lost at the end of a word ('bag' becomes 'bak')"),
    "weak_syllable_deletion": (_opp_weak_syllable_deletion, _app_weak_syllable_deletion,
                               "an unstressed syllable disappears ('banana' becomes 'nana')"),
}


def process_analysis(phoneme_results):
    """Occurrence rate per process, each with its own denominator.

    Excused items (the accent allow-list matched) are removed BEFORE this runs.
    Epenthesis in Indian English is the clearest case: inserting a vowel to break
    up a cluster is systematic and correct, and letting it reach the process
    table would manufacture a phonological disorder out of an accent.
    """
    scored = [p for p in phoneme_results
              if not p.get("held") and p.get("error_type") != "excused"]
    out = {}
    for name, (opp_fn, app_fn, plain) in PROCESSES.items():
        n_opp = n_app = 0
        examples = []
        for p in scored:
            t = _base(p.get("target_arpabet"))
            a = _base(p.get("produced_arpabet"))
            ctx = {"position": p.get("position"),
                   "in_cluster": p.get("in_cluster", False),
                   "in_weak_syllable": p.get("in_weak_syllable", False)}
            if not opp_fn(t, ctx):
                continue
            n_opp += 1
            if p.get("error_type") in ("correct", "excused"):
                continue
            if app_fn(t, a, ctx):
                n_app += 1
                if len(examples) < 5:
                    examples.append({"word": p.get("word"), "target": t,
                                     "produced": a, "position": p.get("position")})
        r = rate(n_app, n_opp, None, name)
        r["plain_english"] = plain
        r["examples"] = examples
        out[name] = r
    return out


# =============================================================================
# 4. Consistency, the same word, three times
# =============================================================================
#
# The clearest example in the whole system of a measurement humans are bad at
# and machines are trivially good at. A clinician cannot reliably remember how
# a word came out on pass one by the time they hear pass three; a database can.
#
# Protocol: exactly three usable trials per word. A word with two usable trials
# leaves BOTH numerator and denominator, computing over eleven words instead of
# twenty-five produces a different figure, so the usable count is reported and
# not buried.


def consistency(trials_by_word):
    """`trials_by_word`: {word: [production_string, ...]}.

    Two productions count as distinct if their phone strings differ.
    Returns None when no word has exactly three usable trials, rather than
    returning a percentage computed over nothing.
    """
    eligible = {w: t for w, t in trials_by_word.items() if len(t) == 3}
    if not eligible:
        return None
    inconsistent, detail = [], []
    for w, trials in sorted(eligible.items()):
        distinct = list(dict.fromkeys(trials))  # order-preserving unique
        if len(distinct) > 1:
            inconsistent.append(w)
            detail.append({"word": w, "productions": trials, "n_distinct": len(distinct)})
    r = rate(len(inconsistent), len(eligible), "three trials in one sitting",
             "inconsistency")
    r["usable_words"] = len(eligible)
    r["words_submitted"] = len(trials_by_word)
    r["inconsistent_words"] = inconsistent
    r["detail"] = detail
    return r


# =============================================================================
# 5. Oral-motor rate and regularity (DDK)
# =============================================================================
#
# The one path in the whole system with no phoneme recognition in it at all,
# which is exactly why it is the most robust measurement Mira makes and the best
# candidate for unsupervised home capture. Onsets come from the amplitude
# envelope; nothing here needs a lexicon, an aligner or a model.
#
# Regularity is reported as a coefficient of variation rather than a raw
# standard deviation, so it is comparable across people who repeat at different
# speeds. Someone slow and even and someone fast and even should score alike.


def ddk_statistics(onset_times, window_seconds, expected_syllables=None):
    """Rate in syllables/second, plus interval regularity as a CV.

    Fewer than three onsets gives no intervals worth a CV, so regularity is
    returned as None with a stated reason rather than as a number computed from
    one interval.
    """
    if window_seconds <= 0:
        raise ValueError("window_seconds must be positive")
    n = len(onset_times)
    out = {"n_onsets": n, "window_seconds": window_seconds,
           "rate_syllables_per_sec": n / window_seconds,
           "regularity_cv": None, "note": None}
    if n < 3:
        out["note"] = "fewer than three onsets; interval regularity is undefined"
        return out
    ivs = [onset_times[i + 1] - onset_times[i] for i in range(n - 1)]
    mean = sum(ivs) / len(ivs)
    if mean <= 0:
        out["note"] = "non-increasing onset times; regularity undefined"
        return out
    var = sum((x - mean) ** 2 for x in ivs) / len(ivs)
    out["regularity_cv"] = math.sqrt(var) / mean
    out["mean_interval_s"] = mean
    if expected_syllables:
        out["completion"] = rate(n, expected_syllables, None, "syllables produced")
    return out


def ddk_sequence_accuracy(produced_triplets, expected="pa-ta-ka"):
    """Sequence accuracy for the three-syllable task only.

    This is the ONE part of the DDK path that touches recognition, because
    checking the ORDER requires knowing which syllable was which. Kept separate
    and labelled so the robust rate/regularity figures are not quietly
    contaminated by a recognition dependency.
    """
    exp = tuple(expected.split("-"))
    ok = sum(1 for t in produced_triplets if tuple(t) == exp)
    r = rate(ok, len(produced_triplets), "requires phone recognition", "sequence accuracy")
    r["depends_on_recognition"] = True
    return r


# =============================================================================
# 6. Stimulability
# =============================================================================
#
# Whether the person can produce a sound correctly when shown how, even though
# they do not produce it correctly on their own. Cheap to test, strongly
# predictive of how fast a sound will resolve, and routinely skipped in practice
# because a clinician has time to probe two or three sounds and not eleven.
#
# Supplying the full matrix for every error sound is a direct improvement to the
# quality of a decision the clinician still owns. That is the shape of every
# good feature in this product.

STIM_LEVELS = ["isolation", "syllable", "word"]


def stimulability_category(successes, total=3):
    if total != 3:
        raise ValueError("protocol specifies exactly three stimulability trials")
    if not 0 <= successes <= 3:
        raise ValueError(f"successes out of range: {successes}")
    if successes >= 2:
        return "stimulable"
    return "partially_stimulable" if successes == 1 else "not_stimulable"


def stimulability_matrix(trials):
    """`trials`: [{phone, level, success(bool), vowel_context(optional)}, ...]

    Vowel context is RETAINED under each syllable cell rather than averaged
    away, because stimulability is often context-dependent and a single frame
    will miss it, a child may manage /s/ before /i/ and not before /u/.
    """
    acc = defaultdict(lambda: {lv: {"n": 0, "ok": 0, "by_vowel": defaultdict(
        lambda: {"n": 0, "ok": 0})} for lv in STIM_LEVELS})
    for t in trials:
        lv = t.get("level")
        if lv not in STIM_LEVELS:
            continue
        cell = acc[t["phone"]][lv]
        cell["n"] += 1
        cell["ok"] += 1 if t.get("success") else 0
        vc = t.get("vowel_context")
        if vc:
            cell["by_vowel"][vc]["n"] += 1
            cell["by_vowel"][vc]["ok"] += 1 if t.get("success") else 0

    out = {}
    for phone, levels in sorted(acc.items()):
        out[phone] = {}
        for lv in STIM_LEVELS:
            c = levels[lv]
            if c["n"] == 0:
                out[phone][lv] = {"category": "not_administered", "n": 0}
                continue
            cat = (stimulability_category(c["ok"]) if c["n"] == 3
                   else ("stimulable" if c["ok"] / c["n"] >= 2 / 3 else
                         "partially_stimulable" if c["ok"] > 0 else "not_stimulable"))
            out[phone][lv] = {
                "category": cat,
                "fraction": f"{c['ok']}/{c['n']}",
                "n": c["n"], "ok": c["ok"],
                "by_vowel": {k: f"{v['ok']}/{v['n']}" for k, v in sorted(c["by_vowel"].items())},
            }
    return out


# =============================================================================
# 7. Deltas against the previous probe
# =============================================================================
#
# The recurring product. An intake battery is administered once per patient; a
# re-probe is administered every few weeks for the length of a course of
# therapy. A dated, objective, comparable progress chart is a retention
# instrument, and retention is worth considerably more to a clinic than twenty
# minutes saved at intake.
#
# The comparability check REFUSES across protocol versions rather than
# subtracting anyway. Two probes on different item lists are not a comparison,
# and a chart that silently plots them next to each other is worse than no
# chart, because it looks authoritative.


def deltas(current, previous, min_denominator=10):
    """Per-metric change between two analyses at the SAME protocol version."""
    if current.get("protocol_version") != previous.get("protocol_version"):
        return {"comparable": False,
                "reason": (f"protocol version changed "
                           f"{previous.get('protocol_version')} -> "
                           f"{current.get('protocol_version')}; these probes are "
                           f"not comparable and must not be plotted on one line")}
    out = {"comparable": True, "metrics": {}}
    for key in ("pcc", "pcc_r", "pvc"):
        a, b = current.get(key), previous.get(key)
        if not a or not b or not a["reportable"] or not b["reportable"]:
            continue
        # A change computed off a tiny denominator is noise wearing a number as
        # a costume. Flag it rather than plotting it as movement.
        thin = min(a["d"], b["d"]) < min_denominator
        out["metrics"][key] = {
            "now": a["pct"], "before": b["pct"], "delta": a["pct"] - b["pct"],
            "n_now": a["d"], "n_before": b["d"],
            "low_confidence": thin,
            "note": "denominator below threshold; treat as indicative only" if thin else None,
        }
    return out


def no_change_flag(history, target_phone, noise_band=3.0, n_probes=3):
    """The highest-value output of the entire system.

    Fires when a treated target has not moved beyond the noise band across three
    consecutive probes. This catches the failure that otherwise takes months to
    become visible, a therapy approach that is not working, and it is the flag
    that prompts a clinician to reconsider, which is a decision only they can make.
    """
    pts = [h for h in history if h.get("phone") == target_phone]
    if len(pts) < n_probes:
        return None
    recent = pts[-n_probes:]
    vals = [p["accuracy_pct"] for p in recent]
    if max(vals) - min(vals) <= noise_band:
        return {
            "flag": "no_change_on_treated_target",
            "phone": target_phone,
            "from_date": recent[0].get("date"),
            "to_date": recent[-1].get("date"),
            "values": vals,
            "text": (f"No measurable change on /{target_phone}/ across "
                     f"{n_probes} probes between {recent[0].get('date')} and "
                     f"{recent[-1].get('date')}."),
        }
    return None


# =============================================================================
# 8. The flag rules, in full
# =============================================================================
#
# Fixed thresholds. No inference, no learned classifier, and NO CONDITION NAMES.
# Every flag is phrased as an observation plus a request for clinician attention.
#
# Read `high_inconsistency` and `oral_motor_outside_reference` together and note
# what is NOT here: both are, in clinical practice, part of the picture that
# raises a question about motor speech. The temptation to write one more
# sentence connecting them will be constant, and it will come from clinicians
# who would find that sentence useful. It stays unwritten. The moment the system
# names a condition it stops being decision support.

FLAG_THRESHOLDS = {
    "min_coverage_pct": 80.0,
    "inconsistency_cut_pct": 40.0,
    "min_inconsistency_words": 15,
    "high_excusal_pct": 25.0,
    "min_adherence_pct": 50.0,
}


def build_flags(analysis, thresholds=None):
    """Every flag is an observation plus a request for attention. Never a finding."""
    th = dict(FLAG_THRESHOLDS)
    if thresholds:
        th.update(thresholds)
    flags = []

    cov = analysis.get("accuracy", {}).get("coverage")
    if cov and cov["reportable"] and cov["pct"] < th["min_coverage_pct"]:
        flags.append({"flag": "low_coverage", "severity": "info",
                      "text": (f"Metrics below are computed from {cov['n']} of "
                               f"{cov['d']} intended items. Interpret accordingly.")})

    if analysis.get("hearing_status") in (None, "not_assessed"):
        flags.append({"flag": "hearing_status_unresolved", "severity": "info",
                      "text": ("Hearing status is not recorded. Speech sound "
                               "findings should be interpreted with this in mind.")})

    inc = analysis.get("consistency")
    if (inc and inc["reportable"] and inc["usable_words"] >= th["min_inconsistency_words"]
            and inc["pct"] > th["inconsistency_cut_pct"]):
        flags.append({"flag": "high_inconsistency", "severity": "review",
                      "text": (f"Productions varied across repeated trials on "
                               f"{inc['n']} of {inc['d']} words. This pattern "
                               f"warrants clinician review.")})

    ddk = analysis.get("ddk")
    ref = analysis.get("ddk_reference")
    if ddk and ref and ddk.get("rate_syllables_per_sec") is not None:
        r = ddk["rate_syllables_per_sec"]
        if r < ref["low"] or r > ref["high"]:
            flags.append({"flag": "oral_motor_outside_reference", "severity": "review",
                          "text": (f"Repetition rate was {r:.1f} syllables per second "
                                   f"against a reference range of {ref['low']} to "
                                   f"{ref['high']} for this age band.")})

    for nc in analysis.get("no_change_flags", []) or []:
        flags.append({"flag": nc["flag"], "severity": "review", "text": nc["text"]})

    adh = analysis.get("adherence")
    if adh and adh["reportable"] and adh["pct"] < th["min_adherence_pct"]:
        flags.append({"flag": "low_adherence", "severity": "info",
                      "text": f"Practice completed on {adh['n']} of {adh['d']} prescribed days."})

    exc = analysis.get("excusal")
    if exc and exc["reportable"] and exc["pct"] > th["high_excusal_pct"]:
        flags.append({"flag": "high_excusal_rate", "severity": "info",
                      "text": (f"{exc['n']} items matched documented regional "
                               f"pronunciation variants and were scored as correct. "
                               f"The list is available for review.")})

    if analysis.get("out_of_scope"):
        flags.append({"flag": "out_of_treated_scope", "severity": "info",
                      "text": ("This report covers speech sound production only. It "
                               "does not assess fluency, voice, language or acquired "
                               "neurological communication disorders.")})
    return flags


# =============================================================================
# 9. The prohibition list, as data
# =============================================================================


def module2_prohibitions():
    """Stated as data so a test can assert against it, rather than living only in
    a design document that nobody re-reads six months later."""
    return {
        "select_a_therapy_approach": "the most consequential decision in a case; clinician's",
        "select_a_target_sound": "depends on stimulability, intelligibility impact, "
                                 "generalisation potential and family circumstances",
        "write_placement_instructions": "a physical instruction without clinical "
                                        "judgement of oral structure is treatment",
        "state_a_diagnosis": "a regulated professional act",
        "state_severity_as_a_verdict": "the figure and the band are facts; the verdict "
                                       "is a clinical judgement wearing a number as a costume",
        "estimate_duration_of_therapy": "clinician's judgement and the basis of their fee",
        "explain_why_progress_stalled": "adherence, approach, target choice, hearing, "
                                        "motivation and family circumstances all produce "
                                        "the same flat line",
    }


# =============================================================================
# 10. Self-test, constructed inputs with known answers
# =============================================================================


def self_test(verbose=True):
    n = 0

    def ck(cond, msg):
        nonlocal n
        assert cond, msg
        n += 1

    # --- rate ---------------------------------------------------------------
    r = rate(3, 4, "single_word", "PCC")
    ck(r["pct"] == 75.0 and r["n"] == 3 and r["d"] == 4, "rate arithmetic")
    ck(rate(0, 0)["pct"] is None, "zero denominator must not become zero percent")
    ck(rate(0, 0)["reportable"] is False, "zero denominator is not reportable")
    ck("3 of 4" in fmt_rate(r), "fmt_rate must print the denominator")

    # --- accuracy -----------------------------------------------------------
    rows = [
        {"target_arpabet": "S", "error_type": "substitution", "held": False},
        {"target_arpabet": "T", "error_type": "correct", "held": False},
        {"target_arpabet": "K", "error_type": "distortion", "held": False},
        {"target_arpabet": "AE1", "error_type": "correct", "held": False},
        {"target_arpabet": "R", "error_type": None, "held": True, "held_reason": "low_snr"},
    ]
    m = accuracy_metrics(rows)
    # three scored consonants; PCC counts distortion as an error -> 1 of 3
    ck(m["pcc"]["n"] == 1 and m["pcc"]["d"] == 3, "PCC counts distortions as errors")
    # PCC-R forgives the distortion -> 2 of 3
    ck(m["pcc_r"]["n"] == 2 and m["pcc_r"]["d"] == 3, "PCC-R forgives distortions")
    ck(abs(m["distortion_load_pct"] - (200 / 3 - 100 / 3)) < 1e-9, "distortion load is the gap")
    ck(m["pvc"]["n"] == 1 and m["pvc"]["d"] == 1, "vowels counted separately")
    ck(m["coverage"]["n"] == 4 and m["coverage"]["d"] == 5, "held items leave the denominator")
    ck(m["n_held"] == 1 and m["held_reasons"] == {"low_snr": 1}, "held reasons retained")

    # a held item must never be counted as an error
    all_held = accuracy_metrics([{"target_arpabet": "S", "held": True}])
    ck(all_held["pcc"]["reportable"] is False, "all-held must not report 0% PCC")

    # --- inventory grid -----------------------------------------------------
    g = inventory_grid([
        {"target_arpabet": "S", "position": "initial", "error_type": "substitution",
         "produced_arpabet": "T", "held": False},
        {"target_arpabet": "S", "position": "final", "error_type": "correct", "held": False},
    ])
    ck(g["S"]["initial"]["produced"]["T"] == 1, "grid records the substitute identity")
    ck(g["S"]["medial"] is None, "unadministered cells stay None, not zero")
    ck("not administered" in str(grid_to_rows(g)), "unadministered is printed as such")

    # an unconfident substitute identity must not be recorded as fact
    g2 = inventory_grid([{"target_arpabet": "S", "position": "initial",
                          "error_type": "substitution", "produced_arpabet": "T",
                          "produced_confident": False, "held": False}])
    ck(len(g2["S"]["initial"]["produced"]) == 0, "uncertain substitute identity is not asserted")

    # --- processes ----------------------------------------------------------
    pa = process_analysis([
        {"target_arpabet": "K", "produced_arpabet": "T", "error_type": "substitution",
         "position": "initial", "word": "key", "held": False},
        {"target_arpabet": "G", "produced_arpabet": "D", "error_type": "substitution",
         "position": "initial", "word": "go", "held": False},
        {"target_arpabet": "K", "produced_arpabet": "K", "error_type": "correct",
         "position": "final", "word": "back", "held": False},
    ])
    ck(pa["fronting"]["n"] == 2 and pa["fronting"]["d"] == 3, "fronting rate is 2 of 3")
    ck(pa["stopping"]["reportable"] is False, "no fricative targets means no stopping opportunity")

    # excused items must never reach the process table
    pa2 = process_analysis([
        {"target_arpabet": "K", "produced_arpabet": "T", "error_type": "excused",
         "position": "initial", "held": False}])
    ck(pa2["fronting"]["n"] == 0, "accent-excused items do not count as process applications")

    # --- consistency --------------------------------------------------------
    c = consistency({"ship": ["SIp", "SIp", "SIp"], "sun": ["tVn", "sVn", "tVn"]})
    ck(c["n"] == 1 and c["d"] == 2 and c["pct"] == 50.0, "inconsistency is 1 of 2")
    ck(consistency({"a": ["x", "x"]}) is None, "two trials is not the protocol")
    ck(consistency({}) is None, "no words means no figure, not zero percent")
    c2 = consistency({"a": ["x", "x", "x"], "b": ["p", "q", "p"], "c": ["z", "z"]})
    ck(c2["usable_words"] == 2 and c2["words_submitted"] == 3, "usable count is reported")

    # --- DDK ----------------------------------------------------------------
    d = ddk_statistics([0.0, 0.25, 0.50, 0.75], 1.0)
    ck(d["rate_syllables_per_sec"] == 4.0, "DDK rate")
    ck(abs(d["regularity_cv"]) < 1e-9, "perfectly even repetition has CV 0")
    ck(ddk_statistics([0.0, 0.3], 1.0)["regularity_cv"] is None, "two onsets, no CV")
    ck(ddk_statistics([0.0, 0.3], 1.0)["note"] is not None, "and it says why")
    try:
        ddk_statistics([0.0], 0)
        ck(False, "zero window should raise")
    except ValueError:
        ck(True, "zero window raises")
    sa = ddk_sequence_accuracy([("pa", "ta", "ka"), ("pa", "ka", "ta")])
    ck(sa["n"] == 1 and sa["depends_on_recognition"] is True, "sequence accuracy flags its dependency")

    # --- stimulability ------------------------------------------------------
    ck(stimulability_category(3) == stimulability_category(2) == "stimulable", "2 of 3 is stimulable")
    ck(stimulability_category(1) == "partially_stimulable", "1 of 3")
    ck(stimulability_category(0) == "not_stimulable", "0 of 3")
    for bad in [(4, 3), (-1, 3), (2, 5)]:
        try:
            stimulability_category(*bad)
            ck(False, "should refuse out-of-protocol input")
        except ValueError:
            ck(True, "refuses out-of-protocol input")
    sm = stimulability_matrix([
        {"phone": "S", "level": "syllable", "success": True, "vowel_context": "i"},
        {"phone": "S", "level": "syllable", "success": False, "vowel_context": "u"},
        {"phone": "S", "level": "syllable", "success": True, "vowel_context": "i"},
    ])
    ck(sm["S"]["syllable"]["by_vowel"]["i"] == "2/2", "vowel context is retained, not averaged")
    ck(sm["S"]["word"]["category"] == "not_administered", "unadministered level says so")

    # --- deltas -------------------------------------------------------------
    cur = {"protocol_version": "3.1.0", "pcc": rate(40, 50), "pcc_r": rate(45, 50)}
    prv = {"protocol_version": "3.1.0", "pcc": rate(30, 50), "pcc_r": rate(38, 50)}
    dd = deltas(cur, prv)
    ck(dd["comparable"] and abs(dd["metrics"]["pcc"]["delta"] - 20.0) < 1e-9, "delta arithmetic")
    bad = deltas({"protocol_version": "3.2.0", "pcc": rate(40, 50)}, prv)
    ck(bad["comparable"] is False, "must refuse to compare across protocol versions")
    thin = deltas({"protocol_version": "v", "pcc": rate(4, 5)},
                  {"protocol_version": "v", "pcc": rate(3, 5)})
    ck(thin["metrics"]["pcc"]["low_confidence"] is True, "thin denominators are flagged")

    # --- no-change flag -----------------------------------------------------
    hist = [{"phone": "R", "accuracy_pct": 40.0, "date": "2026-01-01"},
            {"phone": "R", "accuracy_pct": 41.0, "date": "2026-02-01"},
            {"phone": "R", "accuracy_pct": 42.0, "date": "2026-03-01"}]
    nc = no_change_flag(hist, "R")
    ck(nc is not None and nc["flag"] == "no_change_on_treated_target", "flat line fires")
    moving = [dict(h, accuracy_pct=v) for h, v in zip(hist, [40.0, 55.0, 70.0])]
    ck(no_change_flag(moving, "R") is None, "real movement does not fire")
    ck(no_change_flag(hist[:2], "R") is None, "two probes is not three")

    # --- flags --------------------------------------------------------------
    fl = build_flags({"accuracy": {"coverage": rate(5, 10)}, "hearing_status": None})
    names = {f["flag"] for f in fl}
    ck("low_coverage" in names and "hearing_status_unresolved" in names, "flags fire")
    for f in fl:
        low = f["text"].lower()
        ck(not any(w in low for w in ("apraxia", "dysarthria", "disorder", "diagnos")),
           "no flag text may name a condition")

    # --- prohibitions -------------------------------------------------------
    pr = module2_prohibitions()
    ck("state_a_diagnosis" in pr and "select_a_therapy_approach" in pr,
       "prohibition list is present as data")

    if verbose:
        print(f"mira_module2a {MODULE2A_VERSION}: {n} assertions passed")
    return n


if __name__ == "__main__":
    self_test()