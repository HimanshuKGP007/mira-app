"""
insights.py — Module 2, minimal version: turn session history into a parent
note.

Two steps, both fail closed:

  compute_analysis()  ordinary arithmetic over the session history the app
                       already stores client-side. No model, no torch import,
                       ships from numbers that are already on screen elsewhere.

  narrate()            hands ONLY those numbers to Groq for 2-3 sentences.
                       Verified against a forbidden-word screen before it's
                       shown; any failure (no key, network, timeout, a
                       forbidden word) falls back to a template built from
                       the same numbers. The parent screen never depends on
                       Groq being reachable.
"""

import json
import os

import requests

GROQ_MODEL = "llama-3.1-8b-instant"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_TIMEOUT_S = 6

# Mirrors core/policy.js MUST_NOT_OUTPUT. The narration layer may only
# restate computed figures; it must never say anything that reads as a
# clinical claim.
FORBIDDEN_WORDS = [
    "diagnos", "severity", "disorder", "condition", "prognosis",
    "treatment", "therapy", "recommend", "should see", "specialist",
    "delay", "impairment",
]

POSITION_LABEL = {"initial": "start", "medial": "middle", "final": "end"}


def compute_analysis(sessions, target_phone):
    """sessions: store.sessions shape, oldest first. Ordinary arithmetic,
    nothing here needs a model."""
    n_sessions = len(sessions)
    totals = {"scored": 0, "clear": 0, "flagged": 0, "not_scored": 0}
    by_position = {}
    substitute_counts = {}

    for s in sessions:
        totals["scored"] += s.get("scored", 0)
        totals["clear"] += s.get("clear", 0)
        totals["flagged"] += s.get("flagged", 0)
        totals["not_scored"] += s.get("notScored", 0)
        for pos, v in (s.get("byPosition") or {}).items():
            bp = by_position.setdefault(pos, {"scored": 0, "clear": 0})
            bp["scored"] += v.get("scored", 0)
            bp["clear"] += v.get("clear", 0)
        for item in s.get("items", []):
            for inst in item.get("instances", []):
                sub = inst.get("substitute")
                if sub:
                    substitute_counts[sub] = substitute_counts.get(sub, 0) + 1

    top_substitute = None
    if substitute_counts:
        sub, count = max(substitute_counts.items(), key=lambda kv: kv[1])
        top_substitute = {"sound": sub, "count": count}

    accuracy_pct = (round(100 * totals["clear"] / totals["scored"])
                    if totals["scored"] else None)
    position_pct = {
        pos: (round(100 * v["clear"] / v["scored"]) if v["scored"] else None)
        for pos, v in by_position.items()
    }

    trend = None
    if n_sessions >= 2:
        last = sessions[-1]
        last_rate = (last.get("clear", 0) / last["scored"]) if last.get("scored") else None
        prior_scored = sum(s.get("scored", 0) for s in sessions[:-1])
        prior_clear = sum(s.get("clear", 0) for s in sessions[:-1])
        prior_rate = (prior_clear / prior_scored) if prior_scored else None
        if last_rate is not None and prior_rate is not None:
            delta = last_rate - prior_rate
            trend = "improving" if delta > 0.05 else "declining" if delta < -0.05 else "steady"

    return {
        "target_phone": target_phone,
        "n_sessions": n_sessions,
        "total_scored": totals["scored"],
        "total_clear": totals["clear"],
        "total_flagged": totals["flagged"],
        "total_not_scored": totals["not_scored"],
        "accuracy_pct": accuracy_pct,
        "position_pct": position_pct,
        "trend": trend,
        "top_substitute": top_substitute,
    }


def template_narration(analysis, child_name):
    name = child_name or "Your child"
    phone = analysis["target_phone"]
    n = analysis["n_sessions"]
    acc = analysis["accuracy_pct"]

    if not n or acc is None:
        return "%s hasn't completed a scored practice session yet." % name

    trend_phrase = {
        "improving": "and it's been trending up recently",
        "declining": "and it's dipped a bit in the most recent session",
        "steady": "and it's held steady across sessions",
    }.get(analysis["trend"], "")

    sentence = "%s has practiced the /%s/ sound over %d session%s, getting it right %d%% of the time%s%s." % (
        name, phone, n, "" if n == 1 else "s", acc,
        " so far" if not trend_phrase else "", (" " + trend_phrase) if trend_phrase else "",
    )

    pos_bits = []
    for pos in ("initial", "medial", "final"):
        pct = analysis["position_pct"].get(pos)
        if pct is not None:
            pos_bits.append("%d%% at the %s" % (pct, POSITION_LABEL[pos]))
    if pos_bits:
        sentence += " By position: " + ", ".join(pos_bits) + "."

    if analysis["total_not_scored"]:
        sentence += (" %d sound%s could not be measured reliably and were left out of these numbers."
                      % (analysis["total_not_scored"], "" if analysis["total_not_scored"] == 1 else "s"))

    return sentence


def _verify(text):
    lowered = text.lower()
    return not any(w in lowered for w in FORBIDDEN_WORDS)


def narrate(analysis, child_name=None):
    """Returns (text, source) where source is 'llm' or 'template'. Never
    raises — any failure degrades to the template."""
    fallback = template_narration(analysis, child_name)

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return fallback, "template"

    prompt = (
        "Write exactly 3 short sentences for a parent, in this fixed order, "
        "each on its own line with no numbering or labels:\n"
        "1. Practice count - how many sessions and words attempted, using "
        "only the numbers given.\n"
        "2. The pattern - name the specific word position (start / middle / "
        "end of words) where practice has been hardest, using only the "
        "numbers given. Phrase it as a plain observation, never as advice: "
        "say 'practice has leaned toward...' or 'X has been trickiest at "
        "the ...', never 'should', 'recommend', or 'suggest'.\n"
        "3. One sentence connecting today's word choices to that pattern - "
        "why practice today includes more of that kind of word.\n\n"
        "Use ONLY the numbers given below - never invent a number, never "
        "use clinical language (no diagnosis, severity, disorder, condition, "
        "treatment, therapy, or recommendations to see a specialist). Output "
        "ONLY the 3 sentences themselves - no preamble, no \"Here are...\", "
        "no heading, no meta-commentary about the task.\n\n"
        "Child's name: %s\nData: %s"
        % (child_name or "the child", analysis)
    )

    try:
        resp = requests.post(
            GROQ_URL,
            headers={"Authorization": "Bearer %s" % api_key},
            json={
                "model": GROQ_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.4,
                "max_tokens": 200,
            },
            timeout=GROQ_TIMEOUT_S,
        )
        resp.raise_for_status()
        text = resp.json()["choices"][0]["message"]["content"].strip()
    except Exception:                                  # noqa: BLE001
        return fallback, "template"

    if not text or not _verify(text):
        return fallback, "template"
    return text, "llm"


def select_next_words(analysis, word_bank):
    """Ask Groq which word-bank indices the next level should weight toward,
    validated against the real bank. Any failure, timeout, or invalid index
    falls back to the deterministic worst-position rule below - Groq can
    never hand back a word that isn't in the bank, and never touches an
    in-progress session, only the *next* one."""
    fallback = _fallback_selection(analysis, word_bank)

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return fallback, "rule"

    valid_indices = {w["index"] for w in word_bank}
    top_sub = analysis.get("top_substitute")
    sub_hint = (
        "The child's most frequent substitution is using /%s/ in place of "
        "/s/ (seen %d time%s). Weight your choice toward words where that "
        "specific confusion would be most exposed - e.g. avoid words already "
        "dominated by other hard-to-distinguish sounds, and prefer words "
        "whose surrounding sounds won't mask a /%s/-for-/s/ swap.\n\n"
        % (top_sub["sound"], top_sub["count"], "" if top_sub["count"] == 1 else "s", top_sub["sound"])
        if top_sub else ""
    )
    prompt = (
        "A child is practicing the /s/ sound. Here is their practice data: "
        "%s\n\n%s"
        "Here is the full list of available practice words, each with "
        "an index, the word position of its /s/ sound, and its phone "
        "sequence: %s\n\n"
        "Reply with ONLY a JSON array of 4-6 word indices (integers from the "
        "list above) that would give the most useful next practice session, "
        "weighted toward whichever position has been hardest and, if given, "
        "toward exposing the child's specific substitution pattern above. "
        "Reply with ONLY the JSON array, nothing else - no explanation, no markdown."
        % (analysis, sub_hint, word_bank)
    )

    try:
        resp = requests.post(
            GROQ_URL,
            headers={"Authorization": "Bearer %s" % api_key},
            json={
                "model": GROQ_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "max_tokens": 100,
            },
            timeout=GROQ_TIMEOUT_S,
        )
        resp.raise_for_status()
        raw = resp.json()["choices"][0]["message"]["content"].strip()
        indices = json.loads(raw)
    except Exception:                                  # noqa: BLE001
        return fallback, "rule"

    if not isinstance(indices, list) or not indices:
        return fallback, "rule"
    clean = [i for i in indices if isinstance(i, int) and i in valid_indices]
    if not clean:
        return fallback, "rule"
    return clean[:6], "llm"


def _fallback_selection(analysis, word_bank):
    """Deterministic: weight toward the worst-scoring position, same signal
    core/policy.js's feedbackForSession already surfaces on the frontend."""
    position_pct = analysis.get("position_pct") or {}
    if not position_pct:
        return [w["index"] for w in word_bank[:4]]
    worst = min(position_pct, key=lambda p: position_pct[p] if position_pct[p] is not None else 100)
    matches = [w["index"] for w in word_bank if w.get("position") == worst]
    return (matches or [w["index"] for w in word_bank])[:6]
