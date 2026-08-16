import type { CSSProperties } from 'react'
import type { OrbState } from '../contract'

// The pixel-art Kiki sprite, rebuilt from the frozen design (blue head, yellow
// sprout + cheeks, dark eyes). Resting = two eye-dots, no mouth. Once she's in
// the call (any non-idle state) the mouth appears.
export function KikiOrb({ state }: { state: OrbState }) {
  const awake = state !== 'idle'
  const headRows = [48, 72, 88, 96, 96, 96, 96, 80, 60, 32]

  return (
    <div
      style={{
        animation: 'kfloat 3.6s ease-in-out infinite',
        position: 'relative',
        zIndex: 2,
        imageRendering: 'pixelated',
      }}
    >
      <div style={{ position: 'relative', width: 96, height: 96 }}>
        {/* sprout */}
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: '50%',
            transform: 'translateX(-50%)',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
          }}
        >
          <div style={{ width: 8, height: 8, background: 'var(--sun)' }} />
          <div style={{ width: 8, height: 6, background: 'var(--sun)', marginLeft: 8 }} />
          <div style={{ width: 4, height: 8, background: 'var(--royal-ink)' }} />
        </div>

        {/* head */}
        <div
          style={{
            position: 'absolute',
            top: 16,
            left: 0,
            width: 96,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
          }}
        >
          {headRows.map((w, i) => (
            <div key={i} style={{ width: w, height: 8, background: 'var(--royal)' }} />
          ))}
        </div>

        {/* cheeks */}
        <div style={{ position: 'absolute', top: 56, left: 15, width: 9, height: 6, background: 'var(--sun)' }} />
        <div style={{ position: 'absolute', top: 56, right: 15, width: 9, height: 6, background: 'var(--sun)' }} />

        {/* eyes */}
        <div style={{ position: 'absolute', top: 46, left: 29, width: 7, height: 7, background: 'var(--eye)' }} />
        <div style={{ position: 'absolute', top: 46, left: 61, width: 7, height: 7, background: 'var(--eye)' }} />

        {/* mouth — only once awake */}
        {awake && (
          <div
            style={{
              position: 'absolute',
              top: 63,
              left: 40,
              width: 16,
              height: 12,
              background: 'var(--eye)',
              borderRadius: '0 0 5px 5px',
              animation: 'kfadeup .3s ease .1s both',
            }}
          />
        )}
      </div>
    </div>
  )
}

// A small pixel cloud, reused as decoration.
export function PixelCloud({ style }: { style?: CSSProperties }) {
  return (
    <div
      style={{
        width: 5,
        height: 5,
        background: '#fff',
        boxShadow:
          '5px 0 #fff,10px 0 #fff,15px 0 #fff,-5px 5px #fff,0 5px #fff,5px 5px #fff,10px 5px #fff,15px 5px #fff,20px 5px #fff,-10px 10px #fff,-5px 10px #fff,0 10px #fff,5px 10px #fff,10px 10px #fff,15px 10px #fff,20px 10px #fff,25px 10px #fff',
        ...style,
      }}
    />
  )
}
