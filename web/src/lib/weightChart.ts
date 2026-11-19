import type { WeightPoint } from '../api/types'
import type { ISODate } from './format'

export interface ChartPoint {
  /** Milliseconds since 1970 (UTC midnight), so gaps between measurements are drawn to scale. */
  t: number
  weight: number
  trend: number
}

export function buildChartData(points: WeightPoint[]): ChartPoint[] {
  return points.map((point) => {
    const [year, month, day] = point.date.split('-').map(Number)
    return {
      t: Date.UTC(year, month - 1, day),
      weight: point.weight_kg,
      trend: point.trend_kg,
    }
  })
}

export function isoDateFromTimestamp(t: number): ISODate {
  return new Date(t).toISOString().slice(0, 10)
}

/** The visible weight range: all points and the target, with half a kilo of room. */
export function yDomain(points: ChartPoint[], target: number | null): [number, number] {
  const values = points.flatMap((point) => [point.weight, point.trend])
  if (target !== null) values.push(target)
  if (values.length === 0) return [0, 1]
  return [Math.floor(Math.min(...values) - 0.5), Math.ceil(Math.max(...values) + 0.5)]
}
