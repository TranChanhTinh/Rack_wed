const CACHE_NAME = 'rackflow-pwa-v1';
const APP_SHELL = [
  '/static/manifest.webmanifest',
  '/static/css/style.css',
  '/static/js/script.js',
  '/static/js/pwa.js',
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png',
  '/static/icons/icon-512-maskable.png',
  '/static/offline.html'
];

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (event) => {
  event.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key)))).then(() => self.clients.claim()));
});

self.addEventListener('fetch', (event) => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== 'GET' || url.origin !== self.location.origin) return;

  // Never cache live rack pages, APIs, or Excel exports: they contain mutable inventory data.
  if (url.pathname === '/' || url.pathname === '/export' || ['/edit', '/rack-action', '/color-cells', '/suggest'].includes(url.pathname)) {
    if (request.mode === 'navigate') {
      event.respondWith(fetch(request).catch(() => caches.match('/static/offline.html')));
    }
    return;
  }

  if (url.pathname.startsWith('/static/')) {
    event.respondWith(caches.match(request).then((cached) => cached || fetch(request).then((response) => {
      if (response.ok) {
        const copy = response.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
      }
      return response;
    })));
  }
});
