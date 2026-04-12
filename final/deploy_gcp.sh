#!/bin/bash
# ══════════════════════════════════════════════════════════════════════════
#  deploy_gcp.sh — BlackBugsAI v4 — One-command GCP / VPS Deploy
#  Запуск: bash deploy_gcp.sh
#  Требования: Docker + Docker Compose (ставит если нет)
# ══════════════════════════════════════════════════════════════════════════
set -e

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

info()    { echo -e "${CYAN}[INFO]${NC} $*"; }
success() { echo -e "${GREEN}[OK]${NC}   $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
error()   { echo -e "${RED}[ERR]${NC}  $*"; exit 1; }

echo -e "${BOLD}"
echo "  ██████╗ ██╗      █████╗  ██████╗██╗  ██╗██████╗ ██╗   ██╗ ██████╗ ███████╗"
echo "  ██╔══██╗██║     ██╔══██╗██╔════╝██║ ██╔╝██╔══██╗██║   ██║██╔════╝ ██╔════╝"
echo "  ██████╔╝██║     ███████║██║     █████╔╝ ██████╔╝██║   ██║██║  ███╗███████╗"
echo "  ██╔══██╗██║     ██╔══██║██║     ██╔═██╗ ██╔══██╗██║   ██║██║   ██║╚════██║"
echo "  ██████╔╝███████╗██║  ██║╚██████╗██║  ██╗██████╔╝╚██████╔╝╚██████╔╝███████║"
echo "  ╚═════╝ ╚══════╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝╚═════╝  ╚═════╝  ╚═════╝ ╚══════╝"
echo -e "  AI Platform v4.0 — GCP Deploy Script${NC}"
echo ""

# ── Check root ───────────────────────────────────────────────────────────
if [ "$EUID" -ne 0 ]; then
  warn "Не root — некоторые команды могут потребовать sudo"
fi

# ── Install Docker ───────────────────────────────────────────────────────
if ! command -v docker &>/dev/null; then
  info "Устанавливаю Docker..."
  curl -fsSL https://get.docker.com | sh
  systemctl enable docker
  systemctl start docker
  success "Docker установлен"
else
  success "Docker уже установлен: $(docker --version)"
fi

# ── Install Docker Compose v2 ────────────────────────────────────────────
if ! docker compose version &>/dev/null 2>&1; then
  info "Устанавливаю Docker Compose v2..."
  COMPOSE_VER=$(curl -fsSL https://api.github.com/repos/docker/compose/releases/latest \
    | grep '"tag_name"' | sed 's/.*"v\([^"]*\)".*/\1/')
  curl -fsSL "https://github.com/docker/compose/releases/download/v${COMPOSE_VER}/docker-compose-linux-x86_64" \
    -o /usr/local/bin/docker-compose
  chmod +x /usr/local/bin/docker-compose
  mkdir -p ~/.docker/cli-plugins
  ln -sf /usr/local/bin/docker-compose ~/.docker/cli-plugins/docker-compose
  success "Docker Compose $COMPOSE_VER установлен"
else
  success "Docker Compose: $(docker compose version)"
fi

# ── Check .env ───────────────────────────────────────────────────────────
if [ ! -f ".env" ]; then
  if [ -f ".env.example" ]; then
    cp .env.example .env
    warn ".env создан из .env.example — ОБЯЗАТЕЛЬНО настрой переменные!"
    warn "nano .env  ← добавь BOT_TOKEN, ADMIN_WEB_TOKEN, API ключи"
  else
    error ".env не найден и .env.example отсутствует!"
  fi
fi

# Auto-generate ADMIN_WEB_TOKEN if default
if grep -q "changeme_secret_token" .env 2>/dev/null; then
  NEW_TOKEN=$(python3 -c "import secrets; print(secrets.token_hex(24))" 2>/dev/null || \
              cat /dev/urandom | tr -dc 'a-zA-Z0-9' | head -c 48)
  sed -i "s/changeme_secret_token/${NEW_TOKEN}/" .env
  success "Сгенерирован новый ADMIN_WEB_TOKEN: ${NEW_TOKEN:0:8}..."
  echo -e "${YELLOW}  Сохрани токен: ${BOLD}${NEW_TOKEN}${NC}"
fi

# ── Create directories ───────────────────────────────────────────────────
info "Создаю директории..."
mkdir -p data tools repos sandbox artifacts matrix_workspace \
         neo_workspace agent_projects created_bots output \
         fish_uploads fish_pages fish_logs
success "Директории готовы"

# ── Build ────────────────────────────────────────────────────────────────
info "Собираю Docker образ..."
docker compose build --no-cache
success "Образ собран"

# ── Stop old ─────────────────────────────────────────────────────────────
info "Останавливаю старые контейнеры..."
docker compose down --remove-orphans 2>/dev/null || true

# ── Start ────────────────────────────────────────────────────────────────
info "Запускаю BlackBugsAI..."
docker compose up -d
sleep 5

# ── Health check ─────────────────────────────────────────────────────────
info "Проверяю состояние..."
for i in $(seq 1 12); do
  if curl -sf http://localhost:8080/ping >/dev/null 2>&1; then
    success "Admin Panel отвечает!"
    break
  fi
  if [ $i -eq 12 ]; then
    warn "Admin Panel не ответил за 60с — проверь логи: docker compose logs bot"
  fi
  sleep 5
done

# ── Get Admin Tunnel URL (bore) ──────────────────────────────────────────
info "Ожидаю bore Admin Tunnel URL..."
sleep 8
BORE_URL=$(docker compose logs bore-admin 2>/dev/null | grep -oP 'bore\.pub:\d+' | tail -1)
if [ -n "$BORE_URL" ]; then BORE_URL="http://${BORE_URL}"; fi
CF_URL=$(docker compose logs cloudflare-fish 2>/dev/null | grep -oP 'https://[a-z0-9-]+\.trycloudflare\.com' | tail -1)

# ── Get external IP ──────────────────────────────────────────────────────
EXT_IP=$(curl -sf https://api.ipify.org 2>/dev/null || curl -sf https://ifconfig.me 2>/dev/null || echo "unknown")
ADMIN_TOKEN=$(grep ADMIN_WEB_TOKEN .env | cut -d= -f2 | tr -d '"' | head -1)

# ── Summary ──────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}  ✅ BlackBugsAI v4.0 запущен!${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${CYAN}🌐 Локальный доступ:${NC}"
echo -e "     http://localhost:8080/panel"
echo ""
echo -e "  ${CYAN}🌍 VPS / GCP доступ:${NC}"
echo -e "     http://${EXT_IP}:8080/panel"
echo ""
if [ -n "$BORE_URL" ]; then
  echo -e "  ${CYAN}🌐 Admin Tunnel (bore — не CF):${NC}"
  echo -e "     ${BOLD}${BORE_URL}/panel${NC}"
  echo -e "     ${YELLOW}Server URL: ${BORE_URL}${NC}"
  echo ""
fi
if [ -n "$CF_URL" ]; then
  echo -e "  ${CYAN}🎣 Fish Tunnel (Cloudflare):${NC}"
  echo -e "     ${CF_URL}"
  echo ""
fi
echo -e "  ${CYAN}🔑 Admin Token:${NC}"
echo -e "     ${BOLD}${ADMIN_TOKEN:0:8}...${NC}  (полный в .env)"
echo ""
echo -e "  ${CYAN}📋 Полезные команды:${NC}"
echo -e "     docker compose logs -f bot          # логи бота"
echo -e "     docker compose logs cloudflare       # Cloudflare URL"
echo -e "     docker compose restart bot           # перезапуск"
echo -e "     docker compose down                  # остановка"
echo ""
echo -e "  ${YELLOW}⚠️  Для GCP — открой порт 8080 в Firewall:${NC}"
echo -e "     gcloud compute firewall-rules create allow-8080 \\"
echo -e "       --allow tcp:8080 --source-ranges 0.0.0.0/0"
echo ""
echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
