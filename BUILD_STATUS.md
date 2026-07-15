# BUILD_STATUS — Kiki Voice Agent (The Complete Trip)

**Project:** Voice AI group-trip planning agent · **Repo:** `kiki-voice-agent` (GitHub) · **Render service:** `kiki-complete-trip`
**Stack:** Vocal Bridge (Chatty, web) + FastAPI backend · **Dev tool:** Claude Code
**Scenario:** Maui group trip — 5 travelers (2 couples + 1 child), SFO⇄OGG · **Voice agent:** Kiki
**Live:** https://kiki-complete-trip.onrender.com (auto-deploys on `git push`)

> Paste this whole file into a build chat to re-orient, then say:
> "Work on the next unchecked item: [X]. Repo is `kiki-voice-agent`, FastAPI, MOCK_MODE=true."

---

## The demo (30 seconds)

The group plans the **first week of August** → Kiki surfaces the constraint:
**$15,356, which is $3,356 over their $12,000 budget** (peak season) → Kiki moves
the whole trip to the **first week of October** in one call → flights, hotel,
minivan, and both activities all re-date and re-price → **$11,798, saving $3,558,
inside budget** → pay.

The rebooking cascade is **real, not faked**: August and October are separate
datasets in `backend/mocks/`, assembled by `_apply_month()`.

---

## ✅ Done
- [x] Backend scaffolded — FastAPI, `complete-trip` repo structure
- [x] `MOCK_MODE` + `PAYMENT_MOCK` + `MOCK_DELAY_SECONDS` (1.5s) config working
- [x] **Deployed to Render** → live, `/health` 200, auto-deploys on `git push`
- [x] Vocal Bridge account + practice agents (barista, weather) — platform basics learned
- [x] **Voice model fixed** — `gpt-realtime-1.5` → **`gpt-realtime-2`** (see learnings); 0 errors
- [x] First end-to-end voice run ✅ (session `97191572`) — greeting → status → search → verbal yes → rebook
- [x] **VB account upgraded** — no longer capped at 1 agent / limited usage
- [x] **Pivoted to the Maui group-trip demo** (commit `a099b92`):
      Aug + Oct datasets · 3 tiered flight options with spoken `tradeoff` strings ·
      new `/flights/book`, `/activities/book`, `/trip/rebook` cascade ·
      removed `/dining/move` · payment defaults to trip total · `.env.example` ·
      10 pytest tests (happy path + cascade), verified live over HTTP

---

## ⬜ Next up (in order)
- [ ] **Rewire Kiki's tools for the Maui scenario** — see [`TOOL_WIRING.md`](TOOL_WIRING.md).
      A **fresh agent** is likely cleaner than editing around the old AUS tools (account is upgraded now).
      `get_trip_status` unchanged · `search_flights` gains optional `month` ·
      `rebook_flight` → **`book_flight`** (`/flights/book`) · **new:** `book_hotel`,
      `book_transport`, `book_activities`, `change_trip_dates` (`/trip/rebook`), `confirm_payment`
- [ ] Update Kiki's **system prompt** for the new scenario (group of 5, budget constraint,
      no pre-dawn return flights, confirm before booking/rebooking)
- [ ] **First Maui voice run**: "We're planning Maui for the first week of August"
      → expect: status → search → tradeoffs → book → constraint → `change_trip_dates` → pay
- [ ] **Full tool test pass** — every tool fires; `/trip/status` shows all vendors BOOKED on October dates
- [ ] If tools get flaky with 8 of them → **switch to AI Agent mode (Plan B)**

## ⬜ Later
- [ ] Live itinerary UI via **Client Actions** (`useAgentActions`; declare events in `actions.json`, create agent with `--client-actions-file`). Pattern: Kiki rebooks → fires `update_itinerary` → the whole card grid re-flows Aug → Oct. Mirror the tic-tac-toe `board_sync` pattern so the agent's mental model stays in sync with the screen. **Fallback:** UI polls `/trip/status` every 2s — same visual effect, boring plumbing, judges can't tell.
- [ ] PayPal sandbox payment (or keep `PAYMENT_MOCK=true` fallback)
- [ ] Event day: `MOCK_MODE=false` → real Sabre credentials *(note: there is **no** Sabre account behind this demo today — `sabre_client.py` is an empty stub)*
- [ ] Backup demo video + rehearse ×5

## ⬜ Stretch / Plan C
- [ ] **Outbound call** ("Kiki calls the resort to confirm the two rooms") — `make_phone_call` tool with a required `purpose` param; agent needs `--outbound-enabled true --accept-outbound-tos`. Pattern = base prompt + per-call purpose injected at call time. High wow-factor, high risk — only if everything else is done.

---

## Vocal Bridge: three modes (and what mixes)

| Mode | How it works | Our use |
|---|---|---|
| **Custom API tools** (Background AI ON) | VB's own brain decides which of your REST endpoints to call | Current path |
| **AI Agent mode** (Background AI OFF) | VB = thin voice layer. Every spoken turn POSTs to *your* `/query` endpoint; your code orchestrates and returns a string; VB speaks it | **Plan B** — we own the logic |
| **Client Actions** | Bidirectional agent↔UI over WebRTC data channel (`useAgentActions` hook) | The live itinerary UI (layers on top of either mode) |

⚠️ **AI Agent mode and Background AI are mutually exclusive.** Create the agent with `--background-enabled false` + `--ai-agent-file ai-agent.json`.

### Plan B: AI Agent mode (if the tool count stays unreliable)
- Add ONE route to the existing backend: `POST /query` → takes `{query}`, runs Claude with our endpoints as tools, returns `{response}` string.
- VB config: `ai-agent.json` with `enabled`, `description` (guides VB on when to delegate), `verbatim: false` (lets VB polish phrasing).
- Client side: `useAIAgent({ onQuery })` — forwards every spoken turn to `/query`, speaks whatever string comes back.
- **Upside:** we own the orchestration; VB no longer has to choose among 8 tools. Existing endpoints are reused, not thrown away.

---

## Tool wiring reference

Full copy-paste config with params: [`TOOL_WIRING.md`](TOOL_WIRING.md). All `POST`,
**No auth**, base `https://kiki-complete-trip.onrender.com`, **all params in `body`**.

| Tool | Path | Body |
|---|---|---|
| `get_trip_status` | `/trip/status` | none |
| `search_flights` | `/flights/search` | `month` *(optional)* |
| `book_flight` | `/flights/book` | `flight_id` **required** |
| `book_hotel` | `/hotel/adjust` | none |
| `book_transport` | `/transport/update` | none |
| `book_activities` | `/activities/book` | `activity` *(optional — omit to book both)* |
| `change_trip_dates` ⭐ | `/trip/rebook` | `month` **required** |
| `confirm_payment` | `/payment/confirm` | `amount`, `currency` *(both optional)* |
| `reset_demo` | `/demo/reset` | none — easier via curl between rehearsals |

---

## Key learnings
- **Voice model matters most.** `gpt-realtime-1.5` threw 516 `realtime_model_error`s and produced **zero audio**; `gpt-realtime-2` works cleanly. If the agent won't speak, swap the voice model in Agent settings **before** debugging anything else.
- **Tool-call path:** foreground realtime model → built-in `submit_background_query` → **Background AI (Claude)** → your Custom API tools → Render. That's why Background AI must be ON.
- **Background AI = the tool-calling engine.** OFF → agent talks but only has built-ins (`end_call`, `put_on_hold`, `resume_from_hold`, `trigger_client_action`); your custom tools return **"Unknown function."** ON → required for Custom API tools. OFF only for AI Agent mode.
- **VB tool-editor is fragile.** Adding a tool can throw `APITool id Field required` and the **Parameters sub-panel silently disappears** from every card. Fix: **Save immediately after clicking "+ Add API tool"** (forces VB to assign the `id`) *before* filling fields or adding params. Reload and re-check that params survived — they can be dropped.
- **Params must be `body`, never `query`.** The backend reads JSON bodies; a `query` param yields a 422 "field required."
- **Fewer params = more reliable voice.** Vendor endpoints (hotel/transport/activities) deliberately take **no params** and derive dates from the trip's current month; payment defaults to the trip total. Less for the agent to get wrong, less to wire.
- **Agents hallucinate rather than call tools** unless the prompt explicitly forbids it: *"Never invent flights, times, or prices — always call a tool."*
- **Bridge lines beat silence.** *"hang on, checking…"* — tool calls take 1–6s. *"That's the difference between feeling fast and feeling broken."*
- **Chatty style is documented as best for 1–2 tools.** Kiki has 8. If tool-calling gets unreliable, this is the likely cause → Plan B.
- **STT mis-hears.** `gpt-realtime-whisper` turned "my flight got cancelled" into "my friend got cancer." Speak trigger phrases clearly in the demo.
- **`end_call` needs the Hang up capability enabled** — otherwise Kiki tries and gets "Hangup feature is not enabled."
- **Debug tools:** `vb logs` (structured log of every turn + action), `vb debug` (live event stream), `vb eval <session_id> --objective "..."` (scores a recorded call 0–10 and returns concrete prompt fixes). Run an eval instead of guessing at the prompt.
- **Session JSON is the ground truth.** Export it from Call detail → the `events` array shows exactly which tools fired, what errored, and why. It settled both the no-audio and the "Unknown function" mysteries.
