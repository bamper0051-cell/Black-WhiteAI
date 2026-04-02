#!/bin/bash
# ============================================================
# BlackBugsAI — Quick Docker Run
# Быстрый запуск без установки (только Docker нужен)
# ============================================================

CYAN='\033[0;36m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'

echo -e "${CYAN}BlackBugsAI — Quick Start via Docker${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker не установлен!${NC}"
    echo "Установи: curl -fsSL https://get.docker.com | sh"
    exit 1
fi

# Setup .env
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo -e "${YELLOW}Создаю .env из примера...${NC}"
    cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
    echo ""
    echo -e "${YELLOW}⚠️  ОБЯЗАТЕЛЬНО заполни .env перед запуском:${NC}"
    echo "   nano $PROJECT_DIR/.env"
    echo ""
    echo -e "Минимум нужно:"
    echo "  BOT_TOKEN=     (Telegram Bot Token от @BotFather)"
    echo "  ADMIN_IDS=     (Твой Telegram ID)"
    echo "  OPENAI_API_KEY= ИЛИ GROQ_API_KEY= ИЛИ другой LLM ключ"
    echo ""
    read -p "Открыть .env сейчас? [y/N]: " open_env
    if [ "$open_env" = "y" ]; then
        ${EDITOR:-nano} "$PROJECT_DIR/.env"
    fi
fi

cd "$PROJECT_DIR"

# Build
echo -e "\n${YELLOW}Собираем Docker образ...${NC}"
docker build -t blackbugsai:latest . 2>&1 | grep -E "Step|Successfully|Error" | head -20

# Generate admin token if not set
ADMIN_TOKEN=$(grep "^ADMIN_TOKEN=" .env | cut -d= -f2)
if [ -z "$ADMIN_TOKEN" ] || [ "$ADMIN_TOKEN" = "change_me_to_a_long_random_string" ]; then
    ADMIN_TOKEN=$(openssl rand -hex 24 2>/dev/null || cat /proc/sys/kernel/random/uuid | tr -d '-')
    sed -i "s/^ADMIN_TOKEN=.*/ADMIN_TOKEN=$ADMIN_TOKEN/" .env
    echo -e "${GREEN}Сгенерирован ADMIN_TOKEN: $ADMIN_TOKEN${NC}"
fi

# Stop existing
docker stop blackbugsai 2>/dev/null || true
docker rm blackbugsai 2>/dev/null || true

# Run
echo -e "\n${YELLOW}Запускаем контейнер...${NC}"
docker run -d \
    --name blackbugsai \
    --restart unless-stopped \
    -p 8080:8080 \
    -p 5000:5000 \
    --env-file .env \
    -v "$PROJECT_DIR/data:/app/data" \
    -v "$PROJECT_DIR/logs:/app/logs" \
    blackbugsai:latest

sleep 3

# Check status
if docker ps | grep -q blackbugsai; then
    SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}✅ BlackBugsAI запущен!${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  🌐 Admin Panel: ${CYAN}http://localhost:8080${NC}"
    echo -e "  🌐 External:    ${CYAN}http://$SERVER_IP:8080${NC}"
    echo -e "  🔑 Token:       ${CYAN}$ADMIN_TOKEN${NC}"
    echo ""
    echo -e "  📱 Для Android App:"
    echo -e "     URL:   http://$SERVER_IP:8080"
    echo -e "     Token: $ADMIN_TOKEN"
    echo ""
    echo -e "  📋 Команды:"
    echo "    Логи:   docker logs -f blackbugsai"
    echo "    Стоп:   docker stop blackbugsai"
    echo "    Рестарт: docker restart blackbugsai"
else
    echo -e "${RED}Ошибка запуска!${NC}"
    docker logs blackbugsai --tail=20
fi
