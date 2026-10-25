import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  type TooltipContentProps,
  XAxis,
  YAxis,
} from 'recharts'
import type { HistoryPoint } from '../api/types.gen.ts'
import { dayTick, miss, mw, num, ukDayTime, ukTime } from '../format.ts'
import { useNarrow } from '../useNarrow.ts'
import styles from './Chart.module.css'

type Point = { t: number; at: string; forecast: number; actual: number; miss: number; end: boolean }

const HALF_HOUR = 30 * 60 * 1000
const MW_STEP = 5000

function toPoints(history: readonly HistoryPoint[]): Point[] {
  const points = history.map((p) => ({
    t: Date.parse(p.start_time),
    at: p.start_time,
    forecast: p.forecast_mw,
    actual: p.actual_mw,
    miss: p.miss_mw,
    end: false,
  }))
  // Each value covers its half-hour: repeat the last one at its end so its step is drawn.
  const last = points.at(-1)
  return last ? [...points, { ...last, t: last.t + HALF_HOUR, end: true }] : points
}

function Tip({ active, payload }: TooltipContentProps) {
  const point = payload[0]?.payload as Point | undefined
  if (!active || !point || point.end) return null
  const { text, words } = miss(point.miss)
  return (
    <div className={styles.tip}>
      <p className={styles.tipTitle}>{ukDayTime(point.at)}</p>
      <p>Forecast {mw(point.forecast)}</p>
      <p>Actual {mw(point.actual)}</p>
      <p>
        Miss {text}, {words}
      </p>
    </div>
  )
}

/** Forecast and actual as two recorder pens: solid for the forecast, dashed for the actual. */
export function HistoryChart({ history, days }: { history: readonly HistoryPoint[]; days: number }) {
  const narrow = useNarrow()
  const points = toPoints(history)
  // A tick at each UK midnight, thinned so labels never crowd.
  const every = Math.max(1, Math.ceil(days / (narrow ? 3 : 7)))
  const midnights = points.filter((p) => !p.end && ukTime(p.at) === '00:00')
  const ticks = midnights.filter((_, i) => i % every === 0).map((p) => p.t)
  const dayOf = new Map(midnights.map((p) => [p.t, dayTick(p.at.slice(0, 10))]))
  // Round 5,000 MW steps read faster than whatever the data's maximum happens to divide into.
  const top = Math.ceil(Math.max(...points.map((p) => Math.max(p.forecast, p.actual)), 1) / MW_STEP) * MW_STEP
  const mwTicks = Array.from({ length: top / MW_STEP + 1 }, (_, i) => i * MW_STEP)
  return (
    <div className={styles.frame}>
      <ResponsiveContainer width="100%" height={narrow ? 220 : 280}>
        <LineChart data={points} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid fill="var(--paper)" stroke="var(--grid)" />
          <XAxis
            dataKey="t"
            type="number"
            scale="time"
            domain={['dataMin', 'dataMax']}
            ticks={ticks}
            tickFormatter={(t: number) => dayOf.get(t) ?? ''}
            stroke="var(--grid-major)"
            tick={{ fill: 'var(--ink-2)', fontSize: 14 }}
          />
          <YAxis
            width={60}
            domain={[0, top]}
            ticks={mwTicks}
            tickFormatter={num}
            stroke="var(--grid-major)"
            tick={{ fill: 'var(--ink-2)', fontSize: 14 }}
          />
          <Tooltip content={Tip} cursor={{ stroke: 'var(--ink-2)', strokeDasharray: '3 3' }} />
          <Line
            dataKey="actual"
            type="stepAfter"
            stroke="var(--pen-actual)"
            strokeWidth={2}
            strokeDasharray="5 3"
            dot={false}
            activeDot={false}
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
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
