"""mira_module2b.py, Module 2B, constrained narration.

WHAT THIS IS
------------
A language model still has a job in Mira. It is a much smaller and much safer
job than "write the clinical report": it turns the numbers Module 2A already
computed into sentences a human wants to read, in two registers, one for the
clinician's report and one for the caregiver summary.

It receives the complete Module 2A output AND NOTHING ELSE. No audio, no raw
internal scores, no clinical knowledge base, no history beyond the deltas
already computed. It cannot reach a number that was not computed, because it
was never given one.

THE CHECK IS THE PRODUCT
------------------------
Generation is the easy half. This file is the hard half: a verifier that reads
generated prose back and drops any sentence that cannot be traced to the
computed record. Four stages, in order:

    1. EXTRACT every claim   - numerals, percentages, phoneme references,
                               process names, dates
    2. MATCH each one        - every extracted item must resolve to a field in
                               the Module 2A output, or the sentence fails
    3. SCREEN vocabulary     - diagnostic terms, condition names, severity
                               assertions and recommendation verbs fail outright
    4. FAIL CLOSED           - a failed sentence is dropped; if too much of a
                               section is dropped, the whole narrative is
                               replaced by the underlying tables

THE TEST THAT PROVES THE DESIGN IS RIGHT
----------------------------------------
Delete Module 2B entirely. If the report a clinician receives is still
signable and still useful, the separation is correct. If it is not, something
clinical has leaked into the narration layer and belongs back in 2A.

Narration is a READABILITY layer, never a load-bearing one. That is exactly
what makes it safe to have a language model in a clinical product at all.

Standard library only.
"""

MODULE2B_VERSION = "1.0.0"

import re

# =============================================================================
# 1. The forbidden vocabulary screen
# =============================================================================
#
# A maintained list, versioned with the ruleset, of things the narration layer
# may never say. Grouped by WHY each group is forbidden, because a maintainer
# adding a term six months from now needs to know which bucket it belongs in.

FORBIDDEN = {
    # Naming a condition converts decision support into a diagnosis, which is a
    # regulated professional act.
    "condition_names": [
        "apraxia", "dysarthria", "aphasia", "autism", "asd", "adhd", "dyslexia",
        "cleft", "stutter", "stuttering", "cluttering", "phonological disorder",
        "articulation disorder", "speech sound disorder", "ssd", "delay",
        "delayed", "disordered", "disorder", "impairment", "impaired",
        "pathology", "syndrome",
    ],
    # A computed figure and a published band are facts. "Moderate-severe" is a
    # clinical judgement wearing a number as a costume.
    "severity_assertions": [
        "mild", "moderate", "severe", "profound", "significant", "marked",
        "borderline", "normal for", "abnormal", "atypical", "typical of",
        "concerning", "worrying", "alarming", "poor", "excellent",
    ],
    # Recommending is the clinician's act. The recommendation section of the
    # report stays blank until they write it.
    "recommendation_verbs": [
        "should practise", "should practice", "recommend", "recommended",
        "suggest", "advise", "we advise", "try ", "start with", "begin with",
        "focus on", "work on", "target ", "prescribe", "must ", "needs to",
        "ought to", "consider ",
    ],
    # Predicting the future is the clinician's judgement and the basis on which
    # they justify a course of therapy to a family.
    "prognosis": [
        "will improve", "will resolve", "expect", "expected to", "prognosis",
        "likely to", "unlikely to", "within weeks", "within months",
        "by the age of", "should catch up", "outgrow",
    ],
    # Attributing a flat line is speculation: adherence, approach, target
    # choice, hearing, motivation and family circumstances all look identical
    # in the data.
    "causal_attribution": [
        "because of", "due to", "caused by", "as a result of", "owing to",
        "stems from", "explained by", "attributable to",
    ],
}


def screen_vocabulary(sentence):
    """Returns the list of (group, term) hits. Empty list means the sentence
    passes. Word-boundary matching, so 'target ' does not fire on 'targeted
    phoneme' inside a computed field name."""
    low = " " + sentence.lower() + " "
    hits = []
    for group, terms in FORBIDDEN.items():
        for t in terms:
            pattern = re.escape(t) if t.endswith(" ") else r"\b" + re.escape(t) + r"\b"
            if re.search(pattern, low):
                hits.append((group, t.strip()))
    return hits


# =============================================================================
# 2. Claim extraction
# =============================================================================
#
# Pull every checkable assertion out of a sentence. Anything extracted here must
# later resolve to a computed field, so over-extracting is safe (it only causes
# a sentence to be dropped) while under-extracting is not (it lets an
# unverifiable number through). When in doubt, extract.

NUM_RE = re.compile(r"(?<![\w/])(\d+(?:\.\d+)?)\s*(%|percent|per cent)?")
PHONE_RE = re.compile(r"/([^/\s]{1,4})/")
DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
PROCESS_RE = re.compile(
    r"\b(fronting|backing|stopping|gliding|deaffrication|cluster reduction|"
    r"final consonant deletion|final devoicing|weak syllable deletion|"
    r"assimilation|epenthesis)\b", re.I)


def extract_claims(sentence):
    """Split a sentence into the atoms that must each be verifiable."""
    claims = {"numbers": [], "percentages": [], "phonemes": [],
              "processes": [], "dates": []}
    for m in NUM_RE.finditer(sentence):
        val = float(m.group(1))
        if m.group(2):
            claims["percentages"].append(val)
        else:
            claims["numbers"].append(val)
    claims["phonemes"] = [p for p in PHONE_RE.findall(sentence)]
    claims["processes"] = [p.lower() for p in PROCESS_RE.findall(sentence)]
    claims["dates"] = DATE_RE.findall(sentence)
    return claims


# =============================================================================
# 3. Building the set of permitted facts from the Module 2A output
# =============================================================================


def _walk(obj, out_numbers, out_strings, depth=0):
    """Recursively collect every number and string in the analysis. This is the
    universe of things narration is allowed to mention."""
    if depth > 12:
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            out_strings.add(str(k).lower())
            _walk(v, out_numbers, out_strings, depth + 1)
    elif isinstance(obj, (list, tuple, set)):
        for v in obj:
            _walk(v, out_numbers, out_strings, depth + 1)
    elif isinstance(obj, bool):
        pass
    elif isinstance(obj, (int, float)):
        out_numbers.add(round(float(obj), 4))
    elif isinstance(obj, str):
        out_strings.add(obj.lower())


def permitted_facts(analysis, pct_tolerance=0.55):
    """Every number and name the narration layer may use.

    `pct_tolerance` exists for ONE legitimate reason: a percentage of 84.21 may
    honestly be written as 84.2 or 84. It is deliberately under one whole
    percentage point, so a rounding that changes the meaning of a clinical
    figure still fails. It is not a licence to approximate.
    """
    nums, strs = set(), set()
    _walk(analysis, nums, strs)
    # Also admit the sensible roundings of every number present.
    rounded = set()
    for n in nums:
        rounded.add(round(n))
        rounded.add(round(n, 1))
    return {"numbers": nums | rounded, "strings": strs, "tolerance": pct_tolerance}


def _number_ok(value, facts):
    if value in facts["numbers"]:
        return True
    return any(abs(value - f) <= facts["tolerance"] for f in facts["numbers"])


# =============================================================================
# 4. Sentence-level verification
# =============================================================================


def verify_sentence(sentence, analysis, facts=None):
    """Returns (passed, reasons). A sentence passes only if EVERY claim in it
    resolves and no forbidden vocabulary fires."""
    facts = facts or permitted_facts(analysis)
    reasons = []

    for group, term in screen_vocabulary(sentence):
        reasons.append(f"forbidden vocabulary [{group}]: '{term}'")

    claims = extract_claims(sentence)
    for v in claims["numbers"] + claims["percentages"]:
        if not _number_ok(v, facts):
            reasons.append(f"number {v} does not appear in the computed record")
    for p in claims["phonemes"]:
        if p.lower() not in facts["strings"] and p.upper() not in {s.upper() for s in facts["strings"]}:
            reasons.append(f"phoneme /{p}/ was not measured in this analysis")
    for pr in claims["processes"]:
        key = pr.replace(" ", "_")
        if key not in facts["strings"] and pr not in facts["strings"]:
            reasons.append(f"process '{pr}' was not computed in this analysis")
    for d in claims["dates"]:
        if d not in facts["strings"]:
            reasons.append(f"date {d} does not appear in the computed record")

    return (len(reasons) == 0), reasons


def verify_narrative(text, analysis, min_retained=0.7):
    """Verify a whole generated section and FAIL CLOSED.

    Sentences that fail are dropped. If the proportion retained falls below
    `min_retained`, the entire narrative is discarded and the caller must fall
    back to printing the Module 2A tables, which are, on their own, a complete
    report. That fallback is what makes the language model optional, and
    optional is what makes it safe.
    """
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]
    facts = permitted_facts(analysis)
    kept, dropped = [], []
    for s in sentences:
        ok, why = verify_sentence(s, analysis, facts)
        (kept if ok else dropped).append({"sentence": s, "reasons": why})

    ratio = len(kept) / len(sentences) if sentences else 0.0
    use_narrative = bool(sentences) and ratio >= min_retained
    return {
        "use_narrative": use_narrative,
        "fallback": "module_2a_tables" if not use_narrative else None,
        "retained_ratio": ratio,
        "text": " ".join(k["sentence"] for k in kept) if use_narrative else None,
        "kept": kept,
        "dropped": dropped,
    }


# =============================================================================
# 5. The prompt contract
# =============================================================================


def build_narration_request(analysis, register="clinician"):
    """What Module 2B is handed. Note what is absent: no audio, no raw GOP, no
    reference material, no patient history beyond computed deltas."""
    if register not in ("clinician", "caregiver"):
        raise ValueError("register must be 'clinician' or 'caregiver'")
    return {
        "register": register,
        "analysis": analysis,
        "instructions": [
            "Restate the computed figures in fluent prose. Nothing else.",
            "Every number you write must appear in the analysis object.",
            "Do not name any condition, state any severity, give any "
            "recommendation, predict any outcome, or explain any cause.",
            "If you cannot say something without breaking a rule above, omit it.",
            ("Write for a speech-language pathologist." if register == "clinician"
             else "Write for a parent, in plain language, introducing no clinical "
                  "terminology the clinician did not use."),
        ],
        "may_not_receive": ["audio", "raw_gop_scores", "clinical_knowledge_base",
                            "prior_reports", "diagnostic_criteria"],
    }


# =============================================================================
# 6. Self-test
# =============================================================================


def self_test(verbose=True):
    n = 0

    def ck(cond, msg):
        nonlocal n
        assert cond, msg
        n += 1

    analysis = {
        "protocol_version": "3.1.0",
        "accuracy": {"pcc": {"n": 41, "d": 49, "pct": 83.7, "label": "PCC"},
                     "coverage": {"n": 49, "d": 52, "pct": 94.2}},
        "processes": {"fronting": {"n": 6, "d": 8, "pct": 75.0}},
        "phonemes_measured": ["S", "K", "R"],
        "date": "2026-03-01",
    }
    facts = permitted_facts(analysis)

    # --- things that must PASS ---------------------------------------------
    ok, why = verify_sentence(
        "41 of 49 consonants were produced correctly.", analysis, facts)
    ck(ok, f"a plain restatement of computed integers must pass: {why}")

    ok, _ = verify_sentence("Fronting occurred on 6 of 8 opportunities.", analysis, facts)
    ck(ok, "a computed process with its denominator must pass")

    ok, _ = verify_sentence("Consonant accuracy was 83.7%.", analysis, facts)
    ck(ok, "an exact computed percentage must pass")

    ok, _ = verify_sentence("Consonant accuracy was 84%.", analysis, facts)
    ck(ok, "an honest rounding within tolerance must pass")

    # --- things that must FAIL ---------------------------------------------
    ok, why = verify_sentence("Consonant accuracy was 91%.", analysis, facts)
    ck(not ok and any("does not appear" in r for r in why),
       "a number that was never computed must fail")

    ok, why = verify_sentence(
        "This is consistent with a moderate phonological disorder.", analysis, facts)
    ck(not ok, "naming a condition must fail")
    ck(any("condition_names" in r for r in why), "and it must say which rule fired")
    ck(any("severity_assertions" in r for r in why), "severity assertion caught too")

    ok, why = verify_sentence("We recommend focusing on /s/ first.", analysis, facts)
    ck(not ok and any("recommendation_verbs" in r for r in why),
       "a recommendation must fail")

    ok, why = verify_sentence("This will resolve within months.", analysis, facts)
    ck(not ok and any("prognosis" in r for r in why), "a prognosis must fail")

    ok, why = verify_sentence(
        "The errors are due to weak oral musculature.", analysis, facts)
    ck(not ok and any("causal_attribution" in r for r in why),
       "a causal attribution must fail")

    ok, why = verify_sentence("Stopping occurred on 4 of 6 opportunities.", analysis, facts)
    ck(not ok and any("was not computed" in r for r in why),
       "a process that was never computed must fail even with plausible numbers")

    ok, why = verify_sentence("The /th/ was produced in error.", analysis, facts)
    ck(not ok and any("was not measured" in r for r in why),
       "a phoneme absent from the analysis must fail")

    ok, why = verify_sentence("Recorded on 2025-11-02.", analysis, facts)
    ck(not ok, "a date not in the record must fail")

    # a rounding that CHANGES the figure must still fail
    ok, _ = verify_sentence("Consonant accuracy was 85%.", analysis, facts)
    ck(not ok, "tolerance must not admit a rounding that changes the meaning")

    # --- whole-narrative behaviour -----------------------------------------
    good = ("41 of 49 consonants were produced correctly. "
            "Fronting occurred on 6 of 8 opportunities.")
    res = verify_narrative(good, analysis)
    ck(res["use_narrative"] is True and res["text"], "a clean narrative is used")
    ck(len(res["dropped"]) == 0, "and nothing is dropped from it")

    mixed = ("41 of 49 consonants were produced correctly. "
             "This indicates a severe disorder. "
             "We recommend starting with /k/. "
             "Accuracy was 91%.")
    res = verify_narrative(mixed, analysis)
    ck(res["use_narrative"] is False, "too many failures must fail closed")
    ck(res["fallback"] == "module_2a_tables", "and fall back to the tables")
    ck(res["text"] is None, "no partial narrative is emitted when failing closed")
    ck(len(res["dropped"]) == 3, "each bad sentence is recorded with its reason")

    ck(verify_narrative("", analysis)["use_narrative"] is False, "empty input fails closed")

    # --- request contract ---------------------------------------------------
    req = build_narration_request(analysis, "caregiver")
    ck("audio" in req["may_not_receive"], "the request contract excludes audio")
    ck(req["analysis"] is analysis, "it carries the analysis and nothing more")
    try:
        build_narration_request(analysis, "marketing")
        ck(False, "an unknown register should raise")
    except ValueError:
        ck(True, "an unknown register raises")

    if verbose:
        print(f"mira_module2b {MODULE2B_VERSION}: {n} assertions passed")
    return n


if __name__ == "__main__":
    self_test()