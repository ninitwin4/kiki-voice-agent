import { useEffect, useRef } from 'react'
import type { TranscriptLine } from '../store'

// The live, speaker-labeled transcript on the right panel. Auto-scrolls to the
// newest line.
export function Transcript({ lines }: { lines: TranscriptLine[] }) {
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [lines.length])

  return (
    <div
      style={{
        flex: 1,
        minHeight: 0,
        marginTop: 16,
        borderTop: '2px solid var(--line)',
        paddingTop: 14,
        display: 'flex',
        flexDirection: 'column',
        animation: 'kfadeup .4s ease .3s both',
      }}
    >
      <div style={{ fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--ghost-2)', letterSpacing: '.12em', marginBottom: 11, flex: 'none' }}>
        LIVE TRANSCRIPT
      </div>
      <div className="kiki-scroll" style={{ flex: 1, minHeight: 0, overflowY: 'auto', fontSize: 14, lineHeight: 1.55, color: 'var(--ink-soft)', paddingRight: 4 }}>
        {lines.map((l) => (
          <div key={l.id} style={{ marginBottom: 9, animation: 'kfadeup .4s ease both' }}>
            <span style={{ color: l.speaker === 'Kiki' ? 'var(--royal-deep)' : 'var(--muted)', fontWeight: 700 }}>
              {l.speaker}
            </span>
            &nbsp;&nbsp;{l.text}
          </div>
        ))}
        <div ref={endRef} />
      </div>
    </div>
  )
}
