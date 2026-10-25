import styles from './ViewSwitch.module.css'

type Option<T extends string> = { value: T; label: string }

/** A small set of mutually exclusive buttons; the pressed one is what's showing. */
export function ViewSwitch<T extends string>({
  label,
  options,
  value,
  onChange,
}: {
  label: string
  options: readonly Option<T>[]
  value: T
  onChange: (next: T) => void
}) {
  return (
    <div className={styles.switch} role="group" aria-label={label}>
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          className={styles.button}
          aria-pressed={option.value === value}
          onClick={() => onChange(option.value)}
        >
          {option.label}
        </button>
      ))}
    </div>
  )
}
