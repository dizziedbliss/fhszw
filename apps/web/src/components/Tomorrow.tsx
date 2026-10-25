import { lazy, Suspense, useState } from 'react'
import type { Band, Tomorrow as TomorrowData, WholeDays, WindowMetrics } from '../api/types.gen.ts'
import { dayLong, inTen, mw, mwh, num, signed, ukTime } from '../format.ts'
import chart from './Chart.module.css'
import { CHART_OR_TABLE, type ChartOrTable } from './chartStyle.ts'
import { DayRange } from './DayRange.tsx'
import { HourlyMiss } from './HourlyMiss.tsx'
import shared from './Shared.module.css'
import tables from './Table.module.css'
import styles from './Tomorrow.module.css'
import { ViewSwitch } from './ViewSwitch.tsx'

// Recharts is the bulk of the bundle: load it alongside the data, not in front of it.
const ForecastChart = lazy(() => import('./ForecastChart.tsx').then((m) => ({ default: m.ForecastChart })))

function BandCaption({ band }: { band: Band | null }) {
  if (band === null) {
    return <p className={styles.caption}>No band yet: there are no scored half-hours to learn from.</p>
  }
  return (
    <p className={styles.caption}>
      <span className={styles.swatch} aria-hidden="true" />
      <span>
        Shaded: where tomorrow lands if it misses the way the last {band.window_days} days did.{' '}
        {inTen(band.lower_pct, band.upper_pct)} past half-hours fell inside (misses from{' '}
        {signed(band.lower_miss_mw)} to {signed(band.upper_miss_mw)}&nbsp;MW).
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
  const [view, setView] = useState<ChartOrTable>('chart')
  return (
    <section aria-labelledby="tomorrow" className={shared.section}>
      <h2 id="tomorrow">{dayLong(tomorrow.delivery_day)}</h2>
      <p className={styles.summary}>
        <b>{mwh(tomorrow.total_mwh)}</b> of wind forecast across the day. Lowest hour{' '}
        <b>{mw(tomorrow.low.mw)}</b> at {ukTime(tomorrow.low.start_time)}, highest{' '}
        <b>{mw(tomorrow.high.mw)}</b> at {ukTime(tomorrow.high.start_time)}.
      </p>
      <DayRange whole={wholeDays} />
      <HourlyMiss window={recent} />
      <div className={shared.head}>
        <span className={styles.what}>Hourly forecast, MW</span>
        <ViewSwitch label="Show tomorrow as" options={CHART_OR_TABLE} value={view} onChange={setView} />
      </div>
      {view === 'chart' ? (
        <Suspense fallback={<div className={chart.waitForecast} />}>
          <ForecastChart hours={tomorrow.hours} />
        </Suspense>
      ) : (
        <div className={tables.scroll}>
          <table className={tables.table}>
            <caption className={shared.visuallyHidden}>Tomorrow, hour by hour</caption>
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
