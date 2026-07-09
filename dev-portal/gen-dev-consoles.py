#!/usr/bin/env python3
"""Generate per-demo dev console pages for dev.liamdgray.com.

Usage: python3 gen-dev-consoles.py
Scans ~/src/demo/dev-portal/demos/ and creates a page for each project.
"""
import json, os, subprocess

BASE = os.path.expanduser("~/src/demo/dev-portal")
DEMOS_DIR = os.path.join(BASE, "demos")
TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{name} — Dev Console</title>
<style>
:root{{--bg:#0d1117;--fg:#e6edf3;--accent:#58a6ff;--border:#30363d;--green:#3fb950;--yellow:#d29922}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--fg);line-height:1.6;padding:2rem;}}
.container{{max-width:960px;margin:0 auto}}
h1{{font-size:1.75rem;margin-bottom:0.25rem}}
.sub{{color:#8b949e;font-size:0.9rem;margin-bottom:2rem}}
.card{{background:#161b22;border:1px solid var(--border);border-radius:8px;padding:1.25rem;margin-bottom:1rem}}
.card h3{{font-size:1rem;margin-bottom:0.5rem;color:var(--accent)}}
.card p,.card pre{{font-size:0.85rem;color:#8b949e}}
pre{{background:#0d1117;padding:0.75rem;border-radius:6px;overflow-x:auto;font-size:0.8rem;color:var(--fg)}}
.link-btn{{display:inline-flex;align-items:center;gap:0.3rem;padding:0.3rem 0.75rem;border-radius:4px;font-size:0.8rem;text-decoration:none;border:1px solid var(--border);color:#9ca3af;background:#0d1117;margin-right:0.5rem}}
.link-btn:hover{{border-color:var(--accent);color:var(--accent)}}
.link-btn.primary{{background:#238636;color:#fff;border-color:#238636}}
.back-link{{margin-bottom:1rem;display:inline-block;color:var(--accent);text-decoration:none;font-size:0.9rem}}
.back-link:hover{{text-decoration:underline}}
.status-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:0.75rem;margin:1rem 0}}
.stat-card{{background:#0d1117;border:1px solid var(--border);border-radius:6px;padding:0.75rem;text-align:center}}
.stat-card .num{{font-size:1.25rem;font-weight:600;color:var(--green)}}
.stat-card .label{{font-size:0.75rem;color:#8b949e}}
</style>
</head>
<body>
<div class="container">
<a href="/" class="back-link">← Dev Console</a>
<h1>{icon} {name}</h1>
<p class="sub">{desc} — dev console</p>

<div class="card">
  <h3>📦 Repo</h3>
  <p><a href="{github_url}" style="color:var(--accent)">{github_url}</a></p>
</div>

<div class="card">
  <h3>📊 Status</h3>
  <p>Status: <strong style="color:{status_color}">{status_label}</strong></p>
</div>

<div class="card" style="display:flex;gap:0.75rem">
  <a href="{demo_url}" class="link-btn primary" target="_blank">🌐 {demo_label} ↗</a>
  <a href="{github_url}" class="link-btn" target="_blank">📦 GitHub ↗</a>
</div>
</div>
</body>
</html>
"""

PROJECTS = {
    "geo-csg": {"name": "GeoCSG", "icon": "🧊", "desc": "Photo → editable CAD", "status": "ready", "github_url": "https://github.com/LiamDGray/geo-csg", "demo_url": "https://demo.liamdgray.com/geo-csg/", "demo_label": "Live Demo ↗"},
    "agent-debate": {"name": "Agent Debate", "icon": "🗣️", "desc": "AI persona debates", "status": "ready", "github_url": "https://github.com/LiamDGray/agent-debate", "demo_url": "https://demo.liamdgray.com/agent-debate/", "demo_label": "Live Demo ↗"},
    "name-check": {"name": "Name Check", "icon": "🔍", "desc": "Domain + trademark conflicts", "status": "ready", "github_url": "https://github.com/LiamDGray/name-conflict-check", "demo_url": "https://demo.liamdgray.com/name-check/", "demo_label": "Live Demo ↗"},
    "voice-chat": {"name": "Voice Chat", "icon": "🎤", "desc": "WebSocket voice interface PWA", "status": "building", "github_url": "", "demo_url": "https://demo.liamdgray.com/voice-chat/", "demo_label": "Live Demo ↗"},
    "afterlife": {"name": "Afterlife", "icon": "💳", "desc": "x402 micropayment proxy", "status": "building", "github_url": "https://github.com/LiamDGray/afterlife", "demo_url": "https://demo.liamdgray.com/afterlife/", "demo_label": "Live Demo ↗"},
    "artcall": {"name": "ArtCall", "icon": "🎨", "desc": "Artist grant/residency call scraper", "status": "ready", "github_url": "", "demo_url": "https://demo.liamdgray.com/artcall/", "demo_label": "Live Demo ↗"},
    "loc3net": {"name": "Loc3Net", "icon": "🌐", "desc": "BYOD stealth proxy", "status": "building", "github_url": "https://github.com/LiamDGray/loc3net", "demo_url": "https://demo.liamdgray.com/loc3net/", "demo_label": "Live Demo ↗"},
    "behavioral": {"name": "Behavioral Mimic", "icon": "🧠", "desc": "Browse recording + behavioral dist", "status": "building", "github_url": "", "demo_url": "https://demo.liamdgray.com/behavioral/", "demo_label": "Live Demo ↗"},
    "sigstead": {"name": "Sigstead", "icon": "🔐", "desc": "Crypto provenance for AI agents", "status": "ready", "github_url": "https://github.com/LiamDGray/sigstead", "demo_url": "https://demo.liamdgray.com/sigstead/", "demo_label": "Live Demo ↗"},
}

def main():
    os.makedirs(DEMOS_DIR, exist_ok=True)
    for slug, p in PROJECTS.items():
        d = os.path.join(DEMOS_DIR, slug)
        os.makedirs(d, exist_ok=True)
        sc = "var(--green)" if p["status"] == "ready" else "var(--yellow)"
        sl = "⭐ Ready" if p["status"] == "ready" else "🔨 In Progress"
        html = TEMPLATE.format(
            name=p["name"], icon=p["icon"], desc=p["desc"],
            status_color=sc, status_label=sl,
            github_url=p["github_url"] or "#",
            demo_url=p["demo_url"], demo_label=p["demo_label"],
        )
        with open(os.path.join(d, "index.html"), "w") as f:
            f.write(html)
        print(f"  ✓ {slug}/")

if __name__ == "__main__":
    main()
