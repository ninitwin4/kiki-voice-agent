import type { FlightOption } from '../contract'
import { money } from '../lib/format'

// The three option rows on the flight card (rendered directly from payload —
// this is pre-booking, not yet in trip state). One is `recommended`.
export function FlightOptions({
  options,
  selectedId,
  onPick,
}: {
  options: FlightOption[]
  selectedId: string | null
  onPick: (flightId: string) => void
}) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 8 }}>
      {options.map((o, i) => {
        const selected = selectedId === o.flight_id
        return (
          <button
            key={o.flight_id}
            onClick={() => onPick(o.flight_id)}
            style={{
              textAlign: 'left',
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              padding: '8px 10px',
              borderRadius: 4,
              cursor: 'pointer',
              background: o.recommended ? '#E3F2FF' : '#fff',
              border: `2px solid ${selected ? 'var(--royal-deep)' : o.recommended ? 'var(--royal)' : 'var(--line)'}`,
              animation: `kfadeup .35s ease ${i * 0.06}s both`,
            }}
          >
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                <span style={{ fontFamily: 'var(--serif)', fontWeight: 600, fontSize: 13, color: 'var(--ink)' }}>
                  {o.carrier} · {o.flight_no}
                </span>
                {o.recommended && (
                  <span
                    style={{
                      fontFamily: 'var(--mono)',
                      fontSize: 8,
                      fontWeight: 700,
                      color: '#fff',
                      background: 'var(--royal)',
                      padding: '2px 6px',
                      borderRadius: 3,
                      letterSpacing: '.04em',
                    }}
                  >
                    KIKI’S PICK
                  </span>
                )}
              </div>
              <div style={{ fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--muted)', marginTop: 2 }}>
                {o.depart_time} → {o.arrive_time} · {o.stops === 0 ? 'nonstop' : `${o.stops} stop`}
                {o.tradeoff ? ` · ${o.tradeoff}` : ''}
              </div>
            </div>
            <div style={{ textAlign: 'right', flex: 'none' }}>
              <div style={{ fontFamily: 'var(--mono)', fontWeight: 700, fontSize: 13, color: 'var(--royal-deep)' }}>
                {money(o.total_price)}
              </div>
              <div style={{ fontFamily: 'var(--mono)', fontSize: 9, color: 'var(--ghost)' }}>
                {money(o.price_pp)}/pp
              </div>
            </div>
          </button>
        )
      })}
    </div>
  )
}
