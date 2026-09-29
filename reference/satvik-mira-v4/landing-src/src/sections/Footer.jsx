import Mira from '../components/Mira.jsx';
import PWAInstall from '../components/PWAInstall.jsx';

export default function Footer({ onSignIn }) {
  return (
    <>
      <section id="download" className="mx-auto max-w-3xl px-6 py-14 text-center">
        <h2 className="mb-2 font-kid text-2xl text-ink">Get it on your device</h2>
        <p className="mx-auto mb-6 max-w-sm font-ui text-sm text-ink-soft">
          Mira installs like an app — no app store, no download surprises. It works offline
          once installed.
        </p>
        <PWAInstall />
      </section>

      <footer className="border-t border-bone-d bg-paper px-6 py-8">
        <div className="mx-auto flex max-w-5xl flex-col items-center gap-3 text-center sm:flex-row sm:justify-between sm:text-left">
          <div className="flex items-center gap-2">
            <Mira size={26} />
            <span className="font-kid text-lg text-grape">Mira</span>
          </div>
          <p className="max-w-md font-ui text-xs text-ink-faint">
            Prototype. Scoring comes from a research model with known limits — not a clinical
            device.
          </p>
          <button onClick={onSignIn} className="font-ui text-sm font-extrabold text-ink-soft hover:text-grape-d">
            Sign in
          </button>
        </div>
      </footer>
    </>
  );
}
