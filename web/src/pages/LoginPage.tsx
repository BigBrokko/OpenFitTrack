import { useState, type FormEvent } from 'react'
import { Navigate } from 'react-router'
import { LoginError, useLogin, useMe } from '../api/auth'

function errorMessage(error: unknown): string {
  if (!(error instanceof LoginError)) return 'Er ging iets mis. Probeer het opnieuw.'
  switch (error.kind) {
    case 'wrong-password':
      return 'Dat wachtwoord klopt niet.'
    case 'too-many-attempts': {
      if (error.retryAfterSeconds === null) return 'Te veel pogingen. Probeer het later opnieuw.'
      const minutes = Math.max(1, Math.ceil(error.retryAfterSeconds / 60))
      return `Te veel pogingen. Probeer het over ${minutes} ${minutes === 1 ? 'minuut' : 'minuten'} opnieuw.`
    }
    case 'network':
      return 'Geen verbinding met de server.'
    default:
      return 'Er ging iets mis. Probeer het opnieuw.'
  }
}

export function LoginPage() {
  const [password, setPassword] = useState('')
  const me = useMe()
  const login = useLogin()

  if (me.data?.authenticated) return <Navigate to="/dag" replace />

  function submit(event: FormEvent) {
    event.preventDefault()
    login.mutate(password)
  }

  return (
    <div className="flex min-h-dvh items-center justify-center bg-white p-6 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      <form onSubmit={submit} className="w-full max-w-sm space-y-4">
        <h1 className="text-2xl font-semibold">OpenFitTrack</h1>

        <div className="space-y-1">
          <label htmlFor="password" className="block text-sm font-medium">
            Wachtwoord
          </label>
          <input
            id="password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-base dark:border-slate-700 dark:bg-slate-900"
          />
        </div>

        {login.isError && (
          <p role="alert" className="text-sm text-red-700 dark:text-red-400">
            {errorMessage(login.error)}
          </p>
        )}

        <button
          type="submit"
          disabled={password === '' || login.isPending}
          className="w-full rounded-md bg-green-700 px-4 py-2 font-medium text-white hover:bg-green-800 disabled:opacity-50"
        >
          {login.isPending ? 'Bezig…' : 'Inloggen'}
        </button>
      </form>
    </div>
  )
}
