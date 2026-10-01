#!/usr/bin/env node
// record-demo.mjs — records the scripted Kiki demo (fake driver) to MP4 for the
// portfolio: a sped-up silent loop plus a full-speed cut, and a poster frame.
//
// Zero dependencies, macOS only:
//   - drives the installed Google Chrome (headless, throwaway profile) over the
//     DevTools Protocol using Node's built-in WebSocket — no Playwright;
//   - captures frames with Page.startScreencast (a frame on every visual change);
//   - hands them to encode-frames.swift (AVFoundation H.264) — no ffmpeg.
//
// The bottom demo bar (SOURCE / Play / Reset) is cropped out, so the video shows
// only the product. Holds on the landing and final states are added in the encoder.
//
// Usage — the dev server must be running (npm run dev):
//   npm run record:demo
//   node scripts/record-demo.mjs --url http://localhost:5180 --out demo-video

import { spawn, execFileSync } from 'node:child_process'
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const HERE = dirname(fileURLToPath(import.meta.url))
const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'

// Viewport: 1280x1000 CSS px fits all five cards + budget + payment with no
// scrolling. Captured at 1.5x so text stays crisp after encoding to 1440 wide.
const VIEWPORT = { width: 1280, height: 1000, dsf: 1.5 }

// Each output: playback speed for the demo itself, plus holds (in OUTPUT seconds)
// on the landing state before Play and on the final booked state at the end.
const OUTPUTS = [
  { name: 'kiki-demo-loop.mp4', speed: 1.75, holdStart: 1.0, holdEnd: 2.5, bitrate: 1_800_000 },
  { name: 'kiki-demo-full.mp4', speed: 1.0, holdStart: 1.5, holdEnd: 3.0, bitrate: 1_800_000 },
]

const args = parseArgs(process.argv.slice(2))
const URL_ = args.url ?? 'http://localhost:5180'
const OUT_DIR = resolve(args.out ?? 'demo-video')

function parseArgs(argv) {
  const out = {}
  for (let i = 0; i < argv.length; i += 2) out[argv[i].replace(/^--/, '')] = argv[i + 1]
  return out
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

function fail(msg) {
  console.error(`\n✗ ${msg}`)
  process.exit(1)
}

// --- minimal CDP client over Node's built-in WebSocket ---------------------
class CDP {
  constructor(ws) {
    this.ws = ws
    this.nextId = 0
    this.pending = new Map()
    this.handlers = new Map()
    ws.addEventListener('message', (e) => {
      const msg = JSON.parse(e.data)
      if (msg.id !== undefined) {
        const p = this.pending.get(msg.id)
        this.pending.delete(msg.id)
        if (msg.error) p?.reject(new Error(`${msg.error.message} (${msg.error.code})`))
        else p?.resolve(msg.result)
      } else {
        for (const h of this.handlers.get(msg.method) ?? []) h(msg.params)
      }
    })
  }
  send(method, params = {}) {
    const id = ++this.nextId
    this.ws.send(JSON.stringify({ id, method, params }))
    return new Promise((resolve, reject) => this.pending.set(id, { resolve, reject }))
  }
  on(method, fn) {
    this.handlers.set(method, [...(this.handlers.get(method) ?? []), fn])
  }
  once(method) {
    return new Promise((resolve) => {
      const fn = (p) => {
        this.handlers.set(method, (this.handlers.get(method) ?? []).filter((h) => h !== fn))
        resolve(p)
      }
      this.on(method, fn)
    })
  }
  async evaluate(expression) {
    const r = await this.send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true })
    if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description ?? r.exceptionDetails.text)
    return r.result.value
  }
}

async function launchChrome(profileDir) {
  if (!existsSync(CHROME)) fail(`Google Chrome not found at ${CHROME}`)
  const proc = spawn(
    CHROME,
    [
      '--headless=new',
      '--remote-debugging-port=0', // pick a free port; Chrome writes it to DevToolsActivePort
      `--user-data-dir=${profileDir}`,
      '--no-first-run',
      '--no-default-browser-check',
      '--hide-scrollbars',
      '--mute-audio',
      // Never let timers throttle — a throttled tab stretches the scripted demo.
      '--disable-background-timer-throttling',
      '--disable-renderer-backgrounding',
      '--disable-backgrounding-occluded-windows',
      `--window-size=${VIEWPORT.width},${VIEWPORT.height}`,
      // Screencast frames follow the real surface, not emulated DSF — so render
      // the surface itself at retina scale or frames come back at 1x.
      `--force-device-scale-factor=${VIEWPORT.dsf}`,
      'about:blank',
    ],
    { stdio: 'ignore' },
  )
  const portFile = join(profileDir, 'DevToolsActivePort')
  for (let i = 0; i < 100 && !existsSync(portFile); i++) await sleep(100)
  if (!existsSync(portFile)) fail('Chrome did not start (no DevToolsActivePort).')
  const [port] = readFileSync(portFile, 'utf8').trim().split('\n')
  const targets = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()
  const page = targets.find((t) => t.type === 'page')
  if (!page) fail('No page target in headless Chrome.')
  const ws = new WebSocket(page.webSocketDebuggerUrl)
  await new Promise((res, rej) => {
    ws.addEventListener('open', res, { once: true })
    ws.addEventListener('error', rej, { once: true })
  })
  return { proc, cdp: new CDP(ws), ws }
}

async function main() {
  // Fail fast with a useful message if the dev server isn't up.
  try {
    const r = await fetch(URL_)
    if (!r.ok) throw new Error(`HTTP ${r.status}`)
  } catch (e) {
    fail(`Can't reach ${URL_} (${e.message}). Start the UI first: npm run dev`)
  }

  const work = mkdtempSync(join(tmpdir(), 'kiki-rec-'))
  const framesDir = join(work, 'frames')
  mkdirSync(framesDir)
  mkdirSync(OUT_DIR, { recursive: true })

  console.log(`▸ recording ${URL_}`)
  const { proc, cdp, ws } = await launchChrome(join(work, 'profile'))

  try {
    await cdp.send('Page.enable')
    await cdp.send('Runtime.enable')
    await cdp.send('Emulation.setDeviceMetricsOverride', {
      width: VIEWPORT.width,
      height: VIEWPORT.height,
      deviceScaleFactor: VIEWPORT.dsf,
      mobile: false,
    })
    const loaded = cdp.once('Page.loadEventFired')
    await cdp.send('Page.navigate', { url: URL_ })
    await loaded

    // Web fonts come from Google Fonts — wait for all three, or the first
    // frames would show fallback fonts.
    const fontsOk = await cdp.evaluate(`
      Promise.all([
        document.fonts.load('16px Nunito'),
        document.fonts.load('700 16px "Zilla Slab"'),
        document.fonts.load('12px "Space Mono"'),
      ]).then(() => document.fonts.ready).then(() =>
        document.fonts.check('16px Nunito') &&
        document.fonts.check('700 16px "Zilla Slab"') &&
        document.fonts.check('12px "Space Mono"'))
    `)
    if (!fontsOk) console.warn('  ! web fonts did not load (offline?) — video will use fallback fonts')

    // Must be on the fake driver with the Play button available.
    const ready = await cdp.evaluate(
      `[...document.querySelectorAll('button')].some(b => b.textContent.includes('Play demo'))`,
    )
    if (!ready) fail('No "▶ Play demo" button — is VITE_USE_FAKE=true and the SOURCE toggle on "Fake script"?')

    // Crop everything from the demo bar down (it sits last in the app column).
    const barTop = await cdp.evaluate(`(() => {
      const bar = document.getElementById('root')?.firstElementChild?.lastElementChild
      return bar && bar.textContent.includes('SOURCE') ? bar.getBoundingClientRect().top : null
    })()`)
    if (!barTop) fail('Could not locate the demo control bar to crop.')
    // A fraction, not pixels: frame size depends on the capture scale, and the
    // encoder applies this to whatever resolution the frames actually arrive at.
    const cropFraction = barTop / VIEWPORT.height

    // --- capture ---
    const frames = []
    let n = 0
    cdp.on('Page.screencastFrame', ({ data, metadata, sessionId }) => {
      const file = `f${String(n++).padStart(6, '0')}.jpg`
      writeFileSync(join(framesDir, file), Buffer.from(data, 'base64'))
      frames.push({ file, t: metadata.timestamp })
      void cdp.send('Page.screencastFrameAck', { sessionId })
    })
    await cdp.send('Page.startScreencast', {
      format: 'jpeg',
      quality: 92,
      maxWidth: Math.round(VIEWPORT.width * VIEWPORT.dsf),
      maxHeight: Math.round(VIEWPORT.height * VIEWPORT.dsf),
      everyNthFrame: 1,
    })
    await sleep(800) // let the landing state land in at least one frame

    // Click Play and timestamp it in the page (same wall clock as frame metadata).
    const playAt = await cdp.evaluate(`(() => {
      [...document.querySelectorAll('button')].find(b => b.textContent.includes('Play demo')).click()
      return Date.now() / 1000
    })()`)
    process.stdout.write('  playing')

    // Wait for "Playing…" to flip back to "▶ Play demo".
    let doneAt = null
    const deadline = Date.now() + 120_000
    await sleep(500)
    while (Date.now() < deadline) {
      doneAt = await cdp.evaluate(`(() => {
        const b = [...document.querySelectorAll('button')].find(b => /Play demo|Playing/.test(b.textContent))
        return b && b.textContent.includes('Play demo') ? Date.now() / 1000 : null
      })()`)
      if (doneAt) break
      process.stdout.write('.')
      await sleep(1000)
    }
    console.log('')
    if (!doneAt) fail('Demo never finished playing (timed out after 120s).')

    await sleep(800) // a little extra so the final state is fully settled
    await cdp.send('Page.stopScreencast')
    await sleep(300)

    const played = doneAt - playAt
    console.log(`  captured ${frames.length} frames · demo ran ${played.toFixed(1)}s (script is ~35s)`)
    if (played > 45) console.warn('  ! demo ran long — timers may have been throttled; check the output pacing')
    if (frames.length < 50) fail(`Only ${frames.length} frames captured — something went wrong.`)

    writeFileSync(
      join(work, 'manifest.json'),
      JSON.stringify({ dir: framesDir, frames, cropFraction, playAt, doneAt }, null, 2),
    )
  } finally {
    ws.close()
    proc.kill()
  }

  // --- encode (compile once, run per output) ---
  console.log('▸ encoding with AVFoundation')
  const encoder = join(work, 'encode-frames')
  execFileSync('swiftc', ['-O', join(HERE, 'encode-frames.swift'), '-o', encoder], { stdio: 'inherit' })
  OUTPUTS.forEach((o, i) => {
    const params = [
      join(work, 'manifest.json'),
      join(OUT_DIR, o.name),
      '--speed', String(o.speed),
      '--hold-start', String(o.holdStart),
      '--hold-end', String(o.holdEnd),
      '--width', '1440',
      '--fps', '30',
      '--bitrate', String(o.bitrate),
    ]
    // One poster from the final, fully-booked state — what visitors see if
    // autoplay is blocked (e.g. iOS Low Power Mode).
    if (i === 0) params.push('--poster', join(OUT_DIR, 'kiki-demo-poster.jpg'))
    execFileSync(encoder, params, { stdio: 'inherit' })
  })

  rmSync(work, { recursive: true, force: true })
  console.log(`\n✓ done → ${OUT_DIR}`)
}

main().catch((e) => fail(e.stack ?? String(e)))
