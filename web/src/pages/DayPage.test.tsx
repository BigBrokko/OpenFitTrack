import { screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { dayFixture, emptyDay } from '../test/fixtures'
import { emptyDataHandlers, fakeServer, json, renderApp } from '../test/utils'

// "Today" is 12 November 2026 in all these tests. Only Date is faked, timers keep running.
beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(new Date(2026, 10, 12, 12, 0))
})
afterEach(() => vi.useRealTimers())

function server(day = dayFixture()) {
  return fakeServer({ ...emptyDataHandlers(), 'GET /api/day': () => json(day) })
}

function dayRequests(s: ReturnType<typeof fakeServer>) {
  return s.calls.filter((call) => call.key === 'GET /api/day').map((call) => call.search)
}

describe('day overview', () => {
  it('shows the totals against the goal, what is left, and what was eaten', async () => {
    const s = server()
    renderApp('/dag', s)

    expect(await screen.findByText('Kwark volle')).toBeInTheDocument()
    expect(screen.getByText('08:30 · 200 g')).toBeInTheDocument()
    expect(screen.getByText('236 kcal')).toBeInTheDocument()
    expect(screen.getByText('van 2.000 · nog 1.106 kcal')).toBeInTheDocument()
    expect(screen.getByText('van 160 · nog 123,6 g')).toBeInTheDocument()
    expect(screen.getByText('van 50 · +38,9 g over')).toBeInTheDocument()
    expect(dayRequests(s)).toEqual(['?date=2026-11-12'])
  })

  it('draws a progress bar per value that stops at 100% but reports the real percentage', async () => {
    renderApp('/dag', server())

    const energy = await screen.findByRole('progressbar', { name: 'Energie ten opzichte van je doel' })
    expect(energy).toHaveAttribute('aria-valuenow', '45')
    const carbs = screen.getByRole('progressbar', { name: 'Koolhydraten ten opzichte van je doel' })
    expect(carbs).toHaveAttribute('aria-valuenow', '100')
    expect(carbs).toHaveAttribute('aria-valuetext', '178%')
  })

  it('shows the totals without bars when the day has no goal', async () => {
    renderApp('/dag', server(dayFixture({ goal: null, progress: null })))

    expect(await screen.findByText('Voor deze dag is geen doel ingesteld.')).toBeInTheDocument()
    expect(screen.getByText('Energie')).toBeInTheDocument()
    expect(screen.queryByRole('progressbar')).not.toBeInTheDocument()
  })

  it('says that an empty day is not the same as eating nothing', async () => {
    renderApp('/dag', server(emptyDay))

    expect(
      await screen.findByText(/niets gelogd. Dat betekent niet dat je niets hebt gegeten/),
    ).toBeInTheDocument()
    expect(screen.queryByText(/Nothing is logged/)).not.toBeInTheDocument() // no English API text
  })
})

describe('choosing the day', () => {
  it('starts on today with the next-day button disabled', async () => {
    renderApp('/dag', server())

    expect(await screen.findByText(/donderdag 12 november/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Volgende dag' })).toBeDisabled()
    expect(screen.queryByRole('button', { name: 'Vandaag' })).not.toBeInTheDocument()
  })

  it('goes to the previous day, keeps it in the URL and can return to today', async () => {
    const s = server()
    const { user, router } = renderApp('/dag', s)

    await user.click(await screen.findByRole('button', { name: 'Vorige dag' }))

    expect(await screen.findByText(/woensdag 11 november/i)).toBeInTheDocument()
    expect(router.state.location.search).toBe('?date=2026-11-11')
    expect(dayRequests(s)).toContain('?date=2026-11-11')
    expect(screen.getByRole('button', { name: 'Volgende dag' })).toBeEnabled()

    await user.click(screen.getByRole('button', { name: 'Vandaag' }))

    expect(await screen.findByText(/donderdag 12 november/i)).toBeInTheDocument()
    expect(router.state.location.search).toBe('')
  })

  it('opens the day from the URL', async () => {
    const s = server()
    renderApp('/dag?date=2026-11-05', s)

    expect(await screen.findByText(/donderdag 5 november/i)).toBeInTheDocument()
    expect(dayRequests(s)).toEqual(['?date=2026-11-05'])
  })

  it('falls back to today for a date that does not exist', async () => {
    const s = server()
    renderApp('/dag?date=2026-02-30', s)

    expect(await screen.findByText(/donderdag 12 november/i)).toBeInTheDocument()
    expect(dayRequests(s)).toEqual(['?date=2026-11-12'])
  })
})

describe('when loading fails', () => {
  it('offers to try again', async () => {
    const s = server()
    s.handlers['GET /api/day'] = () => {
      throw new TypeError('Failed to fetch')
    }
    const { user } = renderApp('/dag', s)

    expect(await screen.findByRole('alert')).toHaveTextContent('Kon de gegevens niet laden.')

    s.handlers['GET /api/day'] = () => json(dayFixture())
    await user.click(screen.getByRole('button', { name: 'Opnieuw proberen' }))

    expect(await screen.findByText('Kwark volle')).toBeInTheDocument()
  })
})
