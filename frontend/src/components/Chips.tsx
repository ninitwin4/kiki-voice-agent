import type { Constraint } from '../store'

// Proof-of-understanding chips on the right panel — each fades in as Kiki
// catches a constraint (rendered directly from the update_constraint label).
export function Chips({ constraints }: { constraints: Constraint[] }) {
  if (constraints.length === 0) return null
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 7, marginBottom: 12, flex: 'none' }}>
      {constraints.map((c, i) => (
        <span
          key={`${c.label}-${i}`}
          style={{
            fontFamily: 'var(--mono)',
            fontSize: 11,
            color: c.satisfied ? 'var(--royal-deep)' : 'var(--muted)',
            background: c.satisfied ? '#E3F2FF' : 'var(--chip-bg)',
            border: `2px solid ${c.satisfied ? '#BFDDFF' : 'var(--line)'}`,
            padding: '4px 10px',
            borderRadius: 3,
            display: 'inline-flex',
            alignItems: 'center',
            gap: 6,
            animation: 'kfadeup .4s ease both',
          }}
        >
          <span aria-hidden style={{ color: c.satisfied ? 'var(--ok)' : 'var(--ghost-2)' }}>
            {c.satisfied ? '✓' : '•'}
          </span>
          {c.label}
        </span>
      ))}
    </div>
  )
}
