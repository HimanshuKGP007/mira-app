import { motion } from 'motion/react';
import Mira from '../components/Mira.jsx';

export default function Hero({ onStart, onSignIn }) {
  return (
    <header className="relative overflow-hidden pb-16 pt-6">
      {/* Poppy gradient wash — same technique as /app/'s .screen.kid background:
          soft brand-colour glows over a diagonal pastel wash, not a flat tint.
          z-0 here + z-10 on the foreground below, NOT a negative z-index: a
          negative z-index on this div stacks it under App.jsx's own opaque
          bg-bone wrapper (a plain non-positioned block paints above a
          negative-z positioned descendant in the same stacking context —
          the gradient rendered but was invisible until this was fixed). */}
      <div
        className="pointer-events-none absolute inset-0 z-0"
        style={{
          background: `
            radial-gradient(700px 520px at 8% -6%, rgba(255,255,255,.6), transparent 60%),
            radial-gradient(760px 560px at 98% 4%, rgba(198,105,255,.5), transparent 62%),
            radial-gradient(720px 600px at 50% 108%, rgba(255,128,56,.38), transparent 58%),
            linear-gradient(165deg, var(--sky-soft) 0%, var(--sun-soft) 48%, var(--grape-soft) 100%)`,
        }}
      />

      <nav className="relative z-10 mx-auto flex max-w-5xl items-center justify-between px-6 py-3">
        <div className="flex items-center gap-2">
          <Mira size={38} />
          <span className="font-kid text-2xl text-grape drop-shadow-[2px_2px_0_rgba(49,51,55,.14)]">Mira</span>
        </div>
        <button onClick={onSignIn} className="font-ui text-sm font-extrabold text-ink-soft hover:text-grape-d">
          Sign in
        </button>
      </nav>

      <div className="relative z-10 mx-auto flex max-w-5xl flex-col items-center gap-5 px-6 pt-10 text-center">
        <motion.div
          initial={{ opacity: 0, scale: 0.7, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          transition={{ type: 'spring', bounce: 0.5, duration: 0.7 }}
        >
          <Mira size={190} />
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15, duration: 0.5 }}
          className="max-w-xl font-kid text-4xl leading-tight text-ink sm:text-5xl"
        >
          Speech practice that tells the <span className="text-grape">honest</span> truth
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25, duration: 0.5 }}
          className="max-w-md font-ui text-lg text-ink-soft"
        >
          Mira turns speech-sound practice into a game a kid actually wants to play —
          scored live by a real on-device model, never a guess dressed up as a score.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.35, duration: 0.5 }}
          className="mt-2 flex flex-col items-center gap-3 sm:flex-row"
        >
          <button
            onClick={onStart}
            className="rounded-full bg-sun px-10 py-4 font-kid text-xl text-ink shadow-[0_6px_0_var(--sun-d),0_0_0_5px_rgba(255,255,255,.9)] transition-transform active:translate-y-1"
          >
            Start practising — it&apos;s free
          </button>
          <a
            href="#how"
            className="rounded-full bg-paper px-8 py-4 font-ui text-base font-extrabold text-ink shadow-[0_3px_0_rgba(49,51,55,.12),0_0_0_3px_rgba(255,255,255,.85)]"
          >
            See how it works
          </a>
        </motion.div>
      </div>
    </header>
  );
}
