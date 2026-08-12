"""
insights.py — Module 2, minimal version: turn session history into a parent
note.

Two steps, both fail closed:

  compute_analysis()  ordinary arithmetic over the session history the app
                       already stores client-side. No model, no torch import,
                       ships from numbers that are already on screen elsewhere.

  narrate()            hands ONLY those numbers to Groq for 3-4 sentences.
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
    # Counted over EVERY attempt, not just the one that ended each word.
    # A word answered correctly on the third go, after the sound was replaced
    # once and dropped once, used to contribute a single "clear" here and
    # nothing else — the two errors on the way were not in the numbers the
    # note was written from, so the note could not mention them.
    marking_counts = {"correct": 0, "substituted": 0, "omitted": 0,
                      "assimilated": 0, "not_scored": 0}
    # Same markings, but split by where in the word they happened — a global
    # "mostly omitted" figure can't tell a parent that the omissions are all
    # at the end of words while the middle is fine; this can.
    position_marking_counts = {}
    attempts_total = 0
    unusable_takes = 0
    words_retried = 0
    words_recovered = 0

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
            attempts = item.get("attempts")
            if not attempts:
                # session recorded before the attempt log existed: the final
                # instances are all there is, and are treated as one attempt.
                attempts = [{"outcome": "scored", "instances": item.get("instances", []),
                             "verdict": item.get("verdict")}]
            scored_attempts = [a for a in attempts if a.get("outcome", "scored") == "scored"]
            attempts_total += len(scored_attempts)
            unusable_takes += len(attempts) - len(scored_attempts)
            if len(scored_attempts) > 1:
                words_retried += 1
                if (scored_attempts[0].get("verdict") != "correct"
                        and scored_attempts[-1].get("verdict") == "correct"):
                    words_recovered += 1
            for a in scored_attempts:
                for inst in a.get("instances", []):
                    marking = inst.get("marking")
                    if marking in marking_counts:
                        marking_counts[marking] += 1
                    pos = inst.get("position")
                    if pos and marking in marking_counts:
                        pmc = position_marking_counts.setdefault(
                            pos, {"correct": 0, "substituted": 0,
                                  "omitted": 0, "assimilated": 0, "not_scored": 0})
                        pmc[marking] += 1
                    sub = inst.get("substitute")
                    if sub:
                        substitute_counts[sub] = substitute_counts.get(sub, 0) + 1

    top_substitute = None
    if substitute_counts:
        sub, count = max(substitute_counts.items(), key=lambda kv: kv[1])
        top_substitute = {"sound": sub, "count": count}

    # Which way the errors go is a different fact from how many there are, and
    # the two call for different practice. Left out is not the same as swapped.
    errors = {k: marking_counts[k] for k in ("substituted", "omitted", "assimilated")}
    dominant_error = None
    if any(errors.values()):
        ranked = sorted(errors, key=lambda k: errors[k], reverse=True)
        # A tie is not a dominant pattern. Saying "more often left out" when
        # it happened exactly as often as the alternative would be inventing
        # a finding out of a coin toss.
        if len(ranked) < 2 or errors[ranked[0]] > errors[ranked[1]]:
            dominant_error = ranked[0]

    accuracy_pct = (round(100 * totals["clear"] / totals["scored"])
                    if totals["scored"] else None)
    position_pct = {
        pos: (round(100 * v["clear"] / v["scored"]) if v["scored"] else None)
        for pos, v in by_position.items()
    }

    # Enough attempts at a position before either praising or flagging it —
    # a 1-for-1 "100%" or "0%" at some position is noise, not a finding.
    MIN_POSITION_N = 4
    qualifying_positions = {
        pos: pct for pos, pct in position_pct.items()
        if pct is not None and by_position[pos]["scored"] >= MIN_POSITION_N
    }
    # A strength worth naming: clearly ahead of the rest, not just nominally
    # the best of a close field.
    strongest_position = None
    if qualifying_positions:
        ranked_pos = sorted(qualifying_positions, key=lambda p: qualifying_positions[p], reverse=True)
        best_pct = qualifying_positions[ranked_pos[0]]
        runner_up_pct = qualifying_positions[ranked_pos[1]] if len(ranked_pos) > 1 else None
        if best_pct >= 85 and (runner_up_pct is None or best_pct - runner_up_pct >= 10):
            strongest_position = ranked_pos[0]

    # Which error dominates at the weakest position specifically — "hardest
    # at the end of words, and mostly left out there" is a different, more
    # actionable finding than the global dominant_error.
    weakest_position_error = None
    if qualifying_positions:
        weakest_pos = min(qualifying_positions, key=lambda p: qualifying_positions[p])
        pmc = position_marking_counts.get(weakest_pos) or {}
        perrors = {k: pmc.get(k, 0) for k in ("substituted", "omitted", "assimilated")}
        if sum(perrors.values()) >= 3:
            pranked = sorted(perrors, key=lambda k: perrors[k], reverse=True)
            if perrors[pranked[0]] > perrors[pranked[1]]:
                weakest_position_error = {
                    "position": weakest_pos, "error": pranked[0], "count": perrors[pranked[0]],
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
        "strongest_position": strongest_position,
        "weakest_position_error": weakest_position_error,
        # everything below is measured over every attempt, retries included
        "attempts_total": attempts_total,
        "unusable_takes": unusable_takes,
        "words_retried": words_retried,
        "words_recovered": words_recovered,
        "marking_counts_all_attempts": marking_counts,
        "position_marking_counts_all_attempts": position_marking_counts,
        "error_counts_all_attempts": errors,
        "dominant_error": dominant_error,
    }


def _times(n):
    return "once" if n == 1 else "twice" if n == 2 else "%d times" % n


def template_bullets(analysis, child_name):
    """Deterministic fallback: up to 5 bullet points, `**bold**`-marked on
    the figures that matter, covering more than accuracy alone. Skips any
    bullet its underlying data doesn't support — a first session with
    almost nothing scored should come back short, not padded."""
    name = child_name or "Your child"
    phone = analysis["target_phone"]
    n = analysis["n_sessions"]
    acc = analysis["accuracy_pct"]

    if not n or acc is None:
        return ["%s hasn't completed a scored practice session yet." % name]

    bullets = []

    trend_phrase = {
        "improving": ", and it's been trending up recently",
        "declining": ", and it dipped a bit in the most recent session",
        "steady": ", and it's held steady across sessions",
    }.get(analysis["trend"], "")
    bullets.append(
        "%s has practiced the /%s/ sound over **%d session%s**, getting it "
        "right **%d%%** of the time%s."
        % (name, phone, n, "" if n == 1 else "s", acc, trend_phrase)
    )

    # The specific position+error combination beats a generic position
    # breakdown when there's enough data for one — "hardest at the end,
    # mostly left out there" is something a parent can actually listen for.
    wpe = analysis.get("weakest_position_error")
    if wpe:
        how = {"omitted": "left out", "substituted": "swapped for another sound",
               "assimilated": "blended into a neighbouring sound"}[wpe["error"]]
        bullets.append(
            "The /%s/ has been hardest at the **%s of words**, where it's most "
            "often **%s** (%s)."
            % (phone, POSITION_LABEL[wpe["position"]], how, _times(wpe["count"]))
        )
    else:
        pos_bits = []
        for pos in ("initial", "medial", "final"):
            pct = analysis["position_pct"].get(pos)
            if pct is not None:
                pos_bits.append("**%d%%** at the %s" % (pct, POSITION_LABEL[pos]))
        if pos_bits:
            bullets.append("By word position, accuracy was " + ", ".join(pos_bits) + ".")

    # Every attempt, not only the one that ended each word. Which way the
    # errors went is the part a parent can actually listen for at home.
    errors = analysis.get("error_counts_all_attempts") or {}
    err_bits = []
    if errors.get("omitted"):
        err_bits.append("left out **%s**" % _times(errors["omitted"]))
    if errors.get("substituted"):
        sub = analysis.get("top_substitute")
        err_bits.append("swapped for a different sound **%s**%s" % (
            _times(errors["substituted"]),
            ("" if not sub else
             (", /%s/" % sub["sound"]) if errors["substituted"] == 1
             else (", most often **/%s/**" % sub["sound"]))))
    if errors.get("assimilated"):
        err_bits.append("blended into a neighbouring sound **%s**" % _times(errors["assimilated"]))
    total_attempts = analysis.get("attempts_total") or 0
    if err_bits and total_attempts:
        bullets.append(
            "Across %s, the /%s/ was %s."
            % ("the single recorded attempt" if total_attempts == 1
               else "all %d recorded attempts" % total_attempts,
               phone, " and ".join(err_bits))
        )

    # A strength is as much an insight as a weak spot — it tells a parent
    # what's already working, not just what to fix.
    sp = analysis.get("strongest_position")
    if sp:
        bullets.append(
            "The /%s/ at the **%s of words** is solid, correct **%d%%** of the "
            "time — a real strength to build on."
            % (phone, POSITION_LABEL[sp], analysis["position_pct"][sp])
        )

    retried = analysis.get("words_retried") or 0
    if retried:
        recovered = analysis.get("words_recovered") or 0
        bullets.append(
            "**%d word%s** took more than one try, and **%s** got there by "
            "the last attempt."
            % (retried, "" if retried == 1 else "s",
               "%d of them" % recovered if recovered else "none of them")
        )

    if analysis["total_not_scored"]:
        bullets.append(
            "**%d sound%s** could not be measured reliably and were left "
            "out of these numbers."
            % (analysis["total_not_scored"], "" if analysis["total_not_scored"] == 1 else "s")
        )

    return bullets[:5]


def _verify(bullets):
    lowered = " ".join(bullets).lower()
    return not any(w in lowered for w in FORBIDDEN_WORDS)


def narrate(analysis, child_name=None):
    """Returns (bullets, source) where bullets is a list of 1-5 markdown
    strings (only `**bold**` allowed) and source is 'llm' or 'template'.
    Never raises — any failure degrades to the template."""
    fallback = template_bullets(analysis, child_name)

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return fallback, "template"

    prompt = (
        "Write 3 to 5 short bullet points for a parent about their child's "
        "speech practice. Cover more than accuracy alone - pick whichever of "
        "these the data actually supports, skip any that aren't supported, "
        "and never pad to hit 5:\n"
        "- Practice volume: how many sessions and attempts, and the overall "
        "accuracy trend.\n"
        "- The hardest spot: which word position (start / middle / end) has "
        "been hardest, and, using weakest_position_error if present, what "
        "specifically happens there (left out vs swapped for another sound "
        "vs blended into a neighbour) - these are different findings and "
        "must not be conflated.\n"
        "- The error pattern overall (error_counts_all_attempts, "
        "top_substitute): omission and substitution are different problems, "
        "name whichever dominates.\n"
        "- A genuine strength: if strongest_position is set, or "
        "words_recovered is a meaningful fraction of words_retried, say "
        "what's going well - this matters as much as what's hard.\n"
        "- Retry behaviour: whether words that took more than one attempt "
        "usually got there in the end.\n\n"
        "Rules: use ONLY the numbers given below, never invent one. Never "
        "use clinical language (no diagnosis, severity, disorder, condition, "
        "treatment, therapy, or recommendations to see a specialist). Phrase "
        "everything as a plain observation, never as advice - no 'should', "
        "'recommend', or 'suggest'. Bold the key figures and terms in each "
        "bullet using **double asterisks**, nothing fancier. Reply with "
        "ONLY a JSON array of the bullet strings (no numbering, no "
        "markdown list markers, no preamble, no explanation) - e.g. "
        "[\"...\", \"...\"].\n\n"
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
                "max_tokens": 450,
            },
            timeout=GROQ_TIMEOUT_S,
        )
        resp.raise_for_status()
        raw = resp.json()["choices"][0]["message"]["content"].strip()
        bullets = json.loads(raw)
    except Exception:                                  # noqa: BLE001
        return fallback, "template"

    if (not isinstance(bullets, list) or not bullets
            or not all(isinstance(b, str) and b.strip() for b in bullets)):
        return fallback, "template"
    bullets = [b.strip() for b in bullets][:5]
    if not _verify(bullets):
        return fallback, "template"
    return bullets, "llm"


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
    # Omission and substitution are different problems and want different
    # words, so the selector is told which one dominates rather than being
    # left to infer it from an accuracy percentage that cannot show it.
    err_hint = ""
    if analysis.get("dominant_error") == "omitted":
        err_hint = (
            "The child's errors are most often OMISSIONS - the /s/ is left "
            "out of the word entirely (%d times), rather than replaced. "
            "Prefer words where a dropped /s/ is unmistakable, such as final "
            "position and /s/ clusters.\n\n"
            % (analysis.get("error_counts_all_attempts") or {}).get("omitted", 0)
        )

    prompt = (
        "A child is practicing the /s/ sound. Here is their practice data: "
        "%s\n\n%s%s"
        "Here is the full list of available practice words, each with "
        "an index, the word position of its /s/ sound, and its phone "
        "sequence: %s\n\n"
        "Reply with ONLY a JSON array of 4-6 word indices (integers from the "
        "list above) that would give the most useful next practice session, "
        "weighted toward whichever position has been hardest and, if given, "
        "toward exposing the child's specific error pattern above. "
        "Reply with ONLY the JSON array, nothing else - no explanation, no markdown."
        % (analysis, sub_hint, err_hint, word_bank)
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
