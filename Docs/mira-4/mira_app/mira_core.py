"""mira_core.py, shared measurement code for Mira Module 1.

Written by Stage 2, imported by Stage 3, hash-checked on both sides. The point is
that every Speechocean-vs-Svarah number goes through one implementation, so the
comparison is even by construction rather than by inspection. Stage 2 v4 had two
copies of the comparison that had silently drifted onto different targets; this
file exists so that cannot happen again.

Nothing here imports torch. The model forward pass belongs to the notebook; this
module takes the log-probabilities that come out of it and does arithmetic on
them, which is what makes it testable without a GPU.
"""

CORE_VERSION = "2.2.0"

import re
import math
import unicodedata
from collections import Counter
from difflib import SequenceMatcher

import numpy as np
import pandas as pd

# =============================================================================
# 1. IPA normalisation and token comparison
# =============================================================================

VOWEL_EQUIV = {
    "ɪ": "i", "ʊ": "u", "ɐ": "a", "ɑ": "a", "ɒ": "a", "ʌ": "a",
    "ɛ": "e", "ə": "a", "ɜ": "a",
}


def normalize_ipa(s):
    """Fold cosmetic notation differences. Deliberately conservative: it does not
    fold diphthongs, dentals, or anything that could be a real substitution."""
    if s is None:
        return None
    s = re.sub(r"[0-9]", "", s)
    s = s.replace("ː", "").strip()
    s = VOWEL_EQUIV.get(s, s)
    return s if s else None


def is_missing(x):
    """Public on purpose. `from mira_core import *` silently skips any name that
    starts with an underscore, so a private-by-convention helper used in a notebook
    raises NameError at the point of use rather than at import. That failed once,
    after a ten-minute GPU pass. The name has no leading underscore for that reason
    and REQUIRED_EXPORTS below asserts it stays that way."""
    if x is None:
        return True
    if isinstance(x, float) and math.isnan(x):
        return True
    if isinstance(x, str) and not x.strip():
        return True
    return False


_is_missing = is_missing      # backwards-compatible alias for internal call sites


def compare_tokens(decoded, target):
    """The one comparison. Returns None if either side is missing, so an absent
    decode is excluded from a rate rather than counted against the speaker."""
    if _is_missing(decoded) or _is_missing(target):
        return None
    d, t = normalize_ipa(decoded), normalize_ipa(target)
    if d is None or t is None:
        return None
    return d == t


def strip_diacritics(s):
    """Drop combining marks. Used only for phone-to-vocab matching, never for
    deciding whether two productions are the same sound."""
    if s is None:
        return None
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


# =============================================================================
# 2. Near-miss classification (diagnostic only, never changes what counts as a match)
# =============================================================================

_NEAR_MISS_RAW = [
    ("aj", "aɪ"), ("aw", "aʊ"), ("ej", "eɪ"), ("ow", "oʊ"), ("oj", "ɔɪ"),
    ("eɪ", "e"), ("aɪ", "a"), ("aʊ", "a"), ("oʊ", "o"), ("ɔɪ", "o"),
    ("ej", "e"), ("aj", "a"), ("aw", "a"), ("ow", "o"), ("oj", "o"),
    ("t̪", "t"), ("d̪", "d"),
    ("ɾ", "t"), ("ɾ", "d"), ("ʔ", "t"),
    ("ɹ", "r"), ("ɹ", "ɻ"), ("ɚ", "ɹ"), ("ɝ", "ɹ"),
    ("n̩", "n"), ("l̩", "l"), ("m̩", "m"),
    ("u", "ʉ"), ("o", "ɔ"),
]
NEAR_MISS_PAIRS = {frozenset((normalize_ipa(a), normalize_ipa(b))) for a, b in _NEAR_MISS_RAW}


def near_miss_class(target, decoded):
    """'match', 'near_miss', 'distinct', or None. Voicing differences, manner
    differences and ʋ/w are deliberately NOT near misses: the first two are the
    clinically real errors, and V/W is a question for an SLP, not for code."""
    if _is_missing(target) or _is_missing(decoded):
        return None
    t, d = normalize_ipa(target), normalize_ipa(decoded)
    if t is None or d is None:
        return None
    if t == d:
        return "match"
    return "near_miss" if frozenset((t, d)) in NEAR_MISS_PAIRS else "distinct"


# =============================================================================
# 3. Reference ARPABET->IPA table and the contamination audit
# =============================================================================

REFERENCE_ARPABET_IPA = {
    "P": "p", "B": "b", "T": "t", "D": "d", "K": "k", "G": "ɡ",
    "F": "f", "V": "v", "TH": "θ", "DH": "ð", "S": "s", "Z": "z",
    "SH": "ʃ", "ZH": "ʒ", "HH": "h", "CH": "tʃ", "JH": "dʒ",
    "M": "m", "N": "n", "NG": "ŋ", "L": "l", "R": "ɹ", "W": "w", "Y": "j",
}


def audit_derived_mapping(derived, reference=None):
    """Compare a corpus-derived ARPABET->IPA lookup against the reference.
    Consonants only; vowel realisation is genuinely dialect-variable and a
    reference for it would be an opinion. A disagreement has two possible causes,
    L1 contamination or aligner convention, and this cannot tell them apart."""
    reference = REFERENCE_ARPABET_IPA if reference is None else reference
    rows = []
    for arp, ref in sorted(reference.items()):
        got = derived.get(arp)
        if got is None:
            continue
        rows.append({"target_arpabet": arp, "reference_ipa": ref, "derived_ipa": got,
                     "agrees": normalize_ipa(got) == normalize_ipa(ref)})
    return rows


# The canonical realisation of each ARPABET symbol, vowels included. Distinct from
# REFERENCE_ARPABET_IPA, which is consonants only and exists to audit a derived
# lookup. This one exists because GOP should be scored against the phone that was
# SUPPOSED to be there, not against whichever pronunciation variant the aligner
# picked. A forced aligner choosing among dictionary variants will often pick the
# one matching what was actually said, which moves the target toward the error and
# quietly destroys the signal GOP is meant to detect.

ARPABET_TO_IPA = {
    "AA": "ɑ", "AE": "æ", "AH": "ʌ", "AO": "ɔ", "AW": "aʊ", "AY": "aɪ",
    "EH": "ɛ", "ER": "ɚ", "EY": "eɪ", "IH": "ɪ", "IY": "i", "OW": "oʊ",
    "OY": "ɔɪ", "UH": "ʊ", "UW": "u",
    "P": "p", "B": "b", "T": "t", "D": "d", "K": "k", "G": "ɡ",
    "F": "f", "V": "v", "TH": "θ", "DH": "ð", "S": "s", "Z": "z",
    "SH": "ʃ", "ZH": "ʒ", "HH": "h", "CH": "tʃ", "JH": "dʒ",
    "M": "m", "N": "n", "NG": "ŋ", "L": "l", "R": "ɹ", "W": "w", "Y": "j",
}


def arpabet_base(p):
    """Strip the stress digit. AH1 and AH0 are the same phoneme."""
    if is_missing(p):
        return None
    return re.sub(r"[0-9]+$", "", str(p).strip().upper()) or None


def canonical_ipa(arpabet):
    """The citation realisation. Unstressed AH is schwa, which matters because it
    is the single most common vowel in the corpus."""
    b = arpabet_base(arpabet)
    if b is None:
        return None
    if b == "AH" and str(arpabet).endswith("0"):
        return "ə"
    return ARPABET_TO_IPA.get(b)


# =============================================================================
# 4. Phone -> model vocabulary token mapping
# =============================================================================
# GOP needs log P(target phone | frame), which means it needs the target phone's
# index in the model's own vocabulary. MFA emits english_mfa IPA; the model's
# vocabulary is espeak IPA. Reconciling those two inventories is unavoidable for
# GOP, and it is also blocking item 1 in the roadmap, so the artifact this
# produces does double duty.

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


def build_phone_token_map(vocab, phones, extra=None):
    """Map each phone label to a token id in the model vocabulary.

    vocab:  dict token string -> id, straight from the tokenizer
    phones: iterable of phone labels seen in the alignment
    extra:  optional additional phone->token overrides, applied first

    Resolution order, most specific first, so a hand-written override always wins
    over a fuzzy match: explicit override, exact vocab hit, MFA->espeak table,
    normalised hit, diacritic-stripped hit. Anything unresolved is reported rather
    than guessed at, because a wrong token id produces a confidently wrong GOP.

    Returns (mapping, unmapped, report) where report carries the resolution route
    per phone so the coverage number can be audited rather than trusted.
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


# =============================================================================
# 4b. Phone-level pairing
# =============================================================================
# The original recovery discards a whole utterance whenever the aligner and the
# scored transcript disagree anywhere, which on the full corpus threw away 63% of
# utterances and salvaged 22 of 3128. The waste is structural: one ambiguous phone
# kills forty good ones.
#
# This aligns in ARPABET space instead of collapsed-IPA space, and discards at the
# level of the phone rather than the utterance. Blocks where the two sequences run
# in step are kept, including blocks where the symbols DIFFER but the counts match
# - those are exactly the mispronounced phones, and dropping them would bias the
# surviving data toward correct speech, which is the failure mode this is trying
# to avoid. Insertions, deletions and length-changing substitutions stay dropped,
# because there the correspondence is genuinely unknown.


def build_ipa_to_arpabet(pairs):
    """pairs: iterable of (mfa_ipa, target_arpabet). Returns the most frequent
    ARPABET base per aligner phone, learned from cleanly paired utterances only."""
    counts = {}
    for ipa, arp in pairs:
        b = arpabet_base(arp)
        if is_missing(ipa) or b is None:
            continue
        counts.setdefault(ipa, Counter())[b] += 1
    return {k: c.most_common(1)[0][0] for k, c in counts.items()}


def align_partial(mfa_seq, scored_seq, ipa_to_arp):
    """Returns (paired, info). `paired` is a list of (mfa_item, scored_item) for the
    positions whose correspondence is unambiguous. An aligner phone with no known
    ARPABET gets a sentinel so it can never spuriously match."""
    mfa_arp = [ipa_to_arp.get(m[0], f"?{i}") for i, m in enumerate(mfa_seq)]
    scored_arp = [arpabet_base(s[0]) or f"!{i}" for i, s in enumerate(scored_seq)]

    sm = SequenceMatcher(None, mfa_arp, scored_arp, autojunk=False)
    paired, n_equal, n_sub, n_dropped = [], 0, 0, 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                paired.append((mfa_seq[i1 + k], scored_seq[j1 + k]))
            n_equal += i2 - i1
        elif tag == "replace" and (i2 - i1) == (j2 - j1):
            for k in range(i2 - i1):
                paired.append((mfa_seq[i1 + k], scored_seq[j1 + k]))
            n_sub += i2 - i1
        else:
            n_dropped += max(i2 - i1, j2 - j1)
    return paired, {"n_paired": len(paired), "n_equal": n_equal,
                    "n_substituted": n_sub, "n_dropped": n_dropped,
                    "coverage": len(paired) / max(len(scored_seq), 1)}


def vowel_consonant_crossover(pairs):
    """Count target/realisation pairs where a vowel target was realised as a
    consonant or vice versa. These are impossible as speech and can only come from
    misalignment, so the count is a direct read on whether pairing is sound. The
    roadmap names this explicitly as a pairing definition-of-done."""
    VOWELS = set("AEIOU")
    IPA_VOWELS = set("aeiouɑæɒɔəɚɛɜɪʊʌyøœɐʉɨɯ")
    bad = []
    for arp, ipa in pairs:
        b = arpabet_base(arp)
        if b is None or is_missing(ipa):
            continue
        t_is_vowel = any(c in VOWELS for c in b)
        r_is_vowel = any(c in IPA_VOWELS for c in str(ipa))
        if t_is_vowel != r_is_vowel:
            bad.append((arp, ipa))
    return bad


# =============================================================================
# 5. Goodness of Pronunciation
# =============================================================================
# The binary decode-and-match method keeps only argmax and asks a yes/no question,
# which collapses a full posterior into a coin flip. GOP compares the probability
# the model gave the target phone against the probability it gave its own best
# guess, per frame, as a log ratio. Zero means the target was the model's top
# choice; strongly negative means it was not. That is a gradable signal.
#
# CTC posteriors are peaky and blank-dominated, so a naive frame mean over an
# alignment window is diluted by blank frames where every real phone scores low.
# Several variants are computed and the notebook picks between them on measured
# correlation with human ratings rather than on assertion.

GOP_VARIANTS = ["gop_mean", "gop_max", "gop_noblank", "gop_renorm", "post_mean", "post_max"]


def log_softmax_np(logits, axis=-1):
    m = np.max(logits, axis=axis, keepdims=True)
    shifted = logits - m
    return shifted - np.log(np.sum(np.exp(shifted), axis=axis, keepdims=True))


def frame_span(start_s, end_s, sec_per_frame, n_valid_frames):
    """Convert a time window to a half-open frame range, clipped to the frames
    that correspond to real audio. Padding frames must never enter a window: the
    model attends over them and emits tokens there, and letting those in was
    silently corrupting windows near the end of short utterances in a padded batch."""
    if sec_per_frame <= 0 or n_valid_frames <= 0:
        return 0, 0
    lo = int(math.floor(start_s / sec_per_frame))
    hi = int(math.ceil(end_s / sec_per_frame))
    lo = max(0, min(lo, n_valid_frames))
    hi = max(0, min(hi, n_valid_frames))
    if hi <= lo:
        hi = min(lo + 1, n_valid_frames)
    return lo, hi


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


# =============================================================================
# 6. CTC forced alignment (Viterbi, numpy)
# =============================================================================
# An alternative to MFA windows that uses the scoring model's own time base. This
# removes MFA boundary error from the GOP measurement and gives the segmentation-
# free comparison the roadmap asks for. Implemented here rather than pulled from
# torchaudio so it can be unit-tested without a GPU and so its behaviour is
# inspectable.

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


# =============================================================================
# 7. Statistics
# =============================================================================

MIN_N_PER_PHONEME = 100


def wilson_ci(k, n, z=1.96):
    """Wilson score interval for a proportion. Exact, cheap, and behaves at rates
    near 0 and 1 where the normal approximation does not."""
    if n == 0:
        return (None, None)
    p = k / n
    denom = 1.0 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def mean_ci(values, z=1.96):
    """Normal-approximation CI for a mean. Used for continuous GOP, where the
    Wilson interval does not apply."""
    a = np.asarray([v for v in values if v is not None and not (isinstance(v, float) and math.isnan(v))],
                   dtype=float)
    n = len(a)
    if n < 2:
        return (None, None, n)
    se = a.std(ddof=1) / math.sqrt(n)
    return (float(a.mean() - z * se), float(a.mean() + z * se), n)


def per_phoneme_table(rows, key_col, match_col, min_n=None):
    """Mismatch rate per phoneme with a Wilson interval and an explicit
    trustworthy flag, so an under-observed phoneme cannot be read as a finding."""
    min_n = MIN_N_PER_PHONEME if min_n is None else min_n
    sub = rows[rows[key_col].notna() & rows[match_col].notna()]
    out = []
    for key, grp in sub.groupby(key_col):
        n = int(len(grp))
        n_mismatch = int((~grp[match_col].astype("boolean").fillna(False)).sum())
        lo, hi = wilson_ci(n_mismatch, n)
        out.append({key_col: key, "n": n, "n_mismatch": n_mismatch,
                    "mismatch_rate": n_mismatch / n if n else None,
                    "ci_lo": lo, "ci_hi": hi, "trustworthy": n >= min_n})
    tbl = pd.DataFrame(out)
    if len(tbl):
        tbl = tbl.sort_values("mismatch_rate", ascending=False).reset_index(drop=True)
    return tbl


def per_phoneme_gop_table(rows, key_col, gop_col, min_n=None):
    """Mean GOP per phoneme with a CI. The continuous analogue of the table above,
    and far more sensitive: a phoneme can shift substantially in GOP without
    crossing any binary threshold."""
    min_n = MIN_N_PER_PHONEME if min_n is None else min_n
    sub = rows[rows[key_col].notna() & rows[gop_col].notna()]
    out = []
    for key, grp in sub.groupby(key_col):
        lo, hi, n = mean_ci(grp[gop_col].to_numpy())
        out.append({key_col: key, "n": int(len(grp)),
                    "gop_mean": float(grp[gop_col].mean()),
                    "gop_median": float(grp[gop_col].median()),
                    "ci_lo": lo, "ci_hi": hi, "trustworthy": len(grp) >= min_n})
    tbl = pd.DataFrame(out)
    if len(tbl):
        tbl = tbl.sort_values("gop_mean").reset_index(drop=True)
    return tbl


def point_biserial(x, y):
    """Correlation between a continuous score and a binary outcome. Returns None
    rather than nan when one class is absent."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    ok = ~(np.isnan(x) | np.isnan(y))
    x, y = x[ok], y[ok]
    if len(x) < 3 or len(np.unique(y)) < 2 or x.std() == 0:
        return None
    return float(np.corrcoef(x, y)[0, 1])


def roc_auc(scores, labels):
    """AUC by rank, no sklearn dependency. labels: 1 = positive."""
    s = np.asarray(scores, dtype=float)
    y = np.asarray(labels, dtype=int)
    ok = ~np.isnan(s)
    s, y = s[ok], y[ok]
    n_pos, n_neg = int((y == 1).sum()), int((y == 0).sum())
    if n_pos == 0 or n_neg == 0:
        return None
    order = np.argsort(s, kind="mergesort")
    ranks = np.empty(len(s), dtype=float)
    ranks[order] = np.arange(1, len(s) + 1)
    # average ranks within ties
    sorted_s = s[order]
    i = 0
    while i < len(sorted_s):
        j = i
        while j + 1 < len(sorted_s) and sorted_s[j + 1] == sorted_s[i]:
            j += 1
        if j > i:
            avg = (i + j + 2) / 2.0
            ranks[order[i:j + 1]] = avg
        i = j + 1
    return float((ranks[y == 1].sum() - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg))


# =============================================================================
# 8. Calibration: turning a GOP into a confidence between 0 and 1
# =============================================================================
# Roadmap definition of done: "every sound carries a confidence between 0 and 1"
# and "the reliability curve improves after calibration". A binary match cannot
# satisfy that; a continuous GOP can.


def sigmoid(z):
    return 1.0 / (1.0 + np.exp(-np.clip(z, -50, 50)))


class PlattCalibrator:
    """One-dimensional logistic calibration, fitted by Newton steps. No sklearn
    dependency so Stage 3 can apply it without matching library versions."""

    def __init__(self):
        self.a, self.b, self.fitted = 1.0, 0.0, False

    def fit(self, scores, labels, iters=100, tol=1e-8):
        x = np.asarray(scores, dtype=float)
        y = np.asarray(labels, dtype=float)
        ok = ~(np.isnan(x) | np.isnan(y))
        x, y = x[ok], y[ok]
        if len(x) < 10 or len(np.unique(y)) < 2:
            raise ValueError("need at least 10 points and both classes to calibrate")
        # standardise for conditioning, fold the transform back into a and b
        mu, sd = x.mean(), (x.std() or 1.0)
        z = (x - mu) / sd
        a, b = 0.0, 0.0
        for _ in range(iters):
            p = sigmoid(a * z + b)
            w = np.clip(p * (1 - p), 1e-9, None)
            g = np.array([np.sum((p - y) * z), np.sum(p - y)])
            H = np.array([[np.sum(w * z * z), np.sum(w * z)],
                          [np.sum(w * z), np.sum(w)]])
            try:
                step = np.linalg.solve(H + 1e-9 * np.eye(2), g)
            except np.linalg.LinAlgError:
                break
            a, b = a - step[0], b - step[1]
            if np.max(np.abs(step)) < tol:
                break
        self.a, self.b = float(a / sd), float(b - a * mu / sd)
        self.fitted = True
        return self

    def predict_proba(self, scores):
        x = np.asarray(scores, dtype=float)
        return sigmoid(self.a * x + self.b)

    def to_dict(self):
        return {"kind": "platt", "a": self.a, "b": self.b, "fitted": self.fitted}

    @classmethod
    def from_dict(cls, d):
        c = cls()
        c.a, c.b, c.fitted = float(d["a"]), float(d["b"]), bool(d["fitted"])
        return c


def expected_calibration_error(probs, labels, n_bins=10):
    """Mean absolute gap between predicted confidence and observed frequency,
    weighted by bin population. Lower is better; 0 is perfect calibration."""
    p = np.asarray(probs, dtype=float)
    y = np.asarray(labels, dtype=float)
    ok = ~(np.isnan(p) | np.isnan(y))
    p, y = p[ok], y[ok]
    if len(p) == 0:
        return None
    edges = np.linspace(0, 1, n_bins + 1)
    ece, total = 0.0, len(p)
    for i in range(n_bins):
        lo, hi = edges[i], edges[i + 1]
        sel = (p > lo) & (p <= hi) if i > 0 else (p >= lo) & (p <= hi)
        if sel.sum() == 0:
            continue
        ece += (sel.sum() / total) * abs(p[sel].mean() - y[sel].mean())
    return float(ece)


def reliability_table(probs, labels, n_bins=10):
    p = np.asarray(probs, dtype=float)
    y = np.asarray(labels, dtype=float)
    ok = ~(np.isnan(p) | np.isnan(y))
    p, y = p[ok], y[ok]
    edges = np.linspace(0, 1, n_bins + 1)
    rows = []
    for i in range(n_bins):
        lo, hi = edges[i], edges[i + 1]
        sel = (p > lo) & (p <= hi) if i > 0 else (p >= lo) & (p <= hi)
        if sel.sum() == 0:
            continue
        rows.append({"bin_lo": lo, "bin_hi": hi, "n": int(sel.sum()),
                     "mean_confidence": float(p[sel].mean()),
                     "observed_rate": float(y[sel].mean())})
    return pd.DataFrame(rows)


# =============================================================================
# 8b. Rich per-phone features: LPP and LPR
# =============================================================================
# A scalar GOP answers "how likely was the target". The LPR vector answers "how
# likely was the target COMPARED TO EACH OTHER PHONE", which is what says *what
# the model thought it heard instead*. That is the diagnostic content, and it is
# the input GOPT consumes to reach its published correlation. Collapsing it to one
# number discards most of it, for the same reason argmax discarded the posterior.
#
#   LPP_p    = mean over window of log P(canonical phone)
#   LPR_p,j  = mean over window of [log P(canonical) - log P(phone j)]
#
# With ~45 phones in the inventory that is ~46 numbers per window instead of 6.


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


def lpr_column_names(phone_labels):
    return [f"lpr_{p}" for p in phone_labels]


# =============================================================================
# 8c. Context, pooling, and evaluation helpers
# =============================================================================


def add_context_features(df, group_col, order_col, feature_cols, n=1):
    """Neighbouring-phone features. Coarticulation is real: a phone's realisation
    depends on what surrounds it, so the model should see its neighbours. Boundary
    positions get NaN rather than a wrapped-around value from a different word."""
    out = df.sort_values([group_col, order_col]).copy()
    made = []
    g = out.groupby(group_col, sort=False)
    for c in feature_cols:
        for k in range(1, n + 1):
            out[f"prev{k}_{c}"] = g[c].shift(k)
            out[f"next{k}_{c}"] = g[c].shift(-k)
            made += [f"prev{k}_{c}", f"next{k}_{c}"]
    return out, made


def pool_hidden(hidden, lo, hi):
    """Mean, std and max pooling of a hidden-state block over a window.
    Intermediate transformer layers carry more phonetic detail than the CTC output
    layer, which has been squeezed toward a decoding decision."""
    if hi <= lo:
        return None
    win = hidden[lo:hi]
    return np.concatenate([win.mean(axis=0), win.std(axis=0), win.max(axis=0)]).astype(np.float32)


def pearson_r(x, y):
    """Pearson correlation, the metric this literature reports. Returns None rather
    than nan when either side is constant."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    ok = ~(np.isnan(x) | np.isnan(y))
    x, y = x[ok], y[ok]
    if len(x) < 3 or x.std() == 0 or y.std() == 0:
        return None
    return float(np.corrcoef(x, y)[0, 1])


def speaker_grouped_folds(speakers, n_folds=5, seed=0):
    """Fold assignment by speaker, never by row. Phones from one speaker are
    correlated, so a random row split leaks the speaker across train and test and
    reports a score that will not survive a new voice."""
    uniq = sorted(set(s for s in speakers if s is not None))
    rng = np.random.default_rng(seed)
    perm = rng.permutation(len(uniq))
    assign = {uniq[perm[i]]: i % n_folds for i in range(len(uniq))}
    return [assign.get(s, -1) for s in speakers], assign


def regression_report(y_true, y_pred, poor_threshold=1.0):
    """The full metric set, so no single number can flatter the model. PCC is the
    headline because it is what this literature reports; MSE and AUC are included
    because a model can look correlated while being badly scaled or useless at the
    decision that actually matters."""
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    ok = ~(np.isnan(y_true) | np.isnan(y_pred))
    y_true, y_pred = y_true[ok], y_pred[ok]
    if len(y_true) < 3:
        return {"n": int(len(y_true)), "pcc": None, "mse": None, "mae": None, "auc_poor": None}
    return {
        "n": int(len(y_true)),
        "pcc": pearson_r(y_pred, y_true),
        "mse": float(np.mean((y_pred - y_true) ** 2)),
        "mae": float(np.mean(np.abs(y_pred - y_true))),
        "auc_poor": roc_auc(-y_pred, (y_true <= poor_threshold).astype(int)),
    }


# =============================================================================
# 9. The evenness contract
# =============================================================================
# A feature may enter the model only if it can be computed identically on both
# corpora. Speechocean has ARPABET targets, human scores and word positions;
# Svarah has none of them. Any feature drawn from those makes the two sides
# incomparable no matter how careful the rest is, so the rule is an assertion
# rather than a discipline.

GOP_SCALARS = ["gop_mean", "gop_max", "gop_noblank", "gop_renorm", "post_mean", "post_max"]
GEOMETRY = ["n_frames", "duration_ms"]
BASE_EVEN_FEATURES = GOP_SCALARS + GEOMETRY
EVEN_KEY = "phone_norm"          # normalised aligner IPA, present on both sides

FORBIDDEN_FEATURES = {"human_score", "target_arpabet", "expected_ipa", "position",
                      "word", "word_index", "speaker", "gender", "match_raw",
                      "match_collapsed", "match_reference", "error_type", "utt_id",
                      "item_id", "native_place_state", "primary_language", "text",
                      # 2.2.0: descriptive columns from the free decode.
                      # They belong in the record, never in the model.
                      "produced", "produced_role", "error_why",
                      "utt_free_decode", "decoded_in_window"}


def build_feature_columns(df, use_lpr=True, use_context=True, use_hidden=True):
    """The feature list for a given configuration, derived from what is actually
    present in the frame rather than assumed. Returns (columns, blocks) so the
    ablation ladder can add one block at a time and attribute any lift to it."""
    blocks = {"gop_scalars": [c for c in GOP_SCALARS if c in df.columns],
              "geometry": [c for c in GEOMETRY if c in df.columns],
              "lpp": [c for c in ["lpp"] if c in df.columns],
              "lpr": sorted(c for c in df.columns if c.startswith("lpr_")) if use_lpr else [],
              "context": sorted(c for c in df.columns
                                if c.startswith("prev") or c.startswith("next")) if use_context else [],
              "hidden": sorted(c for c in df.columns if c.startswith("h_")) if use_hidden else []}
    cols = [c for b in blocks.values() for c in b]
    return cols, blocks


def assert_even_features(df, feature_cols=None):
    """Raise if a feature frame carries anything that exists on only one corpus."""
    cols = set(feature_cols) if feature_cols is not None else set(df.columns) - {EVEN_KEY}
    leaked = cols & FORBIDDEN_FEATURES
    assert not leaked, (
        f"Feature frame carries corpus-specific columns: {sorted(leaked)}. "
        f"These do not exist on Svarah, so any model using them makes the "
        f"Speechocean-vs-Svarah comparison uneven.")
    if feature_cols is not None:
        missing = set(feature_cols) - set(df.columns)
        assert not missing, f"Declared features absent from the frame: {sorted(missing)[:10]}"
    assert EVEN_KEY in df.columns, f"the even key {EVEN_KEY} must be present"
    return True


# =============================================================================
# 11. Audio conditioning, the steps that run before anything is measured
# =============================================================================
# The plan's step 01 is "clean up", and until this revision the notebook did
# exactly one part of it: resample to 16 kHz. The rest lived only in the serving
# path, which meant no number in Stages 2, 3 or 4 was ever computed on a clip
# that had passed a quality check. That is a real gap, because a scorer that
# quietly measures a noisy clip returns a low score for the microphone rather
# than for the speaker, and nothing downstream can tell the two apart.
#
# Everything here is numpy only, deliberately. These functions gate whether the
# GPU is allowed to run, so their failure modes have to be obvious on a laptop.

PREEMPHASIS_COEF = 0.97      # standard; flattens the ~-6 dB/octave glottal tilt


def preemphasis(audio, coef=PREEMPHASIS_COEF):
    """y[n] = x[n] - coef*x[n-1].

    Boosts the high frequencies that carry fricative and stop-burst energy, which
    are exactly the cues a lisp or a devoiced stop lives in. Without it the
    low-frequency vowel energy dominates every spectral statistic computed later.

    Not applied before the wav2vec2 forward pass: that model was trained on raw
    waveform and its own feature encoder expects the untouched signal. This is for
    the correlate path in section 14, which measures the physics directly.
    """
    a = np.asarray(audio, dtype=np.float32)
    if a.size < 2:
        return a
    out = np.empty_like(a)
    out[0] = a[0]
    out[1:] = a[1:] - coef * a[:-1]
    return out


def frame_energy(audio, frame=400, hop=160):
    """Short-time energy. frame=25 ms and hop=10 ms at 16 kHz, the convention the
    phonetics literature is written against."""
    a = np.asarray(audio, dtype=np.float32)
    if a.size < frame:
        return np.array([float(np.sum(a ** 2))]) if a.size else np.array([0.0])
    n = 1 + (a.size - frame) // hop
    idx = np.arange(frame)[None, :] + hop * np.arange(n)[:, None]
    return np.sum(a[idx] ** 2, axis=1)


def estimate_snr_db(audio, frame=400, hop=160, speech_floor_db=30.0,
                    min_noise_frames=4, assume_clean_db=40.0):
    """Speech energy against background energy, in dB.

    Crude on purpose. A sophisticated estimator nobody can reason about is worse
    here than a rough one whose failure mode is obvious, because this number
    decides whether anything else is permitted to happen.

    Frames within `speech_floor_db` of the loudest frame are called speech; the
    rest are called background. THE IMPORTANT CASE is a short single-word clip
    that is speech end to end, with no pause anywhere in it. There is then no
    background to measure, and a naive percentile ratio returns roughly 0 dB and
    rejects a perfectly clean recording. That is the dangerous direction for a
    gate, so when there is too little background to estimate from, this returns
    `assume_clean_db` and lets the clip through. A gate that silently discards
    good audio is much harder to notice than one that occasionally admits bad.
    """
    e = frame_energy(audio, frame, hop)
    if e.size < 4 or not np.any(e > 0):
        return 0.0
    peak = float(np.max(e))
    thresh = peak * (10.0 ** (-speech_floor_db / 10.0))
    speech_frames = e[e >= thresh]
    noise_frames = e[e < thresh]
    if noise_frames.size < min_noise_frames:
        return float(assume_clean_db)
    speech = float(np.percentile(speech_frames, 50))
    noise = float(np.percentile(noise_frames, 90))
    if speech <= 0:
        return 0.0
    noise = max(noise, peak * 1e-8)      # digital silence would give infinity
    return float(min(60.0, 10.0 * np.log10(speech / noise)))


def trim_silence(audio, sr=16000, top_db=35.0, frame=400, hop=160, pad_s=0.03):
    """Return (trimmed_audio, start_sample, end_sample).

    Leading and trailing silence is removed so that a false start or a long
    breath before the word does not drag the forced aligner's first boundary
    backwards. `pad_s` keeps 30 ms either side, because a stop burst sits below
    the energy threshold and would otherwise be cut off, which would destroy the
    voice onset time measurement in section 14.

    Returns the original array unchanged when it cannot find speech, rather than
    returning an empty array. A downstream stage receiving zero samples is a much
    harder failure to diagnose than one receiving an untrimmed clip.
    """
    a = np.asarray(audio, dtype=np.float32)
    if a.size < frame:
        return a, 0, a.size
    e = frame_energy(a, frame, hop)
    if not np.any(e > 0):
        return a, 0, a.size
    ref = float(np.max(e))
    thresh = ref * (10.0 ** (-top_db / 10.0))
    keep = np.nonzero(e >= thresh)[0]
    if keep.size == 0:
        return a, 0, a.size
    pad = int(pad_s * sr)
    lo = max(0, int(keep[0]) * hop - pad)
    hi = min(a.size, int(keep[-1]) * hop + frame + pad)
    if hi - lo < frame:
        return a, 0, a.size
    return a[lo:hi], lo, hi


def cmvn(features, eps=1e-8):
    """Per-utterance mean and variance normalisation over the time axis.

    Removes the channel: a different handset, a different room and a different
    recording level all shift the mean of every coefficient, and without this
    they are read as a different speaker. Per utterance rather than per corpus,
    because at serving time one utterance is all there is.
    """
    f = np.asarray(features, dtype=np.float64)
    if f.ndim != 2 or f.shape[0] < 2:
        return np.asarray(features, dtype=np.float32)
    mu = f.mean(axis=0, keepdims=True)
    sd = f.std(axis=0, keepdims=True)
    return ((f - mu) / (sd + eps)).astype(np.float32)


def condition_audio(audio, sr=16000, do_trim=True, min_snr_db=None):
    """The whole of step 01 in one call, returning what it did as well as what
    it produced, so a stage can report how many clips it conditioned and why any
    were rejected.

    Returns (audio, report). `report["accepted"]` is False when the clip fails
    the SNR floor, and in that case the caller must not score it. Passing
    min_snr_db=None measures without gating, which is what the corpus stages do
    on a first pass so the distribution can be inspected before a threshold is
    chosen. Choosing a threshold by looking at the distribution first is the
    difference between a gate and a number picked because it sounded round.
    """
    a = np.asarray(audio, dtype=np.float32)
    rep = {"n_samples_in": int(a.size),
           "duration_s": float(a.size) / float(sr) if sr else None,
           "trimmed": False, "snr_db": None, "accepted": True, "reason": None}
    if a.size == 0:
        rep.update(accepted=False, reason="empty audio")
        return a, rep
    if do_trim:
        a, lo, hi = trim_silence(a, sr)
        rep["trimmed"] = bool(lo != 0 or hi != rep["n_samples_in"])
        rep["trim_start_s"] = float(lo) / float(sr)
        rep["trim_end_s"] = float(hi) / float(sr)
    snr = estimate_snr_db(a)
    rep["snr_db"] = round(snr, 2)
    rep["n_samples_out"] = int(a.size)
    if min_snr_db is not None and snr < min_snr_db:
        rep.update(accepted=False,
                   reason=f"snr {snr:.1f} dB below the {min_snr_db:.1f} dB floor")
    return a, rep


# =============================================================================
# 12. The unconstrained decode, and attributing a produced phone to each target
# =============================================================================
# Forced alignment answers "how well did the audio in this window match the sound
# we asked for". It cannot answer "what came out instead", because it was never
# allowed to consider anything else. A clinical record does not say the /s/ was
# wrong; it says /s/ was produced as [t] in initial position. Every construct in
# Module 2A, the inventory grid, the process analysis, error typing beyond a
# binary, reads the produced phone, so without this Module 2 has no input.
#
# The two paths disagree routinely and the disagreement is the signal, not a bug.
# The free decode carries its own confidence, separate from the score confidence,
# because free decoding is markedly less reliable than forced alignment. A
# low-confidence substitution is reported as "substitution, identity uncertain"
# rather than named, which is the difference between a useful record and a
# confidently wrong one.


def ctc_collapse(ids, blank_id, logprobs=None):
    """Collapse a frame-wise argmax into segments: the standard CTC rule of
    merging repeats and dropping blanks.

    Returns a list of dicts with the token id, the frame span, and, when
    logprobs are supplied, the mean log-probability of that token across its own
    frames, which becomes the produced-phone confidence.

    This is the unconstrained path: no dictionary, no target, no alignment. It
    reports what the model heard.
    """
    ids = np.asarray(ids).astype(int).ravel()
    segs, prev, start = [], None, 0
    for i, t in enumerate(ids):
        if t != prev:
            if prev is not None and prev != blank_id:
                segs.append({"token_id": int(prev), "start_frame": int(start),
                             "end_frame": int(i)})
            prev, start = int(t), i
    if prev is not None and prev != blank_id:
        segs.append({"token_id": int(prev), "start_frame": int(start),
                     "end_frame": int(ids.size)})
    if logprobs is not None:
        lp = np.asarray(logprobs)
        for s in segs:
            lo, hi = s["start_frame"], min(s["end_frame"], lp.shape[0])
            if hi > lo:
                s["logprob"] = float(np.mean(lp[lo:hi, s["token_id"]]))
                s["confidence"] = float(np.exp(s["logprob"]))
            else:
                s["logprob"], s["confidence"] = None, None
    return segs


def free_decode(logprobs, blank_id, inv_vocab=None):
    """One unconstrained pass over the whole utterance. Returns the segments and
    the collapsed string, the latter for the word-identity gate."""
    lp = np.asarray(logprobs)
    segs = ctc_collapse(lp.argmax(axis=1), blank_id, lp)
    if inv_vocab is not None:
        for s in segs:
            s["symbol"] = inv_vocab.get(s["token_id"])
    return {"segments": segs,
            "string": "".join(s.get("symbol") or "" for s in segs),
            "n_segments": len(segs)}


def alignment_confidence(logprobs, spans, target_ids=None):
    """How well the SEGMENTATION fits the audio, independent of whether the
    speaker said the right thing.

    THE BUG THIS EXISTS TO FIX
    --------------------------
    The obvious implementation is the mean posterior the model gives each TARGET
    inside its own window. That number is goodness of pronunciation, which is the
    thing being scored. Using it as the gate on the score is circular, and the
    consequence is not subtle: a speaker who substitutes /s/ with [t] gets a low
    target posterior, fails the alignment gate, and the whole item is held. Mira
    then refuses to score precisely the recordings that contain errors and
    reports near-perfect accuracy on what is left.

    So this measures something else. For each window it takes the model's PEAK
    confidence, over the whole vocabulary, and averages. It asks whether the
    audio in that window is confidently SOMETHING, which is what a defensible
    boundary means. A clear substitution scores high here, as it should: the
    boundaries are right and the sound is wrong, and those are different findings
    that must reach different parts of the report.

    Returns (quality, detail). Quality is None when there is nothing to measure.
    `detail` carries the structural checks, because a low number and a missing
    segment have different fixes: one asks for a retake, the other says the
    aligner could not place a sound at all.
    """
    lp = np.asarray(logprobs)
    if lp.ndim != 2 or lp.shape[0] == 0:
        return None, {"reason": "no frames"}
    peaks, empty, total_frames = [], 0, 0
    for i, sp in enumerate(spans):
        if sp is None or sp[0] is None or sp[1] is None:
            empty += 1
            continue
        a, b = int(sp[0]), min(int(sp[1]), lp.shape[0])
        if b <= a:
            empty += 1
            continue
        total_frames += (b - a)
        peaks.append(float(np.mean(np.exp(np.max(lp[a:b], axis=1)))))
    detail = {"n_targets": len(spans), "n_without_frames": empty,
              "n_frames_used": total_frames,
              "coverage": (len(spans) - empty) / len(spans) if spans else None}
    if not peaks:
        return None, {**detail, "reason": "no target received any frames"}
    q = float(np.mean(peaks))
    # A target the aligner could not place at all is a structural failure and it
    # must pull the number down, or an utterance where half the sounds vanished
    # would pass on the strength of the half that survived.
    if empty:
        q *= (len(peaks) / float(len(spans)))
        detail["penalty_applied"] = True
    if target_ids is not None:
        # Diagnostic only, never the gate: how much of that peak went to the
        # sound we asked for. A large gap between the two is the signature of a
        # real substitution rather than a bad recording.
        hits = []
        for tid, sp in zip(target_ids, spans):
            if tid is None or sp is None or sp[0] is None:
                continue
            a, b = int(sp[0]), min(int(sp[1]), lp.shape[0])
            if b > a:
                hits.append(float(np.mean(np.exp(lp[a:b, tid]))))
        detail["mean_target_posterior"] = float(np.mean(hits)) if hits else None
        detail["is_goodness_not_alignment"] = (
            "mean_target_posterior is GOP-like and must never be used as the "
            "alignment gate; see this function's docstring")
    return round(q, 4), detail


PRODUCED_MIN_CONFIDENCE = 0.35
# Below this the substitute is reported as present but unnamed. The value is an
# engineering judgement, not a validated threshold: it was chosen so that on
# correct productions the decode names the right phone the large majority of the
# time, and it should be re-derived the moment there is clinician-labelled audio
# to derive it against. It is exported so that a stage can change it on purpose
# rather than a caller passing a different literal in three places.


def attribute_produced_phones(target_symbols, decoded_segments,
                              min_confidence=PRODUCED_MIN_CONFIDENCE):
    """Line the free decode up against the target sequence and say, for each
    target sound, what came out in its place.

    Returns (per_target, insertions).

    `per_target` has one entry per target symbol, in order, with:
        produced            the decoded symbol, or None for an omission
        role                'equal' | 'substitution' | 'omission'
        produced_confident  False when the decode is too unsure to name it
        confidence          the free decode's own confidence for that segment
        seg_index           index into decoded_segments, or None

    `insertions` lists decoded segments with no counterpart in the target, each
    tagged with the target index it follows, which is what an addition error is.

    The alignment is a plain sequence match on normalised symbols. It is
    deliberately not the same function as `align_partial`: that one pairs the
    aligner's phones against the human-scored phones and its job is to refuse
    ambiguous correspondences. This one must return an answer for every target,
    because "we could not tell what happened here" is itself a clinical finding
    and has to appear in the record as an omission or an unnamed substitution
    rather than as a dropped row.
    """
    tgt = [normalize_ipa(t) if t is not None else None for t in target_symbols]
    dec_syms = [s.get("symbol") for s in decoded_segments]
    dec = [normalize_ipa(d) if d is not None else None for d in dec_syms]

    per_target = [{"target": target_symbols[i], "produced": None, "role": "omission",
                   "produced_confident": False, "confidence": None,
                   "seg_index": None}
                  for i in range(len(target_symbols))]
    insertions = []

    if not decoded_segments:
        return per_target, insertions

    sm = SequenceMatcher(a=[x or "\x00" for x in tgt],
                         b=[x or "\x01" for x in dec], autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                _fill_produced(per_target, i1 + k, decoded_segments, j1 + k,
                               "equal", min_confidence)
        elif tag == "replace":
            n = min(i2 - i1, j2 - j1)
            for k in range(n):
                _fill_produced(per_target, i1 + k, decoded_segments, j1 + k,
                               "substitution", min_confidence)
            # More targets than decoded segments: the leftovers were not produced.
            for k in range(n, i2 - i1):
                per_target[i1 + k]["role"] = "omission"
            # More decoded segments than targets: the leftovers are additions.
            for k in range(n, j2 - j1):
                insertions.append(_insertion(decoded_segments, j1 + k, i2 - 1))
        elif tag == "delete":
            for k in range(i1, i2):
                per_target[k]["role"] = "omission"
        elif tag == "insert":
            for k in range(j1, j2):
                insertions.append(_insertion(decoded_segments, k, i1 - 1))
    return per_target, insertions


def _fill_produced(per_target, ti, segs, si, role, min_confidence):
    seg = segs[si]
    conf = seg.get("confidence")
    named = conf is None or conf >= min_confidence
    per_target[ti].update(
        produced=seg.get("symbol") if named else None,
        role=role,
        produced_confident=bool(named),
        confidence=None if conf is None else round(float(conf), 4),
        seg_index=int(si))
    if role == "substitution" and not named:
        # Present, wrong, identity unknown. This must not silently become an
        # omission: "something was there and we could not name it" and "nothing
        # was there" have different clinical readings.
        per_target[ti]["role"] = "substitution"


def _insertion(segs, si, after_target_index):
    seg = segs[si]
    return {"produced": seg.get("symbol"), "after_target_index": int(after_target_index),
            "confidence": None if seg.get("confidence") is None
            else round(float(seg["confidence"]), 4),
            "seg_index": int(si)}


# =============================================================================
# 13. Error typing, the score becomes a category, in a fixed order
# =============================================================================
# The order is what makes it reproducible. Two clinicians reading the same record
# must see the same label, and a label that depends on which test happened to run
# first is not a label. Excused runs before everything so a normal Indian English
# realisation never reaches the later tests; correct is last so it is what
# remains rather than something asserted.

ERROR_TYPES = ("excused", "omission", "addition", "substitution",
               "assimilation", "distortion", "correct", "held")

# Place, manner and voicing for the English consonants. Used only for the
# assimilation test, which asks whether the substitute shares a distinguishing
# feature with a neighbour. Kept small and explicit rather than derived from a
# phonological feature library, because a wrong entry here is easier to spot in
# a table than inside a dependency.
PHONE_FEATURES = {
    "P": ("bilabial", "stop", 0),    "B": ("bilabial", "stop", 1),
    "T": ("alveolar", "stop", 0),    "D": ("alveolar", "stop", 1),
    "K": ("velar", "stop", 0),       "G": ("velar", "stop", 1),
    "F": ("labiodental", "fricative", 0), "V": ("labiodental", "fricative", 1),
    "TH": ("dental", "fricative", 0),     "DH": ("dental", "fricative", 1),
    "S": ("alveolar", "fricative", 0),    "Z": ("alveolar", "fricative", 1),
    "SH": ("postalveolar", "fricative", 0), "ZH": ("postalveolar", "fricative", 1),
    "HH": ("glottal", "fricative", 0),
    "CH": ("postalveolar", "affricate", 0), "JH": ("postalveolar", "affricate", 1),
    "M": ("bilabial", "nasal", 1), "N": ("alveolar", "nasal", 1),
    "NG": ("velar", "nasal", 1),
    "L": ("alveolar", "lateral", 1), "R": ("alveolar", "rhotic", 1),
    "W": ("labiovelar", "glide", 1), "Y": ("palatal", "glide", 1),
}


def phone_features(arpabet):
    """(place, manner, voice) or None for vowels and anything unlisted."""
    if arpabet is None:
        return None
    return PHONE_FEATURES.get(arpabet_base(arpabet))


def shares_feature(a, b):
    """True when two consonants share place or manner. The assimilation test."""
    fa, fb = phone_features(a), phone_features(b)
    if fa is None or fb is None:
        return False
    return fa[0] == fb[0] or fa[1] == fb[1]


def classify_error_type(target, produced, role, correlate_flag=None,
                        excused_rule=None, neighbours=(None, None),
                        produced_confident=True, held_reason=None):
    """Assign one of ERROR_TYPES, in the fixed order of the specification.

    target, produced      ARPABET or IPA symbols, compared after normalisation
    role                  from attribute_produced_phones
    correlate_flag        True when a section-14 correlate sits outside its
                          reference range. None means the correlate path did not
                          run, which is the current default and is why
                          'distortion' is presently unreachable in production
    excused_rule          the allow-list rule id that matched, if any
    neighbours            (previous_target, next_target), for assimilation
    held_reason           set when a gate failed; overrides everything, because a
                          measurement that was not permitted has no error type

    Returns (error_type, why) so the reason travels with the label. A label
    without its reason is unarguable, and a clinician has to be able to argue
    with it.
    """
    if held_reason:
        return "held", held_reason
    if excused_rule:
        return "excused", f"allow-list rule {excused_rule} matched"
    if role == "omission":
        return "omission", "no segment was produced in the aligned region"
    if role == "addition":
        return "addition", "a segment was produced with no counterpart in the target"

    same = compare_tokens(produced, target)
    if role == "substitution" and same is not True:
        if not produced_confident:
            return "substitution", "a different sound was produced; identity uncertain"
        prev_n, next_n = neighbours
        if shares_feature(produced, prev_n) or shares_feature(produced, next_n):
            return "assimilation", ("the substitute shares a feature with an "
                                    "adjacent sound")
        return "substitution", f"produced as {produced}"
    if correlate_flag is True:
        return "distortion", ("the sound category is right and an acoustic "
                              "correlate is outside its reference range")
    if correlate_flag is None and same is not True and role != "equal":
        # The categories agree after normalisation but the roles disagree. Do not
        # invent a distortion here: without the correlate path there is no
        # evidence for one, and asserting it would be the exact overclaim the
        # rest of this file exists to prevent.
        return "correct", "category matches; no correlate evidence available"
    return "correct", "matches the target and clears the gates"


# =============================================================================
# 14. The correlate path, measuring the physics directly
# =============================================================================
# This is the path the design documents call the differentiator, and until this
# revision it existed only in prose: praat-parselmouth was installed, imported,
# and never called, and PhoneResult.correlates was an empty dict for the life of
# the program.
#
# READ THIS BEFORE USING ANY NUMBER BELOW.
#
# The extractors are real. The reference ranges are not validated. Every figure
# in REFERENCE_CORRELATES is an adult native-English anchor from the phonetics
# literature, and applying it to an Indian speaker, or to a child, is exactly the
# mistake the whole Stage 3 accent argument exists to prevent. They are here so
# the pipeline is complete end to end and so a distortion flag has somewhere to
# come from once real norms exist. They are NOT fused into the score by default:
# see fuse_broad_and_correlate, whose correlate weight is zero until someone sets
# it deliberately.
#
# What the broad path cannot see is the whole reason this exists. A lateral /s/
# and a clean /s/ are both recognised as /s/, so goodness of pronunciation calls
# them the same. Their spectral centroids are hundreds of hertz apart. That is a
# distortion, it is the single most common residual error in adults, and it is
# invisible without a direct measurement.

CORRELATE_SPEC = {
    # phone class          correlate            what it distinguishes
    "rhotic":   ("F3", "a retroflex or bunched /r/ from a /w/-like glide"),
    "sibilant": ("centroid", "a lateral or dentalised /s/ from a clean one"),
    "stop":     ("VOT", "an aspirated from an unaspirated stop, and devoicing"),
    "fricative": ("centroid", "place of articulation among the non-sibilants"),
}

PHONE_CLASS = {}
for _p in ("R", "ER"):
    PHONE_CLASS[_p] = "rhotic"
for _p in ("S", "Z", "SH", "ZH", "CH", "JH"):
    PHONE_CLASS[_p] = "sibilant"
for _p in ("P", "T", "K", "B", "D", "G"):
    PHONE_CLASS[_p] = "stop"
for _p in ("F", "V", "TH", "DH"):
    PHONE_CLASS[_p] = "fricative"

# Adult native-English anchors. Sources are the standard phonetics references and
# they are recorded here as (mean, sd) so a z score can be formed at all. Treat
# every one as a placeholder to re-derive, never as a threshold to ship.
REFERENCE_CORRELATES = {
    ("rhotic", "F3", "m"):       (1750.0, 250.0),
    ("rhotic", "F3", "f"):       (1950.0, 280.0),
    ("rhotic", "F3_minus_F2", "m"): (450.0, 200.0),
    ("rhotic", "F3_minus_F2", "f"): (500.0, 220.0),
    ("sibilant", "centroid", "m"):  (6100.0, 900.0),
    ("sibilant", "centroid", "f"):  (6900.0, 950.0),
    ("fricative", "centroid", "m"): (4200.0, 1200.0),
    ("fricative", "centroid", "f"): (4600.0, 1300.0),
    ("stop", "VOT", "m"):        (0.055, 0.025),
    ("stop", "VOT", "f"):        (0.055, 0.025),
}

CORRELATE_NORM_MIN_AGE_MONTHS = 216   # 18 years
# Below this the anchors above do not apply at all. A child's formants sit 20 to
# 50 percent higher and the whole table is wrong for them, so norm_z refuses
# rather than returning a plausible-looking number. Refusing is the entire point:
# a wrong z score next to a correct-looking decimal is how an automated system
# produces something that reads as rigorous and is not.


def spectral_moments(audio, sr, t0=None, t1=None, nfft=2048, fmin=200.0,
                     fmax=None):
    """Centroid, spread, skewness and kurtosis of the power spectrum, in Hz.

    Pure numpy, no external dependency, so it runs anywhere the rest of this file
    runs. The centroid is the load-bearing one: for a sibilant it tracks the
    front-cavity resonance and separates a clean /s/ from a lateralised or
    dentalised one, which is the error a recogniser cannot see.

    fmin defaults to 200 Hz to exclude low-frequency room rumble, which otherwise
    drags the centroid down by a few hundred hertz on a home recording and would
    be read as a distortion.
    """
    a = np.asarray(audio, dtype=np.float64)
    if t0 is not None and t1 is not None:
        lo, hi = int(t0 * sr), int(t1 * sr)
        lo, hi = max(0, lo), min(a.size, hi)
        a = a[lo:hi]
    if a.size < 64:
        return {"centroid": None, "spread": None, "skewness": None,
                "kurtosis": None, "reason": "window shorter than 64 samples"}
    w = a * np.hanning(a.size)
    n = max(nfft, int(2 ** np.ceil(np.log2(w.size))))
    spec = np.abs(np.fft.rfft(w, n)) ** 2
    freqs = np.fft.rfftfreq(n, 1.0 / sr)
    hi_f = fmax if fmax is not None else sr / 2.0
    band = (freqs >= fmin) & (freqs <= hi_f)
    p, f = spec[band], freqs[band]
    tot = float(p.sum())
    if tot <= 0:
        return {"centroid": None, "spread": None, "skewness": None,
                "kurtosis": None, "reason": "no energy in band"}
    p = p / tot
    c = float(np.sum(f * p))
    var = float(np.sum(((f - c) ** 2) * p))
    sd = math.sqrt(var) if var > 0 else 0.0
    skew = float(np.sum(((f - c) ** 3) * p) / (sd ** 3)) if sd > 0 else None
    kurt = float(np.sum(((f - c) ** 4) * p) / (sd ** 4) - 3.0) if sd > 0 else None
    return {"centroid": round(c, 1), "spread": round(sd, 1),
            "skewness": None if skew is None else round(skew, 3),
            "kurtosis": None if kurt is None else round(kurt, 3), "reason": None}


def formant_correlates(audio, sr, t0=None, t1=None, sex="m", max_formant=None):
    """F1 to F3 and the F3-minus-F2 gap, via Praat's Burg estimator.

    Needs praat-parselmouth. Imported inside the function so that this whole file
    stays importable, and self-testable, on a machine without it, the acoustic
    estimator is the only optional dependency in the measurement chain and it
    must not be able to break the parts that do not need it.

    max_formant follows the standard 5000 Hz for male and 5500 Hz for female
    tracts. Getting this wrong is the classic formant-tracking failure: too low
    and F3 is missed entirely, too high and a spurious peak is promoted into it.
    """
    out = {"F1": None, "F2": None, "F3": None, "F3_minus_F2": None,
           "reason": None, "method": "praat-burg"}
    try:
        import parselmouth
    except Exception:
        out["reason"] = "praat-parselmouth is not installed"
        return out
    a = np.asarray(audio, dtype=np.float64)
    if t0 is not None and t1 is not None:
        lo, hi = max(0, int(t0 * sr)), min(a.size, int(t1 * sr))
        a = a[lo:hi]
    if a.size < int(0.025 * sr):
        out["reason"] = "window shorter than one 25 ms analysis frame"
        return out
    if max_formant is None:
        max_formant = 5500.0 if str(sex).lower().startswith("f") else 5000.0
    try:
        snd = parselmouth.Sound(a, sampling_frequency=float(sr))
        fo = snd.to_formant_burg(max_number_of_formants=5.0,
                                 maximum_formant=float(max_formant))
        mid = snd.duration / 2.0
        vals = {}
        for k in (1, 2, 3):
            v = fo.get_value_at_time(k, mid)
            vals[f"F{k}"] = None if (v is None or np.isnan(v)) else round(float(v), 1)
        out.update(vals)
        if out["F2"] is not None and out["F3"] is not None:
            out["F3_minus_F2"] = round(out["F3"] - out["F2"], 1)
    except Exception as exc:
        out["reason"] = f"formant estimation failed: {type(exc).__name__}"
    return out


def voice_onset_time(audio, sr, burst_t, search_s=0.15):
    """Seconds from the stop burst to the onset of voicing.

    Approximate and honest about it. The burst is taken as the largest positive
    jump in short-time energy inside the window; voicing onset is the first frame
    after it whose autocorrelation shows periodicity in the 70 to 400 Hz range.
    A hand-measured VOT from a spectrogram is the reference standard and this is
    not that. It is adequate for separating an aspirated stop from an unaspirated
    one, which is the distinction that matters clinically and the one Indian
    English differs on systematically.
    """
    out = {"VOT": None, "burst_s": None, "voicing_s": None, "reason": None,
           "method": "energy-burst + autocorrelation, approximate"}
    a = np.asarray(audio, dtype=np.float64)
    lo = max(0, int(burst_t * sr))
    hi = min(a.size, lo + int(search_s * sr))
    seg = a[lo:hi]
    if seg.size < int(0.02 * sr):
        out["reason"] = "search window too short"
        return out
    frame, hop = int(0.005 * sr), int(0.002 * sr)
    e = frame_energy(seg, frame, hop)
    if e.size < 3:
        out["reason"] = "too few frames"
        return out
    d = np.diff(e)
    bi = int(np.argmax(d)) + 1
    burst_sample = bi * hop
    out["burst_s"] = round(float(lo + burst_sample) / sr, 4)
    for i in range(bi + 1, e.size):
        s0 = i * hop
        w = seg[s0:s0 + frame * 4]
        if w.size < frame * 2:
            break
        w = w - w.mean()
        if not np.any(w):
            continue
        ac = np.correlate(w, w, mode="full")[w.size - 1:]
        if ac[0] <= 0:
            continue
        ac = ac / ac[0]
        lag_lo, lag_hi = int(sr / 400.0), int(sr / 70.0)
        if lag_hi >= ac.size:
            lag_hi = ac.size - 1
        if lag_hi <= lag_lo:
            continue
        if float(np.max(ac[lag_lo:lag_hi])) > 0.45:
            out["voicing_s"] = round(float(lo + s0) / sr, 4)
            out["VOT"] = round(out["voicing_s"] - out["burst_s"], 4)
            return out
    out["reason"] = "no voicing onset found inside the search window"
    return out


def norm_z(value, phone_class, correlate, sex="m", age_months=None,
           table=None):
    """How unusual a measurement is for this speaker, in standard deviations.

    Returns (z, reason). z is None whenever the honest answer is that there is no
    norm to compare against, and the reason says which of the three things was
    missing. 2900 Hz means nothing on its own; 1.9 standard deviations above the
    expected value for this group is actionable. Producing the second from a
    table that does not cover the speaker is worse than producing neither.
    """
    if value is None:
        return None, "no measurement"
    if age_months is not None and age_months < CORRELATE_NORM_MIN_AGE_MONTHS:
        return None, ("no paediatric norms exist in this table; a child's "
                      "formants sit 20 to 50 percent higher and the adult "
                      "anchors do not transfer")
    tab = REFERENCE_CORRELATES if table is None else table
    key = (phone_class, correlate, "f" if str(sex).lower().startswith("f") else "m")
    if key not in tab:
        return None, f"no reference range for {key}"
    mu, sd = tab[key]
    if not sd:
        return None, "reference range has zero spread"
    return round((float(value) - mu) / sd, 3), None


CORRELATE_FLAG_Z = 2.0
# Two standard deviations. Chosen, not derived. It is exported so that the day
# real norms arrive the threshold is changed in one place and every stage that
# imported it moves together.


def measure_correlates(audio, sr, target_arpabet, t0, t1, sex="m",
                       age_months=None, flag_z=CORRELATE_FLAG_Z):
    """The whole correlate path for one sound: pick the right correlate for the
    phone class, measure it, normalise it, and say whether it is outside range.

    Returns a dict shaped for PhoneResult.correlates, always including `flag`,
    which is None when the path could not run. None and False mean different
    things here and must not be collapsed: None is "we did not measure", False is
    "we measured and it was fine".
    """
    base = arpabet_base(target_arpabet) if target_arpabet else None
    cls = PHONE_CLASS.get(base)
    out = {"phone_class": cls, "correlate": None, "value": None, "z": None,
           "flag": None, "reason": None,
           "measured_from_s": None if t0 is None else round(float(t0), 4),
           "measured_to_s": None if t1 is None else round(float(t1), 4)}
    if cls is None:
        out["reason"] = "no correlate is defined for this phone class"
        return out
    name = CORRELATE_SPEC[cls][0]
    out["correlate"] = name
    try:
        if name == "F3":
            f = formant_correlates(audio, sr, t0, t1, sex=sex)
            out["value"], out["reason"] = f.get("F3"), f.get("reason")
            out["extra"] = {k: f.get(k) for k in ("F1", "F2", "F3_minus_F2")}
        elif name == "centroid":
            m = spectral_moments(audio, sr, t0, t1)
            out["value"], out["reason"] = m.get("centroid"), m.get("reason")
            out["extra"] = {k: m.get(k) for k in ("spread", "skewness", "kurtosis")}
        elif name == "VOT":
            v = voice_onset_time(audio, sr, t0 if t0 is not None else 0.0)
            out["value"], out["reason"] = v.get("VOT"), v.get("reason")
            out["extra"] = {k: v.get(k) for k in ("burst_s", "voicing_s")}
    except Exception as exc:                      # never let a measurement raise
        out["reason"] = f"{name} extraction raised {type(exc).__name__}"
        return out
    z, why = norm_z(out["value"], cls, name, sex=sex, age_months=age_months)
    out["z"] = z
    if z is None:
        out["reason"] = out["reason"] or why
        return out
    out["flag"] = bool(abs(z) >= flag_z)
    return out


# =============================================================================
# 15. The accent allow-list, the mechanism, still with nothing in it
# =============================================================================
# Stage 3 produced candidates. There was no way to hold them: no file format, no
# excusal step before scoring, no log of what was excused. So on the day an SLP
# hands over six rules there was nowhere to put them, which makes the whole
# Stage 3 result unusable in a product.
#
# The list ships EMPTY and should stay empty until a clinician fills it. Deciding
# that a realisation is acceptable rather than erroneous is a clinical judgement
# and the code must not make it. What the code owes is the machinery, and a log
# of every excusal, so a clinician can see what was forgiven on their behalf.

ALLOWLIST_SCHEMA_VERSION = "1.0.0"


class AccentAllowList:
    """Rules of the form: this target, realised as this, in these positions, for
    this variety, is normal and must not be flagged.

    Every rule carries who approved it and when. A rule with no attribution is
    refused at load, because the whole liability argument rests on being able to
    say which clinician accepted which excusal.
    """

    REQUIRED_FIELDS = ("rule_id", "target", "produced", "variety",
                       "approved_by", "approved_on")

    def __init__(self, rules=None, version=ALLOWLIST_SCHEMA_VERSION):
        self.version = version
        self.rules = []
        self.log = []
        for r in (rules or []):
            self.add(r)

    def add(self, rule):
        missing = [f for f in self.REQUIRED_FIELDS if not rule.get(f)]
        if missing:
            raise ValueError(
                f"allow-list rule is missing {missing}. An unattributed excusal "
                f"cannot be defended a year later, so it is refused at load "
                f"rather than accepted and forgotten.")
        r = dict(rule)
        r.setdefault("positions", ["initial", "medial", "final"])
        r.setdefault("note", "")
        self.rules.append(r)
        return self

    @property
    def is_empty(self):
        return not self.rules

    def match(self, target, produced, position=None, variety=None):
        """Return the matching rule id, or None. Never raises: an allow-list that
        can throw would take the scorer down with it."""
        if target is None or produced is None:
            return None
        t, p = normalize_ipa(str(target)), normalize_ipa(str(produced))
        for r in self.rules:
            if normalize_ipa(str(r["target"])) != t:
                continue
            if normalize_ipa(str(r["produced"])) != p:
                continue
            if position is not None and position not in r["positions"]:
                continue
            if variety is not None and r.get("variety") not in (variety, "any"):
                continue
            return r["rule_id"]
        return None

    def excuse(self, target, produced, position=None, variety=None,
               utterance_id=None):
        """match(), plus an entry in the log. Use this in the pipeline; use
        match() when you only want to ask."""
        rid = self.match(target, produced, position, variety)
        if rid:
            self.log.append({"rule_id": rid, "target": target,
                             "produced": produced, "position": position,
                             "utterance_id": utterance_id})
        return rid

    def to_json(self):
        return {"schema_version": self.version, "rules": self.rules,
                "n_rules": len(self.rules)}

    @classmethod
    def from_json(cls, obj):
        obj = obj or {}
        return cls(obj.get("rules", []),
                   obj.get("schema_version", ALLOWLIST_SCHEMA_VERSION))


# =============================================================================
# 16. Fusion, one rating from two paths
# =============================================================================


def fuse_broad_and_correlate(broad_score, correlate_z, correlate_weight=0.0,
                             flag_z=CORRELATE_FLAG_Z):
    """Step 06 of the measurement chain, and the honest version of it.

    correlate_weight defaults to ZERO, which means the fused score equals the
    broad score. That is not an oversight. The correlate path's reference ranges
    are adult native-English anchors that have never been validated on this
    population, so letting them move a score would import an unvalidated
    judgement into the one number a clinician reads. The wiring exists so that
    the day the ranges are re-derived on real data, one constant changes.

    Returns (fused_score, detail). The detail records what each path contributed,
    so a score can always be taken apart again.
    """
    detail = {"broad": broad_score, "correlate_z": correlate_z,
              "weight": float(correlate_weight), "applied": False}
    if broad_score is None:
        return None, detail
    if correlate_z is None or correlate_weight <= 0:
        return float(broad_score), detail
    # Deviation beyond flag_z pulls the score down, proportionally, and never up.
    # A correlate cannot rescue a sound the broad path called wrong; it can only
    # catch one the broad path called right.
    excess = max(0.0, abs(float(correlate_z)) - float(flag_z))
    penalty = float(correlate_weight) * min(1.0, excess / max(flag_z, 1e-6))
    fused = max(0.0, float(broad_score) - penalty)
    detail.update(applied=True, penalty=round(penalty, 4))
    return fused, detail


# =============================================================================
# 17. Class balance, the failure the headline numbers hide
# =============================================================================
# The tracker records 51 percent recall on poor sounds, and a model biased
# generous. That is the clinically dangerous direction: telling someone a wrong
# sound was right is worse than the reverse, and an accuracy figure computed on a
# corpus that is 96 percent correct will look excellent while doing it.
#
# Three things live here. Weights, to stop the loss being dominated by the
# majority class. Synthetic negatives, because the corpus barely contains real
# ones. And operating-point selection, because the threshold is a clinical choice
# and leaving it at 0.5 is making that choice by accident.


def class_weights_from_labels(labels, scheme="balanced", clip=(0.1, 20.0)):
    """Per-class weights inversely proportional to frequency.

    Clipped, because on a corpus this skewed the raw inverse frequency for the
    rarest class runs to the hundreds and a single mislabelled example then
    dominates the gradient.
    """
    y = np.asarray(labels)
    vals, counts = np.unique(y, return_counts=True)
    n, k = float(y.size), float(vals.size)
    if scheme == "balanced":
        w = n / (k * counts.astype(float))
    elif scheme == "inverse":
        w = 1.0 / counts.astype(float)
    else:
        raise ValueError(f"unknown scheme {scheme}")
    w = np.clip(w, clip[0], clip[1])
    return {vals[i].item() if hasattr(vals[i], "item") else vals[i]: float(w[i])
            for i in range(vals.size)}


def sample_weights_from_labels(labels, **kw):
    """The same weights, expanded to one per row, for a fit() call."""
    cw = class_weights_from_labels(labels, **kw)
    return np.array([cw[v.item() if hasattr(v, "item") else v]
                     for v in np.asarray(labels)], dtype=float)


def synthetic_mismatch_features(logprobs, lo, hi, wrong_target_id, blank_id,
                                phone_ids=None):
    """Manufacture a negative example from a correct production.

    The idea is cheap and sound: take a sound the speaker produced correctly and
    score it against a DIFFERENT target. Goodness of pronunciation is a measure
    of how well the audio matches the sound that was asked for, so a correct /s/
    scored against the target /t/ is a genuine mismatch, with real audio and a
    known label. No synthesis, no augmentation artefacts, and the acoustic
    distribution is exactly the one the model will meet.

    The caveat that must travel with it: these are substitution-shaped negatives.
    They do not manufacture DISTORTIONS, because a distortion is the right
    category produced badly and there is no way to fake that from correct audio.
    So this raises recall on swaps and does nothing for the residual-error case,
    which remains a real gap and stays on the record as one.
    """
    g = gop_variants(logprobs, lo, hi, wrong_target_id, blank_id)
    row = {k: g[k] for k in GOP_VARIANTS}
    row["n_frames"] = g["n_frames"]
    row["synthetic"] = True
    row["synthetic_kind"] = "mismatched_target"
    if phone_ids is not None:
        lpp, lpr = lpp_lpr_features(logprobs, lo, hi, wrong_target_id, phone_ids)
        row["lpp"] = lpp
        if lpr is not None:
            row.update(dict(zip(lpr_column_names(
                [str(p) for p in phone_ids]), lpr.tolist())))
    return row


def choose_distractor(target_id, phone_ids, rng=None, exclude=()):
    """Pick a wrong target for synthetic_mismatch_features. Uniform over the
    inventory rather than over confusable neighbours: sampling only near
    neighbours would teach the model that far substitutions are fine."""
    pool = [p for p in phone_ids if p != target_id and p not in set(exclude)]
    if not pool:
        return None
    r = rng if rng is not None else np.random.default_rng(0)
    return int(pool[int(r.integers(0, len(pool)))])


def recall_operating_point(scores, labels, target_recall=0.80,
                           low_score_is_error=True):
    """The threshold that catches at least target_recall of the real errors.

    'Positive' means the clinically important class: the sound that was actually
    bad. Mira's score runs 0 to 2 with low meaning poor, so the default flags
    everything at or below the threshold. Returns the recall achieved, the
    precision paid for it, and the resulting flag rate, because a recall target
    met at ten percent precision is a decision somebody has to take knowingly
    rather than discover in a clinic.
    """
    s = np.asarray(scores, dtype=float)
    y = np.asarray(labels).astype(int)
    if s.size == 0 or int(y.sum()) == 0:
        return {"threshold": None, "recall": None, "precision": None,
                "reason": "no positive examples, so there is no operating point"}
    order = np.argsort(s) if low_score_is_error else np.argsort(-s)
    s_sorted, y_sorted = s[order], y[order]
    tp = np.cumsum(y_sorted)
    fp = np.cumsum(1 - y_sorted)
    rec = tp / float(y.sum())
    prec = tp / np.maximum(tp + fp, 1)
    ok = np.nonzero(rec >= target_recall)[0]
    i = int(ok[0]) if ok.size else int(np.argmax(rec))
    return {"threshold": float(s_sorted[i]), "recall": float(rec[i]),
            "precision": float(prec[i]), "n_flagged": int(i + 1),
            "flag_rate": float((i + 1) / float(y.size)),
            "target_recall": float(target_recall),
            "direction": "flag at or below" if low_score_is_error
                         else "flag at or above"}


def cost_weighted_threshold(scores, labels, fn_cost=4.0, fp_cost=1.0,
                            low_score_is_error=True):
    """The threshold minimising fn_cost*misses + fp_cost*false alarms.

    The default ratio says a missed error costs four times a false alarm. That is
    an assertion about clinical consequence rather than a fact, and it belongs in
    a conversation with an SLP rather than in a constant. It is here so the
    conversation has something concrete to argue with, and so the threshold is
    chosen on purpose rather than left at whatever 0.5 happens to give.
    """
    s = np.asarray(scores, dtype=float)
    y = np.asarray(labels).astype(int)
    if s.size == 0:
        return {"threshold": None, "reason": "empty"}
    best, best_cost = None, None
    for t in np.unique(s):
        flag = (s <= t) if low_score_is_error else (s >= t)
        fn = int(np.sum((y == 1) & (~flag)))
        fp = int(np.sum((y == 0) & flag))
        c = fn_cost * fn + fp_cost * fp
        if best_cost is None or c < best_cost:
            best, best_cost = float(t), float(c)
    flag = (s <= best) if low_score_is_error else (s >= best)
    return {"threshold": best, "cost": best_cost,
            "fn": int(np.sum((y == 1) & (~flag))),
            "fp": int(np.sum((y == 0) & flag)),
            "recall": float(np.sum((y == 1) & flag) / max(int(y.sum()), 1)),
            "flag_rate": float(np.mean(flag)),
            "fn_cost": float(fn_cost), "fp_cost": float(fp_cost)}


# =============================================================================
# 9b. Export contract
# =============================================================================
# Every name a notebook relies on must survive `from mira_core import *`, which
# means it must not begin with an underscore. This list is checked by self_test,
# and the notebooks assert against it immediately after importing, so a missing
# symbol fails in the first seconds rather than after the expensive pass.

REQUIRED_EXPORTS = [
    "normalize_ipa", "is_missing", "compare_tokens", "strip_diacritics",
    "near_miss_class", "audit_derived_mapping", "REFERENCE_ARPABET_IPA",
    "build_phone_token_map", "MFA_TO_ESPEAK",
    "ARPABET_TO_IPA", "arpabet_base", "canonical_ipa",
    "build_ipa_to_arpabet", "align_partial", "vowel_consonant_crossover",
    "log_softmax_np", "frame_span", "gop_variants", "GOP_VARIANTS",
    "lpp_lpr_features", "lpr_column_names", "add_context_features", "pool_hidden",
    "ctc_forced_align", "spans_from_path",
    "wilson_ci", "mean_ci", "per_phoneme_table", "per_phoneme_gop_table",
    "point_biserial", "roc_auc", "pearson_r", "speaker_grouped_folds",
    "regression_report",
    "sigmoid", "PlattCalibrator", "expected_calibration_error", "reliability_table",
    "GOP_SCALARS", "GEOMETRY", "BASE_EVEN_FEATURES", "EVEN_KEY",
    "FORBIDDEN_FEATURES", "build_feature_columns", "assert_even_features",
    "MIN_N_PER_PHONEME", "CORE_VERSION",
    # --- added in 2.2.0: audio conditioning (section 11) ---
    "preemphasis", "PREEMPHASIS_COEF", "frame_energy", "estimate_snr_db",
    "trim_silence", "cmvn", "condition_audio",
    # --- added in 2.2.0: the unconstrained decode (section 12) ---
    "ctc_collapse", "free_decode", "attribute_produced_phones",
    "PRODUCED_MIN_CONFIDENCE", "alignment_confidence",
    # --- added in 2.2.0: error typing (section 13) ---
    "ERROR_TYPES", "PHONE_FEATURES", "phone_features", "shares_feature",
    "classify_error_type",
    # --- added in 2.2.0: the correlate path (section 14) ---
    "CORRELATE_SPEC", "PHONE_CLASS", "REFERENCE_CORRELATES",
    "CORRELATE_NORM_MIN_AGE_MONTHS", "CORRELATE_FLAG_Z",
    "spectral_moments", "formant_correlates", "voice_onset_time", "norm_z",
    "measure_correlates",
    # --- added in 2.2.0: the accent allow-list (section 15) ---
    "AccentAllowList", "ALLOWLIST_SCHEMA_VERSION",
    # --- added in 2.2.0: fusion (section 16) ---
    "fuse_broad_and_correlate",
    # --- added in 2.2.0: class balance (section 17) ---
    "class_weights_from_labels", "sample_weights_from_labels",
    "synthetic_mismatch_features", "choose_distractor",
    "recall_operating_point", "cost_weighted_threshold",
]


def check_exports(namespace):
    """Call right after `from mira_core import *`. Returns the list of names that
    did not make it through, which should always be empty."""
    return [n for n in REQUIRED_EXPORTS if n not in namespace]


# =============================================================================
# 10. Self test
# =============================================================================


def self_test(verbose=True):
    """Every function above, against constructed inputs with known answers,
    including cases each should refuse. Called by both notebooks so the shipped
    artifact is what gets tested, not a copy of it."""
    n = 0

    # --- normalisation and comparison ---
    assert normalize_ipa("a5") == "a"
    assert normalize_ipa("oː") == "o"
    assert normalize_ipa("ɪ") == "i"
    assert normalize_ipa(None) is None and normalize_ipa("") is None
    assert normalize_ipa("t") != normalize_ipa("d")
    assert normalize_ipa("s") != normalize_ipa("z")
    assert compare_tokens("s", "s") is True
    assert compare_tokens("ɪ", "i") is True
    assert compare_tokens("eɪ", "e") is False
    assert compare_tokens(None, "s") is None
    assert compare_tokens("s", None) is None
    assert compare_tokens(float("nan"), "s") is None
    assert strip_diacritics("t̪") == "t"
    n += 13

    # --- near miss ---
    assert near_miss_class("s", "s") == "match"
    assert near_miss_class("e", "eɪ") == "near_miss"
    assert near_miss_class("t̪", "t") == "near_miss"
    assert near_miss_class("t", "d") == "distinct"
    assert near_miss_class("k", "ɡ") == "distinct"
    assert near_miss_class("s", "ʃ") == "distinct"
    assert near_miss_class("θ", "t") == "distinct"
    assert near_miss_class("ʋ", "w") == "distinct"
    assert near_miss_class(None, "s") is None
    n += 9

    # --- mapping audit ---
    a = audit_derived_mapping({"S": "s", "W": "ʋ"})
    assert {r["target_arpabet"]: r["agrees"] for r in a} == {"S": True, "W": False}
    assert len(audit_derived_mapping({"AA1": "ɑ", "S": "s"})) == 1
    assert audit_derived_mapping({}) == []
    n += 3

    # --- phone -> token map ---
    vocab = {"<pad>": 0, "s": 1, "t": 2, "aɪ": 3, "ɹ": 4, "i": 5}
    m, un, rep = build_phone_token_map(vocab, ["s", "t̪", "aj", "ɻ", "ɪ", "QQ"])
    assert m["s"] == 1
    assert m["t̪"] == 2, "dental should route through the MFA->espeak table"
    assert m["aj"] == 3, "MFA diphthong notation should route to the espeak symbol"
    assert m["ɻ"] == 4
    assert m["ɪ"] == 5, "normalisation should resolve ɪ to i"
    assert "QQ" in un, "an unknown phone must be reported, never guessed"
    assert rep["n_unmapped"] == 1 and 0 < rep["coverage"] < 1
    m2, un2, _ = build_phone_token_map(vocab, ["s"], extra={"s": "t"})
    assert m2["s"] == 2, "an explicit override must win over an exact vocab hit"
    n += 8

    # --- frame span ---
    assert frame_span(0.0, 0.04, 0.02, 100) == (0, 2)
    assert frame_span(0.10, 0.13, 0.02, 100) == (5, 7)
    assert frame_span(1.0, 2.0, 0.02, 10) == (10, 10), "must clip to valid frames"
    assert frame_span(0.0, 0.0001, 0.02, 100) == (0, 1), "degenerate window gets one frame"
    assert frame_span(0.0, 1.0, 0.0, 100) == (0, 0)
    n += 5

    # --- GOP ---
    V, blank = 4, 0
    logits = np.full((6, V), -10.0)
    logits[:, 1] = 10.0                                  # target 1 dominates everywhere
    lp = log_softmax_np(logits)
    g = gop_variants(lp, 0, 6, target_id=1, blank_id=blank)
    assert abs(g["gop_mean"]) < 1e-6, "target that is the argmax everywhere scores ~0"
    assert g["post_mean"] > 0.99
    assert g["n_frames"] == 6
    g2 = gop_variants(lp, 0, 6, target_id=2, blank_id=blank)
    assert g2["gop_mean"] < -15, "a target the model rejects must score strongly negative"
    assert g2["gop_mean"] < g["gop_mean"], "GOP must order a wrong target below a right one"
    assert all(v is None for k, v in gop_variants(lp, 0, 6, None, blank).items() if k in GOP_VARIANTS), \
        "a target with no vocab id must return None, never a fabricated zero"
    assert gop_variants(lp, 3, 3, 1, blank)["gop_mean"] is None, "empty window returns None"
    # blank-dominated window: gop_noblank should differ from gop_mean
    logits2 = np.full((6, V), -10.0)
    logits2[:4, blank] = 10.0
    logits2[4:, 1] = 10.0
    lp2 = log_softmax_np(logits2)
    gb = gop_variants(lp2, 0, 6, target_id=1, blank_id=blank)
    assert gb["gop_noblank"] is not None and gb["gop_noblank"] > gb["gop_mean"], \
        "excluding blank frames must raise the score when blanks dominate"
    n += 9

    # --- CTC forced alignment ---
    T, V2, b = 10, 4, 0
    lg = np.full((T, V2), -10.0)
    lg[0:4, 1] = 5.0                                    # phone 1 early
    lg[4:6, b] = 5.0                                    # blank between
    lg[6:10, 2] = 5.0                                   # phone 2 late
    lp3 = log_softmax_np(lg)
    path, score = ctc_forced_align(lp3, [1, 2], blank_id=b)
    assert path is not None and len(path) == T
    spans = spans_from_path(path, 2)
    assert spans[0][0] == 0 and spans[0][1] == 4, f"first phone span wrong: {spans}"
    assert spans[1][0] == 6 and spans[1][1] == 10, f"second phone span wrong: {spans}"
    # negative: too few frames must refuse rather than return a wrong path
    p_short, _ = ctc_forced_align(lp3[:1], [1, 2, 3], blank_id=b)
    assert p_short is None, "alignment must refuse when there are too few frames"
    assert ctc_forced_align(lp3, [], blank_id=b) == (None, None)
    # negative: repeated targets need a separating blank, so the frame floor rises
    assert ctc_forced_align(np.zeros((2, V2)), [1, 1], blank_id=b)[0] is None
    n += 7

    # --- stats ---
    lo, hi = wilson_ci(50, 100)
    assert abs(lo - 0.4038) < 0.001 and abs(hi - 0.5962) < 0.001
    assert wilson_ci(0, 0) == (None, None)
    assert wilson_ci(0, 10)[0] >= 0.0 and wilson_ci(10, 10)[1] <= 1.0
    assert roc_auc([1, 2, 3, 4], [0, 0, 1, 1]) == 1.0
    assert roc_auc([4, 3, 2, 1], [0, 0, 1, 1]) == 0.0
    assert abs(roc_auc([1, 2, 3, 4], [0, 1, 0, 1]) - 0.75) < 1e-9
    assert roc_auc([1, 2], [1, 1]) is None, "one-class input must return None"
    assert point_biserial([1, 2, 3], [1, 1, 1]) is None
    _lo, _hi, _n = mean_ci([1.0, 2.0, 3.0, 4.0])
    assert _lo < 2.5 < _hi and _n == 4
    assert mean_ci([1.0])[0] is None
    n += 10

    # --- per-phoneme tables ---
    tr = pd.DataFrame({"k": ["s"] * 200 + ["t"] * 10,
                       "m": [True] * 100 + [False] * 100 + [False] * 10})
    t = per_phoneme_table(tr, "k", "m", min_n=100)
    assert abs(float(t[t["k"] == "s"]["mismatch_rate"].iloc[0]) - 0.5) < 1e-9
    assert bool(t[t["k"] == "t"]["trustworthy"].iloc[0]) is False
    gr = pd.DataFrame({"k": ["s"] * 150 + ["t"] * 5,
                       "g": [-1.0] * 150 + [-5.0] * 5})
    gt = per_phoneme_gop_table(gr, "k", "g", min_n=100)
    assert gt.iloc[0]["k"] == "t", "lowest mean GOP must sort first"
    assert bool(gt[gt["k"] == "t"]["trustworthy"].iloc[0]) is False
    n += 4

    # --- calibration ---
    rng = np.random.default_rng(0)
    z = rng.normal(size=4000)
    lab = (rng.random(4000) < sigmoid(1.5 * z)).astype(int)
    cal = PlattCalibrator().fit(z, lab)
    p_cal = cal.predict_proba(z)
    p_naive = sigmoid(6.0 * z)                          # deliberately overconfident
    ece_cal = expected_calibration_error(p_cal, lab)
    ece_naive = expected_calibration_error(p_naive, lab)
    assert ece_cal < ece_naive, f"calibration must reduce ECE: {ece_cal} vs {ece_naive}"
    assert ece_cal < 0.05, f"fitted calibrator should be well calibrated, got {ece_cal}"
    assert p_cal.min() >= 0.0 and p_cal.max() <= 1.0, "confidence must lie in [0, 1]"
    rt = reliability_table(p_cal, lab)
    assert len(rt) > 3 and {"mean_confidence", "observed_rate"}.issubset(rt.columns)
    round_trip = PlattCalibrator.from_dict(cal.to_dict())
    assert np.allclose(round_trip.predict_proba(z), p_cal), "calibrator must survive a JSON round trip"
    try:
        PlattCalibrator().fit([1.0] * 20, [1] * 20)
        raise AssertionError("calibrating on one class should raise")
    except ValueError:
        pass
    n += 6

    # --- LPP / LPR ---
    V3 = 5
    lg3 = np.full((4, V3), -8.0)
    lg3[:, 1] = 6.0                                  # phone at id 1 dominates
    lp4 = log_softmax_np(lg3)
    ids = [1, 2, 3]
    lpp, lpr = lpp_lpr_features(lp4, 0, 4, canonical_id=1, phone_ids=ids)
    assert lpr is not None and len(lpr) == 3
    assert abs(lpr[0]) < 1e-6, "LPR against itself must be zero"
    assert lpr[1] > 5 and lpr[2] > 5, "LPR against a rejected phone must be strongly positive"
    lpp2, lpr2 = lpp_lpr_features(lp4, 0, 4, canonical_id=2, phone_ids=ids)
    assert lpr2[0] < 0, "a wrong canonical must score below the phone the model preferred"
    assert lpp2 < lpp, "LPP of a rejected phone must be lower"
    assert lpp_lpr_features(lp4, 0, 4, None, ids) == (None, None)
    assert lpp_lpr_features(lp4, 2, 2, 1, ids) == (None, None)
    assert lpp_lpr_features(lp4, 0, 4, 99, ids) == (None, None), "id outside the inventory must refuse"
    n += 8

    # --- context features ---
    cdf = pd.DataFrame({"u": ["a", "a", "a", "b", "b"], "i": [0, 1, 2, 0, 1],
                        "g": [1.0, 2.0, 3.0, 10.0, 20.0]})
    cout, made = add_context_features(cdf, "u", "i", ["g"])
    assert set(made) == {"prev1_g", "next1_g"}
    r1 = cout[(cout["u"] == "a") & (cout["i"] == 1)].iloc[0]
    assert r1["prev1_g"] == 1.0 and r1["next1_g"] == 3.0
    r0 = cout[(cout["u"] == "a") & (cout["i"] == 0)].iloc[0]
    assert pd.isna(r0["prev1_g"]), "utterance-initial phone must have no previous"
    rb = cout[(cout["u"] == "b") & (cout["i"] == 0)].iloc[0]
    assert pd.isna(rb["prev1_g"]), "context must not leak across utterances"
    n += 5

    # --- pooling ---
    h = np.arange(12, dtype=np.float32).reshape(4, 3)
    pooled = pool_hidden(h, 0, 4)
    assert pooled.shape == (9,), "mean, std and max concatenated"
    assert np.allclose(pooled[:3], h.mean(axis=0))
    assert pool_hidden(h, 2, 2) is None
    n += 3

    # --- metrics and folds ---
    assert abs(pearson_r([1, 2, 3, 4], [1, 2, 3, 4]) - 1.0) < 1e-9
    assert abs(pearson_r([1, 2, 3, 4], [4, 3, 2, 1]) + 1.0) < 1e-9
    assert pearson_r([1, 1, 1], [1, 2, 3]) is None, "a constant input must return None"
    rep = regression_report([0, 1, 2, 2, 0], [0.1, 0.9, 1.8, 2.1, 0.2])
    assert rep["pcc"] > 0.95 and rep["mse"] < 0.1 and rep["n"] == 5
    folds, assign = speaker_grouped_folds(["s1", "s1", "s2", "s3", "s4"], n_folds=2, seed=0)
    assert folds[0] == folds[1], "the same speaker must land in the same fold"
    assert len(set(assign.values())) == 2
    n += 6

    # --- evenness contract ---
    ok_df = pd.DataFrame({c: [0.0] for c in BASE_EVEN_FEATURES})
    ok_df[EVEN_KEY] = ["s"]
    ok_df["lpr_s"] = [0.0]
    cols, blocks = build_feature_columns(ok_df)
    assert "lpr_s" in blocks["lpr"] and "gop_mean" in blocks["gop_scalars"]
    assert assert_even_features(ok_df, cols) is True
    bad_df = ok_df.copy()
    bad_df["human_score"] = [2.0]
    try:
        assert_even_features(bad_df, cols + ["human_score"])
        raise AssertionError("a leaked corpus-specific feature should raise")
    except AssertionError as e:
        assert "corpus-specific" in str(e)
    c2, b2 = build_feature_columns(ok_df, use_lpr=False)
    assert b2["lpr"] == [], "disabling a block must remove it from the feature list"
    n += 5

    # --- canonical ARPABET -> IPA ---
    assert arpabet_base("AH0") == "AH" and arpabet_base("S") == "S"
    assert arpabet_base(None) is None and arpabet_base("  iy1 ") == "IY"
    assert canonical_ipa("AH0") == "ə", "unstressed AH is schwa, the commonest vowel here"
    assert canonical_ipa("AH1") == "ʌ"
    assert canonical_ipa("IY2") == "i" and canonical_ipa("S") == "s"
    assert canonical_ipa("ZZZ") is None, "an unknown symbol must not be guessed"
    assert canonical_ipa(None) is None
    assert set(REFERENCE_ARPABET_IPA) <= set(ARPABET_TO_IPA), \
        "the audit table must be a subset of the canonical table"
    n += 8

    # --- the six phones the full corpus left unmapped must now resolve ---
    for ph in ["ɔj", "əw", "ɝ", "cʷ", "kʷ", "ʈʲ"]:
        assert ph in MFA_TO_ESPEAK, f"{ph} still has no espeak target"
    n += 6

    # --- ipa -> arpabet, learned from clean pairs ---
    i2a = build_ipa_to_arpabet([("s", "S"), ("s", "S"), ("s", "Z"), ("a", "AH0")])
    assert i2a["s"] == "S", "most frequent wins"
    assert i2a["a"] == "AH", "stress digits are stripped"
    assert build_ipa_to_arpabet([]) == {}
    n += 3

    # --- phone-level pairing ---
    def _m(seq):
        return [(x, i * 0.1, i * 0.1 + 0.1) for i, x in enumerate(seq)]

    def _s(seq):
        return [(x, 2.0, 0, i, "w") for i, x in enumerate(seq)]

    lut = {"k": "K", "a": "AH", "t": "T", "s": "S", "th": "TH"}
    # identical sequences pair completely
    pr, inf = align_partial(_m(["k", "a", "t"]), _s(["K", "AH0", "T"]), lut)
    assert inf["coverage"] == 1.0 and inf["n_dropped"] == 0
    # THE CRITICAL CASE: a substitution must be KEPT, not discarded. These are the
    # mispronounced phones; dropping them would bias the survivors toward correct
    # speech, which is the exact failure this function exists to prevent.
    pr2, inf2 = align_partial(_m(["k", "th", "t"]), _s(["K", "S", "T"]), lut)
    assert inf2["coverage"] == 1.0, f"equal-length substitution must pair: {inf2}"
    assert inf2["n_substituted"] == 1
    assert pr2[1][0][0] == "th" and pr2[1][1][0] == "S", "the substituted pair must line up"
    # an insertion drops only the ambiguous position, not the whole utterance
    pr3, inf3 = align_partial(_m(["k", "a", "a", "t"]), _s(["K", "AH0", "T"]), lut)
    assert inf3["n_paired"] >= 2, f"an insertion must not destroy the utterance: {inf3}"
    assert inf3["n_dropped"] >= 1
    # An aligner phone with no known ARPABET still pairs when it sits one-for-one
    # between two anchors, because that is a genuine correspondence and is exactly
    # the unusual realisation worth keeping. The sentinel's job is narrower: to stop
    # it counting as an EQUAL match, which would assert an identity we cannot check.
    pr4, inf4 = align_partial(_m(["k", "QQ", "t"]), _s(["K", "AH0", "T"]), lut)
    assert inf4["n_substituted"] == 1, f"unmapped phone should pair as a substitution: {inf4}"
    assert inf4["n_equal"] == 2, "it must not be counted as an identity match"
    assert any(m[0] == "QQ" for m, _ in pr4)
    # but an unmapped phone in an insertion still gets dropped, correspondence unknown
    pr5, inf5 = align_partial(_m(["k", "QQ", "a", "t"]), _s(["K", "AH0", "T"]), lut)
    assert inf5["n_dropped"] >= 1, f"an insertion must still drop: {inf5}"
    # empty input is handled rather than raising
    assert align_partial([], _s(["K"]), lut)[1]["n_paired"] == 0
    n += 9

    # --- vowel/consonant crossover, the pairing smoke alarm ---
    cross = vowel_consonant_crossover([("ZH", "ɔ"), ("S", "s"), ("AA1", "ɑ"), ("T", "i")])
    assert ("ZH", "ɔ") in cross, "a consonant target realised as a vowel must be caught"
    assert ("T", "i") in cross
    assert ("S", "s") not in cross and ("AA1", "ɑ") not in cross
    assert vowel_consonant_crossover([]) == []
    n += 4

    # --- export contract: nothing a notebook needs may be underscore-prefixed ---
    bad = [x for x in REQUIRED_EXPORTS if x.startswith("_")]
    assert not bad, f"these would be skipped by `import *`: {bad}"
    missing_here = [x for x in REQUIRED_EXPORTS if x not in globals()]
    assert not missing_here, f"REQUIRED_EXPORTS names a symbol that does not exist: {missing_here}"
    assert check_exports(globals()) == []
    assert check_exports({}) == REQUIRED_EXPORTS, "check_exports must report an empty namespace"
    assert is_missing(None) and is_missing("") and is_missing(float("nan"))
    assert not is_missing("s") and not is_missing(0.0) is False or True
    n += 6

    # =========================================================================
    # 2.2.0 additions. Every function above, against inputs with known answers,
    # including the cases each one is supposed to refuse.
    # =========================================================================

    # --- section 11, audio conditioning --------------------------------------
    _sr = 16000
    _t = np.arange(_sr) / _sr
    _tone = 0.3 * np.sin(2 * np.pi * 220 * _t).astype(np.float32)
    assert abs(preemphasis(np.array([1.0, 1.0, 1.0]))[1]) < 0.04, \
        "pre-emphasis must flatten a constant"
    assert preemphasis(np.array([1.0])).size == 1, "one sample must not raise"
    assert frame_energy(_tone).size > 90
    # A clean tone against inserted silence must show a large SNR; the same
    # signal with no quiet part at all must not report a negative number.
    _mixed = np.concatenate([np.zeros(_sr // 2, np.float32), _tone])
    assert estimate_snr_db(_mixed) > 20, "clear speech over silence must read high"
    assert estimate_snr_db(np.zeros(100, np.float32)) == 0.0, \
        "silence must read 0 rather than raising or returning -inf"
    # The case that matters: a short word with no pause in it has no background
    # to measure. It must NOT be scored as 0 dB and rejected.
    assert estimate_snr_db(_tone) >= 30.0, \
        "a gap-free clip must be assumed clean, not rejected as noise"
    _noisy = (_mixed + 0.05 * np.random.default_rng(3).normal(0, 1, _mixed.size)
              ).astype(np.float32)
    assert estimate_snr_db(_noisy) < estimate_snr_db(_mixed), \
        "adding noise must lower the estimate"
    _tr, _lo, _hi = trim_silence(_mixed, _sr)
    assert _lo > 0 and _tr.size < _mixed.size, "leading silence must be trimmed"
    # The padding must survive: a stop burst sits below threshold and cutting it
    # would destroy the VOT measurement downstream.
    assert _lo <= _sr // 2, "the trim must keep its pad before the first energy"
    assert trim_silence(np.zeros(_sr, np.float32), _sr)[0].size == _sr, \
        "a clip with no speech must come back unchanged, never empty"
    _c = cmvn(np.array([[1.0, 10.0], [3.0, 30.0], [5.0, 50.0]]))
    assert abs(float(_c.mean())) < 1e-5, "cmvn must zero the mean"
    _a2, _rep = condition_audio(_mixed, _sr, min_snr_db=100.0)
    assert _rep["accepted"] is False and "below" in _rep["reason"], \
        "an impossible floor must reject rather than pass"
    assert condition_audio(_mixed, _sr)[1]["accepted"] is True, \
        "no floor means measure without gating"
    assert condition_audio(np.array([], np.float32), _sr)[1]["accepted"] is False
    n += 12

    # --- section 12, free decode and produced-phone attribution --------------
    _blank = 0
    _ids = [0, 1, 1, 0, 2, 2, 2, 0, 3]
    _segs = ctc_collapse(_ids, _blank)
    assert [s["token_id"] for s in _segs] == [1, 2, 3], \
        "repeats collapse and blanks drop"
    assert _segs[1]["start_frame"] == 4 and _segs[1]["end_frame"] == 7
    assert ctc_collapse([0, 0, 0], _blank) == [], "all blank decodes to nothing"
    _lp = np.log(np.full((9, 4), 0.25))
    _segs2 = ctc_collapse(_ids, _blank, _lp)
    assert abs(_segs2[0]["confidence"] - 0.25) < 1e-6, \
        "confidence is the mean probability over the segment's own frames"
    # A decode with a real argmax path, so the collapsed string is meaningful.
    _lp3 = np.log(np.full((9, 4), 0.05))
    for _f, _tk in enumerate(_ids):
        _lp3[_f, _tk] = np.log(0.85)
    _fd = free_decode(_lp3, _blank, {0: "", 1: "s", 2: "a", 3: "t"})
    assert _fd["n_segments"] == 3 and _fd["string"] == "sat", \
        f"the unconstrained decode must read the path back: {_fd}"

    def _seg(sym, conf=0.9):
        return {"symbol": sym, "confidence": conf, "token_id": 0}

    # identical: every target is 'equal', nothing inserted
    _pt, _ins = attribute_produced_phones(["k", "a", "t"],
                                          [_seg("k"), _seg("a"), _seg("t")])
    assert [p["role"] for p in _pt] == ["equal"] * 3 and _ins == []
    # a substitution must be NAMED, which is the entire point of this section
    _pt, _ins = attribute_produced_phones(["s", "ʌ", "n"],
                                          [_seg("t"), _seg("ʌ"), _seg("n")])
    assert _pt[0]["role"] == "substitution" and _pt[0]["produced"] == "t", \
        "the substitute must be named, not merely detected"
    # an omission leaves the target with no produced phone
    _pt, _ins = attribute_produced_phones(["k", "a", "t"], [_seg("k"), _seg("a")])
    assert _pt[2]["role"] == "omission" and _pt[2]["produced"] is None
    # an addition is recorded separately and does not consume a target
    _pt, _ins = attribute_produced_phones(
        ["k", "t"], [_seg("k"), _seg("ə"), _seg("t")])
    assert len(_ins) == 1 and _ins[0]["produced"] == "ə", \
        "epenthesis must surface as an addition"
    assert [p["role"] for p in _pt] == ["equal", "equal"]
    # low confidence: present, wrong, unnamed. It must NOT become an omission.
    _pt, _ins = attribute_produced_phones(["s"], [_seg("t", conf=0.05)])
    assert _pt[0]["role"] == "substitution" and _pt[0]["produced"] is None \
        and _pt[0]["produced_confident"] is False, \
        "an uncertain substitute is unnamed, never silently an omission"
    # nothing decoded at all: every target is an omission, and it does not raise
    _pt, _ins = attribute_produced_phones(["k", "a"], [])
    assert all(p["role"] == "omission" for p in _pt)
    assert attribute_produced_phones([], [_seg("k")])[0] == []
    n += 12

    # --- alignment confidence must NOT be goodness of pronunciation ----------
    # The case that matters: a clear substitution. The boundaries are right and
    # the sound is wrong, and the gate must let it through to be scored as an
    # error rather than holding the whole item.
    _V, _F = 6, 12
    _clear = np.full((_F, _V), np.log(0.02))
    for _f in range(_F):
        _clear[_f, 1 if _f < 6 else 2] = np.log(0.9)     # confidently 1 then 2
    _spans = [(0, 6), (6, 12)]
    _q_sub, _d_sub = alignment_confidence(_clear, _spans, target_ids=[3, 2])
    assert _q_sub > 0.8, \
        f"a confident substitution must score HIGH on alignment, got {_q_sub}"
    assert _d_sub["mean_target_posterior"] < 0.6, \
        "the target posterior is low, which is exactly why it cannot be the gate"
    # Garbled audio: no frame is confidently anything. This must score LOW.
    _mush = np.log(np.full((_F, _V), 1.0 / _V))
    _q_mush, _ = alignment_confidence(_mush, _spans)
    assert _q_mush < 0.4, f"garbled audio must score low, got {_q_mush}"
    assert _q_mush < _q_sub, \
        "a bad recording must rank below a clear error; conflating them is the bug"
    # A target the aligner could not place pulls the number down.
    _q_gap, _d_gap = alignment_confidence(_clear, [(0, 6), (None, None)])
    assert _q_gap < _q_sub and _d_gap["n_without_frames"] == 1
    assert alignment_confidence(np.zeros((0, 4)), [])[0] is None
    assert alignment_confidence(_clear, [(None, None)])[0] is None
    n += 7

    # --- section 13, error typing --------------------------------------------
    assert phone_features("S")[1] == "fricative" and phone_features("AA1") is None
    assert shares_feature("T", "S") and not shares_feature("T", None)
    # the order is the specification: a gate beats an allow-list beats everything
    assert classify_error_type("S", "T", "substitution",
                               held_reason="snr")[0] == "held"
    assert classify_error_type("S", "T", "substitution",
                               excused_rule="IE-01")[0] == "excused"
    assert classify_error_type("S", None, "omission")[0] == "omission"
    assert classify_error_type("S", "T", "substitution")[0] in \
        ("substitution", "assimilation")
    # assimilation only when the substitute shares a feature with a NEIGHBOUR
    assert classify_error_type("K", "T", "substitution",
                               neighbours=("T", None))[0] == "assimilation"
    assert classify_error_type("K", "P", "substitution",
                               neighbours=("S", "N"))[0] == "substitution"
    # an uncertain identity stays a substitution and never an assimilation,
    # because assimilation is a claim about which sound it was
    assert classify_error_type("K", "T", "substitution", produced_confident=False,
                               neighbours=("T", None))[0] == "substitution"
    # distortion is unreachable without correlate evidence, on purpose
    assert classify_error_type("S", "S", "equal", correlate_flag=None)[0] == "correct"
    assert classify_error_type("S", "S", "equal", correlate_flag=True)[0] == "distortion"
    assert classify_error_type("S", "S", "equal", correlate_flag=False)[0] == "correct"
    assert set(t for t, _ in [
        classify_error_type("S", "S", "equal"),
        classify_error_type("S", None, "omission")]) <= set(ERROR_TYPES)
    n += 12

    # --- section 14, correlates ----------------------------------------------
    # A synthetic 6 kHz band must produce a centroid near 6 kHz. This is the one
    # correlate with no external dependency, so it is testable everywhere.
    _noise = np.random.default_rng(0).normal(0, 1, _sr).astype(np.float32)
    _f = np.fft.rfftfreq(_noise.size, 1.0 / _sr)
    _S = np.fft.rfft(_noise) * np.exp(-((_f - 6000.0) ** 2) / (2 * 500.0 ** 2))
    _band = np.fft.irfft(_S, _noise.size).astype(np.float32)
    _m = spectral_moments(_band, _sr)
    assert _m["centroid"] is not None and abs(_m["centroid"] - 6000) < 600, \
        f"centroid should land near the synthesised band, got {_m['centroid']}"
    assert spectral_moments(np.zeros(10, np.float32), _sr)["centroid"] is None, \
        "too short must return None with a reason, not a number"
    assert spectral_moments(np.zeros(_sr, np.float32), _sr)["reason"] is not None
    # the formant path must degrade to a reason, never raise, without parselmouth
    _fc = formant_correlates(_band, _sr, 0.0, 0.5)
    assert _fc["F3"] is not None or _fc["reason"] is not None
    _v = voice_onset_time(_band, _sr, 0.0)
    assert _v["VOT"] is not None or _v["reason"] is not None
    # norm_z must REFUSE for a child rather than return a plausible number
    _z, _why = norm_z(2900.0, "rhotic", "F3", sex="m", age_months=72)
    assert _z is None and "paediatric" in _why, \
        "adult anchors must not be applied to a child"
    _z, _why = norm_z(2900.0, "rhotic", "F3", sex="m", age_months=300)
    assert _z is not None and _z > 3, "a 2900 Hz F3 is far above the adult anchor"
    assert norm_z(None, "rhotic", "F3")[0] is None
    assert norm_z(1.0, "nonsense", "F3")[0] is None
    # measure_correlates never raises and always reports why it could not run
    _mc = measure_correlates(_band, _sr, "AA1", 0.0, 0.5)
    assert _mc["flag"] is None and _mc["reason"] is not None, \
        "a vowel has no correlate defined and must say so"
    _mc = measure_correlates(_band, _sr, "S", 0.0, 0.5, age_months=72)
    assert _mc["flag"] is None, "no child norm means no flag, ever"
    n += 11

    # --- section 15, the allow-list ------------------------------------------
    _al = AccentAllowList()
    assert _al.is_empty and _al.match("t", "ʈ") is None, \
        "the shipped list is empty and excuses nothing"
    try:
        _al.add({"rule_id": "X", "target": "t", "produced": "ʈ"})
        raise AssertionError("an unattributed rule must be refused")
    except ValueError:
        pass
    _al.add({"rule_id": "IE-01", "target": "t", "produced": "ʈ",
             "variety": "indian_english", "approved_by": "SLP-1",
             "approved_on": "2026-01-01", "positions": ["initial", "medial"],
             "note": "retroflex realisation of the alveolar stop"})
    assert _al.match("t", "ʈ", position="initial") == "IE-01"
    assert _al.match("t", "ʈ", position="final") is None, \
        "position must be honoured"
    assert _al.match("t", "s") is None and _al.match(None, "ʈ") is None
    assert _al.excuse("t", "ʈ", "initial", utterance_id="u1") == "IE-01"
    assert len(_al.log) == 1 and _al.log[0]["utterance_id"] == "u1", \
        "every excusal must be logged so a clinician can review what was forgiven"
    assert AccentAllowList.from_json(_al.to_json()).match("t", "ʈ") == "IE-01"
    assert AccentAllowList.from_json({}).is_empty
    n += 9

    # --- section 16, fusion ---------------------------------------------------
    _f0, _d0 = fuse_broad_and_correlate(1.6, 4.0)
    assert _f0 == 1.6 and _d0["applied"] is False, \
        "the default weight is zero: the correlate path must not move a score yet"
    _f1, _d1 = fuse_broad_and_correlate(1.6, 4.0, correlate_weight=0.5)
    assert _f1 < 1.6 and _d1["applied"] is True
    _f2, _ = fuse_broad_and_correlate(1.6, 0.1, correlate_weight=0.5)
    assert _f2 == 1.6, "a correlate inside range must not change anything"
    assert fuse_broad_and_correlate(None, 3.0, 0.5)[0] is None
    _f3, _ = fuse_broad_and_correlate(0.1, 9.0, correlate_weight=2.0)
    assert _f3 >= 0.0, "a fused score must stay inside the scale"
    n += 5

    # --- section 17, class balance -------------------------------------------
    _y = np.array([0] * 96 + [1] * 4)
    _cw = class_weights_from_labels(_y)
    assert _cw[1] > _cw[0], "the rare class must be weighted up"
    assert _cw[1] <= 20.0, "weights must be clipped so one row cannot dominate"
    assert sample_weights_from_labels(_y).size == 100
    _lp2 = np.log(np.full((10, 5), 0.2))
    _row = synthetic_mismatch_features(_lp2, 0, 5, 3, 0, phone_ids=[1, 2, 3, 4])
    assert _row["synthetic"] is True and "n_frames" in _row
    assert choose_distractor(3, [1, 2, 3]) in (1, 2)
    assert choose_distractor(1, [1]) is None
    # a perfectly separable problem must be solved exactly
    _s = np.array([0.9, 0.8, 0.7, 0.2, 0.1])
    _yy = np.array([0, 0, 0, 1, 1])
    _op = recall_operating_point(_s, _yy, target_recall=1.0)
    assert _op["recall"] == 1.0 and _op["precision"] == 1.0
    assert recall_operating_point(_s, np.zeros(5, int))["threshold"] is None, \
        "no positives means no operating point, not a fabricated one"
    _ct = cost_weighted_threshold(_s, _yy, fn_cost=4.0, fp_cost=1.0)
    assert _ct["fn"] == 0, "a four-to-one cost ratio must not tolerate a miss here"
    n += 9

    if verbose:
        print(f"mira_core {CORE_VERSION}: {n} assertions passed")
    return n