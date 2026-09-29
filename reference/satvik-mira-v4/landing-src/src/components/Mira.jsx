/* Mira, the elephant mascot — the exact art from /app/views/icons.js's
   miraSVG(), copied rather than imported: the landing bundle deliberately
   has zero runtime dependency on the app bundle (see the old landing.js's
   header), so it stays fast and keeps working even if something in /app/
   is broken. Class hooks (.m-all etc.) match the app's naming so the same
   idle-bob/blink keyframes in styles.css drive both. */
export default function Mira({ size = 200, className = '' }) {
  return (
    <svg width={size} height={size * 1.05} viewBox="0 0 220 232" fill="none"
      className={`mira-svg ${className}`} aria-hidden="true">
      <g className="m-all">
        <ellipse cx="88" cy="210" rx="16" ry="10" fill="#8E97F0" />
        <ellipse cx="132" cy="210" rx="16" ry="10" fill="#8E97F0" />
        <ellipse cx="110" cy="168" rx="54" ry="48" fill="#A9B2FF" />
        <ellipse cx="110" cy="180" rx="33" ry="32" fill="#D6DAFF" />
        <g className="m-ear m-ear-l">
          <ellipse cx="56" cy="92" rx="30" ry="40" fill="#9AA4FA" transform="rotate(-15 56 92)" />
          <ellipse cx="61" cy="96" rx="17" ry="25" fill="#FFC2D8" transform="rotate(-15 61 96)" />
        </g>
        <g className="m-ear m-ear-r">
          <ellipse cx="164" cy="92" rx="30" ry="40" fill="#9AA4FA" transform="rotate(15 164 92)" />
          <ellipse cx="159" cy="96" rx="17" ry="25" fill="#FFC2D8" transform="rotate(15 159 96)" />
        </g>
        <circle cx="110" cy="94" r="54" fill="#A9B2FF" />
        <path d="M104 46 Q100 26 90 22 Q98 34 99 48 Z" fill="#8E97F0" />
        <path d="M110 44 Q110 22 102 16 Q108 30 106 46 Z" fill="#7A6CF0" />
        <path d="M116 46 Q122 28 132 24 Q123 36 121 48 Z" fill="#8E97F0" />
        <ellipse cx="70" cy="112" rx="12" ry="8" fill="#FF9EC0" opacity=".55" />
        <ellipse cx="150" cy="112" rx="12" ry="8" fill="#FF9EC0" opacity=".55" />
        <circle cx="88" cy="86" r="15" fill="#fff" />
        <circle cx="132" cy="86" r="15" fill="#fff" />
        <circle cx="90" cy="88" r="7.5" fill="#3B3566" />
        <circle cx="130" cy="88" r="7.5" fill="#3B3566" />
        <circle cx="93" cy="85" r="2.6" fill="#fff" />
        <circle cx="133" cy="85" r="2.6" fill="#fff" />
        <rect className="m-lid" x="73" y="70" width="30" height="30" rx="15" fill="#A9B2FF" />
        <rect className="m-lid" x="117" y="70" width="30" height="30" rx="15" fill="#A9B2FF" />
        <path d="M96 128 Q92 138 96 144 Q100 140 100 130 Z" fill="#FFFDF3" />
        <path d="M124 128 Q128 138 124 144 Q120 140 120 130 Z" fill="#FFFDF3" />
        <path d="M98 124 Q110 134 122 124" stroke="#6B5FA8" strokeWidth="4" strokeLinecap="round" fill="none" />
        <ellipse className="m-mouth" cx="110" cy="128" rx="10" ry="8" fill="#6B5FA8" />
        <g className="m-trunk">
          <path d="M100 100 C96 122 108 136 132 142 C143 145 150 138 148 131 C136 129 122 118 118 100 Z" fill="#A9B2FF" />
          <circle cx="140" cy="136" r="3" fill="#8E97F0" />
          <circle cx="146" cy="133" r="3" fill="#8E97F0" />
        </g>
      </g>
    </svg>
  );
}
