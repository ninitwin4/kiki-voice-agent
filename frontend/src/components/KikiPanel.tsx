import type { OrbState } from '../contract'
import type { Constraint, TranscriptLine } from '../store'
import { KikiOrb, PixelCloud } from './KikiOrb'
import { Chips } from './Chips'
import { Transcript } from './Transcript'

function Waveform({ active }: { active: boolean }) {
  // 10 bars mirrored around the centre; still (short) when not speaking/listening.
  const delays = [0.2, 0.28, 0.36, 0.44, 0.52, 0.6, 0.52, 0.44, 0.36, 0.28]
  return (
    <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'center', gap: 3, height: 34, marginBottom: 9 }}>
      {delays.map((d, i) => (
        <div
          key={i}
          style={{
            width: 4,
            height: 30,
            transformOrigin: 'bottom',
            background: 'var(--royal)',
            borderRadius: 2,
            animation: active ? `kwave .9s ease-in-out ${d}s infinite` : undefined,
            transform: active ? undefined : 'scaleY(.2)',
            opacity: active ? 1 : 0.5,
          }}
        />
      ))}
    </div>
  )
}

const STATE_LABEL: Record<OrbState, string> = {
  idle: 'resting…',
  listening: '● listening…',
  thinking: '● thinking…',
  speaking: '● speaking…',
}

export function KikiPanel({
  screen,
  orb,
  micMuted = false,
  constraints,
  transcript,
  onAddKiki,
}: {
  screen: 'A' | 'B'
  orb: OrbState
  /** While muted, Kiki can't hear — so never claim "listening…". */
  micMuted?: boolean
  constraints: Constraint[]
  transcript: TranscriptLine[]
  onAddKiki: () => void
}) {
  const awake = orb !== 'idle'
  // Kiki can still think and speak while you're muted; only "listening" is false.
  const mutedListening = micMuted && orb === 'listening'
  const stateColor = mutedListening ? 'var(--amber)' : orb === 'idle' ? 'var(--ghost-2)' : 'var(--royal-deep)'
  const stateLabel = mutedListening ? '🔇 muted — Kiki can’t hear you' : STATE_LABEL[orb]

  return (
    <div
      style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        minWidth: 0,
        padding: '20px 22px',
        background: 'linear-gradient(180deg, var(--bg) 0%, var(--panel-tint) 210px)',
        overflow: 'hidden',
      }}
    >
      {/* sprite + clouds */}
      <div style={{ position: 'relative', height: 140, flex: 'none', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <PixelCloud style={{ position: 'absolute', top: 16, left: '9%', opacity: 0.75 }} />
        <PixelCloud style={{ position: 'absolute', top: 6, right: '13%', transform: 'scale(.72)', opacity: 0.6 }} />
        <KikiOrb state={orb} />
      </div>

      {/* state + waveform */}
      <div style={{ flex: 'none', textAlign: 'center', marginTop: 2 }}>
        {screen === 'B' ? (
          <Waveform active={awake} />
        ) : (
          <div style={{ height: 34, marginBottom: 9 }} />
        )}
        <div style={{ fontFamily: 'var(--mono)', fontSize: 12, color: stateColor, fontWeight: 700 }}>
          {screen === 'A' ? 'resting…' : stateLabel}
        </div>
      </div>

      {screen === 'A' ? (
        // ---- SCREEN A: the invite (the only bright thing) ----
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center', padding: '0 24px', gap: 14 }}>
          <div style={{ fontFamily: 'var(--serif)', fontWeight: 700, fontSize: 24, lineHeight: 1.3, color: 'var(--ink)' }}>
            Say <span style={{ color: 'var(--royal-deep)' }}>“Hey Kiki, join us”</span>
            <br />
            and just talk.
          </div>
          <div style={{ fontSize: 14, color: 'var(--muted)', lineHeight: 1.5, maxWidth: 340 }}>
            Kiki books the whole trip out loud — flights, stay, transport, the fun stuff — and keeps it all on budget.
          </div>
          <button
            onClick={onAddKiki}
            style={{
              marginTop: 10,
              fontFamily: 'var(--serif)',
              fontWeight: 700,
              fontSize: 16,
              color: '#fff',
              background: 'var(--royal)',
              border: 'none',
              borderRadius: 4,
              padding: '14px 26px',
              cursor: 'pointer',
              boxShadow: '0 6px 18px -6px rgba(24,131,255,.7)',
            }}
          >
            Add Kiki to the call →
          </button>
        </div>
      ) : (
        // ---- SCREEN B: constraint chips + live transcript ----
        <div style={{ flex: 1, minHeight: 0, marginTop: 16, display: 'flex', flexDirection: 'column' }}>
          <Chips constraints={constraints} />
          <Transcript lines={transcript} />
        </div>
      )}
    </div>
  )
}
