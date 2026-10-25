import { useState } from 'react'
import type { HistoryPoint } from '../api/types.gen.ts'
import { num, signed, ukDayTime } from '../format.ts'
import { HistoryChart } from './HistoryChart.tsx'
import styles from './History.module.css'
import tables from './Table.module.css'
import { ViewSwitch } from './ViewSwitch.tsx'

const VIEWS = [
  { value: 'chart', label: 'Chart' },
  { value: 'table', label: 'Table' },
] as const

const DAY = 86_400_000

function missWords(value: number): string {
  const rounded = Math.round(value)
  return rounded > 0 ? 'higher' : rounded < 0 ? 'lower' : 'even'
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
  const [view, setView] = useState<(typeof VIEWS)[number]['value']>('chart')
  const days = Number(length)
  const cutoff = Date.parse(asOf) - days * DAY
  const shown = history.filter((p) => Date.parse(p.start_time) >= cutoff)

  return (
    <>
      <h3 className={styles.title}>Forecast and actual, last {days} days</h3>
      <div className={styles.head}>
        <div className={styles.legend}>
          <span>
            <svg viewBox="0 0 32 8" aria-hidden="true">
              <line x1="0" y1="4" x2="32" y2="4" stroke="var(--pen-forecast)" strokeWidth="2" />
            </svg>
            Forecast, published the day before
          </span>
          <span>
            <svg viewBox="0 0 32 8" aria-hidden="true">
              <line x1="0" y1="4" x2="32" y2="4" stroke="var(--pen-actual)" strokeWidth="2" strokeDasharray="5 3" />
            </svg>
            Actual, metered
          </span>
        </div>
        <div className={styles.switches}>
          <ViewSwitch label="History length" options={lengths} value={length} onChange={setLength} />
          <ViewSwitch label="Show history as" options={VIEWS} value={view} onChange={setView} />
        </div>
      </div>
      {view === 'chart' ? (
        <HistoryChart history={shown} days={days} />
      ) : (
        <div className={tables.scroll}>
          <table className={tables.table}>
            <caption className={tables.caption}>Forecast and actual, half-hour by half-hour</caption>
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
                    {signed(p.miss_mw)} <span className={styles.words}>{missWords(p.miss_mw)}</span>
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
