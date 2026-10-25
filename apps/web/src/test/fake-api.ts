import { vi } from 'vitest'
import type { DecisionResponse } from '../api/types.gen.ts'
import recorded from './decision-2026-01-15-0930.json'

/** The real API answer for today = 15 Jan, slot 09:30, recorded from live Elexon. */
export const JAN15 = recorded as DecisionResponse

type Reply = { status: number; body: unknown }

/**
 * Fakes the network edge only: every fetch to /api/decision is answered by `reply`,
 * and each requested URL is remembered so tests can check what the page asked for.
 */
export function fakeApi(reply: (url: URL) => Reply = () => ({ status: 200, body: JAN15 })) {
  const requests: URL[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn((input: RequestInfo | URL) => {
      const url = new URL(String(input), 'http://localhost')
      requests.push(url)
      const { status, body } = reply(url)
      return Promise.resolve(
        new Response(JSON.stringify(body), {
          status,
          headers: { 'content-type': 'application/json' },
        }),
      )
    }),
  )
  return requests
}
