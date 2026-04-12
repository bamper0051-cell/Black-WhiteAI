#!/bin/sh
set -e

echo "🔧 Entrypoint: подготовка..."

# Папки
mkdir -p /app/fish_uploads /app/fish_pages /app/fish_logs \
         /app/agent_projects /app/created_bots /app/artifacts

# БД которые монтируются с хоста — проверяем что это файлы, не папки
for db in auth.db automuvie.db; do
    if [ -d "/app/$db" ]; then
        echo "⚠️ /app/$db — это папка вместо файла! Удаляю..."
        rmdir "/app/$db" 2>/dev/null || true
    fi
    [ -f "/app/$db" ] || touch "/app/$db"
done

# БД внутри контейнера — просто создаём если нет
for db in sessions.db tasks.db; do
    [ -f "/app/$db" ] || touch "/app/$db"
    echo "  ✅ /app/$db готов"
done

echo "✅ Entrypoint готово"
exec python bot.py
