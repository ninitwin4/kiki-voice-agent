import type { CSSProperties } from 'react'
import type { Stage } from '../contract'

const STAGES: { key: Stage; label: string }[] = [
  { key: 'listening', label: 'Listening' },
  { key: 'searching', label: 'Searching' },
  { key: 'booking', label: 'Booking' },
  { key: 'confirming', label: 'Confirming' },
]

const pillBase: CSSProperties = {
  flex: 1,
  textAlign: 'center',
  fontFamily: 'var(--mono)',
  fontSize: 10,
  padding: '8px 2px',
  borderRadius: 3,
  whiteSpace: 'nowrap',
}

export function StageBar({ stage }: { stage: Stage | null }) {
  // Not started (screen A): a dashed "ready" pill, then muted future pills.
  if (!stage) {
    return (
      <div style={{ display: 'flex', gap: 6, marginBottom: 18, flex: 'none' }}>
        <div
          style={{
            ...pillBase,
            background: 'transparent',
            border: '2px dashed var(--dash)',
            color: 'var(--ghost)',
          }}
        >
          ready
        </div>
        {STAGES.slice(1).map((s) => (
          <div key={s.key} style={{ ...pillBase, background: 'var(--track)', color: 'var(--ghost-2)' }}>
            {s.label}
          </div>
        ))}
      </div>
    )
  }

  // `updating` isn't its own pill — it lives in the Booking slot, relabeled.
  const activeKey: Stage = stage === 'updating' ? 'booking' : stage
  const activeIndex = STAGES.findIndex((s) => s.key === activeKey)

  return (
    <div style={{ display: 'flex', gap: 6, marginBottom: 18, flex: 'none' }}>
      {STAGES.map((s, i) => {
        const active = i === activeIndex
        const label = active && stage === 'updating' ? '↻ Updating' : s.label
        return (
          <div
            key={s.key}
            style={{
              ...pillBase,
              background: active ? 'var(--royal)' : 'var(--track)',
              color: active ? '#fff' : 'var(--ghost-2)',
              animation: active ? 'kfadeup .4s ease both' : undefined,
            }}
          >
            {active ? `● ${label}` : label}
          </div>
        )
      })}
    </div>
  )
}
