/* ============================================================================
   policy.js — every constant and decision rule taken from the measured backend.
   Nothing in this file is invented. Each value carries its source.

   Sources:
     Stage 2 notebook  — training, calibration, per-phoneme error table
     Stage 3 notebook  — Svarah / Indian-English generalisation
     Stage 4 notebook  — withholding policy (coded, never executed)
     B2B / B2C consolidated docs — contracts, gates, refusals
   ========================================================================== */

/* --- calibration ---------------------------------------------------------
   confidence = sigmoid(a * mira_score + b)      [calibrator.json]
   Chosen on the TRAIN split only, never on test.                          */
export const PLATT = { a: 4.2632, b: -5.8443 };
export const FLAG_THRESHOLD = 0.86;      // confidence < 0.86  ->  flag
                                         // equivalently mira_score < 1.7967

/* --- measured operating point [Stage 2] ---------------------------------- */
export const OPERATING_POINT = {
  falsePositiveRate: 0.160,   // of well-rated phones get flagged
  recallOnPoor:      0.507,   // of poorly-rated phones are caught
  testPCC:           0.376,
  testAUC:           0.843,
  nTestPhones:       15559,
};

/* --- gates [B2C §4.7 / §12, endpoint §15] --------------------------------
   The server applies these; the client mirrors them so it can explain
   a retry and pre-empt an obviously unusable take.                        */
export const GATES = {
  minSnrDb:           12.0,   // below this -> {status:"retry"}, before scoring
  minConfidence:       0.60,  // below this -> ask for a re-recording
  minAlignmentQuality: 0.70,  // below this -> ask for a re-recording
  minDurationMs:      30,     // shorter phones are dropped, never scored
};

/* --- per-phoneme mean absolute error [Stage 2 error_by_phoneme.csv] -------
   Only rows with n >= 50 were reported. Worst ~0.32, best ~0.07.         */
export const PHONEME_MAE = {
  // worst
  'u': 0.315, 't̪': 0.264, 'ɫ': 0.254, 'e': 0.251, 'aw': 0.240,
  'ʎ': 0.237, 'z': 0.232, 'ɹ': 0.231, 'ʉ': 0.231, 'ʃ': 0.210,
  'l': 0.207, 'a': 0.204,
  // best
  'ʋ': 0.123, 'cʰ': 0.110, 'bʲ': 0.098, 'b': 0.090, 'h': 0.085, 'j': 0.068,
};
export const PHONEME_N = {
  'u': 57, 't̪': 73, 'ɫ': 132, 'e': 678, 'aw': 96, 'ʎ': 126, 'z': 451,
  'ɹ': 397, 'ʉ': 109, 'ʃ': 121, 'l': 437, 'a': 2818,
  'ʋ': 492, 'cʰ': 75, 'bʲ': 83, 'b': 181, 'h': 113, 'j': 175,
};

/* --- withholding policy [Stage 4 §12] ------------------------------------
   "not_scored: this sound is not measured reliably enough to judge"

   Applying MAE > 0.25 (and n < 50) to the Stage 2 table yields {u, t̪, ɫ, e}.
   Declining the sounds the model is worst at is what makes the rest
   trustworthy — a tool that guesses on all 24 is worse than the paper form. */
export const WITHHOLD_MAE_CEILING = 0.25;
export const WITHHOLD_MIN_N = 50;
export const WITHHELD_PHONEMES = Object.keys(PHONEME_MAE).filter(
  p => PHONEME_MAE[p] > WITHHOLD_MAE_CEILING || (PHONEME_N[p] ?? 0) < WITHHOLD_MIN_N
);
export const WITHHOLD_REASON =
  'not measured reliably enough to judge';

/* --- markings [B2B §4.2] -------------------------------------------------
   Distortion is a FLAG, never a marking. There is no fifth column.       */
export const MARKINGS = ['correct', 'substituted', 'omitted', 'assimilated', 'not_scored'];

/* --- what this product may never emit [B2B §1.6 / Stage 4 must_not_output] */
export const MUST_NOT_OUTPUT = [
  'diagnosis', 'severity_label', 'prognosis', 'treatment_plan', 'goal',
];

/* --- referral scope [B2C §4.6] ------------------------------------------- */
export const OUT_OF_SCOPE = {
  fluency:  'Stammering or blocks are outside what Mira measures.',
  voice:    'Voice quality, pitch and resonance are outside what Mira measures.',
  aphasia:  'Language difficulty after a stroke or injury is outside what Mira measures.',
  apraxia:  'Motor planning difficulty is outside what Mira measures.',
};
export const REFERRAL_TEXT =
  'This needs a proper assessment by a speech-language pathologist. Mira does not assess it.';

/* --- Indian-English generalisation [Stage 3] -----------------------------
   The allow-list has nothing to excuse: the scorer does not systematically
   penalise Indian English. Kept as data for the "about" panel.           */
export const SVARAH = {
  flagRate: 0.112,          // on 240,473 phones, known-fluent speakers
  ownNoiseFloor: 0.160,     // the model's own FP rate on well-rated phones
  phonemesDepressed: 0,     // of 30 tested
  nUtterances: 6607,
};

/* --- provenance [Stage 3 manifest] --------------------------------------- */
export const EXPECTED_PROVENANCE_KEYS =
  ['model_version', 'aligner_version', 'protocol_version', 'threshold_set_version'];

/* ==========================================================================
   Helpers
   ========================================================================== */

export const sigmoid = x => 1 / (1 + Math.exp(-x));

/** confidence from a raw mira_score, using the shipped Platt calibration. */
export const confidenceFromScore = s => sigmoid(PLATT.a * s + PLATT.b);

/** phone_norm — mirrors normalize_ipa() in mira_core.
 *  Strips digits and length marks, folds a handful of vowels. */
export function normalizeIpa(p) {
  if (p == null) return null;
  let s = String(p).trim().replace(/[0-9ː:ˈˌ]/g, '');
  const fold = { 'ɪ': 'i', 'ʊ': 'u', 'ɐ': 'a', 'ɑ': 'a', 'ɒ': 'a', 'ʌ': 'a', 'ɛ': 'e', 'ə': 'a', 'ɜ': 'a' };
  s = s.split('').map(ch => fold[ch] ?? ch).join('');
  return s;
}

/** Should this phone be declined outright, on reliability grounds? */
export function isWithheld(phone) {
  const n = normalizeIpa(phone);
  return WITHHELD_PHONEMES.includes(n);
}

/** Reliability band for a phoneme — drives the "sounds light up over time" idea. */
export function reliabilityOf(phone) {
  const n = normalizeIpa(phone);
  const mae = PHONEME_MAE[n];
  if (mae == null) return { band: 'unmeasured', mae: null };
  if (mae > WITHHOLD_MAE_CEILING) return { band: 'withheld', mae };
  if (mae > 0.18) return { band: 'weak', mae };
  return { band: 'reliable', mae };
}

/* --- the marking cascade [B2B §12 marking.py] -----------------------------
   Order is fixed and load-bearing. Accent runs FIRST, deliberately: a
   regional variant must never reach the error branches at all.

   The server may already supply `marking`. When it does we respect it and
   only layer the reliability policy on top. When it does not, we derive.  */
export function deriveMarking(phone, gate = {}) {
  const flags = Array.isArray(phone.flags) ? [...phone.flags] : [];

  // 0. utterance-level gate already failed
  if (gate.failed) {
    return { marking: 'not_scored', reason: gate.reason || 'quality gate', confidence: null, flags };
  }

  // 1. accent allow-list — not an error, and not a hedge
  if (phone.accent_flag || flags.some(f => /_ok$/.test(f))) {
    return { marking: 'correct', confidence: phone.confidence ?? null, flags };
  }

  // 2. server-supplied marking wins if present and valid
  if (phone.marking && MARKINGS.includes(phone.marking)) {
    return {
      marking: phone.marking,
      substitute: phone.substitute ?? null,
      reason: phone.reason ?? null,
      confidence: phone.confidence ?? null,
      flags,
    };
  }

  // 3. per-phone gates
  const conf = phone.confidence ?? (phone.score != null ? confidenceFromScore(phone.score) : null);
  if (conf == null) {
    return { marking: 'not_scored', reason: 'no score returned', confidence: null, flags };
  }
  if (phone.duration_ms != null && phone.duration_ms < GATES.minDurationMs) {
    return { marking: 'not_scored', reason: 'too short to measure', confidence: null, flags };
  }
  if (conf < GATES.minConfidence) {
    return { marking: 'not_scored', reason: 'uncertain', confidence: conf, flags };
  }

  // 4. omission / substitution
  if (phone.duration_ms != null && phone.duration_ms < 15 && conf < 0.5) {
    return { marking: 'omitted', confidence: conf, flags };
  }
  if (phone.substitute) {
    return { marking: 'substituted', substitute: phone.substitute, confidence: conf, flags };
  }

  // 5. distortion is a flag on a correct marking, never its own marking
  if (phone.correlate_z != null && Math.abs(phone.correlate_z) > 1.5 && !flags.includes('distortion_suspected')) {
    flags.push('distortion_suspected');
  }

  return { marking: 'correct', confidence: conf, flags };
}

/* --- normalise a raw /score response into one internal shape -------------
   Accepts both documented contracts (B2C "lab report", B2B "scored sheet"). */
export function normalizeResponse(raw, { promptWord, targetPhone } = {}) {
  const gateFailed = raw?.quality_gate && raw.quality_gate.passed === false;
  const gate = gateFailed
    ? { failed: true, reason: raw.quality_gate.reason || 'recording quality' }
    : {};

  const phones = (raw?.phones ?? []).map((p, i) => {
    const target = p.target ?? p.phone ?? p.target_phone ?? null;
    const base = deriveMarking(p, gate);

    // client-side reliability policy, applied on top and traceably tagged
    let marking = base.marking, reason = base.reason ?? null, source = 'server';
    if (marking !== 'not_scored' && isWithheld(target)) {
      marking = 'not_scored';
      reason = WITHHOLD_REASON;
      source = 'client_policy';
    }

    return {
      index: i,
      target,
      targetNorm: normalizeIpa(target),
      position: p.position ?? null,
      marking,
      substitute: base.substitute ?? p.substitute ?? null,
      confidence: marking === 'not_scored' ? null : (base.confidence ?? null),
      // 'raw_posterior' from the GOP baseline vs 'calibrated' from the trained
      // ensemble. The two are NOT on the same scale and must not be compared.
      confidenceKind: p.confidence_kind ?? null,
      flags: base.flags ?? [],
      reason,
      reasonSource: source,
      reliability: reliabilityOf(target),
      isTarget: targetPhone != null && normalizeIpa(target) === normalizeIpa(targetPhone),
      // retained for the clinician view only; NEVER rendered as a number
      _rawScore: p.score ?? null,
    };
  });

  return {
    utteranceId: raw?.utterance_id ?? raw?.utteranceId ?? null,
    promptWord: raw?.prompt_word ?? promptWord ?? null,
    targetPhone: targetPhone ?? null,
    phones,
    // every /s/-family instance in the word, in phone order — a word like
    // "sausage" has two. Never collapse to one: that silently drops data
    // the scorer already measured.
    targets: phones.filter(p => p.isTarget),
    quality: {
      passed: raw?.quality_gate?.passed !== false,
      snrDb: raw?.quality_gate?.snr_db ?? raw?.snr_db ?? null,
      alignmentQuality: raw?.quality_gate?.alignment_quality ?? raw?.alignment_quality ?? null,
      reason: raw?.quality_gate?.reason ?? null,
    },
    provenance: raw?.provenance ?? null,
    summary: summarize(phones),
  };
}

/** scored vs not-scored, always side by side. */
export function summarize(phones) {
  const scored = phones.filter(p => p.marking !== 'not_scored');
  const notScored = phones.filter(p => p.marking === 'not_scored');
  const byMarking = {};
  for (const m of MARKINGS) byMarking[m] = phones.filter(p => p.marking === m).length;
  return {
    total: phones.length,
    scored: scored.length,
    notScored: notScored.length,
    byMarking,
    soundsInError: [...new Set(
      phones.filter(p => ['substituted', 'omitted', 'assimilated'].includes(p.marking))
            .map(p => p.target)
    )],
  };
}

/* --- templated feedback [B2C §12 register] --------------------------------
   Templated, never generated. Reported BY PATTERN, not sound by sound:
   "one odd /r/ is noise, five odd /r/s is a habit".                       */
export function feedbackForSession(items, targetPhone) {
  const done = items.filter(i => i.result);
  const scored = done.filter(i => i.verdict !== 'not_scored');
  const clear = scored.filter(i => i.verdict === 'correct');
  const flagged = scored.filter(i => i.verdict !== 'correct');
  const notScored = done.filter(i => i.verdict === 'not_scored');

  if (!scored.length) {
    return {
      headline: `Nothing could be scored this time.`,
      detail: `All ${done.length} recordings were set aside, usually background noise or a very quiet mic. Try somewhere quieter.`,
      practise: [],
    };
  }

  // pattern by position, not by individual sound
  const byPos = {};
  for (const i of flagged) {
    const pos = i.word.position;
    (byPos[pos] ||= []).push(i.word.text);
  }
  const worstPos = Object.entries(byPos).sort((a, b) => b[1].length - a[1].length)[0];

  let headline, detail;
  if (!flagged.length) {
    headline = `Your /${targetPhone}/ was clear in all ${scored.length} scored words.`;
    detail = `Nothing was flagged this session.`;
  } else {
    headline = `Your /${targetPhone}/ was flagged in ${flagged.length} of ${scored.length} scored words.`;
    detail = worstPos && worstPos[1].length > 1
      ? `Most often at the ${worstPos[0]} of the word: ${worstPos[1].join(', ')}.`
      : `Flagged in: ${flagged.map(i => i.word.text).join(', ')}.`;
  }

  return {
    headline,
    detail,
    notScoredNote: notScored.length
      ? `${notScored.length} ${notScored.length === 1 ? 'word was' : 'words were'} not scored; Mira declines rather than guessing.`
      : null,
    practise: flagged.map(i => i.word.text),
  };
}

/* --- developmental norms [B2C §4.5] --------------------------------------
   Returns true / false / null. NEVER collapses "unknown" to "disordered".
   /r/ is late-acquired; gliding resolves around six or seven.            */
const ACQUISITION_AGE = { // 90% criterion, years
  'p': 3, 'b': 3, 'm': 3, 'n': 3, 'w': 3, 'h': 3,
  'k': 4, 'g': 4, 'f': 4, 'j': 4, 'd': 4, 't': 4,
  'ŋ': 5, 'l': 5.9, 'ɫ': 5.9,
  's': 6.9, 'z': 6.9, 'ʃ': 6.9, 'v': 6.9,
  'ɹ': 6.9, 'ʒ': 6.9, 'ð': 6.9, 'θ': 6.9,
};
export function isAgeExpected(phone, ageYears) {
  const n = normalizeIpa(phone);
  const age = ACQUISITION_AGE[n];
  if (age == null || ageYears == null) return null;   // unknown stays unknown
  return ageYears >= age;
}

export const HONEST_PITCH =
  'It catches about half the sounds you would have marked wrong, it raises a ' +
  'false alarm on about one correct sound in six, it tells you how confident it ' +
  'is on every one, and it says not scored rather than guessing on the sounds ' +
  'it is bad at. It does not diagnose, it does not set goals, and it does not ' +
  'talk to your patient.';
