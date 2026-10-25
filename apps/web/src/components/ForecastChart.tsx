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
import { hourLabel, mw, num } from '../format.ts'
import { useNarrow } from '../useNarrow.ts'
import styles from './Chart.module.css'
import { AXIS, CURSOR, GRID, MARGIN, PENS, STEPS, Y_AXIS } from './chartStyle.ts'

type Point = { hour: number; forecast: number; band: [number, number] | null }

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
        {hourLabel(point.hour)} to {hourLabel(point.hour + 1)}
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
        <ComposedChart data={toPoints(hours)} margin={MARGIN}>
          <CartesianGrid {...GRID} />
          <XAxis
            dataKey="hour"
            type="number"
            domain={[0, 24]}
            ticks={ticks}
            tickFormatter={hourLabel}
            {...AXIS}
          />
          <YAxis {...Y_AXIS} />
          <Tooltip content={Tip} cursor={CURSOR} />
          <Area
            dataKey="band"
            type="stepAfter"
            stroke="none"
            fill={PENS.forecast.stroke}
            fillOpacity={0.16}
            isAnimationActive={false}
          />
          <Line dataKey="forecast" {...STEPS} {...PENS.forecast} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}
