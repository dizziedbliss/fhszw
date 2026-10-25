// Every number on screen goes through here, so units, signs and UK time stay consistent.

const NBSP = ' '
const whole = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 0 })

/** Table cells: the unit lives in the column header. */
export function num(value: number): string {
  return whole.format(value)
}

export function mw(value: number): string {
  return `${whole.format(value)}${NBSP}MW`
}

export function mwh(value: number): string {
  return `${whole.format(value)}${NBSP}MWh`
}

/** Whole number with an explicit sign; a real minus (U+2212) is the same width as the plus. */
export function signed(value: number): string {
  // Round the size, then restore the sign: Math.round(-949.5) is -949 but Math.round(949.5)
  // is 950, and the same-sized miss must read the same either way.
  const rounded = Math.sign(value) * Math.round(Math.abs(value))
  if (rounded === 0) return '0'
  return `${rounded > 0 ? '+' : '\u2212'}${whole.format(Math.abs(rounded))}`
}

/** A miss is forecast minus actual. The sign always travels with words. */
export function miss(value: number): { text: string; words: string } {
  const text = `${signed(value)}${NBSP}MW`
  if (text.startsWith('0')) return { text, words: 'no lean either way' }
  return { text, words: text.startsWith('+') ? 'forecast higher' : 'forecast lower' }
}

const oneDecimal = new Intl.NumberFormat('en-GB', { minimumFractionDigits: 1, maximumFractionDigits: 1 })

export function pct(value: number): string {
  return `${oneDecimal.format(value)}%`
}

// The market runs on UK time, so every clock on screen does too.
const UK = 'Europe/London'
const clock = new Intl.DateTimeFormat('en-GB', { timeZone: UK, hour: '2-digit', minute: '2-digit', hourCycle: 'h23' })
const dayMonth = new Intl.DateTimeFormat('en-GB', { timeZone: UK, day: 'numeric', month: 'short' })
const dayMonthYear = new Intl.DateTimeFormat('en-GB', { timeZone: UK, day: 'numeric', month: 'short', year: 'numeric' })

export function ukTime(iso: string): string {
  return clock.format(new Date(iso))
}

export function ukDayTime(iso: string): string {
  const at = new Date(iso)
  return `${dayMonth.format(at)} ${clock.format(at)}`
}

export function ukDateTime(iso: string): string {
  const at = new Date(iso)
  return `${dayMonthYear.format(at)}, ${clock.format(at)}`
}

// Plain dates ("2026-01-16") have no time zone: read and print them in UTC so they never shift.
const plain = (options: Intl.DateTimeFormatOptions) =>
  new Intl.DateTimeFormat('en-GB', { timeZone: 'UTC', ...options })
const long = plain({ weekday: 'long', day: 'numeric', month: 'long' })
const short = plain({ weekday: 'short', day: 'numeric', month: 'short' })
const tick = plain({ day: 'numeric', month: 'short' })
const asDate = (day: string) => new Date(`${day}T00:00:00Z`)

export function dayLong(day: string): string {
  return long.format(asDate(day)).replace(',', '')
}

export function dayShort(day: string): string {
  return short.format(asDate(day)).replace(',', '')
}

export function dayTick(day: string): string {
  return tick.format(asDate(day))
}
