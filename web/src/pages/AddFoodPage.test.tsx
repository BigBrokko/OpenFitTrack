import { screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { FoodSearchResult } from '../api/types'
import { dayFixture } from '../test/fixtures'
import { emptyDataHandlers, fakeServer, json, renderApp } from '../test/utils'

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(new Date(2026, 10, 12, 12, 0))
})
afterEach(() => vi.useRealTimers())

const banana = { id: 7, name: 'Banaan', source: 'nevo', kcal: 92, protein_g: 1.1, carbs_g: 20, fat_g: 0.3, score: 100 }
const own = { id: 9, name: 'Havermout', source: 'manual', kcal: 370, protein_g: 13, carbs_g: 60, fat_g: 7, score: 100 }

function server(results: FoodSearchResult['results'] = [banana, own]) {
  return fakeServer({
    ...emptyDataHandlers(),
    'GET /api/day': () => json(dayFixture()),
    'GET /api/foods/search': (request) =>
      json({ query: new URL(request.url).searchParams.get('q'), results }),
    'POST /api/entries': () => json({ id: 1 }, 201),
    'POST /api/foods': () => json({ id: 10 }, 201),
    'PATCH /api/foods/9': () => json({ id: 9 }),
  })
}

function posts(s: ReturnType<typeof fakeServer>, key: string) {
  return s.calls.filter((call) => call.key === key).map((call) => JSON.parse(call.body))
}

describe('adding food', () => {
  it('opens from the day page for the day that is shown', async () => {
    const { user, router } = renderApp('/dag?date=2026-11-10', server())

    await user.click(await screen.findByRole('link', { name: 'Eten toevoegen' }))

    expect(router.state.location.pathname).toBe('/dag/toevoegen')
    expect(router.state.location.search).toBe('?date=2026-11-10')
    expect(await screen.findByText('Voor dinsdag 10 november')).toBeInTheDocument()
  })

  it('does not search for a single letter', async () => {
    const s = server()
    const { user } = renderApp('/dag/toevoegen', s)

    await user.type(await screen.findByLabelText('Zoek een voedingsmiddel'), 'b')

    expect(s.calls.filter((call) => call.key === 'GET /api/foods/search')).toHaveLength(0)
  })

  it('logs an amount of a found food for today and returns to the day', async () => {
    const s = server()
    const { user, router } = renderApp('/dag/toevoegen', s)

    await user.type(await screen.findByLabelText('Zoek een voedingsmiddel'), 'banaan')
    await user.click(await screen.findByRole('button', { name: /Banaan/ }))
    const amount = screen.getByLabelText(/Hoeveelheid/)
    await user.clear(amount)
    await user.type(amount, '120,5')
    await user.click(screen.getByRole('button', { name: 'Toevoegen' }))

    expect(await screen.findByRole('heading', { name: 'Dag' })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/dag')
    expect(posts(s, 'POST /api/entries')).toEqual([{ food_id: 7, amount_g: 120.5 }])
  })

  it('logs on the chosen day at noon when that day is not today', async () => {
    const s = server()
    const { user, router } = renderApp('/dag/toevoegen?date=2026-11-10', s)

    await user.type(await screen.findByLabelText('Zoek een voedingsmiddel'), 'banaan')
    await user.click(await screen.findByRole('button', { name: /Banaan/ }))
    await user.click(screen.getByRole('button', { name: 'Toevoegen' }))

    await screen.findByRole('heading', { name: 'Dag' })
    expect(posts(s, 'POST /api/entries')).toEqual([
      { food_id: 7, amount_g: 100, logged_at: '2026-11-10T12:00:00' },
    ])
    expect(router.state.location.search).toBe('?date=2026-11-10')
  })

  it('refuses an amount of zero', async () => {
    const s = server()
    const { user } = renderApp('/dag/toevoegen', s)

    await user.type(await screen.findByLabelText('Zoek een voedingsmiddel'), 'banaan')
    await user.click(await screen.findByRole('button', { name: /Banaan/ }))
    const amount = screen.getByLabelText(/Hoeveelheid/)
    await user.clear(amount)
    await user.type(amount, '0')

    expect(screen.getByRole('button', { name: 'Toevoegen' })).toBeDisabled()
    expect(screen.getByRole('alert')).toHaveTextContent('groter dan 0')
  })

  it('shows a message when the server says no', async () => {
    const s = server()
    s.handlers['POST /api/entries'] = () => json({ detail: 'Nope' }, 404)
    const { user } = renderApp('/dag/toevoegen', s)

    await user.type(await screen.findByLabelText('Zoek een voedingsmiddel'), 'banaan')
    await user.click(await screen.findByRole('button', { name: /Banaan/ }))
    await user.click(screen.getByRole('button', { name: 'Toevoegen' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Dit bestaat niet meer')
    expect(screen.queryByRole('heading', { name: 'Dag' })).not.toBeInTheDocument()
  })

  it('offers to create a product when nothing is found', async () => {
    const { user } = renderApp('/dag/toevoegen', server([]))

    await user.type(await screen.findByLabelText('Zoek een voedingsmiddel'), 'zzzz')

    expect(await screen.findByText(/Niets gevonden/)).toBeInTheDocument()
  })
})

describe('own products', () => {
  it('creates a product with decimal commas', async () => {
    const s = server([])
    const { user } = renderApp('/dag/toevoegen', s)

    await user.click(await screen.findByRole('button', { name: 'Nieuw product maken' }))
    await user.type(screen.getByLabelText('Naam'), '  Skyr ')
    await user.type(screen.getByLabelText(/Energie/), '63')
    await user.type(screen.getByLabelText(/Eiwit/), '11,5')
    await user.type(screen.getByLabelText(/Koolhydraten/), '4')
    await user.type(screen.getByLabelText(/Vet/), '0,2')
    await user.click(screen.getByRole('button', { name: 'Opslaan' }))

    expect(await screen.findByLabelText('Zoek een voedingsmiddel')).toHaveValue('Skyr')
    expect(posts(s, 'POST /api/foods')).toEqual([
      { name: 'Skyr', kcal: 63, protein_g: 11.5, carbs_g: 4, fat_g: 0.2 },
    ])
  })

  it('does not accept macros above 100 g per 100 g', async () => {
    const { user } = renderApp('/dag/toevoegen', server([]))

    await user.click(await screen.findByRole('button', { name: 'Nieuw product maken' }))
    await user.type(screen.getByLabelText('Naam'), 'Magie')
    await user.type(screen.getByLabelText(/Energie/), '100')
    await user.type(screen.getByLabelText(/Eiwit/), '60')
    await user.type(screen.getByLabelText(/Koolhydraten/), '60')
    await user.type(screen.getByLabelText(/Vet/), '0')

    expect(screen.getByRole('alert')).toHaveTextContent('boven 100 g')
    expect(screen.getByRole('button', { name: 'Opslaan' })).toBeDisabled()
  })

  it('edits only your own products', async () => {
    const s = server()
    const { user } = renderApp('/dag/toevoegen', s)

    await user.type(await screen.findByLabelText('Zoek een voedingsmiddel'), 'ha')
    await user.click(await screen.findByRole('button', { name: /Banaan/ }))
    expect(screen.queryByRole('button', { name: 'Product bewerken' })).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /Havermout/ }))
    await user.click(screen.getByRole('button', { name: 'Product bewerken' }))
    const kcal = screen.getByLabelText(/Energie/)
    expect(kcal).toHaveValue('370')
    await user.clear(kcal)
    await user.type(kcal, '380')
    await user.click(screen.getByRole('button', { name: 'Opslaan' }))

    await screen.findByLabelText('Zoek een voedingsmiddel')
    expect(posts(s, 'PATCH /api/foods/9')).toEqual([
      { name: 'Havermout', kcal: 380, protein_g: 13, carbs_g: 60, fat_g: 7 },
    ])
  })
})

