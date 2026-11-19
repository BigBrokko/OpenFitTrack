import { lazy, Suspense } from 'react'
import { useSearchParams } from 'react-router'
import { UnauthorizedError, useWeight } from '../api/data'
import type { WeightTrend } from '../api/types'
import { ErrorMessage, Hint, LoadingMessage } from '../components/QueryStatus'
import { formatFixed, formatSigned } from '../lib/format'

// The chart library is large: load it only when this page needs it, so the login screen and
// the other pages start faster on a phone.
const WeightChart = lazy(() =>
  import('../components/WeightChart').then((module) => ({ default: module.WeightChart })),
)

const RANGES = [30, 90, 180, 365] as const
const DEFAULT_DAYS = 90

export function WeightPage() {
  const [params, setParams] = useSearchParams()
  const requested = Number(params.get('dagen'))
  const days = (RANGES as readonly number[]).includes(requested) ? requested : DEFAULT_DAYS
  const weight = useWeight(days)

  const choose = (next: number) => setParams(next === DEFAULT_DAYS ? {} : { dagen: String(next) })

  return (
    <section className="space-y-5">
      <h2 className="text-xl font-semibold">Gewicht</h2>

      {weight.isPending && <LoadingMessage />}
      {weight.isError && !(weight.error instanceof UnauthorizedError) && (
        <ErrorMessage onRetry={() => weight.refetch()} />
      )}
      {weight.data && (
        <>
          <Stats data={weight.data} />
          {weight.data.measurements_total === 0 ? (
            <Hint>
              Nog geen gewicht gelogd. Invoeren kan voorlopig in de Streamlit-app.
            </Hint>
          ) : (
            <>
              <div role="group" aria-label="Periode" className="grid grid-cols-4 gap-2">
                {RANGES.map((range) => (
                  <button
                    key={range}
                    type="button"
                    aria-pressed={range === days}
                    onClick={() => choose(range)}
                    className={`min-h-11 rounded-md border text-sm font-medium ${
                      range === days
                        ? 'border-green-700 bg-green-700 text-white'
                        : 'border-slate-300 hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-900'
                    }`}
                  >
                    {range} dagen
                  </button>
                ))}
              </div>
              {weight.data.points.length === 0 ? (
                <Hint>Geen metingen in de afgelopen {days} dagen.</Hint>
              ) : (
                <Suspense fallback={<LoadingMessage />}>
                  <WeightChart points={weight.data.points} target={weight.data.target_weight_kg} />
                </Suspense>
              )}
            </>
          )}
        </>
      )}
    </section>
  )
}

function Stats({ data }: { data: WeightTrend }) {
  const dash = '—'
  return (
    <dl className="grid grid-cols-3 gap-2">
      <Stat
        label="Laatste meting"
        value={data.latest_weight_kg === null ? dash : `${formatFixed(data.latest_weight_kg)} kg`}
      />
      <Stat
        label="Trend"
        value={data.latest_trend_kg === null ? dash : `${formatFixed(data.latest_trend_kg)} kg`}
      />
      <Stat
        label="Trend, 7 dagen"
        value={
          data.trend_change_7d_kg === null ? dash : `${formatSigned(data.trend_change_7d_kg)} kg`
        }
      />
    </dl>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-800">
      <dt className="text-xs text-slate-600 dark:text-slate-400">{label}</dt>
      <dd className="mt-1 text-lg font-semibold">{value}</dd>
    </div>
  )
}
