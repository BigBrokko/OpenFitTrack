import { screen, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { fakeServer, json, noContent, renderApp, unauthorized } from './test/utils'

const loggedIn = () => json({ authenticated: true })

function loggedOutServer(extra = {}) {
  return fakeServer({ 'GET /api/me': unauthorized, ...extra })
}

function loggedInServer(extra = {}) {
  return fakeServer({ 'GET /api/me': loggedIn, ...extra })
}

describe('access', () => {
  it('sends a visitor who is not logged in to the login page', async () => {
    const { router } = renderApp('/dag', loggedOutServer())

    expect(await screen.findByRole('button', { name: 'Inloggen' })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/login')
  })

  it('shows the app with its three tabs to a logged-in visitor', async () => {
    renderApp('/dag', loggedInServer())

    expect(await screen.findByRole('heading', { name: 'Dag' })).toBeInTheDocument()
    const menu = screen.getByRole('navigation', { name: 'Hoofdmenu' })
    expect(menu).toHaveTextContent('Dag')
    expect(menu).toHaveTextContent('Gewicht')
    expect(menu).toHaveTextContent('Doelen')
  })

  it('opens the day page from the root and from unknown addresses', async () => {
    const { router } = renderApp('/ergens/anders', loggedInServer())

    expect(await screen.findByRole('heading', { name: 'Dag' })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/dag')
  })

  it('skips the login page for someone who is already logged in', async () => {
    const { router } = renderApp('/login', loggedInServer())

    expect(await screen.findByRole('heading', { name: 'Dag' })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/dag')
  })

  it('says so when the server cannot be reached, and tries again on request', async () => {
    const server = fakeServer({
      'GET /api/me': () => {
        throw new TypeError('Failed to fetch')
      },
    })
    const { user } = renderApp('/dag', server)

    expect(await screen.findByText('Geen verbinding met de server.')).toBeInTheDocument()

    server.handlers['GET /api/me'] = loggedIn
    await user.click(screen.getByRole('button', { name: 'Opnieuw proberen' }))

    expect(await screen.findByRole('heading', { name: 'Dag' })).toBeInTheDocument()
  })
})

describe('logging in', () => {
  async function typePasswordAndSubmit(
    user: ReturnType<typeof renderApp>['user'],
    password = 'geheim-wachtwoord',
  ) {
    await user.type(await screen.findByLabelText('Wachtwoord'), password)
    await user.click(screen.getByRole('button', { name: 'Inloggen' }))
  }

  it('keeps the button disabled until a password is typed', async () => {
    const { user } = renderApp('/login', loggedOutServer())

    const button = await screen.findByRole('button', { name: 'Inloggen' })
    expect(button).toBeDisabled()

    await user.type(screen.getByLabelText('Wachtwoord'), 'x')
    expect(button).toBeEnabled()
  })

  it('sends the password as JSON and opens the app on success', async () => {
    const server = loggedOutServer({ 'POST /api/login': noContent })
    const { user, router } = renderApp('/login', server)

    await typePasswordAndSubmit(user)

    expect(await screen.findByRole('heading', { name: 'Dag' })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/dag')
    const login = server.calls.find((call) => call.key === 'POST /api/login')
    expect(JSON.parse(login!.body)).toEqual({ password: 'geheim-wachtwoord' })
  })

  it('shows a message for a wrong password and stays on the login page', async () => {
    const server = loggedOutServer({
      'POST /api/login': () => json({ detail: 'Wrong password.' }, 401),
    })
    const { user, router } = renderApp('/login', server)

    await typePasswordAndSubmit(user)

    expect(await screen.findByRole('alert')).toHaveTextContent('Dat wachtwoord klopt niet.')
    expect(router.state.location.pathname).toBe('/login')
  })

  it('tells how long to wait after too many attempts', async () => {
    const server = loggedOutServer({
      'POST /api/login': () => json({ detail: 'Too many' }, 429, { 'Retry-After': '900' }),
    })
    const { user } = renderApp('/login', server)

    await typePasswordAndSubmit(user)

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Te veel pogingen. Probeer het over 15 minuten opnieuw.',
    )
  })

  it('rounds a short wait up to one minute', async () => {
    const server = loggedOutServer({
      'POST /api/login': () => json({ detail: 'Too many' }, 429, { 'Retry-After': '30' }),
    })
    const { user } = renderApp('/login', server)

    await typePasswordAndSubmit(user)

    expect(await screen.findByRole('alert')).toHaveTextContent('over 1 minuut opnieuw')
  })

  it('shows a message when the server cannot be reached', async () => {
    const server = loggedOutServer({
      'POST /api/login': () => {
        throw new TypeError('Failed to fetch')
      },
    })
    const { user } = renderApp('/login', server)

    await typePasswordAndSubmit(user)

    expect(await screen.findByRole('alert')).toHaveTextContent('Geen verbinding met de server.')
  })
})

describe('using the app', () => {
  it('moves between the tabs and marks the current one', async () => {
    const { user } = renderApp('/dag', loggedInServer())

    await user.click(await screen.findByRole('link', { name: 'Gewicht' }))

    expect(await screen.findByRole('heading', { name: 'Gewicht' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Gewicht' })).toHaveAttribute('aria-current', 'page')
    expect(screen.getByRole('link', { name: 'Dag' })).not.toHaveAttribute('aria-current')
  })

  it('logs out, returns to the login page and forgets everything it loaded', async () => {
    const server = loggedInServer({ 'POST /api/logout': noContent })
    const { user, queryClient, router } = renderApp('/dag', server)
    queryClient.setQueryData(['day', '2026-01-12'], { totals: { kcal: 1234 } }) // some loaded data

    await user.click(await screen.findByRole('button', { name: 'Uitloggen' }))

    expect(await screen.findByRole('button', { name: 'Inloggen' })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/login')
    expect(server.calls.some((call) => call.key === 'POST /api/logout')).toBe(true)
    await waitFor(() => {
      const keys = queryClient.getQueryCache().getAll().map((query) => query.queryKey)
      expect(keys).toEqual([['me']])
    })
  })

  it('still logs out locally when the server cannot be reached', async () => {
    const server = loggedInServer({
      'POST /api/logout': () => {
        throw new TypeError('Failed to fetch')
      },
    })
    const { user } = renderApp('/dag', server)

    await user.click(await screen.findByRole('button', { name: 'Uitloggen' }))

    expect(await screen.findByRole('button', { name: 'Inloggen' })).toBeInTheDocument()
  })
})
