#!/bin/bash
echo "=========================================="
echo " АВТОМУВИ — первоначальная настройка"
echo "=========================================="

touch auth.db automuvie.db sessions.db tasks.db
mkdir -p fish_uploads fish_pages fish_logs agent_projects created_bots artifacts data

echo "✅ Файлы созданы"
echo ""
echo "Далее:"
echo "  1. cp .env.example .env && nano .env"
echo "  2. docker compose up -d"
echo "  3. Открой http://localhost:8080/panel"
