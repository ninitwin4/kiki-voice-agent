# Kiki — voice-agent travel demo backend

FastAPI backend for **Kiki**, an ambient voice travel agent. Two friends — **Ni Ni**
(party of 2) and **RC** (party of 3, including a five-year-old) — plan a Maui trip
out loud. Kiki listens quietly and chimes in when useful: she checks the weather,
finds early **November** is Maui's rainy season, remembers **RC won't travel in the
rain**, and moves the whole trip to dry **August (Aug 5, 5 nights)** — one call that
re-dates and re-prices flights, hotel, minivan, and activities together.

Three sponsors are integrated for real: **Vocal Bridge** (voice), **Sabre** (live
flight fares, seasonality, and Maui hotels), and **PayPal** (sandbox payment).

```
FastAPI backend ──(9 tools + /token)──► Kiki (Vocal Bridge) ──(client actions)──► React UI
   the kitchen                              the waiter                              the table
```

- **UI backend base URL:** `https://kiki-complete-trip.onrender.com` (what the UI reads)
- **The UI reads exactly one endpoint** — `POST /trip/status` — and refetches it after
  each of Kiki's signals. See [`CONTRACT.md`](../CONTRACT.md) (source of truth for UI↔backend).

## Repo structure

```
backend/
  main.py           # FastAPI app, Pydantic models, in-memory TRIP state, cascade + endpoints
  config.py         # env-var config + feature flags + /health mode()
  sabre_client.py   # real Sabre: Flight Shop v1 fares + Travel Seasonality (REST)
  sabre_mcp.py      # real Sabre hotels via the MCP-Skills server (search-hotels)
  paypal_client.py  # real PayPal sandbox (Orders v2: create + capture)
  vb_client.py      # Vocal Bridge voice-token minting (/token)
  mocks/
    trip.json           # invariant trip header (Ni Ni & RC party, budget, weather constraint)
    catalog.json        # per-month hotel / transport / activities (november + august)
    flight_search.json  # per-month flight options (november + august)
  tests/            # pytest — happy path, weather cascade, configure, real-integration smoke
client_actions.json # the 9 frozen Kiki→UI / UI→Kiki client-action names
CONTRACT.md         # UI↔backend↔Kiki contract (one level up)
render.yaml         # two services: kiki-complete-trip (UI backend) + kiki-real
```

## The demo flow — the weather cascade

| Step | Endpoint | What happens |
| ---- | -------- | ------------ |
| 1 | `POST /demo/reset` | Planning **first week of November** (rainy), nothing booked |
| 2 | `POST /trip/status` | Ni Ni & RC, 5 travelers, ~$9,170, within budget |
| 3 | *(Kiki checks weather via Web Search)* | Early November is Maui's rainy season |
| 4 | `POST /flights/search` | 3 bookable options (A nonstop ★, B one-stop, C 6 AM-return trap) **+ live Sabre fares** |
| 5 | `POST /trip/rebook` | **The cascade** — `{"month":"august"}`; RC won't travel in rain → dry August, every vendor re-flows |
| 6 | `POST /flights/book` · `/hotel/adjust` · `/transport/update` · `/activities/book` | Book each vendor |
| 7 | `POST /payment/confirm` | Charge the trip total (or real PayPal via the UI button) |

`/trip/configure` re-sizes the trip (nights / travelers / rooms) and re-prices. Anything
booked **stays booked** across the cascade — a booked flight carries its tier (A/B/C).

## Endpoints

- **UI reads:** `POST /trip/status` (the whole trip; contract-locked shape).
- **Kiki's 9 tools:** `/trip/status`, `/flights/search`, `/flights/book`, `/hotel/adjust`,
  `/transport/update`, `/activities/book`, `/trip/rebook`, `/trip/configure`, `/payment/confirm`.
- **Voice:** `POST /token` → mints a Vocal Bridge session token (VB API key stays server-side).
- **Real PayPal:** `GET /payment/paypal/config`, `POST /payment/paypal/create-order`,
  `POST /payment/paypal/capture-order` (enabled by `PAYPAL_LIVE`).
- **Ops:** `POST /demo/reset`, `GET /health` (self-describes `mock` vs `real`).

## Real sponsor integrations

**Sabre — hybrid (real proof, safe demo).** The 3 bookable flight options stay curated
(so booking can't break and the narrative holds), but in real mode `/flights/search` also
attaches **live Sabre data** Kiki reads aloud: `sabre_live_fares[]` (real Flight Shop v1
fares) and `sabre_insight` (real Travel Seasonality). `/hotel/adjust` attaches real Maui
hotels (Grand Wailea, Wailea Beach Resort) via the Sabre MCP-Skills server. Needs a
`SABRE_ACCESS_TOKEN` with the PCC `S5OM` attribute; a stale/expired token simply omits the
proof — it never breaks the flow. *(Cars aren't available on the hackathon Sabre token;
transport is mock. Activities aren't a Sabre product.)*

**PayPal — sandbox.** `paypal_client.py` does real Orders v2 create + capture. The UI's
PayPal button drives `create-order → approve → capture-order`.

**Vocal Bridge — voice.** `POST /token` proxies VB's token endpoint server-side. Kiki fires
the client actions in `client_actions.json` to drive the UI (per `CONTRACT.md` §3–4).

## Configuration (env vars)

See [`.env.example`](.env.example). Mock everything by default; flip flags for real.

| Variable | Meaning |
| -------- | ------- |
| `MOCK_MODE` (`true`) | Serve JSON fixtures for the trip narrative |
| `SABRE_FLIGHTS_LIVE` / `SABRE_HOTELS_LIVE` | Attach real Sabre fares+seasonality / real hotels |
| `SABRE_ACCESS_TOKEN` | Pre-issued Sabre token (PCC `S5OM`); **expires — refresh before a demo** |
| `PAYPAL_LIVE` + `PAYPAL_CLIENT_ID` / `PAYPAL_SECRET` | Real sandbox PayPal endpoints |
| `VB_API_KEY` + `VB_AGENT_ID` | Vocal Bridge token minting for `/token` |
| `MOCK_DELAY_SECONDS` (`1.5`) | Artificial latency; `0` for tests |

Secrets live in a gitignored `.env` locally and Render env vars (`sync: false`) — never committed.

## Two Render services (one codebase)

- **`kiki-complete-trip`** — the UI backend. Mock trip narrative + **hybrid real Sabre proof**
  + `/token`. This is what `VITE_API_BASE` points at.
- **`kiki-real`** — same code with more real flags on, for standalone sponsor proof.

Both auto-deploy on `git push`. Set the `sync: false` secrets (Sabre token, PayPal, `VB_API_KEY`)
in each service's Render dashboard. Free tier sleeps after ~15 min — warm with a `/trip/status`
call before a rehearsal.

## Run locally

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then paste real credentials to test live integrations
MOCK_DELAY_SECONDS=0 uvicorn backend.main:app --reload
```

- OpenAPI / docs: http://127.0.0.1:8000/docs
- Load `.env` into a run: `set -a && source .env && set +a && uvicorn backend.main:app`

## Run tests

```bash
pytest
```

Covers the November happy path, the November→August weather cascade, `/trip/configure`
re-sizing, and bounds. Real-integration smoke tests (Sabre / PayPal) **skip automatically**
unless credentials are present, so the default run is always green.
