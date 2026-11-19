import type { ManifestOptions } from 'vite-plugin-pwa'

/** The web app manifest: what the phone shows when you add the app to your home screen. */
export const manifest: Partial<ManifestOptions> = {
  name: 'OpenFitTrack',
  short_name: 'OpenFitTrack',
  description: 'Eten, gewicht en doelen bijhouden',
  lang: 'nl',
  start_url: '/',
  scope: '/',
  display: 'standalone',
  orientation: 'portrait',
  background_color: '#ffffff',
  theme_color: '#15803d',
  icons: [
    { src: 'pwa-64x64.png', sizes: '64x64', type: 'image/png' },
    { src: 'pwa-192x192.png', sizes: '192x192', type: 'image/png' },
    { src: 'pwa-512x512.png', sizes: '512x512', type: 'image/png' },
    {
      src: 'maskable-icon-512x512.png',
      sizes: '512x512',
      type: 'image/png',
      purpose: 'maskable',
    },
  ],
}
