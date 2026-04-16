#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# BlackBugsAI — Entrypoint v3.1
# Telegram token compatibility + stable boot
# ═══════════════════════════════════════════════════════════════════════════

set -euo pipefail

cat << 'BANNER'
╔══════════════════════════════════════════════════════╗
║  🖤🐛  BlackBugsAI v3.1 — Autonomous Agent Platform  ║
╚══════════════════════════════════════════════════════╝
BANNER

echo "⏰ Started: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "🐍 Python: $(python3 --version)"

cd /app

# Backward compatibility for older env files
if [[ -z "${TELEGRAM_BOT_TOKEN:-}" && -n "${BOT_TOKEN:-}" ]]; then
  export TELEGRAM_BOT_TOKEN="$BOT_TOKEN"
  echo "ℹ️ Using BOT_TOKEN as TELEGRAM_BOT_TOKEN (compat mode)"
fi

[[ -z "${TELEGRAM_BOT_TOKEN:-}" ]] && echo "⚠️ TELEGRAM_BOT_TOKEN/BOT_TOKEN not set"
[[ -z "${ADMIN_WEB_TOKEN:-}" ]] && echo "⚠️ ADMIN_WEB_TOKEN not set"

export FISH_TUNNEL_DISABLED="${FISH_TUNNEL_DISABLED:-true}"
export FISH_SERVER_PORT="${FISH_SERVER_PORT:-5100}"

mkdir -p /app/fish_uploads /app/fish_pages /app/fish_logs \
         /app/agent_projects /app/created_bots /app/artifacts /app/logs

for db in auth.db automuvie.db sessions.db tasks.db; do
  [ -d "/app/$db" ] && rmdir "/app/$db" 2>/dev/null || true
  [ -f "/app/$db" ] || touch "/app/$db"
done

cleanup() {
  echo "⏹ BlackBugsAI shutting down..."
  exit 0
}
trap cleanup SIGTERM SIGINT SIGQUIT

if [ $# -gt 0 ]; then
  echo "🚀 Launching custom command: $*"
  exec "$@"
fi

echo "🚀 Launching Telegram bot (bot_main.py)..."
exec python3 -u bot_main.py
