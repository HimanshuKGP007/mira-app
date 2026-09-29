import CategoryTile from '../components/CategoryTile.jsx';
import { IconSpeak, IconTarget, IconChart, IconShield } from '../components/icons.jsx';

const ITEMS = [
  { icon: <IconSpeak style={{ color: 'var(--ink)' }} />, label: 'Practice', color: 'var(--sky)' },
  { icon: <IconTarget style={{ color: 'var(--ink)' }} />, label: 'Live score', color: 'var(--grape)' },
  { icon: <IconChart style={{ color: 'var(--ink)' }} />, label: 'Real progress', color: 'var(--clay)' },
  { icon: <IconShield style={{ color: 'var(--ink)' }} />, label: 'Stated limits', color: 'var(--sun)' },
];

export default function Categories() {
  return (
    <section className="mx-auto max-w-5xl px-6 py-10">
      <div className="flex gap-4 overflow-x-auto pb-2" style={{ scrollbarWidth: 'none' }}>
        {ITEMS.map((it, i) => (
          <CategoryTile key={it.label} {...it} delay={i * 0.08} />
        ))}
      </div>
    </section>
  );
}
