/* Mira service worker.
   Same-origin app files: network-first (so an edited module is never served
   stale), falling back to cache when offline. Cross-origin (fonts): cache-first.
   Non-GET is ignored entirely, so POST /score is never intercepted. */
const CACHE = 'mira-v6';
const SHELL = [
  './', './index.html', './app.css', './manifest.webmanifest',
  './icon.svg', './icon-maskable.svg',
  './core/policy.js', './core/client.js', './core/capture.js',
  './core/rewards.js', './core/exercise.js', './core/voice.js',
  './views/icons.js', './views/kid.js', './views/parent.js', './views/clinician.js',
];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE)
      .then(c => Promise.allSettled(SHELL.map(u => c.add(u))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;                 // never touch POST /score

  const sameOrigin = new URL(req.url).origin === self.location.origin;

  if (sameOrigin) {
    e.respondWith(
      fetch(req)
        .then(res => {
          const copy = res.clone();
          caches.open(CACHE).then(c => c.put(req, copy)).catch(() => {});
          return res;
        })
        .catch(() => caches.match(req).then(hit => hit || caches.match('./index.html')))
    );
    return;
  }

  e.respondWith(
    caches.match(req).then(hit =>
      hit || fetch(req).then(res => {
        const copy = res.clone();
        caches.open(CACHE).then(c => c.put(req, copy)).catch(() => {});
        return res;
      }).catch(() => hit)
    )
  );
});
