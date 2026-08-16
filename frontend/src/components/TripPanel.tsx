import { useStore } from '../store'
import { buildCards, buildBudget } from '../lib/derive'
import { VendorCard } from './VendorCard'
import { FlightOptions } from './FlightOptions'
import { StageBar } from './StageBar'
import { BudgetBar } from './BudgetBar'
import { PaymentBar } from './PaymentBar'

export function TripPanel({ onPickFlight }: { onPickFlight: (flightId: string) => void }) {
  const state = useStore((s) => s)
  const { trip, stage, payment, selectedFlightId, screen } = state
  const cards = buildCards(state)
  const budget = buildBudget(trip)

  const travelers =
    screen === 'A'
      ? '— · — travelers'
      : trip
        ? `${trip.month.toUpperCase()} · ${trip.party.total} TRAVELERS`
        : '…'

  return (
    <div style={{ flex: '0 0 50%', display: 'flex', flexDirection: 'column', minWidth: 0, padding: '20px 22px', overflow: 'hidden' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 15, flex: 'none' }}>
        <span style={{ fontFamily: 'var(--serif)', fontWeight: 700, fontSize: 21 }}>The Trip</span>
        <span
          style={{
            fontFamily: 'var(--mono)',
            fontSize: 11,
            color: screen === 'A' ? 'var(--muted-2)' : '#fff',
            background: screen === 'A' ? 'var(--chip-bg)' : 'var(--royal)',
            border: screen === 'A' ? '2px solid var(--line)' : 'none',
            padding: screen === 'A' ? '4px 11px' : '5px 11px',
            borderRadius: 3,
            animation: screen === 'B' ? 'kfadeup .4s ease .15s both' : undefined,
          }}
        >
          {travelers}
        </span>
      </div>

      <StageBar stage={stage} />

      {/* cards — each renders independently from its own vendor's state */}
      <div className="kiki-scroll" style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 10, overflowY: 'auto', minHeight: 0, paddingRight: 2 }}>
        {cards.map((card) =>
          card.state === 'options' ? (
            <VendorCard key={card.key} card={card}>
              <FlightOptions options={card.options ?? []} selectedId={selectedFlightId} onPick={onPickFlight} />
            </VendorCard>
          ) : (
            <VendorCard key={card.key} card={card} />
          ),
        )}
      </div>

      <BudgetBar budget={budget} />
      <PaymentBar payment={payment} />
    </div>
  )
}
