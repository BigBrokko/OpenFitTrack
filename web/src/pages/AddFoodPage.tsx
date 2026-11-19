import { useState, type FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router'
import { UnauthorizedError } from '../api/data'
import { useFoodSearch, useLogFood, writeErrorMessage } from '../api/mutations'
import type { FoodCandidate } from '../api/types'
import { FoodForm } from '../components/FoodForm'
import { FormError, NumberField } from '../components/Field'
import { ErrorMessage, Hint, LoadingMessage } from '../components/QueryStatus'
import { primaryButton, secondaryButton } from '../components/styles'
import { formatAmount, formatLongDate, parseDecimal, parseISODate, todayISO } from '../lib/format'

type Form = { kind: 'new' } | { kind: 'edit'; food: FoodCandidate }

const MANUAL = 'manual'

export function AddFoodPage() {
  const [params] = useSearchParams()
  const today = todayISO()
  const date = parseISODate(params.get('date')) ?? today
  const backPath = date === today ? '/dag' : `/dag?date=${date}`

  const [query, setQuery] = useState('')
  const [pickedId, setPickedId] = useState<number | null>(null)
  const [form, setForm] = useState<Form | null>(null)
  const search = useFoodSearch(query)

  return (
    <section className="space-y-5">
      <Link to={backPath} className="inline-flex min-h-11 items-center text-green-700 dark:text-green-400">
        ‹ Terug naar de dag
      </Link>
      <div>
        <h2 className="text-xl font-semibold">Eten toevoegen</h2>
        <p className="text-sm text-slate-600 dark:text-slate-400">
          Voor {formatLongDate(date)}
        </p>
      </div>

      {form ? (
        <FoodForm
          // a fresh form for each food, so values of the previous one do not linger
          key={form.kind === 'edit' ? form.food.id : 'new'}
          food={form.kind === 'edit' ? form.food : undefined}
          onSaved={(name) => {
            setForm(null)
            setQuery(name) // show the saved food in the results
          }}
          onCancel={() => setForm(null)}
        />
      ) : (
        <>
          <div className="space-y-1">
            <label htmlFor="food-query" className="block text-sm font-medium">
              Zoek een voedingsmiddel
            </label>
            <input
              id="food-query"
              type="search"
              value={query}
              onChange={(event) => {
                setQuery(event.target.value)
                setPickedId(null)
              }}
              className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-base dark:border-slate-700 dark:bg-slate-900"
            />
          </div>

          {search.isFetching && <LoadingMessage />}
          {search.isError && !(search.error instanceof UnauthorizedError) && (
            <ErrorMessage onRetry={() => search.refetch()} />
          )}
          {search.data && search.data.results.length === 0 && (
            <Hint>Niets gevonden voor “{search.data.query}”. Je kunt het zelf toevoegen.</Hint>
          )}
          {search.data && search.data.results.length > 0 && (
            <ul className="divide-y divide-slate-200 dark:divide-slate-800">
              {search.data.results.map((food) => (
                <FoodResult
                  key={food.id}
                  food={food}
                  date={date}
                  today={today}
                  picked={pickedId === food.id}
                  onPick={() => setPickedId(food.id)}
                  onEdit={() => setForm({ kind: 'edit', food })}
                />
              ))}
            </ul>
          )}

          <button type="button" onClick={() => setForm({ kind: 'new' })} className={secondaryButton}>
            Nieuw product maken
          </button>
        </>
      )}
    </section>
  )
}

function FoodResult({
  food,
  date,
  today,
  picked,
  onPick,
  onEdit,
}: {
  food: FoodCandidate
  date: string
  today: string
  picked: boolean
  onPick: () => void
  onEdit: () => void
}) {
  const navigate = useNavigate()
  const [amount, setAmount] = useState('100')
  const log = useLogFood()
  const grams = parseDecimal(amount)

  function submit(event: FormEvent) {
    event.preventDefault()
    if (grams === null || grams <= 0) return
    log.mutate(
      {
        food_id: food.id,
        amount_g: grams,
        // Today: the server uses the current time. Another day: noon, so it stays on that day.
        logged_at: date === today ? undefined : `${date}T12:00:00`,
      },
      { onSuccess: () => navigate(date === today ? '/dag' : `/dag?date=${date}`) },
    )
  }

  return (
    <li className="py-2">
      <button
        type="button"
        onClick={onPick}
        aria-expanded={picked}
        className="block min-h-11 w-full text-left"
      >
        <span className="block font-medium">{food.name}</span>
        <span className="block text-sm text-slate-600 dark:text-slate-400">
          per 100 g: {formatAmount(food.kcal, 'kcal')} kcal · {formatAmount(food.protein_g, 'g')} g
          eiwit · {formatAmount(food.carbs_g, 'g')} g koolhydraten · {formatAmount(food.fat_g, 'g')}{' '}
          g vet
        </span>
      </button>

      {picked && (
        <form onSubmit={submit} className="mt-2 space-y-3">
          <NumberField label="Hoeveelheid" unit="g" value={amount} onChange={setAmount} />
          {amount !== '' && (grams === null || grams <= 0) && (
            <FormError>Vul een hoeveelheid groter dan 0 in.</FormError>
          )}
          {log.error && !(log.error instanceof UnauthorizedError) && (
            <FormError>{writeErrorMessage(log.error)}</FormError>
          )}
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={grams === null || grams <= 0 || log.isPending}
              className={primaryButton}
            >
              Toevoegen
            </button>
            {food.source === MANUAL && (
              <button type="button" onClick={onEdit} className={secondaryButton}>
                Product bewerken
              </button>
            )}
          </div>
        </form>
      )}
    </li>
  )
}
