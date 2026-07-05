"""
token-auth-service — Token issuer, verifier, and demo-request approval system.

Endpoints:
  POST   /token-issue             Admin: create a token (X-Admin-Key header)
  GET    /verify                   Caddy forward_auth: validate request token
  GET    /tokens                   Admin: list active tokens
  POST   /api/request-demo        Visitor: request access to a demo
  GET    /api/pending              Bot: poll for pending approvals
  PATCH  /api/resolve/:id          Bot: approve/deny a pending request
  POST   /api/event               Visitor: log analytics event
  GET    /api/stats               Admin: get per-demo stats
"""

import hashlib
import json
import os
import sqlite3
import time
import uuid
from pathlib import Path

import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ─── Config ──────────────────────────────────────────────────────────────────

SECRET = os.environ.get("DEMO_AUTH_SECRET", os.urandom(32).hex())
DB_PATH = os.environ.get("DEMO_DB_PATH", str(Path.home() / ".demo" / "auth.db"))
ADMIN_CHAT_ID = os.environ.get("TG_CHAT_ID", "")

app = FastAPI(title="Demo Auth & Analytics")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ─── DB init ─────────────────────────────────────────────────────────────────

def get_db():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS tokens (
            token_hash TEXT PRIMARY KEY,
            path TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            expires_at INTEGER NOT NULL,
            max_uses INTEGER DEFAULT 1,
            uses INTEGER DEFAULT 0,
            label TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS pending_requests (
            id TEXT PRIMARY KEY,
            demo_id TEXT NOT NULL,
            visitor_ip TEXT DEFAULT '',
            email TEXT DEFAULT '',
            reason TEXT DEFAULT '',
            status TEXT DEFAULT 'pending',
            approved_token TEXT DEFAULT '',
            created_at INTEGER NOT NULL,
            resolved_at INTEGER
        );
        CREATE TABLE IF NOT EXISTS analytics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            demo_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            event_data TEXT DEFAULT '{}',
            session_id TEXT DEFAULT '',
            created_at INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_pending_status ON pending_requests(status);
        CREATE INDEX IF NOT EXISTS idx_analytics_demo ON analytics(demo_id, event_type);
    """)
    conn.commit()
    conn.close()

init_db()

# ─── Models ──────────────────────────────────────────────────────────────────

class IssueRequest(BaseModel):
    path: str
    duration_hours: int = 24
    max_uses: int = 1
    label: str = ""

class DemoRequest(BaseModel):
    demo_id: str
    email: str = ""
    reason: str = ""

class ResolveRequest(BaseModel):
    action: str  # "approve" or "deny"
    duration_hours: int = 24
    max_uses: int = 1

class AnalyticsEvent(BaseModel):
    demo_id: str
    event_type: str
    event_data: str = "{}"
    session_id: str = ""

# ─── Auth helpers ────────────────────────────────────────────────────────────

def require_admin(key: str = Header(None, alias="X-Admin-Key")):
    if not key or key != SECRET:
        raise HTTPException(403, "unauthorized")

def get_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    return forwarded.split(",")[0].strip() or request.client.host or ""

# ─── Token endpoints ─────────────────────────────────────────────────────────

@app.post("/token-issue")
def issue_token(req: IssueRequest, admin=Depends(require_admin)):
    token = uuid.uuid4().hex + uuid.uuid4().hex
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    now = int(time.time())
    expires_at = now + (req.duration_hours * 3600)

    conn = get_db()
    conn.execute(
        "INSERT OR REPLACE INTO tokens (token_hash, path, created_at, expires_at, max_uses, label) VALUES (?,?,?,?,?,?)",
        (token_hash, req.path, now, expires_at, req.max_uses, req.label),
    )
    conn.commit()
    conn.close()

    return {
        "url": f"https://demo.liamdgray.com{req.path}?token={token}",
        "token": token,
        "expires_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(expires_at)),
        "path": req.path,
    }

@app.get("/verify")
def verify(request: Request):
    token = request.headers.get("X-Original-Token") or request.query_params.get("token", "")
    uri = request.headers.get("X-Original-URI", "/")

    if not token:
        return Response(status_code=401, content="missing token")

    token_hash = hashlib.sha256(token.encode()).hexdigest()
    conn = get_db()
    row = conn.execute(
        "SELECT path, expires_at, max_uses, uses FROM tokens WHERE token_hash = ?",
        (token_hash,),
    ).fetchone()
    if not row:
        conn.close()
        return Response(status_code=403, content="invalid token")

    path, expires_at, max_uses, uses = row
    now = int(time.time())

    if now > expires_at:
        conn.close()
        return Response(status_code=403, content="token expired")

    # Path prefix check — token for /geo-csg works on /geo-csg/*
    if not uri.startswith(path) and uri != path:
        conn.close()
        return Response(status_code=403, content="path mismatch")

    if max_uses > 0:
        conn.execute("UPDATE tokens SET uses = uses + 1 WHERE token_hash = ?", (token_hash,))
        if uses + 1 >= max_uses:
            conn.execute("DELETE FROM tokens WHERE token_hash = ?", (token_hash,))
        conn.commit()

    conn.close()
    return Response(status_code=200, content="ok")

@app.get("/tokens")
def list_tokens(admin=Depends(require_admin)):
    conn = get_db()
    rows = conn.execute(
        "SELECT path, created_at, expires_at, uses, max_uses, label FROM tokens ORDER BY created_at DESC LIMIT 50"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ─── Demo request flow ───────────────────────────────────────────────────────

@app.post("/api/request-demo")
def create_demo_request(req: DemoRequest, request: Request):
    rid = uuid.uuid4().hex[:12]
    now = int(time.time())
    conn = get_db()
    conn.execute(
        "INSERT INTO pending_requests (id, demo_id, visitor_ip, email, reason, status, created_at) VALUES (?,?,?,?,?,?,?)",
        (rid, req.demo_id, get_ip(request), req.email, req.reason, "pending", now),
    )
    conn.commit()
    conn.close()
    return {"request_id": rid, "status": "pending"}

@app.get("/api/pending")
def list_pending():
    conn = get_db()
    rows = conn.execute(
        "SELECT id, demo_id, visitor_ip, email, reason, created_at FROM pending_requests WHERE status = 'pending' ORDER BY created_at ASC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.patch("/api/resolve/{rid}")
def resolve_request(rid: str, req: ResolveRequest):
    conn = get_db()
    row = conn.execute("SELECT * FROM pending_requests WHERE id = ?", (rid,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "request not found")

    now = int(time.time())

    if req.action == "approve":
        # Issue a token for this demo
        token = uuid.uuid4().hex + uuid.uuid4().hex
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        expires_at = now + (req.duration_hours * 3600)

        conn.execute(
            "INSERT OR REPLACE INTO tokens (token_hash, path, created_at, expires_at, max_uses, label) VALUES (?,?,?,?,?,?)",
            (token_hash, f"/{row['demo_id']}", now, expires_at, req.max_uses, f"demo-request:{rid}"),
        )
        conn.execute(
            "UPDATE pending_requests SET status = 'approved', approved_token = ?, resolved_at = ? WHERE id = ?",
            (token, now, rid),
        )
        conn.commit()
        conn.close()
        return {
            "status": "approved",
            "request_id": rid,
            "url": f"https://demo.liamdgray.com/{row['demo_id']}?token={token}",
        }
    else:
        conn.execute("UPDATE pending_requests SET status = 'denied', resolved_at = ? WHERE id = ?", (now, rid))
        conn.commit()
        conn.close()
        return {"status": "denied", "request_id": rid}

@app.get("/api/request-status/{rid}")
def get_request_status(rid: str):
    conn = get_db()
    row = conn.execute("SELECT id, status, demo_id, approved_token, created_at FROM pending_requests WHERE id = ?", (rid,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "not found")
    result = dict(row)
    if result["status"] == "approved" and result["approved_token"]:
        result["url"] = f"https://demo.liamdgray.com/{row['demo_id']}?token={row['approved_token']}"
    return result

# ─── Analytics ───────────────────────────────────────────────────────────────

@app.post("/api/event")
def log_event(event: AnalyticsEvent):
    now = int(time.time())
    conn = get_db()
    conn.execute(
        "INSERT INTO analytics (demo_id, event_type, event_data, session_id, created_at) VALUES (?,?,?,?,?)",
        (event.demo_id, event.event_type, event.event_data, event.session_id, now),
    )
    conn.commit()
    conn.close()
    return {"ok": True}

@app.get("/api/stats")
def get_stats(admin=Depends(require_admin)):
    conn = get_db()
    rows = conn.execute("""
        SELECT
            demo_id,
            COUNT(*) as total_events,
            SUM(CASE WHEN event_type = 'pageview' THEN 1 ELSE 0 END) as views,
            SUM(CASE WHEN event_type LIKE 'error%' OR event_type = 'error' THEN 1 ELSE 0 END) as errors,
            SUM(CASE WHEN event_type LIKE 'feature_%' THEN 1 ELSE 0 END) as feature_uses
        FROM analytics
        GROUP BY demo_id
        ORDER BY views DESC
    """).fetchall()
    conn.close()
    stats = []
    for r in rows:
        d = dict(r)
        d["error_rate"] = round(d["errors"] / max(d["total_events"], 1) * 100, 1)
        stats.append(d)
    return stats

# ─── Main ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8090)
