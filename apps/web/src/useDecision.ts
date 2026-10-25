import { useEffect, useState } from 'react'
import { ApiError, fetchDecision } from './api.ts'
import type { DecisionResponse } from './api/types.gen.ts'
import type { Choice } from './simulation.ts'

type DecisionState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; data: DecisionResponse }

type Settled = { key: string; state: Exclude<DecisionState, { status: 'loading' }> }

/** Fetches the decision for a day and slot. `retry` asks again after an error. */
export function useDecision(choice: Choice): { state: DecisionState; retry: () => void } {
  const [attempt, setAttempt] = useState(0)
  const [settled, setSettled] = useState<Settled | null>(null)
  const key = `${choice.today} ${choice.slot} #${attempt}`

  useEffect(() => {
    const controller = new AbortController()
    fetchDecision({ today: choice.today, slot: choice.slot }, controller.signal).then(
      (data) => setSettled({ key, state: { status: 'ready', data } }),
      (error: unknown) => {
        if (controller.signal.aborted) return
        const message =
          error instanceof ApiError ? error.message : 'Something unexpected went wrong. Try again.'
        setSettled({ key, state: { status: 'error', message } })
      },
    )
    return () => controller.abort()
  }, [choice.today, choice.slot, key])

  // Loading is derived, not stored: whatever we hold belongs to an older request.
  const state: DecisionState = settled?.key === key ? settled.state : { status: 'loading' }
  return { state, retry: () => setAttempt((n) => n + 1) }
}
