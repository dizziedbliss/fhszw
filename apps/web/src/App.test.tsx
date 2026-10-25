import { act, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import App from './App.tsx'
import type { DecisionResponse } from './api/types.gen.ts'
import { fakeApi, JAN15 } from './test/fake-api.ts'

beforeEach(() => {
  window.history.replaceState(null, '', '/')
})

afterEach(() => {
  vi.unstubAllGlobals()
})

test('renders the page heading', () => {
  fakeApi()
  render(<App />)

  expect(screen.getByRole('heading', { level: 1, name: 'Wind day-ahead' })).toBeInTheDocument()
})

test("shows tomorrow's forecast summary for the default day, 15 Jan at 09:30", async () => {
  const requests = fakeApi()
  render(<App />)

  expect(await screen.findByRole('heading', { name: 'Friday 16 January' })).toBeInTheDocument()
  // toHaveTextContent folds non-breaking spaces into plain ones (format tests pin those).
  expect(screen.getByText(/of wind forecast across the day/)).toHaveTextContent(
    '191,402 MWh of wind forecast across the day. Lowest hour 5,881 MW at 06:00, highest 10,850 MW at 21:00.',
  )
  expect(requests.map((u) => u.pathname + u.search)).toEqual([
    '/api/decision?today=2026-01-15&slot=09%3A30',
  ])
})

const asked = (requests: URL[]) => requests.map((u) => u.searchParams.toString())

test('reads the day and slot from the address bar', async () => {
  window.history.replaceState(null, '', '/?today=2026-01-03&slot=07:30')
  const requests = fakeApi()
  render(<App />)

  expect(await screen.findByRole('combobox', { name: 'Today' })).toHaveValue('2026-01-03')
  expect(screen.getByRole('combobox', { name: 'Forecast as of' })).toHaveValue('07:30')
  expect(asked(requests)).toEqual(['today=2026-01-03&slot=07%3A30'])
})

test('anything not offered in the address bar falls back to 15 Jan at 09:30', () => {
  window.history.replaceState(null, '', '/?today=2026-02-30&slot=10:00')
  const requests = fakeApi()
  render(<App />)

  expect(asked(requests)).toEqual(['today=2026-01-15&slot=09%3A30'])
})

test('picking another day or slot updates the address bar and asks again', async () => {
  const requests = fakeApi()
  const user = userEvent.setup()
  render(<App />)

  await user.selectOptions(screen.getByRole('combobox', { name: 'Today' }), 'Wed 14 Jan')
  await user.selectOptions(screen.getByRole('combobox', { name: 'Forecast as of' }), '07:30')

  expect(window.location.search).toBe('?today=2026-01-14&slot=07%3A30')
  expect(asked(requests).at(-1)).toBe('today=2026-01-14&slot=07%3A30')
})

test('the back button returns to the previous choice', async () => {
  fakeApi()
  const user = userEvent.setup()
  render(<App />)
  await user.selectOptions(screen.getByRole('combobox', { name: 'Today' }), 'Wed 14 Jan')

  act(() => {
    window.history.back()
  })

  await waitFor(() => {
    expect(screen.getByRole('combobox', { name: 'Today' })).toHaveValue('2026-01-15')
  })
})

function withBand(band: DecisionResponse['band']): DecisionResponse {
  return { ...JAN15, band, tomorrow: { ...JAN15.tomorrow, hours: JAN15.tomorrow.hours.map((h) => (band ? h : { ...h, band_low_mw: null, band_high_mw: null })) } }
}

test("tomorrow switches from chart to a table of all 24 hours with the band's edges", async () => {
  fakeApi()
  const user = userEvent.setup()
  render(<App />)
  const show = within(await screen.findByRole('group', { name: 'Show tomorrow as' }))
  expect(show.getByRole('button', { name: 'Chart' })).toHaveAttribute('aria-pressed', 'true')

  await user.click(show.getByRole('button', { name: 'Table' }))

  const table = screen.getByRole('table', { name: 'Tomorrow, hour by hour' })
  const rows = within(table).getAllByRole('row').slice(1)
  expect(rows).toHaveLength(24)
  // 00:00: forecast 7,472; band 7,472 - 4,491.5 and 7,472 + 949.5
  expect(within(rows[0]!).getAllByRole('cell').map((c) => c.textContent)).toEqual([
    '00:00',
    '7,472',
    '2,981',
    '8,422',
  ])
  expect(show.getByRole('button', { name: 'Table' })).toHaveAttribute('aria-pressed', 'true')
})

test('the band says what it is, in numbers', async () => {
  fakeApi()
  render(<App />)

  expect(await screen.findByText(/where tomorrow lands/)).toHaveTextContent(
    'Shaded: where tomorrow lands if it misses the way the last 14 days did. 8 in 10 past half-hours fell inside (misses from −950 to +4,492 MW).',
  )
})

test('without enough history there is no band, and the page says so', async () => {
  fakeApi(() => ({ status: 200, body: withBand(null) }))
  render(<App />)

  expect(await screen.findByText(/No band yet/)).toBeInTheDocument()
  expect(screen.queryByText(/where tomorrow lands/)).not.toBeInTheDocument()
})

/** Cell texts of a row, with any run of spaces (incl. non-breaking) folded to one. */
const cells = (row: HTMLElement | null | undefined) =>
  within(row!).getAllByRole('cell').map((c) => (c.textContent ?? '').replace(/\s+/g, ' ').trim())

const scorecard = () => screen.findByRole('table', { name: 'How close this forecast has been' })
const rowOf = (table: HTMLElement, measure: string) =>
  within(table).getByRole('rowheader', { name: new RegExp(`^${measure}`) }).closest('tr')

test('the scorecard shows each measure for the last 7 and 14 days', async () => {
  fakeApi()
  render(<App />)
  const table = await scorecard()

  expect(cells(rowOf(table, 'MAE'))).toEqual(['2,201 MW', '2,124 MW'])
  expect(cells(rowOf(table, 'RMSE'))).toEqual(['2,943 MW', '2,704 MW'])
  expect(cells(rowOf(table, 'Bias'))).toEqual(['+1,534 MW forecast higher', '+1,703 MW forecast higher'])
  expect(cells(rowOf(table, 'MDA'))).toEqual(['62.3%', '63.3%'])
  expect(cells(rowOf(table, 'Scored'))).toEqual(['336', '672'])
})

test('the scorecard is honest about thin, borrowed or missing history', async () => {
  const [week, fortnight] = JAN15.windows
  fakeApi(() => ({
    status: 200,
    body: {
      ...JAN15,
      windows: [
        { ...week!, half_hours: 0, mae_mw: null, rmse_mw: null, bias_mw: null, mda_pct: null, mda_moves: 0, unscored_half_hours: 48, days_before_sim_start: 5 },
        { ...fortnight!, days_before_sim_start: 12 },
      ],
    },
  }))
  render(<App />)
  const table = await scorecard()

  expect(cells(rowOf(table, 'MAE'))).toEqual(['no data', '2,124 MW'])
  expect(cells(rowOf(table, 'MDA'))).toEqual(['no data', '63.3%'])
  expect(within(table).getByRole('columnheader', { name: /Last 7 days/ })).toHaveTextContent('5 days from Dec 2025')
  expect(within(table).getByRole('columnheader', { name: /Last 14 days/ })).toHaveTextContent('12 days from Dec 2025')
  expect(screen.getByText(/48 half-hours in the last 7 days were skipped/)).toBeInTheDocument()
})

test('history lists every scored half-hour, newest first, for 14 days or 7', async () => {
  fakeApi()
  const user = userEvent.setup()
  render(<App />)
  const length = within(await screen.findByRole('group', { name: 'History length' }))
  expect(length.getByRole('button', { name: '14 days' })).toHaveAttribute('aria-pressed', 'true')

  await user.click(within(screen.getByRole('group', { name: 'Show history as' })).getByRole('button', { name: 'Table' }))
  const historyRows = () =>
    within(screen.getByRole('table', { name: 'Forecast and actual, half-hour by half-hour' }))
      .getAllByRole('row')
      .slice(1)

  expect(historyRows()).toHaveLength(672)
  expect(cells(historyRows()[0])).toEqual(['15 Jan 09:00', '12,678', '12,242', '+436 higher'])

  await user.click(length.getByRole('button', { name: '7 days' }))
  expect(historyRows()).toHaveLength(336)
  expect(cells(historyRows().at(-1))[0]).toBe('8 Jan 09:30')
})

test('says what it is fetching while it waits, then gets out of the way', async () => {
  fakeApi()
  render(<App />)

  expect(screen.getByRole('status')).toHaveTextContent('Fetching the 09:30 forecast for Thu 15 Jan from Elexon')
  await screen.findByRole('heading', { name: 'Friday 16 January' })
  expect(screen.getByRole('status')).toBeEmptyDOMElement()
})

test("when the API fails he sees its plain message, and Try again really tries again", async () => {
  const elexonDown = 'Couldn’t get data from Elexon right now. Nothing is shown rather than guessed. Try again in a minute.'
  let calls = 0
  const requests = fakeApi(() => (++calls === 1 ? { status: 502, body: { detail: elexonDown } } : { status: 200, body: JAN15 }))
  const user = userEvent.setup()
  render(<App />)

  expect(await screen.findByRole('alert')).toHaveTextContent(elexonDown)
  expect(screen.queryByRole('heading', { name: 'Friday 16 January' })).not.toBeInTheDocument()

  await user.click(screen.getByRole('button', { name: 'Try again' }))

  expect(await screen.findByRole('heading', { name: 'Friday 16 January' })).toBeInTheDocument()
  expect(requests).toHaveLength(2)
})

test('when the network itself is down, it says so', async () => {
  vi.stubGlobal('fetch', vi.fn(() => Promise.reject(new TypeError('Failed to fetch'))))
  render(<App />)

  expect(await screen.findByRole('alert')).toHaveTextContent(
    'Couldn’t reach the server. Check your connection and try again.',
  )
})

test('the gate time is always on screen, and the footer says where the data came from and when', async () => {
  fakeApi()
  render(<App />)

  expect(screen.getByText('Gate closes 09:50')).toBeInTheDocument()
  expect(await screen.findByRole('contentinfo')).toHaveTextContent(
    'Data from Elexon BMRS: WINDFOR hourly wind forecasts and FUELHH half-hourly metered generation. Fetched 25 Oct 2026, 11:01 UK time.',
  )
})

test('an error without an explanation still tells him what happened and what to do', async () => {
  fakeApi(() => ({ status: 504, body: '<html>Gateway Timeout</html>' }))
  render(<App />)

  expect(await screen.findByRole('alert')).toHaveTextContent(
    'The server didn’t give an answer (error 504). Try again in a minute.',
  )
})
