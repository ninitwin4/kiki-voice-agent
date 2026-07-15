# Kiki — complete-trip demo backend

FastAPI backend for the "Kiki" voice-agent travel demo. It plans a **Maui group
trip** with Sabre-shaped mock data: 5 travelers (2 couples + 1 child) flying
**SFO⇄OGG**. The group plans the **first week of August**, discovers it's
**$3,356 over their $12,000 budget** (peak season), and Kiki moves the whole trip
to the **first week of October** — one call re-dates and re-prices flights,
hotel, minivan, and both activities, landing at **$11,798, saving $3,558**.

Everything lives in one in-memory `TRIP` object. Endpoints mutate it, so
`POST /trip/status` reflects the demo's progress, and `POST /demo/reset` restores the
initial August-planning state for the next rehearsal.

## Repo structure

```
backend/
  main.py           # FastAPI app, Pydantic models, in-memory TRIP state, cascade logic
  config.py         # env-var config (MOCK_MODE, MOCK_DELAY_SECONDS, PAYMENT_MOCK)
  sabre_client.py   # stub adapter for real Sabre — TODOs mirror the mock interface
  mocks/
    trip.json           # invariant trip header (party, budget, constraint)
    catalog.json        # per-month hotel / transport / activities pricing
    flight_search.json  # per-month flight options (August + October)
  tests/            # pytest — happy path + rebooking cascade
BUILD_STATUS.md     # live build tracker
TOOL_WIRING.md      # copy-paste Vocal Bridge tool config
requirements.txt
```

### Why the fixtures are split
`trip.json` holds only what never changes (party, budget, the constraint).
Everything month-specific lives in `catalog.json` / `flight_search.json`, and
`_apply_month()` assembles the trip from them. That's what makes August and
October **genuinely different data** that can't drift apart — the rebooking
cascade is real, not faked.

## The demo flow

| Step | Endpoint | What happens |
| ---- | -------- | ------------ |
| 1 | `POST /demo/reset` | Planning first week of August, nothing booked |
| 2 | `POST /trip/status` | $15,356 — **$3,356 over** the $12,000 budget |
| 3 | `POST /flights/search` | 3 options: **A** nonstop/pricey ★, **B** one-stop/cheapest, **C** nonstop but 6 AM return *(meant to be rejected)* |
| 4 | `POST /flights/book` | Book all 5 onto the chosen `flight_id` |
| 5 | `POST /hotel/adjust` | 2 ocean-view rooms, 7 nights |
| 6 | `POST /transport/update` | Minivan + child car seat at OGG |
| 7 | `POST /activities/book` | Surf lesson + Molokini snorkel |
| 8 | `POST /trip/rebook` | **The cascade** — `{"month":"october"}` re-flows every vendor |
| 9 | `POST /payment/confirm` | Charges the trip total (omit `amount`) |

Anything already booked **stays booked** across the cascade — a booked flight
carries its tier (A/B/C) to the equivalent option in the new month.

## Configuration (env vars)

See [`.env.example`](.env.example). All three have working defaults, so the demo
runs with no `.env` at all.

| Variable             | Default | Meaning                                                        |
| -------------------- | ------- | -------------------------------------------------------------- |
| `MOCK_MODE`          | `true`  | Serve JSON fixtures from `backend/mocks/`                       |
| `MOCK_DELAY_SECONDS` | `1.5`   | Artificial latency per request so rehearsals match real timing  |
| `PAYMENT_MOCK`       | `true`  | Return a polished fake payment confirmation                     |

With `MOCK_MODE=false` or `PAYMENT_MOCK=false`, endpoints return **501** until
`sabre_client.py` is implemented (real Sabre / payments are intentionally not
integrated yet — there is no Sabre account behind this demo).

## Run locally

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

- API docs / OpenAPI for your voice platform's tool config: http://127.0.0.1:8000/docs
- Each endpoint's one-line docstring is written to be reused verbatim as the
  voice-agent tool description. See [`TOOL_WIRING.md`](TOOL_WIRING.md).
- Tip: `MOCK_DELAY_SECONDS=0 uvicorn backend.main:app --reload` while iterating.

## Run tests

```bash
pytest
```

Covers the full August happy path (plan → book all 4 vendors → pay) and the
rebooking path (August → October cascades every vendor's dates *and* prices).

## Deploy to Render (free tier)

Live at **https://kiki-complete-trip.onrender.com** — it **auto-deploys on `git
push`**. The repo ships a [`render.yaml`](render.yaml) Blueprint that pins
everything: free plan, `pip install -r requirements.txt` build, start command
`uvicorn backend.main:app --host 0.0.0.0 --port $PORT`, health check on `/health`,
and env vars `MOCK_MODE=true`, `PAYMENT_MOCK=true`, `MOCK_DELAY_SECONDS=1.5`.

To stand up a fresh instance: **New → Blueprint**, connect the repo, **Apply**.

Note: free-tier services sleep after ~15 min idle, and the cold start wipes and
restores the in-memory state — hit `POST /demo/reset` before each rehearsal anyway.

## Demo walkthrough (curl)

```bash
BASE=https://kiki-complete-trip.onrender.com   # or http://127.0.0.1:8000

curl -s -X POST $BASE/demo/reset | jq
curl -s -X POST $BASE/trip/status | jq '.totals'
curl -s -X POST $BASE/flights/search -H 'Content-Type: application/json' -d '{"month":"august"}' | jq '.options[] | {tier, flight_no, stops, price_pp, tradeoff}'
curl -s -X POST $BASE/flights/book -H 'Content-Type: application/json' -d '{"flight_id":"AA289"}' | jq '.message'
curl -s -X POST $BASE/hotel/adjust | jq '.message'
curl -s -X POST $BASE/transport/update | jq '.message'
curl -s -X POST $BASE/activities/book | jq '.message'

# The cascade — every vendor moves to October dates and prices
curl -s -X POST $BASE/trip/rebook -H 'Content-Type: application/json' -d '{"month":"october"}' | jq '{message, savings, totals}'

curl -s -X POST $BASE/payment/confirm -H 'Content-Type: application/json' -d '{}' | jq '.message'
curl -s -X POST $BASE/trip/status | jq '.totals'
```

## Going live later

`backend/sabre_client.py` is an empty adapter whose functions mirror the mock
interface exactly (same names, same JSON shapes). Implement its TODOs against real
Sabre (Get Reservation, Bargain Finder Max, exchanges, Content Services for
Lodging) and a real payment provider, then flip `MOCK_MODE=false` /
`PAYMENT_MOCK=false` — no endpoint code changes needed.
