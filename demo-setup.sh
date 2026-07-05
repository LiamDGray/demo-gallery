#!/usr/bin/env bash
# ─── demo-setup.sh — Bootstrap all demo.liamdgray.com services ───
#
# Run once after cloning ~/src/demo. Called by systemd or manually.
# Starts: token-auth service, demo-bot, and all demo backends.
#
# Usage:
#   sops exec-env ~/secrets.enc.env './demo-setup.sh'
#
# Requires env vars: DEMO_APPROVAL_ADMIN_KEY, DEMO_APPROVAL_BOT_TOKEN, DEMO_APPROVAL_CHAT_ID
# (set these in ~/secrets.enc.env)

set -euo pipefail
BASE="$HOME/src/demo"
mkdir -p "$BASE/logs" "$BASE/pids"

log() { echo "[$(date +%H:%M:%S)] $*"; }

# ─── 1. Token Auth Service (:8090) ──────────────────────────
start_service() {
  local name=$1 port=$2 pidfile=$3 logfile=$4 cmd=$5
  if [ -f "$BASE/pids/$pidfile" ] && kill -0 "$(cat "$BASE/pids/$pidfile")" 2>/dev/null; then
    log "[OK] $name already running on :$port (pid $(cat "$BASE/pids/$pidfile"))"
    return
  fi
  log "[START] $name on :$port"
  nohup bash -c "$cmd" > "$BASE/logs/$logfile" 2>&1 &
  echo $! > "$BASE/pids/$pidfile"
  sleep 1
  if kill -0 "$(cat "$BASE/pids/$pidfile")" 2>/dev/null; then
    log "[OK] $name started (pid $(cat "$BASE/pids/$pidfile"))"
  else
    log "[FAIL] $name failed to start — check $BASE/logs/$logfile"
  fi
}

# Token auth service (needs Python venv)
if [ -d "$BASE/token-auth-service/.venv" ]; then
  start_service "token-auth" 8090 "auth.pid" "auth.log" \
    "cd $BASE/token-auth-service && \
     DEMO_APPROVAL_ADMIN_KEY='${DEMO_APPROVAL_ADMIN_KEY:-dev-key}' \
     DEMO_DB_PATH='$HOME/.demo/auth.db' \
     .venv/bin/uvicorn main:app --host 127.0.0.1 --port 8090"
else
  log "[SKIP] token-auth — no .venv found. Run: cd $BASE/token-auth-service && uv venv && uv pip install -r requirements.txt"
fi

# ─── 2. Telegram Bot (polling, no port) ─────────────────────
if [ -n "${DEMO_APPROVAL_BOT_TOKEN:-}" ]; then
  start_service "demo-bot" "-" "bot.pid" "bot.log" \
    "cd $BASE/demo-bot && \
     DEMO_APPROVAL_BOT_TOKEN='${DEMO_APPROVAL_BOT_TOKEN}' \
     DEMO_APPROVAL_CHAT_ID='${DEMO_APPROVAL_CHAT_ID:-}' \
     DEMO_APPROVAL_ADMIN_KEY='${DEMO_APPROVAL_ADMIN_KEY:-dev-key}' \
     AUTH_URL=http://127.0.0.1:8090 \
     node bot.mjs"
else
  log "[SKIP] demo-bot — DEMO_APPROVAL_BOT_TOKEN not set"
fi

# ─── 3. Agent Debate (:8006) ────────────────────────────────
start_service "agent-debate" 8006 "agent-debate.pid" "agent-debate.log" \
  "cd $HOME/src/agent-debate && \
   OPENROUTER_API_KEY='${OPENROUTER_API_KEY:-}' \
   node demo-server.mjs"

# ─── 4. Name Check (:8002) ──────────────────────────────────
start_service "name-check" 8002 "name-check.pid" "name-check.log" \
  "cd $HOME/src/name-conflict-check && node demo-server.mjs"

log "─── Setup complete ───"
log "Token auth:  http://127.0.0.1:8090"
log "Agent debate: http://127.0.0.1:8006"
log "Name check:  http://127.0.0.1:8002"
log ""
log "Caddy reverse proxy: sudo caddy run --config $BASE/Caddyfile"
log "CF tunnel:           systemctl --user start cloudflared-demo.service"
echo ""
log "Add to ~/secrets.enc.env:"
log "  DEMO_APPROVAL_ADMIN_KEY=<random-hex>"
log "  DEMO_APPROVAL_BOT_TOKEN=<telegram-bot-token>"
log "  DEMO_APPROVAL_CHAT_ID=<your-chat-id>"
log ""
log "Then run: sops exec-env ~/secrets.enc.env './demo-setup.sh'"
