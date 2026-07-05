# Demo Gallery Architecture

## Goal

Serve live demos of all your projects at **demo.liamdgray.com**, with a secure reverse proxy between the Cloudflare Tunnel and each backend, and time-limited links for prospective clients.

```
Client (prospect's browser)
    │
    ▼
demo.liamdgray.com ←── Cloudflare DNS (orange-cloud/ proxied)
    │
    ▼
Cloudflare Tunnel (cloudflared, systemd-managed)
    │  ::10225
    ▼
Caddy Reverse Proxy  (:8080 — internal)
    │  Forward_Auth ↓
    ├── /geo-csg       → localhost:8001
    ├── /voice-chat    → localhost:8766
    ├── /name-check    → localhost:8002
    ├── /realpeep      → localhost:8003
    ├── /afterlife     → localhost:8004
    ├── /artcall       → localhost:8005
    ├── /agent-debate  → localhost:8006
    ├── /behavioral    → localhost:8007
    │
    ▼
Token Auth Service  (:8090)
    ├── Issue endpoint — POST /token-issue (your admin key in header)
    ├── Verify endpoint — Caddy forward_auth hits this on every request
    └── Token table — in-memory or SQLite: {token_hash, path, expires_at}
```

---

## Component Details

### 1. Cloudflare Tunnel

Already managed via existing infra. Add an ingress entry:

```yaml
# ~/.cloudflared/config.yml
ingress:
  - hostname: demo.liamdgray.com
    service: http://localhost:8080
  - service: http_status:404
```

Create DNS:

```bash
cloudflared tunnel route dns <tunnel-id> demo.liamdgray.com
```

### 2. Caddy Reverse Proxy (security layer)

Caddy runs on `:8080` (internal, only cloudflared talks to it). Uses `forward_auth` directive backed by a small token-auth service.

**Caddyfile:**

```
demo.liamdgray.com {
    # Forward_auth — every request hits the token checker first
    forward_auth localhost:8090 {
        uri /verify
        copy_headers Cf-Access-Jwt-Assertion
        # Pass original URI so the auth service knows which path
        header_up X-Original-URI {uri}
        header_up X-Original-Method {method}
    }

    # Route definitions
    handle_path /geo-csg/* {
        reverse_proxy localhost:8001
    }
    handle_path /voice-chat/* {
        reverse_proxy localhost:8766
    }
    handle_path /name-check/* {
        reverse_proxy localhost:8002
    }
    handle_path /realpeep/* {
        reverse_proxy localhost:8003
    }
    handle_path /afterlife/* {
        reverse_proxy localhost:8004
    }
    handle_path /artcall/* {
        reverse_proxy localhost:8005
    }
    handle_path /agent-debate/* {
        reverse_proxy localhost:8006
    }
    handle_path /behavioral/* {
        reverse_proxy localhost:8007
    }

    # Landing page — gallery of all demos
    handle {
        root * /var/www/demo-gallery
        file_server
    }
}
```

**Why Caddy over nginx:**
- Automatic TLS (not needed here since tunnel handles it, but good for local dev)
- `forward_auth` is a single Caddyfile directive vs. nginx's `auth_request` + complex subrequest handling
- Simpler config, fewer footguns
- Auto-restarts on config change (`caddy reload`)

### 3. Token Auth Service

A small service that issues and verifies time-limited tokens. Lightweight — Python/FastAPI'd be ~50 lines.

```python
# token-auth-service/main.py
import hashlib, hmac, time, sqlite3, uuid, os
from fastapi import FastAPI, Request, Response
from pydantic import BaseModel

app = FastAPI()
SECRET = os.environ.get("TOKEN_SECRET", "change-me")
DB_PATH = "/var/lib/demo-auth/tokens.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tokens (
            token_hash TEXT PRIMARY KEY,
            path TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            expires_at INTEGER NOT NULL,
            max_uses INTEGER DEFAULT 1,
            uses INTEGER DEFAULT 0,
            label TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

class IssueRequest(BaseModel):
    path: str              # e.g. "/geo-csg"
    duration_hours: int = 24
    max_uses: int = 1      # 0 = unlimited
    label: str = ""        # client name for tracking

class IssueResponse(BaseModel):
    url: str
    token: str
    expires_at: str
    path: str

# --- Issue endpoint (admin only) ---
@app.post("/token-issue")
def issue_token(req: IssueRequest, request: Request):
    key = request.headers.get("X-Admin-Key", "")
    if key != SECRET:
        return Response(status_code=403, content="unauthorized")

    token = uuid.uuid4().hex + uuid.uuid4().hex  # 64 hex chars
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    now = int(time.time())
    expires_at = now + (req.duration_hours * 3600)

    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT OR REPLACE INTO tokens (token_hash, path, created_at, expires_at, max_uses, uses, label) VALUES (?,?,?,?,?,0,?)",
        (token_hash, req.path, now, expires_at, req.max_uses, req.label)
    )
    conn.commit()
    conn.close()

    return {
        "url": f"https://demo.liamdgray.com{req.path}?token={token}",
        "token": token,
        "expires_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(expires_at)),
        "path": req.path
    }

# --- Verify endpoint (called by Caddy forward_auth) ---
@app.get("/verify")
def verify(request: Request):
    token = request.headers.get("X-Original-Token") or request.query_params.get("token", "")
    uri = request.headers.get("X-Original-URI", "/")
    method = request.headers.get("X-Original-Method", "GET")

    if not token:
        return Response(status_code=401, content="missing token")

    token_hash = hashlib.sha256(token.encode()).hexdigest()
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT path, expires_at, max_uses, uses FROM tokens WHERE token_hash = ?",
        (token_hash,)
    ).fetchone()
    conn.close()

    if not row:
        return Response(status_code=403, content="invalid token")

    path, expires_at, max_uses, uses = row
    now = int(time.time())

    if now > expires_at:
        return Response(status_code=403, content="token expired")

    # Check path prefix — token for /geo-csg works on /geo-csg/* too
    requested_dir = "/" + uri.split("/")[1]
    if not uri.startswith(path):
        # Allow root-level exact match
        if uri != path:
            return Response(status_code=403, content="path mismatch")

    # Consume a use
    if max_uses > 0:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("UPDATE tokens SET uses = uses + 1 WHERE token_hash = ?", (token_hash,))
        conn.commit()
        # Delete if exhausted
        if uses + 1 >= max_uses:
            conn.execute("DELETE FROM tokens WHERE token_hash = ?", (token_hash,))
        conn.commit()
        conn.close()

    return Response(status_code=200, content="ok")

# --- List active tokens (admin only) ---
@app.get("/tokens")
def list_tokens(request: Request):
    key = request.headers.get("X-Admin-Key", "")
    if key != SECRET:
        return Response(status_code=403, content="unauthorized")

    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT path, created_at, expires_at, uses, max_uses, label FROM tokens ORDER BY created_at DESC"
    ).fetchall()
    conn.close()

    return [
        {
            "path": r[0],
            "created_at": r[1],
            "expires_at": r[2],
            "uses": r[3],
            "max_uses": r[4],
            "label": r[5],
        }
        for r in rows
    ]
```

### 4. Service Launcher

Each demo backend runs as its own systemd user service or is managed by a supervisord-like runner.

**Option A: systemd user services** (preferred for production)

Each backend gets its own service file. Example:

```ini
# ~/.config/systemd/user/demo-geo-csg.service
[Unit]
Description=Demo: geo-csg
After=network-online.target

[Service]
Type=simple
ExecStart=/home/liam/src/geo-csg/.venv/bin/uvicorn app.backend.main:app --host 127.0.0.1 --port 8001
Restart=on-failure
RestartSec=5
WorkingDirectory=/home/liam/src/geo-csg

[Install]
WantedBy=default.target
```

**Option B: demo-runner.sh** (simpler for ramping up)

```bash
#!/usr/bin/env bash
# ~/src/demo/demo-runner.sh — start all demo backends
set -e

BASE=$HOME/src/demo

start_service() {
    local name=$1 port=$2 cmd=$3
    if lsof -i :$port >/dev/null 2>&1; then
        echo "[OK] $name already running on :$port"
    else
        echo "[START] $name on :$port"
        nohup bash -c "$cmd" > "$BASE/logs/$name.log" 2>&1 &
        echo $! > "$BASE/pids/$name.pid"
    fi
}

mkdir -p "$BASE/logs" "$BASE/pids"

start_service "geo-csg"     8001 "cd ~/src/geo-csg && .venv/bin/uvicorn app.backend.main:app --host 127.0.0.1 --port 8001"
start_service "voice-chat"  8766 "cd ~/src/voice-chat && uv run python3 -m server --port 8766"
start_service "name-check"  8002 "cd ~/src/name-conflict-check && node server.mjs"
# ... etc
```

---

## Time-Limited Link Flow

```
1. Admin creates a token:
   curl -X POST https://demo.liamdgray.com/token-issue \
     -H "X-Admin-Key: $SECRET" \
     -H "Content-Type: application/json" \
     -d '{"path":"/geo-csg","duration_hours":72,"max_uses":3,"label":"Acme Corp demo"}'

2. Response:
   {
     "url": "https://demo.liamdgray.com/geo-csg?token=abc123...",
     "expires_at": "2026-07-08T12:00:00Z",
     "label": "Acme Corp demo"
   }

3. Send the URL to prospect. They click it, Caddy forward_auth hits the
   verify endpoint, token is consumed (or bypassed for duration window).

4. After expiry or use limit is hit: URL returns 403, no further access.
```

## Security Model

| Layer | What it prevents |
|---|---|
| **CF Tunnel** | No open ports on server; traffic encrypted to edge |
| **Caddy reverse proxy** | Only defined routes reachable; no direct backend access |
| **Forward auth + token** | Only bearers of a valid, unexpired, unused token can access |
| **Token hash (SHA-256)** | Token in URL is one-way — DB compromise doesn't leak active tokens |
| **Path binding** | Token for `/geo-csg` can't be used on `/afterlife` |
| **Use count** | Single-use links prevent sharing; multi-use for demos with multiple viewers |
| **Expiry** | 24h/72h/7d windows limit exposure window |

## Future: Layering Cloudflare Access

For admin-only routes (token issuance UI, health dashboard), layer **Cloudflare Access (Zero Trust)** with email OTP on top of the tunnel. This gives you:

```
demo.liamdgray.com/admin/*  →  Cloudflare Access (email OTP)  →  Caddy  →  Admin dashboard
demo.liamdgray.com/*?token= →  No Cloudflare Access             →  Caddy  →  Token auth
```

## Onboarding a New Demo

1. Add the service to the launcher (port, command)
2. Add route to Caddyfile (`handle_path /new-thing/*`)
3. Add systemd service or launcher entry
4. `caddy reload`
5. Issue a test token: `curl -X POST ... -d '{"path":"/new-thing","duration_hours":1}'`

## Directory Layout

```
~/src/demo/
├── README.md                    # This file
├── REPO-EVALUATION.md           # Full repo-by-repo analysis
├── Caddyfile                    # Reverse proxy config
├── token-auth-service/
│   ├── main.py                  # FastAPI token issuer/verifier
│   ├── requirements.txt         # fastapi, uvicorn, pydantic
│   └── token-auth.service       # systemd unit for the auth service
├── demo-runner.sh               # Start all backend services
├── gallery/                     # Landing page static files
│   └── index.html               # Gallery of all available demos
└── logs/                        # Service logs
```
