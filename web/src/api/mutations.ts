import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useApi } from './ApiContext'
import type { ApiClient } from './client'
import { forgetSession } from './auth'
import { UnauthorizedError, unwrap } from './data'
import type { EntryChange, FoodSearchResult, FoodValues, GoalIn, NewEntry, WeightIn } from './types'

export type WriteErrorKind = 'rejected' | 'not-found' | 'network' | 'unknown'

/** A write that did not work. The server's own message is English, so screens map `kind`. */
export class WriteError extends Error {
  kind: WriteErrorKind

  constructor(kind: WriteErrorKind) {
    super(kind)
    this.name = 'WriteError'
    this.kind = kind
  }
}

export function writeErrorMessage(error: unknown): string {
  if (!(error instanceof WriteError)) return 'Er ging iets mis. Probeer het opnieuw.'
  switch (error.kind) {
    case 'rejected':
      return 'De server accepteert deze waarden niet. Is de naam al in gebruik, of kloppen de getallen niet?'
    case 'not-found':
      return 'Dit bestaat niet meer. Misschien is het al verwijderd.'
    case 'network':
      return 'Geen verbinding met de server.'
    default:
      return 'Er ging iets mis. Probeer het opnieuw.'
  }
}

/**
 * Runs one write request, turns the answer into a WriteError when it failed and, when it
 * worked, reloads what the screens show (everything except the login state).
 */
function useWrite<V>(request: (api: ApiClient, variables: V) => Promise<{ response: Response }>) {
  const api = useApi()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (variables: V): Promise<void> => {
      let response: Response
      try {
        ;({ response } = await request(api, variables))
      } catch {
        throw new WriteError('network')
      }
      if (response.status === 401) {
        forgetSession(queryClient) // the screens react by showing the login page
        throw new UnauthorizedError()
      }
      if (response.status === 400 || response.status === 422) throw new WriteError('rejected')
      if (response.status === 404) throw new WriteError('not-found')
      if (!response.ok) throw new WriteError('unknown')
    },
    onSuccess: () =>
      queryClient.invalidateQueries({ predicate: (query) => query.queryKey[0] !== 'me' }),
  })
}

export const useLogFood = () =>
  useWrite((api, body: NewEntry) => api.POST('/api/entries', { body }))

export const useUpdateEntry = () =>
  useWrite((api, { id, ...body }: EntryChange & { id: number }) =>
    api.PATCH('/api/entries/{entry_id}', { params: { path: { entry_id: id } }, body }),
  )

export const useDeleteEntry = () =>
  useWrite((api, id: number) =>
    api.DELETE('/api/entries/{entry_id}', { params: { path: { entry_id: id } } }),
  )

export const useCreateFood = () =>
  useWrite((api, body: FoodValues) => api.POST('/api/foods', { body }))

export const useUpdateFood = () =>
  useWrite((api, { id, ...body }: FoodValues & { id: number }) =>
    api.PATCH('/api/foods/{food_id}', { params: { path: { food_id: id } }, body }),
  )

export const useSaveWeight = () => useWrite((api, body: WeightIn) => api.PUT('/api/weight', { body }))

export const useSaveGoal = () => useWrite((api, body: GoalIn) => api.PUT('/api/goals', { body }))

const MIN_SEARCH_LENGTH = 2

/** Searches your foods. Nothing is requested for a query that is too short. */
export function useFoodSearch(query: string) {
  const api = useApi()
  const queryClient = useQueryClient()
  const trimmed = query.trim()
  return useQuery<FoodSearchResult>({
    queryKey: ['foods', trimmed],
    queryFn: async () =>
      unwrap(
        queryClient,
        await api.GET('/api/foods/search', { params: { query: { q: trimmed, limit: 10 } } }),
      ),
    enabled: trimmed.length >= MIN_SEARCH_LENGTH,
  })
}
