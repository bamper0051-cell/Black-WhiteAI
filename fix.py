#!/bin/bash
set -e

echo "🔧 Применяю исправления для BlackBugsAI..."

# 1. Патчим bot.py
cat >> bot.py << 'EOF'

# ---- PATCH: Remote Control functions via module ----
try:
    import remote_control as rc
    RC_ENABLED = True
except ImportError:
    RC_ENABLED = False

# ---- PATCH: MATRIX warmup in main ----
# (этот блок нужно вставить в функцию main(), но мы не можем вставить в середину
#  через cat, поэтому лучше вручную добавить вызов matrix_warmup)
EOF

# 2. Добавляем вызов warmup в main (вручную)
echo "⚠️ Вставьте в bot.py в функцию main() перед poll():"
echo "    try:"
echo "        from agent_matrix import warmup as matrix_warmup"
echo "        matrix_warmup(on_status=lambda m: print(f'  MATRIX: {m}'))"
echo "    except: pass"

# 3. Обновляем Dockerfile
cat >> Dockerfile << 'EOF'

# WebSocket support
RUN pip install flask-socketio eventlet

# Docker CLI for remote control
RUN apt-get update && apt-get install -y docker.io && rm -rf /var/lib/apt/lists/*
EOF

# 4. Пересборка контейнера
echo "✅ Готово. Запустите:"
echo "   docker compose build"
echo "   docker compose up -d"
echo "   docker compose logs -f"
