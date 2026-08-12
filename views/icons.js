/* ============================================================================
   icons.js — all artwork, inline SVG, one flat palette. No emoji in the
   product surface (the app icon is the only exception).
   ========================================================================== */

export const ICONS = {
  /* --- exercise words --- */
  sun: `<svg viewBox="0 0 100 100"><g stroke="#F2AE1E" stroke-width="6" stroke-linecap="round">
    <line x1="50" y1="10" x2="50" y2="22"/><line x1="50" y1="78" x2="50" y2="90"/>
    <line x1="10" y1="50" x2="22" y2="50"/><line x1="78" y1="50" x2="90" y2="50"/>
    <line x1="22" y1="22" x2="30" y2="30"/><line x1="70" y1="70" x2="78" y2="78"/>
    <line x1="78" y1="22" x2="70" y2="30"/><line x1="30" y1="70" x2="22" y2="78"/></g>
    <circle cx="50" cy="50" r="22" fill="#FFC93C"/><circle cx="50" cy="50" r="14" fill="#FFDD7A"/></svg>`,

  sock: `<svg viewBox="0 0 100 100"><path d="M36 14 h26 v40 c0 10 4 14 12 20 c10 8 8 22 -4 24 c-12 2 -22 -6 -28 -14
    c-6 -8 -6 -14 -6 -22 Z" fill="#7A6CF0"/>
    <path d="M36 14 h26 v13 h-26 z" fill="#5B4CE0"/>
    <path d="M40 60 c8 6 18 8 26 6" stroke="#5B4CE0" stroke-width="4" fill="none" stroke-linecap="round"/>
    <circle cx="46" cy="40" r="3.5" fill="#FFC2D8"/><circle cx="57" cy="46" r="3.5" fill="#FFC2D8"/></svg>`,

  pencil: `<svg viewBox="0 0 100 100"><g transform="rotate(38 50 50)">
    <rect x="42" y="14" width="17" height="46" fill="#FFC93C"/>
    <rect x="42" y="14" width="17" height="8" rx="2" fill="#FF9EC0"/>
    <rect x="42" y="22" width="17" height="4" fill="#B9C0D4"/>
    <path d="M42 60 h17 l-8.5 16 Z" fill="#F0D6AE"/>
    <path d="M46.5 69 h8 l-4 7 Z" fill="#3C4666"/>
    <line x1="50.5" y1="26" x2="50.5" y2="60" stroke="#E0A81E" stroke-width="2"/></g></svg>`,

  bicycle: `<svg viewBox="0 0 100 100">
    <circle cx="26" cy="66" r="17" fill="none" stroke="#3C4666" stroke-width="5"/>
    <circle cx="74" cy="66" r="17" fill="none" stroke="#3C4666" stroke-width="5"/>
    <path d="M26 66 L44 40 L62 66 M44 40 L64 40 M62 66 L52 40" stroke="#35C6C0" stroke-width="5"
      fill="none" stroke-linecap="round" stroke-linejoin="round"/>
    <path d="M40 36 h10" stroke="#F0616A" stroke-width="5" stroke-linecap="round"/>
    <path d="M62 34 h9" stroke="#F0616A" stroke-width="5" stroke-linecap="round"/>
    <circle cx="26" cy="66" r="3" fill="#3C4666"/><circle cx="74" cy="66" r="3" fill="#3C4666"/></svg>`,

  bus: `<svg viewBox="0 0 100 100">
    <rect x="12" y="26" width="76" height="46" rx="9" fill="#F5A93B"/>
    <rect x="12" y="26" width="76" height="15" rx="9" fill="#E08D1E"/>
    <rect x="19" y="44" width="20" height="15" rx="3" fill="#CFE9FF"/>
    <rect x="42" y="44" width="16" height="15" rx="3" fill="#CFE9FF"/>
    <rect x="61" y="44" width="20" height="15" rx="3" fill="#CFE9FF"/>
    <circle cx="30" cy="76" r="8" fill="#3C4666"/><circle cx="70" cy="76" r="8" fill="#3C4666"/>
    <circle cx="30" cy="76" r="3" fill="#9AA3B8"/><circle cx="70" cy="76" r="3" fill="#9AA3B8"/></svg>`,

  glass: `<svg viewBox="0 0 100 100">
    <path d="M32 20 h36 l-4 56 a6 6 0 0 1 -6 5 h-16 a6 6 0 0 1 -6 -5 Z" fill="#DCEEF7" stroke="#B6D8E8" stroke-width="2.5"/>
    <path d="M35 44 h30 l-2.6 32 a6 6 0 0 1 -6 5 h-13 a6 6 0 0 1 -6 -5 Z" fill="#6FC3E8"/>
    <ellipse cx="50" cy="44" rx="15" ry="3.6" fill="#9BDBF3"/>
    <path d="M40 52 v18" stroke="#fff" stroke-width="3" stroke-linecap="round" opacity=".65"/></svg>`,

  /* --- theme --- */
  snake: `<svg viewBox="0 0 100 100">
    <path d="M22 74 c0 -14 18 -12 18 -24 c0 -12 -16 -10 -16 -22 c0 -10 12 -14 22 -10"
      stroke="#5BAF4E" stroke-width="11" fill="none" stroke-linecap="round"/>
    <circle cx="62" cy="24" r="14" fill="#6FC85F"/>
    <circle cx="57" cy="20" r="3.4" fill="#3C4666"/><circle cx="68" cy="21" r="3.4" fill="#3C4666"/>
    <path d="M74 28 l10 3 l-10 3" stroke="#F0616A" stroke-width="3" fill="none" stroke-linecap="round"/>
    <circle cx="30" cy="60" r="3" fill="#3E8C42"/><circle cx="34" cy="42" r="3" fill="#3E8C42"/></svg>`,

  /* --- rewards --- */
  star: `<svg viewBox="0 0 24 24"><path d="M12 3 L14.6 9 L21 9.6 L16 14 L17.4 20.4 L12 17 L6.6 20.4
    L8 14 L3 9.6 L9.4 9 Z" fill="#FFC93C" stroke="#E0A81E" stroke-width="1.3" stroke-linejoin="round"/></svg>`,
  crown: `<svg viewBox="0 0 24 24"><path d="M4 18 L3 7 L9 12 L12 5 L15 12 L21 7 L20 18 Z" fill="#FFC93C"/>
    <rect x="4" y="18" width="16" height="3" rx="1.2" fill="#E0A81E"/></svg>`,
  paw: `<svg viewBox="0 0 40 40"><ellipse cx="20" cy="26" rx="9" ry="7.5" fill="#5BAF4E"/>
    <circle cx="11" cy="16" r="3.4" fill="#5BAF4E"/><circle cx="20" cy="12.5" r="3.6" fill="#5BAF4E"/>
    <circle cx="29" cy="16" r="3.4" fill="#5BAF4E"/></svg>`,
  medal: `<svg viewBox="0 0 40 40"><path d="M14 6 L18 18 L14 18 Z" fill="#7A6CF0"/>
    <path d="M26 6 L22 18 L26 18 Z" fill="#5B4CE0"/>
    <circle cx="20" cy="26" r="10" fill="#FFC93C" stroke="#E0A81E" stroke-width="2"/>
    <path d="M20 21 L21.6 24.4 L25 24.7 L22.4 27 L23 30.4 L20 28.6 L17 30.4 L17.6 27 L15 24.7 L18.4 24.4 Z" fill="#fff"/></svg>`,
  flame: `<svg viewBox="0 0 40 40"><path d="M20 6 C26 14 30 16 30 24 A10 10 0 0 1 10 24 C10 19 13 18 14 14
    C17 18 16 12 20 6 Z" fill="#F5A93B"/><path d="M20 18 C23 22 24 23 24 26 A4 4 0 0 1 16 26 C16 23 18 22 20 18 Z" fill="#FFC93C"/></svg>`,
  trophy: `<svg viewBox="0 0 40 40"><path d="M12 8 h16 v6 a8 8 0 0 1 -16 0 z" fill="#FFC93C"/>
    <path d="M12 9 h-4 a4 4 0 0 0 4 5 M28 9 h4 a4 4 0 0 1 -4 5" fill="none" stroke="#E0A81E" stroke-width="2"/>
    <rect x="17" y="22" width="6" height="6" fill="#E0A81E"/><rect x="13" y="28" width="14" height="4" rx="1.5" fill="#E0A81E"/></svg>`,
  gift: `<svg viewBox="0 0 40 40"><rect x="8" y="16" width="24" height="16" rx="2" fill="#7A6CF0"/>
    <rect x="8" y="16" width="24" height="5" fill="#5B4CE0"/><rect x="18" y="16" width="4" height="16" fill="#FFC93C"/>
    <path d="M20 16 C16 10 10 12 14 16 M20 16 C24 10 30 12 26 16" fill="none" stroke="#FFC93C" stroke-width="2.4"/></svg>`,

  /* --- UI glyphs --- */
  chart: `<svg viewBox="0 0 24 24"><path d="M4 18 L10 12 L14 15 L20 7" fill="none" stroke="#43C06B"
    stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/><circle cx="20" cy="7" r="2" fill="#43C06B"/></svg>`,
  clipboard: `<svg viewBox="0 0 24 24"><rect x="5" y="4" width="14" height="17" rx="2.5" fill="none"
    stroke="#8A93AD" stroke-width="2"/><rect x="9" y="2.5" width="6" height="3.6" rx="1.2" fill="#8A93AD"/>
    <line x1="8.5" y1="11" x2="15.5" y2="11" stroke="#8A93AD" stroke-width="2" stroke-linecap="round"/>
    <line x1="8.5" y1="15" x2="13" y2="15" stroke="#8A93AD" stroke-width="2" stroke-linecap="round"/></svg>`,
  target: `<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9" fill="none" stroke="#8A93AD" stroke-width="2"/>
    <circle cx="12" cy="12" r="5" fill="none" stroke="#8A93AD" stroke-width="2"/><circle cx="12" cy="12" r="1.8" fill="#F0616A"/></svg>`,
  shield: `<svg viewBox="0 0 24 24"><path d="M12 3 L20 6 v6 c0 5 -4 8 -8 9 c-4 -1 -8 -4 -8 -9 V6 Z"
    fill="none" stroke="#8A93AD" stroke-width="2" stroke-linejoin="round"/>
    <path d="M8.6 12 L11 14.4 L15.4 10" fill="none" stroke="#43C06B" stroke-width="2.2"
    stroke-linecap="round" stroke-linejoin="round"/></svg>`,
  bulb: `<svg viewBox="0 0 24 24"><path d="M12 3 A7 7 0 0 1 16 16 L8 16 A7 7 0 0 1 12 3 Z" fill="#FFC93C"/>
    <rect x="9" y="17" width="6" height="4" rx="1.5" fill="#8A93AD"/></svg>`,
  home: `<svg viewBox="0 0 24 24"><path d="M4 11 L12 4 L20 11 V20 H4 Z" fill="none" stroke="#8A93AD"
    stroke-width="2" stroke-linejoin="round"/><rect x="10" y="14" width="4" height="6" fill="#8A93AD"/></svg>`,
  gear: `<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="3.4" fill="none" stroke="#3C4666" stroke-width="2"/>
    <path d="M12 3 v2.5 M12 18.5 V21 M21 12 h-2.5 M5.5 12 H3 M18.4 5.6 l-1.8 1.8 M7.4 16.6 l-1.8 1.8
    M18.4 18.4 l-1.8 -1.8 M7.4 7.4 L5.6 5.6" stroke="#3C4666" stroke-width="2" stroke-linecap="round"/></svg>`,
  lock: `<svg viewBox="0 0 24 24"><rect x="5" y="10" width="14" height="10" rx="2.5" fill="#8A93AD"/>
    <path d="M8 10 V7.5 a4 4 0 0 1 8 0 V10" fill="none" stroke="#8A93AD" stroke-width="2.2"/></svg>`,
  check: `<svg viewBox="0 0 24 24"><path d="M5 12.5 L10 17.5 L19 7" fill="none" stroke="#43C06B"
    stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
  mic: `<svg viewBox="0 0 24 24"><rect x="9" y="3" width="6" height="11" rx="3" fill="#fff"/>
    <path d="M5.5 11.5 a6.5 6.5 0 0 0 13 0" fill="none" stroke="#fff" stroke-width="2.2" stroke-linecap="round"/>
    <line x1="12" y1="18" x2="12" y2="21" stroke="#fff" stroke-width="2.2" stroke-linecap="round"/></svg>`,
};

export const icon = (k, size) => {
  const raw = ICONS[k];
  if (!raw) return '';
  return size ? raw.replace('<svg ', `<svg width="${size}" height="${size}" `) : raw;
};

/* --- Mira, the elephant ---------------------------------------------------
   Retained as the child's companion. Purely presentational — she never
   carries a number, a score or a judgement.                                */
export function miraSVG(size) {
  return `<svg width="${size}" height="${size * 1.05}" viewBox="0 0 220 232" fill="none"><g class="m-all">
    <ellipse cx="88" cy="210" rx="16" ry="10" fill="#8E97F0"/><ellipse cx="132" cy="210" rx="16" ry="10" fill="#8E97F0"/>
    <ellipse cx="110" cy="168" rx="54" ry="48" fill="#A9B2FF"/><ellipse cx="110" cy="180" rx="33" ry="32" fill="#D6DAFF"/>
    <g class="m-ear m-ear-l"><ellipse cx="56" cy="92" rx="30" ry="40" fill="#9AA4FA" transform="rotate(-15 56 92)"/>
      <ellipse cx="61" cy="96" rx="17" ry="25" fill="#FFC2D8" transform="rotate(-15 61 96)"/></g>
    <g class="m-ear m-ear-r"><ellipse cx="164" cy="92" rx="30" ry="40" fill="#9AA4FA" transform="rotate(15 164 92)"/>
      <ellipse cx="159" cy="96" rx="17" ry="25" fill="#FFC2D8" transform="rotate(15 159 96)"/></g>
    <circle cx="110" cy="94" r="54" fill="#A9B2FF"/>
    <path d="M104 46 Q100 26 90 22 Q98 34 99 48 Z" fill="#8E97F0"/>
    <path d="M110 44 Q110 22 102 16 Q108 30 106 46 Z" fill="#7A6CF0"/>
    <path d="M116 46 Q122 28 132 24 Q123 36 121 48 Z" fill="#8E97F0"/>
    <ellipse cx="70" cy="112" rx="12" ry="8" fill="#FF9EC0" opacity=".55"/>
    <ellipse cx="150" cy="112" rx="12" ry="8" fill="#FF9EC0" opacity=".55"/>
    <circle cx="88" cy="86" r="15" fill="#fff"/><circle cx="132" cy="86" r="15" fill="#fff"/>
    <circle cx="90" cy="88" r="7.5" fill="#3B3566"/><circle cx="130" cy="88" r="7.5" fill="#3B3566"/>
    <circle cx="93" cy="85" r="2.6" fill="#fff"/><circle cx="133" cy="85" r="2.6" fill="#fff"/>
    <rect class="m-lid" x="73" y="70" width="30" height="30" rx="15" fill="#A9B2FF"/>
    <rect class="m-lid" x="117" y="70" width="30" height="30" rx="15" fill="#A9B2FF"/>
    <path d="M96 128 Q92 138 96 144 Q100 140 100 130 Z" fill="#FFFDF3"/>
    <path d="M124 128 Q128 138 124 144 Q120 140 120 130 Z" fill="#FFFDF3"/>
    <path d="M98 124 Q110 134 122 124" stroke="#6B5FA8" stroke-width="4" stroke-linecap="round" fill="none"/>
    <ellipse class="m-mouth" cx="110" cy="128" rx="10" ry="8" fill="#6B5FA8"/>
    <g class="m-trunk"><path d="M100 100 C96 122 108 136 132 142 C143 145 150 138 148 131 C136 129 122 118 118 100 Z" fill="#A9B2FF"/>
      <circle cx="140" cy="136" r="3" fill="#8E97F0"/><circle cx="146" cy="133" r="3" fill="#8E97F0"/></g>
  </g></svg>`;
}
