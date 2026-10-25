import type { WindowMetrics } from '../api/types.gen.ts'
import { mw } from '../format.ts'
import styles from './Tomorrow.module.css'

/** The hourly view, up top: how far off a typical half-hour was lately, and which way it leaned. */
export function HourlyMiss({ window }: { window: WindowMetrics | undefined }) {
  if (!window || window.mae_mw === null || window.bias_mw === null) return null
  const lean = Math.round(window.bias_mw)
  return (
    <p className={styles.lead}>
      Hour by hour, the last {window.days} days were off by <mark>{mw(window.mae_mw)}</mark> on a
      typical half-hour,{' '}
      {lean === 0 ? (
        'with no lean either way.'
      ) : (
        <>
          leaning <mark>{`${mw(Math.abs(window.bias_mw))} ${lean > 0 ? 'high' : 'low'}`}</mark>.
        </>
      )}
    </p>
  )
}
