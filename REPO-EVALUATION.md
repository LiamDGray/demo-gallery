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

### Phase 1: Low-hanging fruit (week 1)
1. **geo-csg** — Most complete web app, SaaS-ready, auth already built
2. **name-conflict-check** — Simple Node server, useful tool anyone can try
3. **voice-chat** — PWA with speech, very interactive, good for demos
4. **artcall** — Already deployed, just add to launcher

### Phase 2: Build web wrappers (week 2-3)
5. **realpeep-dashboard** — Provenance chain visualizer (flag ship)
6. **afterlife-relay** — Live proxy relay status + payment flow demo
7. **behavioral-mimicry** — Upload behavior recording, see analysis
8. **agent-debate-http** — Wrap MCP server in HTTP for interactive demos

### Phase 3: Niche but compelling (week 3+)
9. **solverprog/reasoning-trace** — Step-through inference viewer
10. **loc3net/map** — Network topology + latency dashboard
11. **TrackXY/video** — Upload video, track objects (if GPU available)
