import type { WholeDays } from '../api/types.gen.ts'
import { mwh, num, pct } from '../format.ts'
import styles from './Tomorrow.module.css'

/** The whole-day view: how far past days' totals missed, applied to tomorrow's total. */
export function DayRange({ whole }: { whole: WholeDays }) {
  const { average_miss_mwh: avg, average_miss_pct: avgPct } = whole
  const { tomorrow_low_mwh: low, tomorrow_high_mwh: high } = whole
  if (avg === null || avgPct === null || low === null || high === null) {
    return (
      <p className={styles.range}>
        No whole past days to compare yet, so there&rsquo;s no day range.
      </p>
    )
  }
  const used = whole.days.length
  const over =
    used === whole.window_days
      ? `Over the last ${used} whole days`
      : `Over ${used} whole days from the last ${whole.window_days}`
  const rounded = Math.round(avg)
  const lean =
    rounded === 0
      ? 'matched what came, on average'
      : `ran ${mwh(Math.abs(avg))} (${pct(Math.abs(avgPct))}) ${rounded > 0 ? 'above' : 'below'} what came, on average`
  const share = Math.round((whole.upper_pct - whole.lower_pct) / 10)
  return (
    <p className={styles.range}>
      {over}, the day&rsquo;s forecast {lean}. {share} in 10 of those days&rsquo; misses, applied to
      tomorrow, would put it between {num(low)} and {mwh(high)}
      {whole.clipped_at_zero && ' (the low end is held at 0 MWh)'}. A single day can still fall
      outside it.
    </p>
  )
}
