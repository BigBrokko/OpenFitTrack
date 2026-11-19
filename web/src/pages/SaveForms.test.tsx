import { screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { goalsFixture, noGoals, weightFixture } from '../test/fixtures'
import { emptyDataHandlers, fakeServer, json, renderApp } from '../test/utils'

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(new Date(2026, 10, 12, 12, 0))
})
afterEach(() => vi.useRealTimers())

function bodies(s: ReturnType<typeof fakeServer>, key: string) {
  return s.calls.filter((call) => call.key === key).map((call) => JSON.parse(call.body))
}

describe('logging weight', () => {
  function server() {
    return fakeServer({
      ...emptyDataHandlers(),
      'GET /api/weight': () => json(weightFixture()),
      'PUT /api/weight': () => json({ date: '2026-11-12', weight_kg: 80.4 }),
    })
  }

  it('saves the weight of today and reloads the chart data', async () => {
    const s = server()
    const { user } = renderApp('/gewicht', s)

    await user.type(await screen.findByLabelText(/Gewicht \(kg\)/), '80,4')
    await user.click(screen.getByRole('button', { name: 'Opslaan' }))

    expect(await screen.findByRole('status')).toHaveTextContent('Opgeslagen.')
    expect(bodies(s, 'PUT /api/weight')).toEqual([{ date: '2026-11-12', weight_kg: 80.4 }])
    expect(s.calls.filter((call) => call.key === 'GET /api/weight')).toHaveLength(2)
    expect(screen.getByLabelText(/Gewicht \(kg\)/)).toHaveValue('')
  })

  it('can log an earlier day, but not a day in the future', async () => {
    const s = server()
    const { user } = renderApp('/gewicht', s)

    const date = await screen.findByLabelText('Datum')
    expect(date).toHaveAttribute('max', '2026-11-12')
    await user.clear(date)
    await user.type(date, '2026-11-10')
    await user.type(screen.getByLabelText(/Gewicht \(kg\)/), '81')
    await user.click(screen.getByRole('button', { name: 'Opslaan' }))

    await screen.findByRole('status')
    expect(bodies(s, 'PUT /api/weight')).toEqual([{ date: '2026-11-10', weight_kg: 81 }])
  })

  it('refuses an implausible weight', async () => {
    const { user } = renderApp('/gewicht', server())

    await user.type(await screen.findByLabelText(/Gewicht \(kg\)/), '8')

    expect(screen.getByRole('alert')).toHaveTextContent('tussen 20 en 400 kg')
    expect(screen.getByRole('button', { name: 'Opslaan' })).toBeDisabled()
  })
})

describe('setting a goal', () => {
  function server(goals = goalsFixture) {
    return fakeServer({
      ...emptyDataHandlers(),
      'GET /api/goals': () => json(goals),
      'PUT /api/goals': () => json(goals.current ?? goalsFixture.history[0]),
    })
  }

  it('starts with the current goal, saves a change and closes the form', async () => {
    const s = server()
    const { user } = renderApp('/doelen', s)

    await user.click(await screen.findByRole('button', { name: 'Doel wijzigen' }))
    const kcal = screen.getByLabelText(/Energie/)
    expect(kcal).toHaveValue('2000')
    await user.clear(kcal)
    await user.type(kcal, '1900')
    await user.click(screen.getByRole('button', { name: 'Opslaan' }))

    expect(await screen.findByRole('button', { name: 'Doel wijzigen' })).toBeInTheDocument()
    expect(bodies(s, 'PUT /api/goals')).toEqual([
      { kcal: 1900, protein_g: 160, carbs_g: 50, fat_g: 70, target_weight_kg: 80 },
    ])
    expect(s.calls.filter((call) => call.key === 'GET /api/goals')).toHaveLength(2)
  })

  it('can set a first goal without a target weight', async () => {
    const s = server(noGoals)
    const { user } = renderApp('/doelen', s)

    await user.click(await screen.findByRole('button', { name: 'Doel instellen' }))
    await user.type(screen.getByLabelText(/Energie/), '2200')
    await user.type(screen.getByLabelText(/Eiwit/), '150')
    await user.type(screen.getByLabelText(/Koolhydraten/), '250')
    await user.type(screen.getByLabelText(/Vet/), '70')
    await user.click(screen.getByRole('button', { name: 'Opslaan' }))

    await screen.findByRole('button', { name: 'Doel instellen' })
    expect(bodies(s, 'PUT /api/goals')).toEqual([
      { kcal: 2200, protein_g: 150, carbs_g: 250, fat_g: 70, target_weight_kg: null },
    ])
  })

  it('needs an energy goal above zero', async () => {
    const { user } = renderApp('/doelen', server(noGoals))

    await user.click(await screen.findByRole('button', { name: 'Doel instellen' }))
    await user.type(screen.getByLabelText(/Energie/), '0')
    await user.type(screen.getByLabelText(/Eiwit/), '1')
    await user.type(screen.getByLabelText(/Koolhydraten/), '1')
    await user.type(screen.getByLabelText(/Vet/), '1')

    expect(screen.getByRole('button', { name: 'Opslaan' })).toBeDisabled()
  })
})
