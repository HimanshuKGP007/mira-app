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

  soap: `<svg viewBox="0 0 100 100"><rect x="18" y="34" width="64" height="34" rx="17" fill="#8FE3D3"/>
    <rect x="18" y="34" width="64" height="34" rx="17" fill="none" stroke="#4FBFA8" stroke-width="2.5"/>
    <ellipse cx="38" cy="46" rx="10" ry="5" fill="#fff" opacity=".5"/></svg>`,

  spoon: `<svg viewBox="0 0 100 100"><ellipse cx="50" cy="32" rx="18" ry="22" fill="#CFD5E6"/>
    <ellipse cx="46" cy="26" rx="7" ry="10" fill="#fff" opacity=".5"/>
    <rect x="46" y="50" width="8" height="42" rx="4" fill="#CFD5E6"/></svg>`,

  house: `<svg viewBox="0 0 100 100"><path d="M50 16 L88 46 H12 Z" fill="#F0616A"/>
    <rect x="22" y="46" width="56" height="40" fill="#FFE8B8"/>
    <rect x="42" y="62" width="16" height="24" fill="#7A6CF0"/>
    <rect x="30" y="54" width="12" height="12" fill="#CFE9FF"/><rect x="58" y="54" width="12" height="12" fill="#CFE9FF"/></svg>`,

  mouse: `<svg viewBox="0 0 100 100"><circle cx="34" cy="30" r="12" fill="#B9C0D4"/><circle cx="66" cy="30" r="12" fill="#B9C0D4"/>
    <ellipse cx="50" cy="56" rx="30" ry="24" fill="#D5D9E8"/>
    <path d="M78 60 Q94 66 90 80" stroke="#D5D9E8" stroke-width="5" fill="none" stroke-linecap="round"/>
    <circle cx="40" cy="52" r="3" fill="#3C4666"/><ellipse cx="52" cy="60" rx="4" ry="3" fill="#FF9EC0"/></svg>`,

  castle: `<svg viewBox="0 0 100 100">
    <rect x="14" y="50" width="20" height="34" fill="#B9C0D4"/>
    <rect x="66" y="50" width="20" height="34" fill="#B9C0D4"/>
    <rect x="34" y="60" width="32" height="24" fill="#CFD5E6"/>
    <rect x="14" y="44" width="6" height="8" fill="#B9C0D4"/><rect x="28" y="44" width="6" height="8" fill="#B9C0D4"/>
    <rect x="66" y="44" width="6" height="8" fill="#B9C0D4"/><rect x="80" y="44" width="6" height="8" fill="#B9C0D4"/>
    <rect x="42" y="68" width="16" height="16" fill="#7A6CF0"/>
    <path d="M50 24 v18" stroke="#8A93AD" stroke-width="3"/><path d="M50 24 l12 5 l-12 5 Z" fill="#F0616A"/></svg>`,

  basket: `<svg viewBox="0 0 100 100"><path d="M24 46 h52 l-6 34 a6 6 0 0 1 -6 5 h-28 a6 6 0 0 1 -6 -5 Z" fill="#E0A81E"/>
    <path d="M28 54 h44 M25 64 h50 M27 74 h46" stroke="#B5820F" stroke-width="2.5"/>
    <path d="M36 46 a14 18 0 0 1 28 0" fill="none" stroke="#8A5A12" stroke-width="4"/></svg>`,

  whistle: `<svg viewBox="0 0 100 100"><ellipse cx="46" cy="50" rx="26" ry="18" fill="#F5A93B"/>
    <circle cx="30" cy="50" r="6" fill="#3C4666"/>
    <rect x="70" y="42" width="14" height="16" rx="7" fill="#F5A93B"/>
    <circle cx="20" cy="34" r="7" fill="none" stroke="#8A93AD" stroke-width="3"/></svg>`,

  dinosaur: `<svg viewBox="0 0 100 100"><path d="M20 78 C16 60 24 46 40 44 C40 34 48 24 58 26 C56 32 56 36 60 40
    C74 40 82 50 80 62 C88 62 92 68 90 74 L80 74 C80 80 74 84 68 82 L66 78 L34 78 C32 84 22 84 20 78 Z" fill="#5BAF4E"/>
    <circle cx="52" cy="36" r="3" fill="#3C4666"/>
    <path d="M46 30 l6 -8 M56 28 l4 -9 M64 32 l4 -8" stroke="#3E8C42" stroke-width="4" stroke-linecap="round"/>
    <rect x="30" y="78" width="6" height="10" fill="#3E8C42"/><rect x="64" y="78" width="6" height="10" fill="#3E8C42"/></svg>`,

  seven: `<svg viewBox="0 0 100 100"><path d="M22 22 H78 L44 84" fill="none" stroke="#7A6CF0" stroke-width="14"
    stroke-linecap="round" stroke-linejoin="round"/></svg>`,

  sunglasses: `<svg viewBox="0 0 100 100"><rect x="14" y="38" width="30" height="24" rx="10" fill="#3C4666"/>
    <rect x="56" y="38" width="30" height="24" rx="10" fill="#3C4666"/>
    <path d="M44 46 h12" stroke="#3C4666" stroke-width="5"/>
    <path d="M14 46 L4 42 M86 46 L96 42" stroke="#3C4666" stroke-width="4" stroke-linecap="round"/>
    <ellipse cx="24" cy="46" rx="7" ry="5" fill="#8FE3D3" opacity=".7"/><ellipse cx="66" cy="46" rx="7" ry="5" fill="#8FE3D3" opacity=".7"/></svg>`,

  sausage: `<svg viewBox="0 0 100 100"><g fill="#D2434C">
    <ellipse cx="28" cy="50" rx="16" ry="13"/><ellipse cx="52" cy="50" rx="16" ry="13"/><ellipse cx="76" cy="50" rx="14" ry="12"/></g>
    <line x1="40" y1="40" x2="40" y2="60" stroke="#8B2530" stroke-width="3"/>
    <line x1="64" y1="40" x2="64" y2="60" stroke="#8B2530" stroke-width="3"/>
    <ellipse cx="24" cy="44" rx="5" ry="3" fill="#fff" opacity=".3"/></svg>`,

  biscuits: `<svg viewBox="0 0 100 100"><rect x="16" y="40" width="40" height="40" rx="8" fill="#E0A81E" transform="rotate(-8 36 60)"/>
    <rect x="44" y="36" width="40" height="40" rx="8" fill="#F5A93B" transform="rotate(6 64 56)"/>
    <circle cx="58" cy="48" r="2.4" fill="#B5820F"/><circle cx="70" cy="56" r="2.4" fill="#B5820F"/>
    <circle cx="60" cy="64" r="2.4" fill="#B5820F"/><circle cx="72" cy="68" r="2.4" fill="#B5820F"/></svg>`,

  zoneStart: `<svg viewBox="0 0 100 100"><ellipse cx="50" cy="70" rx="38" ry="16" fill="#D9EFC9"/>
    <path d="M50 62 C40 62 34 52 34 42 C34 30 42 22 50 22 C58 22 66 30 66 42 C66 52 60 62 50 62 Z" fill="#7FCB6E"/>
    <circle cx="42" cy="40" r="3" fill="#3E8C42"/><circle cx="58" cy="40" r="3" fill="#3E8C42"/></svg>`,
  zoneMiddle: `<svg viewBox="0 0 100 100"><ellipse cx="50" cy="70" rx="38" ry="16" fill="#D9EFC9"/>
    <path d="M50 62 C36 62 28 50 28 38 C28 24 38 16 50 16 C62 16 72 24 72 38 C72 50 64 62 50 62 Z" fill="#5BAF4E"/>
    <circle cx="40" cy="36" r="3.2" fill="#fff"/><circle cx="60" cy="36" r="3.2" fill="#fff"/></svg>`,
  zoneEnd: `<svg viewBox="0 0 100 100"><ellipse cx="50" cy="70" rx="38" ry="16" fill="#D9EFC9"/>
    <path d="M50 62 C34 62 24 48 24 34 C24 18 36 8 50 8 C64 8 76 18 76 34 C76 48 66 62 50 62 Z" fill="#3E8C42"/>
    <circle cx="38" cy="32" r="3.4" fill="#FFC93C"/><circle cx="62" cy="32" r="3.4" fill="#FFC93C"/>
    <path d="M40 46 Q50 54 60 46" stroke="#FFC93C" stroke-width="3" fill="none" stroke-linecap="round"/></svg>`,

  /* --- friends: unlockable collectible animals --- */
  friendMira: `<svg viewBox="0 0 100 100"><ellipse cx="28" cy="46" rx="16" ry="20" fill="#9AA4FA"/><ellipse cx="72" cy="46" rx="16" ry="20" fill="#9AA4FA"/>
    <circle cx="50" cy="50" r="30" fill="#A9B2FF"/>
    <circle cx="40" cy="46" r="4" fill="#3B3566"/><circle cx="60" cy="46" r="4" fill="#3B3566"/>
    <path d="M46 58 Q50 68 54 58 Q56 72 50 76 Q44 72 46 58 Z" fill="#8E97F0"/></svg>`,
  friendRabbit: `<svg viewBox="0 0 100 100"><ellipse cx="38" cy="20" rx="8" ry="24" fill="#FFD5E5"/><ellipse cx="62" cy="20" rx="8" ry="24" fill="#FFD5E5"/>
    <ellipse cx="38" cy="20" rx="4" ry="18" fill="#FF9EC0"/><ellipse cx="62" cy="20" rx="4" ry="18" fill="#FF9EC0"/>
    <circle cx="50" cy="58" r="28" fill="#FFF0F5"/>
    <circle cx="41" cy="55" r="3.5" fill="#3C4666"/><circle cx="59" cy="55" r="3.5" fill="#3C4666"/>
    <ellipse cx="50" cy="65" rx="4" ry="3" fill="#FF9EC0"/></svg>`,
  friendFox: `<svg viewBox="0 0 100 100"><path d="M28 26 L40 42 L22 44 Z" fill="#F5A93B"/><path d="M72 26 L60 42 L78 44 Z" fill="#F5A93B"/>
    <circle cx="50" cy="54" r="28" fill="#F5A93B"/>
    <path d="M36 62 a14 12 0 0 0 28 0 Z" fill="#FFF3E2"/>
    <circle cx="41" cy="50" r="3.5" fill="#3C4666"/><circle cx="59" cy="50" r="3.5" fill="#3C4666"/>
    <path d="M46 64 L54 64 L50 70 Z" fill="#3C4666"/></svg>`,
  friendPanda: `<svg viewBox="0 0 100 100"><circle cx="26" cy="26" r="12" fill="#3C4666"/><circle cx="74" cy="26" r="12" fill="#3C4666"/>
    <circle cx="50" cy="54" r="30" fill="#fff" stroke="#E4E7F0" stroke-width="2"/>
    <ellipse cx="39" cy="50" rx="8" ry="10" fill="#3C4666"/><ellipse cx="61" cy="50" rx="8" ry="10" fill="#3C4666"/>
    <circle cx="39" cy="51" r="3" fill="#fff"/><circle cx="61" cy="51" r="3" fill="#fff"/>
    <ellipse cx="50" cy="64" rx="4" ry="3" fill="#3C4666"/></svg>`,
  friendBear: `<svg viewBox="0 0 100 100"><circle cx="28" cy="26" r="12" fill="#B08968"/><circle cx="72" cy="26" r="12" fill="#B08968"/>
    <circle cx="50" cy="54" r="30" fill="#C9A27A"/>
    <ellipse cx="50" cy="60" rx="12" ry="9" fill="#EAD9C0"/>
    <circle cx="40" cy="50" r="3.5" fill="#3C4666"/><circle cx="60" cy="50" r="3.5" fill="#3C4666"/>
    <ellipse cx="50" cy="58" rx="3.5" ry="2.6" fill="#3C4666"/></svg>`,
  friendLion: `<svg viewBox="0 0 100 100"><circle cx="50" cy="54" r="38" fill="#E0A81E"/>
    <circle cx="50" cy="54" r="26" fill="#FFC93C"/>
    <circle cx="40" cy="50" r="3.4" fill="#3C4666"/><circle cx="60" cy="50" r="3.4" fill="#3C4666"/>
    <ellipse cx="50" cy="60" rx="10" ry="7" fill="#FFE8A8"/>
    <ellipse cx="50" cy="62" rx="3" ry="2.2" fill="#3C4666"/></svg>`,
  friendOwl: `<svg viewBox="0 0 100 100"><path d="M22 30 Q30 14 40 28 Z" fill="#B08968"/><path d="M78 30 Q70 14 60 28 Z" fill="#B08968"/>
    <circle cx="50" cy="54" r="30" fill="#C9A27A"/>
    <circle cx="38" cy="50" r="12" fill="#fff"/><circle cx="62" cy="50" r="12" fill="#fff"/>
    <circle cx="38" cy="50" r="5" fill="#3C4666"/><circle cx="62" cy="50" r="5" fill="#3C4666"/>
    <path d="M46 62 L54 62 L50 70 Z" fill="#F5A93B"/></svg>`,
  friendPenguin: `<svg viewBox="0 0 100 100"><path d="M50 16 C28 16 20 40 22 62 C24 80 38 88 50 88 C62 88 76 80 78 62 C80 40 72 16 50 16 Z" fill="#3C4666"/>
    <path d="M50 30 C36 30 30 46 32 62 C34 76 42 82 50 82 C58 82 66 76 68 62 C70 46 64 30 50 30 Z" fill="#fff"/>
    <circle cx="42" cy="42" r="3" fill="#3C4666"/><circle cx="58" cy="42" r="3" fill="#3C4666"/>
    <path d="M46 48 L54 48 L50 54 Z" fill="#F5A93B"/></svg>`,
  friendFrog: `<svg viewBox="0 0 100 100"><circle cx="34" cy="34" r="12" fill="#5BAF4E"/><circle cx="66" cy="34" r="12" fill="#5BAF4E"/>
    <circle cx="34" cy="34" r="5" fill="#3C4666"/><circle cx="66" cy="34" r="5" fill="#3C4666"/>
    <ellipse cx="50" cy="58" rx="32" ry="26" fill="#6FC85F"/>
    <path d="M32 66 Q50 76 68 66" stroke="#3C4666" stroke-width="3" fill="none" stroke-linecap="round"/></svg>`,
  friendTurtle: `<svg viewBox="0 0 100 100"><circle cx="50" cy="52" r="26" fill="#5BAF4E"/>
    <path d="M50 30 L58 40 L50 50 L42 40 Z" fill="#3E8C42"/><path d="M32 52 L42 44 L42 60 L32 62 Z" fill="#3E8C42"/>
    <path d="M68 52 L58 44 L58 60 L68 62 Z" fill="#3E8C42"/><path d="M50 74 L42 64 L58 64 Z" fill="#3E8C42"/>
    <ellipse cx="50" cy="82" rx="12" ry="8" fill="#7FCB6E"/>
    <circle cx="45" cy="80" r="2.4" fill="#3C4666"/><circle cx="55" cy="80" r="2.4" fill="#3C4666"/></svg>`,
  friendDeer: `<svg viewBox="0 0 100 100"><path d="M32 30 Q24 14 16 18 M32 30 Q30 12 38 10" stroke="#B08968" stroke-width="4" fill="none" stroke-linecap="round"/>
    <path d="M68 30 Q76 14 84 18 M68 30 Q70 12 62 10" stroke="#B08968" stroke-width="4" fill="none" stroke-linecap="round"/>
    <circle cx="50" cy="56" r="28" fill="#D5B48C"/>
    <circle cx="40" cy="52" r="3.4" fill="#3C4666"/><circle cx="60" cy="52" r="3.4" fill="#3C4666"/>
    <ellipse cx="50" cy="64" rx="5" ry="4" fill="#fff"/><ellipse cx="50" cy="64" rx="2.6" ry="2" fill="#3C4666"/></svg>`,
  friendDolphin: `<svg viewBox="0 0 100 100"><path d="M50 20 C30 20 18 38 18 56 C18 72 32 84 50 84 C68 84 82 72 82 56 C82 38 70 20 50 20 Z" fill="#6FC3E8"/>
    <path d="M50 20 L58 6 L54 24 Z" fill="#4FA9D6"/>
    <path d="M18 56 C10 54 6 60 6 66 C10 64 16 62 20 60 Z" fill="#4FA9D6"/>
    <circle cx="60" cy="42" r="3" fill="#3C4666"/>
    <path d="M40 58 Q50 64 62 56" stroke="#3C4666" stroke-width="2.4" fill="none" stroke-linecap="round"/></svg>`,

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
  settings: `<svg viewBox="0 0 24 24">
    <line x1="4" y1="6.5" x2="20" y2="6.5" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
    <circle cx="15" cy="6.5" r="2.2" fill="currentColor"/>
    <line x1="4" y1="12" x2="20" y2="12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
    <circle cx="9" cy="12" r="2.2" fill="currentColor"/>
    <line x1="4" y1="17.5" x2="20" y2="17.5" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
    <circle cx="17" cy="17.5" r="2.2" fill="currentColor"/></svg>`,
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
