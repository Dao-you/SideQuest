const VERSION = 'sidequest-v1'
const APP_SHELL_CACHE = `${VERSION}-shell`
const ASSET_CACHE = `${VERSION}-assets`

const APP_SHELL = [
  '/',
  '/index.html',
  '/manifest.webmanifest',
  '/icons/sidequest-icon.svg',
  '/icons/sidequest-icon-192.png',
  '/icons/sidequest-icon-512.png',
  '/brand/sidequest-mark.png',
  '/data/taipeidope_events.csv',
]

const isAssetRequest = (url) => (
  url.pathname.startsWith('/assets/')
  || /\.(?:css|js|png|jpg|jpeg|gif|svg|ico|webp|woff2?|ttf|csv)$/.test(url.pathname)
)

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(APP_SHELL_CACHE)
      .then((cache) => cache.addAll(APP_SHELL))
      .then(() => self.skipWaiting()),
  )
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(
        keys
          .filter((key) => key.startsWith('sidequest-') && ![APP_SHELL_CACHE, ASSET_CACHE].includes(key))
          .map((key) => caches.delete(key)),
      ))
      .then(() => self.clients.claim()),
  )
})

self.addEventListener('fetch', (event) => {
  const { request } = event
  const url = new URL(request.url)

  if (request.method !== 'GET' || url.origin !== self.location.origin || url.pathname.startsWith('/api/')) {
    return
  }

  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then((response) => {
          if (response.ok) {
            const copy = response.clone()
            caches.open(APP_SHELL_CACHE).then((cache) => cache.put(request, copy))
          }
          return response
        })
        .catch(async () => caches.match(request).then((cached) => cached || caches.match('/index.html'))),
    )
    return
  }

  if (isAssetRequest(url)) {
    event.respondWith(
      caches.open(ASSET_CACHE).then(async (cache) => {
        const cached = await cache.match(request)
        if (cached) return cached

        const response = await fetch(request)
        if (response.ok) await cache.put(request, response.clone())
        return response
      }),
    )
  }
})
