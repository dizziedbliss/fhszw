import { useState } from 'react'
import type { Band, Tomorrow as TomorrowData, WholeDays, WindowMetrics } from '../api/types.gen.ts'
import { dayLong, mw, mwh, num, signed, ukTime } from '../format.ts'
import { DayRange } from './DayRange.tsx'
import { ForecastChart } from './ForecastChart.tsx'
import { HourlyMiss } from './HourlyMiss.tsx'
import tables from './Table.module.css'
import styles from './Tomorrow.module.css'
import { ViewSwitch } from './ViewSwitch.tsx'

const VIEWS = [
  { value: 'chart', label: 'Chart' },
  { value: 'table', label: 'Table' },
] as const

function BandCaption({ band }: { band: Band | null }) {
  if (band === null) {
    return <p className={styles.caption}>No band yet: there are no scored half-hours to learn from.</p>
  }
  const share = Math.round((band.upper_pct - band.lower_pct) / 10)
  return (
    <p className={styles.caption}>
      <span className={styles.swatch} aria-hidden="true" />
      <span>
        Shaded: where tomorrow lands if it misses the way the last {band.window_days} days did.{' '}
        {share} in 10 past half-hours fell inside (misses from {signed(band.lower_miss_mw)} to{' '}
        {signed(band.upper_miss_mw)}&nbsp;MW).
      </span>
    </p>
  )
}

export function Tomorrow({
  tomorrow,
  band,
  wholeDays,
  recent,
}: {
  tomorrow: TomorrowData
  band: Band | null
  wholeDays: WholeDays
  recent: WindowMetrics | undefined
}) {
  const [view, setView] = useState<(typeof VIEWS)[number]['value']>('chart')
  return (
    <section aria-labelledby="tomorrow" className={styles.section}>
      <h2 id="tomorrow">{dayLong(tomorrow.delivery_day)}</h2>
      <p className={styles.summary}>
        <b>{mwh(tomorrow.total_mwh)}</b> of wind forecast across the day. Lowest hour{' '}
        <b>{mw(tomorrow.low.mw)}</b> at {ukTime(tomorrow.low.start_time)}, highest{' '}
        <b>{mw(tomorrow.high.mw)}</b> at {ukTime(tomorrow.high.start_time)}.
      </p>
      <DayRange whole={wholeDays} />
      <HourlyMiss window={recent} />
      <div className={styles.head}>
        <span className={styles.what}>Hourly forecast, MW</span>
        <ViewSwitch label="Show tomorrow as" options={VIEWS} value={view} onChange={setView} />
      </div>
      {view === 'chart' ? (
        <ForecastChart hours={tomorrow.hours} />
      ) : (
        <div className={tables.scroll}>
          <table className={tables.table}>
            <caption className={tables.caption}>Tomorrow, hour by hour</caption>
            <thead>
              <tr>
                <th scope="col">Hour</th>
                <th scope="col">Forecast MW</th>
                <th scope="col">Band low MW</th>
                <th scope="col">Band high MW</th>
              </tr>
            </thead>
            <tbody>
              {tomorrow.hours.map((h) => (
                <tr key={h.start_time}>
                  <td>{ukTime(h.start_time)}</td>
                  <td>{num(h.forecast_mw)}</td>
                  <td>{h.band_low_mw === null ? '' : num(h.band_low_mw)}</td>
                  <td>{h.band_high_mw === null ? '' : num(h.band_high_mw)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <BandCaption band={band} />
    </section>
  )
}
