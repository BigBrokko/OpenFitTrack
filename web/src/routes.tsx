import { Navigate, type RouteObject } from 'react-router'
import { RequireAuth } from './components/RequireAuth'
import { AddFoodPage } from './pages/AddFoodPage'
import { DayPage } from './pages/DayPage'
import { GoalsPage } from './pages/GoalsPage'
import { LoginPage } from './pages/LoginPage'
import { WeightPage } from './pages/WeightPage'

export const routes: RouteObject[] = [
  { path: '/login', element: <LoginPage /> },
  {
    path: '/',
    element: <RequireAuth />,
    children: [
      { index: true, element: <Navigate to="/dag" replace /> },
      { path: 'dag', element: <DayPage /> },
      { path: 'dag/toevoegen', element: <AddFoodPage /> },
      { path: 'gewicht', element: <WeightPage /> },
      { path: 'doelen', element: <GoalsPage /> },
    ],
  },
  { path: '*', element: <Navigate to="/" replace /> },
]
