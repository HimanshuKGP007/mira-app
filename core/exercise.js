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

export const WORDS = [
  { text: 'sun',     position: 'initial', icon: 'sun',
    phones: ['s', 'ʌ', 'n'] },
  { text: 'sock',    position: 'initial', icon: 'sock',
    phones: ['s', 'ɒ', 'k'] },
  { text: 'pencil',  position: 'medial',  icon: 'pencil',
    phones: ['p', 'ɛ', 'n', 's', 'ɪ', 'ɫ'] },   // ɛ->e and ɫ are withheld
  { text: 'bicycle', position: 'medial',  icon: 'bicycle',
    phones: ['b', 'aɪ', 's', 'ɪ', 'k', 'ɫ'] },  // ɫ withheld
  { text: 'bus',     position: 'final',   icon: 'bus',
    phones: ['b', 'ʌ', 's'] },
  { text: 'glass',   position: 'final',   icon: 'glass',
    phones: ['g', 'ɫ', 'æ', 's'] },             // ɫ withheld
];

export const LEVELS = [
  { id: 1, name: 'Whispering Woods', words: [0, 1] },
  { id: 2, name: 'Pebble Creek',     words: [2, 3] },
  { id: 3, name: "Snake's Hollow",   words: [4, 5] },
  { id: 4, name: 'Fern Gully',       words: [0, 2, 4] },
  { id: 5, name: 'Mossy Ridge',      words: [1, 3, 5] },
  { id: 6, name: 'Sunlit Summit',    words: [0, 1, 2, 3, 4, 5] },
];

export function wordsForLevel(level) {
  return level.words.map(i => WORDS[i]);
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
      demo: false,
    })),
  };
}

export const current = s => s.items[s.index] ?? null;
export const isComplete = s => s.items.every(i => i.verdict);
