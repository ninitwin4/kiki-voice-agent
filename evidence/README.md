# Evidence — the integrations really are live

Raw, timestamped responses captured from the **real** third-party APIs and from our own
backend, so the integrations remain verifiable after credentials expire.

Why this exists: Sabre CERT tokens are short-lived (ours expired mid-project and had to be
re-minted). Once a token dies, a live demo can no longer *prove* the integration ever worked.
These fixtures are that proof.

| File | What it proves |
|---|---|
| `01-sabre-flightshop-v1-SFO-OGG.json` | **Live Sabre Flight Shop v1** — 10 real priced offers / 14 flight segments for SFO⇄OGG (Aug 5–10 2026, 5 adults), via `api.cert.platform.sabre.com/v1/offers/flightShop` with PCC `S5OM`. Cheapest offer: **$3,371.00 USD**. |
| `02-sabre-seasonality-OGG.json` | **Live Sabre Travel Seasonality** for Maui — weekly Low/Medium/High demand ratings, the real data behind the November-vs-August comparison. |
| `03-sabre-mcp-hotels-OGG.json` | **Live Sabre hotel search via MCP-Skills** (`mcp2.cert.sabre.com/mcp`, `tools/call search-hotels`) — real Maui properties: **Wailea Beach Resort – Marriott Maui**, **Grand Wailea**. |
| `05-paypal-sandbox-order.json` | **Live PayPal sandbox order** created through Orders v2 — real `order_id` and PayPal-issued `approve_url`. |
| `04-vocalbridge-token-mint.json` | **Live Vocal Bridge session-token mint** — real response shape and 3600s expiry (JWT + subdomain redacted). |
| `05-health-real-mode.json` | Our `/health` self-reporting every integration live. |
| `06-our-api-hybrid-flight-search.json` | The **hybrid design** end-to-end: curated bookable options **plus** `sabre_live_fares` (real Alaska fares) and `sabre_insight` (real seasonality) in one response. |
| `07-our-api-hotel-with-sabre.json` | `/hotel/adjust` returning the narrative booking **plus** real Sabre Maui properties. |
| `08-our-api-weather-cascade.json` | The **November → August cascade** — one call re-dating and re-pricing flights, hotel, transport and activities together. |

## Notes

- **Nothing here contains a credential.** The Vocal Bridge JWT and LiveKit subdomain are
  redacted; Sabre/PayPal responses contain no secrets. API keys live only in a gitignored
  `.env` and in Render env vars.
- **Prices differ between captures** because they're real: an earlier capture returned
  American at $469/$525, this one Alaska at $342/$380. That variation *is* the evidence the
  data is live rather than fixture-backed.
- **Cars are absent by design** — the hackathon Sabre token has no car-shopping entitlement
  (independently confirmed by two teammates), so ground transport is mock. Activities aren't
  a Sabre product either.
- **Reproduce** with a valid `SABRE_ACCESS_TOKEN` (PCC `S5OM`) plus PayPal/Vocal Bridge keys
  in `.env`; see the repo README.
