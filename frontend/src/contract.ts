// contract.ts — the frozen shared vocabulary, copied from CONTRACT.md.
// Change CONTRACT.md first, then this file. Never the reverse.

// ---------------------------------------------------------------------------
// 1. Backend truth: the shape of POST /trip/status
// ---------------------------------------------------------------------------

/** Real vendor statuses the backend returns. PARTIAL is activities-only. */
export type BackendStatus = 'NOT_BOOKED' | 'BOOKED' | 'PARTIAL';

export interface TripDates {
  start: string;
  end: string;
  nights: number;
  label: string;
  season: string;
}

export interface Traveler {
  name: string;
  type: 'adult' | 'child';
  age?: number;
}

export interface Party {
  adults: number;
  children: number;
  total: number;
  rooms: number;
  note?: string;
  travelers: Traveler[];
}

export interface Budget {
  amount: number;
  currency: string;
  note?: string;
}

export interface Preferences {
  no_early_return?: boolean;
  note?: string;
}

export interface Flights {
  status: BackendStatus;
  tier?: string;
  flight_id?: string;
  carrier?: string;
  flight_no?: string;
  depart_time?: string;
  arrive_time?: string;
  stops?: number;
  price_pp?: number;
  total_price?: number;
  return_flight_no?: string;
  return_depart_time?: string;
  return_arrive_time?: string;
  tradeoff?: string;
  record_locator?: string;
}

export interface Hotel {
  status: BackendStatus;
  name?: string;
  room_type?: string;
  rooms?: number;
  check_in?: string;
  check_out?: string;
  nightly_rate?: number;
  nights?: number;
  total?: number;
  note?: string;
  confirmation_number?: string;
}

export interface Transport {
  status: BackendStatus;
  provider?: string;
  vehicle?: string;
  pickup_location?: string;
  pickup_date?: string;
  dropoff_date?: string;
  car_seat?: boolean;
  car_seat_fee_per_day?: number;
  daily_rate?: number;
  days?: number;
  total?: number;
  note?: string;
  confirmation_number?: string;
}

export interface ActivityItem {
  activity_id: string;
  name: string;
  provider?: string;
  kid_friendly?: boolean;
  date?: string;
  time?: string;
  duration?: string;
  price_pp?: number;
  participants?: number;
  total?: number;
  note?: string;
  status: BackendStatus;
  confirmation_number?: string;
}

export interface Activities {
  status: BackendStatus;
  items: ActivityItem[];
}

export interface Totals {
  currency: string;
  flights: number;
  hotel: number;
  transport: number;
  activities: number;
  trip_total: number;
  budget: number;
  over_budget_by: number;
  within_budget: boolean;
  flights_quoted: boolean;
}

export interface Payment {
  confirmation_code: string;
  amount: number;
  currency: string;
  method?: string;
  status: string;
  processed_at?: string;
}

export interface TripStatus {
  trip_id: string;
  trip_name: string;
  status: string;
  month: string;
  origin: string;
  destination: string;
  dates: TripDates;
  party: Party;
  budget: Budget;
  preferences: Preferences;
  constraint: string;
  flights: Flights;
  hotel: Hotel;
  transport: Transport;
  activities: Activities;
  totals: Totals;
  payments: Payment[];
}

// ---------------------------------------------------------------------------
// 3. Client Actions Contract (Agent -> App) — the frozen action vocabulary
// ---------------------------------------------------------------------------

export type Vendor = 'flight' | 'hotel' | 'transport' | 'activities';

export type OrbState = 'idle' | 'listening' | 'thinking' | 'speaking';

export type Stage =
  | 'listening'
  | 'searching'
  | 'booking'
  | 'updating'
  | 'confirming';

/** One flight option, rendered directly from the flight_options payload. */
export interface FlightOption {
  flight_id: string;
  carrier: string;
  flight_no: string;
  depart_time: string;
  arrive_time: string;
  stops: number;
  price_pp: number;
  total_price: number;
  recommended?: boolean;
  tradeoff?: string;
}

// Each Agent->App action, keyed by its `type`, with its payload shape.
export type AgentAction =
  | { type: 'agent_state'; payload: { state: OrbState } }
  // NOTE: `vendor` is an optional UI hint so set_stage can light the right
  // card. Strict readers ignore it; the demo/Kiki config supplies it.
  | { type: 'set_stage'; payload: { stage: Stage; vendor?: Vendor } }
  | { type: 'update_constraint'; payload: { label: string; satisfied: boolean } }
  | { type: 'flight_options'; payload: { options: FlightOption[] } }
  | { type: 'card_update'; payload: { vendor: Vendor } }
  | { type: 'trip_reflow'; payload: { month: string } }
  | { type: 'payment_pending'; payload: { amount: number } }
  | { type: 'payment_confirmed'; payload: { code: string; amount: number } };

export type AgentActionType = AgentAction['type'];

// App -> Agent (the screen talks back to Kiki)
export type AppAction =
  | { type: 'user_picked_flight'; payload: { flight_id: string } }
  | { type: 'user_removed_item'; payload: { vendor: string } };

/** The single handler both the fake driver and the live SDK feed into. */
export type OnAction = (action: AgentAction) => void | Promise<void>;

/** Kiki-side callback the UI uses to talk back (flight pick / remove). */
export type EmitToAgent = (action: AppAction) => void;
