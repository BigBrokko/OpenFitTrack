export function LoadingMessage() {
  return <p className="text-slate-500 dark:text-slate-400">Laden…</p>
}

export function ErrorMessage({ onRetry }: { onRetry: () => void }) {
  return (
    <div role="alert" className="space-y-3">
      <p>Kon de gegevens niet laden.</p>
      <button
        type="button"
        onClick={onRetry}
        className="min-h-11 rounded-md bg-green-700 px-4 font-medium text-white hover:bg-green-800"
      >
        Opnieuw proberen
      </button>
    </div>
  )
}

export function Hint({ children }: { children: React.ReactNode }) {
  return (
    <p className="rounded-lg bg-slate-100 p-3 text-sm text-slate-700 dark:bg-slate-900 dark:text-slate-300">
      {children}
    </p>
  )
}
