import { useState, type FormEvent } from 'react'
import { UnauthorizedError } from '../api/data'
import { useSaveGoal, writeErrorMessage } from '../api/mutations'
import type { GoalInfo } from '../api/types'
import { parseDecimal, toInputText } from '../lib/format'
import { FormError, NumberField } from './Field'
import { primaryButton, secondaryButton } from './styles'

/** Set a new goal, valid from today. The form starts with the current goal. */
export function GoalForm({ current, onDone }: { current: GoalInfo | null; onDone: () => void }) {
  const [kcal, setKcal] = useState(toInputText(current?.kcal))
  const [protein, setProtein] = useState(toInputText(current?.protein_g))
  const [carbs, setCarbs] = useState(toInputText(current?.carbs_g))
  const [fat, setFat] = useState(toInputText(current?.fat_g))
  const [target, setTarget] = useState(toInputText(current?.target_weight_kg))
  const save = useSaveGoal()

  const [kcalValue, proteinValue, carbsValue, fatValue] = [kcal, protein, carbs, fat].map(
    parseDecimal,
  )
  const targetValue = target.trim() === '' ? null : parseDecimal(target)
  const targetOk = target.trim() === '' || (targetValue !== null && targetValue > 0)
  const goal =
    kcalValue !== null &&
    kcalValue > 0 &&
    proteinValue !== null &&
    carbsValue !== null &&
    fatValue !== null &&
    targetOk
      ? {
          kcal: kcalValue,
          protein_g: proteinValue,
          carbs_g: carbsValue,
          fat_g: fatValue,
          target_weight_kg: targetValue,
        }
      : null

  function submit(event: FormEvent) {
    event.preventDefault()
    if (goal) save.mutate(goal, { onSuccess: onDone })
  }

  return (
    <form
      onSubmit={submit}
      className="space-y-3 rounded-lg border border-slate-200 p-4 dark:border-slate-800"
    >
      <h3 className="font-semibold">Nieuw doel</h3>
      <p className="text-sm text-slate-600 dark:text-slate-400">
        Het nieuwe doel geldt vanaf vandaag. Eerdere dagen houden hun oude doel.
      </p>
      <NumberField label="Energie" unit="kcal" value={kcal} onChange={setKcal} />
      <NumberField label="Eiwit" unit="g" value={protein} onChange={setProtein} />
      <NumberField label="Koolhydraten" unit="g" value={carbs} onChange={setCarbs} />
      <NumberField label="Vet" unit="g" value={fat} onChange={setFat} />
      <NumberField label="Streefgewicht (optioneel)" unit="kg" value={target} onChange={setTarget} />
      {save.error && !(save.error instanceof UnauthorizedError) && (
        <FormError>{writeErrorMessage(save.error)}</FormError>
      )}
      <div className="flex gap-2">
        <button type="submit" disabled={goal === null || save.isPending} className={primaryButton}>
          Opslaan
        </button>
        <button type="button" onClick={onDone} className={secondaryButton}>
          Annuleren
        </button>
      </div>
    </form>
  )
}
