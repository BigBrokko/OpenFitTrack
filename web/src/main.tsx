import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { createBrowserRouter } from 'react-router'
import { RouterProvider } from 'react-router/dom'
import { ApiProvider } from './api/ApiContext'
import { createApiClient } from './api/client'
import { shouldRetry } from './api/data'
import './index.css'
import { routes } from './routes'

const queryClient = new QueryClient({ defaultOptions: { queries: { retry: shouldRetry } } })
const api = createApiClient()
const router = createBrowserRouter(routes)

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ApiProvider client={api}>
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>
    </ApiProvider>
  </StrictMode>,
)
