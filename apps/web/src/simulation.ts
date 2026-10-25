// What can be picked: a day in the simulated month and a morning publish slot.
// The API is the authority (it answers 422 for anything else); these drive the dropdowns.

export const FIRST_DAY = '2026-01-01'
const LAST_DAY = '2026-01-31'
export const SLOTS = ['02:30', '04:30', '07:30', '09:30'] as const

/** The GB day-ahead auction (N2EX) gate: the buying has to be done by then. */
export const GATE_CLOSES = '09:50'

export const DAY_MS = 86_400_000

export type Choice = { today: string; slot: string }

const DEFAULT_CHOICE: Choice = { today: '2026-01-15', slot: '09:30' }

const plainDate = (ms: number) => new Date(ms).toISOString().slice(0, 10)

/** The plain date the day before `day`, e.g. '2026-01-01' -> '2025-12-31'. */
export function dayBefore(day: string): string {
  return plainDate(Date.parse(`${day}T00:00:00Z`) - DAY_MS)
}

/** Every day on offer, oldest first. */
export const SIM_DAYS: readonly string[] = Array.from(
  { length: (Date.parse(LAST_DAY) - Date.parse(FIRST_DAY)) / DAY_MS + 1 },
  (_, i) => plainDate(Date.parse(`${FIRST_DAY}T00:00:00Z`) + i * DAY_MS),
)

/** The query both the address bar and the API use: ?today=…&slot=… */
export function toQuery(choice: Choice): string {
  return new URLSearchParams({ today: choice.today, slot: choice.slot }).toString()
}

/** Reads ?today=&slot= from the address bar; anything not offered falls back to the default. */
export function readChoice(search: string): Choice {
  const params = new URLSearchParams(search)
  const today = params.get('today') ?? ''
  const slot = params.get('slot') ?? ''
  return {
    today: SIM_DAYS.includes(today) ? today : DEFAULT_CHOICE.today,
    slot: (SLOTS as readonly string[]).includes(slot) ? slot : DEFAULT_CHOICE.slot,
  }
}
