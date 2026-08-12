"""
mira_core — ported verbatim from Stage 2 of the Mira notebooks (CORE_VERSION 2.1.0).

This file is the source of truth for the measurement primitives. It is copied
rather than paraphrased on purpose: Stage 4 reimplemented several of these and
got them subtly wrong (it pooled mean/max/min where training used mean/std/max,
it dropped the (path, score) unpack from ctc_forced_align, and it looked for
`prev_` columns where Stage 2 emits `prev1_`). Stage 4 has zero cell outputs —
it was never executed. Stage 2 is what actually ran.

Everything here is pure numpy + stdlib. No torch, no MFA, no TextGrid.
"""

import math
import re
import unicodedata

import numpy as np

CORE_VERSION = "2.1.0"

# ---------------------------------------------------------------------------
# §1  symbol tables
# ---------------------------------------------------------------------------

# NOTE: "ɡ" below is U+0261 LATIN SMALL LETTER SCRIPT G, not ASCII "g".
# Getting this wrong makes every /g/ miss the model vocabulary.

REFERENCE_ARPABET_IPA = {
    "P": "p", "B": "b", "T": "t", "D": "d", "K": "k", "G": "ɡ",
    "F": "f", "V": "v", "TH": "θ", "DH": "ð", "S": "s", "Z": "z",
    "SH": "ʃ", "ZH": "ʒ", "HH": "h", "CH": "tʃ", "JH": "dʒ",
    "M": "m", "N": "n", "NG": "ŋ", "L": "l", "R": "ɹ", "W": "w", "Y": "j",
}

ARPABET_TO_IPA = {
    "AA": "ɑ", "AE": "æ", "AH": "ʌ", "AO": "ɔ", "AW": "aʊ", "AY": "aɪ",
    "EH": "ɛ", "ER": "ɚ", "EY": "eɪ", "IH": "ɪ", "IY": "i", "OW": "oʊ",
    "OY": "ɔɪ", "UH": "ʊ", "UW": "u",
    "P": "p", "B": "b", "T": "t", "D": "d", "K": "k", "G": "ɡ",
    "F": "f", "V": "v", "TH": "θ", "DH": "ð", "S": "s", "Z": "z",
    "SH": "ʃ", "ZH": "ʒ", "HH": "h", "CH": "tʃ", "JH": "dʒ",
    "M": "m", "N": "n", "NG": "ŋ", "L": "l", "R": "ɹ", "W": "w", "Y": "j",
}

MFA_TO_ESPEAK = {
    # diphthongs written differently by the two conventions
    "aj": "aɪ", "aw": "aʊ", "ej": "eɪ", "ow": "oʊ", "oj": "ɔɪ",
    # dental stops the model does not distinguish from alveolar
    "t̪": "t", "d̪": "d",
    # affricates written as two symbols by MFA
    "tʃ": "tʃ", "dʒ": "dʒ",
    # syllabics
    "n̩": "n", "l̩": "l", "m̩": "m",
    # rhotics
    "ɹ": "ɹ", "ɻ": "ɹ", "ɝ": "ɚ",
    # diphthong variants the first pass missed on the full corpus
    "ɔj": "ɔɪ", "əw": "oʊ",
    # labialised and palatalised stops: the model has no such tokens, so they
    # resolve to the plain place of articulation rather than being dropped
    "cʷ": "k", "kʷ": "k", "ɡʷ": "ɡ", "tʷ": "t", "ʈʲ": "t", "ʈ": "t", "ɖ": "d",
    "cʰ": "k", "c": "k", "ɟ": "ɡ",
}

VOWEL_EQUIV = {
    "ɪ": "i", "ʊ": "u", "ɐ": "a", "ɑ": "a", "ɒ": "a", "ʌ": "a",
    "ɛ": "e", "ə": "a", "ɜ": "a",
}


# ---------------------------------------------------------------------------
# §2  small helpers
# ---------------------------------------------------------------------------

def is_missing(x):
    if x is None:
        return True
    if isinstance(x, float) and math.isnan(x):
        return True
    if isinstance(x, str) and not x.strip():
        return True
    return False


_is_missing = is_missing  # Stage 2 used the private name inside build_phone_token_map


def normalize_ipa(s):
    """Fold cosmetic notation differences. Deliberately conservative: it does not
    fold diphthongs, dentals, or anything that could be a real substitution."""
    if s is None:
        return None
    s = re.sub(r"[0-9]", "", s)
    s = s.replace("ː", "").strip()
    s = VOWEL_EQUIV.get(s, s)
    return s if s else None


def strip_diacritics(s):
    """Drop combining marks. Used only for phone-to-vocab matching, never for
    deciding whether two productions are the same sound."""
    if s is None:
        return None
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


def arpabet_base(p):
    """Strip the stress digit. AH1 and AH0 are the same phoneme."""
    if is_missing(p):
        return None
    return re.sub(r"[0-9]+$", "", str(p).strip().upper()) or None


def canonical_ipa(arpabet):
    """The citation realisation. Unstressed AH is schwa, which matters because it
    is the single most common vowel in the corpus.

    Pass the RAW ARPABET symbol (with its stress digit) so the AH0 rule can fire.
    """
    b = arpabet_base(arpabet)
    if b is None:
        return None
    if b == "AH" and str(arpabet).endswith("0"):
        return "ə"
    return ARPABET_TO_IPA.get(b)


def sigmoid(z):
    return 1.0 / (1.0 + np.exp(-np.clip(z, -50, 50)))


def log_softmax_np(logits, axis=-1):
    m = np.max(logits, axis=axis, keepdims=True)
    shifted = logits - m
    return shifted - np.log(np.sum(np.exp(shifted), axis=axis, keepdims=True))


# ---------------------------------------------------------------------------
# §3  phone -> vocabulary token
# ---------------------------------------------------------------------------

def build_phone_token_map(vocab, phones, extra=None):
    """Map each phone label to a token id in the model vocabulary.

    vocab:  dict token string -> id, straight from the tokenizer
    phones: iterable of phone labels seen in the alignment
    extra:  optional additional phone->token overrides, applied first

    Resolution order, most specific first, so a hand-written override always wins
    over a fuzzy match: explicit override, exact vocab hit, MFA->espeak table,
    normalised hit, diacritic-stripped hit. Anything unresolved is reported rather
    than guessed at, because a wrong token id produces a confidently wrong GOP.
    """
    extra = extra or {}
    mapping, unmapped, report = {}, [], []

    for p in sorted(set(x for x in phones if not _is_missing(x))):
        route, tok = None, None
        candidates = [
            ("override", extra.get(p)),
            ("exact", p if p in vocab else None),
            ("mfa_table", MFA_TO_ESPEAK.get(p)),
            ("normalised", normalize_ipa(p)),
            ("stripped", strip_diacritics(p)),
        ]
        for name, cand in candidates:
            if cand is not None and cand in vocab:
                route, tok = name, cand
                break
        if tok is None:
            unmapped.append(p)
            report.append({"phone": p, "route": "UNMAPPED", "token": None, "token_id": None})
        else:
            mapping[p] = vocab[tok]
            report.append({"phone": p, "route": route, "token": tok, "token_id": vocab[tok]})

    coverage = len(mapping) / max(len(mapping) + len(unmapped), 1)
    return mapping, unmapped, {"coverage": coverage, "detail": report,
                               "n_mapped": len(mapping), "n_unmapped": len(unmapped)}


# ---------------------------------------------------------------------------
# §4  frames
# ---------------------------------------------------------------------------

def frame_span(start_s, end_s, sec_per_frame, n_valid_frames):
    """Convert a time window to a half-open frame range, clipped to the frames
    that correspond to real audio. Padding frames must never enter a window: the
    model attends over them and emits tokens there, and letting those in was
    silently corrupting windows near the end of short utterances in a padded batch.
    """
    if sec_per_frame <= 0 or n_valid_frames <= 0:
        return 0, 0
    lo = int(math.floor(start_s / sec_per_frame))
    hi = int(math.ceil(end_s / sec_per_frame))
    lo = max(0, min(lo, n_valid_frames))
    hi = max(0, min(hi, n_valid_frames))
    if hi <= lo:
        hi = min(lo + 1, n_valid_frames)
    return lo, hi


# ---------------------------------------------------------------------------
# §5  GOP
# ---------------------------------------------------------------------------

GOP_VARIANTS = ["gop_mean", "gop_max", "gop_noblank", "gop_renorm", "post_mean", "post_max"]


def gop_variants(logprobs, lo, hi, target_id, blank_id):
    """GOP over frames [lo, hi) for one target phone.

    logprobs: [T, V] log-softmax over the model vocabulary
    Returns a dict of variants, all None if the window is empty or the target has
    no vocabulary id. Never returns a fabricated zero for a missing target.
    """
    out = {k: None for k in GOP_VARIANTS}
    out["n_frames"] = 0
    if target_id is None or hi <= lo:
        return out

    win = logprobs[lo:hi]                       # [n, V]
    n = win.shape[0]
    out["n_frames"] = int(n)

    tgt = win[:, target_id]                      # [n]
    best = win.max(axis=1)                       # [n]
    ratio = tgt - best                           # <= 0

    out["gop_mean"] = float(ratio.mean())
    out["gop_max"] = float(ratio.max())
    out["post_mean"] = float(np.exp(tgt).mean())
    out["post_max"] = float(np.exp(tgt).max())

    argmax = win.argmax(axis=1)
    keep = argmax != blank_id
    if keep.any():
        out["gop_noblank"] = float(ratio[keep].mean())

    # renormalise the posterior over non-blank tokens, then recompute the ratio
    mask = np.ones(win.shape[1], dtype=bool)
    mask[blank_id] = False
    sub = win[:, mask]
    sub_norm = sub - np.log(np.sum(np.exp(sub), axis=1, keepdims=True))
    if target_id != blank_id:
        sub_idx = target_id - 1 if target_id > blank_id else target_id
        tgt_n = sub_norm[:, sub_idx]
        best_n = sub_norm.max(axis=1)
        out["gop_renorm"] = float((tgt_n - best_n).mean())
    return out


def lpp_lpr_features(logprobs, lo, hi, canonical_id, phone_ids):
    """logprobs: [T, V]. phone_ids: ordered list of vocabulary ids for the phone
    inventory. Returns (lpp, lpr_vector) with lpr aligned to phone_ids, or
    (None, None) when the window is empty or the canonical phone has no id."""
    if canonical_id is None or hi <= lo or not phone_ids:
        return None, None
    win = logprobs[lo:hi]
    means = win[:, phone_ids].mean(axis=0)
    try:
        k = phone_ids.index(canonical_id)
    except ValueError:
        return None, None
    lpp = float(means[k])
    return lpp, (lpp - means).astype(np.float32)


def pool_hidden(hidden, lo, hi):
    """Mean, std and max pooling of a hidden-state block over a window.

    Intermediate transformer layers carry more phonetic detail than the CTC output
    layer, which has been squeezed toward a decoding decision.

    NOTE: mean/std/max. Stage 4 used mean/max/min; that was never executed and is
    wrong relative to what trained the scorer.
    """
    if hi <= lo:
        return None
    win = hidden[lo:hi]
    return np.concatenate([win.mean(axis=0), win.std(axis=0), win.max(axis=0)]).astype(np.float32)


# ---------------------------------------------------------------------------
# §6  CTC forced alignment  (replaces Montreal Forced Aligner entirely)
# ---------------------------------------------------------------------------

NEG_INF = -1e30


def ctc_forced_align(logprobs, targets, blank_id):
    """Viterbi-align a known target token sequence to CTC log-probabilities.

    Returns (path, score) where path[t] is the index into the blank-extended
    sequence. Returns (None, None) when alignment is impossible, e.g. fewer frames
    than the extended sequence requires, rather than returning a wrong path.
    """
    T, V = logprobs.shape
    n = len(targets)
    if n == 0 or T == 0:
        return None, None

    ext = [blank_id]
    for tk in targets:
        ext.append(tk)
        ext.append(blank_id)
    S = len(ext)

    min_frames = n + sum(1 for i in range(1, n) if targets[i] == targets[i - 1])
    if T < min_frames:
        return None, None

    alpha = np.full((T, S), NEG_INF, dtype=np.float64)
    back = np.zeros((T, S), dtype=np.int32)

    alpha[0, 0] = logprobs[0, ext[0]]
    if S > 1:
        alpha[0, 1] = logprobs[0, ext[1]]

    for t in range(1, T):
        for s in range(S):
            best_prev, best_s = alpha[t - 1, s], s
            if s - 1 >= 0 and alpha[t - 1, s - 1] > best_prev:
                best_prev, best_s = alpha[t - 1, s - 1], s - 1
            if (s - 2 >= 0 and ext[s] != blank_id and ext[s] != ext[s - 2]
                    and alpha[t - 1, s - 2] > best_prev):
                best_prev, best_s = alpha[t - 1, s - 2], s - 2
            if best_prev <= NEG_INF / 2:
                continue
            alpha[t, s] = best_prev + logprobs[t, ext[s]]
            back[t, s] = best_s

    end_candidates = [S - 1] + ([S - 2] if S >= 2 else [])
    end = max(end_candidates, key=lambda s: alpha[T - 1, s])
    if alpha[T - 1, end] <= NEG_INF / 2:
        return None, None

    path = [0] * T
    s = end
    for t in range(T - 1, -1, -1):
        path[t] = s
        s = int(back[t, s])
    return path, float(alpha[T - 1, end])


def spans_from_path(path, n_targets):
    """Frame span per target from a forced-alignment path. Extended-sequence index
    2i+1 is target i; blanks are index 2i. A target that received no frames gets
    (None, None) rather than a zero-width guess."""
    spans = [[None, None] for _ in range(n_targets)]
    for t, s in enumerate(path):
        if s % 2 == 1:
            i = (s - 1) // 2
            if i < n_targets:
                if spans[i][0] is None:
                    spans[i][0] = t
                spans[i][1] = t + 1
    return [tuple(x) for x in spans]
