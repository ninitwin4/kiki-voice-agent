# TOOL_WIRING — Kiki (Vocal Bridge / Chatty)

Copy-paste reference for wiring Kiki's tools to the live backend. Values below
are verified against production, not guessed.

- **Live base URL:** `https://kiki-complete-trip.onrender.com`
- **All endpoints:** `POST`, `Content-Type: application/json`.
- **GitHub repo:** `kiki-voice-agent` · **Render service:** `kiki-complete-trip`
  (the service name is *not* the repo name — don't let that trip you up in the dashboards).
- Free tier sleeps after idle. **Warm it before a rehearsal/demo** with one
  `get_trip_status` call (~30–50s cold start on the first hit).

---

## Phase 1 — the 3 core tools

Wire these three first, then do the first voice run before adding the rest.

### 1. `get_trip_status`
- **Method / URL:** `POST https://kiki-complete-trip.onrender.com/trip/status`
- **Request body:** none — send an empty object `{}`
- **Description (paste as tool description):**
  > Get the traveler's full trip itinerary with the current status of the flight, hotel, airport pickup, and rehearsal dinner. Call this first when the user reports a problem, to assess impact.
- **What Kiki reads back:** `flight.status` (e.g. `CANCELLED`), and the
  `hotel.status` / `transport.status` / `dining.status` (each `AT_RISK` until its own tool fires).

### 2. `search_flights`
- **Method / URL:** `POST https://kiki-complete-trip.onrender.com/flights/search`
- **Request body:** none — send an empty object `{}`
- **Description (paste as tool description):**
  > Search alternative flights after a disruption. Call ONLY after a cancellation is confirmed, never for initial booking.
- **What Kiki reads back:** from `itineraries[]`, the item where `recommended: true`
  (currently `flight_id: "AA1885"`), plus its `reason` and `totalFare.amount`.

### 3. `rebook_flight`
- **Method / URL:** `POST https://kiki-complete-trip.onrender.com/flights/rebook`
- **Request body (ONE required string param):**
  ```json
  { "flight_id": "AA1885" }
  ```
  - `flight_id` (string, required) — the `flight_id` from `search_flights`, e.g. `AA1885`.
- **Description (paste as tool description):**
  > Rebook onto a chosen flight. Requires explicit verbal user confirmation before calling. Returns confirmation and price difference.
- **What Kiki reads back:** `confirmed` (true), `price_difference` + `currency`
  (e.g. `45.20 USD`), and `message`.

---

## Verified live sample (captured from production)

```
POST /trip/status   {}                       -> flight CANCELLED; hotel/transport/dining AT_RISK
POST /flights/search {}                       -> AA1885 (recommended, $209.40), AA2694 ($176.10), AA989 ($434.00)
POST /flights/rebook {"flight_id":"AA1885"}   -> confirmed:true, price_difference:45.20 USD
```

---

## Vocal Bridge reminders
- **Background AI must be ON** — tool-calling depends on it.
- **Persona prompt must forbid guessing:** "Never invent flights, times, or
  prices — always call a tool." Kiki will hallucinate answers instead of calling
  tools unless the prompt explicitly forbids it.
- Free tier = 1 agent; edit the same Kiki agent in place.
- Tool-call latency is audible — use filler speech to cover it. Real Sabre will
  be slower than the 1.5s mock.

## Phase 2 — remaining 6 tools (after the first voice run)
Same base URL, all `POST`. Add these once the 3 core tools pass a live voice run:

| Tool | Path | Request body |
|---|---|---|
| `adjust_hotel` | `/hotel/adjust` | `{ "expected_arrival": "22:30" }` (optional; defaults to a late check-in) |
| `move_dining` | `/dining/move` | `{ "new_time": "22:00" }` |
| `update_transport` | `/transport/update` | `{ "new_pickup_time": "21:45", "flight_number": "AA 1885" }` |
| `confirm_payment` | `/payment/confirm` | `{ "amount": 45.20, "currency": "USD" }` |
| `reset_demo` | `/demo/reset` | none `{}` — restores the cancellation for the next rehearsal |

(`get_trip_status` is reused to confirm every AT_RISK item flipped to CONFIRMED — that's the full 9-tool test pass.)
