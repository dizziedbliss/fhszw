import { describe, expect, test } from 'vitest'
import {
  dayLong,
  hourLabel,
  inTen,
  lean,
  monthYear,
  dayShort,
  dayTick,
  miss,
  mw,
  mwh,
  num,
  numTenths,
  pct,
  signed,
  signedPct,
  signedTenths,
  ukDateTime,
  ukDayTime,
  ukTime,
} from './format.ts'

const NBSP = ' '

describe('mw', () => {
  test('rounds to whole MW with thousands separators, and never splits number from unit', () => {
    expect(mw(5880.6)).toBe(`5,881${NBSP}MW`)
  })
})

describe('mwh', () => {
  test('formats energy the same way, in MWh', () => {
    expect(mwh(191402)).toBe(`191,402${NBSP}MWh`)
  })
})

describe('miss', () => {
  test.each([
    [1534.04, `+1,534${NBSP}MW`, 'forecast higher'],
    [-949.5, `\u2212950${NBSP}MW`, 'forecast lower'], // same size as +949.5, so 950 too
    [0.2, `0${NBSP}MW`, 'no lean either way'],
  ])('%s MW reads as %s, %s', (value, text, words) => {
    expect(miss(value)).toEqual({ text, words })
  })
})

describe('pct', () => {
  test('one decimal place', () => {
    expect(pct(62.264151)).toBe('62.3%')
  })
})

describe('UK time', () => {
  test('clock times are UK time, whatever the viewer machine is set to', () => {
    expect(ukTime('2026-01-16T06:00:00Z')).toBe('06:00') // GMT in winter
    expect(ukTime('2026-07-01T05:00:00Z')).toBe('06:00') // BST in summer
  })

  test('history rows and the footer carry the day too', () => {
    expect(ukDayTime('2026-01-15T09:00:00Z')).toBe('15 Jan 09:00')
    expect(ukDateTime('2026-10-25T11:01:26.301429Z')).toBe('25 Oct 2026, 11:01')
  })
})

describe('days', () => {
  test.each([
    [dayLong, 'Friday 16 January'],
    [dayShort, 'Fri 16 Jan'],
    [dayTick, '16 Jan'],
  ])('%o formats a plain date without shifting it a day', (format, expected) => {
    expect(format('2026-01-16')).toBe(expected)
  })
})

describe('num', () => {
  test('table cells: whole number with separators, unit lives in the column header', () => {
    expect(num(2980.5)).toBe('2,981')
  })
})

describe('signed', () => {
  test.each([
    [4491.5, '+4,492'],
    [-949.5, '\u2212950'],
  ])('%s keeps an explicit sign: %s', (value, expected) => {
    expect(signed(value)).toBe(expected)
  })
})

describe('signedPct', () => {
  test.each([
    [25.323484, '+25.3%'],
    [-2.100334, '\u22122.1%'],
  ])('%s reads as %s', (value, expected) => {
    expect(signedPct(value)).toBe(expected)
  })
})

describe('tenths (whole-day MWh, so forecast - actual = miss checks exactly)', () => {
  test.each([
    [325376.5, '325,376.5'],
    [241643, '241,643.0'],
  ])('numTenths(%s) is %s', (value, expected) => {
    expect(numTenths(value)).toBe(expected)
  })

  test.each([
    [117530.5, '+117,530.5'],
    [-4774.5, '\u22124,774.5'],
  ])('signedTenths(%s) is %s', (value, expected) => {
    expect(signedTenths(value)).toBe(expected)
  })
})

describe('lean (the one sign rule every signed number and word uses)', () => {
  test.each([
    [1534.04, 1],
    [0.4, 0],
    [0.5, 1],
    [-0.5, -1], // the same size as +0.5, so it leans the same amount
  ])('lean(%s) is %s', (value, expected) => {
    expect(lean(value)).toBe(expected)
  })

  test('it can judge at one decimal place too', () => {
    expect([lean(0.04, 1), lean(-0.05, 1)]).toEqual([0, -1])
  })
})

describe('inTen', () => {
  test('a share in tens reads as "N in 10"; anything else stays an honest percentage', () => {
    expect([inTen(10, 90), inTen(10, 85)]).toEqual(['8 in 10', '75%'])
  })
})

describe('hourLabel', () => {
  test('hours of the day, with 24:00 for the end of it', () => {
    expect([hourLabel(3), hourLabel(24)]).toEqual(['03:00', '24:00'])
  })
})

describe('monthYear', () => {
  test('a plain date as month and year, without shifting it', () => {
    expect(monthYear('2025-12-31')).toBe('Dec 2025')
  })
})
