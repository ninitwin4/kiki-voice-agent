import { useEffect, useState } from 'react'
import type { CSSProperties } from 'react'
import type { TripStatus } from '../contract'
import type { ConnectionUI } from '../store'
import { PixelCloud } from './KikiOrb'

function useElapsed(active: boolean, resetKey: number): string {
  const [s, setS] = useState(0)
  useEffect(() => {
    if (!active) return
    setS(0)
    const id = setInterval(() => setS((v) => v + 1), 1000)
    return () => clearInterval(id)
  }, [active, resetKey])
  const mm = Math.floor(s / 60)
  const ss = String(s % 60).padStart(2, '0')
  return `${mm}:${ss}`
}

const clockLabel: CSSProperties = {
  fontFamily: 'var(--mono)',
  fontSize: 11,
  letterSpacing: '.05em',
  position: 'relative',
  zIndex: 2,
}

const muteBtn = (muted: boolean): CSSProperties => ({
  fontFamily: 'var(--mono)',
  fontSize: 11,
  fontWeight: 700,
  color: muted ? 'var(--amber)' : 'var(--ink-soft)',
  background: muted ? 'var(--amber-bg)' : '#fff',
  padding: '4px 11px',
  borderRadius: 3,
  border: `2px solid ${muted ? 'var(--amber-line)' : 'var(--line)'}`,
  cursor: 'pointer',
  whiteSpace: 'nowrap',
})

const endBtn = (bg: string): CSSProperties => ({
  fontFamily: 'var(--mono)',
  fontSize: 11,
  fontWeight: 700,
  color: '#fff',
  background: bg,
  padding: '6px 13px',
  borderRadius: 3,
  border: 'none',
  cursor: 'pointer',
  whiteSpace: 'nowrap',
})

export function HeroStrip({
  screen,
  trip,
  onEndCall,
  resetKey = 0,
  connection = { status: 'idle' },
  onRetry,
  micMuted = false,
  onToggleMute,
}: {
  screen: 'A' | 'B'
  trip: TripStatus | null
  onEndCall: () => void
  /** Bumped on each fresh session so the elapsed clock restarts at 0:00. */
  resetKey?: number
  /** Live SDK connection status (fake mode stays 'idle'). */
  connection?: ConnectionUI
  /** Retry a failed connect (live mode). */
  onRetry?: () => void
  /** Mic mute state + toggle, shown while the call is up. */
  micMuted?: boolean
  onToggleMute?: () => void
}) {
  const elapsed = useElapsed(screen === 'B', resetKey)

  // Title flips from "A new trip" to the real destination once it's known.
  const title = screen === 'A' ? 'A new trip' : trip?.trip_name ?? 'A new trip'
  const meta =
    screen === 'A'
      ? 'GROUP TRIP · NOT STARTED'
      : trip
        ? `GROUP TRIP · ${(trip.party.note ?? `${trip.party.total} travelers`).toUpperCase()}`
        : 'GROUP TRIP'

  return (
    <div
      style={{
        height: 54,
        flex: 'none',
        background: 'linear-gradient(180deg, var(--bg-hero-top), var(--bg))',
        borderBottom: '2px solid var(--line)',
        display: 'flex',
        alignItems: 'center',
        padding: '0 22px',
        gap: 16,
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      <PixelCloud style={{ position: 'absolute', top: 12, left: 210, opacity: 0.7 }} />

      <span
        style={{
          fontFamily: 'var(--serif)',
          fontWeight: 700,
          fontSize: 20,
          color: screen === 'A' ? 'var(--muted)' : 'var(--royal-deep)',
          position: 'relative',
          zIndex: 2,
          animation: screen === 'B' ? 'kfadeup .4s ease both' : undefined,
        }}
      >
        {title} {screen === 'B' && '✦'}
      </span>
      <span style={{ ...clockLabel, color: screen === 'A' ? 'var(--ghost)' : 'var(--muted)' }}>{meta}</span>

      <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 12, position: 'relative', zIndex: 2 }}>
        {screen === 'A' ? (
          <span
            style={{
              fontFamily: 'var(--mono)',
              fontSize: 11,
              fontWeight: 700,
              color: 'var(--muted-2)',
              background: 'var(--chip-bg)',
              border: '2px solid var(--line)',
              padding: '5px 13px',
              borderRadius: 3,
              display: 'flex',
              alignItems: 'center',
              gap: 7,
            }}
          >
            <span style={{ width: 7, height: 7, borderRadius: '50%', background: 'var(--ghost-3)' }} />
            idle
          </span>
        ) : connection.status === 'connecting' ? (
          <span style={{ ...clockLabel, color: 'var(--royal-deep)', fontSize: 12, fontWeight: 700, display: 'flex', alignItems: 'center', gap: 7 }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--royal)', animation: 'kdot 1.2s infinite' }} />
            connecting…
          </span>
        ) : connection.status === 'error' ? (
          <>
            <span
              title={connection.code ? `code: ${connection.code}` : undefined}
              style={{
                fontFamily: 'var(--mono)',
                fontSize: 11,
                fontWeight: 700,
                color: 'var(--amber)',
                background: 'var(--amber-bg)',
                border: '2px solid var(--amber-line)',
                padding: '5px 12px',
                borderRadius: 3,
                display: 'flex',
                alignItems: 'center',
                gap: 7,
                maxWidth: 320,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              ⚠ {connection.message ?? "Couldn't connect to Kiki"}
            </span>
            {onRetry && (
              <button onClick={onRetry} style={endBtn('var(--royal)')}>
                ↻ Retry
              </button>
            )}
            <button onClick={onEndCall} style={endBtn('var(--danger)')}>
              ✕ End call
            </button>
          </>
        ) : (
          <>
            <span style={{ ...clockLabel, color: 'var(--ink-soft)', fontSize: 12, display: 'flex', alignItems: 'center', gap: 7 }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--danger)', animation: 'kdot 1.4s infinite' }} />
              {elapsed}
            </span>
            {onToggleMute && (
              <button
                onClick={onToggleMute}
                style={muteBtn(micMuted)}
                aria-pressed={micMuted}
                aria-label={micMuted ? 'Unmute microphone' : 'Mute microphone'}
                title={micMuted ? 'Kiki can’t hear you — click to unmute' : 'Mute your microphone'}
              >
                {micMuted ? '🔇 Muted' : '🎙 Mute'}
              </button>
            )}
            <button onClick={onEndCall} style={endBtn('var(--danger)')}>
              ✕ End call
            </button>
          </>
        )}
      </div>
    </div>
  )
}
