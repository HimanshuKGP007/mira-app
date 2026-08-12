/* ============================================================================
   exercise.js — one exercise: the /s/ "snake sound" probe.

   Why /s/ and not /r/:
     - /s z/ are `highest` clinical priority [B2B Theory B.7], alongside /r/.
     - /ɹ/ is the 8th-worst phoneme in the measured error table (MAE 0.231),
       while /s/ sits outside the worst-12 entirely.
     - The PRD already names /s/ the "snake sound" in Mira's own character
       vocabulary, so the theme is canon rather than invented.

   Why these six words:
     - Position is never collapsible [B2B G.3]: a sound correct initially and
       omitted finally is a different clinical picture. Two words per position.
     - `pencil`, `bicycle` and `glass` contain phonemes in the withheld set
       ({u, t̪, ɫ, e}), so `not_scored` appears as a normal outcome rather
       than something contrived for the demo.
   ========================================================================== */

export const TARGET_PHONE = 's';
export const TARGET_LABEL = 'snake sound';

// Bump whenever WORDS or LEVELS changes shape (words added/removed/reordered,
// levels added/removed). rewards.js uses this to invalidate cached
// word-bank-index data (nextWords, levels) that would otherwise silently
// point at the wrong word after a code update — never touches real user
// data (name, stars, xp, sessions, badges).
export const CONTENT_VERSION = 2;

export const WORDS = [
  { text: 'sun',        position: 'initial', icon: 'sun',
    phones: ['s', 'ʌ', 'n'] },
  { text: 'sock',       position: 'initial', icon: 'sock',
    phones: ['s', 'ɒ', 'k'] },
  { text: 'soap',       position: 'initial', icon: 'soap',
    phones: ['s', 'oʊ', 'p'] },
  { text: 'seven',      position: 'initial', icon: 'seven',
    phones: ['s', 'ɛ', 'v', 'ə', 'n'] },
  { text: 'spoon',      position: 'initial', icon: 'spoon',
    phones: ['s', 'p', 'u', 'n'] },
  { text: 'pencil',     position: 'medial',  icon: 'pencil',
    phones: ['p', 'ɛ', 'n', 's', 'ɪ', 'ɫ'] },   // ɛ->e and ɫ are withheld
  { text: 'bicycle',    position: 'medial',  icon: 'bicycle',
    phones: ['b', 'aɪ', 's', 'ɪ', 'k', 'ɫ'] },  // ɫ withheld
  { text: 'castle',     position: 'medial',  icon: 'castle',
    phones: ['k', 'æ', 's', 'ɫ'] },             // ɫ withheld
  { text: 'basket',     position: 'medial',  icon: 'basket',
    phones: ['b', 'æ', 's', 'k', 'ə', 't'] },
  { text: 'whistle',    position: 'medial',  icon: 'whistle',
    phones: ['w', 'ɪ', 's', 'ɫ'] },             // ɫ withheld
  { text: 'dinosaur',   position: 'medial',  icon: 'dinosaur',
    phones: ['d', 'aɪ', 'n', 'ə', 's', 'ɔ', 'r'] },
  { text: 'bus',        position: 'final',   icon: 'bus',
    phones: ['b', 'ʌ', 's'] },
  { text: 'glass',      position: 'final',   icon: 'glass',
    phones: ['g', 'ɫ', 'æ', 's'] },             // ɫ withheld
  { text: 'house',      position: 'final',   icon: 'house',
    phones: ['h', 'aʊ', 's'] },
  { text: 'mouse',      position: 'final',   icon: 'mouse',
    phones: ['m', 'aʊ', 's'] },
  { text: 'horse',      position: 'final',   icon: null,
    phones: ['h', 'ɔ', 'r', 's'] },
  // multi-instance: /s/ appears twice, at different positions in the same word
  { text: 'sunglasses', position: 'initial', icon: 'sunglasses',
    phones: ['s', 'ʌ', 'n', 'g', 'l', 'æ', 's', 'ɪ', 'z'] },   // s: initial + medial
  { text: 'sausage',    position: 'initial', icon: 'sausage',
    phones: ['s', 'ɔ', 's', 'ɪ', 'dʒ'] },                      // s: initial + medial
  { text: 'biscuits',   position: 'medial',  icon: 'biscuits',
    phones: ['b', 'ɪ', 's', 'k', 'ɪ', 't', 's'] },              // s: medial + final
  { text: 'socks',      position: 'initial', icon: 'sock',
    phones: ['s', 'ɒ', 'k', 's'] },                             // s: initial + final
];

export const LEVELS = [
  { id: 1, name: 'Whispering Woods', words: [0, 1, 2] },      // initial: sun, sock, soap
  { id: 2, name: 'Pebble Creek',     words: [5, 6, 8] },      // medial: pencil, bicycle, basket
  { id: 3, name: "Snake's Hollow",   words: [11, 12, 13] },   // final: bus, glass, house
  { id: 4, name: 'Fern Gully',       words: [3, 7, 9] },      // mix: seven, castle, whistle
  { id: 5, name: 'Mossy Ridge',      words: [4, 10, 14] },    // mix: spoon, dinosaur, mouse
  { id: 6, name: 'Sunlit Summit',    words: [16, 17, 18, 19] }, // multi-instance
  { id: 7, name: 'Highland Trail',   words: [0, 5, 11, 15] }, // review, includes horse
];

export function wordsForLevel(level) {
  return level.words.map(i => WORDS[i]);
}

/** Build a level-shaped object from arbitrary word-bank indices (used for
 * the practice set Mira assembles after enough sessions to detect a
 * pattern). Falls back to nothing usable if the indices are empty/invalid -
 * callers must check the returned words.length before using it. */
export function levelFromWords(indices) {
  const valid = (indices || []).filter(i => Number.isInteger(i) && i >= 0 && i < WORDS.length);
  return {
    id: 'practice',
    name: 'Practice Trail',
    words: valid,
  };
}

/** A fresh session for one level. */
export function newSession(level) {
  return {
    levelId: level.id,
    levelName: level.name,
    targetPhone: TARGET_PHONE,
    index: 0,
    items: wordsForLevel(level).map(w => ({
      word: w,
      verdict: null,     // 'correct' | 'substituted' | 'omitted' | 'assimilated' | 'not_scored'
      result: null,      // the normalised contract object
      attempts: 0,
      confidenceHistory: [],   // lowest target-instance confidence per attempt, oldest first
      demo: false,
    })),
  };
}

export const current = s => s.items[s.index] ?? null;
export const isComplete = s => s.items.every(i => i.verdict);
