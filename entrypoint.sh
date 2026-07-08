#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# BlackBugsAI — Entrypoint v3.0
# FIX: Единый туннельный менеджмент (больше нет конфликта fish/admin)
# FIX: Fish module на порту 5100, туннель → nginx:80 или admin:8080
# ═══════════════════════════════════════════════════════════════════════════

set -euo pipefail

# ── Banner ────────────────────────────────────────────────────────────────
cat << 'EOF'
╔══════════════════════════════════════════════════════╗
║  🖤🐛  BlackBugsAI v3.0 — Autonomous Agent Platform  ║
║  Matrix Agent · Neo Agent · Fish Module · Admin v4   ║
╚══════════════════════════════════════════════════════╝
EOF
echo "⏰ Started: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "🐍 Python: $(python3 --version)"
echo "📦 Platform: $(uname -m)"

cd /app

# ── Validate required env ─────────────────────────────────────────────────
[[ -z "${TELEGRAM_BOT_TOKEN:-}" ]] && echo "⚠️  TELEGRAM_BOT_TOKEN not set — bot won't start Telegram polling"
[[ -z "${ADMIN_WEB_TOKEN:-}" ]]    && echo "⚠️  ADMIN_WEB_TOKEN not set — using default (INSECURE!)"

# ── FISH TUNNEL FIX ───────────────────────────────────────────────────────
# Проблема: и fish_web.py и admin_web.py пытались управлять туннелем
# Решение:  fish получает FISH_TUNNEL_DISABLED=true → только admin управляет
export FISH_TUNNEL_DISABLED="${FISH_TUNNEL_DISABLED:-true}"
export FISH_SERVER_PORT="${FISH_SERVER_PORT:-5100}"

echo "🎣 Fish module port: $FISH_SERVER_PORT (tunnel: disabled=$FISH_TUNNEL_DISABLED)"

# ── Patch fish_bot_state to prevent tunnel management ─────────────────────
if [[ "$FISH_TUNNEL_DISABLED" == "true" ]]; then
  python3 - << 'PYEOF'
import os, sys
state_file = "fish_bot_state.py"
if os.path.exists(state_file):
    with open(state_file) as f:
        content = f.read()
    # Inject tunnel guard
    guard = '''
# INJECTED BY ENTRYPOINT v3: fish tunnel disabled (managed by admin_web only)
import os as _os
_FISH_TUNNEL_DISABLED = _os.environ.get("FISH_TUNNEL_DISABLED","true").lower() == "true"
'''
    if "_FISH_TUNNEL_DISABLED" not in content:
        with open(state_file, 'w') as f:
            f.write(guard + content)
        print("✅ fish_bot_state.py patched: tunnel disabled")
    else:
        print("ℹ️  fish_bot_state.py already patched")
PYEOF
fi

# ── Install deps if missing ────────────────────────────────────────────────
echo "📦 Checking Python deps..."

check_and_install() {
  python3 -c "import $1" 2>/dev/null || {
    echo "  Installing: $2..."
    pip install -q "$2" --break-system-packages 2>/dev/null || true
  }
}

check_and_install flask_socketio  "flask-socketio==5.3.6"
check_and_install psutil          "psutil"
check_and_install eventlet        "eventlet"
check_and_install gevent          "gevent"

# ── Apply admin panel v4 ──────────────────────────────────────────────────
if [[ -f "admin_panel_v4.html" ]]; then
  cp -f admin_panel_v4.html admin_panel.html
  echo "✅ Admin Panel v4 applied"
fi

# ── TUNNEL MANAGER ───────────────────────────────────────────────────────
# Один туннель, только если AUTO_TUNNEL=true
# Туннель указывает на ADMIN_WEB (8080) или на nginx (80 если есть)
_TUNNEL_PID=""

start_tunnel() {
  local provider="${TUNNEL_PROVIDER:-cloudflared}"
  local port="${TUNNEL_TARGET_PORT:-${ADMIN_WEB_PORT:-8080}}"

  echo "🌐 Tunnel: $provider → localhost:$port"

  case "$provider" in
    cloudflared)
      if command -v cloudflared &>/dev/null; then
        cloudflared tunnel --url "http://localhost:${port}" \
          --no-autoupdate \
          --logfile /tmp/cloudflared.log \
          2>&1 | while IFS= read -r line; do
            # Extract URL and write to shared state
            if echo "$line" | grep -qE 'trycloudflare\.com|cfargotunnel\.com'; then
              URL=$(echo "$line" | grep -oE 'https://[^\s]+\.(trycloudflare|cfargotunnel)\.com')
              [[ -n "$URL" ]] && echo "$URL" > /tmp/tunnel_url.txt && echo "🌐 Tunnel URL: $URL"
            fi
          done &
        _TUNNEL_PID=$!
      else
        echo "⚠️ cloudflared not found"
      fi
      ;;
    bore)
      local server="${BORE_SERVER:-bore.pub}"
      if command -v bore &>/dev/null; then
        bore local "${port}" --to "${server}" 2>&1 | tee /tmp/bore.log &
        _TUNNEL_PID=$!
        sleep 2
        BORE_URL=$(grep -oE 'bore\.pub:[0-9]+' /tmp/bore.log 2>/dev/null|head -1)
        [[ -n "$BORE_URL" ]] && echo "http://$BORE_URL" > /tmp/tunnel_url.txt && echo "🌐 Bore URL: http://$BORE_URL"
      else
        echo "⚠️ bore not found"
      fi
      ;;
    none|"")
      echo "ℹ️  Auto-tunnel disabled (set AUTO_TUNNEL=true to enable)"
      ;;
  esac
}

if [[ "${AUTO_TUNNEL:-false}" == "true" ]]; then
  sleep 8 && start_tunnel &
  echo "⏳ Auto-tunnel will start in 8 seconds..."
fi

# ── Graceful shutdown ─────────────────────────────────────────────────────
cleanup() {
  echo ""
  echo "⏹ BlackBugsAI shutting down..."
  [[ -n "$_TUNNEL_PID" ]] && kill "$_TUNNEL_PID" 2>/dev/null || true
  echo "👋 Bye!"
  exit 0
}
trap cleanup SIGTERM SIGINT SIGQUIT

# ── Status summary ────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════"
echo "  Admin Panel: http://localhost:${ADMIN_WEB_PORT:-8080}"
echo "  Fish Module: http://localhost:${FISH_SERVER_PORT:-5100} (internal)"
echo "  Tunnel:      ${AUTO_TUNNEL:-false} (provider: ${TUNNEL_PROVIDER:-cloudflared})"
echo "  Token:       ${ADMIN_WEB_TOKEN:0:8}..."
echo "═══════════════════════════════════════════"
echo ""

# ── Launch ────────────────────────────────────────────────────────────────
echo "🚀 Launching BlackBugsAI..."
exec python3 -u bot.py
