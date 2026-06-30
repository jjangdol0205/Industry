// ─────────────────────────────────────────────────────────────
// Alpha Research Service Worker
// 전략: JS/CSS → Network First (배포 즉시 반영)
//       이미지/폰트 → Cache First (빠른 로딩)
//       API → Network Only (항상 최신 데이터)
//
// 버전을 올리면 → 모든 기기에서 자동으로 구 캐시 삭제 + 새 버전 설치
// ─────────────────────────────────────────────────────────────
const CACHE_VERSION = 'v6';
const CACHE_NAME = `alpha-research-${CACHE_VERSION}`;

// ── 설치: 핵심 셸만 캐시 (JS 번들은 제외 — Network First로 관리) ──
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll([
        '/',
        '/index.html',
        '/manifest.json',
        '/favicon.svg',
        '/favicon.png',
        '/icon-192x192.png',
        '/icon-512x512.png',
        '/apple-touch-icon.png',
      ]))
      // 새 SW 즉시 활성화 (기존 탭 대기 없이)
      .then(() => self.skipWaiting())
  );
});

// ── 활성화: 구 버전 캐시 전부 삭제 ──────────────────────────────
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(
        keys
          .filter(k => k !== CACHE_NAME)
          .map(k => {
            console.log('[SW] 구 캐시 삭제:', k);
            return caches.delete(k);
          })
      ))
      // 열려있는 모든 탭에 새 SW 즉시 적용
      .then(() => self.clients.claim())
      .then(() => {
        // 모든 열린 탭에 새로고침 메시지 전송
        self.clients.matchAll({ type: 'window' }).then(clients => {
          clients.forEach(client => client.postMessage({ type: 'SW_UPDATED' }));
        });
      })
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
