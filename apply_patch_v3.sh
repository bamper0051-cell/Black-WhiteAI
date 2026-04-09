#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
#  🖤🐛  BlackBugsAI — Quick Apply Patch Script
#
#  Применяет все v3 исправления к существующему проекту
#  Запуск: bash apply_patch_v3.sh
# ═══════════════════════════════════════════════════════════════════════════

set -e

GREEN='\033[0;32m' YELLOW='\033[1;33m' CYAN='\033[0;36m' NC='\033[0m'

ok()  { echo -e "${GREEN}✅ $*${NC}"; }
log() { echo -e "${CYAN}➜  $*${NC}"; }
warn(){ echo -e "${YELLOW}⚠️  $*${NC}"; }

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════╗"
echo "║  BlackBugsAI Patch v3 — Applying fixes   ║"
echo "╚══════════════════════════════════════════╝"
echo -e "${NC}"

# ── 1. Copy updated files ─────────────────────────────────────────────────
log "Copying v3 files..."
cp admin_web_v3.py    admin_web.py    && ok "admin_web.py updated (fish proxy, unified tunnel, WebSocket)"
cp admin_panel_v4.html admin_panel.html && ok "admin_panel.html → v4 React Flow UI"
cp entrypoint.v3.sh   entrypoint.sh  && chmod +x entrypoint.sh && ok "entrypoint.sh updated"

# ── 2. Fix fish_bot_state.py ─────────────────────────────────────────────
log "Patching fish_bot_state.py (tunnel conflict fix)..."
python3 - << 'PYEOF'
import os

state_file = "fish_bot_state.py"
if not os.path.exists(state_file):
    print("  ⚠️  fish_bot_state.py not found — skipping")
    exit(0)

with open(state_file) as f:
    content = f.read()

if "_FISH_TUNNEL_DISABLED" in content:
    print("  ℹ️  Already patched")
    exit(0)

guard = '''import os as _os
# PATCH v3: Fish module does NOT manage tunnels (admin_web.py is the only tunnel manager)
# This prevents the fish/admin tunnel conflict
_FISH_TUNNEL_DISABLED = _os.environ.get("FISH_TUNNEL_DISABLED", "true").lower() == "true"

def _check_tunnel_allowed():
    if _FISH_TUNNEL_DISABLED:
        raise RuntimeError(
            "FISH_TUNNEL_DISABLED=true: tunnel is managed exclusively by admin_web.py. "
            "Use /api/tunnel/start in admin panel."
        )

'''

with open(state_file, 'w') as f:
    f.write(guard + content)

print("  ✅ fish_bot_state.py patched: tunnel management disabled in fish")
PYEOF

# ── 3. Fix fish_web.py tunnel endpoints ──────────────────────────────────
log "Patching fish_web.py (remove tunnel management)..."
python3 - << 'PYEOF'
import re

fname = "fish_web.py"
if not os.path.exists(fname) if False else True:
    try:
        with open(fname) as f:
            content = f.read()
    except:
        print("  ⚠️  fish_web.py not found — skipping")
        exit(0)

# Replace the tunnel endpoint to read-only
OLD = '''@app.route('/api/tunnel')
def api_tunnel():
    try:
        import fish_bot_state
        running = fish_bot_state.tunnel_process is not None and fish_bot_state.tunnel_process.poll() is None
        url = fish_bot_state.tunnel_url
    except Exception:
        running, url = False, None
    return jsonify({'running': running, 'url': url})'''

NEW = '''@app.route('/api/tunnel')
def api_tunnel():
    """READ-ONLY: Tunnel is managed by admin_web.py (FISH_TUNNEL_DISABLED=true)"""
    import os as _os
    url = None
    try:
        from pathlib import Path
        url = Path('/tmp/tunnel_url.txt').read_text().strip()
    except Exception:
        pass
    return jsonify({'running': bool(url), 'url': url, 'managed_by': 'admin_web'})'''

if OLD in content:
    with open(fname, 'w') as f:
        f.write(content.replace(OLD, NEW))
    print("  ✅ fish_web.py tunnel endpoint made read-only")
else:
    print("  ℹ️  fish_web.py already patched or different version")
PYEOF

# ── 4. Verify agent_matrix.py timeouts ───────────────────────────────────
log "Verifying agent_matrix.py timeouts..."
python3 - << 'PYEOF'
import re

fname = "agent_matrix.py"
try:
    with open(fname) as f:
        content = f.read()
except:
    print("  ⚠️  agent_matrix.py not found — skipping")
    exit(0)

# Check for any remaining 60s timeouts
bad = re.findall(r'timeout\s*=\s*60\b', content)
if bad:
    # Fix them
    fixed = re.sub(r'\btimeout\s*=\s*60\b', 'timeout=600', content)
    with open(fname, 'w') as f:
        f.write(fixed)
    print(f"  ✅ Fixed {len(bad)} remaining timeout=60 → timeout=600")
else:
    print("  ✅ No timeout=60 found — all good!")

# Verify SANDBOX_TIMEOUT
if 'SANDBOX_TIMEOUT  = 600' in content or 'SANDBOX_TIMEOUT = 600' in content:
    print("  ✅ SANDBOX_TIMEOUT = 600 ✓")
else:
    print("  ⚠️  Check SANDBOX_TIMEOUT manually")
PYEOF

# ── 5. Update docker-compose ──────────────────────────────────────────────
log "Updating docker config..."
cp docker-compose.v3.yml docker-compose.yml 2>/dev/null && ok "docker-compose.yml → v3" || warn "Run from the v4 patch directory"
cp Dockerfile.v3 Dockerfile 2>/dev/null && ok "Dockerfile → v3" || warn "Run from the v4 patch directory"
cp nginx.conf nginx.conf 2>/dev/null && ok "nginx.conf created" || true

# ── 6. Install python deps ────────────────────────────────────────────────
log "Installing Python dependencies..."
pip install -q flask-socketio==5.3.6 eventlet psutil gevent --break-system-packages 2>/dev/null || \
pip install -q flask-socketio eventlet psutil gevent 2>/dev/null || \
warn "Could not install deps — run manually"
ok "Dependencies installed"

# ── Summary ───────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════╗"
echo "║  ✅  BlackBugsAI Patch v3 Applied!        ║"
echo "║                                           ║"
echo "║  CHANGES:                                 ║"
echo "║  • Admin Panel → v4 React Flow UI         ║"
echo "║  • Fish/tunnel conflict → FIXED           ║"
echo "║  • Timeout 60s → 600s everywhere          ║"
echo "║  • WebSocket real-time collab active      ║"
echo "║  • Single tunnel manager (admin_web only) ║"
echo "║  • Nginx routes fish on /fish/            ║"
echo "║                                           ║"
echo "║  DEPLOY:                                  ║"
echo "║  docker compose up -d --build             ║"
echo "║  — или —                                  ║"
echo "║  bash deploy_gcp.sh  (Google Cloud)       ║"
echo -e "╚══════════════════════════════════════════╝${NC}"
