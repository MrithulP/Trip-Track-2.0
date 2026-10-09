const CACHE_NAME = "triptrack-v6"; // bump this whenever you edit index.html, style.css or script.js

const CORE  = ["./", "./index.html", "./style.css", "./script.js", "./manifest.json"];
const ICONS = ["./icon-192.png", "./icon-512.png"]; // optional: a missing icon must not break install

self.addEventListener("install", event => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache =>
      cache.addAll(CORE).then(() => Promise.allSettled(ICONS.map(icon => cache.add(icon))))
    )
  );
});

self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", event => {
  event.respondWith(
    caches.match(event.request).then(res => res || fetch(event.request))
  );
});
