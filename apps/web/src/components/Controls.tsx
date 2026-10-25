import { dayShort } from '../format.ts'
import { type Choice, SLOTS, simulatedDays } from '../simulation.ts'
import styles from './Controls.module.css'

const DAYS = simulatedDays()
// Latest publish first: 09:30 is the one he'll usually want.
const SLOTS_LATEST_FIRST = [...SLOTS].reverse()

/** The hero sentence: the two dropdowns are part of what it says. */
export function Controls({ choice, onChange }: { choice: Choice; onChange: (next: Choice) => void }) {
  return (
    <p className={styles.hero}>
      Today is{' '}
      <label>
        <span className={styles.visuallyHidden}>Today</span>
        <select
          className={styles.select}
          value={choice.today}
          onChange={(event) => onChange({ ...choice, today: event.target.value })}
        >
          {DAYS.map((day) => (
            <option key={day} value={day}>
              {dayShort(day)}
            </option>
          ))}
        </select>
      </label>
      , and you&rsquo;re reading the{' '}
      <label>
        <span className={styles.visuallyHidden}>Forecast as of</span>
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
