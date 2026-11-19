import { describe, expect, it } from 'vitest'
import {
  addDays,
  formatAmount,
  formatFixed,
  formatFullDate,
  formatLongDate,
  formatNumber,
  formatShortDate,
  formatSigned,
  parseISODate,
  toISODate,
} from './format'

describe('numbers', () => {
  it('uses a decimal comma and a dot for thousands', () => {
    expect(formatNumber(1234.5)).toBe('1.234,5')
    expect(formatNumber(2000, 0)).toBe('2.000')
  })

  it('shows kcal as whole numbers and grams with at most one decimal', () => {
    expect(formatAmount(1105.8, 'kcal')).toBe('1.106')
    expect(formatAmount(38.94, 'g')).toBe('38,9')
    expect(formatAmount(36, 'g')).toBe('36')
  })

  it('keeps a fixed number of decimals', () => {
    expect(formatFixed(82)).toBe('82,0')
    expect(formatFixed(82.64)).toBe('82,6')
  })

  it('puts a sign on changes, with a real minus, and none on zero', () => {
    expect(formatSigned(0.3)).toBe('+0,3')
    expect(formatSigned(-0.2)).toBe('−0,2')
    expect(formatSigned(0)).toBe('0,0')
    expect(formatSigned(-0.04)).toBe('0,0') // rounds to zero: no sign
  })
})

describe('dates', () => {
  it('formats a local Date by its local calendar day', () => {
    expect(toISODate(new Date(2026, 10, 11, 23, 59))).toBe('2026-11-11')
    expect(toISODate(new Date(2026, 0, 1, 0, 0))).toBe('2026-01-01')
  })

  it('accepts only real calendar dates', () => {
    expect(parseISODate('2026-11-11')).toBe('2026-11-11')
    expect(parseISODate('2024-02-29')).toBe('2024-02-29') // leap day
    expect(parseISODate('2026-02-29')).toBeNull()
    expect(parseISODate('2026-13-01')).toBeNull()
    expect(parseISODate('11-11-2026')).toBeNull()
    expect(parseISODate('gisteren')).toBeNull()
    expect(parseISODate(null)).toBeNull()
  })

  it('adds and subtracts days across month and year borders', () => {
    expect(addDays('2026-11-11', 1)).toBe('2026-11-12')
    expect(addDays('2026-11-01', -1)).toBe('2026-10-31')
    expect(addDays('2026-12-31', 1)).toBe('2027-01-01')
    expect(addDays('2024-02-28', 1)).toBe('2024-02-29')
    expect(addDays('2026-03-29', 1)).toBe('2026-03-30') // a daylight saving change in the Netherlands
  })

  it('writes dates in Dutch', () => {
    expect(formatLongDate('2026-11-11')).toBe('woensdag 11 november')
    expect(formatFullDate('2026-11-11')).toBe('11 november 2026')
    expect(formatShortDate('2026-11-11')).toBe('11 nov')
  })
})
