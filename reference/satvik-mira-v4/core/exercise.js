/* ============================================================================
   exercise.js — one exercise: the /s/ "snake sound" probe.

   Why /s/ and not /r/:
     - /s z/ are `highest` clinical priority [B2B Theory B.7], alongside /r/.
     - /ɹ/ is the 8th-worst phoneme in the measured error table (MAE 0.231),
       while /s/ sits outside the worst-12 entirely.
     - The PRD already names /s/ the "snake sound" in Mira's own character
       vocabulary, so the theme is canon rather than invented.

   Why these words:
     - Position is never collapsible [B2B G.3]: a sound correct initially and
       omitted finally is a different clinical picture. Several words per
       position.
     - `pencil`, `bicycle`, `castle`, `whistle` and `glass` contain phonemes
       in the withheld set ({u, t̪, ɫ, e}), so `not_scored` appears as a
       normal outcome rather than something contrived for the demo.

   Phase 4 (merge from the teammate's fork) expanded this from 6 words/6
   levels to 16 words/7 levels — same single-target-phone-per-word shape as
   before. The fork's word bank also added four MULTI-instance words
   (sunglasses, sausage, biscuits, socks — /s/ appearing twice at different
   positions in one word) and a matching `items[].instances[]` session
   schema; that part was deliberately NOT ported here. It threads through
   client.js's phone-matching, rewards.js's commitSession, the exercise
   loop's pass/fail logic and parent.js's item rendering all at once — a
   cross-cutting change to the pipeline the honesty contract depends on,
   and not something to rush in untested. Single-instance words only. */

export const TARGET_PHONE = 's';
export const TARGET_LABEL = 'snake sound';

export const WORDS = [
  { text: 'sun',      position: 'initial', icon: 'sun',
    phones: ['s', 'ʌ', 'n'] },
  { text: 'sock',     position: 'initial', icon: 'sock',
    phones: ['s', 'ɒ', 'k'] },
  { text: 'soap',     position: 'initial', icon: 'soap',
    phones: ['s', 'oʊ', 'p'] },
  { text: 'seven',    position: 'initial', icon: 'seven',
    phones: ['s', 'ɛ', 'v', 'ə', 'n'] },
  { text: 'spoon',    position: 'initial', icon: 'spoon',
    phones: ['s', 'p', 'u', 'n'] },             // u withheld
  { text: 'pencil',   position: 'medial',  icon: 'pencil',
    phones: ['p', 'ɛ', 'n', 's', 'ɪ', 'ɫ'] },   // ɫ withheld
  { text: 'bicycle',  position: 'medial',  icon: 'bicycle',
    phones: ['b', 'aɪ', 's', 'ɪ', 'k', 'ɫ'] },  // ɫ withheld
  { text: 'castle',   position: 'medial',  icon: 'castle',
    phones: ['k', 'æ', 's', 'ɫ'] },             // ɫ withheld
  { text: 'basket',   position: 'medial',  icon: 'basket',
    phones: ['b', 'æ', 's', 'k', 'ə', 't'] },
  { text: 'whistle',  position: 'medial',  icon: 'whistle',
    phones: ['w', 'ɪ', 's', 'ɫ'] },             // ɫ withheld
  { text: 'dinosaur', position: 'medial',  icon: 'dinosaur',
    phones: ['d', 'aɪ', 'n', 'ə', 's', 'ɔ', 'r'] },
  { text: 'bus',      position: 'final',   icon: 'bus',
    phones: ['b', 'ʌ', 's'] },
  { text: 'glass',    position: 'final',   icon: 'glass',
    phones: ['g', 'ɫ', 'æ', 's'] },             // ɫ withheld
  { text: 'house',    position: 'final',   icon: 'house',
    phones: ['h', 'aʊ', 's'] },
  { text: 'mouse',    position: 'final',   icon: 'mouse',
    phones: ['m', 'aʊ', 's'] },
  { text: 'horse',    position: 'final',   icon: 'horse',
    phones: ['h', 'ɔ', 'r', 's'] },
];

export const LEVELS = [
  { id: 1, name: 'Whispering Woods', words: [0, 1, 2] },       // initial: sun, sock, soap
  { id: 2, name: 'Pebble Creek',     words: [5, 6, 8] },       // medial: pencil, bicycle, basket
  { id: 3, name: "Snake's Hollow",   words: [11, 12, 13] },    // final: bus, glass, house
  { id: 4, name: 'Fern Gully',       words: [3, 7, 9] },       // mix: seven, castle, whistle
  { id: 5, name: 'Mossy Ridge',      words: [4, 10, 14] },     // mix: spoon, dinosaur, mouse
  { id: 6, name: 'Sunlit Summit',    words: [7, 9, 10, 14] },  // hardest medials
  { id: 7, name: 'Highland Trail',   words: [0, 5, 11, 15] },  // review, closes with horse
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
      result: null,      // the normalised contract object, from the MOST RECENT attempt only
      attempts: 0,
      // Every attempt's own marking, oldest first — a retry after a flagged
      // first try is itself informative (a consistent substitution vs. a
      // one-off dip), and used to get silently discarded when the second
      // attempt overwrote `result` wholesale. See views/kid.js's
      // handleOutcome() for what gets pushed here.
      attemptHistory: [],
      demo: false,
    })),
  };
}

export const current = s => s.items[s.index] ?? null;
export const isComplete = s => s.items.every(i => i.verdict);
