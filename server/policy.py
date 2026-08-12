"""
policy.py — decision rules and stated limits for the served scorer.

Mirrors core/policy.js on the frontend. The server is authoritative: it always
emits an explicit `marking`, so the client's own gates stay dormant.
"""

import os

import mira_core

# --------------------------------------------------------------------------
# scorer identity
# --------------------------------------------------------------------------
# Two tiers exist in the notebooks. Only the lower one is reproducible here,
# because the trained model's 193 feature columns include 74 lpr_<phone>
# columns whose labels live in phone_token_map.json, which is a Kaggle artifact
# derived from Speechocean762's MFA output and is not on this machine.
SCORER_TIER = "gop_baseline"
SCORER_DESCRIPTION = (
    "Goodness-of-Pronunciation baseline: wav2vec2 CTC posteriors over a "
    "forced-aligned target sequence. This is the 'post_max alone' rung of the "
    "Stage 2 ablation, not the trained ensemble."
)
# Measured on the official speechocean762 test split (15,559 phones, 125 unseen
# speakers). Stage 2, method_comparison table.
EXPECTED_AUC = 0.734          # trained ensemble reached 0.843
EXPECTED_PCC = 0.176          # trained ensemble reached 0.376

MODEL_ID = os.environ.get("MIRA_MODEL_ID", "facebook/wav2vec2-lv-60-espeak-cv-ft")
SEC_PER_FRAME = 0.02

# --------------------------------------------------------------------------
# gates  [B2C §4.7, endpoint §15]
# --------------------------------------------------------------------------
MIN_SNR_DB = float(os.environ.get("MIRA_MIN_SNR_DB", 12.0))
MIN_DURATION_MS = 30.0        # below this no acoustic method resolves reliably

# --------------------------------------------------------------------------
# flag threshold
# --------------------------------------------------------------------------
# UNCALIBRATED. The published operating point (confidence < 0.86, from Platt
# a=4.2632 b=-5.8443) belongs to the trained ensemble's 0-2 output. Those
# parameters do not transfer to a raw posterior, and applying them anyway would
# produce a confident, precise, entirely wrong number. Tune this on your own
# data before treating it as meaningful.
FLAG_THRESHOLD = float(os.environ.get("MIRA_FLAG_THRESHOLD", 0.50))
CONFIDENCE_KIND = "raw_posterior"

# --------------------------------------------------------------------------
# corroboration gate
# --------------------------------------------------------------------------
# post_max alone can flag a phone on one bad frame even when the rest of the
# window and the model's discriminability both looked fine. Before honoring a
# post_max-driven "substituted" verdict, require it to be corroborated by at
# least one of two independent variants computed from the same window:
#   - post_mean: was the whole window weak, not just its single worst/best frame
#   - gop_renorm: did the model actually prefer this phone over its competitors
# If neither corroborates, the low post_max is treated as a spike/dip rather
# than real evidence, and the phone is marked "correct" instead. This never
# flags a phone post_max would have passed — it only rescues borderline
# flags, so it can only reduce false positives. UNCALIBRATED like
# FLAG_THRESHOLD above; tune on real data.
COMBINE_GOP_VARIANTS = os.environ.get("MIRA_COMBINE_GOP", "1") not in ("0", "false", "False")
POST_MEAN_CORROBORATE = float(os.environ.get("MIRA_POST_MEAN_THRESHOLD", 0.50))
GOP_RENORM_CORROBORATE = float(os.environ.get("MIRA_GOP_RENORM_THRESHOLD", -1.0))

# --------------------------------------------------------------------------
# per-phoneme reliability  [Stage 2 error_by_phoneme.csv, n >= 50]
# --------------------------------------------------------------------------
PHONEME_MAE = {
    "u": 0.315, "t̪": 0.264, "ɫ": 0.254, "e": 0.251, "aw": 0.240,
    "ʎ": 0.237, "z": 0.232, "ɹ": 0.231, "ʉ": 0.231, "ʃ": 0.210,
    "l": 0.207, "a": 0.204,
    "ʋ": 0.123, "cʰ": 0.110, "bʲ": 0.098, "b": 0.090, "h": 0.085, "j": 0.068,
}
PHONEME_N = {
    "u": 57, "t̪": 73, "ɫ": 132, "e": 678, "aw": 96, "ʎ": 126, "z": 451,
    "ɹ": 397, "ʉ": 109, "ʃ": 121, "l": 437, "a": 2818,
    "ʋ": 492, "cʰ": 75, "bʲ": 83, "b": 181, "h": 113, "j": 175,
}

# Withholding policy  [Stage 4 §12]: MAE > 0.25 or n < 50 -> decline.
WITHHOLD_MAE_CEILING = 0.25
WITHHOLD_MIN_N = 50
WITHHELD_PHONEMES = sorted(
    p for p, mae in PHONEME_MAE.items()
    if mae > WITHHOLD_MAE_CEILING or PHONEME_N.get(p, 0) < WITHHOLD_MIN_N
)
WITHHOLD_REASON = "not measured reliably enough to judge"

MARKINGS = ["correct", "substituted", "omitted", "assimilated", "not_scored"]


def is_withheld(phone_ipa):
    """Decline the sounds the model is measurably worst at.

    'A tool that marks 18 of 24 consonants reliably and says not scored for the
    other six is genuinely valuable and honest. A tool that guesses on all 24 is
    worse than the paper form.'
    """
    return mira_core.normalize_ipa(phone_ipa) in WITHHELD_PHONEMES


def decide_marking(*, post_max, duration_ms, substitute, withheld,
                    post_mean=None, gop_renorm=None):
    """The marking cascade. Distortion is a flag, never a marking; there is no
    fifth column. Returns (marking, reason)."""
    if withheld:
        return "not_scored", WITHHOLD_REASON
    if post_max is None:
        return "not_scored", "no frames aligned to this sound"
    if duration_ms is not None and duration_ms < MIN_DURATION_MS:
        return "not_scored", "too short to measure"
    # An omission reads as a near-absent segment the model has no evidence for.
    if duration_ms is not None and duration_ms < 40.0 and post_max < 0.20:
        return "omitted", None
    if post_max < FLAG_THRESHOLD:
        if COMBINE_GOP_VARIANTS:
            corroborated = (
                (post_mean is not None and post_mean < POST_MEAN_CORROBORATE)
                or (gop_renorm is not None and gop_renorm < GOP_RENORM_CORROBORATE)
            )
            if not corroborated:
                return "correct", None
        # `substitute` may be None: we can be confident the target was not
        # produced without being able to name what replaced it. The marking
        # stands on its own; the substitute is an annotation when available.
        return "substituted", None
    return "correct", None


def provenance(device):
    """Travels with every scored record. Names the model, the alignment route
    and the operating point, so a marking can always be traced."""
    return {
        "model_version": MODEL_ID,
        "aligner_version": "ctc_forced_align (mira_core %s)" % mira_core.CORE_VERSION,
        "protocol_version": "gop_baseline_post_max_v1",
        "threshold_set_version": "uncalibrated_post_max_t%.2f" % FLAG_THRESHOLD,
        "device": device,
        "scorer": {
            "tier": SCORER_TIER,
            "description": SCORER_DESCRIPTION,
            "expected_auc": EXPECTED_AUC,
            "expected_pcc": EXPECTED_PCC,
            "confidence_kind": CONFIDENCE_KIND,
            "calibrated": False,
            "note": (
                "Raw CTC posterior, not a calibrated probability. The trained "
                "ensemble (AUC 0.843) needs Stage 2 artifacts that are not "
                "present; this is the ablation rung below it (AUC 0.734)."
            ),
        },
    }
