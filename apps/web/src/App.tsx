import { useEffect, useState } from 'react'
import styles from './App.module.css'
import { Accuracy } from './components/Accuracy.tsx'
import { Controls } from './components/Controls.tsx'
import { History } from './components/History.tsx'
import { Tomorrow } from './components/Tomorrow.tsx'
import { WholeDaysTable } from './components/WholeDaysTable.tsx'
import { dayShort, ukDateTime } from './format.ts'
import { type Choice, GATE_CLOSES, readChoice } from './simulation.ts'
import { useDecision } from './useDecision.ts'

function toSearch(choice: Choice): string {
  return `?${new URLSearchParams({ today: choice.today, slot: choice.slot }).toString()}`
}

export default function App() {
  const [choice, setChoice] = useState(() => readChoice(window.location.search))
  const { state, retry } = useDecision(choice)

  // The address bar holds the choice, so links can be shared and Back works.
  useEffect(() => {
    const onPopState = () => setChoice(readChoice(window.location.search))
    window.addEventListener('popstate', onPopState)
    return () => window.removeEventListener('popstate', onPopState)
  }, [])

  const choose = (next: Choice) => {
    window.history.pushState(null, '', toSearch(next))
    setChoice(next)
  }

  return (
    <div className={styles.wrap}>
      <a className={styles.skip} href="#tomorrow">
        Skip to tomorrow&rsquo;s forecast
      </a>
      <header className={styles.top}>
        <h1 className={styles.wordmark} translate="no">
          Wind day-ahead
        </h1>
        <p className={styles.gate}>
          <svg viewBox="0 0 12 12" aria-hidden="true">
            <path d="M0 0h12L6 10z" />
          </svg>
          Gate closes {GATE_CLOSES}
        </p>
      </header>
      <Controls choice={choice} onChange={choose} />

      <p role="status" className={styles.status}>
        {state.status === 'loading' &&
          `Fetching the ${choice.slot} forecast for ${dayShort(choice.today)} from Elexon…`}
      </p>

      {state.status === 'error' && (
        <div role="alert" className={styles.error}>
          <p>{state.message}</p>
          <button type="button" className={styles.retry} onClick={retry}>
            Try again
          </button>
        </div>
      )}

      {state.status === 'ready' && (
        <>
          <main>
            <Tomorrow
              tomorrow={state.data.tomorrow}
              band={state.data.band}
              wholeDays={state.data.whole_days}
              // The shortest scoring window: the most recent read on the hourly miss.
              recent={[...state.data.windows].sort((a, b) => a.days - b.days)[0]}
            />
            <section aria-labelledby="accuracy" className={styles.section}>
              <Accuracy windows={state.data.windows} slot={choice.slot} />
              <WholeDaysTable whole={state.data.whole_days} slot={choice.slot} />
              <History
                history={state.data.history}
                windowDays={state.data.windows.map((w) => w.days)}
                asOf={state.data.tomorrow.publish_time}
              />
            </section>
          </main>
          <footer className={styles.footer}>
            Data from <span translate="no">Elexon BMRS</span>: <span translate="no">WINDFOR</span>{' '}
            hourly wind forecasts and <span translate="no">FUELHH</span> half-hourly metered
            generation. Fetched {ukDateTime(state.data.fetched_at)} UK time.
          </footer>
        </>
      )}
    </div>
  )
}
