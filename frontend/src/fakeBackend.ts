// fakeBackend.ts — an in-memory stand-in for POST /trip/status so the whole
// loop builds & tests with no backend and no voice. The fake script mutates
// this snapshot as steps run; `fakeFetchTripStatus` returns the current truth,
// exactly like the real endpoint. DELETE alongside fakeScript.ts for prod.
//
// The data here mirrors the real backend fixtures (backend/mocks/*.json) and
// the real cascade: November (rainy, $9,170) -> August (dry, $11,460). Numbers
// were verified against a live /trip/status + /trip/rebook run — keep them in
// sync if the fixtures change.

import type { TripStatus } from './contract'

const CURRENCY = 'USD'
const BUDGET = 12000

/** Build a fresh trip: meta known (as if `configure_trip` ran), nothing booked. */
function baseTrip(): TripStatus {
  return {
    trip_id: 'TRIP-MAUI-2026',
    trip_name: 'Maui trip — Ni Ni & RC',
    status: 'planning',
    month: 'november',
    origin: 'SFO',
    destination: 'OGG',
    dates: {
      start: '2026-11-02',
      end: '2026-11-07',
      nights: 5,
      label: 'first week of November',
      season: 'rainy',
    },
    party: {
      adults: 4,
      children: 1,
      total: 5,
      rooms: 2,
      // Kept short: the hero strip uppercases this next to "GROUP TRIP ·".
      note: "Ni Ni's 2 + RC's 3",
      travelers: [
        { name: 'Ni Ni', type: 'adult' },
        { name: 'Ana', type: 'adult' },
        { name: 'RC', type: 'adult' },
        { name: 'Mia', type: 'adult' },
        { name: 'Leo', type: 'child', age: 5 },
      ],
    },
    budget: { amount: BUDGET, currency: CURRENCY, note: 'all-in, five travelers' },
    preferences: {
      no_early_return: true,
      note: "RC won't travel in the rain · no pre-dawn returns",
    },
    constraint: '',
    flights: { status: 'NOT_BOOKED' },
    hotel: { status: 'NOT_BOOKED' },
    transport: { status: 'NOT_BOOKED' },
    activities: { status: 'NOT_BOOKED', items: [] },
    totals: emptyTotals(),
    payments: [],
  }
}

function emptyTotals() {
  return {
    currency: CURRENCY,
    flights: 0,
    hotel: 0,
    transport: 0,
    activities: 0,
    trip_total: 0,
    budget: BUDGET,
    over_budget_by: 0,
    within_budget: true,
    flights_quoted: false,
  }
}

let trip: TripStatus = baseTrip()

/** When true, the next fetch throws — simulates a provider we couldn't reach. */
let failNext = false

/** Recompute totals from whatever vendors are currently booked. */
function reprice() {
  const flights = trip.flights.total_price ?? 0
  const hotel = trip.hotel.total ?? 0
  const transport = trip.transport.total ?? 0
  const activities = trip.activities.items
    .filter((i) => i.status === 'BOOKED')
    .reduce((sum, i) => sum + (i.total ?? 0), 0)
  const trip_total = flights + hotel + transport + activities
  const over = trip_total - BUDGET
  trip.totals = {
    currency: CURRENCY,
    flights,
    hotel,
    transport,
    activities,
    trip_total,
    budget: BUDGET,
    over_budget_by: over > 0 ? over : 0,
    within_budget: trip_total <= BUDGET,
    flights_quoted: flights > 0,
  }
}

// ---------------------------------------------------------------------------
// The fake fetch + control surface the fake script drives.
// ---------------------------------------------------------------------------

/** Same signature/latency feel as the real endpoint (~75ms warm). */
export async function fakeFetchTripStatus(): Promise<TripStatus> {
  await delay(80)
  if (failNext) {
    failNext = false
    throw new Error('fake provider timeout')
  }
  // Return a deep-ish clone so consumers can't mutate our source of truth.
  return structuredClone(trip)
}

export const fakeBackend = {
  reset() {
    trip = baseTrip()
    failNext = false
  },

  /** Make the very next fetch throw (degradation demo). */
  failOnce() {
    failNext = true
  },

  /** Tier A — the recommended nonstop (November pricing). */
  bookFlight() {
    trip.flights = {
      status: 'BOOKED',
      tier: 'A',
      flight_id: 'AA511',
      carrier: 'American Airlines',
      flight_no: 'AA 511',
      depart_time: '08:20',
      arrive_time: '10:55',
      stops: 0,
      price_pp: 596,
      total_price: 2980,
      return_flight_no: 'AA 512',
      return_depart_time: '14:30',
      return_arrive_time: '22:10',
      tradeoff: 'nonstop both ways · afternoon flight home',
      record_locator: 'KX4RQP',
    }
    reprice()
  },

  bookHotel() {
    trip.hotel = {
      status: 'BOOKED',
      name: "The Westin Maui Resort & Spa, Ka'anapali",
      room_type: 'Ocean-view double queen',
      rooms: 2,
      check_in: '2026-11-02',
      check_out: '2026-11-07',
      nightly_rate: 480,
      nights: 5,
      total: 4800,
      note: 'two rooms · off-season rate',
      confirmation_number: 'WMR-88213',
    }
    reprice()
  },

  bookTransport() {
    trip.transport = {
      status: 'BOOKED',
      provider: 'Maui Family Car Rentals',
      vehicle: 'Toyota Sienna minivan (seats 7)',
      pickup_location: 'OGG — Kahului Airport',
      pickup_date: '2026-11-02',
      dropoff_date: '2026-11-07',
      car_seat: true,
      car_seat_fee_per_day: 9,
      daily_rate: 71,
      total: 400,
      days: 5,
      note: 'one minivan for all 5 · child car seat',
      confirmation_number: 'MFC-4471',
    }
    reprice()
  },

  /** First activity books (PARTIAL: one of two). November pricing. */
  bookActivitiesPartial() {
    trip.activities = {
      status: 'PARTIAL',
      items: [
        {
          activity_id: 'surf',
          name: 'Beginner group surfing lesson',
          provider: 'Maui Surf School — Lahaina',
          kid_friendly: true,
          date: '2026-11-03',
          time: '09:00',
          duration: '2h',
          price_pp: 79,
          participants: 5,
          total: 395,
          status: 'BOOKED',
          confirmation_number: 'MSS-9021',
        },
        {
          activity_id: 'snorkel',
          name: 'Molokini Crater snorkeling tour',
          provider: "Molokini Express — Ma'alaea Harbor",
          kid_friendly: true,
          date: '2026-11-05',
          time: '07:00',
          duration: '4h 30m',
          price_pp: 119,
          participants: 5,
          total: 595,
          status: 'NOT_BOOKED',
        },
      ],
    }
    reprice()
  },

  /** Second activity books (both done). */
  bookActivitiesAll() {
    if (trip.activities.items[1]) {
      trip.activities.items[1].status = 'BOOKED'
      trip.activities.items[1].confirmation_number = 'MEX-3345'
    }
    trip.activities.status = 'BOOKED'
    reprice()
  },

  /**
   * The cascade: RC won't travel in the rain, so the whole trip shifts from
   * rainy November to dry August — and EVERY vendor re-dates and re-prices,
   * activities included. Dry season costs more ($9,170 -> $11,460), which is
   * the honest outcome and still inside the $12k budget.
   */
  reflowToAugust() {
    trip.month = 'august'
    trip.constraint = 'August — warm and dry, no rain'
    trip.dates = {
      start: '2026-08-05',
      end: '2026-08-10',
      nights: 5,
      label: 'first week of August',
      season: 'dry',
    }
    if (trip.flights.status === 'BOOKED') {
      trip.flights.flight_id = 'AA289'
      trip.flights.flight_no = 'AA 289'
      trip.flights.depart_time = '08:15'
      trip.flights.arrive_time = '10:50'
      trip.flights.return_flight_no = 'AA 290'
      trip.flights.return_depart_time = '14:25'
      trip.flights.return_arrive_time = '22:05'
      trip.flights.price_pp = 720
      trip.flights.total_price = 3600
    }
    if (trip.hotel.status === 'BOOKED') {
      trip.hotel.check_in = '2026-08-05'
      trip.hotel.check_out = '2026-08-10'
      trip.hotel.nightly_rate = 620
      trip.hotel.total = 6200
      trip.hotel.note = 'two rooms · dry-season rate'
    }
    if (trip.transport.status === 'BOOKED') {
      trip.transport.pickup_date = '2026-08-05'
      trip.transport.dropoff_date = '2026-08-10'
      trip.transport.daily_rate = 89
      trip.transport.total = 490
    }
    // Activities re-date and re-price too — matching the real backend, which
    // moves 11-03 -> 08-06 and 11-05 -> 08-08. Booked status is preserved.
    for (const item of trip.activities.items) {
      if (item.activity_id === 'surf') {
        item.date = '2026-08-06'
        item.price_pp = 95
        item.total = 475
      }
      if (item.activity_id === 'snorkel') {
        item.date = '2026-08-08'
        item.price_pp = 139
        item.total = 695
      }
    }
    reprice()
  },

  confirmPayment(code: string) {
    reprice()
    const amount = trip.totals.trip_total
    trip.status = 'confirmed'
    trip.payments = [
      {
        confirmation_code: code,
        amount,
        currency: CURRENCY,
        method: 'Visa •• 4417',
        status: 'confirmed',
        processed_at: '2026-08-05T18:41:00Z',
      },
    ]
    return amount
  },

  /** Current all-in total, so the script can quote payment_pending honestly. */
  currentTotal() {
    reprice()
    return trip.totals.trip_total
  },
}

function delay(ms: number) {
  return new Promise((r) => setTimeout(r, ms))
}
