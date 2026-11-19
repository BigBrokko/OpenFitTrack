import { screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { goalsFixture, noGoals } from '../test/fixtures'
import { emptyDataHandlers, fakeServer, json, renderApp } from '../test/utils'

function server(goals = goalsFixture) {
  return fakeServer({ ...emptyDataHandlers(), 'GET /api/goals': () => json(goals) })
}

describe('goals page', () => {
  it('shows the current goal with its start date and target weight', async () => {
    renderApp('/doelen', server())

    expect(await screen.findByText('Huidig doel, sinds 1 november 2026')).toBeInTheDocument()
    const current = screen.getByText('Huidig doel, sinds 1 november 2026').parentElement!
    expect(within(current).getByText('2.000 kcal')).toBeInTheDocument()
    expect(within(current).getByText('160 g')).toBeInTheDocument()
    expect(within(current).getByText('80 kg')).toBeInTheDocument()
  })

  it('lists the history, newest first, and marks the current goal once', async () => {
    renderApp('/doelen', server())

    const history = (await screen.findByRole('heading', { name: 'Geschiedenis' })).parentElement!
    const items = within(history).getAllByRole('listitem')
    expect(items).toHaveLength(2)
    expect(items[0]).toHaveTextContent('1 november 2026')
    expect(items[0]).toHaveTextContent('Huidig')
    expect(items[0]).toHaveTextContent('streefgewicht 80 kg')
    expect(items[1]).toHaveTextContent('3 september 2026')
    expect(items[1]).toHaveTextContent('2.200 kcal')
    expect(items[1]).not.toHaveTextContent('Huidig')
    expect(items[1]).not.toHaveTextContent('streefgewicht')
  })

  it('shows a dash when the current goal has no target weight', async () => {
    const goal = { ...goalsFixture.history[1], valid_from: '2026-11-01' }
    renderApp('/doelen', server({ current: goal, history: [goal] }))

    const current = (await screen.findByText(/Huidig doel, sinds/)).parentElement!
    expect(within(current).getByText('—')).toBeInTheDocument()
  })

  it('explains that there is no goal yet', async () => {
    renderApp('/doelen', server(noGoals))

    expect(await screen.findByText(/nog geen doel ingesteld/)).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Geschiedenis' })).not.toBeInTheDocument()
  })
})
