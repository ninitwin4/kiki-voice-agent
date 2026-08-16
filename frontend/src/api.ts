// api.ts — the ONLY real backend calls the UI makes.
//   1. POST /trip/status  -> the entire trip (initial paint + refetch-on-signal)
//   2. POST /token        -> a short-lived Vocal Bridge token (backend owns the key)
//
// Option A: the UI never trusts signal payloads for booked data. Every booked
// number comes from here, so numbers can never drift from the backend.

import type { TripStatus } from './contract'

const BASE = import.meta.env.VITE_API_BASE as string

if (!BASE) {
  // Fail loud in dev — a missing base URL silently breaks every refetch.
  console.warn('[kiki] VITE_API_BASE is not set. Add it to .env')
}

/** POST /trip/status · body {} · no auth · ~75ms warm. Returns the whole trip. */
export async function fetchTripStatus(signal?: AbortSignal): Promise<TripStatus> {
  const res = await fetch(`${BASE}/trip/status`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: '{}',
    signal,
  })
  if (!res.ok) {
    throw new Error(`/trip/status ${res.status}`)
  }
  return (await res.json()) as TripStatus
}

/**
 * Credentials the Vocal Bridge SDK needs to connect. Mirrors the SDK's
 * `TokenResponse` (it wants `url`; our backend returns `livekit_url`, which we
 * map). The API key stays on the backend — we never call VB directly.
 */
export interface VbToken {
  url: string
  token: string
  room_name: string
  participant_identity: string
  expires_in: number
  agent_mode?: string
}

/** A structured token failure, so the hero can surface code + message. */
export class TokenError extends Error {
  code: string | number
  constructor(message: string, code: string | number) {
    super(message)
    this.name = 'TokenError'
    this.code = code
  }
}

/**
 * POST /token · body { participant_name } -> VB session credentials.
 *
 * The token lives 1 hour; the SDK calls this on every connect/reconnect, so we
 * NEVER cache and reuse. On non-200 the backend returns
 * `{ error: { code, message } }` (503 not_configured · 502 vb_rejected ·
 * 502 vb_unreachable) — we throw a TokenError carrying both.
 */
export async function fetchVbToken(participantName: string, signal?: AbortSignal): Promise<VbToken> {
  let res: Response
  try {
    res = await fetch(`${BASE}/token`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ participant_name: participantName }),
      signal,
    })
  } catch (e) {
    throw new TokenError('Could not reach the token service.', 'network_error')
  }

  if (!res.ok) {
    let code: string | number = res.status
    let message = `Token request failed (${res.status}).`
    try {
      const body = await res.json()
      code = body?.error?.code ?? res.status
      message = body?.error?.message ?? message
    } catch {
      /* non-JSON error body — keep the status defaults */
    }
    throw new TokenError(message, code)
  }

  const data = await res.json()
  return {
    // Backend returns `livekit_url`; the SDK's TokenResponse wants `url`.
    url: data.url ?? data.livekit_url,
    token: data.token,
    room_name: data.room_name,
    participant_identity: data.participant_identity,
    expires_in: data.expires_in,
    agent_mode: data.agent_mode,
  }
}

/** A refetch function: fake mode swaps in a stubbed backend, live uses fetch. */
export type Refetch = (signal?: AbortSignal) => Promise<TripStatus>
