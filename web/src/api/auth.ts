import { useMutation, useQuery, useQueryClient, type QueryClient } from '@tanstack/react-query'
import { useApi } from './ApiContext'

export type LoginErrorKind = 'wrong-password' | 'too-many-attempts' | 'network' | 'unknown'

export class LoginError extends Error {
  kind: LoginErrorKind
  retryAfterSeconds: number | null

  constructor(kind: LoginErrorKind, retryAfterSeconds: number | null = null) {
    super(kind)
    this.name = 'LoginError'
    this.kind = kind
    this.retryAfterSeconds = retryAfterSeconds
  }
}

export interface Me {
  authenticated: boolean
}

const ME_KEY = ['me']

/**
 * Marks the visitor as logged out and forgets everything loaded for them, so no health data
 * lingers. The "me" query stays: screens listen to it, and queryClient.clear() would detach
 * them from it.
 */
export function forgetSession(queryClient: QueryClient) {
  queryClient.removeQueries({ predicate: (query) => query.queryKey[0] !== ME_KEY[0] })
  queryClient.setQueryData<Me>(ME_KEY, { authenticated: false })
}

/** Whether the visitor is logged in. A network failure is an error, not "logged out". */
export function useMe() {
  const api = useApi()
  return useQuery({
    queryKey: ME_KEY,
    queryFn: async (): Promise<Me> => {
      const { response } = await api.GET('/api/me')
      if (response.status === 401) return { authenticated: false }
      if (!response.ok) throw new Error(`Unexpected status ${response.status}`)
      return { authenticated: true }
    },
    retry: false,
    staleTime: 30_000,
  })
}

export function useLogin() {
  const api = useApi()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (password: string): Promise<void> => {
      let response: Response
      try {
        ;({ response } = await api.POST('/api/login', { body: { password } }))
      } catch {
        throw new LoginError('network')
      }
      if (response.status === 204) return
      if (response.status === 401) throw new LoginError('wrong-password')
      if (response.status === 429) {
        const seconds = Number(response.headers.get('Retry-After'))
        throw new LoginError('too-many-attempts', Number.isFinite(seconds) ? seconds : null)
      }
      throw new LoginError('unknown')
    },
    onSuccess: () => queryClient.setQueryData<Me>(ME_KEY, { authenticated: true }),
  })
}

export function useLogout() {
  const api = useApi()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (): Promise<void> => {
      await api.POST('/api/logout')
    },
    // Whatever the server said, this device is logged out afterwards.
    onSettled: () => forgetSession(queryClient),
  })
}
