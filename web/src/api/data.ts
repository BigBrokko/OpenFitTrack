import { useQuery, useQueryClient, type QueryClient } from '@tanstack/react-query'
import type { ISODate } from '../lib/format'
import { useApi } from './ApiContext'
import { forgetSession } from './auth'

/** The server said 401: the session is gone. The app has already moved to the login page. */
export class UnauthorizedError extends Error {
  constructor() {
    super('Not logged in')
    this.name = 'UnauthorizedError'
  }
}

/** Retry a failed request once, but never when the session has expired. */
export function shouldRetry(failureCount: number, error: Error): boolean {
  return !(error instanceof UnauthorizedError) && failureCount < 1
}

export function unwrap<T>(queryClient: QueryClient, result: { data?: T; response: Response }): T {
  if (result.response.status === 401) {
    forgetSession(queryClient) // the screens react by showing the login page
    throw new UnauthorizedError()
  }
  if (result.data === undefined) throw new Error(`Unexpected status ${result.response.status}`)
  return result.data
}

const STALE_MS = 30_000

export function useDay(date: ISODate) {
  const api = useApi()
  const queryClient = useQueryClient()
  return useQuery({
    queryKey: ['day', date],
    queryFn: async () =>
      unwrap(queryClient, await api.GET('/api/day', { params: { query: { date } } })),
    staleTime: STALE_MS,
  })
}

export function useWeight(days: number) {
  const api = useApi()
  const queryClient = useQueryClient()
  return useQuery({
    queryKey: ['weight', days],
    queryFn: async () =>
      unwrap(queryClient, await api.GET('/api/weight', { params: { query: { days } } })),
    staleTime: STALE_MS,
  })
}

export function useGoals() {
  const api = useApi()
  const queryClient = useQueryClient()
  return useQuery({
    queryKey: ['goals'],
    queryFn: async () => unwrap(queryClient, await api.GET('/api/goals')),
    staleTime: STALE_MS,
  })
}
