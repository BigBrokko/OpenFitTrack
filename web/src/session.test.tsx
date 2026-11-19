import { screen, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { dayFixture } from './test/fixtures'
import { emptyDataHandlers, fakeServer, json, renderApp, unauthorized } from './test/utils'

describe('a session that expires while the app is open', () => {
  it('moves to the login page instead of showing an error, and forgets the loaded data', async () => {
    const server = fakeServer({ ...emptyDataHandlers(), 'GET /api/day': unauthorized })
    const { queryClient, router } = renderApp('/dag', server)
    queryClient.setQueryData(['goals'], { current: null, history: [] }) // some other loaded data

    expect(await screen.findByRole('button', { name: 'Inloggen' })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/login')
    expect(screen.queryByText('Kon de gegevens niet laden.')).not.toBeInTheDocument()
    await waitFor(() => {
      const keys = queryClient.getQueryCache().getAll().map((query) => query.queryKey)
      expect(keys).toEqual([['me']])
    })
  })

  it('does not try the request again', async () => {
    const server = fakeServer({ ...emptyDataHandlers(), 'GET /api/day': unauthorized })
    renderApp('/dag', server)

    await screen.findByRole('button', { name: 'Inloggen' })
    expect(server.calls.filter((call) => call.key === 'GET /api/day')).toHaveLength(1)
  })

  it('shows the data again after logging back in', async () => {
    const server = fakeServer({
      ...emptyDataHandlers(),
      'GET /api/day': unauthorized,
      'POST /api/login': () => new Response(null, { status: 204 }),
    })
    const { user } = renderApp('/dag', server)
    await user.type(await screen.findByLabelText('Wachtwoord'), 'geheim-wachtwoord')
    server.handlers['GET /api/day'] = () => json(dayFixture({ date: new Date().toISOString().slice(0, 10) }))

    await user.click(screen.getByRole('button', { name: 'Inloggen' }))

    expect(await screen.findByText('Kwark volle')).toBeInTheDocument()
  })
})
