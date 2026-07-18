# BUILD_STATUS — Kiki Voice Agent

**Project:** Ambient voice travel agent · **Repo:** `kiki-voice-agent` (GitHub)
**Stack:** Vocal Bridge (voice) + FastAPI backend + React UI · **Dev tool:** Claude Code
**Scenario:** Ni Ni & RC plan Maui — the **weather cascade** · **Voice agent:** Kiki (agent `98d6dd19…`)
**Sponsors integrated:** Vocal Bridge ✅ · Sabre ✅ · PayPal ✅
**Live backends:** `kiki-complete-trip.onrender.com` (UI backend) · `kiki-real.onrender.com`

> Paste this file into a build chat to re-orient. Contract of record: [`CONTRACT.md`](../CONTRACT.md).

---

## The demo (30 seconds)

Ni Ni (party of 2) and RC (party of 3, incl. a 5-year-old) plan Maui. They start on the
**first week of November** → Kiki checks the weather (VB Web Search), finds it's the **rainy
season** → RC won't travel in rain → Kiki moves the trip to dry **August (Aug 5, 5 nights)**
in one call. Flights, hotel, minivan, and activities all re-date and re-price together. Kiki
recalls their prefs (RC: local/vegetarian cuisine; Ni Ni: pack deodorant + hair mask), then
they book and pay. The cascade is real (november + august are separate datasets).

---

## ✅ Done
- [x] Backend: 9 tools + in-memory `TRIP`, the month cascade, `/trip/configure` re-sizing
- [x] Deployed on Render, two services (mock UI backend + real), auto-deploy on push
- [x] **Voice working** — model `gpt-realtime-2`; ambient "quiet third friend" prompt
- [x] **Scenario = Ni Ni & RC weather cascade** (November → August), 5 nights; tests rewritten
- [x] **Sabre (real):** hybrid flight search — curated bookable options **+ live Sabre fares
      (Flight Shop v1) + real Travel Seasonality**; real Maui hotels via MCP-Skills. Unlocked
      by PCC `S5OM` (from the team's `sabre-api-testing` repo). Cars unavailable; activities mock.
- [x] **PayPal (real):** sandbox Orders v2 create + capture verified
- [x] **Vocal Bridge (real):** `POST /token` live (minted a real token, HTTP 200) — key stays server-side
- [x] **Client actions configured** on Kiki — the 7 agent→app signals + 2 app→agent (exact
      CONTRACT names); prompt says when to fire each
- [x] `/trip/status` audited field-for-field against `CONTRACT.md §1` — exact match
- [x] `CONTRACT.md` gap audit done (see at-risk items below)

---

## ⬜ Next up (tonight)
- [ ] **Wire the SDK in the UI** (in the UI chat) — `POST /token` returns
      `{livekit_url, token, room_name, participant_identity, expires_in, agent_mode}`.
      `VITE_API_BASE` = `kiki-complete-trip`.
- [ ] **Set secrets on `kiki-complete-trip` Render env** and redeploy:
      `VB_API_KEY`, a **fresh** `SABRE_ACCESS_TOKEN` (expires!), and confirm
      `SABRE_FLIGHTS_LIVE` / `SABRE_HOTELS_LIVE` are on.
- [ ] **Full live rehearsal** — voice → screen: weather → Nov→Aug reflow → book → pay
- [ ] Turn **Debug mode OFF** on the agent for the real demo

## ⚠️ Known at-risk (from the audit)
- **Sabre token expiry** — CERT tokens die within hours; the live Sabre *proof* goes blank if
  stale. Mitigated: hybrid design degrades to pure-mock (never breaks). Refresh right before demo.
- **`book_flight` + real IDs** — real Sabre flight IDs aren't bookable by design; that's exactly
  why flights are hybrid (bookable options stay mock). No action needed unless you go full-real.
- **`kiki-real` token** was stale in the audit — refresh if you demo that URL directly.

## ⬜ Later / stretch
- [ ] Full PayPal capture in the UI (approve → capture) for a completed sandbox transaction on screen
- [ ] Real Sabre booking (create-booking via MCP) — heavy, creates real CERT PNRs; out of scope for demo

---

## Key learnings
- **Voice model matters** — `gpt-realtime-1.5` produced zero audio; `gpt-realtime-2` works.
- **Ambient design** — empty greeting + observer prompt + `semantic_vad`/`eagerness: low`; Kiki
  wakes on her name or a real finding. `Listener` style has no voice pipeline — don't use it.
- **VB client actions** run through `trigger_client_action`; declare them (`client_actions.json`)
  AND tell the prompt when to fire. `Conversation-Id` header is required for MCP-Skills calls.
- **Sabre** — the hackathon token needs PCC `S5OM`; Flight Shop v1 (`api.cert.platform.sabre.com`)
  gives real itineraries, hotels only via MCP (`mcp2.cert.sabre.com`), cars nowhere. A Sabre 404
  often means "no results," not a missing endpoint.
- **Two-level auth** — a self-minted Sabre OAuth token may lack the MCP/PCC attribute the
  pre-issued token carries. **PayPal** auth is plain Basic; **Sabre** is double-base64 — don't share helpers.
- **Session JSON is ground truth** — `vb logs <id> --json` shows exactly which tools/actions fired.
- **`vb` CLI** drives prompt/config/logs from the terminal — faster and dodges the flaky tool-editor UI.
