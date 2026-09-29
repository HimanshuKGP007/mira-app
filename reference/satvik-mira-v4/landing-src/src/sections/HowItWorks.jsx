import StoryCard from '../components/StoryCard.jsx';
import { IconSnake, IconMic, IconTarget, IconStar } from '../components/icons.jsx';

const iconStyle = { color: 'var(--ink)' };
const STEPS = [
  { icon: <IconSnake style={iconStyle} className="size-full" />, label: 'Pick a trail on the map', tint: 'var(--sky-soft)' },
  { icon: <IconMic style={iconStyle} className="size-full" />, label: 'Say the word out loud', tint: 'var(--grape-soft)' },
  { icon: <IconTarget style={iconStyle} className="size-full" />, label: 'A real model scores it live', tint: 'var(--clay-soft)' },
  { icon: <IconStar style={iconStyle} className="size-full" />, label: 'Stars, crowns, real progress', tint: 'var(--sun-soft)' },
];

export default function HowItWorks() {
  return (
    <section id="how" className="mx-auto max-w-5xl px-6 py-14">
      <h2 className="mb-1 font-kid text-3xl text-ink">How it works</h2>
      <p className="mb-7 max-w-md font-ui text-ink-soft">
        Four words is all it takes to see it working.
      </p>
      <div className="flex gap-4 overflow-x-auto pb-2" style={{ scrollbarWidth: 'none' }}>
        {STEPS.map((s, i) => (
          <StoryCard key={s.label} {...s} delay={i * 0.08} />
        ))}
      </div>
    </section>
  );
}
