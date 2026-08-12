"""mira_serve/contracts.py, the shapes that cross every boundary, and the gates.

WHY THIS FILE EXISTS SEPARATELY FROM THE MODEL CODE
---------------------------------------------------
A contract is an agreed shape for data moving between two pieces of software.
In a clinical instrument it is also WHERE THE SAFETY PROPERTIES LIVE, because a
gate only works if the signal it depends on survives every handover intact.

Keeping the contracts and the gates in a file that imports neither torch nor
transformers has one concrete payoff: the safety logic can be unit-tested in a
second on any machine, including in CI, without a GPU and without downloading a
2 GB checkpoint. The rules that decide whether Mira is allowed to speak should
not be the least-tested code in the system, and that is exactly what happens
when they are tangled up with the model.

THE THREE PROMISES EVERY RESPONSE KEEPS
---------------------------------------
1. Every sound carries EITHER a score OR a stated reason it has none. Silence
   is never the answer; "not scored, and here is why" is.
2. Provenance travels with the result. A number must never be quotable later
   without knowing which model, aligner, threshold set and protocol produced it.
3. There is no field for a diagnosis, a severity or a plan. The schema cannot
   express them, which is a stronger guarantee than a policy saying it shouldn't.

Standard library only.
"""

CONTRACTS_VERSION = "1.0.0"

from dataclasses import dataclass, field, asdict
from typing import Optional


# =============================================================================
# 1. The safety gate
# =============================================================================
#
# Four checks decide whether Mira may say anything at all about a recording.
# They run BEFORE scoring, not after, because the cheapest failure is the one
# that never reaches the model.
#
# A FAILED GATE MEANS "HOLD", NOT "SILENCE". This is the inversion that separates
# the clinical product from the consumer one. Previously a failed gate produced
# nothing, because there was no qualified person to hand uncertainty to. Now
# uncertainty is routed to the person whose job it is to resolve it, coverage
# becomes a headline figure, and a report that says "we could not score fourteen
# of these" is more trustworthy than one that quietly does not mention them.

GATE_DEFAULTS = {
    # Below roughly 12 dB the room is competing with the speaker, and background
    # hiss gets measured as breathiness. This is the cheapest gate and it
    # prevents the most misleading failure.
    "min_snr_db": 12.0,
    # The most important safety field in the system. A forced aligner is never
    # allowed to answer "none of these", it returns confident-looking
    # boundaries even when the person said a completely different word. Every
    # per-sound measurement sits on top of these boundaries, so if they are
    # guesses, everything above them is a guess wearing a decimal point.
    "min_alignment_quality": 0.70,
    # Per-phoneme, not per-item, so one uncertain sound does not discard four
    # good ones sitting beside it.
    "min_confidence": 0.60,
    # A phone window shorter than this has too few frames to measure anything
    # stable. Kept identical to the training-time filter so serving and training
    # see the same population of windows.
    "min_duration_ms": 30.0,
    # Stricter at home, where nobody qualified is present, the room is unknown
    # and a caregiver may have prompted the child without recording that they did.
    "home_capture_multiplier": 1.15,
}


@dataclass
class GateResult:
    passed: bool
    failures: list = field(default_factory=list)
    measurements: dict = field(default_factory=dict)

    def as_dict(self):
        return asdict(self)


def check_recording_gates(snr_db, alignment_quality, capture_context="clinic",
                          thresholds=None):
    """Utterance-level gates. Returns every failure, not just the first.

    Reporting all failures at once matters operationally: a caregiver told
    "too noisy" who fixes the room and is then told "we could not hear the word"
    will not attempt a third recording.
    """
    th = dict(GATE_DEFAULTS)
    if thresholds:
        th.update(thresholds)
    mult = th["home_capture_multiplier"] if capture_context == "home" else 1.0

    min_snr = th["min_snr_db"] * mult
    min_align = min(th["min_alignment_quality"] * mult, 0.95)

    failures = []
    if snr_db is None or snr_db < min_snr:
        failures.append({
            "gate": "recording_quality", "measured": snr_db, "required": min_snr,
            "action": "request_retake",
            "reason": "the recording is too noisy to measure reliably",
        })
    if alignment_quality is None or alignment_quality < min_align:
        failures.append({
            "gate": "alignment_quality", "measured": alignment_quality,
            "required": min_align, "action": "hold_for_review",
            # Suppressed rather than shown with a caveat: a caveat printed next
            # to a precise-looking number does not survive being read quickly.
            "reason": "sound boundaries could not be placed reliably, so the "
                      "per-sound measurements are suppressed rather than shown "
                      "with a caveat",
        })
    return GateResult(passed=not failures, failures=failures,
                      measurements={"snr_db": snr_db,
                                    "alignment_quality": alignment_quality,
                                    "capture_context": capture_context,
                                    "thresholds_applied": {"min_snr_db": min_snr,
                                                           "min_alignment_quality": min_align}})


def check_word_identity(decoded_string, expected_string, min_similarity=0.45):
    """The gate that stops one wrong word becoming five consecutive errors.

    If someone was prompted "rabbit" and said "carrot", forced alignment will
    still return five confident boundaries and the scorer will mark five errors.
    That is not a pronunciation finding, it is a different word, and recording
    it as five errors is a fabrication that will end up in a clinical document.
    """
    if not decoded_string or not expected_string:
        return GateResult(True, [], {"similarity": None,
                                     "note": "no decode available to compare"})
    a, b = set(str(decoded_string)), set(str(expected_string))
    sim = len(a & b) / max(len(a | b), 1)
    if sim < min_similarity:
        return GateResult(False, [{
            "gate": "word_identity", "measured": round(sim, 3),
            "required": min_similarity, "action": "hold_for_review",
            "reason": "what was heard differs strongly from the prompted word; "
                      "the speaker probably said something else",
        }], {"similarity": round(sim, 3)})
    return GateResult(True, [], {"similarity": round(sim, 3)})


# =============================================================================
# 2. The withholding policy
# =============================================================================
#
# Stage 2 measured per-phoneme error and found roughly a factor of four between
# the best and worst sounds. Reporting them all at one confidence throws away
# information already sitting in the export.
#
# The point is not accuracy, it is CALIBRATION AS A PRODUCT PROPERTY:
#   - a tool that quietly gets /ʃ/ wrong is UNRELIABLE
#   - a tool that says "I do not score /ʃ/ well enough to judge it" is CALIBRATED
# A professional trusts the rest of the output MORE because of the omission.
#
# The trade-off is set on purpose against a coverage floor, so that a policy
# withholding half the sounds is rejected as useless rather than shipped as
# cautious.


class WithholdingPolicy:
    """Per-phoneme decision: score it, or return `not_scored` with a reason."""

    def __init__(self, withheld_phonemes=None, mae_by_phoneme=None,
                 mae_ceiling=0.25, min_n=50, coverage_floor=0.75):
        self.withheld = set(withheld_phonemes or [])
        self.mae = dict(mae_by_phoneme or {})
        self.mae_ceiling = mae_ceiling
        self.min_n = min_n
        self.coverage_floor = coverage_floor

    @classmethod
    def from_error_table(cls, rows, mae_key="mae", n_key="n", phone_key="phone",
                         mae_ceiling=0.25, min_n=50, coverage_floor=0.75):
        """Build from Stage 2's `error_by_phoneme.csv`, as a list of dicts.

        Two independent reasons to withhold, and they are different failures:
          - the model is measurably bad on this sound (MAE above the ceiling)
          - there was never enough data to know whether it is good or bad (n < min_n)
        The second is not a milder version of the first. Both must be stated.
        """
        withheld, mae, total, held = set(), {}, 0, 0
        for r in rows:
            p = r.get(phone_key)
            m = r.get(mae_key)
            n = r.get(n_key, 0) or 0
            total += n
            if p is None:
                continue
            if m is not None:
                mae[p] = m
            if (m is not None and m > mae_ceiling) or n < min_n:
                withheld.add(p)
                held += n
        pol = cls(withheld, mae, mae_ceiling, min_n, coverage_floor)
        pol.coverage = 1 - (held / total) if total else None
        # A policy that scores less than the floor is honest AND useless. Better
        # to know that at build time than to discover it on a clinician's screen.
        pol.meets_coverage_floor = (pol.coverage is None) or (pol.coverage >= coverage_floor)
        return pol

    def decide(self, phoneme, confidence=None, min_confidence=0.60):
        """Returns (scored: bool, reason: str|None). The reason is written for a
        human reader, because it is printed on the report."""
        if phoneme in self.withheld:
            m = self.mae.get(phoneme)
            detail = f" (measured error {m:.2f})" if isinstance(m, (int, float)) else ""
            return False, f"not measured reliably enough to judge{detail}"
        if confidence is not None and confidence < min_confidence:
            return False, "measurement confidence below the reporting threshold"
        return True, None


# =============================================================================
# 3. The response contract
# =============================================================================


@dataclass
class PhoneResult:
    """One sound. Either `score` is set, or `reason` explains why it is not.

    Note what has no field here: severity, diagnosis, recommendation, prognosis.
    The schema cannot express them.
    """
    target: str
    position: Optional[str] = None
    score: Optional[float] = None
    confidence: Optional[float] = None
    flag: str = "ok"                  # ok | review | not_scored | held | excused
    reason: Optional[str] = None
    produced: Optional[str] = None    # what was heard instead, when confident
    produced_confident: bool = True
    correlates: dict = field(default_factory=dict)
    start_s: Optional[float] = None
    end_s: Optional[float] = None
    # --- added with the free decode ---------------------------------------
    # `error_type` is a CATEGORY, not a claim: substitution, omission,
    # assimilation and the rest are descriptions of what happened acoustically.
    # None of them is a diagnosis, and assert_no_clinical_claims below still
    # refuses any field that is. `error_why` carries the reason, because a label
    # a clinician cannot argue with is a label they cannot use.
    error_type: Optional[str] = None
    error_why: Optional[str] = None
    excused_by: Optional[str] = None   # the allow-list rule id, when one matched
    fusion: dict = field(default_factory=dict)

    def __post_init__(self):
        # Promise 1, enforced structurally rather than by convention: a sound
        # with no score must carry a reason, and a scored sound must not claim
        # to be unscored.
        if self.score is None and self.flag not in ("not_scored", "held"):
            raise ValueError(f"/{self.target}/ has no score but flag is '{self.flag}'")
        if self.score is None and not self.reason:
            raise ValueError(f"/{self.target}/ has no score and no reason; "
                             f"every sound carries one or the other")
        if self.score is not None and self.flag in ("not_scored", "held"):
            raise ValueError(f"/{self.target}/ is flagged '{self.flag}' but carries a score")


REQUIRED_PROVENANCE = ("model_version", "aligner_version",
                       "protocol_version", "threshold_set_version",
                       "core_sha256", "bundle_version")


def stamp_provenance(record, versions):
    """Promise 2. An unauditable clinical record is worse than a missing one,
    so this refuses rather than filling a blank with 'unknown'."""
    missing = [k for k in REQUIRED_PROVENANCE if not versions.get(k)]
    if missing:
        raise ValueError(f"incomplete provenance, missing: {missing}")
    out = dict(record)
    out["provenance"] = {k: versions[k] for k in REQUIRED_PROVENANCE}
    return out


FORBIDDEN_RESPONSE_FIELDS = {
    "diagnosis", "severity", "condition", "prognosis", "treatment",
    "therapy_plan", "recommendation", "duration_estimate", "disorder",
}


def assert_no_clinical_claims(payload):
    """Promise 3, enforced at the boundary. Recursively refuses any field whose
    name is a clinical claim, so a well-meaning future change that adds
    `severity` to a response object fails a test rather than reaching a patient."""
    def walk(o, path="response"):
        if isinstance(o, dict):
            for k, v in o.items():
                if str(k).lower() in FORBIDDEN_RESPONSE_FIELDS:
                    raise ValueError(
                        f"{path}.{k}: the response schema may not carry clinical "
                        f"claims. Module 1 measures; the clinician decides.")
                walk(v, f"{path}.{k}")
        elif isinstance(o, (list, tuple)):
            for i, v in enumerate(o):
                walk(v, f"{path}[{i}]")
    walk(payload)
    return True


def build_response(utterance_id, prompt_word, phones, gate, provenance,
                   quality=None):
    """Assemble the final payload and run the boundary assertions on it."""
    scored = [p for p in phones if p.score is not None]
    payload = {
        "utterance_id": utterance_id,
        "prompt_word": prompt_word,
        "status": "scored" if gate.passed else "held",
        "phones": [asdict(p) for p in phones],
        "coverage": {"n_scored": len(scored), "n_total": len(phones),
                     "pct": (100.0 * len(scored) / len(phones)) if phones else None},
        "quality_gate": {"passed": gate.passed, "failures": gate.failures,
                         **(quality or {}), **gate.measurements},
    }
    payload = stamp_provenance(payload, provenance)
    assert_no_clinical_claims(payload)
    return payload


# =============================================================================
# 4. Self-test
# =============================================================================


def self_test(verbose=True):
    n = 0

    def ck(cond, msg):
        nonlocal n
        assert cond, msg
        n += 1

    # --- gates --------------------------------------------------------------
    g = check_recording_gates(22.0, 0.86)
    ck(g.passed and not g.failures, "a clean clinic recording passes")

    g = check_recording_gates(8.0, 0.86)
    ck(not g.passed and g.failures[0]["gate"] == "recording_quality", "low SNR fails")
    ck(g.failures[0]["action"] == "request_retake", "and asks for a retake")

    g = check_recording_gates(22.0, 0.4)
    ck(not g.passed and g.failures[0]["action"] == "hold_for_review",
       "bad alignment holds rather than silently scoring")

    g = check_recording_gates(8.0, 0.4)
    ck(len(g.failures) == 2, "all failures are reported at once, not just the first")

    clinic = check_recording_gates(13.0, 0.86, "clinic")
    home = check_recording_gates(13.0, 0.86, "home")
    ck(clinic.passed and not home.passed, "home capture is held to a stricter bar")

    ck(check_recording_gates(None, None).passed is False, "missing measurements fail closed")

    # --- word identity ------------------------------------------------------
    ck(check_word_identity("rabit", "rabbit").passed, "a near miss is still the word")
    ck(not check_word_identity("kfgz", "rabbit").passed, "a different word is held")
    ck(check_word_identity(None, "rabbit").passed, "no decode cannot fail the gate")

    # --- withholding --------------------------------------------------------
    pol = WithholdingPolicy.from_error_table([
        {"phone": "S", "mae": 0.10, "n": 400},
        {"phone": "SH", "mae": 0.32, "n": 300},   # withheld: model is bad at it
        {"phone": "ZH", "mae": 0.09, "n": 12},    # withheld: too rare to know
    ])
    ok, why = pol.decide("S")
    ck(ok and why is None, "a well-measured phoneme is scored")
    ok, why = pol.decide("SH")
    ck(not ok and "reliably" in why, "a badly-measured phoneme is withheld with a reason")
    ok, why = pol.decide("ZH")
    ck(not ok, "a phoneme with too little data is withheld")
    ok, why = pol.decide("S", confidence=0.2)
    ck(not ok and "confidence" in why, "low confidence withholds even a good phoneme")
    ck(pol.meets_coverage_floor is False, "a policy below the coverage floor says so")

    pol2 = WithholdingPolicy.from_error_table([
        {"phone": "S", "mae": 0.10, "n": 900}, {"phone": "SH", "mae": 0.32, "n": 50}])
    ck(pol2.meets_coverage_floor is True, "a sensible policy clears the floor")

    # --- phone result invariants -------------------------------------------
    p = PhoneResult("R", "initial", score=1.2, confidence=0.71, flag="review")
    ck(p.score == 1.2, "a scored phone is fine")
    p = PhoneResult("AE", "medial", flag="not_scored", reason="not measured reliably")
    ck(p.score is None and p.reason, "an unscored phone carries a reason")
    for bad in [dict(target="X", flag="ok"),
                dict(target="X", flag="not_scored"),
                dict(target="X", score=1.0, flag="not_scored")]:
        try:
            PhoneResult(**bad)
            ck(False, f"invalid PhoneResult should raise: {bad}")
        except ValueError:
            ck(True, "invalid PhoneResult raises")

    # --- provenance ---------------------------------------------------------
    full = {k: "v1" for k in REQUIRED_PROVENANCE}
    s = stamp_provenance({"x": 1}, full)
    ck(s["x"] == 1 and len(s["provenance"]) == len(REQUIRED_PROVENANCE), "provenance stamped")
    for bad in [{}, {**full, "core_sha256": ""}, {**full, "model_version": None}]:
        try:
            stamp_provenance({"x": 1}, bad)
            ck(False, "incomplete provenance should raise")
        except ValueError:
            ck(True, "incomplete provenance raises")

    # --- clinical-claim boundary -------------------------------------------
    ck(assert_no_clinical_claims({"phones": [{"target": "R", "score": 1}]}),
       "a measurement payload passes")
    for bad in [{"severity": "moderate"},
                {"phones": [{"target": "R", "diagnosis": "SSD"}]},
                {"a": {"b": [{"recommendation": "practise /s/"}]}}]:
        try:
            assert_no_clinical_claims(bad)
            ck(False, f"clinical claim should be refused: {bad}")
        except ValueError:
            ck(True, "clinical claim refused at the boundary")

    # --- full response ------------------------------------------------------
    resp = build_response(
        "utt-1", "rabbit",
        [PhoneResult("R", "initial", score=1.2, confidence=0.71, flag="review"),
         PhoneResult("AE", "medial", flag="not_scored", reason="not measured reliably")],
        check_recording_gates(22.0, 0.86), full)
    ck(resp["coverage"]["n_scored"] == 1 and resp["coverage"]["n_total"] == 2,
       "coverage is computed and reported")
    ck(resp["status"] == "scored" and "provenance" in resp, "response is well formed")
    ck(all(("score" in p) or ("reason" in p) for p in resp["phones"]),
       "every phone carries a score or a reason")

    if verbose:
        print(f"mira_serve.contracts {CONTRACTS_VERSION}: {n} assertions passed")
    return n


if __name__ == "__main__":
    self_test()