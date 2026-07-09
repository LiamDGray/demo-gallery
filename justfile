# Demo Gallery — Task Runner
# ~/src/demo/justfile

default: check

# ── Status ──────────────────────────────────────────────────

# Check which services are running
check:
    @echo "=== Demo Gallery Services ==="
    @for port in 8001 8002 8003 8004 8005 8006 8007 8008 8009 8010 8090; do \
        if ss -tlnp | grep -q ":$port "; then \
            echo "  ✅ :$$port — $$(ss -tlnp | grep ":$port " | head -1 | sed 's/.*users:((//;s/)).*//')"; \
        else \
            echo "  ❌ :$$port — not running"; \
        fi; \
    done

# ── Dev Portal ──────────────────────────────────────────────

# Generate per-demo dev console pages
gen-dev-consoles:
    python3 dev-portal/gen-dev-consoles.py

# ── Services ────────────────────────────────────────────────

# Start all demo services
start-all:
    @echo "Use demo-setup.sh for full startup:"
    @echo "  sops exec-env ~/secrets.enc.env './demo-setup.sh'"

# Start Intersect engine
start-intersect:
    cd ~/src/intersect && sops exec-env ~/secrets.enc.env 'uvicorn app.main:app --host 127.0.0.1 --port 8010' &
    @echo "Intersect starting on :8010"

# Start token auth service
start-auth:
    cd token-auth-service && .venv/bin/uvicorn main:app --host 127.0.0.1 --port 8090 &

# Start Caddy (demo gallery)
start-caddy:
    sudo caddy run --config Caddyfile &

# Start Caddy (dev portal)
start-caddy-dev:
    sudo caddy run --config Caddyfile.dev --watch &

# ── Deploy ──────────────────────────────────────────────────

# Deploy demo gallery to CF Pages (if using Pages for static)
deploy-gallery:
    @echo "Deploy gallery/ to CF Tunnel (managed separately)"

# ── Tunnel ──────────────────────────────────────────────────

# Restart cloudflared tunnel
restart-tunnel:
    systemctl --user restart cloudflared-demo.service

# ── Git ─────────────────────────────────────────────────────

# Show current state
status:
    git status -s
