import { useSearchParams } from 'react-router'
import { UnauthorizedError, useDay } from '../api/data'
import type { DaySummary, ProgressItem } from '../api/types'
import { ProgressBar } from '../components/ProgressBar'
import { ErrorMessage, Hint, LoadingMessage } from '../components/QueryStatus'
import {
  addDays,
  formatAmount,
  formatLongDate,
  parseISODate,
  todayISO,
  type ISODate,
  type Unit,
} from '../lib/format'

const NUTRIENTS = [
  { key: 'kcal', label: 'Energie', unit: 'kcal' },
  { key: 'protein_g', label: 'Eiwit', unit: 'g' },
  { key: 'carbs_g', label: 'Koolhydraten', unit: 'g' },
  { key: 'fat_g', label: 'Vet', unit: 'g' },
] as const

const stepButton =
  'flex min-h-11 min-w-11 items-center justify-center rounded-md border border-slate-300 text-xl ' +
  'hover:bg-slate-100 disabled:opacity-40 dark:border-slate-700 dark:hover:bg-slate-900'

export function DayPage() {
  const [params, setParams] = useSearchParams()
  const today = todayISO()
  const date = parseISODate(params.get('date')) ?? today
  const day = useDay(date)

  // Today is the default, so its URL stays clean; other days keep the date in the URL.
  const goTo = (next: ISODate) => setParams(next === today ? {} : { date: next })

  return (
    <section className="space-y-5">
      <h2 className="text-xl font-semibold">Dag</h2>

      <div className="flex items-center justify-between gap-2">
        <button
          type="button"
          aria-label="Vorige dag"
          onClick={() => goTo(addDays(date, -1))}
          className={stepButton}
        >
          ‹
        </button>
        <div className="text-center">
          <p className="font-medium first-letter:uppercase">{formatLongDate(date)}</p>
          {date !== today && (
            <button
              type="button"
              onClick={() => goTo(today)}
              className="text-sm font-medium text-green-700 dark:text-green-400"
            >
              Vandaag
            </button>
          )}
        </div>
        <button
          type="button"
          aria-label="Volgende dag"
          disabled={date >= today}
          onClick={() => goTo(addDays(date, 1))}
          className={stepButton}
        >
          ›
        </button>
      </div>

      {day.isPending && <LoadingMessage />}
      {day.isError && !(day.error instanceof UnauthorizedError) && (
        <ErrorMessage onRetry={() => day.refetch()} />
      )}
      {day.data && <DayContent data={day.data} />}
    </section>
  )
}

function DayContent({ data }: { data: DaySummary }) {
  return (
    <>
      {data.goal === null && <Hint>Voor deze dag is geen doel ingesteld.</Hint>}

      <div className="grid grid-cols-2 gap-3">
        {NUTRIENTS.map(({ key, label, unit }) => (
          <NutrientCard
            key={key}
            label={label}
            unit={unit}
            eaten={data.totals[key]}
            progress={data.progress?.[key]}
          />
        ))}
      </div>

      <div className="space-y-2">
        <h3 className="font-semibold">Gegeten</h3>
        {data.entries.length === 0 ? (
          // The API's own note is written for AI models, in English; the app says it in Dutch.
          <Hint>Voor deze dag is niets gelogd. Dat betekent niet dat je niets hebt gegeten.</Hint>
        ) : (
          <ul className="divide-y divide-slate-200 dark:divide-slate-800">
            {data.entries.map((entry, index) => (
              <li key={index} className="flex items-baseline justify-between gap-3 py-2">
                <div className="min-w-0">
                  <p className="truncate font-medium">{entry.food}</p>
                  <p className="text-sm text-slate-600 dark:text-slate-400">
                    {entry.time} · {formatAmount(entry.amount_g, 'g')} g
                  </p>
                </div>
                <p className="shrink-0 text-sm font-medium">
                  {formatAmount(entry.nutrients.kcal, 'kcal')} kcal
                </p>
              </li>
            ))}
          </ul>
        )}
      </div>
    </>
  )
}

function remainingText(progress: ProgressItem, unit: Unit): string {
  return progress.remaining >= 0
    ? `nog ${formatAmount(progress.remaining, unit)} ${unit}`
    : `+${formatAmount(-progress.remaining, unit)} ${unit} over`
}

function NutrientCard({
  label,
  unit,
  eaten,
  progress,
}: {
  label: string
  unit: Unit
  eaten: number
  progress: ProgressItem | undefined
}) {
  return (
    <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-800">
      <p className="text-sm text-slate-600 dark:text-slate-400">{label}</p>
      <p className="mt-1 text-2xl font-semibold">
        {formatAmount(eaten, unit)} <span className="text-sm font-normal">{unit}</span>
      </p>
      {progress && (
        <div className="mt-2 space-y-2">
          <ProgressBar percent={progress.percent} label={`${label} ten opzichte van je doel`} />
          <p className="text-xs text-slate-600 dark:text-slate-400">
            van {formatAmount(progress.goal, unit)} · {remainingText(progress, unit)}
          </p>
        </div>
      )}
    </div>
  )
}
