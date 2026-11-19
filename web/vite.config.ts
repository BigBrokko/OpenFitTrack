import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'
import { defineConfig } from 'vitest/config'
import { manifest } from './pwa.config.ts'

// In development the browser talks to Vite only; Vite forwards /api to the Python API.
// That keeps everything on one origin, so the SameSite=Strict login cookie just works.
const apiProxy = { '/api': { target: 'http://127.0.0.1:8000' } }

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: 'autoUpdate',
      manifest,
      includeAssets: ['favicon.ico', 'apple-touch-icon-180x180.png', 'icon.svg'],
      workbox: {
        cleanupOutdatedCaches: true,
        navigateFallback: '/index.html',
        // Never serve the app shell for API or documentation URLs.
        navigateFallbackDenylist: [/^\/api\//, /^\/docs/, /^\/openapi\.json/],
        // Health data and login state must never be cached: always ask the server.
        runtimeCaching: [
          { urlPattern: ({ url }) => url.pathname.startsWith('/api/'), handler: 'NetworkOnly' },
        ],
      },
    }),
  ],
  server: { proxy: apiProxy },
  preview: { proxy: apiProxy },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test/setup.ts',
    css: false,
  },
})
