import type { DecisionResponse } from './api/types.gen.ts'
import { type Choice, toQuery } from './simulation.ts'

/** Something to read: every message here is shown on screen as-is. */
export class ApiError extends Error {}

function detailOf(body: unknown): string | null {
  if (typeof body === 'object' && body !== null && 'detail' in body) {
    const { detail } = body
    if (typeof detail === 'string') return detail
  }
  return null
}

export async function fetchDecision(choice: Choice, signal: AbortSignal): Promise<DecisionResponse> {
  let response: Response
  try {
    response = await fetch(`/api/decision?${toQuery(choice)}`, { signal })
  } catch (error) {
    if (signal.aborted) throw error
    throw new ApiError('Couldn’t reach the server. Check your connection and try again.')
  }
  const body: unknown = await response.json().catch(() => null)
  if (!response.ok) {
    const fallback = `The server didn’t give an answer (error ${response.status}). Try again in a minute.`
    throw new ApiError(detailOf(body) ?? fallback)
  }
  // The shape is the API's own OpenAPI contract (types generated from it, drift-checked).
  return body as DecisionResponse
}
