#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# BlackBugsAI — Entrypoint v3.1
# FIX: Tunnel запускается ТОЛЬКО после того как admin web ответит на /health
# FIX: Fish module на порту 5100, туннель → nginx:80
# FIX: Merge-конфликт убран
# ═══════════════════════════════════════════════════════════════════════════

set -euo pipefail

cat << 'EOF'
╔══════════════════════════════════════════════════════╗
║  🖤🐛  BlackBugsAI v3.1 — Autonomous Agent Platform  ║
║  Matrix · Neo · Pythia · Anderson · Alliance v2      ║
╚══════════════════════════════════════════════════════╝
EOF
echo "⏰ Started: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "🐍 Python: $(python3 --version)"
echo "📦 Platform: $(uname -m)"

cd /app

# ── Init directories ──────────────────────────────────────────────────────
mkdir -p /app/data /app/fish_uploads /app/fish_pages /app/fish_logs \
         /app/agent_projects /app/created_bots /app/artifacts \
         /app/neo_workspace /app/matrix_workspace /app/logs

# Создаём пустые БД-файлы если их нет (предотвращаем создание директорий вместо файлов)
for db in auth.db tasks.db; do
    [ -d "/app/data/$db" ] && rmdir "/app/data/$db" 2>/dev/null || true
    [ -f "/app/data/$db" ] || touch "/app/data/$db"
done

# ── Validate required env ─────────────────────────────────────────────────
[[ -z "${TELEGRAM_BOT_TOKEN:-}" ]] && echo "⚠️  TELEGRAM_BOT_TOKEN not set"
[[ -z "${ADMIN_WEB_TOKEN:-}" ]]    && echo "⚠️  ADMIN_WEB_TOKEN not set — using default (INSECURE!)"

# ── Fish tunnel isolation fix ─────────────────────────────────────────────
export FISH_TUNNEL_DISABLED="${FISH_TUNNEL_DISABLED:-true}"
export FISH_SERVER_PORT="${FISH_SERVER_PORT:-5100}"
echo "🎣 Fish module port: $FISH_SERVER_PORT (tunnel disabled: $FISH_TUNNEL_DISABLED)"

# ── Apply admin panel v4 ──────────────────────────────────────────────────
if [[ -f "admin_panel_v4.html" ]]; then
  cp -f admin_panel_v4.html admin_panel.html
  echo "✅ Admin Panel v4 applied"
fi

# ── Install critical deps if missing ─────────────────────────────────────
check_and_install() {
  python3 -c "import $1" 2>/dev/null || {
    echo "  Installing: $2..."
    pip install -q "$2" --break-system-packages 2>/dev/null || true
  }
}
check_and_install flask_socketio  "flask-socketio==5.3.6"
check_and_install psutil          "psutil"
check_and_install eventlet        "eventlet"

# ── Tunnel manager ────────────────────────────────────────────────────────
_TUNNEL_PID=""

wait_for_health() {
  # Ждём пока admin web ответит на /health — максимум 60 секунд
  local port="${ADMIN_WEB_PORT:-8080}"
  local attempts=0
  echo "⏳ Waiting for admin web on port $port to be ready..."
  while ! curl -sf "http://localhost:${port}/health" > /dev/null 2>&1; do
    attempts=$((attempts + 1))
    if [[ $attempts -ge 30 ]]; then
      echo "⚠️  Health check timeout after 60s — starting tunnel anyway"
      return
    fi
    sleep 2
  done
  echo "✅ Admin web is healthy (${attempts}x2s elapsed)"
}

start_tunnel() {
  local provider="${TUNNEL_PROVIDER:-cloudflared}"
  local port="${TUNNEL_TARGET_PORT:-80}"

  echo "🌐 Starting tunnel: $provider → localhost:$port"

  case "$provider" in
    cloudflared)
      if command -v cloudflared &>/dev/null; then
        cloudflared tunnel --url "http://localhost:${port}" \
          --no-autoupdate \
          --logfile /tmp/cloudflared.log \
          2>&1 | while IFS= read -r line; do
            if echo "$line" | grep -qE 'trycloudflare\.com|cfargotunnel\.com'; then
              URL=$(echo "$line" | grep -oE 'https://[^\s]+\.(trycloudflare|cfargotunnel)\.com' | head -1)
              if [[ -n "$URL" ]]; then
                echo "$URL" > /tmp/tunnel_url.txt
                echo "🌐 Tunnel URL: $URL"
              fi
            fi
          done &
        _TUNNEL_PID=$!
      else
        echo "⚠️  cloudflared not found — install via: curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb && dpkg -i cloudflared.deb"
      fi
      ;;
    bore)
      local server="${BORE_SERVER:-bore.pub}"
      if command -v bore &>/dev/null; then
        bore local "${port}" --to "${server}" 2>&1 | tee /tmp/bore.log &
        _TUNNEL_PID=$!
        sleep 3
        BORE_URL=$(grep -oE 'bore\.pub:[0-9]+' /tmp/bore.log 2>/dev/null | head -1)
        [[ -n "$BORE_URL" ]] && echo "http://$BORE_URL" > /tmp/tunnel_url.txt && echo "🌐 Bore URL: http://$BORE_URL"
      else
        echo "⚠️  bore not found"
      fi
      ;;
    none|"")
      echo "ℹ️  Auto-tunnel disabled (set AUTO_TUNNEL=true to enable)"
      ;;
  esac
}

# Запускаем туннель только ПОСЛЕ того как сервис стал healthy
if [[ "${AUTO_TUNNEL:-false}" == "true" ]]; then
  (wait_for_health && start_tunnel) &
  echo "⏳ Tunnel will start after health check passes..."
fi

# ── Graceful shutdown ─────────────────────────────────────────────────────
cleanup() {
  echo ""
  echo "⏹  BlackBugsAI shutting down..."
  [[ -n "$_TUNNEL_PID" ]] && kill "$_TUNNEL_PID" 2>/dev/null || true
  echo "👋 Bye!"
  exit 0
}
trap cleanup SIGTERM SIGINT SIGQUIT

# ── Status ────────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════"
echo "  Admin Panel : http://localhost:${ADMIN_WEB_PORT:-8080}"
echo "  Fish Module : http://localhost:${FISH_SERVER_PORT:-5100} (internal)"
echo "  Tunnel      : AUTO_TUNNEL=${AUTO_TUNNEL:-false} (${TUNNEL_PROVIDER:-cloudflared})"
echo "  Brand       : ${BRAND_NAME:-BlackBugsAI}"
echo "═══════════════════════════════════════════════════"
echo ""

# ── Launch ────────────────────────────────────────────────────────────────
echo "🚀 Launching BlackBugsAI..."
if [ $# -gt 0 ]; then
    exec "$@"
else
    exec python3 -u bot.py
fi
