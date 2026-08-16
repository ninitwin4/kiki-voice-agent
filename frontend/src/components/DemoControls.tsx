// DemoControls — the bottom bar. Holds the signal-source toggle (Fake ↔ Live)
// and, in fake mode, the demo playback controls. The source toggle is the
// demo-day safety net: flip to Fake instantly if the live agent misbehaves.

import type { CSSProperties } from 'react'

type Mode = 'fake' | 'live'

function pill(active: boolean): CSSProperties {
  return {
    fontFamily: 'var(--sans)',
    fontWeight: 700,
    fontSize: 13,
    padding: '9px 16px',
    borderRadius: 4,
    cursor: 'pointer',
    border: `2px solid ${active ? 'var(--royal)' : 'var(--line)'}`,
    background: active ? 'var(--royal)' : '#fff',
    color: active ? '#fff' : 'var(--muted)',
  }
}

function seg(active: boolean): CSSProperties {
  return {
    fontFamily: 'var(--mono)',
    fontWeight: 700,
    fontSize: 12,
    padding: '7px 12px',
    borderRadius: 3,
    cursor: 'pointer',
    border: 'none',
    background: active ? 'var(--royal-deep)' : 'transparent',
    color: active ? '#fff' : 'var(--muted-2)',
  }
}

export function DemoControls({
  mode,
  onToggleMode,
  screen,
  playing,
  signalCount,
  lastSignal,
  onScreenA,
  onScreenB,
  onPlay,
  onReset,
}: {
  mode: Mode
  onToggleMode: (next: Mode) => void
  screen: 'A' | 'B'
  playing: boolean
  /** Live-mode diagnostics: Agent->App signals received this session. */
  signalCount: number
  lastSignal: string | null
  onScreenA: () => void
  onScreenB: () => void
  onPlay: () => void
  onReset: () => void
}) {
  return (
    <div
      style={{
        height: 56,
        flex: 'none',
        background: 'var(--panel-tint)',
        borderTop: '2px solid var(--line)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 10,
      }}
    >
      {/* signal source */}
      <span style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--ghost)', marginRight: 2 }}>SOURCE</span>
      <div style={{ display: 'flex', border: '2px solid var(--line)', borderRadius: 4, overflow: 'hidden', background: '#fff' }}>
        <button style={seg(mode === 'fake')} onClick={() => onToggleMode('fake')}>
          Fake script
        </button>
        <button style={seg(mode === 'live')} onClick={() => onToggleMode('live')}>
          ● Live SDK
        </button>
      </div>

      <span style={{ width: 1, height: 24, background: 'var(--line)', margin: '0 6px' }} />

      {mode === 'fake' ? (
        <>
          <button style={pill(screen === 'A')} onClick={onScreenA}>
            A · Blank
          </button>
          <button style={pill(screen === 'B')} onClick={onScreenB}>
            B · Live call
          </button>
          <button
            style={{ ...pill(false), color: playing ? 'var(--ghost-2)' : 'var(--royal-deep)', borderColor: 'var(--royal)', cursor: playing ? 'default' : 'pointer' }}
            onClick={onPlay}
            disabled={playing}
          >
            {playing ? '▮▮ Playing…' : '▶ Play demo'}
          </button>
          <button style={pill(false)} onClick={onReset}>
            ↺ Reset
          </button>
        </>
      ) : (
        <>
          <span
            title="Agent→App signals received (set_stage, card_update, …). If this stays 0 during a call, Kiki isn't firing client actions."
            style={{
              fontFamily: 'var(--mono)',
              fontSize: 11,
              color: signalCount > 0 ? 'var(--royal-deep)' : 'var(--ghost)',
              display: 'flex',
              alignItems: 'center',
              gap: 7,
            }}
          >
            <span style={{ fontSize: 13 }}>⚡</span>
            {signalCount > 0
              ? `${signalCount} signal${signalCount === 1 ? '' : 's'} · last: ${lastSignal}`
              : 'voice-driven — waiting for Kiki’s signals'}
          </span>
          <button style={pill(false)} onClick={onReset}>
            ↺ End / Reset
          </button>
        </>
      )}
    </div>
  )
}
