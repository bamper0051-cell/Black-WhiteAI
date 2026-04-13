#!/bin/bash
# verify_server.sh — Проверка доступности BlackBugsAI сервера для Android app

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  BlackBugsAI Server Verification Script"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if .env exists
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    echo -e "${RED}✗ .env file not found${NC}"
    echo "  Create .env from .env.example:"
    echo "  cp .env.example .env"
    exit 1
fi

# Extract admin token
ADMIN_TOKEN=$(grep ADMIN_WEB_TOKEN "$SCRIPT_DIR/.env" | cut -d'=' -f2 | tr -d ' "')
ADMIN_PORT=$(grep ADMIN_WEB_PORT "$SCRIPT_DIR/.env" | cut -d'=' -f2 | tr -d ' "')
ADMIN_PORT=${ADMIN_PORT:-8080}

if [ -z "$ADMIN_TOKEN" ] || [ "$ADMIN_TOKEN" = "changeme_secret_token" ]; then
    echo -e "${YELLOW}⚠ Warning: Using default/weak admin token${NC}"
    echo "  Consider generating a strong token:"
    echo "  echo \"ADMIN_WEB_TOKEN=\$(openssl rand -hex 32)\" >> .env"
    echo ""
fi

# Check 1: Docker container
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1. Checking Docker Container..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
<<<<<<< HEAD
if docker ps | grep -q blackbugs-main; then
    echo -e "${GREEN}✓ Container 'blackbugs-main' is running${NC}"
    docker ps | grep blackbugs-main | awk '{print "  Status: " $7 " ago"}'
else
    echo -e "${RED}✗ Container 'blackbugs-main' is not running${NC}"
=======
if docker ps | grep -q automuvie; then
    echo -e "${GREEN}✓ Container 'automuvie' is running${NC}"
    docker ps | grep automuvie | awk '{print "  Status: " $7 " ago"}'
else
    echo -e "${RED}✗ Container 'automuvie' is not running${NC}"
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
    echo "  Start it with: docker-compose up -d"
    exit 1
fi
echo ""

# Check 2: Port listening
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2. Checking Port $ADMIN_PORT..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if netstat -tln 2>/dev/null | grep -q ":$ADMIN_PORT " || ss -tln 2>/dev/null | grep -q ":$ADMIN_PORT "; then
    echo -e "${GREEN}✓ Port $ADMIN_PORT is listening${NC}"
else
    echo -e "${RED}✗ Port $ADMIN_PORT is not listening${NC}"
    exit 1
fi
echo ""

# Check 3: Local ping endpoint
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3. Testing /ping endpoint (no auth)..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
PING_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" "http://localhost:$ADMIN_PORT/ping" || echo "FAILED")
HTTP_CODE=$(echo "$PING_RESPONSE" | grep "HTTP_CODE" | cut -d':' -f2)

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓ /ping endpoint works${NC}"
    echo "$PING_RESPONSE" | grep -v "HTTP_CODE" | python3 -m json.tool 2>/dev/null || echo "$PING_RESPONSE" | grep -v "HTTP_CODE"
else
    echo -e "${RED}✗ /ping endpoint failed (HTTP $HTTP_CODE)${NC}"
    echo "$PING_RESPONSE" | grep -v "HTTP_CODE"
fi
echo ""

# Check 4: /health endpoint
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "4. Testing /health endpoint (no auth)..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
HEALTH_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" "http://localhost:$ADMIN_PORT/health" || echo "FAILED")
HTTP_CODE=$(echo "$HEALTH_RESPONSE" | grep "HTTP_CODE" | cut -d':' -f2)

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓ /health endpoint works${NC}"
    echo "$HEALTH_RESPONSE" | grep -v "HTTP_CODE" | python3 -m json.tool 2>/dev/null || echo "$HEALTH_RESPONSE" | grep -v "HTTP_CODE"
else
    echo -e "${YELLOW}⚠ /health endpoint returned HTTP $HTTP_CODE${NC}"
fi
echo ""

# Check 5: Admin authenticated endpoint
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "5. Testing /api/status endpoint (with auth)..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
STATUS_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
    -H "X-Admin-Token: $ADMIN_TOKEN" \
    "http://localhost:$ADMIN_PORT/api/status" || echo "FAILED")
HTTP_CODE=$(echo "$STATUS_RESPONSE" | grep "HTTP_CODE" | cut -d':' -f2)

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓ /api/status endpoint works with admin token${NC}"
    echo "$STATUS_RESPONSE" | grep -v "HTTP_CODE" | python3 -m json.tool 2>/dev/null | head -20 || echo "$STATUS_RESPONSE" | grep -v "HTTP_CODE"
elif [ "$HTTP_CODE" = "401" ]; then
    echo -e "${RED}✗ Authentication failed (401 Unauthorized)${NC}"
    echo "  Check your ADMIN_WEB_TOKEN in .env"
else
    echo -e "${RED}✗ /api/status endpoint failed (HTTP $HTTP_CODE)${NC}"
fi
echo ""

# Check 6: External IP
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "6. Getting External IP Address..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
EXTERNAL_IP=$(curl -s ifconfig.me || curl -s icanhazip.com || echo "UNKNOWN")
LOCAL_IP=$(ip route get 8.8.8.8 2>/dev/null | awk '{print $7; exit}' || hostname -I | awk '{print $1}')

echo -e "${GREEN}External IP:${NC} $EXTERNAL_IP"
echo -e "${GREEN}Local IP:${NC} $LOCAL_IP"
echo ""

# Check 7: GCP Firewall (if gcloud is available)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "7. Checking GCP Firewall Rules..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if command -v gcloud &> /dev/null; then
    if gcloud compute firewall-rules list --format="table(name,allowed)" 2>/dev/null | grep -q "tcp:$ADMIN_PORT"; then
        echo -e "${GREEN}✓ Firewall rule exists for port $ADMIN_PORT${NC}"
        gcloud compute firewall-rules list --format="table(name,allowed)" 2>/dev/null | grep "tcp:$ADMIN_PORT"
    else
        echo -e "${YELLOW}⚠ No firewall rule found for port $ADMIN_PORT${NC}"
        echo "  Create one with:"
        echo "  gcloud compute firewall-rules create allow-admin-panel \\"
        echo "    --allow tcp:$ADMIN_PORT \\"
        echo "    --source-ranges 0.0.0.0/0 \\"
        echo "    --description 'Allow BlackBugsAI Admin Panel'"
    fi
else
    echo -e "${YELLOW}⚠ gcloud CLI not installed, skipping firewall check${NC}"
fi
echo ""

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Configuration Summary for Android App"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "GCP SERVER IP:    $EXTERNAL_IP"
echo "DOCKER PORT:      $ADMIN_PORT"
echo "ADMIN TOKEN:      ${ADMIN_TOKEN:0:8}... ($(echo -n "$ADMIN_TOKEN" | wc -c) chars)"
echo "USE HTTPS:        OFF"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Quick Test from Another Machine"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Run this command from your local computer or phone (via Termux):"
echo ""
echo "curl http://$EXTERNAL_IP:$ADMIN_PORT/ping"
echo ""
echo "Expected response:"
echo '{"ok":true,"pong":true,"port":'$ADMIN_PORT'}'
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓ Server is ready for Android app connection!${NC}"
    exit 0
else
    echo -e "${RED}✗ Server has issues, check the errors above${NC}"
    exit 1
fi
