# Kiki — voice trip-agent UI

Vite + React + TypeScript. Pixel-art, light mode. Reads all trip data from one
endpoint (`POST /trip/status`); Kiki fires thin client-action signals that mostly
tell the UI when to refetch. Built **degradation-first** — every card renders
independently, so one vendor being slow/missing/errored never blocks the rest.

## Run

```bash
npm install        # needs Node 18+ (not installed on this box yet)
npm run dev        # http://localhost:5173
```

Then click **Add Kiki to the call →** (or **B · Live call**), then **▶ Play demo**
in the bottom bar. The scripted loop runs with **no backend and no voice**.

`.env` holds `VITE_API_BASE=https://kiki-complete-trip.onrender.com`.

## Fake ↔ Live (both wired)

Both the fake driver and the **real Vocal Bridge SDK** feed the **same**
`onAction` handler; only the refetch source differs. Flip the signal source with
the **SOURCE** toggle in the bottom bar (or `VITE_USE_FAKE=false` in `.env` to
start live). In live mode, "Add Kiki to the call →" mints a token from `/token`
and connects; the hero shows a connecting state, and any token/connection error
(e.g. `503 not_configured`) surfaces as an amber banner with Retry — never a
silent hang.

```
signals ─► onAction (actions.ts) ─► store ─► components
                    │
     card_update/reflow/payment ─► refetch /trip/status ─► re-render
```

- `src/contract.ts` — types + action names, copied from `CONTRACT.md`.
- `src/api.ts` — `fetchTripStatus()` (+ `fetchVocalBridgeToken()` via our backend).
- `src/actions.ts` — the `onAction` switch (signal → refetch/render).
- `src/store.ts` — tiny external store shared by driver, SDK, and components.
- `src/fakeBackend.ts` / `src/fakeScript.ts` — the no-backend demo. **Delete for prod.**
- `src/bridge/fakeDriver.ts` — walks the script into `onAction`.
- `src/bridge/LiveBridge.tsx` — real Vocal Bridge wiring: `VocalBridgeProvider`
  with a `tokenProvider` (mints from `/token` on every connect — never cached),
  `useVocalBridge` (connect + state → orb), `useTranscript` (→ right panel),
  `useAgentActions` (registers all 8 §3 action names → the same `onAction`).
- `src/App.tsx` — `mode` (fake/live) + composition. `onAction` is identical in
  both modes; only the refetch differs (`fakeRefetch` vs `fetchTripStatus`).

The VB token is minted by our backend (`POST /token` · `{ participant_name }`) —
we never call Vocal Bridge's token endpoint directly or embed a key in client
code. A `livekit_url` in the response is mapped to the SDK's `url`.

## Card states

`empty` (dashed) → `searching` (breathing pulse, "Kiki's looking…") → `booked`
(check) → `error` (amber, "couldn't reach provider — retrying"). Flight also has
an `options` state (3 rows, one recommended); reflow paints every card `updating`.
The demo includes one step that drops **transport** into `error` and then
recovers, so degradation is visible.
