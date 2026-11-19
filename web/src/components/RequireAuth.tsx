import type { ReactNode } from 'react'
import { Navigate } from 'react-router'
import { useMe } from '../api/auth'
import { AppShell } from './AppShell'

function FullScreenMessage({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-dvh flex-col items-center justify-center gap-4 bg-white p-6 text-center text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      {children}
    </div>
  )
}

/** Shows the app for a logged-in visitor and sends everyone else to the login page. */
export function RequireAuth() {
  const me = useMe()

  if (me.isPending) return <FullScreenMessage>Laden…</FullScreenMessage>

  if (me.isError) {
    return (
      <FullScreenMessage>
        <p>Geen verbinding met de server.</p>
        <button
          type="button"
          onClick={() => me.refetch()}
          className="rounded-md bg-green-700 px-4 py-2 font-medium text-white hover:bg-green-800"
        >
          Opnieuw proberen
        </button>
      </FullScreenMessage>
    )
  }

  if (!me.data.authenticated) return <Navigate to="/login" replace />

  return <AppShell />
}
