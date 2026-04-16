#!/bin/bash
# ============================================================
# BlackBugsAI — GCP VM / Ubuntu Server Setup Script
# Поддерживает: Ubuntu 20.04+, Debian 11+, GCP VM
# Запуск: curl -fsSL https://raw.githubusercontent.com/bamper0051-cell/Black-WhiteAI/main/deploy/gcp_vm_setup.sh | bash
# ============================================================

set -e

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

print_header() {
    echo -e "${CYAN}"
    cat << 'LOGO'
██████╗ ██╗      █████╗  ██████╗██╗  ██╗    ██╗    ██╗██╗  ██╗██╗████████╗███████╗ █████╗ ██╗
██╔══██╗██║     ██╔══██╗██╔════╝██║ ██╔╝    ██║    ██║██║  ██║██║╚══██╔══╝██╔════╝██╔══██╗██║
██████╔╝██║     ███████║██║     █████╔╝     ██║ █╗ ██║███████║██║   ██║   █████╗  ███████║██║
██╔══██╗██║     ██╔══██║██║     ██╔═██╗     ██║███╗██║██╔══██║██║   ██║   ██╔══╝  ██╔══██║██║
██████╔╝███████╗██║  ██║╚██████╗██║  ██╗    ╚███╔███╔╝██║  ██║██║   ██║   ███████╗██║  ██║██║
╚═════╝ ╚══════╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝     ╚══╝╚══╝ ╚═╝  ╚═╝╚═╝   ╚═╝   ╚══════╝╚═╝  ╚═╝
LOGO
    echo -e "${NC}"
    echo -e "${GREEN}${BOLD}GCP VM / Ubuntu Server Setup${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

log()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
fail() { echo -e "${RED}[✗]${NC} $1"; exit 1; }
step() { echo -e "\n${CYAN}${BOLD}[$1] $2${NC}"; }

print_header

INSTALL_DIR="/opt/blackbugsai"
SERVICE_USER="blackbugsai"

# ── Root check ────────────────────────────────────────────────────────────────
if [ "$EUID" -ne 0 ]; then
    fail "Запусти скрипт с root правами: sudo bash gcp_vm_setup.sh"
fi

OS=$(grep -oP '(?<=^ID=).+' /etc/os-release | tr -d '"')
log "OS: $OS"

# ── 1. System update ──────────────────────────────────────────────────────────
step "1/9" "Обновляем систему"
apt-get update -qq
apt-get upgrade -y -qq
apt-get install -y -qq \
    git curl wget unzip \
    python3 python3-pip python3-venv \
    ffmpeg \
    libpng-dev libjpeg-dev \
    nmap whois dnsutils \
    jq htop net-tools \
    nginx certbot python3-certbot-nginx
log "Системные пакеты установлены"

# ── 2. Docker ─────────────────────────────────────────────────────────────────
step "2/9" "Устанавливаем Docker"
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
    log "Docker установлен"
else
    log "Docker уже установлен: $(docker --version)"
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null 2>&1; then
    apt-get install -y docker-compose-plugin || \
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
         -o /usr/local/bin/docker-compose && chmod +x /usr/local/bin/docker-compose
fi
log "Docker Compose готов"

# ── 3. Service user ───────────────────────────────────────────────────────────
step "3/9" "Создаём системного пользователя"
if ! id "$SERVICE_USER" &>/dev/null; then
    useradd -r -m -s /bin/bash -d "$INSTALL_DIR" "$SERVICE_USER"
    usermod -aG docker "$SERVICE_USER"
    log "Пользователь $SERVICE_USER создан"
else
    log "Пользователь $SERVICE_USER уже существует"
fi

# ── 4. Clone repo ─────────────────────────────────────────────────────────────
step "4/9" "Клонируем репозиторий"
if [ ! -d "$INSTALL_DIR/.git" ]; then
    mkdir -p "$INSTALL_DIR"
    git clone https://github.com/bamper0051-cell/Black-WhiteAI.git "$INSTALL_DIR"
    chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"
    log "Репозиторий склонирован в $INSTALL_DIR"
else
    cd "$INSTALL_DIR" && git pull origin main
    log "Репозиторий обновлён"
fi

# ── 5. Environment config ─────────────────────────────────────────────────────
step "5/9" "Создаём конфигурацию"
if [ ! -f "$INSTALL_DIR/.env" ]; then
    cp "$INSTALL_DIR/.env.example" "$INSTALL_DIR/.env"

    # Generate random tokens
    ADMIN_TOKEN=$(openssl rand -hex 32)
    JWT_SECRET=$(openssl rand -hex 32)

    sed -i "s/ADMIN_TOKEN=change_me_to_a_long_random_string/ADMIN_TOKEN=$ADMIN_TOKEN/" "$INSTALL_DIR/.env"
    sed -i "s/JWT_SECRET=change_me_to_another_long_random_string/JWT_SECRET=$JWT_SECRET/" "$INSTALL_DIR/.env"

    echo ""
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}⚠️  СОХРАНИ ЭТИ ДАННЫЕ!${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "ADMIN_TOKEN = ${GREEN}$ADMIN_TOKEN${NC}"
    echo -e "JWT_SECRET  = ${GREEN}$JWT_SECRET${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    warn "Добавь API ключи в $INSTALL_DIR/.env"
    warn "Минимум один LLM провайдер: OPENAI_API_KEY, GROQ_API_KEY, и т.д."
fi

# ── 6. Docker build ───────────────────────────────────────────────────────────
step "6/9" "Собираем Docker образ"
cd "$INSTALL_DIR"
docker build -t blackbugsai:latest . 2>&1 | tail -5
log "Docker образ собран"

# ── 7. Systemd service ────────────────────────────────────────────────────────
step "7/9" "Создаём systemd сервис"
cat > /etc/systemd/system/blackbugsai.service << EOF
[Unit]
Description=BlackBugsAI Multi-Agent Platform
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
User=root
WorkingDirectory=$INSTALL_DIR
ExecStartPre=/usr/bin/docker compose down --remove-orphans
ExecStart=/usr/bin/docker compose up
ExecStop=/usr/bin/docker compose down
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable blackbugsai
log "Systemd сервис создан: blackbugsai"

# ── 8. Nginx reverse proxy ────────────────────────────────────────────────────
step "8/9" "Настраиваем Nginx (panel + api + websocket)"
SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')

cat > /etc/nginx/sites-available/blackbugsai << EOF
server {
    listen 80;
    server_name $SERVER_IP _;

    # Admin Panel
    location /panel {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }

    # API
    location /api {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # WebSocket for realtime panel
    location /socket.io/ {
        proxy_pass http://127.0.0.1:8080/socket.io/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }

    # Default — redirect to panel
    location / {
        return 301 /panel;
    }
}
EOF

ln -sf /etc/nginx/sites-available/blackbugsai /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
log "Nginx настроен"

# ── 9. Firewall ───────────────────────────────────────────────────────────────
step "9/9" "Настраиваем firewall"
if command -v ufw &> /dev/null; then
    ufw --force enable
    ufw allow ssh
    ufw allow 80/tcp
    ufw allow 8080/tcp
    log "UFW firewall настроен"
fi

# ── Start service ─────────────────────────────────────────────────────────────
echo ""
echo -e "${YELLOW}Запускаем BlackBugsAI...${NC}"
systemctl start blackbugsai
sleep 5
systemctl status blackbugsai --no-pager | head -10

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}${BOLD}✅ BlackBugsAI успешно установлен!${NC}"
echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  📁 Директория:    ${CYAN}$INSTALL_DIR${NC}"
echo -e "  🌐 Admin Panel:   ${CYAN}http://$SERVER_IP:8080${NC}"
echo -e "  🌐 Через Nginx:   ${CYAN}http://$SERVER_IP/panel${NC}"
echo ""
echo -e "  📋 Команды:"
echo -e "    Статус:   ${YELLOW}systemctl status blackbugsai${NC}"
echo -e "    Логи:     ${YELLOW}journalctl -u blackbugsai -f${NC}"
echo -e "    Стоп:     ${YELLOW}systemctl stop blackbugsai${NC}"
echo -e "    Конфиг:   ${YELLOW}nano $INSTALL_DIR/.env${NC}"
echo ""
echo -e "  📱 Android App:"
echo -e "    URL:      ${CYAN}http://$SERVER_IP:8080${NC}"
echo -e "    Token:    ${CYAN}$(grep ADMIN_TOKEN $INSTALL_DIR/.env | cut -d= -f2)${NC}"
echo ""
