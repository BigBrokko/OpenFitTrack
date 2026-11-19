import { defineConfig, minimal2023Preset } from '@vite-pwa/assets-generator/config'

// `npm run gen:icons` turns public/icon.svg into the PNG icons the manifest refers to.
export default defineConfig({
  preset: minimal2023Preset,
  images: ['public/icon.svg'],
})
