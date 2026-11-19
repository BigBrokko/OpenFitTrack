import { NavLink, Outlet } from 'react-router'
import { useLogout } from '../api/auth'
import { CalendarIcon, ScaleIcon, TargetIcon } from './icons'

const tabs = [
  { to: '/dag', label: 'Dag', icon: <CalendarIcon /> },
  { to: '/gewicht', label: 'Gewicht', icon: <ScaleIcon /> },
  { to: '/doelen', label: 'Doelen', icon: <TargetIcon /> },
]

/** The frame around every page after login: a header, the page, and a tab bar at the bottom. */
export function AppShell() {
  const logout = useLogout()

  return (
    <div className="flex min-h-dvh flex-col bg-white text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      <header className="sticky top-0 z-10 flex items-center justify-between border-b border-slate-200 bg-white/95 px-4 pt-[env(safe-area-inset-top)] backdrop-blur dark:border-slate-800 dark:bg-slate-950/95">
        <h1 className="py-3 text-lg font-semibold">OpenFitTrack</h1>
        <button
          type="button"
          onClick={() => logout.mutate()}
          disabled={logout.isPending}
          className="rounded-md px-3 py-2 text-sm font-medium text-green-700 hover:bg-green-50 disabled:opacity-50 dark:text-green-400 dark:hover:bg-slate-900"
        >
          Uitloggen
        </button>
      </header>

      <main className="flex-1 px-4 py-6">
        <Outlet />
      </main>

      <nav
        aria-label="Hoofdmenu"
        className="sticky bottom-0 grid grid-cols-3 border-t border-slate-200 bg-white/95 pb-[env(safe-area-inset-bottom)] backdrop-blur dark:border-slate-800 dark:bg-slate-950/95"
      >
        {tabs.map((tab) => (
          <NavLink
            key={tab.to}
            to={tab.to}
            className={({ isActive }) =>
              `flex flex-col items-center gap-1 py-2 text-xs font-medium ${
                isActive
                  ? 'text-green-700 dark:text-green-400'
                  : 'text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100'
              }`
            }
          >
            {tab.icon}
            {tab.label}
          </NavLink>
        ))}
      </nav>
    </div>
  )
}
