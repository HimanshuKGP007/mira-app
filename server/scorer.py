"""
scorer.py — the live scoring pipeline.

audio -> SNR gate -> CMUdict canonical phones -> wav2vec2 CTC posteriors
      -> CTC forced alignment -> per-phone GOP -> withholding -> markings

No Montreal Forced Aligner: alignment is mira_core.ctc_forced_align, so there is
no subprocess and no conda environment to stand up.
"""

import collections
import io
import math
import re

import numpy as np

import mira_core
import policy

_STATE = {"loaded": False}


# --------------------------------------------------------------------------
# startup
# --------------------------------------------------------------------------

def _pick_device():
    import torch
    if torch.cuda.is_available():
        return "cuda"
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def load(model_id=None, device=None):
    """Load the acoustic model once. Called from the FastAPI lifespan hook.

    Deliberately avoids AutoProcessor: the phoneme tokenizer for this checkpoint
    constructs a `phonemizer` backend (and wants an espeak-ng binary) purely to
    turn text into phones. We never do that — CMUdict supplies the target
    sequence — and all we actually need from the tokenizer is its vocabulary
    table, which is a plain vocab.json on the Hub.
    """
    if _STATE.get("loaded"):
        return _STATE

    import json

    import torch
    from huggingface_hub import hf_hub_download
    from transformers import AutoFeatureExtractor, AutoModelForCTC

    model_id = model_id or policy.MODEL_ID
    device = device or _pick_device()

    feature_extractor = AutoFeatureExtractor.from_pretrained(model_id)
    model = AutoModelForCTC.from_pretrained(model_id).to(device).eval()

    with open(hf_hub_download(model_id, "vocab.json"), encoding="utf-8") as fh:
        vocab = json.load(fh)

    # blank == pad for a CTC head. Prefer the tokenizer config, fall back to the
    # model config, then to the conventional id 0.
    blank_id = None
    try:
        with open(hf_hub_download(model_id, "tokenizer_config.json"), encoding="utf-8") as fh:
            pad_tok = json.load(fh).get("pad_token")
        if isinstance(pad_tok, dict):
            pad_tok = pad_tok.get("content")
        if pad_tok is not None:
            blank_id = vocab.get(pad_tok)
    except Exception:                             # noqa: BLE001
        blank_id = None
    if blank_id is None:
        blank_id = model.config.pad_token_id
    if blank_id is None:
        blank_id = 0

    import cmudict
    cmu = cmudict.dict()

    _STATE.update({
        "loaded": True,
        "torch": torch,
        "feature_extractor": feature_extractor,
        "model": model,
        "device": device,
        "model_id": model_id,
        "vocab": vocab,
        "id2token": {v: k for k, v in vocab.items()},
        "blank_id": int(blank_id),
        "cmu": cmu,
        "target_classes": build_target_classes(vocab),
    })
    return _STATE


def state():
    return _STATE


# --------------------------------------------------------------------------
# audio
# --------------------------------------------------------------------------

TARGET_SR = 16000


def decode_audio(raw_bytes):
    """Bytes -> (mono float32 @ 16 kHz, source_sample_rate). Raises ValueError."""
    import soundfile as sf
    try:
        data, sr = sf.read(io.BytesIO(raw_bytes), dtype="float32", always_2d=True)
    except Exception as exc:                     # noqa: BLE001
        raise ValueError("could not decode audio: %s" % exc) from exc
    if data.size == 0:
        raise ValueError("empty audio")
    mono = data.mean(axis=1).astype(np.float32)
    if sr != TARGET_SR:
        mono = _resample(mono, sr, TARGET_SR)
    return mono, sr


def _resample(x, src, dst):
    if src == dst or x.size == 0:
        return x
    n_out = int(round(x.size * dst / src))
    if n_out <= 1:
        return x
    src_idx = np.linspace(0, x.size - 1, num=n_out, dtype=np.float64)
    lo = np.floor(src_idx).astype(np.int64)
    hi = np.minimum(lo + 1, x.size - 1)
    frac = (src_idx - lo).astype(np.float32)
    return ((1 - frac) * x[lo] + frac * x[hi]).astype(np.float32)


def estimate_snr_db(pcm, sample_rate=TARGET_SR):
    """Quietest decile of 20 ms frames treated as noise, loudest as signal.

    Deliberately crude — it exists to reject an unusable take before spending a
    forward pass on it, not to characterise the room.
    """
    frame = int(sample_rate * 0.02)
    if frame <= 0 or pcm.size < frame * 5:
        return None
    n = pcm.size // frame
    frames = pcm[: n * frame].reshape(n, frame)
    rms = np.sqrt((frames ** 2).mean(axis=1))
    rms.sort()
    noise = float(rms[int(n * 0.1)]) or 1e-8
    signal = float(rms[int(n * 0.9)]) or 1e-8
    if signal <= noise:
        return 0.0
    return round(20.0 * math.log10(signal / max(noise, 1e-8)), 1)


# --------------------------------------------------------------------------
# prompt word -> canonical phones
# --------------------------------------------------------------------------

def canonical_phones(word):
    """Prompt word -> [(arpabet, ipa)].

    Returns None when the word is absent from CMUdict, rather than guessing.
    A missing word must propagate as 'not scored', not as a silently wrong target.
    """
    st = load()
    w = re.sub(r"[^a-z']", "", (word or "").lower())
    if not w:
        return None
    prons = st["cmu"].get(w)
    if not prons:
        return None
    raw = prons[0]                                  # variant 0
    out = []
    for sym in raw:
        # keep the stress digit so canonical_ipa can apply the AH0 -> schwa rule
        ipa = mira_core.canonical_ipa(sym)
        out.append((mira_core.arpabet_base(sym), ipa))
    return out


_VOWEL_CHARS = set("iɪeɛæaɑɒɔoʊuʉʌəɚɝɜɐyøœɶʏɤɯ")


def _token_base(tok):
    """Strip length marks and stress digits from a vocabulary token."""
    return re.sub(r"[0-9ː]", "", tok or "")


def build_target_classes(vocab):
    """canonical IPA -> the vocabulary ids that spell the same phone.

    The espeak vocabulary spells one phone several ways: /ɑ/ also appears as
    `ɑː`, /a/ as `a5`. Scoring against a single bare symbol therefore measures
    the wrong thing — the model puts its probability mass on a marked variant and
    the bare form reads as a near-zero posterior, i.e. a false error on a
    perfectly good vowel.

    So each target gets an equivalence class and GOP is taken against the best
    member of it. Consonants keep their exact identity — that is where this
    method actually separates (59.7% vs 29.5% for vowels in the Stage 2 decode
    analysis), so folding them would throw away the signal. Vowels additionally
    fold through normalize_ipa, which is the same collapse Stage 2 applied when
    it built `phone_norm`, and is why vowels carry the highest error in the
    published per-phoneme table.
    """
    by_base = {}
    for tok, tid in vocab.items():
        if not tok or tok.startswith("<"):
            continue
        by_base.setdefault(_token_base(tok), []).append(tid)

    folded = {}
    for base, ids in by_base.items():
        key = mira_core.normalize_ipa(base)
        if key:
            folded.setdefault(key, []).extend(ids)

    classes = {}
    for base, ids in by_base.items():
        out = list(ids)
        if base and base[0] in _VOWEL_CHARS:
            key = mira_core.normalize_ipa(base)
            out = list(dict.fromkeys(out + folded.get(key, [])))
        classes[base] = out
    return classes


def target_ids_for(ipa, classes, vocab):
    """Equivalence class for one canonical phone, most specific first."""
    if not ipa:
        return []
    base = _token_base(ipa)
    ids = classes.get(base)
    if ids:
        return ids
    tid = vocab.get(ipa)
    return [tid] if tid is not None else []


def word_positions(n):
    """Position tag per phone index, matching Stage 2's tag_position()."""
    if n == 1:
        return ["only"]
    return ["initial"] + ["medial"] * (n - 2) + ["final"]


# --------------------------------------------------------------------------
# the pipeline
# --------------------------------------------------------------------------

def score_utterance(raw_bytes, prompt_word, speaker_age_years=None):
    """Returns a dict that is either a retry envelope or the scored contract."""
    st = load()
    torch = st["torch"]

    # 1. audio ------------------------------------------------------------
    pcm, src_sr = decode_audio(raw_bytes)
    duration_s = pcm.size / TARGET_SR
    snr = estimate_snr_db(pcm)

    # 2. quality gate, BEFORE scoring ------------------------------------
    if duration_s < 0.20:
        return {"status": "retry", "reason": "too_short",
                "snr_db": snr, "duration_s": round(duration_s, 3)}
    if snr is not None and snr < policy.MIN_SNR_DB:
        return {"status": "retry", "reason": "low_snr",
                "snr_db": snr, "duration_s": round(duration_s, 3)}

    # 3. canonical target sequence ---------------------------------------
    canon = canonical_phones(prompt_word)
    if not canon:
        return _all_not_scored(prompt_word, snr,
                               "'%s' is not in the pronunciation dictionary" % prompt_word)

    ipas = [ipa for _, ipa in canon]
    positions = word_positions(len(ipas))

    # 4. phone -> vocabulary token ---------------------------------------
    # build_phone_token_map gives the single canonical id (override -> exact ->
    # MFA table -> normalised -> stripped); the equivalence class widens that to
    # the marked spellings the model actually emits.
    mapping, _unmapped, _report = mira_core.build_phone_token_map(
        st["vocab"], [i for i in ipas if i]
    )
    classes = st["target_classes"]
    targets = [mapping.get(i) if i else None for i in ipas]
    target_sets = [target_ids_for(i, classes, st["vocab"]) or ([t] if t is not None else [])
                   for i, t in zip(ipas, targets)]
    targets = [ts[0] if ts else None for ts in target_sets]
    if all(t is None for t in targets):
        return _all_not_scored(prompt_word, snr, "no target sound could be mapped to the model")

    # Alignment needs a contiguous token sequence; drop unmappable phones from
    # the alignment but keep their slot so the response still lists them.
    align_idx = [k for k, t in enumerate(targets) if t is not None]
    align_targets = [targets[k] for k in align_idx]

    # 5. forward pass -----------------------------------------------------
    inputs = st["feature_extractor"](pcm, sampling_rate=TARGET_SR, return_tensors="pt")
    with torch.no_grad():
        out = st["model"](inputs.input_values.to(st["device"]))
    logits = out.logits[0].float().cpu().numpy()
    logprobs = mira_core.log_softmax_np(logits)
    blank_id = st["blank_id"]

    # 6. CTC forced alignment --------------------------------------------
    path, align_score = mira_core.ctc_forced_align(logprobs, align_targets, blank_id)
    if path is None:
        return {"status": "retry", "reason": "alignment",
                "snr_db": snr, "duration_s": round(duration_s, 3)}
    spans_compact = expand_spans(path, len(align_targets))
    spans = [(None, None)] * len(ipas)
    for slot, span in zip(align_idx, spans_compact):
        spans[slot] = span

    # 7-11. per-phone measurement ----------------------------------------
    phones = []
    for k, (ipa, pos) in enumerate(zip(ipas, positions)):
        lo, hi = spans[k]
        tid = targets[k]
        withheld = policy.is_withheld(ipa) if ipa else False

        post_max = None
        duration_ms = None
        substitute = None
        gop = {}

        if lo is not None and hi is not None and hi > lo and tid is not None:
            # Score against the best-fitting spelling of this phone; the GOP
            # denominator (max over the whole vocabulary) is untouched, so a
            # genuinely wrong production still scores low.
            best_id = _best_class_member(logprobs, lo, hi, target_sets[k]) or tid
            gop = mira_core.gop_variants(logprobs, lo, hi, best_id, blank_id)
            post_max = gop.get("post_max")
            duration_ms = round((hi - lo) * policy.SEC_PER_FRAME * 1000.0, 1)
            substitute = _substitute_for(logprobs, lo, hi, set(target_sets[k]),
                                         blank_id, st["id2token"])

        marking, reason = policy.decide_marking(
            post_max=post_max, duration_ms=duration_ms,
            substitute=substitute, withheld=withheld,
        )
        if marking != "substituted":
            substitute = None
        if tid is None and marking == "not_scored" and reason is None:
            reason = "this sound is not in the model's inventory"

        entry = {
            "target": ipa,
            "target_arpabet": canon[k][0],
            "position": pos,
            "marking": marking,
            "score": None,                       # no 0-2 score without the trained model
            "confidence": None if marking == "not_scored" else _round(post_max),
            "confidence_kind": policy.CONFIDENCE_KIND,
            "duration_ms": duration_ms,
            "flags": [],
        }
        if substitute:
            entry["substitute"] = substitute
        if reason:
            entry["reason"] = reason
        if gop:
            entry["gop"] = {k2: _round(v) for k2, v in gop.items()
                            if k2 in ("gop_mean", "gop_max", "post_mean", "post_max")}
        phones.append(entry)

    scored = [p for p in phones if p["marking"] != "not_scored"]
    return {
        "utterance_id": "live-%s-%d" % (re.sub(r"[^a-z]", "", (prompt_word or "x").lower()),
                                        int(abs(hash((prompt_word, len(pcm)))) % 10 ** 8)),
        "prompt_word": prompt_word,
        "speaker_age_years": speaker_age_years,
        "phones": phones,
        "quality_gate": {
            "passed": True,
            "snr_db": snr,
            "alignment_quality": _round(_alignment_quality(align_score, len(path))),
            "duration_s": round(duration_s, 3),
        },
        "summary": {
            "total": len(phones),
            "scored": len(scored),
            "not_scored": len(phones) - len(scored),
        },
        "provenance": policy.provenance(st["device"]),
    }


def expand_spans(path, n_targets):
    """Turn CTC spikes into contiguous phone windows.

    This is the one place where replacing MFA with CTC forced alignment changes
    the measurement, and it has to be handled explicitly. MFA returns true phone
    boundaries, so a phone's window is its actual duration. CTC is peaky: the
    Viterbi path parks most frames on blank and gives each real token one or two
    spike frames. Measuring GOP over a single frame is both noisy and, against a
    30 ms floor calibrated on MFA durations, indistinguishable from an omission.

    So every frame is attributed to a phone: a run of blanks between two tokens
    is split down the middle, leading blanks go to the first phone and trailing
    blanks to the last. The result is contiguous, covers the whole utterance, and
    approximates the boundaries MFA would have produced.
    """
    owner = [None] * len(path)
    for t, s in enumerate(path):
        if s % 2 == 1:
            i = (s - 1) // 2
            if i < n_targets:
                owner[t] = i

    known = [t for t, o in enumerate(owner) if o is not None]
    if not known:
        return [(None, None)] * n_targets

    # leading and trailing blanks
    for t in range(known[0]):
        owner[t] = owner[known[0]]
    for t in range(known[-1] + 1, len(owner)):
        owner[t] = owner[known[-1]]

    # interior blank runs: first half to the left phone, second half to the right
    t = 0
    while t < len(owner):
        if owner[t] is not None:
            t += 1
            continue
        start = t
        while t < len(owner) and owner[t] is None:
            t += 1
        left, right = owner[start - 1], owner[t] if t < len(owner) else owner[start - 1]
        mid = start + (t - start) // 2
        for u in range(start, mid):
            owner[u] = left
        for u in range(mid, t):
            owner[u] = right

    spans = []
    for i in range(n_targets):
        frames = [t for t, o in enumerate(owner) if o == i]
        spans.append((frames[0], frames[-1] + 1) if frames else (None, None))
    return spans


def _best_class_member(logprobs, lo, hi, ids):
    """Which spelling of this phone the model favours over the window."""
    ids = [i for i in ids if i is not None]
    if not ids:
        return None
    if len(ids) == 1:
        return ids[0]
    win = logprobs[lo:hi]
    return max(ids, key=lambda i: float(win[:, i].max()))


def _substitute_for(logprobs, lo, hi, target_ids, blank_id, id2token):
    """What the model actually heard instead, from an unconstrained argmax over
    the phone's own frames. Consonants separate well this way; vowels much less
    so, which is why this is reported as an annotation and never as the score."""
    win = logprobs[lo:hi]
    if win.size == 0:
        return None
    arg = win.argmax(axis=1)
    counts = collections.Counter(int(a) for a in arg if int(a) != blank_id)
    if not counts:
        return None
    top, _n = counts.most_common(1)[0]
    if top in target_ids:            # a marked spelling of the target is not a substitution
        return None
    tok = id2token.get(top)
    if not tok or not tok.strip() or tok.startswith("<"):
        return None
    return tok


def _alignment_quality(align_score, n_frames):
    """Mean per-frame log-likelihood of the chosen path, squashed to 0..1.
    A rough proxy: low means the boundaries were guessed."""
    if align_score is None or not n_frames:
        return None
    per_frame = align_score / n_frames
    return float(mira_core.sigmoid(per_frame + 2.0))


def _all_not_scored(prompt_word, snr, reason):
    return {
        "utterance_id": "live-unscorable",
        "prompt_word": prompt_word,
        "phones": [],
        "quality_gate": {"passed": True, "snr_db": snr, "alignment_quality": None},
        "summary": {"total": 0, "scored": 0, "not_scored": 0},
        "unscorable_reason": reason,
        "provenance": policy.provenance(_STATE.get("device", "cpu")),
    }


def _round(x, nd=4):
    if x is None:
        return None
    try:
        if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
            return None
        return round(float(x), nd)
    except (TypeError, ValueError):
        return None
