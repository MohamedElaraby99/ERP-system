const CACHE_NAME = "erp-cache-v2";

const STATIC_RESOURCES = [
  "/",
  "/static/dashboard.css",
  "/static/style.css",
  "/static/dashboard.js",
  "/static/client-protection.js",
  "/static/favicon.svg",
  // Google Fonts and Material Icons will be cached dynamically
];

// Install event - cache static resources
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => {
        console.log("Opened cache");
        return cache.addAll(STATIC_RESOURCES);
      })
      .catch((error) => {
        console.error("Pre-caching failed:", error);
      })
  );
  // Force activation of the new service worker
  self.skipWaiting();
});

// Activate event - clean up old caches
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME) {
            console.log("Deleting old cache:", cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
  // Take control of all clients immediately
  event.waitUntil(clients.claim());
});

// Fetch event - network first, then cache
self.addEventListener("fetch", (event) => {
  // Skip cross-origin requests
  if (!event.request.url.startsWith(self.location.origin)) {
    return;
  }

  event.respondWith(
    fetch(event.request)
      .then((response) => {
        // Cache successful responses
        if (response.status === 200) {
          const responseClone = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseClone);
          });
        }
        return response;
      })
      .catch(async () => {
        // Try to get the resource from cache
        const cachedResponse = await caches.match(event.request);
        if (cachedResponse) {
          return cachedResponse;
        }

        // Log the failure for debugging
        console.log(
          "Service Worker: Network failed, trying cache",
          event.request.url
        );
        return new Response("Network error occurred", {
          status: 503,
          statusText: "Service Unavailable",
        });
      })
  );
});
