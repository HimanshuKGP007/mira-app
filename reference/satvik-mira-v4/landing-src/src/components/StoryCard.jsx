import { motion } from 'motion/react';

/* Rounded art tile + label OUTSIDE and below it — the reference's
   "Islamic History" row pattern. Same shape as /app/'s .story-card. */
export default function StoryCard({ icon, label, tint, delay = 0 }) {
  return (
    <motion.div
      className="flex w-32 flex-none flex-col gap-2"
      initial={{ opacity: 0, y: 14, scale: 0.9 }}
      whileInView={{ opacity: 1, y: 0, scale: 1 }}
      viewport={{ once: true, margin: '-40px' }}
      transition={{ type: 'spring', bounce: 0.45, duration: 0.45, delay }}
    >
      <div
        className="grid size-32 place-items-center rounded-3xl shadow-[0_3px_0_rgba(49,51,55,.12),0_0_0_3px_rgba(255,255,255,.85)]"
        style={{ background: tint }}
      >
        <div className="size-14">{icon}</div>
      </div>
      <div className="font-kid text-sm leading-snug text-ink">{label}</div>
    </motion.div>
  );
}
