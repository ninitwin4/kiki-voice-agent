# BUILD_STATUS — Kiki Voice Agent (The Complete Trip)

**Project:** Voice AI disruption-recovery agent · **Repo:** `complete-trip`
**Stack:** Vocal Bridge + FastAPI backend · **Dev tool:** Claude Code
**Traveler:** Mary · **Voice agent:** Kiki

> Paste this whole file into a build chat to re-orient, then say:
> "Work on the next unchecked item: [X]. Repo is `complete-trip`, FastAPI, MOCK_MODE=true."

---

## ✅ Done
- [x] Backend scaffolded — FastAPI, `complete-trip` repo structure
- [x] All 9 endpoints built: `/trip/status`, `/flights/search`, `/flights/rebook`, `/hotel/adjust`, `/dining/move`, `/transport/update`, `/payment/confirm`, `/demo/reset`, + shared `TRIP` state
- [x] `MOCK_MODE` + `PAYMENT_MOCK` + `MOCK_DELAY_SECONDS` (1.5s) config working
- [x] `TRIP` state mutates correctly — hotel/dinner/pickup stay AT_RISK until their own endpoints fire
- [x] All 3 pytest tests pass; verified live (`/trip/status` = 1.506s, rebook → `price_difference: 45.20`)
- [x] `/demo/reset` restores the cancellation for repeat rehearsals
- [x] Traveler renamed to **Mary**; **Kiki** = voice agent only
- [x] Vocal Bridge account + practice agents (barista, weather) — platform basics learned

---

## 🔴 CURRENT BLOCKER — voice model won't produce audio (Background AI ON)

**Symptom:** With Background AI **ON**, the voice agent wouldn't speak at all (no greeting). With Background AI **OFF**, Kiki talks fine — but can't fetch data or complete a booking (no tool calls fire).

**Root cause (from session `8c9e552e`, 2026-07-10):** the failure is the **foreground voice model**, not tool-calling. The agent connected (`initializing → listening`) and tried to speak the greeting **15×**, but every attempt threw `realtime_model_error` — **516 errors** from **OpenAI `gpt-realtime-1.5`** over 74s. Result: `transcript: []`, `message_count: 0`, zero audio. **The custom tools were never reached** — so the "9 tools / token-mint / tool-URL" theories below are NOT what broke this run. This looks like an OpenAI Realtime **quota / API-key / model-access / outage** problem on the voice layer.

**Fix the voice model first (in this order):**
1. **Retry once** — rules out a transient OpenAI Realtime outage.
2. **Agent settings → Model/voice** — try a **different voice model** than `gpt-realtime-1.5`; if the alternate speaks, it's model-access/quota on that model.
3. **OpenAI API key / credit** — if VB uses your own OpenAI key, confirm it's valid, funded, and has Realtime access. If VB manages the key, check free-tier realtime-minute limits (note the "Upgrade" button).

**Only once the greeting plays** do the tool-calling concerns below apply:
- **Token minting** — browser needs a short-lived session token, minted server-side:
  `POST https://vocalbridgeai.com/api/v1/token` · headers `X-API-Key`, `X-Agent-Id`, `Content-Type: application/json` · body `{"participant_name":"Web User"}` → `{ token, connection_url, ... }`. A missing `X-Agent-Id` is a suspect. *(Not the cause of this run — the model failed before any tool call.)*
- **Tool URL** — endpoints are already public HTTPS on Render (**deploy is DONE**), not `localhost`. ✅ resolved.
- **Tool count** — Chatty is documented as best for 1–2 tools; Kiki has 9. Watch for flaky tool-calling *after* the voice model works → if so, Plan B.

**→ If, once voice works, the 9 Custom API tools stay flaky, switch to AI Agent mode (Plan B below).**

---

## Vocal Bridge: three modes (and what mixes)

| Mode | How it works | Our use |
|---|---|---|
| **Custom API tools** (Background AI ON) | VB's own brain decides which of your REST endpoints to call | Current path — core rebooking |
| **AI Agent mode** (Background AI OFF) | VB = thin voice layer. Every spoken turn POSTs to *your* `/query` endpoint; your code orchestrates and returns a string; VB speaks it | **Plan B** — we own the 9-step logic |
| **Client Actions** | Bidirectional agent↔UI over WebRTC data channel (`useAgentActions` hook) | The live itinerary UI (layers on top of either mode) |

⚠️ **AI Agent mode and Background AI are mutually exclusive.** Create the agent with `--background-enabled false` + `--ai-agent-file ai-agent.json`.

### Plan B: AI Agent mode (if 9 tools stay unreliable)
- Add ONE route to the existing backend: `POST /query` → takes `{query}`, runs Claude with our 9 endpoints as tools, returns `{response}` string.
- VB config: `ai-agent.json` with `enabled`, `description` (what the agent is good at — guides VB on when to delegate), `verbatim: false` (lets VB polish phrasing for natural delivery).
- Client side: `useAIAgent({ onQuery })` — one hook; forwards every spoken turn to `/query`, speaks whatever string comes back.
- **Upside:** we own the orchestration; VB no longer has to choose among 9 tools. Existing endpoints are reused, not thrown away.

---

## ⬜ Next up (in order)
- [x] **Deploy backend to Render** → **live at https://kiki-complete-trip.onrender.com** (auto-deploys on `git push`; `/health` 200 + full flow verified via curl)
      *(free tier sleeps ~30–50s after idle — warm it with one `/trip/status` call before any rehearsal/demo)*
- [x] Wire 3 core tools in Vocal Bridge: `get_trip_status`, `search_flights`, `rebook_flight` (POST, No auth, pointed at the Render URL; see [`TOOL_WIRING.md`](TOOL_WIRING.md)) — configured, not yet verified live (blocked below)
- [ ] **Unblock the voice model** (see CURRENT BLOCKER) — no greeting/audio until `gpt-realtime-1.5` runs
- [ ] First end-to-end voice run: "My flight got cancelled — fix my trip"
- [ ] If still flaky → **switch to AI Agent mode (Plan B)**
- [ ] Wire remaining 6 tools (hotel, dining, transport, payment)
- [ ] **Full 9-tool test pass** — every tool fires + AT_RISK items flip to rescued in `/trip/status`

## ⬜ Later
- [ ] Live itinerary UI via **Client Actions** (`useAgentActions`; declare events in `actions.json`, create agent with `--client-actions-file`). Pattern: Kiki rebooks → fires `update_itinerary` → card flips AT_RISK → rescued. Mirror the tic-tac-toe `board_sync` pattern so the agent's mental model stays in sync with the screen. **Fallback:** UI polls `/trip/status` every 2s — same visual effect, boring plumbing, judges can't tell.
- [ ] PayPal sandbox payment (or keep `PAYMENT_MOCK=true` fallback)
- [ ] Event day: `MOCK_MODE=false` → real Sabre credentials
- [ ] Backup demo video + rehearse ×5

## ⬜ Stretch / Plan C
- [ ] **Outbound call** ("Kiki calls the hotel and waits on hold") — `make_phone_call` tool with a required `purpose` param; agent needs `--outbound-enabled true --accept-outbound-tos`. Pattern = base prompt + per-call purpose injected at call time. **Requires paid plan.** High wow-factor, high risk — only if everything else is done.

---

## Tool wiring reference (3 core tools)

| Tool name | Method | URL (append to Render base) | Description |
|---|---|---|---|
| `get_trip_status` | POST | `…/trip/status` | Returns the traveler's full current itinerary with per-item status. Call this first when the user reports a problem, to assess impact. |
| `search_flights` | POST | `…/flights/search` | Search alternative flights after a disruption. Call ONLY after a cancellation is confirmed, never for initial booking. |
| `rebook_flight` | POST | `…/flights/rebook` | Rebook onto a chosen flight. Requires explicit verbal user confirmation before calling. Returns confirmation and price difference. |

---

## Key learnings
- **Background AI = the tool-calling engine.** OFF → agent talks but can't use tools. ON → required for Custom API tools. OFF only for AI Agent mode.
- **Agents hallucinate rather than call tools** unless the prompt explicitly forbids it. Kiki's prompt must say: *"Never invent flights, times, or prices — always call a tool."* (Learned the hard way on the weather practice agent.)
- **Bridge lines beat silence.** Instruct the agent to say a short line the moment a query is delegated — *"hang on, checking…"* — because tool calls take 1–6s. Per the VB course: *"that's the difference between feeling fast and feeling broken."* Real Sabre will be slower than our 1.5s mock.
- **Chatty style is documented as best for 1–2 tools.** Kiki has 9. If tool-calling is unreliable, this is a likely cause → Plan B.
- **Free tier = 1 agent.** Edit the same agent in place. Fine — Kiki is the only agent that matters.
- **Debug tools:** `vb logs` (structured log of every turn + action), `vb debug` (live event stream during a call), `vb eval <session_id> --objective "..."` (scores a recorded call 0–10 and returns concrete prompt fixes). If Kiki misbehaves in rehearsal, run an eval instead of guessing at the prompt.
