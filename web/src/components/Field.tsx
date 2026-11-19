import { useId } from 'react'

const inputClass =
  'w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-base dark:border-slate-700 dark:bg-slate-900'

interface FieldProps {
  label: string
  value: string
  onChange: (value: string) => void
}

export function TextField({ label, value, onChange }: FieldProps) {
  const id = useId()
  return (
    <div className="space-y-1">
      <label htmlFor={id} className="block text-sm font-medium">
        {label}
      </label>
      <input
        id={id}
        type="text"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className={inputClass}
      />
    </div>
  )
}

/** A number typed with a decimal comma or point; `unit` is shown after the label. */
export function NumberField({ label, unit, value, onChange }: FieldProps & { unit: string }) {
  const id = useId()
  return (
    <div className="space-y-1">
      <label htmlFor={id} className="block text-sm font-medium">
        {label} <span className="font-normal text-slate-600 dark:text-slate-400">({unit})</span>
      </label>
      <input
        id={id}
        type="text"
        inputMode="decimal"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className={inputClass}
      />
    </div>
  )
}

export function DateField({
  label,
  value,
  max,
  onChange,
}: FieldProps & { max: string }) {
  const id = useId()
  return (
    <div className="space-y-1">
      <label htmlFor={id} className="block text-sm font-medium">
        {label}
      </label>
      <input
        id={id}
        type="date"
        value={value}
        max={max}
        onChange={(event) => onChange(event.target.value)}
        className={inputClass}
      />
    </div>
  )
}

export function FormError({ children }: { children: React.ReactNode }) {
  return (
    <p role="alert" className="text-sm text-red-700 dark:text-red-400">
      {children}
    </p>
  )
}
