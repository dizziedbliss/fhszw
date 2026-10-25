// What he can pick: a day in the simulated month and a morning publish slot.
// The API is the authority (it answers 422 for anything else); these drive the dropdowns.

export const FIRST_DAY = '2026-01-01'
export const LAST_DAY = '2026-01-31'
export const SLOTS = ['02:30', '04:30', '07:30', '09:30'] as const

/** The GB day-ahead auction (N2EX) gate: he has to have bought by then. */
export const GATE_CLOSES = '09:50'

export type Choice = { today: string; slot: string }

export const DEFAULT_CHOICE: Choice = { today: '2026-01-15', slot: '09:30' }

export function simulatedDays(): string[] {
  const days: string[] = []
  for (let d = new Date(`${FIRST_DAY}T00:00:00Z`); d <= new Date(`${LAST_DAY}T00:00:00Z`); ) {
    days.push(d.toISOString().slice(0, 10))
    d = new Date(d.getTime() + 86_400_000)
  }
  return days
}

/** Reads ?today=&slot= from the address bar; anything not offered falls back to the default. */
export function readChoice(search: string): Choice {
  const params = new URLSearchParams(search)
  const today = params.get('today') ?? ''
  const slot = params.get('slot') ?? ''
  return {
    today: simulatedDays().includes(today) ? today : DEFAULT_CHOICE.today,
    slot: (SLOTS as readonly string[]).includes(slot) ? slot : DEFAULT_CHOICE.slot,
  }
}
