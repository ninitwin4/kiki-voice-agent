import type { BudgetModel } from '../lib/derive'
import { money, moneyShort } from '../lib/format'

export function BudgetBar({ budget }: { budget: BudgetModel }) {
  const { spent, cap, pct, over, hasAny } = budget
  const barColor = over ? 'var(--amber)' : 'var(--royal)'
  const totalColor = !hasAny ? 'var(--ghost-2)' : over ? 'var(--amber)' : 'var(--royal-deep)'

  return (
    <div
      style={{
        flex: 'none',
        marginTop: 14,
        background: 'var(--bg)',
        border: '2px solid var(--line)',
        borderRadius: 4,
        padding: '12px 16px',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 8 }}>
        <span style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--muted)', letterSpacing: '.06em' }}>
          RUNNING TOTAL
        </span>
        <span style={{ fontFamily: 'var(--mono)', fontSize: 15, fontWeight: 700, color: totalColor }}>
          {hasAny ? money(spent) : '—'}{' '}
          <span style={{ color: 'var(--ghost-3)', fontSize: 12 }}>/ {hasAny ? moneyShort(cap) : '—'}</span>
        </span>
      </div>

      <div style={{ height: 9, background: 'var(--track)', borderRadius: 6, overflow: 'hidden' }}>
        <div
          style={{
            width: `${hasAny ? Math.max(pct, 2) : 0}%`,
            height: '100%',
            background: hasAny ? barColor : 'var(--ghost-2)',
            transition: 'width .5s ease, background .3s ease',
          }}
        />
      </div>

      <div style={{ fontSize: 11, color: over ? 'var(--amber)' : 'var(--ghost)', marginTop: 7, fontFamily: 'var(--mono)' }}>
        {!hasAny
          ? 'Nothing planned yet'
          : over
            ? `Over by ${money(spent! - cap)} — trimming`
            : `${money(cap - spent!)} left under budget`}
      </div>
    </div>
  )
}
