// fakeDriver.ts — walks the fake demo script, feeding the SAME onAction the
// live SDK uses. This is the "no backend, no voice" path. DELETE for prod.

import type { OnAction } from '../contract'
import { store } from '../store'
import { fakeBackend, fakeFetchTripStatus } from '../fakeBackend'
import { FAKE_SCRIPT, resolveAction } from '../fakeScript'

/** The refetch the fake onAction uses — a stubbed /trip/status. */
export const fakeRefetch = fakeFetchTripStatus

const INTRO = "Hey! I'm Kiki. Plan out loud and I'll handle the booking."

/** Start of call (screen A -> B): reset, greet, and paint the trip meta. */
export async function seedFakeSession(): Promise<void> {
  fakeBackend.reset()
  store.set({
    orb: 'listening',
    stage: 'listening',
    trip: null,
    vendorUI: { flight: 'idle', hotel: 'idle', transport: 'idle', activities: 'idle' },
    flightOptions: null,
    selectedFlightId: null,
    constraints: [],
    payment: { state: 'idle' },
    transcript: [],
  })
  store.pushTranscript('Kiki', INTRO)
  // Initial paint — like get_trip_status: meta known, vendors NOT_BOOKED yet.
  try {
    const trip = await fakeRefetch()
    store.set({ trip })
  } catch {
    /* fake fetch never fails on seed */
  }
}

const delay = (ms: number) => new Promise((r) => setTimeout(r, ms))

/**
 * Run the full demo sequence. `signal` lets the caller cancel (Reset / End call).
 * `speed` scales every beat (1 = as written; 0.5 = twice as fast).
 */
export async function runFakeScript(
  onAction: OnAction,
  { signal, speed = 1 }: { signal?: AbortSignal; speed?: number } = {},
): Promise<void> {
  for (const step of FAKE_SCRIPT) {
    await delay(step.delay * speed)
    if (signal?.aborted) return
    if (step.say) store.pushTranscript(step.say.speaker, step.say.text)
    if (step.mutate) step.mutate()
    const action = resolveAction(step)
    if (action) await onAction(action)
  }
}
