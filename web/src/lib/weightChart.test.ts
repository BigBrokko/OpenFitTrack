import { describe, expect, it } from 'vitest'
import { buildChartData, isoDateFromTimestamp, yDomain } from './weightChart'

const points = [
  { date: '2026-10-01', weight_kg: 84, trend_kg: 84 },
  { date: '2026-11-10', weight_kg: 82, trend_kg: 82.6 },
]

describe('chart data', () => {
  it('uses UTC midnight timestamps, so the time between points is to scale', () => {
    const data = buildChartData(points)

    expect(data[0]).toEqual({ t: Date.UTC(2026, 9, 1), weight: 84, trend: 84 })
    expect(data[1].t - data[0].t).toBe(40 * 24 * 3600 * 1000)
  })

  it('turns a timestamp back into the same date', () => {
    expect(isoDateFromTimestamp(buildChartData(points)[1].t)).toBe('2026-11-10')
  })
})

describe('y axis range', () => {
  it('leaves room around the lowest and highest value', () => {
    expect(yDomain(buildChartData(points), null)).toEqual([81, 85])
  })

  it('includes the target weight, also when it is far below the data', () => {
    expect(yDomain(buildChartData(points), 75)).toEqual([74, 85])
    expect(yDomain(buildChartData(points), 90)).toEqual([81, 91])
  })

  it('looks at the trend as well as at the measurements', () => {
    const data = buildChartData([{ date: '2026-11-10', weight_kg: 80, trend_kg: 83 }])

    expect(yDomain(data, null)).toEqual([79, 84])
  })

  it('has a harmless default without data', () => {
    expect(yDomain([], null)).toEqual([0, 1])
  })
})
