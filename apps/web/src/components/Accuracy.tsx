import type { ReactNode } from 'react'
import type { WindowMetrics } from '../api/types.gen.ts'
import { miss, mw, num, pct } from '../format.ts'
import { FIRST_DAY } from '../simulation.ts'
import styles from './Accuracy.module.css'

// The month before the simulation starts, e.g. "Dec 2025", for windows that reach back into it.
const MONTH_BEFORE = new Intl.DateTimeFormat('en-GB', {
  timeZone: 'UTC',
  month: 'short',
  year: 'numeric',
}).format(new Date(new Date(`${FIRST_DAY}T00:00:00Z`).getTime() - 86_400_000))

const NO_DATA = 'no data'

type Measure = { name: string; meaning: string; value: (w: WindowMetrics) => ReactNode }

const MEASURES: Measure[] = [
  {
    name: 'MAE',
    meaning: 'Average miss, ignoring direction',
    value: (w) => (w.mae_mw === null ? NO_DATA : mw(w.mae_mw)),
  },
  {
    name: 'RMSE',
    meaning: 'Same, but big misses count extra',
    value: (w) => (w.rmse_mw === null ? NO_DATA : mw(w.rmse_mw)),
  },
  {
    name: 'Bias',
    meaning: 'Average miss with its direction',
    value: (w) => {
      if (w.bias_mw === null) return NO_DATA
      const { text, words } = miss(w.bias_mw)
      return (
        <>
          {text} <span className={styles.words}>{words}</span>
        </>
      )
    },
  },
  {
    name: 'MDA',
    meaning: 'Hour-to-hour ups and downs called right',
    value: (w) => (w.mda_pct === null ? NO_DATA : pct(w.mda_pct)),
  },
  { name: 'Scored', meaning: 'Half-hours compared', value: (w) => num(w.half_hours) },
]

export function Accuracy({ windows, slot }: { windows: readonly WindowMetrics[]; slot: string }) {
  const skipped = windows.filter((w) => w.unscored_half_hours > 0)
  return (
    <>
      <h2 id="accuracy">How close this forecast has been</h2>
      <p className={styles.lead}>
        Each past half-hour, scored against the forecast published at {slot} the day before: the
        same kind of forecast you&rsquo;re reading now. Misses are forecast minus actual.
      </p>
      <table className={styles.table}>
        <caption className={styles.visuallyHidden}>How close this forecast has been</caption>
        <thead>
          <tr>
            <th scope="col">
              <span className={styles.visuallyHidden}>Measure</span>
            </th>
            {windows.map((w) => (
              <th key={w.days} scope="col">
                Last {w.days} days
                {w.days_before_sim_start > 0 && (
                  <span className={styles.words}>
                    {w.days_before_sim_start} days from {MONTH_BEFORE}
                  </span>
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {MEASURES.map((measure) => (
            <tr key={measure.name}>
              <th scope="row">
                {measure.name} <span className={styles.meaning}>{measure.meaning}</span>
              </th>
              {windows.map((w) => (
                <td key={w.days}>{measure.value(w)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {skipped.map((w) => (
        <p key={w.days} className={styles.note}>
          {num(w.unscored_half_hours)} half-hours in the last {w.days} days were skipped: Elexon has
          no {slot} forecast from the day before them to compare with.
        </p>
      ))}
    </>
  )
}
