#!/bin/sh
set -e
echo "🔧 Entrypoint..."
mkdir -p /app/fish_uploads /app/fish_pages /app/fish_logs \
         /app/agent_projects /app/created_bots /app/artifacts \
         /app/logs /app/data
for db in auth.db automuvie.db sessions.db tasks.db; do
    [ -d "/app/$db" ] && rmdir "/app/$db" 2>/dev/null || true
    [ -f "/app/$db" ] || touch "/app/$db"
done

# Support BOT_TOKEN as alias for TELEGRAM_BOT_TOKEN
if [ -n "$BOT_TOKEN" ] && [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    export TELEGRAM_BOT_TOKEN="$BOT_TOKEN"
fi
if [ -n "$TELEGRAM_BOT_TOKEN" ] && [ -z "$BOT_TOKEN" ]; then
    export BOT_TOKEN="$TELEGRAM_BOT_TOKEN"
fi

echo "✅ Ready"
exec python bot.py
