import type { PaymentUI } from '../store'
import { money } from '../lib/format'

// The payment card. Hidden until Kiki starts charging: pending -> confirm
// state, paid -> green confirmation with the code from payment_confirmed.
export function PaymentBar({ payment }: { payment: PaymentUI }) {
  if (payment.state === 'idle') return null
  const paid = payment.state === 'paid'

  return (
    <div
      style={{
        flex: 'none',
        marginTop: 10,
        borderRadius: 4,
        padding: '11px 16px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 10,
        background: paid ? '#E4F6EC' : '#fff',
        border: `2px solid ${paid ? 'var(--ok)' : 'var(--royal)'}`,
        animation: paid ? 'kfadeup .4s ease both' : 'kbreathe 1.6s ease-in-out infinite',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 0 }}>
        <span style={{ fontSize: 18, flex: 'none' }}>{paid ? '✅' : '💳'}</span>
        <div style={{ minWidth: 0 }}>
          <div style={{ fontFamily: 'var(--serif)', fontWeight: 700, fontSize: 14, color: paid ? 'var(--ok)' : 'var(--ink)' }}>
            {paid ? 'Payment confirmed' : 'Charging your card…'}
          </div>
          <div style={{ fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--muted)', marginTop: 2 }}>
            {paid && payment.code ? `#${payment.code}` : 'awaiting confirmation'}
          </div>
        </div>
      </div>
      <span style={{ fontFamily: 'var(--mono)', fontSize: 15, fontWeight: 700, color: paid ? 'var(--ok)' : 'var(--royal-deep)', flex: 'none' }}>
        {money(payment.amount)}
      </span>
    </div>
  )
}
