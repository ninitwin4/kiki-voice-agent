# Kiki v2 — Portfolio Roadmap

> **Paste this file into a fresh build chat to start v2.**
> Companion reading in this repo: `BUILD_STATUS.md` (state of play + learnings),
> `README.md` (architecture), `evidence/` (proof the integrations were live).

---

## 1. Why v2 exists

v1 was built to survive **one night on stage**: a rehearsed narrative, a warm backend, and a
human operator who could reset state between runs. It shipped and it worked
(tag `v1.0-hackathon`).

v2 has the opposite requirement: **a stranger clicks a link months later, alone, with no
context, and it has to work.** That single change of audience drives every decision below.

| | v1 (hackathon) | v2 (portfolio) |
|---|---|---|
| Audience | Judges, with you narrating | A recruiter/engineer, alone, unguided |
| Lifespan | One evening | Indefinite |
| Credentials | Fresh tokens, minutes old | Assume **all expired** |
| Failure mode | You recover live | Must self-recover, silently |
| Success | Demo lands | Visitor *understands* it in <60s |

---

## 2. What carries over unchanged

Do **not** rebuild these — they're done and proven:

- **FastAPI backend + mock engine.** Runs with zero credentials; 16 tests green.
- **The multi-vendor date cascade** (`/trip/rebook`) — still the most impressive mechanic.
- **`/trip/status` as single source of truth**, and the signal-and-refetch UI contract.
- **Graceful degradation.** Real data enriches; mock always carries the flow. This design
  is *why* v2 is even viable — it already survives dead tokens.
- **PayPal sandbox** (Orders v2). Sandbox creds don't expire like Sabre's.
- **`evidence/`** — the permanent proof the live integrations worked.

---

## 3. Decisions still open (settle these first in the new chat)

### 3a. What does Landing AI actually do? ⬅ biggest open question
It's the new differentiator, and it changes the UI, the tools, and the demo script.

**Recommended: Agentic Document Extraction on travel documents.** A visitor uploads (or
picks a sample) boarding pass / hotel confirmation / passport → Kiki extracts the details
and folds them into the itinerary. Why this fits:
- Visually obvious in a portfolio — you *see* a document become structured data
- Genuinely useful in the story ("I already booked a flight, here's the confirmation")
- Multimodal: pairs a vision/document model with the voice agent, which reads well
- Works offline-ish with bundled sample documents → no credential dependency for a visitor

**Alternatives worth 5 minutes of thought:** receipt reconciliation against the trip budget;
extracting a destination from a screenshot/brochure. Both weaker on "obvious in 10 seconds."

### 3b. Keep the ambient two-friend concept?
Ambient (Kiki listens to *two* people) is the distinctive idea — but a solo visitor can't
experience it. Options:
- **Recommended:** keep ambient as the *concept*, but make Kiki wake on her name so one
  person can drive it. Add a short recorded clip of the true two-friend flow.
- Or: switch v2 to single-user and keep ambient as a documented v1 story.

### 3c. How does a visitor with no microphone experience it?
A large fraction of portfolio visitors won't (or can't) talk to it. Needs an answer:
a scripted playback mode, a demo video above the fold, or a text-input fallback.

---

## 4. v2 workstreams

### A. Durability (the actual portfolio requirement)
- [ ] **Assume every credential is dead.** Verify the whole flow with an empty `.env`.
- [ ] **Kill the cold start** (Render free tier sleeps ~15 min → 30–50s first load). A
      visitor will leave. Either a keep-warm ping, a paid tier, or an instant-loading UI
      shell that hides the wake-up.
- [ ] **Self-resetting demo state** — no operator to hit `/demo/reset`. Auto-reset on new
      session, or per-session state instead of one global `TRIP`.
- [ ] **Honest live-vs-mock badge** in the UI. Never imply live data when serving mock.

### B. Landing AI integration (once 3a is decided)
- [ ] New `backend/landing_client.py`, mirroring the existing adapter pattern
      (`sabre_client.py` / `paypal_client.py`) — feature-flagged, degrades gracefully.
- [ ] Endpoint + Kiki tool + UI surface for the extraction result.
- [ ] Bundle sample documents so it works without the visitor uploading anything.
- [ ] Add to `evidence/` once verified live.

### C. Kiki v2 agent (Vocal Bridge)
- [ ] New VB agent; port the 9 tools + `client_actions.json` (`vb config set` — the CLI
      beats the flaky web tool-editor; see BUILD_STATUS learnings).
- [ ] Keep `gpt-realtime-2`. Re-tune VAD for a solo speaker if 3b changes.
- [ ] Update the prompt for the new narrative + Landing AI tool.
- [ ] Update `VB_AGENT_ID` in Render env.

### D. UI rebuild
- [ ] Landing/context above the fold: what this is, in one sentence, before any interaction.
- [ ] Document-extraction surface (per 3a).
- [ ] No-mic fallback (per 3c).
- [ ] Mobile — portfolio links get opened on phones.

### E. Portfolio framing
- [ ] README opens with the story + a demo GIF/video, not setup instructions.
- [ ] Link the `v1.0-hackathon` Release so the build history is visible.
- [ ] Architecture diagram (voice ↔ backend ↔ 4 APIs ↔ UI).
- [ ] Write up *decisions*, not just features — the hybrid design and graceful degradation
      are the strongest engineering signals here.

---

## 5. Branch strategy (decided)

- `main` — stays at the shipped v1 state; tagged **`v1.0-hackathon`** (`790ae7f`).
- `v2` — all v2 work happens here; **merge to `main` when v2 is solid.**
- One repo on purpose: the git history is timestamped proof this was built at a hackathon
  and upgraded afterward. A fresh repo would throw that away.

---

## 6. Known traps (learned the hard way — don't rediscover)

- **Sabre CERT tokens expire in hours.** Never let a demo depend on one being alive.
- **Sabre has no car inventory** on this token, and no activities product. Confirmed twice.
- **`gpt-realtime-1.5` produces zero audio** — use `gpt-realtime-2`.
- **VB's web tool-editor drops parameters** and throws `APITool id` errors. Use `vb config set`.
- **VB client-action params must be `body`, not `query`** — a `query` param yields a 422.
- **Set `git config user.email`** to the GitHub noreply address, or commits don't count
  toward contributions (this cost v1 its entire contribution graph until it was rewritten).
