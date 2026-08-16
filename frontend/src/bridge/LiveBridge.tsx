// LiveBridge.tsx — the REAL Vocal Bridge wiring.
//
// This is a SOURCE SWAP, not a rewrite: incoming signals are routed into the
// SAME `onAction` handler the fake driver uses. Components, card states, and
// the /trip/status refetch logic are untouched. The only new surface here is a
// thin mapper at the SDK boundary + connection lifecycle.
//
// Auth: we mint the token from OUR backend (/token) via a tokenProvider — the
// SDK calls it on every connect/reconnect, so the 1-hour token is never cached
// and reused, and no API key ever touches the client.

import { useEffect, useRef } from 'react'
import {
  VocalBridgeProvider,
  useVocalBridge,
  useTranscript,
  useAgentActions,
} from '@vocalbridgeai/react'
import { ConnectionState } from '@vocalbridgeai/sdk'
import type { VocalBridgeOptions, TokenResponse } from '@vocalbridgeai/sdk'

import type { AgentAction, AgentActionType, EmitToAgent, OnAction } from '../contract'
import { fetchTripStatus, fetchVbToken, TokenError } from '../api'
import { store, useStore } from '../store'

// Display name sent to /token as `participant_name`.
const PARTICIPANT_NAME = 'Trip Planner'

// Every §3 Agent -> App action name. Each is registered on the SDK and routed,
// unchanged, into the existing onAction switch. Frozen vocabulary per CONTRACT.
const AGENT_ACTIONS: AgentActionType[] = [
  'agent_state',
  'set_stage',
  'update_constraint',
  'flight_options',
  'card_update',
  'trip_reflow',
  'payment_pending',
  'payment_confirmed',
]

/** Mint credentials from our backend. Surfaces backend errors on the hero. */
async function tokenProvider(): Promise<TokenResponse> {
  try {
    return await fetchVbToken(PARTICIPANT_NAME)
  } catch (e) {
    const err = e as TokenError
    // Surface the backend's exact code + message on the hero.
    store.set({ connection: { status: 'error', code: err.code, message: err.message }, orb: 'idle' })
    throw e
  }
}

const liveOptions: VocalBridgeOptions = {
  auth: { tokenProvider },
  participantName: PARTICIPANT_NAME,
  autoAckHeartbeat: true,
  autoPlayAudio: true,
  // Fail fast on a dead token instead of hanging the demo on retries.
  maxReconnectAttempts: 1,
  reconnectDelay: 1500,
}

// ---------------------------------------------------------------------------
// The session component — must live inside the provider to use the hooks.
// ---------------------------------------------------------------------------

function LiveSession({
  onAction,
  onEmitReady,
}: {
  onAction: OnAction
  onEmitReady?: (emit: EmitToAgent) => void
}) {
  const { state, connect, disconnect, sendAction, setMicrophoneEnabled, error } = useVocalBridge()
  const { transcript } = useTranscript()
  const { onAction: onAgentAction, lastAction } = useAgentActions()
  const wantConnected = useStore((s) => s.wantConnected)
  const connectNonce = useStore((s) => s.connectNonce)
  // The nonce we've already fired a connect() for — prevents an auto-reconnect
  // loop when a connect fails and the SDK drops back to `disconnected`.
  const attemptedNonce = useRef<number | null>(null)

  // --- 1. useAgentActions: route every §3 action into the same handler ---
  useEffect(() => {
    const unsubs = AGENT_ACTIONS.map((name) =>
      onAgentAction(name, (payload) => {
        store.set((s) => ({ signalCount: s.signalCount + 1, lastSignal: name }))
        if (import.meta.env.DEV) console.debug('[kiki] signal →', name, payload)
        void onAction({ type: name, payload } as AgentAction)
      }),
    )
    return () => unsubs.forEach((u) => u())
  }, [onAgentAction, onAction])

  // Diagnostic: log EVERY raw agent action (incl. names we don't handle) so a
  // name/envelope mismatch is obvious in the console during a live call.
  useEffect(() => {
    if (lastAction && import.meta.env.DEV) {
      const known = (AGENT_ACTIONS as string[]).includes(lastAction.action)
      console.debug(`[kiki] raw action${known ? '' : ' (UNHANDLED name!)'} →`, lastAction.action, lastAction.payload)
    }
  }, [lastAction])

  // --- 2. useTranscript: live transcript -> right panel (role -> speaker) ---
  useEffect(() => {
    const lines = transcript.map((e, i) => ({
      id: i,
      speaker: (e.role === 'agent' ? 'Kiki' : 'You') as 'Kiki' | 'You',
      text: e.text,
    }))
    store.set({ transcript: lines })
  }, [transcript])

  // --- 3. connection state -> hero + orb. NOTE: the trip panel is NOT gated on
  //     this — it's painted by the /trip/status poll below, so the left panel
  //     fills the moment the room is up, independent of when the agent joins. ---
  useEffect(() => {
    switch (state) {
      case ConnectionState.Connecting:
      case ConnectionState.Reconnecting:
        // Never clobber a surfaced error (e.g. token failure) while the SDK
        // burns through its retry attempts.
        store.set((s) => (s.connection.status === 'error' ? {} : { connection: { status: 'connecting' }, orb: 'thinking' }))
        break
      case ConnectionState.WaitingForAgent:
      case ConnectionState.Connected:
        // Room is up = we're live. Don't wait for the agent to "join" — the
        // transcript + trip poll are already flowing.
        store.set((s) => (s.connection.status === 'error' ? {} : { connection: { status: 'connected' }, orb: 'listening' }))
        break
      case ConnectionState.Disconnected:
        // Preserve an error state if one was set; otherwise go idle.
        store.set((s) => (s.connection.status === 'error' ? {} : { connection: { status: 'idle' }, orb: 'idle' }))
        break
      case ConnectionState.Disconnecting:
        break
    }
  }, [state])

  // --- 3b. Trip poll — the left panel's real source of truth. Fires an
  //     immediate paint when the user joins, then every 2s (CONTRACT §5
  //     fallback). This keeps the itinerary populating even if a client-action
  //     signal is missed, renamed, or the agent is slow to join. Signal-driven
  //     refetches (card_update etc.) still layer on top for instant updates. ---
  useEffect(() => {
    if (!wantConnected) return
    let alive = true
    const paint = () =>
      fetchTripStatus()
        .then((trip) => {
          if (alive) store.set({ trip })
        })
        .catch(() => {
          /* transient; the next tick retries */
        })
    paint()
    const id = setInterval(paint, 2000)
    return () => {
      alive = false
      clearInterval(id)
    }
  }, [wantConnected])

  // --- SDK errors (non-token, e.g. ConnectionFailed) -> hero, without
  //     clobbering the more specific message tokenProvider already surfaced ---
  useEffect(() => {
    if (!error) return
    store.set((s) =>
      s.connection.status === 'error' && s.connection.message
        ? {}
        : { connection: { status: 'error', code: error.code, message: error.message }, orb: 'idle' },
    )
  }, [error])

  // --- 4. intent flag -> connect / disconnect. Keyed on connectNonce so a
  //     Retry (same wantConnected + state) still fires a fresh attempt. The
  //     token is refetched by the SDK on every connect/reconnect. ---
  useEffect(() => {
    if (!wantConnected) {
      attemptedNonce.current = null
      if (state !== ConnectionState.Disconnected && state !== ConnectionState.Disconnecting) {
        void disconnect()
      }
      return
    }
    // Fire connect() at most ONCE per nonce. A failed attempt drops state back
    // to `disconnected`; without this guard we'd immediately reconnect forever.
    if (state === ConnectionState.Disconnected && attemptedNonce.current !== connectNonce) {
      attemptedNonce.current = connectNonce
      store.set({ connection: { status: 'connecting' }, orb: 'thinking' })
      connect()
        // A denied/absent mic must NOT drop a successful connection — swallow it.
        .then(() => setMicrophoneEnabled(true).catch(() => undefined))
        .catch((e) => {
          store.set((s) =>
            s.connection.status === 'error'
              ? {}
              : { connection: { status: 'error', message: (e as Error)?.message ?? 'Connection failed' }, orb: 'idle' },
          )
        })
    }
  }, [connectNonce, wantConnected, state, connect, disconnect, setMicrophoneEnabled])

  // --- 5. App -> Agent: hand the emit fn up so the UI can talk back ---
  useEffect(() => {
    onEmitReady?.((action) => {
      void sendAction(action.type, action.payload as Record<string, unknown>)
    })
  }, [onEmitReady, sendAction])

  return null
}

export function LiveBridge(props: {
  onAction: OnAction
  onEmitReady?: (emit: EmitToAgent) => void
}) {
  return (
    <VocalBridgeProvider options={liveOptions}>
      <LiveSession {...props} />
    </VocalBridgeProvider>
  )
}
