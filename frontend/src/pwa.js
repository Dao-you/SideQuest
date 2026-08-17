let deferredInstallPrompt = null

export function registerPwa() {
  if (!import.meta.env.PROD || !('serviceWorker' in navigator)) return

  window.addEventListener('beforeinstallprompt', (event) => {
    event.preventDefault()
    deferredInstallPrompt = event
    window.dispatchEvent(new Event('sidequest:pwa-installable'))
  })

  window.addEventListener('appinstalled', () => {
    deferredInstallPrompt = null
    window.dispatchEvent(new Event('sidequest:pwa-installed'))
  })

  navigator.serviceWorker.register('/sw.js', { scope: '/', updateViaCache: 'none' })
    .catch((error) => console.error('SideQuest PWA service worker registration failed:', error))
}

export function isPwaInstallable() {
  return Boolean(deferredInstallPrompt)
}

export function isPwaStandalone() {
  return window.matchMedia?.('(display-mode: standalone)').matches
    || window.navigator.standalone === true
}

export async function promptPwaInstall() {
  if (!deferredInstallPrompt) return false

  const promptEvent = deferredInstallPrompt
  deferredInstallPrompt = null
  promptEvent.prompt()
  const { outcome } = await promptEvent.userChoice
  return outcome === 'accepted'
}
