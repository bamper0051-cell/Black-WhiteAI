#!/data/data/com.termux/files/usr/bin/bash
# ============================================================
# BlackBugsAI — Termux Setup Script
# Запускай на Android с установленным Termux
# ============================================================

set -e

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}"
echo "██████╗ ██╗      █████╗  ██████╗██╗  ██╗"
echo "██╔══██╗██║     ██╔══██╗██╔════╝██║ ██╔╝"
echo "██████╔╝██║     ███████║██║     █████╔╝ "
echo "██╔══██╗██║     ██╔══██║██║     ██╔═██╗ "
echo "██████╔╝███████╗██║  ██║╚██████╗██║  ██╗"
echo "╚═════╝ ╚══════╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝"
echo -e "${NC}"
echo -e "${GREEN}BlackBugsAI — Termux Setup${NC}"
echo "=================================="

# ── 1. System packages ────────────────────────────────────────────────────────
echo -e "\n${YELLOW}[1/7] Обновляем пакеты Termux...${NC}"
pkg update -y && pkg upgrade -y

echo -e "\n${YELLOW}[2/7] Устанавливаем зависимости...${NC}"
pkg install -y \
    python \
    python-pip \
    git \
    curl \
    wget \
    ffmpeg \
    libxml2 \
    libxslt \
    libjpeg-turbo \
    libpng \
    openssl \
    rust \
    clang \
    make

# ── 2. Storage permission ────────────────────────────────────────────────────
echo -e "\n${YELLOW}[3/7] Запрашиваем доступ к хранилищу...${NC}"
termux-setup-storage 2>/dev/null || echo "Storage already set up"

# ── 3. Clone or update repo ──────────────────────────────────────────────────
echo -e "\n${YELLOW}[4/7] Клонируем репозиторий...${NC}"
INSTALL_DIR="$HOME/blackbugsai"

if [ -d "$INSTALL_DIR" ]; then
    echo "Директория существует, обновляем..."
    cd "$INSTALL_DIR" && git pull origin main
else
    git clone https://github.com/bamper0051-cell/Black-WhiteAI.git "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# ── 4. Python dependencies ────────────────────────────────────────────────────
echo -e "\n${YELLOW}[5/7] Устанавливаем Python зависимости...${NC}"
pip install --upgrade pip wheel
pip install -r requirements.txt

# ── 5. Environment setup ──────────────────────────────────────────────────────
echo -e "\n${YELLOW}[6/7] Настраиваем конфигурацию...${NC}"
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo -e "${YELLOW}⚠️  Заполни .env файл своими API ключами!${NC}"
    echo -e "   nano $INSTALL_DIR/.env"
fi

# ── 6. Create launch script ──────────────────────────────────────────────────
cat > "$HOME/start-blackbugsai.sh" << 'EOF'
#!/data/data/com.termux/files/usr/bin/bash
cd $HOME/blackbugsai
echo "Starting BlackBugsAI..."
python main.py
EOF
chmod +x "$HOME/start-blackbugsai.sh"

# ── 7. Termux service (auto-start) ───────────────────────────────────────────
if command -v sv &> /dev/null; then
    mkdir -p ~/.termux/boot
    cat > ~/.termux/boot/blackbugsai << 'EOF'
#!/data/data/com.termux/files/usr/bin/bash
cd $HOME/blackbugsai
python main.py >> $HOME/blackbugsai.log 2>&1 &
EOF
    chmod +x ~/.termux/boot/blackbugsai
    echo "Auto-start on boot configured"
fi

echo -e "\n${GREEN}=================================="
echo "✅ BlackBugsAI установлен!"
echo "=================================="
echo ""
echo "1. Заполни конфиг:"
echo "   nano $INSTALL_DIR/.env"
echo ""
echo "2. Запусти:"
echo "   ~/start-blackbugsai.sh"
echo ""
echo "3. Или вручную:"
echo "   cd $INSTALL_DIR && python main.py"
echo ""
echo "Admin panel: http://localhost:8080"
echo -e "===================${NC}"
