/** Dutch number and date formatting. Dates are plain "YYYY-MM-DD" text, never Date objects
 * in the local time zone, so a day can not shift by one around midnight. */

export type ISODate = string

const MINUS = '−' // a real minus sign, not a hyphen

export function formatNumber(value: number, maxDecimals = 1): string {
  return new Intl.NumberFormat('nl-NL', { maximumFractionDigits: maxDecimals }).format(value)
}

/** Always the same number of decimals: "82,0". */
export function formatFixed(value: number, decimals = 1): string {
  return new Intl.NumberFormat('nl-NL', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value)
}

/** "+0,3" or "−0,2"; no sign when the value rounds to zero. */
export function formatSigned(value: number, decimals = 1): string {
  const digits = formatFixed(Math.abs(value), decimals)
  if (Number(Math.abs(value).toFixed(decimals)) === 0) return digits
  return `${value > 0 ? '+' : MINUS}${digits}`
}

/** What a person typed ("12,5" or "12.5") as a number; null when it is not a plain number. */
export function parseDecimal(text: string): number | null {
  const normalized = text.trim().replace(',', '.')
  return /^\d+(\.\d+)?$/.test(normalized) ? Number(normalized) : null
}

/** A number as text for an input field: decimal comma, no thousands separator. */
export function toInputText(value: number | null | undefined): string {
  return value === null || value === undefined ? '' : String(value).replace('.', ',')
}

export type Unit ='kcal' | 'g' | 'kg'

/** kcal as whole numbers, grams with at most one decimal. */
export function formatAmount(value: number, unit: Unit): string {
  return formatNumber(value, unit === 'kcal' ? 0 : 1)
}

// --- dates -----------------------------------------------------------------------------

function parts(date: ISODate): [number, number, number] {
  const [year, month, day] = date.split('-').map(Number)
  return [year, month, day]
}

function utc(date: ISODate): Date {
  const [year, month, day] = parts(date)
  return new Date(Date.UTC(year, month - 1, day))
}

/** The calendar date of a Date in the local time zone. */
export function toISODate(date: Date): ISODate {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

export function todayISO(): ISODate {
  return toISODate(new Date())
}

/** The text if it is a real calendar date ("2026-02-30" is not), otherwise null. */
export function parseISODate(text: string | null): ISODate | null {
  if (text === null || !/^\d{4}-\d{2}-\d{2}$/.test(text)) return null
  return utc(text).toISOString().slice(0, 10) === text ? text : null
}

export function addDays(date: ISODate, days: number): ISODate {
  const [year, month, day] = parts(date)
  return new Date(Date.UTC(year, month - 1, day + days)).toISOString().slice(0, 10)
}

function dateFormat(options: Intl.DateTimeFormatOptions) {
  return new Intl.DateTimeFormat('nl-NL', { ...options, timeZone: 'UTC' })
}

/** "woensdag 11 november" */
export function formatLongDate(date: ISODate): string {
  return dateFormat({ weekday: 'long', day: 'numeric', month: 'long' }).format(utc(date))
}

/** "11 november 2026" */
export function formatFullDate(date: ISODate): string {
  return dateFormat({ day: 'numeric', month: 'long', year: 'numeric' }).format(utc(date))
}

/** "11 nov" */
export function formatShortDate(date: ISODate): string {
  return dateFormat({ day: 'numeric', month: 'short' }).format(utc(date))
}
