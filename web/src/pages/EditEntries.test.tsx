import { screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { dayFixture } from '../test/fixtures'
import { emptyDataHandlers, fakeServer, json, noContent, renderApp } from '../test/utils'

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(new Date(2026, 10, 12, 12, 0))
})
afterEach(() => vi.useRealTimers())

function server() {
  return fakeServer({
    ...emptyDataHandlers(),
    'GET /api/day': () => json(dayFixture()),
    'PATCH /api/entries/1': () => json({ id: 1 }),
    'DELETE /api/entries/1': noContent,
  })
}

function dayLoads(s: ReturnType<typeof fakeServer>) {
  return s.calls.filter((call) => call.key === 'GET /api/day').length
}

describe('correcting a logged line', () => {
  it('saves a new amount and reloads the day', async () => {
    const s = server()
    const { user } = renderApp('/dag', s)

    await user.click(await screen.findByRole('button', { name: 'Wijzig Kwark volle' }))
    const amount = screen.getByLabelText(/Hoeveelheid/)
    expect(amount).toHaveValue('200')
    await user.clear(amount)
    await user.type(amount, '150')
    await user.click(screen.getByRole('button', { name: 'Opslaan' }))

    await vi.waitFor(() => expect(dayLoads(s)).toBe(2))
    const patch = s.calls.find((call) => call.key === 'PATCH /api/entries/1')
    expect(JSON.parse(patch!.body)).toEqual({ amount_g: 150 })
    expect(screen.queryByLabelText(/Hoeveelheid/)).not.toBeInTheDocument()
  })

  it('cancels without sending anything', async () => {
    const s = server()
    const { user } = renderApp('/dag', s)

    await user.click(await screen.findByRole('button', { name: 'Wijzig Kwark volle' }))
    await user.click(screen.getByRole('button', { name: 'Annuleren' }))

    expect(screen.getByRole('button', { name: 'Wijzig Kwark volle' })).toBeInTheDocument()
    expect(s.calls.some((call) => call.key.startsWith('PATCH'))).toBe(false)
  })

  it('does not allow an empty or zero amount', async () => {
    const { user } = renderApp('/dag', server())

    await user.click(await screen.findByRole('button', { name: 'Wijzig Kwark volle' }))
    await user.clear(screen.getByLabelText(/Hoeveelheid/))

    expect(screen.getByRole('button', { name: 'Opslaan' })).toBeDisabled()
  })
})

describe('deleting a logged line', () => {
  it('asks first and then deletes', async () => {
    const s = server()
    const { user } = renderApp('/dag', s)

    await user.click(await screen.findByRole('button', { name: 'Wijzig Kwark volle' }))
    await user.click(screen.getByRole('button', { name: 'Verwijderen' }))

    expect(screen.getByText('Verwijder Kwark volle (200 g) van deze dag?')).toBeInTheDocument()
    expect(s.calls.some((call) => call.key.startsWith('DELETE'))).toBe(false)

    await user.click(screen.getByRole('button', { name: 'Ja, verwijderen' }))

    await vi.waitFor(() => expect(dayLoads(s)).toBe(2))
    expect(s.calls.some((call) => call.key === 'DELETE /api/entries/1')).toBe(true)
  })

  it('shows an error and keeps the line when deleting fails', async () => {
    const s = server()
    s.handlers['DELETE /api/entries/1'] = () => {
      throw new TypeError('Failed to fetch')
    }
    const { user } = renderApp('/dag', s)

    await user.click(await screen.findByRole('button', { name: 'Wijzig Kwark volle' }))
    await user.click(screen.getByRole('button', { name: 'Verwijderen' }))
    await user.click(screen.getByRole('button', { name: 'Ja, verwijderen' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Geen verbinding met de server.')
    expect(screen.getByText('Kwark volle')).toBeInTheDocument()
  })
})
