// actions.ts — the ONE handler both the fake driver and the live SDK feed.
//
// Signals are thin triggers. Most of them just tell the UI WHEN to refetch
// /trip/status; the UI renders booked data only from that refetch. The two
// exceptions rendered straight from payload are `flight_options` and the
// `update_constraint` label (per the contract).
//
// Degradation-first: a refetch failure degrades ONLY the acting card to `error`.
// Every other card keeps its last-known state — one vendor down never blocks
// the rest, and never blocks the reflow.

import type { AgentAction, OnAction, Vendor } from './contract'
import type { Refetch } from './api'
import { store } from './store'

const ALL_VENDORS: Vendor[] = ['flight', 'hotel', 'transport', 'activities']

/**
 * Build the action handler. `refetch` is injected so swapping fake <-> live is
 * a one-line change (fake passes a stubbed backend, live passes fetchTripStatus).
 */
export function makeOnAction(refetch: Refetch): OnAction {
  /** Pull the truth and paint it, clearing the given card overlays to idle. */
  async function refetchInto(clear: Vendor[], onError?: () => void) {
    try {
      const trip = await refetch()
      store.set((s) => {
        const vendorUI = { ...s.vendorUI }
        for (const v of clear) vendorUI[v] = 'idle'
        return { trip, vendorUI }
      })
    } catch (err) {
      console.warn('[kiki] refetch failed', err)
      onError?.()
    }
  }

  return async function onAction(action: AgentAction): Promise<void> {
    switch (action.type) {
      // The AI's heartbeat — always reflect it, essential given the long waits.
      case 'agent_state':
        store.set({ orb: action.payload.state })
        return

      // Fired BEFORE a tool runs — advance the stage bar and light the relevant
      // card so the 13–40s wait reads as intentional, before any data returns.
      case 'set_stage': {
        const { stage, vendor } = action.payload
        store.set({ stage })
        if (vendor) {
          store.setVendorUI(vendor, stage === 'updating' ? 'updating' : 'searching')
        }
        return
      }

      // Rendered directly from payload (pre-booking, not yet in trip state).
      case 'update_constraint':
        store.set((s) => ({
          constraints: [
            ...s.constraints,
            { label: action.payload.label, satisfied: action.payload.satisfied },
          ],
        }))
        return

      // Rendered directly from payload — the 3 option rows on the flight card.
      // Clear the flight overlay so the card shows the options, not the pulse.
      case 'flight_options':
        store.set((s) => ({
          flightOptions: action.payload.options,
          vendorUI: { ...s.vendorUI, flight: 'idle' },
        }))
        return

      // A booking tool returned -> refetch, re-render that card + budget. On
      // failure, degrade ONLY this card to `error`; the rest carry the demo.
      case 'card_update': {
        const { vendor } = action.payload
        await refetchInto(
          [vendor],
          () => store.setVendorUI(vendor, 'error'),
        )
        // flight options are consumed once the flight is booked.
        if (vendor === 'flight') store.set({ flightOptions: null })
        return
      }

      // The money shot (Aug->Oct): pulse every card `updating`, refetch, and
      // re-render everything. Highest priority — must survive a card in `error`.
      case 'trip_reflow': {
        store.set((s) => {
          const vendorUI = { ...s.vendorUI }
          for (const v of ALL_VENDORS) vendorUI[v] = 'updating'
          return { stage: 'updating', vendorUI }
        })
        await refetchInto(ALL_VENDORS, () => {
          // Even if the refetch hiccups, clear the pulse so cards fall back to
          // their last-known state rather than pulsing forever.
          store.set((s) => {
            const vendorUI = { ...s.vendorUI }
            for (const v of ALL_VENDORS) if (vendorUI[v] === 'updating') vendorUI[v] = 'idle'
            return { vendorUI }
          })
        })
        return
      }

      case 'payment_pending':
        store.set({ payment: { state: 'pending', amount: action.payload.amount } })
        return

      case 'payment_confirmed':
        store.set({
          payment: {
            state: 'paid',
            amount: action.payload.amount,
            code: action.payload.code,
          },
        })
        // Refetch to flip the trip `status` to confirmed.
        await refetchInto([])
        return
    }
  }
}
