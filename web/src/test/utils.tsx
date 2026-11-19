import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter } from 'react-router'
import { RouterProvider } from 'react-router/dom'
import { ApiProvider } from '../api/ApiContext'
import { createApiClient } from '../api/client'
import { routes } from '../routes'
import { emptyDay, noGoals, noWeights } from './fixtures'

/** Answers one request, e.g. `() => new Response(null, { status: 204 })`. */
export type Handler = (request: Request) => Response | Promise<Response>

export function json(body: unknown, status = 200, headers: HeadersInit = {}): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json', ...headers },
  })
}

export const noContent = () => new Response(null, { status: 204 })
export const unauthorized = () => json({ detail: 'Not logged in.' }, 401)
export const loggedIn = () => json({ authenticated: true })

/** Answers for a logged-in visitor with no data yet. Tests replace the ones they care about. */
export function emptyDataHandlers(): Record<string, Handler> {
  return {
    'GET /api/me': loggedIn,
    'GET /api/day': () => json(emptyDay),
    'GET /api/weight': () => json(noWeights),
    'GET /api/goals': () => json(noGoals),
  }
}

/**
 * A fake server: `handlers` maps "METHOD /path" to an answer. `handlers` can be changed
 * during a test, and every request is recorded in `calls` (with its query string).
 */
export function fakeServer(handlers: Record<string, Handler>) {
  const calls: { key: string; body: string; search: string }[] = []
  const fakeFetch = async (input: RequestInfo | URL) => {
    const request = input as Request
    const url = new URL(request.url)
    const key = `${request.method} ${url.pathname}`
    calls.push({ key, body: await request.clone().text(), search: url.search })
    const handler = handlers[key]
    if (!handler) throw new Error(`Unexpected request: ${key}`)
    return handler(request)
  }
  return { handlers, calls, fetch: fakeFetch as typeof fetch }
}

export function renderApp(route: string, server: ReturnType<typeof fakeServer>) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
  const router = createMemoryRouter(routes, { initialEntries: [route] })
  render(
    <ApiProvider client={createApiClient(server.fetch)}>
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>
    </ApiProvider>,
  )
  return { user: userEvent.setup(), queryClient, router }
}
