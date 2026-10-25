import { dayShort } from '../format.ts'
import { type Choice, SIM_DAYS, SLOTS } from '../simulation.ts'
import styles from './Controls.module.css'
import shared from './Shared.module.css'

const DAY_OPTIONS = SIM_DAYS.map((day) => ({ day, label: dayShort(day) }))
// Latest publish first: 09:30 is the one usually wanted.
const SLOTS_LATEST_FIRST = [...SLOTS].reverse()

/** The hero sentence: the two dropdowns are part of what it says. */
export function Controls({ choice, onChange }: { choice: Choice; onChange: (next: Choice) => void }) {
  return (
    <p className={styles.hero}>
      Today is{' '}
      <label>
        <span className={shared.visuallyHidden}>Today</span>
        <select
          className={styles.select}
          value={choice.today}
          onChange={(event) => onChange({ ...choice, today: event.target.value })}
        >
          {DAY_OPTIONS.map(({ day, label }) => (
            <option key={day} value={day}>
              {label}
            </option>
          ))}
        </select>
      </label>
      , and you&rsquo;re reading the{' '}
      <label>
        <span className={shared.visuallyHidden}>Forecast as of</span>
        <select
          className={styles.select}
          value={choice.slot}
          onChange={(event) => onChange({ ...choice, slot: event.target.value })}
        >
          {SLOTS_LATEST_FIRST.map((slot) => (
            <option key={slot} value={slot}>
              {slot}
            </option>
          ))}
        </select>
      </label>{' '}
      wind forecast.
    </p>
  )
}
