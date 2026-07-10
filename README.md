# Kiki — complete-trip demo backend

FastAPI backend for the "Kiki" voice-agent travel demo. It simulates trip-disruption
recovery with Sabre-shaped mock data: traveler **Mary** is flying SFO→AUS tonight for
her sister's wedding, her flight just got **cancelled**, and the agent recovers the
whole trip — flight, hotel late check-in, rehearsal dinner, airport pickup, payment.

Everything lives in one in-memory `TRIP` object. Endpoints mutate it, so
`POST /trip/status` reflects the demo's progress, and `POST /demo/reset` restores the
initial state for the next rehearsal.

## Repo structure

```
backend/
  main.py           # FastAPI app, Pydantic models, in-memory TRIP state
  config.py         # env-var config (MOCK_MODE, MOCK_DELAY_SECONDS, PAYMENT_MOCK)
  sabre_client.py   # stub adapter for real Sabre — TODOs mirror the mock interface
  mocks/            # JSON fixtures (initial trip, flight search results)
  tests/            # pytest happy path
requirements.txt
```

## Configuration (env vars)

| Variable             | Default | Meaning                                                        |
| -------------------- | ------- | -------------------------------------------------------------- |
| `MOCK_MODE`          | `true`  | Serve JSON fixtures from `backend/mocks/`                       |
| `MOCK_DELAY_SECONDS` | `1.5`   | Artificial latency per request so rehearsals match real timing  |
| `PAYMENT_MOCK`       | `true`  | Return a polished fake payment confirmation                     |

With `MOCK_MODE=false` or `PAYMENT_MOCK=false`, endpoints return **501** until
`sabre_client.py` is implemented (real Sabre / payments are intentionally not
integrated yet).

## Run locally

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

- API docs / OpenAPI for your voice platform's tool config: http://127.0.0.1:8000/docs
  and http://127.0.0.1:8000/openapi.json
- Each endpoint's one-line docstring is written to be reused verbatim as the
  voice-agent tool description.
- Tip: `MOCK_DELAY_SECONDS=0 uvicorn backend.main:app --reload` while iterating.

## Run tests

```bash
pytest
```

## Deploy to Render (free tier)

The repo ships a [`render.yaml`](render.yaml) Blueprint that pins everything: free
plan, `pip install -r requirements.txt` build, start command
`uvicorn backend.main:app --host 0.0.0.0 --port $PORT`, health check on `/health`,
and env vars `MOCK_MODE=true`, `PAYMENT_MOCK=true`, `MOCK_DELAY_SECONDS=1.5`.

1. Push this folder to a GitHub repo.
2. In the Render dashboard: **New → Blueprint**, connect the repo, and Render reads
   `render.yaml` — click **Apply** and it builds and deploys.
3. Alternatively (manual): **New → Web Service**, connect the repo, and enter the
   same build/start commands and env vars from `render.yaml` by hand.
4. Verify: `curl -s -X POST https://<your-service>.onrender.com/trip/status`
5. Note: free-tier services sleep after ~15 min idle, and the cold start wipes and
   restores the in-memory state — hit `POST /demo/reset` before each rehearsal anyway.
   Set `MOCK_DELAY_SECONDS=0` in the service's Environment tab if you want snappy
   responses while wiring up the voice platform.

## Demo walkthrough (curl)

```bash
BASE=http://127.0.0.1:8000   # or your Render URL

# 0. Fresh start
curl -s -X POST $BASE/demo/reset | jq

# 1. What's wrong? (flight CANCELLED, hotel/dinner/pickup AT_RISK)
curl -s -X POST $BASE/trip/status | jq

# 2. Find alternatives tonight (AA1885 nonstop is the recommended one)
curl -s -X POST $BASE/flights/search | jq

# 3. Rebook onto AA1885 — returns price_difference of 45.20
curl -s -X POST $BASE/flights/rebook \
  -H 'Content-Type: application/json' -d '{"flight_id": "AA1885"}' | jq

# 4. Hold the hotel room for a late check-in
curl -s -X POST $BASE/hotel/adjust \
  -H 'Content-Type: application/json' -d '{"expected_arrival": "22:30"}' | jq

# 5. Move the rehearsal dinner to 10pm
curl -s -X POST $BASE/dining/move \
  -H 'Content-Type: application/json' -d '{"new_time": "22:00"}' | jq

# 6. Re-time the airport pickup to the new arrival
curl -s -X POST $BASE/transport/update \
  -H 'Content-Type: application/json' -d '{"new_pickup_time": "21:45", "flight_number": "AA 1885"}' | jq

# 7. Pay the fare difference — fake-but-polished confirmation code
curl -s -X POST $BASE/payment/confirm \
  -H 'Content-Type: application/json' -d '{"amount": 45.20}' | jq

# 8. All green
curl -s -X POST $BASE/trip/status | jq
```

## Going live later

`backend/sabre_client.py` is an empty adapter whose functions mirror the mock
interface exactly (same names, same JSON shapes). Implement its TODOs against real
Sabre (Get Reservation, Bargain Finder Max, exchanges) and a real payment provider,
then flip `MOCK_MODE=false` / `PAYMENT_MOCK=false` — no endpoint code changes needed.
