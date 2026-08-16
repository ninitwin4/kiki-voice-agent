import { useEffect, useRef, useState } from 'react'
import type { CSSProperties, ReactNode } from 'react'
import type { CardModel, CardDisplayState } from '../lib/derive'
import { money } from '../lib/format'

// ---- per-state visual tokens ----------------------------------------------

function containerStyle(state: CardDisplayState): CSSProperties {
  const base: CSSProperties = {
    borderRadius: 4,
    display: 'flex',
    alignItems: 'stretch',
    flex: 'none',
    transition: 'border-color .3s ease, background .3s ease',
  }
  switch (state) {
    case 'empty':
      return { ...base, background: 'var(--card-empty-bg)', border: '2px dashed var(--dash)', opacity: 0.6 }
    case 'searching':
      return { ...base, background: '#fff', border: '2px solid var(--royal)', animation: 'kcardwake .4s ease both, kbreathe 2s ease-in-out .4s infinite' }
    case 'options':
      return { ...base, background: '#fff', border: '2px solid var(--royal)', animation: 'kcardwake .4s ease both' }
    case 'updating':
      return { ...base, background: '#fff', border: '2px solid var(--royal)', animation: 'kbreathe 1.6s ease-in-out infinite' }
    case 'quoted':
      // Planned but not booked — visible, but calmer than a confirmed booking.
      return { ...base, background: 'var(--panel-tint)', border: '2px solid var(--line)' }
    case 'booked':
    case 'partial':
      return { ...base, background: '#fff', border: '2px solid #DCEBFF' }
    case 'error':
      return { ...base, background: 'var(--amber-bg)', border: '2px solid var(--amber)', animation: 'kbreathe-amber 1.8s ease-in-out infinite' }
  }
}

function iconStyle(state: CardDisplayState): CSSProperties {
  const base: CSSProperties = {
    width: 48,
    flex: 'none',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: 20,
  }
  if (state === 'empty')
    return { ...base, background: 'var(--card-icon-bg)', borderRight: '2px dashed var(--dash)', opacity: 0.7 }
  if (state === 'error')
    return { ...base, background: '#FBEAD3', borderRight: '2px solid var(--amber-line)' }
  if (state === 'quoted')
    return { ...base, background: 'var(--card-empty-bg)', borderRight: '2px solid var(--line)' }
  return { ...base, background: '#E3F2FF', borderRight: '2px solid #BFDDFF' }
}

function Chip({ state }: { state: CardDisplayState }) {
  const map: Record<CardDisplayState, { text: string; fg: string; bg: string } | null> = {
    empty: null,
    searching: { text: 'searching', fg: 'var(--royal-deep)', bg: '#E3F2FF' },
    options: { text: 'choose', fg: 'var(--royal-deep)', bg: '#E3F2FF' },
    quoted: { text: 'planned', fg: 'var(--muted)', bg: 'var(--chip-bg)' },
    updating: { text: 'updating', fg: 'var(--royal-deep)', bg: '#E3F2FF' },
    booked: { text: '✓ booked', fg: 'var(--ok)', bg: '#E4F6EC' },
    partial: { text: '1 of 2', fg: 'var(--royal-deep)', bg: '#E3F2FF' },
    error: { text: 'error', fg: '#fff', bg: 'var(--amber)' },
  }
  const c = map[state]
  if (!c) return null
  return (
    <span
      style={{
        fontFamily: 'var(--mono)',
        fontSize: 9,
        fontWeight: 700,
        color: c.fg,
        background: c.bg,
        padding: '2px 7px',
        borderRadius: 3,
        whiteSpace: 'nowrap',
        flex: 'none',
      }}
    >
      {c.text}
    </span>
  )
}

// ---- the card -------------------------------------------------------------

export function VendorCard({ card, children }: { card: CardModel; children?: ReactNode }) {
  const { state } = card
  const titleColor = state === 'empty' ? 'var(--ghost)' : 'var(--ink)'

  // Flash the card once when its meaningful content changes (a booking lands, a
  // plan updates) so the left panel visibly tracks what the call is doing —
  // whether the change arrived via a signal or the /trip/status poll.
  const sig = `${state}|${card.title ?? ''}|${card.price ?? ''}`
  const prevSig = useRef(sig)
  const [flash, setFlash] = useState(false)
  useEffect(() => {
    if (sig !== prevSig.current) {
      prevSig.current = sig
      setFlash(true)
      const id = setTimeout(() => setFlash(false), 900)
      return () => clearTimeout(id)
    }
  }, [sig])

  // Don't fight the states that already animate (searching/updating/options).
  const alreadyAnimated = state === 'searching' || state === 'updating' || state === 'options'
  const container =
    flash && !alreadyAnimated
      ? { ...containerStyle(state), animation: 'kflash .9s ease' }
      : containerStyle(state)

  return (
    <div style={container}>
      <div style={iconStyle(state)}>{card.icon}</div>

      <div style={{ flex: 1, padding: '11px 14px', minWidth: 0, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
        {/* header row: category/title + state chip */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
          <span style={{ fontFamily: 'var(--serif)', fontWeight: 600, fontSize: 14, color: titleColor, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {state === 'booked' || state === 'partial' || state === 'quoted' ? card.title ?? card.category : card.category}
          </span>
          <Chip state={state} />
        </div>

        {/* searching / updating subline */}
        {(state === 'searching' || state === 'updating') && (
          <div style={{ fontSize: 11, color: 'var(--royal)', fontFamily: 'var(--mono)', marginTop: 3 }}>
            {state === 'updating' ? 'Re-pricing… ▮▮▯' : 'Kiki’s looking… ▮▮▯'}
          </div>
        )}

        {/* error subline */}
        {state === 'error' && (
          <div style={{ fontSize: 11, color: 'var(--amber)', fontFamily: 'var(--mono)', marginTop: 3 }}>
            Couldn’t reach provider — retrying…
          </div>
        )}

        {/* booked / partial / quoted details */}
        {(state === 'booked' || state === 'partial' || state === 'quoted') && (
          <>
            {card.lines?.map((l, i) => (
              <div key={i} style={{ fontSize: 12, color: 'var(--muted)', marginTop: i === 0 ? 4 : 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {l}
              </div>
            ))}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginTop: 6, gap: 8 }}>
              <span style={{ fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--ghost)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {card.confirmation ? `#${card.confirmation}` : ''}
              </span>
              {card.price != null && (
                <span style={{ fontFamily: 'var(--mono)', fontSize: 13, fontWeight: 700, color: 'var(--royal-deep)', flex: 'none' }}>
                  {money(card.price)}
                </span>
              )}
            </div>
          </>
        )}

        {/* options (flight) rendered as children */}
        {state === 'options' && children}
      </div>
    </div>
  )
}
