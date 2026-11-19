import { useState, type FormEvent } from 'react'
import { UnauthorizedError } from '../api/data'
import { useDeleteEntry, useUpdateEntry, writeErrorMessage } from '../api/mutations'
import type { LoggedEntry } from '../api/types'
import { formatAmount, parseDecimal, toInputText } from '../lib/format'
import { FormError, NumberField } from './Field'
import { primaryButton, secondaryButton } from './styles'

type Mode = 'view' | 'edit' | 'confirm-delete'

/** One logged line: tap "Wijzig" to correct the amount or to delete it. */
export function EntryRow({ entry }: { entry: LoggedEntry }) {
  const [mode, setMode] = useState<Mode>('view')
  const [amount, setAmount] = useState(toInputText(entry.amount_g))
  const update = useUpdateEntry()
  const remove = useDeleteEntry()

  const grams = parseDecimal(amount)
  const error = update.error ?? remove.error
  const busy = update.isPending || remove.isPending

  function cancel() {
    setMode('view')
    setAmount(toInputText(entry.amount_g))
    update.reset()
    remove.reset()
  }

  function save(event: FormEvent) {
    event.preventDefault()
    if (grams === null || grams <= 0) return
    update.mutate({ id: entry.id, amount_g: grams }, { onSuccess: () => setMode('view') })
  }

  return (
    <li className="py-2">
      <div className="flex items-baseline justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate font-medium">{entry.food}</p>
          <p className="text-sm text-slate-600 dark:text-slate-400">
            {entry.time} · {formatAmount(entry.amount_g, 'g')} g
          </p>
        </div>
        <p className="shrink-0 text-sm font-medium">
          {formatAmount(entry.nutrients.kcal, 'kcal')} kcal
        </p>
      </div>

      {mode === 'view' && (
        <button
          type="button"
          aria-label={`Wijzig ${entry.food}`}
          onClick={() => setMode('edit')}
          className="mt-1 min-h-11 text-sm font-medium text-green-700 dark:text-green-400"
        >
          Wijzig
        </button>
      )}

      {mode === 'edit' && (
        <form onSubmit={save} className="mt-2 space-y-3">
          <NumberField label="Hoeveelheid" unit="g" value={amount} onChange={setAmount} />
          {amount !== '' && (grams === null || grams <= 0) && (
            <FormError>Vul een hoeveelheid groter dan 0 in.</FormError>
          )}
          {error && !(error instanceof UnauthorizedError) && (
            <FormError>{writeErrorMessage(error)}</FormError>
          )}
          <div className="flex flex-wrap gap-2">
            <button
              type="submit"
              disabled={grams === null || grams <= 0 || busy}
              className={primaryButton}
            >
              Opslaan
            </button>
            <button type="button" onClick={cancel} className={secondaryButton}>
              Annuleren
            </button>
            <button
              type="button"
              onClick={() => setMode('confirm-delete')}
              className="min-h-11 px-2 font-medium text-red-700 dark:text-red-400"
            >
              Verwijderen
            </button>
          </div>
        </form>
      )}

      {mode === 'confirm-delete' && (
        <div className="mt-2 space-y-3">
          <p>
            Verwijder {entry.food} ({formatAmount(entry.amount_g, 'g')} g) van deze dag?
          </p>
          {error && !(error instanceof UnauthorizedError) && (
            <FormError>{writeErrorMessage(error)}</FormError>
          )}
          <div className="flex gap-2">
            <button
              type="button"
              disabled={busy}
              onClick={() => remove.mutate(entry.id)}
              className="min-h-11 rounded-md bg-red-700 px-4 font-medium text-white hover:bg-red-800 disabled:opacity-50"
            >
              Ja, verwijderen
            </button>
            <button type="button" onClick={cancel} className={secondaryButton}>
              Annuleren
            </button>
          </div>
        </div>
      )}
    </li>
  )
}
