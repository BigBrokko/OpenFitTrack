import { Navigate, type RouteObject } from 'react-router'
import { RequireAuth } from './components/RequireAuth'
import { LoginPage } from './pages/LoginPage'
import { PlaceholderPage } from './pages/PlaceholderPage'

export const routes: RouteObject[] = [
  { path: '/login', element: <LoginPage /> },
  {
    path: '/',
    element: <RequireAuth />,
    children: [
      { index: true, element: <Navigate to="/dag" replace /> },
      { path: 'dag', element: <PlaceholderPage title="Dag" /> },
      { path: 'gewicht', element: <PlaceholderPage title="Gewicht" /> },
      { path: 'doelen', element: <PlaceholderPage title="Doelen" /> },
    ],
  },
  { path: '*', element: <Navigate to="/" replace /> },
]
