import { useState, type FormEvent } from 'react'
import { UnauthorizedError } from '../api/data'
import { useCreateFood, useUpdateFood, writeErrorMessage } from '../api/mutations'
import type { FoodCandidate } from '../api/types'
import { parseDecimal, toInputText } from '../lib/format'
import { FormError, NumberField, TextField } from './Field'
import { primaryButton, secondaryButton } from './styles'

const MAX_MACROS_PER_100G = 100

/** Create your own food, or (with `food`) change one. Values are per 100 g. */
export function FoodForm({
  food,
  onSaved,
  onCancel,
}: {
  food?: FoodCandidate
  onSaved: (name: string) => void
  onCancel: () => void
}) {
  const [name, setName] = useState(food?.name ?? '')
  const [kcal, setKcal] = useState(toInputText(food?.kcal))
  const [protein, setProtein] = useState(toInputText(food?.protein_g))
  const [carbs, setCarbs] = useState(toInputText(food?.carbs_g))
  const [fat, setFat] = useState(toInputText(food?.fat_g))
  const create = useCreateFood()
  const update = useUpdateFood()
  const save = food ? update : create

  const [kcalN, proteinN, carbsN, fatN] = [kcal, protein, carbs, fat].map(parseDecimal)
  const values =
    name.trim() !== '' && kcalN !== null && proteinN !== null && carbsN !== null && fatN !== null
      ? { name: name.trim(), kcal: kcalN, protein_g: proteinN, carbs_g: carbsN, fat_g: fatN }
      : null
  const tooMuch = values !== null && values.protein_g + values.carbs_g + values.fat_g > MAX_MACROS_PER_100G

  function submit(event: FormEvent) {
    event.preventDefault()
    if (values === null || tooMuch) return
    const done = { onSuccess: () => onSaved(values.name) }
    if (food) update.mutate({ id: food.id, ...values }, done)
    else create.mutate(values, done)
  }

  return (
    <form onSubmit={submit} className="space-y-3 rounded-lg border border-slate-200 p-4 dark:border-slate-800">
      <h3 className="font-semibold">{food ? 'Product bewerken' : 'Nieuw product'}</h3>
      <p className="text-sm text-slate-600 dark:text-slate-400">Alle waarden zijn per 100 g.</p>
      <TextField label="Naam" value={name} onChange={setName} />
      <NumberField label="Energie" unit="kcal" value={kcal} onChange={setKcal} />
      <NumberField label="Eiwit" unit="g" value={protein} onChange={setProtein} />
      <NumberField label="Koolhydraten" unit="g" value={carbs} onChange={setCarbs} />
      <NumberField label="Vet" unit="g" value={fat} onChange={setFat} />
      {tooMuch && <FormError>Eiwit, koolhydraten en vet samen kunnen niet boven 100 g uitkomen.</FormError>}
      {save.error && !(save.error instanceof UnauthorizedError) && (
        <FormError>{writeErrorMessage(save.error)}</FormError>
      )}
      <div className="flex gap-2">
        <button type="submit" disabled={values === null || tooMuch || save.isPending} className={primaryButton}>
          Opslaan
        </button>
        <button type="button" onClick={onCancel} className={secondaryButton}>
          Annuleren
        </button>
      </div>
    </form>
  )
}
