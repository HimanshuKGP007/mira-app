import { motion } from 'motion/react';

/* Icon-on-a-blob-arch — the reference's "Story Categories" pattern: a
   round icon badge overlaps the top of a colour-domed arch, the label
   sits in the dome's lower half. Same shape as /app/'s .cat-tile. */
export default function CategoryTile({ icon, label, color, delay = 0 }) {
  return (
    <motion.div
      className="flex w-24 flex-none flex-col items-center"
      initial={{ opacity: 0, scale: 0.6 }}
      whileInView={{ opacity: 1, scale: 1 }}
      viewport={{ once: true, margin: '-40px' }}
      transition={{ type: 'spring', bounce: 0.5, duration: 0.5, delay }}
    >
      <div className="relative z-10 -mb-5 grid size-16 place-items-center rounded-full bg-paper shadow-[0_5px_0_rgba(49,51,55,.14),0_0_0_5px_rgba(255,255,255,.9)]">
        <div className="size-8" style={{ color }}>{icon}</div>
      </div>
      <div
        className="w-full pt-7 pb-3 text-center shadow-[0_3px_0_rgba(49,51,55,.16),0_0_0_3px_rgba(255,255,255,.7)]"
        style={{ background: color, borderRadius: '40% 40% 50% 50% / 22% 22% 78% 78%' }}
      >
        <span className="font-kid text-[13px] leading-tight text-white drop-shadow-[0_1px_1px_rgba(0,0,0,.2)]">{label}</span>
      </div>
    </motion.div>
  );
}
