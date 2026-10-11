// Service worker: makes the app installable and lets it open even when the
// server (your computer) is unreachable, so it can say so instead of showing a
// browser error page. Network first, so a new version always shows up at once;
// API calls are never cached.
const CACHE = "transcript-puller-v1";
const SHELL = [
  "/",
  "/css/styles.css",
  "/js/app.js",
  "/js/formats.js",
  "/manifest.json",
  "/favicon.svg",
  "/icons/icon-192.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(SHELL)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (event.request.method !== "GET" || url.origin !== self.location.origin || url.pathname.startsWith("/api/")) {
    return;
  }
  const isPage = event.request.mode === "navigate";
  // Pages are cached as "/" whatever their query string (?url=…, shared links).
  const key = isPage ? "/" : url.pathname;
  event.respondWith(
    fetch(event.request)
      .then((response) => {
        if (response.ok && (isPage || SHELL.includes(key))) {
          const copy = response.clone();
          caches.open(CACHE).then((cache) => cache.put(key, copy));
        }
        return response;
      })
      .catch(() => caches.match(key).then((cached) => cached || Response.error())),
  );
});
