#!/bin/bash
# ══════════════════════════════════════════════════════════════════════════════
#  tunnel_admin.sh — Admin Panel Tunnel Manager
#
#  Запускает ADMIN туннель (не Cloudflare!) чтобы не конфликтовать с фишингом.
#
#  Использование:
#    bash tunnel_admin.sh            # авто-выбор лучшего
#    bash tunnel_admin.sh bore       # bore.pub (встроен в Docker)
#    bash tunnel_admin.sh ngrok      # ngrok (нужен NGROK_AUTHTOKEN)
#    bash tunnel_admin.sh serveo     # serveo.net (SSH, без аккаунта)
#    bash tunnel_admin.sh localhost  # localhost.run (SSH, без аккаунта)
#    bash tunnel_admin.sh tailscale  # Tailscale Funnel (VPN, самый надёжный)
# ══════════════════════════════════════════════════════════════════════════════

set -e
GREEN='\033[0;32m'; CYAN='\033[0;36m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; BOLD='\033[1m'; NC='\033[0m'
ADMIN_PORT="${ADMIN_WEB_PORT:-8080}"
TUNNEL_TYPE="${1:-auto}"

echo -e "${BOLD}⬛ BlackBugsAI — Admin Panel Tunnel${NC}"
echo -e "${YELLOW}ℹ️  Используем НЕ-Cloudflare туннель (CF занят фишингом)${NC}"
echo ""

# ── Проверить что admin panel запущена ────────────────────────────────────
if ! curl -sf "http://localhost:${ADMIN_PORT}/ping" >/dev/null 2>&1; then
    echo -e "${RED}❌ Admin Panel не отвечает на порту ${ADMIN_PORT}${NC}"
    echo "   Запусти сначала: docker compose up -d"
    exit 1
fi
echo -e "${GREEN}✅ Admin Panel запущена на порту ${ADMIN_PORT}${NC}"

# ── Авто-выбор ────────────────────────────────────────────────────────────
if [ "$TUNNEL_TYPE" = "auto" ]; then
    if command -v bore >/dev/null 2>&1; then
        TUNNEL_TYPE="bore"
    elif command -v tailscale >/dev/null 2>&1 && tailscale status >/dev/null 2>&1; then
        TUNNEL_TYPE="tailscale"
    elif command -v ngrok >/dev/null 2>&1 && [ -n "$NGROK_AUTHTOKEN" ]; then
        TUNNEL_TYPE="ngrok"
    elif command -v ssh >/dev/null 2>&1; then
        TUNNEL_TYPE="serveo"
    else
        TUNNEL_TYPE="bore"
    fi
    echo -e "  Авто-выбор: ${CYAN}${TUNNEL_TYPE}${NC}"
fi

echo ""

# ── Запуск туннеля ────────────────────────────────────────────────────────
case "$TUNNEL_TYPE" in

  bore)
    # bore — установлен в Docker образе, не Cloudflare, бесплатно
    if ! command -v bore >/dev/null 2>&1; then
        echo -e "${YELLOW}Устанавливаю bore...${NC}"
        BORE_VER=$(curl -fsSL https://api.github.com/repos/ekzhang/bore/releases/latest \
            | grep '"tag_name"' | sed 's/.*"v//;s/".*//' | head -1)
        curl -fsSL "https://github.com/ekzhang/bore/releases/download/v${BORE_VER}/bore-v${BORE_VER}-x86_64-unknown-linux-musl.tar.gz" \
            | tar -xz -C /usr/local/bin/
        chmod +x /usr/local/bin/bore
        echo -e "${GREEN}✅ bore установлен${NC}"
    fi
    echo -e "${CYAN}🌐 Запускаю bore туннель...${NC}"
    echo -e "${YELLOW}URL появится в формате: http://bore.pub:NNNNN${NC}"
    echo -e "${YELLOW}Нажми Ctrl+C для остановки${NC}"
    echo ""
    bore local "${ADMIN_PORT}" --to bore.pub
    ;;

  ngrok)
    if ! command -v ngrok >/dev/null 2>&1; then
        echo -e "${YELLOW}Устанавливаю ngrok...${NC}"
        curl -fsSL https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz | tar -xz -C /usr/local/bin/
    fi
    if [ -n "$NGROK_AUTHTOKEN" ]; then
        ngrok config add-authtoken "$NGROK_AUTHTOKEN"
    fi
    echo -e "${CYAN}🌐 Запускаю ngrok туннель...${NC}"
    echo -e "${YELLOW}Dashboard: http://localhost:4040${NC}"
    echo -e "${YELLOW}Нажми Ctrl+C для остановки${NC}"
    echo ""
    ngrok http "${ADMIN_PORT}" --log=stdout &
    NGROK_PID=$!
    sleep 3
    # Получаем URL из API
    NGROK_URL=$(curl -sf http://localhost:4040/api/tunnels 2>/dev/null \
        | python3 -c "import sys,json; t=json.load(sys.stdin)['tunnels']; print(next((x['public_url'] for x in t if 'https' in x['public_url']), t[0]['public_url'] if t else ''))" 2>/dev/null || echo "")
    echo ""
    echo -e "${GREEN}══════════════════════════════════════════${NC}"
    echo -e "${BOLD}  ✅ Admin Panel доступна:${NC}"
    echo -e "  ${CYAN}${NGROK_URL}/panel${NC}"
    echo -e "${GREEN}══════════════════════════════════════════${NC}"
    wait $NGROK_PID
    ;;

  serveo)
    # serveo.net — SSH туннель, не нужен аккаунт
    echo -e "${CYAN}🌐 Запускаю serveo.net туннель (SSH)...${NC}"
    echo -e "${YELLOW}URL появится как: https://XXXX.serveo.net${NC}"
    echo -e "${YELLOW}Нажми Ctrl+C для остановки${NC}"
    echo ""
    ssh -o StrictHostKeyChecking=no \
        -o ServerAliveInterval=30 \
        -o ExitOnForwardFailure=yes \
        -R "80:localhost:${ADMIN_PORT}" \
        serveo.net
    ;;

  localhost|localhostrun)
    # localhost.run — SSH туннель, не нужен аккаунт
    echo -e "${CYAN}🌐 Запускаю localhost.run туннель (SSH)...${NC}"
    echo -e "${YELLOW}URL появится как: https://XXXX.lhr.life${NC}"
    echo -e "${YELLOW}Нажми Ctrl+C для остановки${NC}"
    echo ""
    ssh -o StrictHostKeyChecking=no \
        -o ServerAliveInterval=30 \
        -R "80:localhost:${ADMIN_PORT}" \
        nokey@localhost.run
    ;;

  tailscale)
    # Tailscale Funnel — VPN mesh, самый безопасный
    if ! command -v tailscale >/dev/null 2>&1; then
        echo -e "${YELLOW}Устанавливаю Tailscale...${NC}"
        curl -fsSL https://tailscale.com/install.sh | sh
    fi
    if ! tailscale status >/dev/null 2>&1; then
        echo -e "${RED}❌ Tailscale не авторизован.${NC}"
        echo "   Запусти: tailscale up"
        echo "   Потом:   tailscale funnel ${ADMIN_PORT}"
        exit 1
    fi
    echo -e "${CYAN}🌐 Запускаю Tailscale Funnel...${NC}"
    tailscale funnel "${ADMIN_PORT}"
    TS_URL=$(tailscale funnel status 2>/dev/null | grep -oP 'https://[\w\-\.]+\.ts\.net' | head -1)
    if [ -n "$TS_URL" ]; then
        echo ""
        echo -e "${GREEN}══════════════════════════════════════════${NC}"
        echo -e "${BOLD}  ✅ Admin Panel (Tailscale):${NC}"
        echo -e "  ${CYAN}${TS_URL}/panel${NC}"
        echo -e "${GREEN}══════════════════════════════════════════${NC}"
    fi
    ;;

  docker-bore)
    echo -e "${CYAN}🐳 Запускаю bore через Docker Compose...${NC}"
    docker compose --profile admin-bore up -d bore-admin
    sleep 5
    echo -e "${YELLOW}URL в логах:${NC}"
    docker compose logs bore-admin | grep -i "bore.pub" | tail -5
    ;;

  docker-ngrok)
    echo -e "${CYAN}🐳 Запускаю ngrok через Docker Compose...${NC}"
    docker compose --profile admin-ngrok up -d ngrok-admin
    sleep 4
    NGROK_URL=$(curl -sf http://localhost:4040/api/tunnels 2>/dev/null \
        | python3 -c "import sys,json; t=json.load(sys.stdin).get('tunnels',[]); print(t[0]['public_url'] if t else '')" 2>/dev/null || echo "")
    echo -e "${GREEN}URL: ${NGROK_URL}/panel${NC}"
    ;;

  *)
    echo -e "${RED}Неизвестный тип туннеля: ${TUNNEL_TYPE}${NC}"
    echo ""
    echo "Доступные варианты:"
    echo "  bore        — bore.pub (встроен в Docker, не Cloudflare)"
    echo "  ngrok       — ngrok.com (нужен NGROK_AUTHTOKEN)"
    echo "  serveo      — serveo.net (SSH, без аккаунта)"
    echo "  localhost   — localhost.run (SSH, без аккаунта)"
    echo "  tailscale   — Tailscale Funnel (VPN, самый надёжный)"
    echo "  docker-bore — bore через docker compose"
    echo "  docker-ngrok — ngrok через docker compose"
    exit 1
    ;;
esac
