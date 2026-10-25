import type { WholeDays } from '../api/types.gen.ts'
import { dayShort, num, numTenths, signedPct, signedTenths } from '../format.ts'
import tables from './Table.module.css'
import shared from './Shared.module.css'
import styles from './WholeDaysTable.module.css'

/** The past whole days the day range is built from: every one of them, newest first. */
export function WholeDaysTable({ whole, slot }: { whole: WholeDays; slot: string }) {
  const title = `Whole days, last ${whole.window_days} days`
  return (
    <>
      <h3 className={shared.subhead}>{title}</h3>
      <p className={styles.lead}>
        Each day&rsquo;s total as forecast at {slot} the day before, against what was metered.
        The whole-day range above is built from these numbers.
      </p>
      {whole.days.length > 0 && (
        <div className={tables.scroll}>
          <table className={tables.table}>
            <caption className={shared.visuallyHidden}>{title}</caption>
            <thead>
              <tr>
                <th scope="col">Day</th>
                <th scope="col">Forecast MWh</th>
                <th scope="col">Actual MWh</th>
                <th scope="col">Miss MWh</th>
                <th scope="col">Miss %</th>
              </tr>
            </thead>
            <tbody>
              {[...whole.days].reverse().map((d) => (
                <tr key={d.day}>
                  <td>{dayShort(d.day)}</td>
                  <td>{num(d.forecast_mwh)}</td>
                  <td>{numTenths(d.actual_mwh)}</td>
                  <td>{signedTenths(d.miss_mwh)}</td>
                  <td>{signedPct(d.miss_pct)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {whole.skipped_days > 0 && (
        <p className={shared.note}>
          {whole.skipped_days} of the last {whole.window_days} days were skipped: not every
          half-hour could be scored.
        </p>
      )}
    </>
  )
}
