import { screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { noWeights, weightFixture } from '../test/fixtures'
import { emptyDataHandlers, fakeServer, json, renderApp } from '../test/utils'

function server(weight = weightFixture()) {
  return fakeServer({ ...emptyDataHandlers(), 'GET /api/weight': () => json(weight) })
}

function weightRequests(s: ReturnType<typeof fakeServer>) {
  return s.calls.filter((call) => call.key === 'GET /api/weight').map((call) => call.search)
}

describe('weight page', () => {
  it('shows the latest weight, the trend and the 7-day change', async () => {
    renderApp('/gewicht', server())

    expect(await screen.findByText('82,0 kg')).toBeInTheDocument()
    expect(screen.getByText('82,6 kg')).toBeInTheDocument()
    expect(screen.getByText('−0,2 kg')).toBeInTheDocument()
  })

  it('shows a dash where there is not enough data yet', async () => {
    renderApp(
      '/gewicht',
      server(weightFixture({ trend_change_7d_kg: null, latest_trend_kg: null })),
    )

    expect(await screen.findByText('82,0 kg')).toBeInTheDocument()
    expect(screen.getAllByText('—')).toHaveLength(2)
  })

  it('draws the chart with a legend that includes the target weight', async () => {
    renderApp('/gewicht', server())

    expect(await screen.findByRole('img', { name: /Grafiek van je gewicht/ })).toBeInTheDocument()
    expect(screen.getByText('Streefgewicht')).toBeInTheDocument()
  })

  it('leaves the target out of the legend when there is none', async () => {
    renderApp('/gewicht', server(weightFixture({ target_weight_kg: null })))

    await screen.findByRole('img', { name: /Grafiek van je gewicht/ })
    expect(screen.queryByText('Streefgewicht')).not.toBeInTheDocument()
  })

  it('explains an empty log and offers no period buttons', async () => {
    renderApp('/gewicht', server(noWeights))

    expect(await screen.findByText(/Nog geen gewicht gelogd/)).toBeInTheDocument()
    expect(screen.queryByRole('group', { name: 'Periode' })).not.toBeInTheDocument()
  })

  it('says so when there are measurements, but none in the chosen period', async () => {
    renderApp('/gewicht?dagen=30', server(weightFixture({ points: [] })))

    expect(await screen.findByText('Geen metingen in de afgelopen 30 dagen.')).toBeInTheDocument()
    expect(screen.getByText('82,0 kg')).toBeInTheDocument()
  })
})

describe('choosing the period', () => {
  it('asks for 90 days by default, with a clean URL', async () => {
    const s = server()
    renderApp('/gewicht', s)

    expect(await screen.findByRole('button', { name: '90 dagen' })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
    expect(weightRequests(s)).toEqual(['?days=90'])
  })

  it('loads another period and keeps it in the URL', async () => {
    const s = server()
    const { user, router } = renderApp('/gewicht', s)

    await user.click(await screen.findByRole('button', { name: '365 dagen' }))

    expect(await screen.findByRole('button', { name: '365 dagen' })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
    expect(screen.getByRole('button', { name: '90 dagen' })).toHaveAttribute('aria-pressed', 'false')
    expect(weightRequests(s)).toContain('?days=365')
    expect(router.state.location.search).toBe('?dagen=365')
  })

  it('ignores a period that is not on offer', async () => {
    const s = server()
    renderApp('/gewicht?dagen=7', s)

    await screen.findByRole('button', { name: '90 dagen' })
    expect(weightRequests(s)).toEqual(['?days=90'])
  })
})
