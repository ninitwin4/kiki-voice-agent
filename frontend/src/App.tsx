import { useCallback, useMemo, useRef, useState } from 'react'
import './styles.css'

import type { EmitToAgent, OnAction } from './contract'
import { makeOnAction } from './actions'
import { fetchTripStatus } from './api'
import { store, useStore } from './store'

// Fake demo driver (no backend/voice) — kept as a demo-day safety net.
import { fakeBackend } from './fakeBackend'
import { fakeRefetch, seedFakeSession, runFakeScript } from './bridge/fakeDriver'
// Real Vocal Bridge wiring.
import { LiveBridge } from './bridge/LiveBridge'

import { HeroStrip } from './components/HeroStrip'
import { TripPanel } from './components/TripPanel'
import { KikiPanel } from './components/KikiPanel'
import { DemoControls } from './components/DemoControls'

type Mode = 'fake' | 'live'

// The fake script and the live SDK feed the SAME onAction handler — this is a
// source swap, not a rewrite. The default source is chosen by env; a dev toggle
// (bottom bar) flips it live at runtime.
const INITIAL_MODE: Mode = import.meta.env.VITE_USE_FAKE === 'false' ? 'live' : 'fake'

export default function App() {
  const screen = useStore((s) => s.screen)
  const orb = useStore((s) => s.orb)
  const trip = useStore((s) => s.trip)
  const constraints = useStore((s) => s.constraints)
  const transcript = useStore((s) => s.transcript)
  const connection = useStore((s) => s.connection)
  const signalCount = useStore((s) => s.signalCount)
  const lastSignal = useStore((s) => s.lastSignal)

  const [mode, setMode] = useState<Mode>(INITIAL_MODE)
  const [playing, setPlaying] = useState(false)
  // Bumped on each fresh session so the hero's elapsed clock restarts at 0:00.
  const [runKey, setRunKey] = useState(0)
  const abortRef = useRef<AbortController | null>(null)
  // Emit fn handed up by LiveBridge (App -> Agent), used for flight picks.
  const liveEmitRef = useRef<EmitToAgent | null>(null)

  // Same handler in both modes; only the refetch source differs.
  const onAction = useMemo<OnAction>(
    () => makeOnAction(mode === 'fake' ? fakeRefetch : fetchTripStatus),
    [mode],
  )

  // App -> Agent: the screen talks back to Kiki.
  const emit: EmitToAgent = useCallback(
    (action) => {
      if (action.type === 'user_picked_flight') {
        store.set({ selectedFlightId: action.payload.flight_id })
      }
      if (mode === 'live') {
        // Kiki confirms + books, then fires card_update over the wire.
        liveEmitRef.current?.(action)
        return
      }
      // Fake mode + not autoplaying: simulate Kiki confirming + booking.
      if (action.type === 'user_picked_flight' && !abortRef.current) {
        store.pushTranscript('You', 'Let’s go with that one.')
        fakeBackend.bookFlight()
        void onAction({ type: 'card_update', payload: { vendor: 'flight' } })
      }
    },
    [mode, onAction],
  )

  // "Add Kiki to the call →" — fake seeds the scripted session; live connects.
  const enterCall = useCallback(async () => {
    setRunKey((k) => k + 1)
    if (mode === 'fake') {
      store.set({ screen: 'B' })
      await seedFakeSession()
    } else {
      store.set((s) => ({
        screen: 'B',
        wantConnected: true,
        connection: { status: 'connecting' },
        connectNonce: s.connectNonce + 1,
      }))
    }
  }, [mode])

  const endCall = useCallback(() => {
    abortRef.current?.abort()
    abortRef.current = null
    setPlaying(false)
    // reset() flips wantConnected false -> LiveBridge disconnects; screen -> A.
    store.reset()
  }, [])

  const retryConnect = useCallback(() => {
    store.set((s) => ({
      wantConnected: true,
      connection: { status: 'connecting' },
      connectNonce: s.connectNonce + 1,
    }))
  }, [])

  // Fake-only: walk the scripted demo.
  const playDemo = useCallback(async () => {
    if (playing) return
    abortRef.current?.abort()
    setRunKey((k) => k + 1)
    store.set({ screen: 'B' })
    await seedFakeSession()
    const ac = new AbortController()
    abortRef.current = ac
    setPlaying(true)
    try {
      await runFakeScript(onAction, { signal: ac.signal })
    } finally {
      if (abortRef.current === ac) {
        abortRef.current = null
        setPlaying(false)
      }
    }
  }, [playing, onAction])

  const toggleMode = useCallback((next: Mode) => {
    endCall()
    setMode(next)
  }, [endCall])

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', overflow: 'hidden', background: 'var(--bg)' }}>
      <HeroStrip
        screen={screen}
        trip={trip}
        onEndCall={endCall}
        resetKey={runKey}
        connection={connection}
        onRetry={retryConnect}
      />

      <div style={{ flex: 1, display: 'flex', minHeight: 0 }}>
        <TripPanel onPickFlight={(id) => emit({ type: 'user_picked_flight', payload: { flight_id: id } })} />
        <div style={{ width: 2, flex: 'none', background: 'var(--line)' }} />
        <KikiPanel
          screen={screen}
          orb={orb}
          constraints={constraints}
          transcript={transcript}
          onAddKiki={enterCall}
        />
      </div>

      {/* Live SDK provider — mounted only in live mode; feeds the same onAction. */}
      {mode === 'live' && (
        <LiveBridge onAction={onAction} onEmitReady={(e) => (liveEmitRef.current = e)} />
      )}

      <DemoControls
        mode={mode}
        onToggleMode={toggleMode}
        screen={screen}
        playing={playing}
        signalCount={signalCount}
        lastSignal={lastSignal}
        onScreenA={endCall}
        onScreenB={enterCall}
        onPlay={playDemo}
        onReset={endCall}
      />
    </div>
  )
}
