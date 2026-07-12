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

## ✅ RESOLVED — voice + 3 core tools working end-to-end (session `97191572`, 2026-07-10)

**The fix:** the foreground voice model **`gpt-realtime-1.5` was broken** (516 `realtime_model_error`, zero audio — session `8c9e552e`). **Switching to `gpt-realtime-2` fixed it** — next run had **0 errors** and a full 266s voice conversation.

**How VB actually runs your tools (confirmed):** the foreground voice model (OpenAI realtime) does NOT call Custom API tools directly. It calls a built-in **`submit_background_query`**, which hands off to **Background AI (Claude)**, which executes your REST tools against Render. → **Background AI must be ON** (with it OFF, only built-ins `end_call`/`put_on_hold`/`resume_from_hold`/`trigger_client_action` exist, and `get_trip_status` errors as "Unknown function").

**Verified live in one call:** greeting → `get_trip_status` (flight cancelled) → `search_flights` (recommends AA1885) → asks for verbal "yes" → `rebook_flight` (confirmed, +$45.20). Exactly the intended flow.

**Notes / minor polish:**
- `search_flights` returns `totalFare` but no original fare, so the price *difference* only comes from `rebook_flight` (45.20). Kiki narrated this correctly — no fix needed.
- STT (`gpt-realtime-whisper`) mis-hears the trigger occasionally ("flight cancelled" → "friend got cancer"). Speak the cue clearly in the demo.
- `end_call` is disabled → enable the **Hang up** capability if you want Kiki to end the call herself.

**Still on the table if 9 tools get flaky later:** AI Agent mode (Plan B below).

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
- [x] Wire 3 core tools in Vocal Bridge: `get_trip_status`, `search_flights`, `rebook_flight` (POST, No auth, Render URL; see [`TOOL_WIRING.md`](TOOL_WIRING.md)) — **verified live**
- [x] **Voice model fixed** — switched `gpt-realtime-1.5` → `gpt-realtime-2` (Agent settings); 0 errors
- [x] First end-to-end voice run: "My flight got cancelled — fix my trip" ✅ (session `97191572`)
- [ ] If 9 tools get flaky → **switch to AI Agent mode (Plan B)**
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
- **Voice model matters.** `gpt-realtime-1.5` threw 516 realtime errors (no audio); `gpt-realtime-2` works cleanly. If the agent won't speak, swap the voice model in Agent settings before debugging anything else.
- **Tool-call path:** foreground realtime model → built-in `submit_background_query` → Background AI (Claude) → your Custom API tools → Render. That's why Background AI must be ON.
- **Background AI = the tool-calling engine.** OFF → agent talks but only has built-ins (`end_call`, `put_on_hold`, `resume_from_hold`, `trigger_client_action`); your custom tools return "Unknown function." ON → required for Custom API tools. OFF only for AI Agent mode.
- **Agents hallucinate rather than call tools** unless the prompt explicitly forbids it. Kiki's prompt must say: *"Never invent flights, times, or prices — always call a tool."* (Learned the hard way on the weather practice agent.)
- **Bridge lines beat silence.** Instruct the agent to say a short line the moment a query is delegated — *"hang on, checking…"* — because tool calls take 1–6s. Per the VB course: *"that's the difference between feeling fast and feeling broken."* Real Sabre will be slower than our 1.5s mock.
- **Chatty style is documented as best for 1–2 tools.** Kiki has 9. If tool-calling is unreliable, this is a likely cause → Plan B.
- **Free tier = 1 agent.** Edit the same agent in place. Fine — Kiki is the only agent that matters.
- **Debug tools:** `vb logs` (structured log of every turn + action), `vb debug` (live event stream during a call), `vb eval <session_id> --objective "..."` (scores a recorded call 0–10 and returns concrete prompt fixes). If Kiki misbehaves in rehearsal, run an eval instead of guessing at the prompt.
