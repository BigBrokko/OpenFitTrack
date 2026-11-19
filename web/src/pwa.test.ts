import { existsSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import { manifest } from '../pwa.config'

const publicDir = resolve(import.meta.dirname, '../public')

describe('web app manifest', () => {
  it('describes an installable app', () => {
    expect(manifest.name).toBe('OpenFitTrack')
    expect(manifest.short_name).toBeTruthy()
    expect(manifest.start_url).toBe('/')
    expect(manifest.display).toBe('standalone')
    expect(manifest.lang).toBe('nl')
    expect(manifest.theme_color).toMatch(/^#[0-9a-f]{6}$/i)
    expect(manifest.background_color).toMatch(/^#[0-9a-f]{6}$/i)
  })

  it('has the icon sizes phones ask for, including a maskable one', () => {
    const icons = manifest.icons ?? []

    expect(icons.some((icon) => icon.sizes === '192x192')).toBe(true)
    expect(icons.some((icon) => icon.sizes === '512x512' && !icon.purpose)).toBe(true)
    expect(icons.some((icon) => icon.purpose === 'maskable')).toBe(true)
  })

  it('refers only to icon files that exist (run `npm run gen:icons` if one is missing)', () => {
    for (const icon of manifest.icons ?? []) {
      expect(existsSync(resolve(publicDir, icon.src)), icon.src).toBe(true)
    }
  })

  it('has the favicon and the iPhone home screen icon', () => {
    for (const file of ['favicon.ico', 'apple-touch-icon-180x180.png', 'icon.svg']) {
      expect(existsSync(resolve(publicDir, file)), file).toBe(true)
    }
  })
})
