// store.ts — a tiny external store (no dependency) shared by the action
// handler, the fake driver, the live SDK, and every component. Components read
// slices via useStore(selector) backed by useSyncExternalStore.

import { useSyncExternalStore } from 'react'
import type {
  FlightOption,
  OrbState,
  Stage,
  TripStatus,
  Vendor,
} from './contract'

/** UI-only transient overlay a card can be in, on top of backend truth. */
export type VendorUI = 'idle' | 'searching' | 'updating' | 'error'

export interface TranscriptLine {
  id: number
  speaker: 'Kiki' | 'You'
  text: string
}

export interface Constraint {
  label: string
  satisfied: boolean
}

export interface PaymentUI {
  state: 'idle' | 'pending' | 'paid'
  amount?: number
  code?: string
}

export type ConnStatus = 'idle' | 'connecting' | 'connected' | 'error'

export interface ConnectionUI {
  status: ConnStatus
  /** Present in the error state — surfaced on the hero. */
  code?: string | number
  message?: string
}

export interface UIState {
  /** A = blank landing, B = live call. */
  screen: 'A' | 'B'
  /** Kiki's heartbeat, drives the orb. */
  orb: OrbState
  /** Current phase for the stage bar. `null` = not started (screen A). */
  stage: Stage | null
  /** The whole trip, straight from /trip/status. `null` until first refetch. */
  trip: TripStatus | null
  /** Per-vendor transient overlays the UI paints during Kiki's long waits. */
  vendorUI: Record<Vendor, VendorUI>
  /** Pre-booking flight choices (rendered directly from the payload). */
  flightOptions: FlightOption[] | null
  /** The option the user tapped (App -> Agent). */
  selectedFlightId: string | null
  /** Proof-of-understanding chips on the right panel. */
  constraints: Constraint[]
  payment: PaymentUI
  transcript: TranscriptLine[]
  /** Live SDK connection status (fake mode leaves this 'idle'). */
  connection: ConnectionUI
  /** Intent flag the live bridge watches to connect/disconnect. */
  wantConnected: boolean
  /** Bumped to (re)trigger a connect attempt — makes retry deterministic. */
  connectNonce: number
  /** How many Agent->App signals have arrived this session (live diagnostics). */
  signalCount: number
  /** The most recent signal's action type. */
  lastSignal: string | null
}

export const initialState: UIState = {
  screen: 'A',
  orb: 'idle',
  stage: null,
  trip: null,
  vendorUI: { flight: 'idle', hotel: 'idle', transport: 'idle', activities: 'idle' },
  flightOptions: null,
  selectedFlightId: null,
  constraints: [],
  payment: { state: 'idle' },
  transcript: [],
  connection: { status: 'idle' },
  wantConnected: false,
  connectNonce: 0,
  signalCount: 0,
  lastSignal: null,
}

type Listener = () => void
type Patch = Partial<UIState> | ((s: UIState) => Partial<UIState>)

class Store {
  private state: UIState = initialState
  private listeners = new Set<Listener>()
  private lineId = 0

  getSnapshot = (): UIState => this.state

  subscribe = (l: Listener): (() => void) => {
    this.listeners.add(l)
    return () => this.listeners.delete(l)
  }

  set = (patch: Patch): void => {
    const partial = typeof patch === 'function' ? patch(this.state) : patch
    this.state = { ...this.state, ...partial }
    this.listeners.forEach((l) => l())
  }

  reset = (): void => {
    this.lineId = 0
    this.state = { ...initialState, vendorUI: { ...initialState.vendorUI } }
    this.listeners.forEach((l) => l())
  }

  // --- convenience mutators used by actions / drivers ---

  setVendorUI = (vendor: Vendor, ui: VendorUI): void =>
    this.set((s) => ({ vendorUI: { ...s.vendorUI, [vendor]: ui } }))

  pushTranscript = (speaker: TranscriptLine['speaker'], text: string): void =>
    this.set((s) => ({
      transcript: [...s.transcript, { id: ++this.lineId, speaker, text }],
    }))
}

export const store = new Store()

/** Read a slice of state; re-renders only when that slice changes by Object.is. */
export function useStore<T>(selector: (s: UIState) => T): T {
  return useSyncExternalStore(store.subscribe, () => selector(store.getSnapshot()))
}
