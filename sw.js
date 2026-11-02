/* Service worker: aplikace funguje i bez signálu v garážích. Shell se předcachuje, loga a obrázky za běhu. */
const VERSION = 'flora-v3';
const SHELL = ['./', './index.html', './style.css', './app.js', './keyboard.js', './screensaver.js', './data.js', './manifest.webmanifest', './assets/icon.svg'];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(VERSION).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (e) => {
  e.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== VERSION).map((k) => caches.delete(k)))).then(() => self.clients.claim()));
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  const sameOrigin = url.origin === self.location.origin;
  // Shell: network first (čerstvá data), fallback cache.
  if (sameOrigin && SHELL.some((p) => url.pathname.endsWith(p.replace('./', '/')) || url.pathname.endsWith('/'))) {
    e.respondWith(fetch(req).then((res) => { const copy = res.clone(); caches.open(VERSION).then((c) => c.put(req, copy)); return res; }).catch(() => caches.match(req).then((r) => r || caches.match('./index.html'))));
    return;
  }
  // Loga a obrázky: cache first.
  if (req.destination === 'image' || /\.(svg|png|jpe?g|webp)$/i.test(url.pathname)) {
    e.respondWith(caches.match(req).then((hit) => hit || fetch(req).then((res) => { if (res.ok) { const copy = res.clone(); caches.open(VERSION).then((c) => c.put(req, copy)); } return res; }).catch(() => hit)));
  }
});
