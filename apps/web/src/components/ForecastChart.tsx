import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  type TooltipContentProps,
  XAxis,
  YAxis,
} from 'recharts'
import type { HourForecast } from '../api/types.gen.ts'
import { mw, num } from '../format.ts'
import { useNarrow } from '../useNarrow.ts'
import styles from './Chart.module.css'

type Point = { hour: number; forecast: number; band: [number, number] | null }

// 24 means the end of the day, not midnight at its start.
const clock = (hour: number) => `${String(hour).padStart(2, '0')}:00`

function toPoints(hours: readonly HourForecast[]): Point[] {
  const points = hours.map((h, hour) => ({
    hour,
    forecast: h.forecast_mw,
    band:
      h.band_low_mw === null || h.band_high_mw === null
        ? null
        : ([h.band_low_mw, h.band_high_mw] as [number, number]),
  }))
  // Each value covers its whole hour: repeat the last one at 24:00 so its step is drawn.
  const last = points.at(-1)
  return last ? [...points, { ...last, hour: points.length }] : points
}

function Tip({ active, payload }: TooltipContentProps) {
  const point = payload[0]?.payload as Point | undefined
  if (!active || !point || point.hour >= 24) return null
  return (
    <div className={styles.tip}>
      <p className={styles.tipTitle}>
        {clock(point.hour)} to {clock(point.hour + 1)}
      </p>
      <p>Forecast {mw(point.forecast)}</p>
      {point.band && (
        <p>
          Band {num(point.band[0])} to {mw(point.band[1])}
        </p>
      )}
    </div>
  )
}

/** Tomorrow's hourly forecast as recorder-style steps, with the past-misses band behind it. */
export function ForecastChart({ hours }: { hours: readonly HourForecast[] }) {
  const narrow = useNarrow()
  const ticks = narrow ? [0, 6, 12, 18, 24] : [0, 3, 6, 9, 12, 15, 18, 21, 24]
  return (
    <div className={styles.frame}>
      <ResponsiveContainer width="100%" height={narrow ? 240 : 300}>
        <ComposedChart data={toPoints(hours)} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid fill="var(--paper)" stroke="var(--grid)" />
          <XAxis
            dataKey="hour"
            type="number"
            domain={[0, 24]}
            ticks={ticks}
            tickFormatter={clock}
            stroke="var(--grid-major)"
            tick={{ fill: 'var(--ink-2)', fontSize: 14 }}
          />
          <YAxis
            width={60}
            tickFormatter={num}
            stroke="var(--grid-major)"
            tick={{ fill: 'var(--ink-2)', fontSize: 14 }}
          />
          <Tooltip content={Tip} cursor={{ stroke: 'var(--ink-2)', strokeDasharray: '3 3' }} />
          <Area
            dataKey="band"
            type="stepAfter"
            stroke="none"
            fill="var(--pen-forecast)"
            fillOpacity={0.16}
            isAnimationActive={false}
          />
          <Line
            dataKey="forecast"
            type="stepAfter"
            stroke="var(--pen-forecast)"
            strokeWidth={2}
            dot={false}
            activeDot={false}
            isAnimationActive={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}
