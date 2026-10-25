// Every number on screen goes through here, so units, signs and UK time stay consistent.

const NBSP = ' '
// A real minus sign (U+2212): the same width as the plus, unlike a hyphen.
const MINUS = '−'
const whole = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 0 })
const tenths = new Intl.NumberFormat('en-GB', { minimumFractionDigits: 1, maximumFractionDigits: 1 })

/** The one sign rule: judge the rounded size, then keep the sign, so a −0.5 and a +0.5
 *  lean the same amount (Math.round(-0.5) is 0 but Math.round(0.5) is 1). */
export function lean(value: number, decimals = 0): -1 | 0 | 1 {
  if (Math.round(Math.abs(value) * 10 ** decimals) === 0) return 0
  return value > 0 ? 1 : -1
}

function withSign(value: number, decimals: 0 | 1): string {
  const format = decimals === 0 ? whole : tenths
  const direction = lean(value, decimals)
  if (direction === 0) return format.format(0)
  return `${direction > 0 ? '+' : MINUS}${format.format(Math.abs(value))}`
}

/** Table cells: the unit lives in the column header. */
export function num(value: number): string {
  return whole.format(value)
}

/** Whole-day energy can end in .5 (half-hours x 0.5 h): keep it so rows add up exactly. */
export function numTenths(value: number): string {
  return tenths.format(value)
}

/** Whole number with an explicit sign. */
export function signed(value: number): string {
  return withSign(value, 0)
}

/** Signed, to one decimal place. */
export function signedTenths(value: number): string {
  return withSign(value, 1)
}

export function mw(value: number): string {
  return `${whole.format(value)}${NBSP}MW`
}

export function mwh(value: number): string {
  return `${whole.format(value)}${NBSP}MWh`
}

/** A miss is forecast minus actual. The sign always travels with words. */
export function miss(value: number): { text: string; words: string } {
  const direction = lean(value)
  const words =
    direction === 0 ? 'no lean either way' : direction > 0 ? 'forecast higher' : 'forecast lower'
  return { text: `${signed(value)}${NBSP}MW`, words }
}

export function pct(value: number): string {
  return `${tenths.format(value)}%`
}

/** Percentage with an explicit sign, one decimal place. */
export function signedPct(value: number): string {
  return `${withSign(value, 1)}%`
}

/** How much of the past a percentile range covers: "8 in 10" when it's in tens. */
export function inTen(lowerPct: number, upperPct: number): string {
  const share = upperPct - lowerPct
  return share % 10 === 0 ? `${share / 10} in 10` : `${share}%`
}

/** Chart ticks for hours of a day; 24 is the end of it, not midnight at its start. */
export function hourLabel(hour: number): string {
  return `${String(hour).padStart(2, '0')}:00`
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
const month = plain({ month: 'short', year: 'numeric' })
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

export function monthYear(day: string): string {
  return month.format(asDate(day))
}
