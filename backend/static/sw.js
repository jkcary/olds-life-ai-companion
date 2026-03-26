// 银龄AI伙伴 — Service Worker v1.0
const CACHE = 'yinling-v1';
const STATIC = ['/demo', '/static/icon.svg', '/static/manifest.json'];

// Install: cache static shell
self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(STATIC)).then(() => self.skipWaiting())
  );
});

// Activate: clean old caches
self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

// Fetch strategy:
// - API calls: network-first (need fresh AI data), fall back to error message
// - Static assets: cache-first
self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);

  // API: always network
  if (url.pathname.startsWith('/api/')) {
    e.respondWith(
      fetch(e.request).catch(() =>
        new Response(JSON.stringify({detail: '网络不可用，请检查连接后重试'}),
          {status: 503, headers: {'Content-Type': 'application/json'}})
      )
    );
    return;
  }

  // Static / demo page: cache-first, refresh in background
  e.respondWith(
    caches.match(e.request).then(cached => {
      const fresh = fetch(e.request).then(res => {
        if (res.ok) caches.open(CACHE).then(c => c.put(e.request, res.clone()));
        return res;
      }).catch(() => cached);
      return cached || fresh;
    })
  );
});

// Push notifications (reserved for medication reminders)
self.addEventListener('push', e => {
  const data = e.data?.json() || {};
  e.waitUntil(
    self.registration.showNotification(data.title || '银龄AI伙伴提醒', {
      body: data.body || '您有新的健康提醒',
      icon: '/static/icon.svg',
      badge: '/static/icon.svg',
      vibrate: [200, 100, 200],
      tag: data.tag || 'reminder',
      requireInteraction: data.requireInteraction || false,
    })
  );
});

self.addEventListener('notificationclick', e => {
  e.notification.close();
  e.waitUntil(clients.openWindow('/demo'));
});
