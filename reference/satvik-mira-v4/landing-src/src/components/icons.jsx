/* Simple line icons in the same voice as /app/'s UI glyphs (views/icons.js) —
   currentColor throughout so CategoryTile/StoryCard can tint them per-card. */
const base = { fill: 'none', stroke: 'currentColor', strokeWidth: 2, strokeLinecap: 'round', strokeLinejoin: 'round' };

export const IconMic = (p) => (
  <svg viewBox="0 0 24 24" {...p}>
    <rect x="9" y="3" width="6" height="11" rx="3" fill="currentColor" />
    <path d="M5.5 11.5a6.5 6.5 0 0 0 13 0" {...base} />
    <line x1="12" y1="18" x2="12" y2="21" {...base} />
  </svg>
);
export const IconTarget = (p) => (
  <svg viewBox="0 0 24 24" {...p}>
    <circle cx="12" cy="12" r="9" {...base} />
    <circle cx="12" cy="12" r="5" {...base} />
    <circle cx="12" cy="12" r="1.8" fill="currentColor" />
  </svg>
);
export const IconChart = (p) => (
  <svg viewBox="0 0 24 24" {...p}>
    <path d="M4 18 L10 12 L14 15 L20 7" {...base} />
    <circle cx="20" cy="7" r="2" fill="currentColor" />
  </svg>
);
export const IconShield = (p) => (
  <svg viewBox="0 0 24 24" {...p}>
    <path d="M12 3 L20 6 v6 c0 5 -4 8 -8 9 c-4 -1 -8 -4 -8 -9 V6 Z" {...base} />
    <path d="M8.6 12 L11 14.4 L15.4 10" {...base} />
  </svg>
);
export const IconSnake = (p) => (
  <svg viewBox="0 0 100 100" {...p}>
    <path d="M22 74 c0 -14 18 -12 18 -24 c0 -12 -16 -10 -16 -22 c0 -10 12 -14 22 -10"
      stroke="currentColor" strokeWidth="11" fill="none" strokeLinecap="round" />
    <circle cx="62" cy="24" r="14" fill="currentColor" />
  </svg>
);
export const IconStar = (p) => (
  <svg viewBox="0 0 24 24" {...p}>
    <path d="M12 3 L14.6 9 L21 9.6 L16 14 L17.4 20.4 L12 17 L6.6 20.4 L8 14 L3 9.6 L9.4 9 Z"
      fill="currentColor" />
  </svg>
);
export const IconSpeak = (p) => (
  <svg viewBox="0 0 24 24" {...p}>
    <path d="M4 15 V9 h4 l6 -5 v16 l-6 -5 Z" fill="currentColor" />
    <path d="M17 8.5 a5 5 0 0 1 0 7" {...base} />
    <path d="M19.7 6 a9 9 0 0 1 0 12" {...base} />
  </svg>
);
export const IconHeart = (p) => (
  <svg viewBox="0 0 24 24" {...p}>
    <path d="M12 20 C6 15.5 3 12.4 3 8.6 C3 5.9 5.1 4 7.6 4 C9.2 4 10.7 4.9 12 6.6 C13.3 4.9 14.8 4 16.4 4 C18.9 4 21 5.9 21 8.6 C21 12.4 18 15.5 12 20 Z" fill="currentColor" />
  </svg>
);
export const IconCheck = (p) => (
  <svg viewBox="0 0 24 24" {...p}>
    <path d="M5 12.5 L10 17.5 L19 7" {...base} strokeWidth={3} />
  </svg>
);
