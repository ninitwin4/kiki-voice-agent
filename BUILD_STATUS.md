# BUILD_STATUS — Kiki Voice Agent (The Complete Trip)

**Project:** Voice AI disruption-recovery agent · **Repo:** `complete-trip`
**Stack:** Vocal Bridge (Chatty, web) + FastAPI backend · **Dev tool:** Claude Code
**Traveler:** Mary · **Voice agent:** Kiki

> To re-orient a Claude Code build chat, paste this file and add:
> "Here's where we are — I want to work on the next unchecked item: [X].
> Repo is `complete-trip`, FastAPI backend, MOCK_MODE=true."

---

## ✅ Done
- [x] Backend scaffolded — FastAPI, `complete-trip` repo structure
- [x] All 9 endpoints built: `/trip/status`, `/flights/search`, `/flights/rebook`, `/hotel/adjust`, `/dining/move`, `/transport/update`, `/payment/confirm`, `/demo/reset`, plus shared `TRIP` state
- [x] `MOCK_MODE` + `PAYMENT_MOCK` + `MOCK_DELAY_SECONDS` (1.5s) config working
- [x] In-memory `TRIP` state mutates correctly — hotel/dinner/pickup stay AT_RISK until their own endpoints fire
- [x] All 3 pytest tests pass; verified live (`/trip/status` = 1.506s, rebook returned `price_difference: 45.20`)
- [x] `/demo/reset` restores the cancellation for repeat rehearsals
- [x] Traveler renamed to **Mary**; **Kiki** = voice agent only (find-and-replace across TRIP object, README, fixtures + pytest re-run)

## ⬜ Next up (in order)
- [x] Deploy backend to Render free tier → **live at https://kiki-complete-trip.onrender.com** (auto-deploys on `git push`; verified `/health` 200 + full flow via curl)
      *(note: free tier sleeps ~30–50s after idle — warm it with one `/trip/status` call before rehearsal/demo)*
- [ ] Wire 3 core tools into Kiki: `get_trip_status`, `search_flights`, `rebook_flight` — see [`TOOL_WIRING.md`](TOOL_WIRING.md)
- [ ] First end-to-end voice run: "My flight got cancelled — fix my trip"
- [ ] Wire remaining 6 tools (hotel, dining, transport, payment)
- [ ] **Full 9-tool test pass** — every tool fires + AT_RISK items flip to rescued in `/trip/status`

## ⬜ Later phases
- [ ] Live itinerary UI (client actions / polling fallback)
- [ ] PayPal sandbox payment (or keep `PAYMENT_MOCK` fallback)
- [ ] Event day: swap `MOCK_MODE=false` → real Sabre credentials
- [ ] Backup demo video + rehearse ×5

---

## Tool wiring reference (3 core tools)

| Tool name | Method | URL (append to Render base) | Description (paste as tool description) |
|---|---|---|---|
| `get_trip_status` | POST | `…/trip/status` | Returns the traveler's full current itinerary with per-item status. Call this first when the user reports a problem, to assess impact. |
| `search_flights` | POST | `…/flights/search` | Search alternative flights after a disruption. Call ONLY after a cancellation is confirmed, never for initial booking. |
| `rebook_flight` | POST | `…/flights/rebook` | Rebook onto a chosen flight. Requires explicit verbal user confirmation before calling. Returns confirmation and price difference. |

**Vocal Bridge reminders:** Background AI must be ON (tool-calling needs it). Persona prompt must forbid guessing: "Never invent flights, times, or prices — always call a tool."

## Key learnings (from practice agents)
- Agent will hallucinate answers rather than call tools unless the prompt explicitly forbids it.
- Free tier = 1 agent only; edit the same agent in place (fine — Kiki is the only agent that matters).
- Tool-call latency is audible; filler speech will cover it. Real Sabre will be slower than the 1.5s mock.
