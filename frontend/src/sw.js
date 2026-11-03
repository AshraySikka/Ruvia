/* Ruvia service worker: offline shell, cached reads, push reminders. */
import { clientsClaim } from "workbox-core";
import { ExpirationPlugin } from "workbox-expiration";
import { cleanupOutdatedCaches, createHandlerBoundToURL, precacheAndRoute } from "workbox-precaching";
import { NavigationRoute, registerRoute } from "workbox-routing";
import { CacheFirst, NetworkFirst, StaleWhileRevalidate } from "workbox-strategies";

self.skipWaiting();
clientsClaim();
cleanupOutdatedCaches();
precacheAndRoute(self.__WB_MANIFEST);
registerRoute(new NavigationRoute(createHandlerBoundToURL("/index.html")));

// Recent reads stay available offline. Exports and PDFs are never cached.
registerRoute(
  ({ url, request }) => request.method === "GET" && url.pathname.startsWith("/api/") &&
    !/report\.pdf|export|auth|push/.test(url.pathname),
  new NetworkFirst({ cacheName: "ruvia-api", networkTimeoutSeconds: 6,
    plugins: [new ExpirationPlugin({ maxEntries: 80, maxAgeSeconds: 60 * 60 * 24 * 7 })] }),
);
registerRoute(({ url }) => url.origin === "https://fonts.googleapis.com", new StaleWhileRevalidate({ cacheName: "ruvia-fonts-css" }));
registerRoute(({ url }) => url.origin === "https://fonts.gstatic.com",
  new CacheFirst({ cacheName: "ruvia-fonts", plugins: [new ExpirationPlugin({ maxEntries: 20, maxAgeSeconds: 60 * 60 * 24 * 365 })] }));

self.addEventListener("message", (event) => {
  if (event.data === "clear-api-cache") caches.delete("ruvia-api");
});

self.addEventListener("push", (event) => {
  let data = {};
  try { data = event.data ? event.data.json() : {}; } catch { data = { title: "Ruvia", body: event.data?.text() }; }
  const title = data.title || "Ruvia";
  event.waitUntil(self.registration.showNotification(title, {
    body: data.body || "",
    icon: "/icons/icon-192.png",
    badge: "/icons/icon-192.png",
    tag: data.tag || "ruvia",
    data: { url: data.url || "/" },
    actions: (data.actions || []).slice(0, 2),
  }));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  let url = event.notification.data?.url || "/";
  const action = event.action;
  if (action && url.startsWith("/followup/")) url = `${url}?answer=${action}`;
  else if (action === "yes" || action === "not_yet") url = `/cycle?confirm=${action}`;
  else if (action === "water250") url = "/?water=250";
  event.waitUntil((async () => {
    const all = await self.clients.matchAll({ type: "window", includeUncontrolled: true });
    for (const c of all) {
      if ("focus" in c) { await c.focus(); c.postMessage({ type: "navigate", url }); return; }
    }
    await self.clients.openWindow(url);
  })());
});
