# TOOL_WIRING — Kiki (Vocal Bridge / Chatty)

Copy-paste reference for wiring Kiki's tools to the live backend. Values below
are verified against the running API, not guessed.

- **Live base URL:** `https://kiki-complete-trip.onrender.com`
- **All endpoints:** `POST`, `Content-Type: application/json`, **No auth**.
- **All parameters go in the `body`** (never `query`) — the backend reads JSON bodies.
- **GitHub repo:** `kiki-voice-agent` · **Render service:** `kiki-complete-trip`
- Free tier sleeps after idle. **Warm it before a rehearsal** with one
  `get_trip_status` call (~30–50s cold start on the first hit).
- **Background AI must be ON** — it's the layer that actually executes these tools.
- Voice model: **`gpt-realtime-2`** (`gpt-realtime-1.5` is broken — no audio).

---

## All 8 tools at a glance (copy-paste)

Every one is **POST** + **No auth**. Only 3 take parameters — and every parameter
goes in the **body**, never `query`.

| # | Tool name | Full URL | Parameters |
|---|---|---|---|
| 1 | `get_trip_status` | `https://kiki-complete-trip.onrender.com/trip/status` | — |
| 2 | `search_flights` | `https://kiki-complete-trip.onrender.com/flights/search` | `month` *(optional)* |
| 3 | `book_flight` | `https://kiki-complete-trip.onrender.com/flights/book` | `flight_id` **required** |
| 4 | `book_hotel` | `https://kiki-complete-trip.onrender.com/hotel/adjust` | — |
| 5 | `book_transport` | `https://kiki-complete-trip.onrender.com/transport/update` | — |
| 6 | `book_activities` | `https://kiki-complete-trip.onrender.com/activities/book` | `activity` *(optional)* |
| 7 | `change_trip_dates` | `https://kiki-complete-trip.onrender.com/trip/rebook` | `month` **required** |
| 8 | `confirm_payment` | `https://kiki-complete-trip.onrender.com/payment/confirm` | `amount` *(optional)* |
| 9 | `configure_trip` | `https://kiki-complete-trip.onrender.com/trip/configure` | `nights`, `travelers`, `rooms` *(all optional, number)* |

`configure_trip` re-prices the whole trip for a different size/length (e.g. "5 nights not 7",
"party of 3"). Hotel + transport scale with nights; flights + activities scale with travelers.
It exists so Kiki never has to price a variation in its head. Already wired on the agent via CLI.

⚠️ **Adding tools in the VB editor:** click **+ Add API tool** → **Save immediately** →
*then* fill the fields → Save again. Saving right after adding forces VB to assign the
internal `id`; skipping it triggers `APITool id Field required` and makes the
Parameters panel vanish from every card.

Per-tool descriptions and response fields are below.

---

## The demo: Maui group trip

5 travelers (2 couples + 1 child), SFO⇄OGG. The group plans the **first week of
August**, discovers it's **$3,356 over their $12,000 budget** (peak season), and
Kiki moves the whole trip to the **first week of October** — one call re-dates
and re-prices flights, hotel, minivan, and both activities, landing at **$11,798
(within budget, saving $3,558)**.

---

## Phase 1 — core tools

### 1. `get_trip_status`
- **URL:** `https://kiki-complete-trip.onrender.com/trip/status` · **Body:** none (`{}`)
- **Description:**
  > Get the group's full Maui trip plan: dates, party, flights, hotel, transport, activities, running total, and whether it fits the budget. Call this first to see where the trip stands.
- **Kiki reads back:** `month`, `dates.label`, each vendor's `status`, and
  `totals.trip_total` / `totals.within_budget` / `totals.over_budget_by`.

### 2. `search_flights`
- **URL:** `https://kiki-complete-trip.onrender.com/flights/search`
- **Body — one optional param:**
  - `month` · string · **body** · *not required* — `august` or `october`. Omit to use the trip's current month.
- **Description:**
  > Search SFO to Maui (OGG) flights for 5 travelers and return three priced options, each with a tradeoff to read aloud. Call after the traveler asks about flights or dates.
- **Kiki reads back:** for each option — `carrier`, `flight_no`, `stops`,
  `price_pp`, `total_price`, and the **`tradeoff`** string (written to be spoken verbatim).
  Exactly one option has `recommended: true`.

### 3. `book_flight`
- **URL:** `https://kiki-complete-trip.onrender.com/flights/book`
- **Body — one required param:**
  - `flight_id` · string · **body** · **required** — from `search_flights`, e.g. `AA289`
- **Description:**
  > Book all 5 travelers onto a chosen flight by flight_id. Requires explicit verbal user confirmation before calling. Returns the record locator and updated trip total.
- **Kiki reads back:** `record_locator`, `flights.total_price`, `totals.trip_total`.

### 4. `book_hotel`
- **URL:** `https://kiki-complete-trip.onrender.com/hotel/adjust` · **Body:** none (`{}`)
- **Description:**
  > Book the two resort rooms on Maui for the trip's current dates. Returns the confirmation number and total.
- **Kiki reads back:** `hotel.name`, `hotel.check_in`/`check_out`, `hotel.total`.

### 5. `book_transport`
- **URL:** `https://kiki-complete-trip.onrender.com/transport/update` · **Body:** none (`{}`)
- **Description:**
  > Book the minivan with a child car seat at Maui airport (OGG) for the trip's current dates. Returns the confirmation and total.
- **Kiki reads back:** `transport.vehicle`, `transport.pickup_date`, `transport.total`.

### 6. `book_activities`
- **URL:** `https://kiki-complete-trip.onrender.com/activities/book`
- **Body — one optional param:**
  - `activity` · string · **body** · *not required* — `surf` or `snorkel`. **Omit to book both.**
- **Description:**
  > Book the group's Maui experiences — a kid-friendly beginner surfing lesson and the Molokini snorkeling tour — for the trip's current dates. Omit the activity parameter to book both at once.
- **Kiki reads back:** each item's `name`, `date`, `time`, `total`.

### 7. `change_trip_dates` ⭐ the money shot
- **URL:** `https://kiki-complete-trip.onrender.com/trip/rebook`
- **Body — one required param:**
  - `month` · string · **body** · **required** — `august` or `october`
- **Description:**
  > Move the entire trip to a different month. This re-dates and re-prices the flights, hotel, minivan, and activities together in one step. Requires explicit verbal user confirmation before calling.
- **Kiki reads back:** `message`, `savings`, `totals.trip_total`, `totals.within_budget`.
- **Note:** anything already booked **stays booked** — a booked flight carries its
  tier (A/B/C) to the equivalent option in the new month.

### 8. `confirm_payment`
- **URL:** `https://kiki-complete-trip.onrender.com/payment/confirm`
- **Body — both optional:**
  - `amount` · number · **body** · *not required* — **omit to charge the trip's current total**
  - `currency` · string · **body** · *not required* — defaults to `USD`
- **Description:**
  > Charge the card on file for the trip total and return a payment confirmation code. Requires explicit verbal user confirmation before calling.

### 9. `reset_demo` (operator tool — optional)
- **URL:** `https://kiki-complete-trip.onrender.com/demo/reset` · **Body:** none (`{}`)
- Restores the initial August-planning state. Easiest run from the terminal
  between rehearsals rather than wiring it as a voice tool:
  ```bash
  curl -s -X POST https://kiki-complete-trip.onrender.com/demo/reset
  ```

---

## Verified live sample

```
POST /demo/reset       {}                      -> planning first week of August, $15,356 (over by $3,356)
POST /flights/search   {"month":"august"}      -> A AA289 nonstop $782pp ★ | B AA1412 1-stop $648pp | C AA674 ret 06:05
POST /flights/book     {"flight_id":"AA289"}  -> PNR-…, $3,910
POST /hotel/adjust     {}                      -> Westin Maui, 2 rooms, 08-03→08-10, $9,590
POST /transport/update {}                      -> Sienna minivan + car seat @ OGG, $686
POST /activities/book  {}                      -> surf 08-04 $475 + Molokini 08-06 $695
POST /trip/rebook      {"month":"october"}     -> everything → 10-05→10-12, $11,798, saving $3,558 ✅ within budget
POST /payment/confirm  {}                      -> PAY-…, $11,798
```

---

## Voice/persona reminders
- **Never invent flights, times, or prices — always call a tool.** Kiki will
  hallucinate otherwise.
- **Option C is a trap by design** — its return leaves OGG at ~6 AM. The group's
  stated preference (`preferences.no_early_return`) is no pre-dawn flights home.
  Kiki should surface the tradeoff, not silently pick it.
- **Bridge lines beat silence** — "let me check that now" covers the 1.5s mock delay.
- The `tradeoff` field on each flight option is written to be **spoken verbatim**.
- STT mis-hears things; speak trigger phrases clearly.
