import { useState, type FormEvent } from 'react'
import { UnauthorizedError } from '../api/data'
import { useSaveWeight, writeErrorMessage } from '../api/mutations'
import { parseDecimal, parseISODate, todayISO } from '../lib/format'
import { DateField, FormError, NumberField } from './Field'
import { primaryButton } from './styles'

const MIN_KG = 20
const MAX_KG = 400

/** Log your weight for today or an earlier day. A weight already logged that day is replaced. */
export function WeightForm() {
  const today = todayISO()
  const [date, setDate] = useState(today)
  const [kg, setKg] = useState('')
  const save = useSaveWeight()

  const value = parseDecimal(kg)
  const validKg = value !== null && value >= MIN_KG && value <= MAX_KG
  const validDate = parseISODate(date) !== null && date <= today

  function submit(event: FormEvent) {
    event.preventDefault()
    if (value === null || !validKg || !validDate) return
    save.mutate({ date, weight_kg: value }, { onSuccess: () => setKg('') })
  }

  return (
    <form
      onSubmit={submit}
      className="space-y-3 rounded-lg border border-slate-200 p-4 dark:border-slate-800"
    >
      <h3 className="font-semibold">Gewicht invoeren</h3>
      <DateField label="Datum" value={date} max={today} onChange={setDate} />
      <NumberField label="Gewicht" unit="kg" value={kg} onChange={setKg} />
      {kg !== '' && !validKg && (
        <FormError>
          Vul een gewicht tussen {MIN_KG} en {MAX_KG} kg in.
        </FormError>
      )}
      {save.error && !(save.error instanceof UnauthorizedError) && (
        <FormError>{writeErrorMessage(save.error)}</FormError>
      )}
      {save.isSuccess && <p role="status" className="text-sm text-green-700 dark:text-green-400">Opgeslagen.</p>}
      <button
        type="submit"
        disabled={!validKg || !validDate || save.isPending}
        className={primaryButton}
      >
        Opslaan
      </button>
    </form>
  )
}
