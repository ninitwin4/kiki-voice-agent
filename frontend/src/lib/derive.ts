// derive.ts — turn (trip status + UI overlays) into the render model for each
// card. This is where "degradation-first" lives: every card computes its own
// state from its own vendor's data, independent of the others. A missing,
// slow, or errored vendor produces its own state and never touches the rest.

import type { FlightOption, TripStatus, Vendor } from '../contract'
import type { UIState, VendorUI } from '../store'

// Demo narrative toggle.
//   false = "build live": the left panel starts EMPTY and each card appears only
//           when Kiki books it; the running total climbs from $0 as bookings land.
//   true  = "start with the plan": show the backend's seeded (NOT_BOOKED) itinerary
//           upfront as `planned` cards, with the full quoted total.
// The backend always carries the full catalog plan, so this is a pure UI choice.
const SHOW_PLANNED = false

export type CardDisplayState =
  | 'empty'
  | 'searching'
  | 'options'
  // NOT_BOOKED but the backend already has details (a chosen flight, a held
  // hotel, …). Shows the itinerary as Kiki plans it, before the final booking.
  | 'quoted'
  | 'updating'
  | 'booked'
  | 'partial'
  | 'error'

export interface CardModel {
  key: string
  /** Which vendor overlay drives this card (two experiences share 'activities'). */
  vendor: Vendor
  icon: string
  /** Generic category label shown in the empty/blank state (no destination). */
  category: string
  state: CardDisplayState
  /** Bold title line once booked, e.g. "Hawaiian · HA 21 · nonstop". */
  title?: string
  /** Detail lines under the title. */
  lines?: string[]
  price?: number
  confirmation?: string
  /** Flight only: the option rows to render in the `options` state. */
  options?: FlightOption[]
}

/** Resolve the display state from an overlay + a backend status. */
function resolveState(
  overlay: VendorUI,
  booked: boolean,
  partial = false,
): CardDisplayState {
  if (overlay === 'error') return 'error'
  if (overlay === 'updating') return 'updating'
  if (overlay === 'searching') return 'searching'
  if (partial) return 'partial'
  if (booked) return 'booked'
  return 'empty'
}

function flightCard(s: UIState): CardModel {
  const f = s.trip?.flights
  const overlay = s.vendorUI.flight
  const booked = f?.status === 'BOOKED'
  const hasData = !!(f && (f.flight_no || f.carrier || f.total_price))
  let state = resolveState(overlay, booked)
  if (state === 'empty') {
    // Pre-booking options take over the card; otherwise show the chosen flight.
    if (s.flightOptions && !booked) state = 'options'
    else if (SHOW_PLANNED && hasData) state = 'quoted'
  }
  const card: CardModel = {
    key: 'flight',
    vendor: 'flight',
    icon: '✈️',
    category: 'Flight',
    state,
    options: state === 'options' ? s.flightOptions ?? undefined : undefined,
  }
  if (f && (booked || state === 'quoted')) {
    const stopsLabel = f.stops === 0 ? ' · nonstop' : f.stops ? ` · ${f.stops} stop` : ''
    card.title = [f.carrier ?? 'Flight', f.flight_no].filter(Boolean).join(' · ') + stopsLabel
    card.lines = [
      f.depart_time && f.arrive_time ? `${f.depart_time} → ${f.arrive_time}` : '',
      f.tradeoff ?? '',
    ].filter(Boolean)
    card.price = f.total_price
    card.confirmation = f.record_locator
  }
  return card
}

function hotelCard(s: UIState): CardModel {
  const h = s.trip?.hotel
  const booked = h?.status === 'BOOKED'
  const hasData = !!(h && h.name)
  let state = resolveState(s.vendorUI.hotel, booked)
  if (state === 'empty' && SHOW_PLANNED && hasData) state = 'quoted'
  const card: CardModel = { key: 'hotel', vendor: 'hotel', icon: '🏨', category: 'Stay', state }
  if (h && (booked || state === 'quoted')) {
    card.title = h.name ?? 'Hotel'
    card.lines = [
      `${h.room_type ?? ''} · ${h.nights ?? ''} nights`.trim(),
      h.note ?? '',
    ].filter(Boolean)
    card.price = h.total
    card.confirmation = h.confirmation_number
  }
  return card
}

function transportCard(s: UIState): CardModel {
  const t = s.trip?.transport
  const booked = t?.status === 'BOOKED'
  const hasData = !!(t && (t.vehicle || t.provider))
  let state = resolveState(s.vendorUI.transport, booked)
  if (state === 'empty' && SHOW_PLANNED && hasData) state = 'quoted'
  const card: CardModel = { key: 'transport', vendor: 'transport', icon: '🚐', category: 'Transport', state }
  if (t && (booked || state === 'quoted')) {
    card.title = t.vehicle ?? 'Rental'
    card.lines = [
      `${t.provider ?? ''} · ${t.days ?? ''} days`.trim(),
      t.car_seat ? t.note ?? 'car seats included' : '',
    ].filter(Boolean)
    card.price = t.total
    card.confirmation = t.confirmation_number
  }
  return card
}

/** One "Experience" slot bound to activities.items[index]. */
function experienceCard(s: UIState, index: number, icon: string): CardModel {
  const acts = s.trip?.activities
  const item = acts?.items?.[index]
  const overlay = s.vendorUI.activities

  // Within a PARTIAL set, an unbooked item is still being worked → searching.
  let effectiveOverlay = overlay
  if (overlay === 'idle' && acts?.status === 'PARTIAL' && item && item.status !== 'BOOKED') {
    effectiveOverlay = 'searching'
  }

  const booked = item?.status === 'BOOKED'
  const hasData = !!(item && item.name)
  let state = resolveState(effectiveOverlay, booked)
  if (state === 'empty' && SHOW_PLANNED && hasData) state = 'quoted'

  const card: CardModel = {
    key: `experience-${index}`,
    vendor: 'activities',
    icon,
    category: 'Experience',
    state,
  }
  if (item && (booked || state === 'quoted')) {
    card.title = item.name
    card.lines = [
      [item.date, item.time].filter(Boolean).join(' · '),
      item.kid_friendly ? 'kid-friendly' : item.provider ?? '',
    ].filter(Boolean)
    card.price = item.total
    card.confirmation = item.confirmation_number
  }
  return card
}

/** Build the fixed five slots. Each reflects ONLY its own vendor's real state. */
export function buildCards(s: UIState): CardModel[] {
  return [
    flightCard(s),
    hotelCard(s),
    transportCard(s),
    experienceCard(s, 0, '🏄'),
    experienceCard(s, 1, '🤿'),
  ]
}

export interface BudgetModel {
  spent: number | null
  cap: number
  pct: number
  over: boolean
  hasAny: boolean
}

/** Sum only what's actually BOOKED — so the total climbs live as Kiki books. */
function bookedTotal(trip: TripStatus): number {
  let sum = 0
  if (trip.flights?.status === 'BOOKED') sum += trip.flights.total_price ?? 0
  if (trip.hotel?.status === 'BOOKED') sum += trip.hotel.total ?? 0
  if (trip.transport?.status === 'BOOKED') sum += trip.transport.total ?? 0
  for (const it of trip.activities?.items ?? []) {
    if (it.status === 'BOOKED') sum += it.total ?? 0
  }
  return sum
}

export function buildBudget(trip: TripStatus | null): BudgetModel {
  const cap = trip?.totals?.budget ?? trip?.budget?.amount ?? 12000
  // build-live: booked-only running total. plan mode: the backend's quoted total.
  const spent = !trip ? 0 : SHOW_PLANNED ? trip.totals?.trip_total ?? 0 : bookedTotal(trip)
  const hasAny = spent > 0
  const pct = cap > 0 ? Math.min(100, (spent / cap) * 100) : 0
  return {
    spent: hasAny ? spent : null,
    cap,
    pct,
    over: spent > cap,
    hasAny,
  }
}
