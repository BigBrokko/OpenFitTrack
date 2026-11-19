import createClient from 'openapi-fetch'
import type { paths } from './schema'

export type ApiClient = ReturnType<typeof createApiClient>

/**
 * A typed client for the API. The types come from web/openapi.json (npm run gen:api), so a
 * wrong path or field is a compile error. Tests pass their own `fetchImpl`.
 */
export function createApiClient(
  fetchImpl: typeof fetch = (...args) => fetch(...args),
  baseUrl: string = window.location.origin,
) {
  return createClient<paths>({ baseUrl, fetch: fetchImpl })
}
