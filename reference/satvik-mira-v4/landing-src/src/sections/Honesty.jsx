import { motion } from 'motion/react';
import { IconShield } from '../components/icons.jsx';

const STATS = [
  { n: '10ms', l: 'frame resolution' },
  { n: 'On-device', l: 'audio never leaves the phone' },
  { n: 'Uncalibrated', l: 'confidence is a ranking, stated as one' },
];

export default function Honesty() {
  return (
    <section className="bg-bone-d/40 py-16">
      <div className="mx-auto max-w-3xl px-6 text-center">
        <motion.div
          initial={{ opacity: 0, scale: 0.7 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          transition={{ type: 'spring', bounce: 0.5 }}
          className="mx-auto mb-5 grid size-16 place-items-center rounded-full bg-paper shadow-[0_5px_0_rgba(49,51,55,.14),0_0_0_5px_rgba(255,255,255,.9)]"
        >
          <IconShield className="size-8 text-mark-correct" />
        </motion.div>
        <h2 className="mb-4 font-kid text-3xl text-ink">What Mira can — and can&apos;t — tell you</h2>
        <p className="mx-auto max-w-xl font-ui text-[15px] leading-relaxed text-ink-soft">
          Mira listens to each practice word and marks the sound. It&apos;s a rough guide, not
          a verdict: it misses a real share of errors and sometimes flags a sound that was
          perfectly fine. It says <b className="text-ink">not scored</b> rather than guessing
          on sounds it measures poorly. A clear result is not proof a sound was right, and a
          flag is not proof it was wrong — Mira is a practice aid, not an assessment, and it
          never diagnoses, rates severity, or replaces a speech-language pathologist.
        </p>

        <div className="mx-auto mt-9 grid max-w-lg grid-cols-3 gap-3">
          {STATS.map((s) => (
            <div key={s.l} className="rounded-2xl bg-paper px-3 py-4 shadow-[0_3px_0_rgba(49,51,55,.1),0_0_0_3px_rgba(255,255,255,.85)]">
              <div className="font-kid text-lg text-ink">{s.n}</div>
              <div className="mt-1 font-ui text-[11px] font-bold uppercase tracking-wide text-ink-soft">{s.l}</div>
            </div>
          ))}
        </div>

        <p className="mx-auto mt-8 max-w-xl font-ui text-sm text-ink-faint">
          Parents see progress by word position, not a score that hides the gaps — and can open
          the sound-by-sound detail behind it any time, with an override that never erases
          Mira&apos;s original marking.
        </p>
      </div>
    </section>
  );
}
