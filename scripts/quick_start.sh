#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# BlackBugsAI v4.0 — Quick Start Script
#
# This script sets up and starts the entire infrastructure
# ═══════════════════════════════════════════════════════════════════════════

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║       BlackBugsAI v4.0 — Infrastructure Quick Start         ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Step 1: Check prerequisites
echo -e "${YELLOW}📋 Step 1: Checking prerequisites...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi

if ! command -v docker compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed. Please install Docker Compose first.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker $(docker --version) found${NC}"
echo -e "${GREEN}✅ Docker Compose $(docker compose version) found${NC}"
echo ""

# Step 2: Setup environment
echo -e "${YELLOW}📋 Step 2: Setting up environment...${NC}"

if [ ! -f .env ]; then
    echo -e "${BLUE}Creating .env from .env.example...${NC}"
    cp .env.example .env

    echo -e "${YELLOW}⚠️  IMPORTANT: You need to configure .env file!${NC}"
    echo -e "${YELLOW}   Please fill in the following required values:${NC}"
    echo -e "${YELLOW}   - TELEGRAM_BOT_TOKEN${NC}"
    echo -e "${YELLOW}   - ADMIN_WEB_TOKEN${NC}"
    echo -e "${YELLOW}   - POSTGRES_PASSWORD${NC}"
    echo -e "${YELLOW}   - REDIS_PASSWORD${NC}"
    echo -e "${YELLOW}   - N8N_BASIC_AUTH_PASSWORD${NC}"
    echo -e "${YELLOW}   - At least one LLM API key (OPENAI_API_KEY, GROQ_API_KEY, etc.)${NC}"
    echo ""

    read -p "Press Enter to edit .env file now, or Ctrl+C to edit manually later..."
    ${EDITOR:-nano} .env
else
    echo -e "${GREEN}✅ .env file already exists${NC}"
fi

echo ""

# Step 3: Pull images
echo -e "${YELLOW}📋 Step 3: Pulling Docker images...${NC}"
docker compose pull

echo -e "${GREEN}✅ Images pulled successfully${NC}"
echo ""

# Step 4: Build services
echo -e "${YELLOW}📋 Step 4: Building services...${NC}"
docker compose build --no-cache

echo -e "${GREEN}✅ Services built successfully${NC}"
echo ""

# Step 5: Start infrastructure services first
echo -e "${YELLOW}📋 Step 5: Starting infrastructure services...${NC}"
docker compose up -d postgres redis

echo -e "${BLUE}Waiting for PostgreSQL to be ready...${NC}"
timeout=60
while ! docker compose exec -T postgres pg_isready -U blackbugs > /dev/null 2>&1; do
    timeout=$((timeout - 1))
    if [ $timeout -le 0 ]; then
        echo -e "${RED}❌ PostgreSQL failed to start${NC}"
        exit 1
    fi
    sleep 1
done

echo -e "${GREEN}✅ PostgreSQL is ready${NC}"

echo -e "${BLUE}Waiting for Redis to be ready...${NC}"
timeout=30
while ! docker compose exec -T redis redis-cli ping > /dev/null 2>&1; do
    timeout=$((timeout - 1))
    if [ $timeout -le 0 ]; then
        echo -e "${RED}❌ Redis failed to start${NC}"
        exit 1
    fi
    sleep 1
done

echo -e "${GREEN}✅ Redis is ready${NC}"
echo ""

# Step 6: Run migrations
echo -e "${YELLOW}📋 Step 6: Running database migrations...${NC}"

# Create scripts directory if it doesn't exist
mkdir -p scripts

# Check if migrate.py exists
if [ -f scripts/migrate.py ]; then
    # Install psycopg2 in backend container if needed
    docker compose run --rm backend pip install psycopg2-binary > /dev/null 2>&1 || true

    # Run migrations
    docker compose run --rm backend python scripts/migrate.py
    echo -e "${GREEN}✅ Migrations completed${NC}"
else
    echo -e "${YELLOW}⚠️  Migration script not found, skipping...${NC}"
fi

echo ""

# Step 7: Start all services
echo -e "${YELLOW}📋 Step 7: Starting all services...${NC}"
docker compose up -d

echo -e "${GREEN}✅ All services started${NC}"
echo ""

# Step 8: Wait for services to be healthy
echo -e "${YELLOW}📋 Step 8: Waiting for services to be healthy...${NC}"

echo -e "${BLUE}Waiting for backend to be ready...${NC}"
timeout=120
while ! curl -sf http://localhost/health > /dev/null 2>&1; do
    timeout=$((timeout - 1))
    if [ $timeout -le 0 ]; then
        echo -e "${RED}❌ Backend failed to become healthy${NC}"
        echo -e "${YELLOW}Check logs with: docker compose logs backend${NC}"
        exit 1
    fi
    sleep 2
done

echo -e "${GREEN}✅ Backend is healthy${NC}"
echo ""

# Step 9: Show status
echo -e "${YELLOW}📋 Step 9: Service status...${NC}"
docker compose ps

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    🎉 Setup Complete! 🎉                      ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}📡 Services are now running:${NC}"
echo -e "   ${GREEN}•${NC} Admin Panel:       ${YELLOW}http://localhost/admin/${NC}"
echo -e "   ${GREEN}•${NC} API:               ${YELLOW}http://localhost/api/${NC}"
echo -e "   ${GREEN}•${NC} n8n:               ${YELLOW}http://localhost/n8n/${NC}"
echo -e "   ${GREEN}•${NC} Fish Module:       ${YELLOW}http://localhost/fish/${NC}"
echo -e "   ${GREEN}•${NC} Health Check:      ${YELLOW}http://localhost/health${NC}"
echo ""
echo -e "${BLUE}📊 Useful commands:${NC}"
echo -e "   ${GREEN}•${NC} View logs:         ${YELLOW}docker compose logs -f${NC}"
echo -e "   ${GREEN}•${NC} Stop services:     ${YELLOW}docker compose down${NC}"
echo -e "   ${GREEN}•${NC} Restart service:   ${YELLOW}docker compose restart backend${NC}"
echo -e "   ${GREEN}•${NC} View status:       ${YELLOW}docker compose ps${NC}"
echo ""
echo -e "${BLUE}📚 Documentation:${NC}"
echo -e "   ${GREEN}•${NC} README_INFRASTRUCTURE.md - Complete setup guide"
echo -e "   ${GREEN}•${NC} INFRASTRUCTURE.md        - Architecture overview"
echo ""
echo -e "${YELLOW}⚠️  Don't forget to configure your Telegram bot and LLM API keys in .env!${NC}"
echo ""
