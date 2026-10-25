import { lazy, Suspense, useState } from 'react'
import type { HistoryPoint } from '../api/types.gen.ts'
import { lean, num, signed, ukDayTime } from '../format.ts'
import { DAY_MS } from '../simulation.ts'
import chart from './Chart.module.css'
import { CHART_OR_TABLE, type ChartOrTable, PENS } from './chartStyle.ts'
import styles from './History.module.css'
import shared from './Shared.module.css'
import tables from './Table.module.css'
import { ViewSwitch } from './ViewSwitch.tsx'

// Recharts is the bulk of the bundle: load it alongside the data, not in front of it.
const HistoryChart = lazy(() => import('./HistoryChart.tsx').then((m) => ({ default: m.HistoryChart })))

const MISS_WORD = { 1: 'higher', 0: 'even', [-1]: 'lower' } as const

/** A legend swatch drawn with the same pen as the line it labels, so the two can't drift. */
function PenSwatch({ pen }: { pen: (typeof PENS)[keyof typeof PENS] }) {
  return (
    <svg viewBox="0 0 32 8" aria-hidden="true">
      <line x1="0" y1="4" x2="32" y2="4" {...pen} />
    </svg>
  )
}

/** The scored half-hours behind the scorecard, for any of the scoring windows. */
export function History({
  history,
  windowDays,
  asOf,
}: {
  history: readonly HistoryPoint[]
  windowDays: readonly number[]
  asOf: string
}) {
  const lengths = windowDays.map((days) => ({ value: String(days), label: `${days} days` }))
  const [length, setLength] = useState(String(Math.max(...windowDays)))
  const [view, setView] = useState<ChartOrTable>('chart')
  const days = Number(length)
  const cutoff = Date.parse(asOf) - days * DAY_MS
  const shown = history.filter((p) => Date.parse(p.start_time) >= cutoff)

  return (
    <>
      <h3 className={shared.subhead}>Forecast and actual, last {days} days</h3>
      <div className={shared.head}>
        <div className={styles.legend}>
          <span>
            <PenSwatch pen={PENS.forecast} />
            Forecast, published the day before
          </span>
          <span>
            <PenSwatch pen={PENS.actual} />
            Actual, metered
          </span>
        </div>
        <div className={styles.switches}>
          <ViewSwitch label="History length" options={lengths} value={length} onChange={setLength} />
          <ViewSwitch label="Show history as" options={CHART_OR_TABLE} value={view} onChange={setView} />
        </div>
      </div>
      {view === 'chart' ? (
        <Suspense fallback={<div className={chart.waitHistory} />}>
          <HistoryChart history={shown} days={days} />
        </Suspense>
      ) : (
        <div className={tables.scroll}>
          <table className={tables.table}>
            <caption className={shared.visuallyHidden}>Forecast and actual, half-hour by half-hour</caption>
            <thead>
              <tr>
                <th scope="col">Half-hour</th>
                <th scope="col">Forecast MW</th>
                <th scope="col">Actual MW</th>
                <th scope="col">Miss MW</th>
              </tr>
            </thead>
            <tbody>
              {[...shown].reverse().map((p) => (
                <tr key={p.start_time}>
                  <td>{ukDayTime(p.start_time)}</td>
                  <td>{num(p.forecast_mw)}</td>
                  <td>{num(p.actual_mw)}</td>
                  <td>
                    {signed(p.miss_mw)} <span className={styles.words}>{MISS_WORD[lean(p.miss_mw)]}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}
