/* ============================================================================
   icons.js — all artwork, inline SVG, one flat palette. No emoji in the
   product surface (the app icon is the only exception).

   Object icons (word cards, theme, rewards) are built in layers —
   <g class="i-body">, optional <g class="i-accent">, <g class="i-shine">
   (a soft specular highlight, matching the reference art's glossy-object
   look) — so Phase 2's app.css keyframes can bob/drift each layer
   independently instead of the icon moving as one rigid unit. icon()
   stamps a per-instance --phase custom property so a row of icons never
   pulses in lockstep; the CSS keyframes that actually consume --phase are
   added in Phase 2 alongside the rest of the reskin.

   The ten small UI glyphs (chart/clipboard/target/shield/bulb/home/gear/
   lock/check/mic) stay simple, unlayered, unanimated line icons on
   purpose — they sit inline in parent-view headings at 15-19px, a
   register where a bobbing gear icon next to "Scored sheet" would read as
   broken, not alive.
   ========================================================================== */

export const ICONS = {
  /* ======================= object icons (layered) ======================= */

  /* --- exercise words --- */
  sun: `<svg viewBox="0 0 100 100">
    <g class="i-accent" stroke="#F2AE1E" stroke-width="6" stroke-linecap="round">
      <line x1="50" y1="10" x2="50" y2="22"/><line x1="50" y1="78" x2="50" y2="90"/>
      <line x1="10" y1="50" x2="22" y2="50"/><line x1="78" y1="50" x2="90" y2="50"/>
      <line x1="22" y1="22" x2="30" y2="30"/><line x1="70" y1="70" x2="78" y2="78"/>
      <line x1="78" y1="22" x2="70" y2="30"/><line x1="30" y1="70" x2="22" y2="78"/>
    </g>
    <g class="i-body"><circle cx="50" cy="50" r="22" fill="#FFC93C"/><circle cx="50" cy="50" r="14" fill="#FFDD7A"/></g>
    <ellipse class="i-shine" cx="44" cy="43" rx="6" ry="4" fill="#fff" opacity=".55"/></svg>`,

  sock: `<svg viewBox="0 0 100 100">
    <g class="i-body">
      <path d="M36 14 h26 v40 c0 10 4 14 12 20 c10 8 8 22 -4 24 c-12 2 -22 -6 -28 -14
        c-6 -8 -6 -14 -6 -22 Z" fill="#7A6CF0"/>
      <path d="M36 14 h26 v13 h-26 z" fill="#5B4CE0"/>
    </g>
    <g class="i-accent">
      <path d="M40 60 c8 6 18 8 26 6" stroke="#5B4CE0" stroke-width="4" fill="none" stroke-linecap="round"/>
      <circle cx="46" cy="40" r="3.5" fill="#FFC2D8"/><circle cx="57" cy="46" r="3.5" fill="#FFC2D8"/>
    </g>
    <ellipse class="i-shine" cx="43" cy="24" rx="5" ry="7" fill="#fff" opacity=".4"/></svg>`,

  pencil: `<svg viewBox="0 0 100 100"><g transform="rotate(38 50 50)">
    <g class="i-body"><rect x="42" y="14" width="17" height="46" fill="#FFC93C"/></g>
    <g class="i-accent">
      <rect x="42" y="14" width="17" height="8" rx="2" fill="#FF9EC0"/>
      <rect x="42" y="22" width="17" height="4" fill="#B9C0D4"/>
      <path d="M42 60 h17 l-8.5 16 Z" fill="#F0D6AE"/>
      <path d="M46.5 69 h8 l-4 7 Z" fill="#3C4666"/>
    </g>
    <line class="i-shine" x1="50.5" y1="26" x2="50.5" y2="60" stroke="#E0A81E" stroke-width="2" opacity=".7"/>
  </g></svg>`,

  bicycle: `<svg viewBox="0 0 100 100">
    <g class="i-body">
      <circle cx="26" cy="66" r="17" fill="none" stroke="#3C4666" stroke-width="5"/>
      <circle cx="74" cy="66" r="17" fill="none" stroke="#3C4666" stroke-width="5"/>
      <path d="M26 66 L44 40 L62 66 M44 40 L64 40 M62 66 L52 40" stroke="#35C6C0" stroke-width="5"
        fill="none" stroke-linecap="round" stroke-linejoin="round"/>
    </g>
    <g class="i-accent">
      <path d="M40 36 h10" stroke="#F0616A" stroke-width="5" stroke-linecap="round"/>
      <path d="M62 34 h9" stroke="#F0616A" stroke-width="5" stroke-linecap="round"/>
      <circle cx="26" cy="66" r="3" fill="#3C4666"/><circle cx="74" cy="66" r="3" fill="#3C4666"/>
    </g>
    <path class="i-shine" d="M16 60 A17 17 0 0 1 26 49" stroke="#fff" stroke-width="3" fill="none"
      stroke-linecap="round" opacity=".5"/></svg>`,

  bus: `<svg viewBox="0 0 100 100">
    <g class="i-body">
      <rect x="12" y="26" width="76" height="46" rx="9" fill="#F5A93B"/>
      <rect x="12" y="26" width="76" height="15" rx="9" fill="#E08D1E"/>
    </g>
    <g class="i-accent">
      <rect x="19" y="44" width="20" height="15" rx="3" fill="#CFE9FF"/>
      <rect x="42" y="44" width="16" height="15" rx="3" fill="#CFE9FF"/>
      <rect x="61" y="44" width="20" height="15" rx="3" fill="#CFE9FF"/>
      <circle cx="30" cy="76" r="8" fill="#3C4666"/><circle cx="70" cy="76" r="8" fill="#3C4666"/>
      <circle cx="30" cy="76" r="3" fill="#9AA3B8"/><circle cx="70" cy="76" r="3" fill="#9AA3B8"/>
    </g>
    <ellipse class="i-shine" cx="24" cy="32" rx="8" ry="3" fill="#fff" opacity=".45"/></svg>`,

  glass: `<svg viewBox="0 0 100 100">
    <g class="i-body">
      <path d="M32 20 h36 l-4 56 a6 6 0 0 1 -6 5 h-16 a6 6 0 0 1 -6 -5 Z" fill="#DCEEF7" stroke="#B6D8E8" stroke-width="2.5"/>
    </g>
    <g class="i-accent">
      <path d="M35 44 h30 l-2.6 32 a6 6 0 0 1 -6 5 h-13 a6 6 0 0 1 -6 -5 Z" fill="#6FC3E8"/>
      <ellipse cx="50" cy="44" rx="15" ry="3.6" fill="#9BDBF3"/>
    </g>
    <path class="i-shine" d="M40 52 v18" stroke="#fff" stroke-width="3" stroke-linecap="round" opacity=".65"/></svg>`,

  soap: `<svg viewBox="0 0 100 100">
    <g class="i-body"><rect x="24" y="34" width="52" height="34" rx="16" fill="#FF9EC0"/></g>
    <g class="i-accent">
      <circle cx="70" cy="24" r="5" fill="#CFEFFF"/><circle cx="80" cy="34" r="3.4" fill="#CFEFFF"/>
      <path d="M32 50 q18 10 36 0" stroke="#E0729E" stroke-width="3" fill="none" stroke-linecap="round"/>
    </g>
    <ellipse class="i-shine" cx="36" cy="42" rx="7" ry="4" fill="#fff" opacity=".55"/></svg>`,

  seven: `<svg viewBox="0 0 100 100">
    <g class="i-body"><path d="M28 22 h44 v12 L48 78 h-15 L54 34 H28 Z" fill="#7A6CF0"/></g>
    <g class="i-accent"><rect x="28" y="22" width="44" height="12" fill="#5B4CE0"/></g>
    <ellipse class="i-shine" cx="36" cy="27" rx="5" ry="2.4" fill="#fff" opacity=".5"/></svg>`,

  spoon: `<svg viewBox="0 0 100 100">
    <g class="i-body">
      <ellipse cx="50" cy="28" rx="17" ry="20" fill="#DCEEF7" stroke="#B6D8E8" stroke-width="2.5"/>
      <path d="M46 46 q-4 24 -6 40 q-1 8 6 8 q7 0 6 -8 q-2 -16 -6 -40 Z" fill="#DCEEF7" stroke="#B6D8E8" stroke-width="2.5"/>
    </g>
    <ellipse class="i-accent" cx="50" cy="28" rx="10" ry="13" fill="#EFF8FC"/>
    <ellipse class="i-shine" cx="45" cy="21" rx="3.4" ry="5" fill="#fff" opacity=".6"/></svg>`,

  castle: `<svg viewBox="0 0 100 100">
    <g class="i-body">
      <rect x="18" y="46" width="64" height="34" fill="#B9C0D4"/>
      <rect x="18" y="36" width="12" height="12" fill="#B9C0D4"/><rect x="44" y="36" width="12" height="12" fill="#B9C0D4"/>
      <rect x="70" y="36" width="12" height="12" fill="#B9C0D4"/>
      <path d="M46 80 v-18 a4 4 0 0 1 8 0 v18 Z" fill="#7A6CF0"/>
    </g>
    <g class="i-accent">
      <rect x="36" y="14" width="4" height="14" fill="#3C4666"/><path d="M40 14 l14 5 l-14 5 Z" fill="#F0616A"/>
      <rect x="30" y="58" width="10" height="10" fill="#8C93AD"/><rect x="60" y="58" width="10" height="10" fill="#8C93AD"/>
    </g>
    <rect class="i-shine" x="20" y="48" width="6" height="30" fill="#fff" opacity=".3"/></svg>`,

  basket: `<svg viewBox="0 0 100 100">
    <g class="i-body"><path d="M22 46 h56 l-8 32 a6 6 0 0 1 -6 5 h-28 a6 6 0 0 1 -6 -5 Z" fill="#E0A81E"/></g>
    <g class="i-accent">
      <path d="M28 46 q22 14 44 0" stroke="#B9860F" stroke-width="3" fill="none"/>
      <path d="M22 46 q28 14 56 0" stroke="#B9860F" stroke-width="3" fill="none"/>
      <path d="M32 46 C32 28 68 28 68 46" fill="none" stroke="#8A5A0F" stroke-width="5" stroke-linecap="round"/>
    </g>
    <ellipse class="i-shine" cx="36" cy="58" rx="6" ry="4" fill="#fff" opacity=".4"/></svg>`,

  whistle: `<svg viewBox="0 0 100 100">
    <g class="i-body">
      <circle cx="34" cy="58" r="20" fill="none" stroke="#F5A93B" stroke-width="7"/>
      <rect x="46" y="28" width="34" height="20" rx="8" fill="#F5A93B"/>
    </g>
    <g class="i-accent">
      <circle cx="34" cy="58" r="6" fill="#E08D1E"/>
      <rect x="70" y="32" width="8" height="12" rx="3" fill="#E08D1E"/>
    </g>
    <ellipse class="i-shine" cx="54" cy="34" rx="5" ry="2.6" fill="#fff" opacity=".5"/></svg>`,

  dinosaur: `<svg viewBox="0 0 100 100">
    <g class="i-body">
      <path d="M20 78 C18 56 30 40 48 40 C50 30 58 22 68 22 C64 30 64 36 66 40
        C76 42 82 52 80 62 L74 62 L74 78 L64 78 L64 66 C56 70 46 70 38 66 L34 78 Z" fill="#5BAF4E"/>
    </g>
    <g class="i-accent">
      <path d="M50 40 L54 30 L58 40 L62 32 L64 40" fill="#3E8C42"/>
      <circle cx="66" cy="30" r="3" fill="#3C4666"/>
    </g>
    <ellipse class="i-shine" cx="34" cy="52" rx="5" ry="3" fill="#fff" opacity=".35"/></svg>`,

  house: `<svg viewBox="0 0 100 100">
    <g class="i-body">
      <path d="M50 16 L86 46 H78 V80 H22 V46 H14 Z" fill="#F5A93B"/>
    </g>
    <g class="i-accent">
      <rect x="42" y="56" width="16" height="24" fill="#7A6CF0"/>
      <rect x="28" y="52" width="12" height="12" fill="#CFE9FF"/><rect x="60" y="52" width="12" height="12" fill="#CFE9FF"/>
    </g>
    <path class="i-shine" d="M50 16 L22 46 H30 Z" fill="#fff" opacity=".25"/></svg>`,

  mouse: `<svg viewBox="0 0 100 100">
    <g class="i-body">
      <circle cx="46" cy="30" r="12" fill="#B9C0D4"/><circle cx="70" cy="30" r="12" fill="#B9C0D4"/>
      <ellipse cx="50" cy="60" rx="30" ry="24" fill="#DCE1EE"/>
    </g>
    <g class="i-accent">
      <circle cx="40" cy="54" r="3.4" fill="#3C4666"/><circle cx="60" cy="54" r="3.4" fill="#3C4666"/>
      <circle cx="50" cy="62" r="3" fill="#FF9EC0"/>
      <path d="M78 66 q14 -4 16 8" stroke="#B9C0D4" stroke-width="4" fill="none" stroke-linecap="round"/>
    </g>
    <ellipse class="i-shine" cx="38" cy="52" rx="6" ry="4" fill="#fff" opacity=".5"/></svg>`,

  horse: `<svg viewBox="0 0 100 100">
    <g class="i-body">
      <path d="M40 82 V60 C30 58 24 48 28 36 C22 34 20 26 26 20 C34 12 48 14 54 24
        C64 24 72 32 70 44 L70 82 H58 V66 H52 V82 Z" fill="#8A5A3C"/>
    </g>
    <g class="i-accent">
      <path d="M30 20 C24 16 20 20 22 26" fill="none" stroke="#6B4327" stroke-width="4" stroke-linecap="round"/>
      <circle cx="52" cy="26" r="3" fill="#3C4666"/>
      <path d="M46 16 q6 -8 14 -4 q-4 6 -10 8 Z" fill="#6B4327"/>
    </g>
    <ellipse class="i-shine" cx="34" cy="42" rx="5" ry="7" fill="#fff" opacity=".3"/></svg>`,

  /* --- theme --- */
  snake: `<svg viewBox="0 0 100 100">
    <g class="i-body">
      <path d="M22 74 c0 -14 18 -12 18 -24 c0 -12 -16 -10 -16 -22 c0 -10 12 -14 22 -10"
        stroke="#5BAF4E" stroke-width="11" fill="none" stroke-linecap="round"/>
      <circle cx="62" cy="24" r="14" fill="#6FC85F"/>
    </g>
    <g class="i-face">
      <circle cx="57" cy="20" r="3.4" fill="#3C4666"/><circle cx="68" cy="21" r="3.4" fill="#3C4666"/>
      <path d="M74 28 l10 3 l-10 3" stroke="#F0616A" stroke-width="3" fill="none" stroke-linecap="round"/>
    </g>
    <g class="i-accent"><circle cx="30" cy="60" r="3" fill="#3E8C42"/><circle cx="34" cy="42" r="3" fill="#3E8C42"/></g>
    <ellipse class="i-shine" cx="57" cy="18" rx="4" ry="2.6" fill="#fff" opacity=".55"/></svg>`,

  /* --- trail friends (Phase 5) ---------------------------------------------
     Small decorative companions scattered along the map trail (views/kid.js's
     renderMap) — pure scenery, same as the tree scatter already there. They
     never gate progress, never speak lines of their own; Mira stays the only
     character who talks. More animal representation without touching the
     one exercise's rules. */
  fox: `<svg viewBox="0 0 100 100">
    <g class="i-body">
      <path d="M50 30 C68 30 78 46 76 62 C74 78 62 86 50 86 C38 86 26 78 24 62
        C22 46 32 30 50 30 Z" fill="#F5934B"/>
      <path d="M50 52 C58 52 64 60 62 70 C60 80 56 84 50 84 C44 84 40 80 38 70
        C36 60 42 52 50 52 Z" fill="#FFF3E4"/>
    </g>
    <g class="i-accent">
      <path d="M28 34 L18 14 L38 26 Z" fill="#F5934B"/><path d="M72 34 L82 14 L62 26 Z" fill="#F5934B"/>
      <path d="M28 34 L23 20 L36 28 Z" fill="#3C4666"/><path d="M72 34 L77 20 L64 28 Z" fill="#3C4666"/>
    </g>
    <g class="i-face">
      <circle cx="40" cy="54" r="3.4" fill="#3C4666"/><circle cx="60" cy="54" r="3.4" fill="#3C4666"/>
      <path d="M46 66 Q50 70 54 66" stroke="#3C4666" stroke-width="2.4" fill="none" stroke-linecap="round"/>
      <ellipse cx="50" cy="62" rx="3" ry="2.2" fill="#3C4666"/>
    </g>
    <ellipse class="i-shine" cx="40" cy="42" rx="5" ry="3" fill="#fff" opacity=".4"/></svg>`,

  otter: `<svg viewBox="0 0 100 100">
    <g class="i-body">
      <ellipse cx="50" cy="58" rx="30" ry="26" fill="#8A6A4E"/>
      <ellipse cx="50" cy="64" rx="18" ry="15" fill="#D9C3A8"/>
    </g>
    <g class="i-accent">
      <circle cx="28" cy="38" r="9" fill="#8A6A4E"/><circle cx="72" cy="38" r="9" fill="#8A6A4E"/>
      <circle cx="28" cy="38" r="4" fill="#5C4530"/><circle cx="72" cy="38" r="4" fill="#5C4530"/>
    </g>
    <g class="i-face">
      <circle cx="40" cy="52" r="3.2" fill="#3C4666"/><circle cx="60" cy="52" r="3.2" fill="#3C4666"/>
      <ellipse cx="50" cy="60" rx="3.4" ry="2.6" fill="#3C4666"/>
      <path d="M32 62 h-6 M32 66 h-7 M68 62 h6 M68 66 h7" stroke="#5C4530" stroke-width="1.6" stroke-linecap="round"/>
    </g>
    <ellipse class="i-shine" cx="42" cy="48" rx="4.6" ry="3" fill="#fff" opacity=".4"/></svg>`,

  bunny: `<svg viewBox="0 0 100 100">
    <g class="i-body">
      <ellipse cx="50" cy="64" rx="26" ry="22" fill="#F3EFE8"/>
      <ellipse cx="50" cy="70" rx="14" ry="11" fill="#FFC2D8"/>
    </g>
    <g class="i-accent">
      <path d="M36 40 C32 20 40 8 44 8 C48 8 46 26 44 42 Z" fill="#F3EFE8"/>
      <path d="M64 40 C68 20 60 8 56 8 C52 8 54 26 56 42 Z" fill="#F3EFE8"/>
      <path d="M40 20 C38 12 42 8 44 10 C45 18 44 28 42 36 Z" fill="#FFC2D8"/>
      <path d="M60 20 C62 12 58 8 56 10 C55 18 56 28 58 36 Z" fill="#FFC2D8"/>
    </g>
    <g class="i-face">
      <circle cx="41" cy="56" r="3.2" fill="#3C4666"/><circle cx="59" cy="56" r="3.2" fill="#3C4666"/>
      <ellipse cx="50" cy="64" rx="2.6" ry="2" fill="#FF9EC0"/>
      <path d="M44 68 Q50 72 56 68" stroke="#3C4666" stroke-width="2" fill="none" stroke-linecap="round"/>
    </g>
    <ellipse class="i-shine" cx="40" cy="56" rx="4" ry="2.6" fill="#fff" opacity=".45"/></svg>`,

  /* --- rewards --- */
  star: `<svg viewBox="0 0 24 24">
    <path class="i-body" d="M12 3 L14.6 9 L21 9.6 L16 14 L17.4 20.4 L12 17 L6.6 20.4
      L8 14 L3 9.6 L9.4 9 Z" fill="#FFC93C" stroke="#E0A81E" stroke-width="1.3" stroke-linejoin="round"/>
    <path class="i-shine" d="M11 6.5 L12 8.8" stroke="#fff" stroke-width="1.4" stroke-linecap="round" opacity=".7"/></svg>`,

  crown: `<svg viewBox="0 0 24 24">
    <path class="i-body" d="M4 18 L3 7 L9 12 L12 5 L15 12 L21 7 L20 18 Z" fill="#FFC93C"/>
    <g class="i-accent"><rect x="4" y="18" width="16" height="3" rx="1.2" fill="#E0A81E"/><circle cx="12" cy="13" r="1.6" fill="#F0616A"/></g>
    <ellipse class="i-shine" cx="8" cy="10" rx="1.6" ry="1" fill="#fff" opacity=".6"/></svg>`,

  paw: `<svg viewBox="0 0 40 40">
    <g class="i-body"><ellipse cx="20" cy="26" rx="9" ry="7.5" fill="#5BAF4E"/></g>
    <g class="i-accent"><circle cx="11" cy="16" r="3.4" fill="#5BAF4E"/><circle cx="20" cy="12.5" r="3.6" fill="#5BAF4E"/>
      <circle cx="29" cy="16" r="3.4" fill="#5BAF4E"/></g>
    <ellipse class="i-shine" cx="17" cy="23" rx="2.4" ry="1.6" fill="#fff" opacity=".4"/></svg>`,

  medal: `<svg viewBox="0 0 40 40">
    <g class="i-accent"><path d="M14 6 L18 18 L14 18 Z" fill="#7A6CF0"/><path d="M26 6 L22 18 L26 18 Z" fill="#5B4CE0"/></g>
    <g class="i-body"><circle cx="20" cy="26" r="10" fill="#FFC93C" stroke="#E0A81E" stroke-width="2"/></g>
    <path class="i-face" d="M20 21 L21.6 24.4 L25 24.7 L22.4 27 L23 30.4 L20 28.6 L17 30.4 L17.6 27 L15 24.7 L18.4 24.4 Z" fill="#fff"/>
    <ellipse class="i-shine" cx="15" cy="21" rx="2" ry="1.4" fill="#fff" opacity=".5"/></svg>`,

  flame: `<svg viewBox="0 0 40 40">
    <path class="i-body" d="M20 6 C26 14 30 16 30 24 A10 10 0 0 1 10 24 C10 19 13 18 14 14
      C17 18 16 12 20 6 Z" fill="#F5A93B"/>
    <path class="i-accent" d="M20 18 C23 22 24 23 24 26 A4 4 0 0 1 16 26 C16 23 18 22 20 18 Z" fill="#FFC93C"/>
    <ellipse class="i-shine" cx="16" cy="16" rx="2.2" ry="3" fill="#fff" opacity=".4"/></svg>`,

  trophy: `<svg viewBox="0 0 40 40">
    <path class="i-body" d="M12 8 h16 v6 a8 8 0 0 1 -16 0 z" fill="#FFC93C"/>
    <path class="i-accent" d="M12 9 h-4 a4 4 0 0 0 4 5 M28 9 h4 a4 4 0 0 1 -4 5" fill="none" stroke="#E0A81E" stroke-width="2"/>
    <g class="i-accent"><rect x="17" y="22" width="6" height="6" fill="#E0A81E"/><rect x="13" y="28" width="14" height="4" rx="1.5" fill="#E0A81E"/></g>
    <ellipse class="i-shine" cx="16" cy="11" rx="2.4" ry="1.6" fill="#fff" opacity=".5"/></svg>`,

  gift: `<svg viewBox="0 0 40 40">
    <g class="i-body"><rect x="8" y="16" width="24" height="16" rx="2" fill="#7A6CF0"/></g>
    <g class="i-accent">
      <rect x="8" y="16" width="24" height="5" fill="#5B4CE0"/><rect x="18" y="16" width="4" height="16" fill="#FFC93C"/>
      <path d="M20 16 C16 10 10 12 14 16 M20 16 C24 10 30 12 26 16" fill="none" stroke="#FFC93C" stroke-width="2.4"/>
    </g>
    <ellipse class="i-shine" cx="12" cy="24" rx="2.2" ry="3" fill="#fff" opacity=".35"/></svg>`,

  /* ===================== UI glyphs (simple, unanimated) ================== */
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

// Icons that get the idle-motion treatment (i-body/i-accent/i-shine bob and
// drift independently, per Phase 2's app.css keyframes). The ten UI glyphs
// above are deliberately excluded — see the file header.
const _ANIMATED = new Set([
  'sun', 'sock', 'soap', 'seven', 'spoon', 'pencil', 'bicycle', 'castle',
  'basket', 'whistle', 'dinosaur', 'bus', 'glass', 'house', 'mouse', 'horse',
  'snake', 'fox', 'otter', 'bunny', 'star', 'crown', 'paw', 'medal', 'flame', 'trophy', 'gift',
]);

const _parser = typeof DOMParser !== 'undefined' ? new DOMParser() : null;
const _serializer = typeof XMLSerializer !== 'undefined' ? new XMLSerializer() : null;

/**
 * icon(key, size, opts?) → an SVG markup string, safe to drop straight into
 * an innerHTML template (every call site in the app does exactly that, so
 * this always returns a string, never a DOM node).
 *
 * opts:
 *   animate  default true for the object icons above, false for UI glyphs.
 *            When true, stamps a per-instance --phase CSS custom property
 *            (random unless passed explicitly) so a row of the same icon
 *            never bobs in lockstep.
 *   phase    0..1, override the randomised phase (e.g. to sync two icons).
 *   label    if given, the icon becomes role="img" aria-label="label";
 *            otherwise it's aria-hidden (decorative, which is every use
 *            today — Mira's art never carries information text alone).
 */
export function icon(k, size, opts = {}) {
  const raw = ICONS[k];
  if (!raw) return '';
  if (!_parser || !_serializer) {
    // Environments without DOMParser (shouldn't happen in a browser, but
    // fail soft rather than throw): fall back to the old string-replace.
    return size ? raw.replace('<svg ', `<svg width="${size}" height="${size}" `) : raw;
  }
  const doc = _parser.parseFromString(raw, 'image/svg+xml');
  const svg = doc.documentElement;
  if (!svg || svg.nodeName !== 'svg') return raw;

  if (size) { svg.setAttribute('width', String(size)); svg.setAttribute('height', String(size)); }
  svg.setAttribute('overflow', 'visible');   // layers may bob outside the nominal box

  // Attribute-only (no .style / .classList): a document parsed standalone
  // via DOMParser doesn't reliably expose CSSOM on its elements in every
  // engine, but setAttribute always works regardless of document type.
  const animate = opts.animate ?? _ANIMATED.has(k);
  if (animate) {
    const phase = opts.phase ?? Math.random();
    const prevStyle = svg.getAttribute('style');
    svg.setAttribute('style', (prevStyle ? prevStyle + ';' : '') + `--phase:${phase.toFixed(3)}`);
  } else {
    const prevClass = svg.getAttribute('class');
    svg.setAttribute('class', (prevClass ? prevClass + ' ' : '') + 'i-static');
  }

  if (opts.label) { svg.setAttribute('role', 'img'); svg.setAttribute('aria-label', opts.label); }
  else svg.setAttribute('aria-hidden', 'true');

  return _serializer.serializeToString(svg);
}

/* --- Mira, the elephant ---------------------------------------------------
   Retained as the child's companion. Purely presentational — she never
   carries a number, a score or a judgement. The class hooks below (.m-all,
   .m-ear-*, .m-trunk, .m-mouth, .m-lid) are the pattern the rest of the
   animal cast (Phase 5) and the object icons above now follow: separate
   named layers, one shared stylesheet driving all instances.            */
export function miraSVG(size) {
  return `<svg width="${size}" height="${size * 1.05}" viewBox="0 0 220 232" fill="none" overflow="visible" aria-hidden="true"><g class="m-all">
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
