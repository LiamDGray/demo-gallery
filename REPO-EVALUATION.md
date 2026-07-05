# Demo Gallery — Repo Evaluation

**goal:** Serve live demos at `demo.liamdgray.com` via CF tunnel + reverse proxy, with time-limited links for prospective clients.

**75 repos evaluated** (your own projects; forks excluded). Each assessed for:
- ⭐ **Ready** — has a working web service/API that can be proxied as-is
- 🔨 **Buildable** — code has a plausible web demo path with moderate effort
- 🧪 **CLI Wrapper** — CLI/lib that could get a web frontend
- 📄 **Docs/Config** — not demoable as a running service
- ⏳ **Stub** — 1-commit initial states, not worth demoing yet

---

## TIER A: ⭐ Ready to Proxy

These repos already run a web service, have a server entry point, or are already deployed. Could be behind the reverse proxy today.

| Repo | Type | What to proxy | Effort |
|---|---|---|---|
| **geo-csg** | FastAPI | `uvicorn app.backend.main:app` on :8000. SaaS with auth/queue. | **Zero** — already a web app |
| **voice-chat** | PWA + WS | `uv run python3 -m server` → :8766. Serves PWA at `/`. | **Zero** — just needs WSS proxy |
| **voice-bridge** | WS server | `.venv/bin/python -m server` → :8765. Mock mode for testing. | **Minimal** — needs WSS + health page |
| **artcall** | Python server | Already deployed to artcall.liamdgray.com. Just route to existing infra. | **Zero** — already live |
| **name-conflict-check** | Node server | `node server.mjs` → HTTP. Domain + trademark checker. | **Minimal** — needs env config |
| **socratic-site** | HTML + Docker | `docker compose up` or static serve from `functions/`. Has `index.html`. | **Minimal** |
| **liamdgray.com** | Static site | Already live at liamdgray.com. Just route. | **Zero** — already live |
| **schoolboard** | Hugo static | Already deployed to CF Pages. Just route. | **Zero** — already live |
| **ubl** | Astro static | Already deployed to CF Pages. Just route. | **Zero** — already live |
| **sigstead** | Pages deploy | Has `pages.yml` workflow. Static docs site. | **Minimal** |
| **hermes-voice-study** | Python server | `server/app.py` → HTTP. Voice demo. | **Minimal** |
| **email2mqtt** | Worker + Node | Complex multi-service (CF Worker + local Playwright). **Not suitable** as a simple demo gating target. | Skip for now |

**Recommendation for Tier A:** Start with **geo-csg**, **voice-chat**, and **name-conflict-check** — they're the most presentable to clients. geo-csg is the crown jewel (SaaS with auth tiers).

---

## TIER B: 🔨 Buildable Web Demo (moderate effort)

These have APIs or CLIs that could get a meaningful web UI.

| Repo | Commits | What exists | Demo idea | Effort |
|---|---|---|---|---|
| **realpeep** | 102 | Python provenance core + CF Pages deploy. BLE mesh + ZK identity. | Dashboard showing provenance chain status, hash chain visualizer | 2-3 days |
| **afterlife-relay** | 7 | Rust relay with Docker. Lease-gated CONNECT proxy. | Relay health dashboard: live conns, lease metrics, proxy pool status | 1-2 days |
| **afterlife** | 1 | Python daemon. x402 payment + lease issuance. | Payment flow demo: request proxy, get x402 challenge, show lease | 1-2 days |
| **behavioral-mimicry** | 8 | Browser recorder extension + CLI analyzer (TS) | Upload recording → see behavioral distributions, gap analysis chart | 1-2 days |
| **sluice** | 1 | Proxy scraper/validator + Puddle storage | Pool dashboard: live pool count, uptime %, geo-distribution of proxies | 1 day |
| **puddle** | 1 | DuckDB wrapper library | Query playground: connect to a puddle DB, run SQL, see results | 0.5 day |
| **candidate-manager** | 1 | V8 sandbox candidate runner | "Test your parser" — paste input, run candidates, see results | 0.5 day |
| **solverprog** | 29 | Symbolic reasoning engine (SLR) | Reasoning trace viewer — step through RLR inference | 2-3 days |
| **TrackXY** | 30 | OpenCV object tracker (C++) | Upload video → see tracking overlay (complex, needs GPU?) | 3-5 days |
| **loc3net** | 25 | Go proxy network | Network topology map — show relay nodes, routes, latency | 1-2 days |
| **evidance** | 27 | Onyx-based RAG with docker-compose | Already has docker-compose + nginx. Could proxy the Onyx web UI. | 1 day (complex infra) |
| **resumex** | 31 | Chrome extension + backend API | Job → tailored resume preview. Backend API already exists. | 1 day to expose API |
| **agent-debate** | 1 | MCP server (stdio) | Wrap in HTTP: submit prompt, see multi-round debate. | 1 day |
| **mcp-loop-checker** | 1 | MCP server (stdio) | Wrap in HTTP: feed thoughts, see loop detection visualization | 1 day |

**High-value picks for clients:**
- **realpeep** — the most ambitious project, visuals are compelling (hash chains, mesh consensus)
- **afterlife-relay** — demonstrates the x402 micropayment/proxy-vending model
- **behavioral-mimicry** — very visual (distributions, gaps, behavioral profiles)
- **loc3net** — sell the "phone as exit node" architecture

---

## TIER C: 🧪 CLI Wrapper Possible

These are CLI tools or libraries that *could* get a web wrapper but the payoff isn't obvious for client demos.

| Repo | Commits | Demo idea |
|---|---|---|
| **priorities-digest** | 9 | Web report of repo activity |
| **tweets** | 1 | Twitter analysis report viewer |
| **hermes-stealth-mcp** | 7 | Stealth HTTP test page — curl through stealth proxy |
| **appbot** | 1 | Job board aggregator — web results view |
| **cooling** | 11 | Truck part search results viewer |
| **smolpaper** | 2 | Email sender test |
| **wiggum-loop** | 1 | Task runner status page |

---

## TIER D: 📄 Docs/Config — Not Demoable

These are research, config, or documentation repos. They don't produce a running service.

| Repo | Reason |
|---|---|
| **p51nix** | NixOS system config |
| **antisci / medtextract** | Medical text extraction pipeline (research pipeline, not a service) |
| **supps-lmn** | Literature review + DuckDB |
| **graykm** | Knowledge management paper + prototype files |
| **openecg** | Biosensing hardware research docs |
| **openaed** | AED hardware BOM/cost analysis |
| **wardrobe** | USB modem compatibility docs |
| **llmghidra** | Formal verification survey paper |
| **selfmod** | Meta repo list |
| **teaching** | Teaching schema/catalog |
| **nixharness** | NixOS test infrastructure |
| **bt** | Bluetooth scripts and logs |
| **pumpswitch** | Relay driver simulation data |
| **cooling** | Truck parts research |

---

## TIER E: ⏳ Stubs — Not Worth Demoing

These are 1-commit "Initial state" repos with no real development yet. Skip.

doh-proxy, drives, langclaw, legacydata, minions, scraper, secrets-email2mqtt, thyroid, torrent, truck, tut, wifi, hacking, hitrust, automators, liam-todo, localrsi, supps-mog, stealth-patches

---

## Priority Recommendations for demo.liamdgray.com

### Phase 1: Ready to deploy (week 1) — mostly done
1. **geo-csg** ✅ Architected, SaaS chassis already works. Need to:
   - Create `demo/simple-core` branch
   - Replace ML pipeline with deterministic edge-detect+extrusion (OpenCV, no PyTorch)
   - Keep auth/queue/Stripe/frontend — the SaaS chassis is the demo value
2. **name-conflict-check** ✅ **HTTP wrapper built** (`demo-server.mjs` + `demo.html`)
   - Token-level enforcement: issue tokens with `max_uses: 2`
   - Client-side counter shows remaining checks
   - Proxied at `/name-check` → :8002
3. **agent-debate** ✅ **HTTP wrapper built** (`demo-server.mjs` + `demo.html`)
   - Runs actual multi-round LLM debates via OpenRouter
   - 4 presets (Tech, Philosophy, Policy, Fun) + custom proposition
   - Proxied at `/agent-debate` → :8006
4. **artcall** — Already deployed at artcall.liamdgray.com, just add to gallery landing page

### Phase 1b: Needs decision
5. **voice-chat** ⚠️ 14 bugs found (see voice-chat investigation report)
   - Architecture is sound, ~80% of bugs are in frontend JS
   - **~2-3 days to fix** for demo-ready
   - Key fix: streaming subprocess for Hermes (eliminates biggest UX flaw)
   - If skip: Pipecat, Vocode, or LiveKit Agents could replace the backend

### Phase 2: Build web wrappers (week 2-3)
6. **realpeep-dashboard** — Provenance chain visualizer (flagship project)
7. **afterlife-relay** — Live proxy relay status + x402 payment flow demo
8. **behavioral-mimicry** — Upload behavior recording, see analysis distributions
9. **sigstead** — Verify an agent decision record online

### Phase 3: Niche but compelling (week 3+)
10. **solverprog/reasoning-trace** — Step-through inference viewer
11. **loc3net/map** — Network topology + latency dashboard
12. **TrackXY/video** — Upload video, track objects (needs GPU)

### Infrastructure ready
- **Repo**: `~/src/demo/` with full architecture plan (SECURITY-AND-PLAN.md)
- **Proxy**: Caddy recommended over Rust turnkey options (same memory safety, simpler config, forward_auth is 1 line vs ~200 lines Rust)
- **Sandboxing**: systemd.exec template unit (zero extra processes) preferred over bwrap
  - 10 demos = ~2-5MB overhead via systemd vs ~12-17MB extra processes via bwrap
  - systemd covers: ProtectHome=tmpfs, PrivateNetwork=true, DynamicUser=true, ProtectProc=invisible
  - bwrap optionally for defense-in-depth on sensitive demos
- **Auth**: Token-auth service + optional Telegram bot for visitor→approval→token flow
- **Analytics**: Lightweight event logging endpoint (POST /api/event + GET /api/stats), SQLite storage
