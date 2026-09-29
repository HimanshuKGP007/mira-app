import { motion } from 'motion/react';
import Mira from '../components/Mira.jsx';

export default function CTA({ onStart }) {
  return (
    <section className="relative overflow-hidden py-16">
      <div
        className="pointer-events-none absolute inset-0 z-0"
        style={{
          background: `
            radial-gradient(600px 460px at 90% 10%, rgba(1,173,255,.35), transparent 60%),
            radial-gradient(560px 480px at 10% 100%, rgba(198,105,255,.32), transparent 58%),
            linear-gradient(160deg, var(--sun-soft) 0%, var(--sky-soft) 100%)`,
        }}
      />
      <div className="relative z-10 mx-auto flex max-w-3xl flex-col items-center gap-4 px-6 text-center">
        <motion.div initial={{ y: 0 }} animate={{ y: [-6, 0, -6] }} transition={{ duration: 3.2, repeat: Infinity, ease: 'easeInOut' }}>
          <Mira size={110} />
        </motion.div>
        <h2 className="font-kid text-3xl text-ink">Ready to try the trail?</h2>
        <p className="max-w-md font-ui text-ink-soft">
          Free to start. No credit card, no app store — Mira installs straight from the browser.
        </p>
        <button
          onClick={onStart}
          className="mt-1 rounded-full bg-sun px-10 py-4 font-kid text-xl text-ink shadow-[0_6px_0_var(--sun-d),0_0_0_5px_rgba(255,255,255,.9)] transition-transform active:translate-y-1"
        >
          Start practising — it&apos;s free
        </button>
      </div>
    </section>
  );
}
