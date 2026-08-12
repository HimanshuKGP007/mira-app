"""mira_app/session.py - the join between Module 1 and Module 2.

Module 2A was written first, written well, and unreachable. Every function in it
reads a record shaped like this:

    {"target_arpabet": "S", "produced_arpabet": "T", "error_type": "substitution",
     "position": "initial", "word": "sun", "held": False}

and Module 1 emitted no produced phone and no error type. So Module 2A was
complete, 46 assertions passing, and connected to nothing. That is the expensive
kind of gap: nothing is broken and nothing works.

This module closes it. Two mismatches have to be resolved and both are real.

ALPHABET. Module 1 works in IPA because the acoustic model does. Module 2A works
in ARPABET because the clinical literature and the phonological process tables do.
Where the conversion fails the item is HELD, never guessed, because a process
analysis that silently drops what it could not convert reports a lower process
rate than the truth and reads as clinical improvement.

HELD ITEMS. A sound that failed a gate has no error type and must not count as
correct. Module 2A takes held=True and excludes it from every numerator and every
denominator, then reports the count as coverage. A report saying "we could not
score fourteen of these" is more trustworthy than one that does not mention them.

THE SPLIT THAT MAKES THIS SAFE
------------------------------
Module 2A computes. Module 2B writes sentences. Every clinical figure in the
report comes out of ordinary code, is unit-testable, and is reproducible by
rerunning the same function on the same input. The language model is downstream of
all of it and cannot change a number. Deleting Module 2B entirely still leaves a
report a clinician can read, and that is the test of whether the separation is
real.
"""

from collections import Counter

from . import mira_core
from . import mira_module2a as m2a
from . import mira_module2b as m2b
from . import protocol as proto

# Inverse of the canonical table, built once. Refused rather than guessed when a
# symbol has no entry: a wrong ARPABET here silently changes which phonological
# process a substitution counts as.
IPA_TO_ARPABET = {}
for _arp, _ipa in mira_core.ARPABET_TO_IPA.items():
    IPA_TO_ARPABET.setdefault(mira_core.normalize_ipa(_ipa) or _ipa,
                              mira_core.arpabet_base(_arp))


def to_arpabet(sym):
    """IPA or ARPABET in, ARPABET out, or None when it cannot be resolved.

    Does NOT fall through to the raw symbol. Module 2A would then compare an IPA
    string against an ARPABET table, find no match, and record a substitution that
    never happened.
    """
    if sym is None:
        return None
    s = str(sym).strip()
    if not s:
        return None
    # ARPABET is upper-case letters with an optional trailing stress digit.
    # Testing `s.isalpha()` alone silently fails every stressed vowel, because
    # "AE1" contains a digit, and the whole vowel inventory then arrives at
    # Module 2A as unconvertible and gets held. That looked like a coverage
    # problem and was a one-character predicate bug.
    base = "".join(c for c in s if not c.isdigit())
    if base and base.isalpha() and base.upper() == base:
        return mira_core.arpabet_base(s)
    return IPA_TO_ARPABET.get(mira_core.normalize_ipa(s) or s)


def response_to_records(response):
    """One Module 1 response to the record list Module 2A consumes."""
    recs = []
    word = response.get("prompt_word")
    item = response.get("item", {})
    positions = item.get("positions") or []
    clusters = item.get("in_cluster") or []
    phones = response.get("phones", [])

    if not phones and response.get("status") == "held":
        # A whole item that never got scored. It still has to reach Module 2A,
        # as held rows, or the coverage figure will not know it was attempted.
        reason = (response.get("quality_gate", {}).get("reason")
                  or "the recording did not clear the gates")
        for i, arp in enumerate(item.get("phones", []) or []):
            recs.append({"target_arpabet": to_arpabet(arp), "produced_arpabet": None,
                         "error_type": "held", "held": True, "held_reason": reason,
                         "position": positions[i] if i < len(positions) else None,
                         "in_cluster": clusters[i] if i < len(clusters) else False,
                         "word": word})
        return recs

    for i, ph in enumerate(phones):
        tgt = to_arpabet(ph.get("target"))
        prod = to_arpabet(ph.get("produced"))
        held = (ph.get("score") is None) or (ph.get("flag") in ("held", "not_scored"))
        reason = ph.get("reason") or ph.get("error_why")

        if tgt is None:
            held = True
            reason = (f"target {ph.get('target')!r} has no ARPABET equivalent, so "
                      f"it cannot enter the clinical tables")
        if (not held and ph.get("produced") is not None and prod is None
                and ph.get("produced_confident")):
            # The decode named a substitute that does not map. Holding is honest:
            # "a sound we cannot name" is a finding, and discarding it would
            # understate the error rate.
            held = True
            reason = (f"produced {ph.get('produced')!r} has no ARPABET equivalent; "
                      f"the substitution cannot be typed")

        recs.append({
            "target_arpabet": tgt,
            "produced_arpabet": prod,
            "error_type": "held" if held else (ph.get("error_type") or "correct"),
            "held": bool(held),
            "held_reason": reason if held else None,
            "position": ph.get("position") or (positions[i] if i < len(positions) else None),
            "in_cluster": clusters[i] if i < len(clusters) else False,
            "word": word,
            "start_s": ph.get("start_s"), "end_s": ph.get("end_s"),
            "confidence": ph.get("confidence"),
            "excused_by": ph.get("excused_by"),
            "score": ph.get("score"),
        })
    return recs


def analyse(responses, speaker=None, uncalibrated=True):
    """Every Module 2A computation over a whole session.

    Returns the analysis object Module 2B is allowed to read. Note what it does
    NOT contain: no audio, no goodness figures, no reference material, no history
    beyond computed deltas. That restriction is what makes the narration layer
    unable to invent a clinical claim.
    """
    records = []
    for r in responses:
        records.extend(response_to_records(r))

    trials = {}
    for r in responses:
        trials.setdefault(r.get("prompt_word"), []).append(
            "".join(str(p.get("produced") or "-")
                    for p in r.get("phones", [])))

    analysis = {
        "protocol": {"id": proto.PROTOCOL_ID, "version": proto.PROTOCOL_VERSION},
        "speaker": speaker or {},
        "hearing_status": (speaker or {}).get("hearing_status", "not_assessed"),
        "n_items": len(responses),
        "n_phonemes": len(records),
        "accuracy": m2a.accuracy_metrics(records, context="single_word"),
        "inventory": m2a.inventory_grid(records),
        "processes": m2a.process_analysis(records),
        "errors": dict(Counter(r["error_type"] for r in records)),
        # Consistency needs genuine repeat trials. With one trial per word it
        # reports nothing rather than reporting 100 percent, which would be a
        # measurement of the protocol rather than of the speaker.
        "consistency": (m2a.consistency({w: v for w, v in trials.items() if len(v) >= 3})
                        if any(len(v) >= 3 for v in trials.values()) else None),
        "uncalibrated": bool(uncalibrated),
    }
    analysis["flags"] = m2a.build_flags(analysis)
    if uncalibrated:
        analysis["flags"].insert(0, {
            "flag": "uncalibrated_preview",
            "severity": "review",
            "text": ("These figures come from an uncalibrated preview scorer, not "
                     "the validated model. They demonstrate the pipeline and must "
                     "not be used for any clinical purpose."),
        })
    analysis["records"] = records
    return analysis


# =============================================================================
# Module 2B, the narration layer
# =============================================================================
# It may only restate what Module 2A computed. Two narrators ship.
#
# TemplateNarrator fills sentences from the analysis object. It has no model
# behind it, cannot invent, and passes the verifier by construction. It is the
# default because it makes the language model optional, and optional is what
# makes it safe.
#
# LLMNarrator takes any callable that maps a prompt to text. Whatever it produces
# goes through the same verifier, and if too many sentences fail the whole
# narrative is discarded and the report falls back to the tables. The tables on
# their own are a complete report; the narration is a readability layer.


class TemplateNarrator:
    def __call__(self, request):
        a = request["analysis"]
        acc = a["accuracy"]
        care = request["register"] == "caregiver"
        out = []

        cov = acc["coverage"]
        if cov["reportable"]:
            out.append(f"{cov['n']} of {cov['d']} sounds were measured.")
        if acc["pcc"]["reportable"]:
            word = "correct" if care else "correct"
            out.append(f"Consonants {word}: {acc['pcc']['pct']:.1f} percent, "
                       f"{acc['pcc']['n']} of {acc['pcc']['d']}.")
        if acc["pvc"]["reportable"]:
            out.append(f"Vowels correct: {acc['pvc']['pct']:.1f} percent, "
                       f"{acc['pvc']['n']} of {acc['pvc']['d']}.")

        applied = {k: v for k, v in a["processes"].items()
                   if isinstance(v, dict) and (v.get("n") or 0) > 0}
        for name, v in sorted(applied.items(), key=lambda kv: -kv[1]["n"])[:4]:
            out.append(f"{name.replace('_', ' ').capitalize()} occurred on "
                       f"{v['n']} of {v['d']} opportunities.")
        if not applied:
            out.append("No phonological process reached its threshold.")
        if acc["n_held"]:
            out.append(f"{acc['n_held']} sounds were held and not scored.")
        return " ".join(out)


class LLMNarrator:
    """Wraps any text generator. `generate(prompt) -> str`."""

    def __init__(self, generate):
        self.generate = generate

    def __call__(self, request):
        a = request["analysis"]
        lines = [
            "You restate computed figures in fluent prose. Nothing else.",
            *request["instructions"],
            "",
            "FIGURES YOU MAY USE:",
            f"coverage: {a['accuracy']['coverage']['n']} of "
            f"{a['accuracy']['coverage']['d']}",
            f"consonant accuracy: {a['accuracy']['pcc']['pct']} percent "
            f"({a['accuracy']['pcc']['n']} of {a['accuracy']['pcc']['d']})",
            f"vowel accuracy: {a['accuracy']['pvc']['pct']} percent",
            f"held: {a['accuracy']['n_held']}",
        ]
        for k, v in a["processes"].items():
            if isinstance(v, dict) and (v.get("n") or 0) > 0:
                lines.append(f"{k}: {v['n']} of {v['d']}")
        return self.generate("\n".join(lines))


def narrate(analysis, register="clinician", narrator=None):
    """Generate, then verify, then fail closed.

    The verifier drops any sentence containing a number that is not in the
    analysis, or a word from the forbidden vocabulary. If fewer than 70 percent
    of sentences survive, the whole narrative is discarded and the caller prints
    the tables instead.
    """
    narrator = narrator or TemplateNarrator()
    request = m2b.build_narration_request(analysis, register=register)
    # The analysis handed to a narrator must not carry the raw record list: it is
    # per-sound detail with timings and confidences, none of which a narration
    # layer has any business seeing.
    request["analysis"] = {k: v for k, v in analysis.items() if k != "records"}
    text = narrator(request)
    verdict = m2b.verify_narrative(text, request["analysis"])
    verdict["register"] = register
    verdict["narrator"] = type(narrator).__name__
    verdict["raw"] = text
    return verdict
