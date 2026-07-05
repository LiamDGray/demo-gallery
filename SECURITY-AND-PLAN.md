# Security & Architecture Deep-Dive

## 1. Reverse Proxy: Caddy vs Rust Alternatives

| Criterion | **Caddy (Go)** | **sozu (Rust)** | **Pingora (Rust framework)** | **Custom hyper (Rust)** |
|---|---|---|---|---|
| Turnkey? | ✅ Yes, one Caddyfile | ✅ Yes, config file | ❌ Framework, ~200 lines Rust | ❌ ~300 lines Rust |
| forward_auth | ✅ Built-in directive | ❌ No — need custom middleware | 🔧 Manual impl | 🔧 Manual impl |
| WebSocket passthrough | ✅ Automatic | ✅ Automatic | ✅ Requires config | ✅ Manual |
| Static file serving | ✅ Built-in | ❌ No | ✅ Via pingora_web crate | ❌ Manual |
| Memory safety | ✅ GC + bounds-checked | ✅ Rust ownership | ✅ Rust ownership | ✅ Rust ownership |
| Binary size | ~20MB static | ~15MB | ~5MB (library only) | ~4MB |
| On T430s (4c i5) | ✅ ~15MB RSS, instant start | ✅ ~12MB RSS, ~200ms start | ❌ Needs compilation | ❌ Needs compilation |
| Maintainable by you? | ✅ Change Caddyfile | ✅ Change config.toml | ❌ Must write Rust code | ❌ Must write Rust code |
| Proven in production | ✅ Millions of sites | ✅ Smaller deployments | ✅ Cloudflare scale | ❌ Custom |

**Both Go and Rust are memory-safe** — the attack surface difference is negligible for this use case.

**Verdict: Stick with Caddy.** The proxy is not the security bottleneck — the demo backends behind it are. Caddy is memory-safe, simpler to configure, and forward_auth is a 1-line directive. There's no Rust turnkey proxy with comparable `forward_auth` ergonomics.

---

## 2. Sandboxing: bwrap vs systemd.exec

Both are available. **Prefer systemd.exec** — zero extra processes, native integration.

```ini
# /etc/systemd/system/demo@.service — template for ALL demo backends
[Unit]
Description=Demo %i
After=network.target
After=caddy.service

[Service]
Type=simple
ExecStart=/usr/local/bin/demo-runner %i

# ═══ FILESYSTEM ISOLATION ═══
ProtectSystem=strict              # / read-only
ProtectHome=tmpfs                  # /home /root hidden
PrivateTmp=true                    # Private /tmp + /var/tmp
ReadWritePaths=/var/lib/demo-%i /var/log/demo-%i /run/demo-%i
BindReadOnlyPaths=/opt/demos/%i

# ═══ NETWORK ISOLATION ═══
PrivateNetwork=true                # Loopback only
IPAddressAllow=127.0.0.1           # Only localhost

# ═══ PROCESS ISOLATION ═══
ProtectProc=invisible
NoNewPrivileges=true
CapabilityBoundingSet=
SystemCallFilter=@system-service
MemoryDenyWriteExecute=true
LockPersonality=true
RestrictRealtime=true
RestrictNamespaces=true

# ═══ USER ISOLATION ═══
DynamicUser=true                   # Per-service transient UID
PrivateUsers=true                  # User namespace isolation

[Install]
WantedBy=multi-user.target
```

bwrap can be added for defense-in-depth on the most sensitive demos, but the systemd template above already covers:

| Threat | Blocked by |
|---|---|
| Demo reads another demo's code | `ProtectHome=tmpfs` + `ReadWritePaths` scoping |
| Demo writes to system dirs | `ProtectSystem=strict` (/) |
| Demo connects to internet | `PrivateNetwork=true` + `IPAddressAllow=127.0.0.1` |
| Demo ptrace's another demo | `ProtectProc=invisible` + `NoNewPrivileges` + `CapabilityBoundingSet=` |
| Demo reads /etc/passwd, /etc/ssh, etc. | `InaccessiblePaths=/etc` (add to template) |
| Demo runs as shared user | `DynamicUser=true` (ephemeral UID per service) |
| Demo survives compromise to persist | `PrivateTmp=true` + `DynamicUser=true` |

---

## 3. Telegram Auth Flow

The architecture supports it. Extend the token-auth service with a "pending approvals" table and a Telegram bot.

```
Visitor                     Demo Server                    Telegram Bot           You
   │                            │                              │                  │
   ├─ "Request Access" ────────►│                              │                  │
   │                            ├── POST /request-demo ──────►│                  │
   │                            │   {demo, ip, timestamp}      │                  │
   │                            │                              ├── Inline Keybd ──►│
   │                            │                              │   [Approve] [Deny] │
   │                            │                              │◄── Button: Yes ───┤
   │                            │◄── /token-issue ◄────────────│                  │
   │◄── ?token=xxx ◄───────────│                              │                  │
   │  (polling or page reload) │                              │                  │
```

Implementation:
- `demo-bot/` directory in this repo with a Python bot using the Telegram Bot API
- Bot polls the token-auth service's `/pending` endpoint or gets webhook callbacks
- On approval, calls `/token-issue` with the visitor's requested demo + short duration (24h)
- Visitor's page detects the token via polling (GET /check-status?id=ABC every 3s) or WebSocket

The bot code is lightweight — the `xurl` tool can handle Telegram messaging, but for inline keyboard interactions, a small Python script using `python-telegram-bot` or raw webhooks is cleaner.

---

## 4. Analytics

Per-demo tracking: pageviews, feature usage, errors.

**Design:** lightweight event-logging endpoint on the token-auth service:

```
POST /api/event
  {demo_id, event_type, event_data, session_id, timestamp}

GET /api/stats
  Returns: {demos: [{id, views, errors, features:{...}}]}
```

Each demo's HTML gets a small injected `<script>` that:
- Fires a `pageview` event on load
- Wraps global `onerror` / `unhandledrejection` to log JS errors
- Demo authors emit custom events via `window.__demo_event({type, data})`

Storage: SQLite in `~/.demo/stats.db`. Simple, no infra.

Dashboard at `/admin/stats` shows:
| Demo | Views | Errors | Unique Tokens | Top Features | Error Rate |
|---|---|---|---|---|---|
| geo-csg | 47 | 3 | 5 | upload, auth, queue | 6.4% |
| voice-chat | 12 | 8 | 2 | connect, vad, ptt | 66.7% |

Auto-highlight demos with >20% error rate for attention.

---

## 5. Per-Project Phase 1 Actions

### geo-csg — Branch + Simplify Core
The app has a full SaaS structure already (FastAPI + auth + queue + Stripe + frontend). The core pipeline uses `DepthAnythingAdapter` + `GeoCSGEncoder` + `HRRTreeDecoder` with PyTorch on CPU — but the new algos don't work yet.

**Plan:** Create `demo/simple-core` branch. Swap the pipeline to a deterministic geometry algorithm that works on a T430s:
- Accept photo upload
- Run a simple edge-detection + extrusion pipeline (OpenCV, no ML)
- Generate OpenSCAD output
- Keep all the SaaS plumbing intact (auth, queue, email, frontend)

The app as a SaaS chassis is already impressive — just need a working backend.

### name-conflict-check — Max-Uses Token
The code is an MCP server (stdio), not an HTTP server. Two options:
1. **Wrap as HTTP** (like agent-debate) — expose check_domains + check_trademark via JSON POST endpoints
2. **Token system already supports `max_uses: 2`** in the token-auth service design. When issuing a token for this demo, set max_uses=2.

**Need:** Build the HTTP wrapper first, then enforce at token level.

### voice-chat — Study → Fix or Skip
Deep analysis complete (see subagent report). 14 bugs found, ~80% in frontend JS. Architecture is sound.

**Recommendation: Fix (~2-3 days) for demo.** The top-priority fixes:
1. Make HermesProcessor streaming (asyncio subprocess instead of subprocess.run) — eliminates the biggest UX flaw
2. Fix VAD/PTT state machine race (debounce onend auto-restart) — stops transcript loss
3. Add auto-reconnect (exponential backoff on ws.onclose)
4. Add conversation context (pass last N turns to Hermes)
5. Remove dead code (~20 LOC dead)

If you decide to skip: the comparison table in the subagent report has links to Pipecat, Vocode, LiveKit Agents — any could replace the backend.

### agent-debate — Wrap MCP for HTTP
Simple HTTP wrapper. The MCP server logic (debate state machine) is cleanly separated from transport. Create an HTTP server that:
- POST /debate-create {proposition, rounds, roles}
- POST /debate-round {debate_id, round_args}
- Backend calls the LLMs itself (no longer delegates to the agent)
- Returns structured debate JSON for the frontend

The frontend: a simple HTML page that shows the debate unfolding round by round.

---

## Updated Architecture

```
cloudflared ←── Caddy (:8080) ─── forward_auth → token-auth (:8090)
                                      │
              ┌───────────────────────┼───────────────────────┐
              │                       │                       │
         systemd sandbox         systemd sandbox         systemd sandbox
         geo-csg (:8001)         agent-debate (:8006)    name-check (:8002)
              │                       │                       │
         bwrap (opt)             bwrap (opt)             bwrap (opt)

Analytics DB ←─── token-auth (:8090) logs all events
Telegram Bot ←─── token-auth (:8090) pending approvals
```
