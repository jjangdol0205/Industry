// ─────────────────────────────────────────────────────────────
// Alpha Research Service Worker
// 전략: JS/CSS → Network First (배포 즉시 반영)
//       이미지/폰트 → Cache First (빠른 로딩)
//       API → Network Only (항상 최신 데이터)
//
// 버전을 올리면 → 모든 기기에서 자동으로 구 캐시 삭제 + 새 버전 설치
// ─────────────────────────────────────────────────────────────
const CACHE_VERSION = 'v1003_purge';
const CACHE_NAME = 'alpha-research-cache-v1003';

self.addEventListener('install', event => {
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => Promise.all(keys.map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

// ── Fetch 전략 분기 ──────────────────────────────────────────────
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);

  // 1. API / Render 백엔드 → Network Only (캐시 절대 안 함)
  if (
    url.pathname.startsWith('/api') ||
    url.hostname.includes('onrender.com') ||
    url.hostname.includes('render.com')
  ) {
    event.respondWith(
      fetch(request).catch(() =>
        new Response(JSON.stringify({ error: 'offline' }), {
          headers: { 'Content-Type': 'application/json' },
        })
      )
    );
    return;
  }

  // 2. JS / CSS 번들 → Network First (배포 즉시 반영)
  //    네트워크 성공 시 캐시 갱신, 실패 시 캐시 fallback
  if (
    url.pathname.startsWith('/assets/') &&
    (url.pathname.endsWith('.js') || url.pathname.endsWith('.css'))
  ) {
    event.respondWith(
      fetch(request)
        .then(response => {
          if (response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then(cache => cache.put(request, clone));
          }
          return response;
        })
        .catch(() => caches.match(request))
    );
    return;
  }

  // 3. HTML (index.html) → Network First (새 배포 감지)
  if (request.mode === 'navigate' || url.pathname.endsWith('.html') || url.pathname === '/') {
    event.respondWith(
      fetch(request)
        .then(response => {
          if (response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then(cache => cache.put(request, clone));
          }
          return response;
        })
        .catch(() => caches.match('/index.html'))
    );
    return;
  }

  // 4. 이미지 / 폰트 / 기타 정적 → Cache First (빠른 로딩)
  event.respondWith(
    caches.match(request).then(cached => {
      if (cached) return cached;
      return fetch(request).then(response => {
        if (response.ok) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(request, clone));
        }
        return response;
      });
    })
  );
});
