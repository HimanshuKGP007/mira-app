import { useEffect, useState } from 'react';

/* Ported from the old landing.js's install flow verbatim — same three
   states (already installed / native prompt available / iOS manual steps),
   same service-worker registration pointing at /app/sw.js scope /app/ so
   install criteria can be met before the user ever visits /app/. */
export default function PWAInstall() {
  const [deferredPrompt, setDeferredPrompt] = useState(null);
  const [installed, setInstalled] = useState(false);

  const isStandalone = typeof window !== 'undefined' &&
    (window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true);
  const isIOS = typeof navigator !== 'undefined' && /iP(hone|ad|od)/.test(navigator.userAgent);

  useEffect(() => {
    const onPrompt = (e) => { e.preventDefault(); setDeferredPrompt(e); };
    const onInstalled = () => { setDeferredPrompt(null); setInstalled(true); };
    window.addEventListener('beforeinstallprompt', onPrompt);
    window.addEventListener('appinstalled', onInstalled);
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/app/sw.js', { scope: '/app/' }).catch(() => {});
    }
    return () => {
      window.removeEventListener('beforeinstallprompt', onPrompt);
      window.removeEventListener('appinstalled', onInstalled);
    };
  }, []);

  async function doInstall() {
    if (!deferredPrompt) return;
    deferredPrompt.prompt();
    await deferredPrompt.userChoice;
    setDeferredPrompt(null);
  }

  const card = 'mx-auto max-w-md rounded-2xl bg-paper px-6 py-5 text-left font-ui text-sm text-ink-soft shadow-[0_3px_0_rgba(49,51,55,.1),0_0_0_3px_rgba(255,255,255,.85)]';

  if (isStandalone || installed) {
    return <div className={`${card} text-center`}>You already have Mira installed — nice.</div>;
  }
  if (deferredPrompt) {
    return (
      <button
        onClick={doInstall}
        className="rounded-full bg-sky px-8 py-3 font-kid text-lg text-white shadow-[0_5px_0_var(--sky-d)]"
      >
        ⤓ Install Mira
      </button>
    );
  }
  if (isIOS) {
    return (
      <div className={card}>
        <b className="text-ink">Add Mira to your Home Screen on iPhone / iPad:</b>
        <ol className="mt-2 list-decimal space-y-1 pl-5">
          <li>Tap the <b>Share</b> button in Safari&apos;s toolbar</li>
          <li>Scroll down and tap <b>Add to Home Screen</b></li>
          <li>Tap <b>Add</b> — Mira opens like any other app, even offline</li>
        </ol>
      </div>
    );
  }
  return (
    <div className={card}>
      Your browser will offer to install Mira automatically — look for an install icon in the
      address bar, or open this page in Chrome/Edge on Android or desktop for a one-tap prompt.
    </div>
  );
}
