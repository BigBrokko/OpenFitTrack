import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter } from 'react-router'
import { RouterProvider } from 'react-router/dom'
import { ApiProvider } from '../api/ApiContext'
import { createApiClient } from '../api/client'
import { routes } from '../routes'

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

/**
 * A fake server: `handlers` maps "METHOD /path" to an answer. `handlers` can be changed
 * during a test (to simulate logging in), and every request is recorded in `calls`.
 */
export function fakeServer(handlers: Record<string, Handler>) {
  const calls: { key: string; body: string }[] = []
  const fakeFetch = async (input: RequestInfo | URL) => {
    const request = input as Request
    const key = `${request.method} ${new URL(request.url).pathname}`
    calls.push({ key, body: await request.clone().text() })
    const handler = handlers[key]
    if (!handler) throw new Error(`Unexpected request: ${key}`)
    return handler(request)
  }
  return { handlers, calls, fetch: fakeFetch as typeof fetch }
}

export function renderApp(route: string, server: ReturnType<typeof fakeServer>) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
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
