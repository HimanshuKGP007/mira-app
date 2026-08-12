"""End-to-end tests. No model, no network, no GPU, under a second.

These test the WIRING, not the acoustics. They cannot tell you whether the model
is any good. They can tell you that a substitution travels correctly from the
decode, through attribution, through error typing, through the alphabet
conversion, into the phonological process table and out into the report.

That is the failure mode that actually bit this project: every component was
individually correct and tested, and the connections between them were not.
"""

import sys
import pathlib

import numpy as np
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from mira_app import (MiraEngine, SyntheticDecoder, default_vocab_symbols,
                      protocol, session, mira_core)
from mira_app import report as rpt
from mira_app import contracts, mira_module2a, mira_module2b


STOPPING_GLIDING = {"s": "t", "z": "d", "ʃ": "s", "θ": "t", "ð": "d", "ɹ": "w"}


def engine():
    return MiraEngine(SyntheticDecoder(default_vocab_symbols()))


def run_session(eng, words, substitutions=None, seed=0):
    sub = substitutions or {}
    rng = np.random.default_rng(seed)
    out = []
    for w in words:
        item = protocol.get_item(w)
        ipas = [eng.arp_to_ipa[a] for a in item["phones"]]
        eng.decoder.set_production([sub.get(i, i) for i in ipas])
        out.append(eng.score(rng.normal(0, 0.1, 16000).astype(np.float32), 16000, w))
    return out


# =============================================================================
# the component self-tests still pass through the app package
# =============================================================================

def test_component_self_tests():
    assert mira_core.self_test(False) >= 214
    assert contracts.self_test(False) >= 32
    assert mira_module2a.self_test(False) >= 46
    assert mira_module2b.self_test(False) >= 25


# =============================================================================
# the protocol
# =============================================================================

def test_protocol_refuses_unknown_words():
    with pytest.raises(KeyError):
        protocol.get_item("supercalifragilistic")


def test_position_tags():
    it = protocol.get_item("street")            # S T R IY1 T
    assert it["positions"][0] == "initial"      # first of an initial cluster
    assert it["positions"][2] == "initial"      # still pre-vocalic
    assert it["positions"][-1] == "final"
    assert it["positions"][3] is None           # the vowel


def test_cluster_flags():
    assert protocol.get_item("street")["in_cluster"][:3] == [True, True, True]
    assert protocol.get_item("sun")["in_cluster"][0] is False


def test_every_protocol_phone_resolves_to_a_token():
    eng = engine()
    assert eng.readiness()["phones_unresolved"] == [], (
        "a target phone with no token id produces a confidently wrong goodness "
        "figure on every recording that contains it")


# =============================================================================
# THE GATES. Each of these caught a real bug.
# =============================================================================

def test_a_clear_substitution_is_scored_not_held():
    """The gate bug that mattered most.

    Alignment quality computed as the mean TARGET posterior is goodness of
    pronunciation, so gating on it holds every item containing an error. Mira then
    refuses to score exactly the recordings with mistakes and reports near-perfect
    accuracy on what survives.
    """
    eng = engine()
    r = run_session(eng, ["sun"], {"s": "t"})[0]
    assert r["status"] == "scored", (
        f"a clear substitution must be scored, not held: "
        f"{r['quality_gate'].get('reason')}")
    assert r["phones"][0]["error_type"] == "substitution"
    assert r["phones"][0]["produced"] == "t"


def test_confidence_is_measurement_certainty_not_target_match():
    """A confident error is a HIGH confidence measurement of a LOW score.

    Deriving confidence from the target posterior makes a confident error read as
    low confidence, so the per-phone gate withholds it. Same failure as the
    alignment one, one level down.
    """
    eng = engine()
    r = run_session(eng, ["sun"], {"s": "t"})[0]
    p = r["phones"][0]
    assert p["score"] is not None and p["score"] < 1.0, "the score must be low"
    assert p["confidence"] > 0.6, (
        f"the measurement was clean, so confidence must be high: {p['confidence']}")


def test_short_words_do_not_trip_the_word_identity_gate():
    """'shoe' is two sounds. One substitution drops similarity to 0.25 and the
    gate would hold a perfectly good recording of a real error."""
    eng = engine()
    r = run_session(eng, ["shoe"], {"ʃ": "s"})[0]
    assert r["status"] == "scored"
    assert r["phones"][0]["error_type"] == "substitution"


def test_garbled_audio_is_still_held():
    """The gates must still work. A window that is confidently nothing must not
    pass just because the substitution fix loosened things."""
    eng = engine()
    q_clear, _ = mira_core.alignment_confidence(
        np.log(np.array([[0.9, 0.02, 0.02, 0.06]] * 8)), [(0, 8)])
    q_mush, _ = mira_core.alignment_confidence(
        np.log(np.full((8, 4), 0.25)), [(0, 8)])
    assert q_mush < 0.4 < q_clear, "a bad recording must rank below a clear error"


def test_a_missing_segment_penalises_alignment():
    lp = np.log(np.array([[0.9, 0.02, 0.02, 0.06]] * 8))
    full, _ = mira_core.alignment_confidence(lp, [(0, 4), (4, 8)])
    gap, detail = mira_core.alignment_confidence(lp, [(0, 4), (None, None)])
    assert gap < full and detail["n_without_frames"] == 1


# =============================================================================
# THE SEAM. Module 1 output reaching Module 2A intact.
# =============================================================================

def test_arpabet_conversion_handles_stress_digits():
    """`'AE1'.isalpha()` is False, so a naive check sends the entire vowel
    inventory to Module 2A as unconvertible and every vowel is held."""
    assert session.to_arpabet("AE1") == "AE"
    assert session.to_arpabet("AH0") == "AH"
    assert session.to_arpabet("s") == "S"
    assert session.to_arpabet("ʃ") == "SH"
    assert session.to_arpabet(None) is None


def test_unconvertible_symbols_are_held_never_guessed():
    recs = session.response_to_records({
        "prompt_word": "x", "status": "scored",
        "item": {"positions": ["initial"], "in_cluster": [False]},
        "phones": [{"target": "s", "produced": "\u0288\u02b2", "score": 1.0,
                    "flag": "ok", "error_type": "substitution",
                    "produced_confident": True}]})
    assert recs[0]["held"] is True, (
        "a substitute that cannot be typed must be held; discarding it would "
        "understate the error rate")


def test_a_held_item_still_reaches_module_2a():
    recs = session.response_to_records({
        "prompt_word": "sun", "status": "held", "phones": [],
        "quality_gate": {"reason": "too noisy"},
        "item": {"phones": ["S", "AH1", "N"],
                 "positions": ["initial", None, "final"],
                 "in_cluster": [False, False, False]}})
    assert len(recs) == 3 and all(r["held"] for r in recs), (
        "an item that was attempted and not scored must reach coverage, or the "
        "report will not know it happened")


def test_stopping_and_gliding_reach_the_process_table():
    """The end-to-end assertion. /s/ produced as [t] is a fricative realised as a
    stop, which is the textbook example, and /r/ as [w] is gliding."""
    eng = engine()
    words = ["sun", "bus", "shoe", "think", "this", "zoo", "rabbit", "carrot",
             "fish", "street", "green", "bath"]
    a = session.analyse(run_session(eng, words, STOPPING_GLIDING))
    applied = {k: v for k, v in a["processes"].items()
               if isinstance(v, dict) and (v.get("n") or 0) > 0}
    assert "stopping" in applied, "the seam is broken: produced_arpabet is not arriving"
    assert "gliding" in applied
    assert a["accuracy"]["pcc"]["pct"] < 90


def test_a_clean_speaker_produces_no_processes():
    """The control. Without this, a table that always fires proves nothing."""
    eng = engine()
    words = ["sun", "bus", "shoe", "think", "this", "zoo", "rabbit", "fish"]
    a = session.analyse(run_session(eng, words))
    applied = {k: v for k, v in a["processes"].items()
               if isinstance(v, dict) and (v.get("n") or 0) > 0}
    assert applied == {}, f"a clean speaker triggered {list(applied)}"
    assert a["accuracy"]["pcc"]["pct"] == 100.0
    assert a["accuracy"]["n_held"] == 0


# =============================================================================
# MODULE 2B. Narration may only restate what 2A computed.
# =============================================================================

def test_narration_passes_verification():
    eng = engine()
    a = session.analyse(run_session(eng, ["sun", "bus", "rabbit", "fish"],
                                    STOPPING_GLIDING))
    n = session.narrate(a)
    assert n["use_narrative"] is True
    assert n["retained_ratio"] == 1.0


def test_an_inventing_narrator_is_rejected():
    """The safety property. A narrator that states a diagnosis, a severity or a
    number that is not in the analysis must be dropped."""
    eng = engine()
    a = session.analyse(run_session(eng, ["sun", "bus"], STOPPING_GLIDING))

    class Liar:
        def __call__(self, request):
            return ("This child presents with a moderate phonological disorder. "
                    "Consonant accuracy was 12.7 percent. "
                    "I recommend twelve weeks of minimal pair therapy.")

    n = session.narrate(a, narrator=Liar())
    assert n["use_narrative"] is False, "an inventing narrator must fail closed"
    assert n["fallback"] == "module_2a_tables"


def test_the_narrator_never_sees_the_raw_records():
    seen = {}

    class Spy:
        def __call__(self, request):
            seen.update(request["analysis"])
            return "No phonological process reached its threshold."

    eng = engine()
    a = session.analyse(run_session(eng, ["sun", "bus"]))
    session.narrate(a, narrator=Spy())
    assert "records" not in seen, (
        "per-sound timings and confidences are not a narration layer's business")


def test_deleting_the_narration_still_leaves_a_report():
    """The test of whether the 2A/2B split is real."""
    eng = engine()
    a = session.analyse(run_session(eng, ["sun", "bus", "rabbit"], STOPPING_GLIDING))
    html = rpt.render(a, narration=None)
    assert "Consonants correct" in html and "stopping" in html.lower()


# =============================================================================
# The response contract holds all the way out
# =============================================================================

def test_no_clinical_claim_can_reach_a_response():
    eng = engine()
    r = run_session(eng, ["sun"], {"s": "t"})[0]
    contracts.assert_no_clinical_claims(r)
    with pytest.raises(ValueError):
        contracts.assert_no_clinical_claims({**r, "severity": "moderate"})


def test_provenance_travels_with_every_response():
    eng = engine()
    r = run_session(eng, ["sun"])[0]
    for k in contracts.REQUIRED_PROVENANCE:
        assert r["provenance"].get(k), f"{k} missing from provenance"
    assert "PREVIEW" in r["provenance"]["threshold_set_version"], (
        "preview mode must be visible in the provenance, not just in the UI")


def test_preview_mode_is_stamped_everywhere():
    eng = engine()
    resp = run_session(eng, ["sun", "bus"])
    a = session.analyse(resp, uncalibrated=True)
    assert a["uncalibrated"] is True
    assert any(f["flag"] == "uncalibrated_preview" for f in a["flags"])
    assert "Preview mode" in rpt.render(a, None)


def test_report_renders_and_contains_the_evidence():
    eng = engine()
    a = session.analyse(run_session(eng, ["sun", "rabbit", "fish"], STOPPING_GLIDING))
    html = rpt.render(a, session.narrate(a))
    assert html.startswith("<!doctype html>")
    assert "What this report does not say" in html
    assert "0.00" in html or "s</td>" in html    # clip timestamps are present
