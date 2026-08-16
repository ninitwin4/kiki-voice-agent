// fakeScript.ts — the demo sequence, walked by the Play button. Fires the §3
// client actions in demo order against the SAME onAction handler the live SDK
// uses, so swapping to live is a one-line change. DELETE for prod.
//
// The narrative is the real one (see README / BUILD_STATUS): Ni Ni's party of 2
// and RC's party of 3 plan Maui for the first week of November. Kiki books it
// all, then surfaces that early November is Maui's rainy season — and RC won't
// travel in rain. One call moves the whole trip to dry August, re-dating and
// re-pricing flights, hotel, minivan AND both activities together.
//
// Includes one step that drops transport into the `error` state (and a retry
// that recovers) so degradation is visible.

import type { AgentAction } from './contract'
import { fakeBackend } from './fakeBackend'

export interface FakeStep {
  /** ms to wait BEFORE running this step (compressed stand-in for 13–40s). */
  delay: number
  label?: string
  /** Push a transcript line (mirrors what useTranscript would deliver live). */
  say?: { speaker: 'Kiki' | 'You'; text: string }
  /** Advance the fake backend before the refetch that follows. */
  mutate?: () => void
  /** Fire a client action into onAction. A thunk lets a step read live totals. */
  action?: AgentAction | (() => AgentAction)
}

/** Resolve a step's action (thunk or literal) to a concrete AgentAction. */
export function resolveAction(step: FakeStep): AgentAction | undefined {
  if (!step.action) return undefined
  return typeof step.action === 'function' ? step.action() : step.action
}

// A demo beat is ~0.8–1.8s here; live it's Kiki's real 13–40s. Tune to taste.
// Total authored runtime ≈ 35.3s (+~1.2s of fake-fetch latency).
export const FAKE_SCRIPT: FakeStep[] = [
  // ---- the ask ----
  { delay: 600, say: { speaker: 'You', text: 'Okay — Maui. First week of November. My two plus RC’s three.' } },
  { delay: 500, action: { type: 'agent_state', payload: { state: 'thinking' } } },
  { delay: 300, action: { type: 'set_stage', payload: { stage: 'searching', vendor: 'flight' } } },
  { delay: 400, say: { speaker: 'Kiki', text: 'Five of you, two rooms, twelve thousand all-in. Let me look at flights.' } },
  { delay: 400, action: { type: 'update_constraint', payload: { label: 'Under $12k · all-in', satisfied: true } } },

  // ---- flight: options -> pick -> book ----
  { delay: 1500, action: { type: 'flight_options', payload: { options: [
    { flight_id: 'AA511', carrier: 'American', flight_no: 'AA 511', depart_time: '08:20', arrive_time: '10:55', stops: 0, price_pp: 596, total_price: 2980, recommended: true, tradeoff: 'home at 2:30p' },
    { flight_id: 'AA1620', carrier: 'American', flight_no: 'AA 1620', depart_time: '06:55', arrive_time: '12:30', stops: 1, price_pp: 512, total_price: 2560, tradeoff: 'LA connection' },
    { flight_id: 'AA742', carrier: 'American', flight_no: 'AA 742', depart_time: '09:45', arrive_time: '12:20', stops: 0, price_pp: 571, total_price: 2855, tradeoff: '6:05a return' },
  ] } } },
  { delay: 300, action: { type: 'agent_state', payload: { state: 'speaking' } } },
  { delay: 300, say: { speaker: 'Kiki', text: 'Three on American. AA 511 is my pick — nonstop both ways, home mid-afternoon.' } },
  { delay: 1400, say: { speaker: 'You', text: 'The nonstop works.' } },
  { delay: 400, action: { type: 'set_stage', payload: { stage: 'booking', vendor: 'flight' } } },
  { delay: 300, action: { type: 'agent_state', payload: { state: 'thinking' } } },
  { delay: 1200, mutate: () => fakeBackend.bookFlight(), action: { type: 'card_update', payload: { vendor: 'flight' } } },
  { delay: 300, action: { type: 'update_constraint', payload: { label: 'No pre-dawn return', satisfied: true } } },
  { delay: 300, action: { type: 'agent_state', payload: { state: 'speaking' } } },
  { delay: 200, say: { speaker: 'Kiki', text: 'Booked — and I skipped the 6 AM return. Not with a five-year-old.' } },

  // ---- hotel ----
  { delay: 500, action: { type: 'set_stage', payload: { stage: 'booking', vendor: 'hotel' } } },
  { delay: 300, action: { type: 'agent_state', payload: { state: 'thinking' } } },
  { delay: 400, say: { speaker: 'Kiki', text: 'Now two rooms on Kā‘anapali…' } },
  { delay: 1400, mutate: () => fakeBackend.bookHotel(), action: { type: 'card_update', payload: { vendor: 'hotel' } } },
  { delay: 300, action: { type: 'agent_state', payload: { state: 'speaking' } } },
  { delay: 200, say: { speaker: 'Kiki', text: 'The Westin — ocean-view double queens, five nights.' } },

  // ---- transport: fails once (degradation), then recovers ----
  { delay: 500, action: { type: 'set_stage', payload: { stage: 'booking', vendor: 'transport' } } },
  { delay: 300, action: { type: 'agent_state', payload: { state: 'thinking' } } },
  { delay: 400, say: { speaker: 'Kiki', text: 'One minivan for all five, with a car seat for Leo…' } },
  // The next fetch throws -> the transport card degrades to `error`. Everything
  // else keeps its state; the demo carries on.
  { delay: 1200, mutate: () => fakeBackend.failOnce(), action: { type: 'card_update', payload: { vendor: 'transport' } } },
  { delay: 300, say: { speaker: 'Kiki', text: 'Hmm — that rental provider didn’t respond. Retrying…' } },
  { delay: 1000, action: { type: 'set_stage', payload: { stage: 'booking', vendor: 'transport' } } },
  { delay: 1200, mutate: () => fakeBackend.bookTransport(), action: { type: 'card_update', payload: { vendor: 'transport' } } },
  { delay: 300, action: { type: 'agent_state', payload: { state: 'speaking' } } },
  { delay: 200, say: { speaker: 'Kiki', text: 'Got it — Sienna minivan, forward-facing seat included.' } },

  // ---- activities: partial (one of two) then both ----
  { delay: 500, action: { type: 'set_stage', payload: { stage: 'booking', vendor: 'activities' } } },
  { delay: 300, action: { type: 'agent_state', payload: { state: 'thinking' } } },
  { delay: 400, say: { speaker: 'Kiki', text: 'And two things all five can do — a surf lesson and Molokini…' } },
  { delay: 1200, mutate: () => fakeBackend.bookActivitiesPartial(), action: { type: 'card_update', payload: { vendor: 'activities' } } },
  { delay: 1100, mutate: () => fakeBackend.bookActivitiesAll(), action: { type: 'card_update', payload: { vendor: 'activities' } } },
  { delay: 300, action: { type: 'agent_state', payload: { state: 'speaking' } } },
  { delay: 200, say: { speaker: 'Kiki', text: 'Both booked. The surf school takes ages five and up.' } },

  // ---- the weather finding -> the cascade (the money shot) ----
  { delay: 900, action: { type: 'agent_state', payload: { state: 'thinking' } } },
  { delay: 500, say: { speaker: 'Kiki', text: 'One thing before you pay — I checked the forecast. Early November is Maui’s rainy season.' } },
  { delay: 900, say: { speaker: 'You', text: 'Oh — RC won’t travel in the rain.' } },
  { delay: 500, action: { type: 'agent_state', payload: { state: 'thinking' } } },
  { delay: 400, say: { speaker: 'Kiki', text: 'I remember. Moving the whole trip to the first week of August — warm and dry.' } },
  { delay: 1600, mutate: () => fakeBackend.reflowToAugust(), action: { type: 'trip_reflow', payload: { month: 'august' } } },
  { delay: 300, action: { type: 'agent_state', payload: { state: 'speaking' } } },
  { delay: 300, action: { type: 'update_constraint', payload: { label: 'August — dry season', satisfied: true } } },
  { delay: 300, say: { speaker: 'Kiki', text: 'Everything moved to August 5th — flights, hotel, minivan, both activities.' } },
  { delay: 900, say: { speaker: 'Kiki', text: 'Dry season runs higher: eleven-four-sixty. Still under your twelve.' } },

  // ---- the preferences Kiki kept ----
  { delay: 700, say: { speaker: 'Kiki', text: 'Two things I kept: RC’s group wants local and vegetarian — I’ve shortlisted places.' } },
  { delay: 1100, say: { speaker: 'Kiki', text: 'And Ni Ni — pack deodorant and your hair mask.' } },

  // ---- pay ----
  { delay: 700, action: { type: 'set_stage', payload: { stage: 'confirming' } } },
  { delay: 200, say: { speaker: 'Kiki', text: 'Ready to lock it in?' } },
  { delay: 1000, say: { speaker: 'You', text: 'Do it.' } },
  { delay: 400, action: { type: 'agent_state', payload: { state: 'thinking' } } },
  { delay: 600, action: () => ({ type: 'payment_pending', payload: { amount: fakeBackend.currentTotal() } }) },
  { delay: 1400, mutate: () => fakeBackend.confirmPayment('PAY-8H2K'), action: () => ({ type: 'payment_confirmed', payload: { code: 'PAY-8H2K', amount: fakeBackend.currentTotal() } }) },
  { delay: 300, action: { type: 'agent_state', payload: { state: 'speaking' } } },
  { delay: 200, say: { speaker: 'Kiki', text: 'Paid — eleven thousand four sixty. Maui in August. ✦' } },
  { delay: 1200, action: { type: 'agent_state', payload: { state: 'idle' } } },
]
