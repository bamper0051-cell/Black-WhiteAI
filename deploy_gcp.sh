#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
#  🖤🐛  BlackBugsAI — Google Cloud Platform Deploy Script v3.0
#
#  Что делает:
#   1. Создаёт GCP VM (e2-standard-2, Debian 12)
#   2. Устанавливает Docker + Docker Compose
#   3. Настраивает root SSH с паролем
#   4. Деплоит BlackBugsAI через Docker Compose v3
#   5. Автозапускает cloudflared туннель
#   6. Выводит URL для доступа из любой точки мира
#
#  Требования:
#   - gcloud CLI: https://cloud.google.com/sdk/docs/install
#   - Проект GCP: gcloud config set project YOUR_PROJECT
#
#  Запуск:
#   chmod +x deploy_gcp.sh && ./deploy_gcp.sh
# ═══════════════════════════════════════════════════════════════════════════

set -euo pipefail

# ── CONFIG — измени под себя ──────────────────────────────────────────────
GCP_PROJECT="${GCP_PROJECT:-$(gcloud config get-value project 2>/dev/null)}"
GCP_ZONE="${GCP_ZONE:-us-central1-a}"
INSTANCE_NAME="${INSTANCE_NAME:-blackbugsai-prod}"
MACHINE_TYPE="${MACHINE_TYPE:-e2-standard-2}"    # 2 vCPU, 8GB RAM
DISK_SIZE="${DISK_SIZE:-50}"                     # GB
IMAGE_FAMILY="${IMAGE_FAMILY:-debian-12}"
IMAGE_PROJECT="${IMAGE_PROJECT:-debian-cloud}"

# Bot settings
BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
ADMIN_TOKEN="${ADMIN_WEB_TOKEN:-$(openssl rand -hex 24)}"
SECRET_KEY="${SECRET_KEY:-$(openssl rand -hex 32)}"
LLM_KEY="${LLM_API_KEY:-}"
DEEPSEEK_KEY="${DEEPSEEK_API_KEY:-}"

# ── COLORS ────────────────────────────────────────────────────────────────
RED='\033[0;31m' GREEN='\033[0;32m' YELLOW='\033[1;33m'
CYAN='\033[0;36m' NC='\033[0m' BOLD='\033[1m'

log()  { echo -e "${CYAN}[$(date +%H:%M:%S)]${NC} $*"; }
ok()   { echo -e "${GREEN}✅ $*${NC}"; }
warn() { echo -e "${YELLOW}⚠️  $*${NC}"; }
err()  { echo -e "${RED}❌ $*${NC}"; exit 1; }

echo -e "${BOLD}"
cat << 'EOF'
╔══════════════════════════════════════════════════════╗
║  🖤🐛  BlackBugsAI — GCP Deploy v3.0                 ║
║  Docker + Root SSH + Global Tunnel                   ║
╚══════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

# ── Validate ──────────────────────────────────────────────────────────────
command -v gcloud &>/dev/null || err "gcloud не найден. Установи: https://cloud.google.com/sdk/docs/install"
[[ -z "$GCP_PROJECT" ]] && err "Установи: export GCP_PROJECT=your-project-id"
[[ -z "$BOT_TOKEN" ]] && warn "TELEGRAM_BOT_TOKEN не задан — бот не будет работать"

log "Проект: ${BOLD}$GCP_PROJECT${NC}"
log "Зона:   ${BOLD}$GCP_ZONE${NC}"
log "VM:     ${BOLD}$INSTANCE_NAME (${MACHINE_TYPE})${NC}"

# ── Generate root password ────────────────────────────────────────────────
ROOT_PASS=$(openssl rand -base64 16 | tr -d '/+=')
log "Root password: ${BOLD}$ROOT_PASS${NC} (сохрани!)"

# ── Check if instance exists ──────────────────────────────────────────────
if gcloud compute instances describe "$INSTANCE_NAME" --zone="$GCP_ZONE" --project="$GCP_PROJECT" &>/dev/null; then
  warn "Instance $INSTANCE_NAME уже существует — переиспользуем"
  INSTANCE_EXISTS=true
else
  INSTANCE_EXISTS=false
fi

# ── Create VM ─────────────────────────────────────────────────────────────
if [[ "$INSTANCE_EXISTS" == "false" ]]; then
  log "Создаём VM..."
  gcloud compute instances create "$INSTANCE_NAME" \
    --project="$GCP_PROJECT" \
    --zone="$GCP_ZONE" \
    --machine-type="$MACHINE_TYPE" \
    --image-family="$IMAGE_FAMILY" \
    --image-project="$IMAGE_PROJECT" \
    --boot-disk-size="${DISK_SIZE}GB" \
    --boot-disk-type="pd-ssd" \
    --tags="blackbugsai,http-server,https-server" \
    --metadata="enable-oslogin=false" \
    --scopes="cloud-platform" \
    --no-address
  ok "VM создана: $INSTANCE_NAME"
fi

# ── Get external IP ────────────────────────────────────────────────────────
EXTERNAL_IP=$(gcloud compute instances describe "$INSTANCE_NAME" \
  --zone="$GCP_ZONE" --project="$GCP_PROJECT" \
  --format='get(networkInterfaces[0].accessConfigs[0].natIP)' 2>/dev/null || echo "")

[[ -z "$EXTERNAL_IP" ]] && {
  warn "Нет внешнего IP — добавляем ephemeral адрес..."
  gcloud compute instances add-access-config "$INSTANCE_NAME" \
    --zone="$GCP_ZONE" --project="$GCP_PROJECT"
  EXTERNAL_IP=$(gcloud compute instances describe "$INSTANCE_NAME" \
    --zone="$GCP_ZONE" --project="$GCP_PROJECT" \
    --format='get(networkInterfaces[0].accessConfigs[0].natIP)')
}

log "External IP: ${BOLD}$EXTERNAL_IP${NC}"

# ── Firewall rules ────────────────────────────────────────────────────────
log "Настройка firewall..."
gcloud compute firewall-rules describe "blackbugsai-allow-web" --project="$GCP_PROJECT" &>/dev/null || \
  gcloud compute firewall-rules create "blackbugsai-allow-web" \
    --project="$GCP_PROJECT" \
    --direction=INGRESS \
    --action=ALLOW \
    --rules=tcp:80,tcp:8080,tcp:443 \
    --target-tags=blackbugsai \
    --source-ranges=0.0.0.0/0 \
    --description="BlackBugsAI web access" 2>/dev/null || true

# ── Startup script ────────────────────────────────────────────────────────
log "Создаём startup script..."
STARTUP_SCRIPT=$(cat << STARTUP_EOF
#!/bin/bash
set -euo pipefail

echo "🚀 BlackBugsAI GCP Startup Script"

# ── Root SSH setup ──────────────────────────────────────────────────────
echo "root:${ROOT_PASS}" | chpasswd
sed -i 's/#PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config
sed -i 's/PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config
sed -i 's/#PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config
sed -i 's/PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config
systemctl restart sshd
echo "✅ Root SSH enabled"

# ── Update system ───────────────────────────────────────────────────────
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq && apt-get install -yq curl git unzip jq openssl

# ── Install Docker ──────────────────────────────────────────────────────
if ! command -v docker &>/dev/null; then
  curl -fsSL https://get.docker.com | bash
  systemctl enable --now docker
  echo "✅ Docker installed: \$(docker --version)"
fi

# ── Install Docker Compose v2 ────────────────────────────────────────────
if ! docker compose version &>/dev/null 2>&1; then
  mkdir -p /usr/local/lib/docker/cli-plugins
  COMPOSE_VER=\$(curl -fsSL https://api.github.com/repos/docker/compose/releases/latest | jq -r '.tag_name')
  curl -fsSL "https://github.com/docker/compose/releases/download/\${COMPOSE_VER}/docker-compose-linux-\$(uname -m)" \
    -o /usr/local/lib/docker/cli-plugins/docker-compose
  chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
  echo "✅ Docker Compose: \$(docker compose version)"
fi

# ── App directory ────────────────────────────────────────────────────────
mkdir -p /opt/blackbugsai
cd /opt/blackbugsai

# ── Write .env ──────────────────────────────────────────────────────────
cat > .env << 'ENVEOF'
TELEGRAM_BOT_TOKEN=${BOT_TOKEN}
ADMIN_WEB_TOKEN=${ADMIN_TOKEN}
SECRET_KEY=${SECRET_KEY}
LLM_API_KEY=${LLM_KEY}
DEEPSEEK_API_KEY=${DEEPSEEK_KEY}
LLM_PROVIDER=deepseek
ADMIN_WEB_PORT=8080
FISH_SERVER_PORT=5100
FISH_TUNNEL_DISABLED=true
TUNNEL_PROVIDER=cloudflared
TUNNEL_TARGET_PORT=80
AUTO_TUNNEL=true
TZ=UTC
HTTP_PORT=80
ENVEOF

echo "✅ .env written"

# ── Upload hint ──────────────────────────────────────────────────────────
cat > README_UPLOAD.txt << 'READMEEOF'
BlackBugsAI is ready for deployment!

Next steps:
1. Upload your project files to /opt/blackbugsai/:
   scp -r . root@${EXTERNAL_IP}:/opt/blackbugsai/

2. Run deployment:
   ssh root@${EXTERNAL_IP}
   cd /opt/blackbugsai
   docker compose -f docker-compose.v3.yml up -d --build

3. Check admin panel:
   Wait ~60s for tunnel URL in logs:
   docker compose -f docker-compose.v3.yml logs -f blackbugs | grep "Tunnel URL"
READMEEOF

# ── Systemd service for auto-restart ────────────────────────────────────
cat > /etc/systemd/system/blackbugsai.service << 'SVCEOF'
[Unit]
Description=BlackBugsAI Autonomous Agent Platform
After=docker.service network-online.target
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/blackbugsai
ExecStart=/usr/bin/docker compose -f docker-compose.v3.yml up -d --build
ExecStop=/usr/bin/docker compose -f docker-compose.v3.yml down
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
SVCEOF

systemctl daemon-reload
systemctl enable blackbugsai.service

echo ""
echo "╔═════════════════════════════════════════════╗"
echo "║  ✅ BlackBugsAI GCP Setup Complete!         ║"
echo "║                                             ║"
echo "║  Root SSH:  ssh root@${EXTERNAL_IP}        ║"
echo "║  Password:  ${ROOT_PASS}        ║"
echo "║                                             ║"
echo "║  Next: upload files and run docker compose  ║"
echo "╚═════════════════════════════════════════════╝"
STARTUP_EOF
)

# ── Apply startup script ──────────────────────────────────────────────────
log "Применяем startup script на VM..."
echo "$STARTUP_SCRIPT" > /tmp/startup.sh
gcloud compute ssh "$INSTANCE_NAME" \
  --zone="$GCP_ZONE" \
  --project="$GCP_PROJECT" \
  --tunnel-through-iap \
  --command="bash -s" < /tmp/startup.sh || {
    warn "SSH через IAP не сработал, пробуем напрямую..."
    sleep 30
    gcloud compute ssh "$INSTANCE_NAME" \
      --zone="$GCP_ZONE" \
      --project="$GCP_PROJECT" \
      --command="bash -s" < /tmp/startup.sh
  }

ok "VM настроена!"

# ── Upload project files ──────────────────────────────────────────────────
log "Загружаем файлы проекта..."
# Create archive excluding unnecessary files
tar czf /tmp/blackbugsai_deploy.tar.gz \
  --exclude='.git' \
  --exclude='*.pyc' \
  --exclude='__pycache__' \
  --exclude='*.db' \
  --exclude='memory.db' \
  --exclude='sessions.db' \
  --exclude='auth.db' \
  --exclude='asd.html' \
  --exclude='Limpa.ru.html' \
  . 2>/dev/null || warn "Некоторые файлы пропущены"

gcloud compute scp /tmp/blackbugsai_deploy.tar.gz \
  "$INSTANCE_NAME:/opt/blackbugsai/" \
  --zone="$GCP_ZONE" --project="$GCP_PROJECT" \
  --tunnel-through-iap 2>/dev/null || \
gcloud compute scp /tmp/blackbugsai_deploy.tar.gz \
  "$INSTANCE_NAME:/opt/blackbugsai/" \
  --zone="$GCP_ZONE" --project="$GCP_PROJECT"

ok "Файлы загружены"

# ── Launch on VM ─────────────────────────────────────────────────────────
log "Запускаем Docker Compose..."
gcloud compute ssh "$INSTANCE_NAME" \
  --zone="$GCP_ZONE" --project="$GCP_PROJECT" \
  --tunnel-through-iap \
  --command="
    cd /opt/blackbugsai
    tar xzf blackbugsai_deploy.tar.gz --overwrite 2>/dev/null || true
    # Use v3 compose if available
    COMPOSE_FILE=docker-compose.v3.yml
    [ -f docker-compose.v3.yml ] || COMPOSE_FILE=docker-compose.yml
    docker compose -f \$COMPOSE_FILE pull --quiet 2>/dev/null || true
    docker compose -f \$COMPOSE_FILE up -d --build
    echo '⏳ Waiting for tunnel URL...'
    sleep 15
    docker compose -f \$COMPOSE_FILE logs --tail=30 blackbugs 2>/dev/null || \
    docker compose -f \$COMPOSE_FILE logs --tail=30
  " 2>/dev/null || \
gcloud compute ssh "$INSTANCE_NAME" \
  --zone="$GCP_ZONE" --project="$GCP_PROJECT" \
  --command="cd /opt/blackbugsai && tar xzf blackbugsai_deploy.tar.gz --overwrite 2>/dev/null; docker compose -f docker-compose.v3.yml up -d --build"

# ── Summary ───────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${GREEN}"
cat << SUMMARY_EOF
╔══════════════════════════════════════════════════════════════╗
║  ✅  BlackBugsAI задеплоен на GCP!                           ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  🌍 External IP:   ${EXTERNAL_IP}                             ║
║  🖥️  Admin Panel:  http://${EXTERNAL_IP}:8080?token=${ADMIN_TOKEN:0:12}...   ║
║                                                              ║
║  🔑 SSH Root:      ssh root@${EXTERNAL_IP}                    ║
║  🔐 SSH Password:  ${ROOT_PASS}                               ║
║                                                              ║
║  🌐 Tunnel URL:    Смотри в логах (занимает ~30с)             ║
║     docker compose -f docker-compose.v3.yml logs blackbugs   ║
║                                                              ║
║  📋 Admin Token:   ${ADMIN_TOKEN}     ║
║                                                              ║
╠══════════════════════════════════════════════════════════════╣
║  СОХРАНИ ЭТИ ДАННЫЕ! Они больше не будут показаны.           ║
╚══════════════════════════════════════════════════════════════╝
SUMMARY_EOF
echo -e "${NC}"

# Save credentials to file
cat > ./gcp_deploy_credentials.txt << CREDS
=== BlackBugsAI GCP Deploy Credentials ===
Deployed: $(date -u)
Instance: $INSTANCE_NAME
Zone: $GCP_ZONE
External IP: $EXTERNAL_IP

SSH Root Access:
  ssh root@$EXTERNAL_IP
  Password: $ROOT_PASS

Admin Panel:
  URL: http://$EXTERNAL_IP:8080
  Token: $ADMIN_TOKEN
  Direct with auth: http://$EXTERNAL_IP:8080?token=$ADMIN_TOKEN

Environment:
  ADMIN_WEB_TOKEN=$ADMIN_TOKEN
  SECRET_KEY=$SECRET_KEY
CREDS
ok "Данные сохранены в gcp_deploy_credentials.txt"
warn "НИКОМУ НЕ ПЕРЕДАВАЙ этот файл!"
