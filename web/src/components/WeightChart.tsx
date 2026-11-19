import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { WeightPoint } from '../api/types'
import { formatFullDate, formatNumber, formatShortDate } from '../lib/format'
import { buildChartData, isoDateFromTimestamp, yDomain } from '../lib/weightChart'

const TREND_COLOR = '#16a34a'
const POINT_COLOR = '#94a3b8'
const TARGET_COLOR = '#d97706'

/** Measurements as dots, the trend as a line, and the target weight as a dashed line. */
export function WeightChart({
  points,
  target,
}: {
  points: WeightPoint[]
  target: number | null
}) {
  const data = buildChartData(points)

  return (
    <figure className="space-y-2">
      <div
        role="img"
        aria-label="Grafiek van je gewicht en de trend"
        className="h-64 text-slate-500 dark:text-slate-400"
      >
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -8 }}>
            <CartesianGrid strokeDasharray="3 3" strokeOpacity={0.3} vertical={false} />
            <XAxis
              dataKey="t"
              type="number"
              scale="time"
              domain={['dataMin', 'dataMax']}
              tickFormatter={(t: number) => formatShortDate(isoDateFromTimestamp(t))}
              tick={{ fill: 'currentColor', fontSize: 12 }}
              minTickGap={32}
            />
            <YAxis
              domain={yDomain(data, target)}
              tickFormatter={(value: number) => formatNumber(value, 0)}
              tick={{ fill: 'currentColor', fontSize: 12 }}
              width={40}
            />
            <Tooltip
              labelFormatter={(t) => formatFullDate(isoDateFromTimestamp(Number(t)))}
              formatter={(value) => `${formatNumber(Number(value))} kg`}
              contentStyle={{ backgroundColor: '#0f172a', border: 'none', borderRadius: 8 }}
              labelStyle={{ color: '#f8fafc' }}
              itemStyle={{ color: '#e2e8f0' }}
            />
            {target !== null && (
              <ReferenceLine
                y={target}
                stroke={TARGET_COLOR}
                strokeDasharray="6 4"
                label={{
                  value: `Streefgewicht ${formatNumber(target)} kg`,
                  position: 'insideBottomRight',
                  fill: TARGET_COLOR,
                  fontSize: 12,
                }}
              />
            )}
            <Line
              dataKey="weight"
              name="Gewicht"
              stroke="none"
              dot={{ r: 3, fill: POINT_COLOR, stroke: 'none' }}
              activeDot={{ r: 5 }}
              isAnimationActive={false}
            />
            <Line
              dataKey="trend"
              name="Trend"
              stroke={TREND_COLOR}
              strokeWidth={2.5}
              dot={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <figcaption className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-600 dark:text-slate-400">
        <span>
          <span style={{ color: POINT_COLOR }}>●</span> Gewicht
        </span>
        <span>
          <span style={{ color: TREND_COLOR }}>━</span> Trend
        </span>
        {target !== null && (
          <span>
            <span style={{ color: TARGET_COLOR }}>┅</span> Streefgewicht
          </span>
        )}
      </figcaption>
    </figure>
  )
}
