#!/bin/sh
set -e
echo "🔧 Entrypoint..."
mkdir -p /app/fish_uploads /app/fish_pages /app/fish_logs \
         /app/agent_projects /app/created_bots /app/artifacts
for db in auth.db automuvie.db sessions.db tasks.db; do
    [ -d "/app/$db" ] && rmdir "/app/$db" 2>/dev/null || true
    [ -f "/app/$db" ] || touch "/app/$db"
done
echo "✅ Ready"
if [ $# -gt 0 ]; then
    exec "$@"
else
    exec python bot.py
fi
