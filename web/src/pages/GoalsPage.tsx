import { UnauthorizedError, useGoals } from '../api/data'
import type { GoalInfo } from '../api/types'
import { ErrorMessage, Hint, LoadingMessage } from '../components/QueryStatus'
import { formatAmount, formatFullDate, formatNumber } from '../lib/format'

export function GoalsPage() {
  const goals = useGoals()

  return (
    <section className="space-y-5">
      <h2 className="text-xl font-semibold">Doelen</h2>

      {goals.isPending && <LoadingMessage />}
      {goals.isError && !(goals.error instanceof UnauthorizedError) && (
        <ErrorMessage onRetry={() => goals.refetch()} />
      )}
      {goals.data && (
        <>
          {goals.data.current === null ? (
            <Hint>Je hebt nog geen doel ingesteld. Instellen kan voorlopig in de Streamlit-app.</Hint>
          ) : (
            <CurrentGoal goal={goals.data.current} />
          )}

          {goals.data.history.length > 0 && (
            <div className="space-y-2">
              <h3 className="font-semibold">Geschiedenis</h3>
              <ul className="divide-y divide-slate-200 dark:divide-slate-800">
                {goals.data.history.map((goal) => (
                  <li key={goal.valid_from} className="py-2">
                    <p className="flex items-center gap-2 font-medium">
                      {formatFullDate(goal.valid_from)}
                      {goal.valid_from === goals.data.current?.valid_from && (
                        <span className="rounded bg-green-100 px-1.5 py-0.5 text-xs font-medium text-green-800 dark:bg-green-950 dark:text-green-300">
                          Huidig
                        </span>
                      )}
                    </p>
                    <p className="text-sm text-slate-600 dark:text-slate-400">{summary(goal)}</p>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}
    </section>
  )
}

function summary(goal: GoalInfo): string {
  const parts = [
    `${formatAmount(goal.kcal, 'kcal')} kcal`,
    `${formatAmount(goal.protein_g, 'g')} g eiwit`,
    `${formatAmount(goal.carbs_g, 'g')} g koolhydraten`,
    `${formatAmount(goal.fat_g, 'g')} g vet`,
  ]
  if (goal.target_weight_kg !== null && goal.target_weight_kg !== undefined) {
    parts.push(`streefgewicht ${formatNumber(goal.target_weight_kg)} kg`)
  }
  return parts.join(' · ')
}

function CurrentGoal({ goal }: { goal: GoalInfo }) {
  const rows: [string, string][] = [
    ['Energie', `${formatAmount(goal.kcal, 'kcal')} kcal`],
    ['Eiwit', `${formatAmount(goal.protein_g, 'g')} g`],
    ['Koolhydraten', `${formatAmount(goal.carbs_g, 'g')} g`],
    ['Vet', `${formatAmount(goal.fat_g, 'g')} g`],
    [
      'Streefgewicht',
      goal.target_weight_kg === null || goal.target_weight_kg === undefined
        ? '—'
        : `${formatNumber(goal.target_weight_kg)} kg`,
    ],
  ]

  return (
    <div className="rounded-lg border border-slate-200 p-4 dark:border-slate-800">
      <p className="text-sm text-slate-600 dark:text-slate-400">
        Huidig doel, sinds {formatFullDate(goal.valid_from)}
      </p>
      <dl className="mt-3 divide-y divide-slate-200 dark:divide-slate-800">
        {rows.map(([label, value]) => (
          <div key={label} className="flex justify-between py-2">
            <dt className="text-slate-600 dark:text-slate-400">{label}</dt>
            <dd className="font-semibold">{value}</dd>
          </div>
        ))}
      </dl>
    </div>
  )
}
