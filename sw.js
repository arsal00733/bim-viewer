const CACHE = 'bim-viewer-v1';
const STATIC = [
  './',
  './index.html',
  './viewer.html',
  './manifest.json',
  './data/sites.json',
  './favicon.svg',
  './icons/icon-192.svg'
];

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(STATIC)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
  );
  e.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url);
  // Model files (.glb) — network first, fallback to cache
  if (url.pathname.endsWith('.glb')) {
    e.respondWith(networkFirst(e.request));
    return;
  }
  // Everything else — cache first
  e.respondWith(cacheFirst(e.request));
});

async function cacheFirst(req) {
  const hit = await caches.match(req);
  if (hit) return hit;
  try {
    const res = await fetch(req);
    if (res.ok) {
      const copy = res.clone();
      caches.open(CACHE).then(c => c.put(req, copy));
    }
    return res;
  } catch {
    return new Response('Offline', { status: 503 });
  }
}

async function networkFirst(req) {
  try {
    const res = await fetch(req);
    if (res.ok) {
      const copy = res.clone();
      caches.open(CACHE).then(c => c.put(req, copy));
    }
    return res;
  } catch {
    const hit = await caches.match(req);
    return hit || new Response('Offline', { status: 503 });
  }
}
