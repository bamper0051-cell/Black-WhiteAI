# ═══════════════════════════════════════════════════════════════════════════
#  🖤🐛  BlackBugsAI — Dockerfile v3.0
#  Autonomous AI Agent Platform
#  Build: docker build -f Dockerfile.v3 -t blackbugsai:v3 .
# ═══════════════════════════════════════════════════════════════════════════

FROM python:3.11-slim AS base

LABEL org.opencontainers.image.title="BlackBugsAI" \
      org.opencontainers.image.version="3.0" \
      org.opencontainers.image.description="Autonomous AI Agent Platform with Matrix + Neo agents" \
      maintainer="BlackBugsAI"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # Fix fish/admin tunnel conflict
    FISH_TUNNEL_DISABLED=true \
    # No 60s timeout anywhere
    SANDBOX_TIMEOUT=600

WORKDIR /app

RUN apt-get update && apt-get install -y curl \
 && curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /usr/local/bin/cloudflared \
 && chmod +x /usr/local/bin/cloudflared
# ── Системные зависимости ─────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl wget ca-certificates git jq unzip \
    openssh-client netcat-openbsd dnsutils net-tools iproute2 \
    nmap whois ffmpeg \
    procps htop \
    gcc g++ libffi-dev libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# ── Cloudflared (мультиарх) ───────────────────────────────────────────────
RUN ARCH=$(dpkg --print-architecture) && \
    CF_ARCH=$(case $ARCH in amd64) echo amd64;; arm64) echo arm64;; armhf) echo arm;; *) echo amd64;; esac) && \
    curl -fsSL "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-${CF_ARCH}" \
    -o /usr/local/bin/cloudflared && chmod +x /usr/local/bin/cloudflared \
    || echo "⚠️ cloudflared not installed — tunnel won't work"

# ── Bore tunnel ───────────────────────────────────────────────────────────
RUN BORE_VER=$(curl -fsSL https://api.github.com/repos/ekzhang/bore/releases/latest 2>/dev/null \
    | python3 -c "import sys,json;print(json.load(sys.stdin).get('tag_name','v0.5.0').lstrip('v'))" 2>/dev/null || echo "0.5.0") && \
    curl -fsSL "https://github.com/ekzhang/bore/releases/download/v${BORE_VER}/bore-v${BORE_VER}-x86_64-unknown-linux-musl.tar.gz" \
    -o /tmp/bore.tar.gz && tar -xzf /tmp/bore.tar.gz -C /usr/local/bin/ && \
    chmod +x /usr/local/bin/bore && rm -f /tmp/bore.tar.gz \
    || echo "⚠️ bore not installed"

# ── Python зависимости ────────────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir \
      flask-socketio==5.3.6 \
      eventlet==0.35.2 \
      psutil==5.9.8 \
      gevent==23.9.1

# ── Код ───────────────────────────────────────────────────────────────────
COPY . .

# ── Применяем v4 файлы если есть ─────────────────────────────────────────
RUN set -e; \
    [ -f admin_panel_v4.html ] && cp admin_panel_v4.html admin_panel.html && echo "✅ Admin v4 applied"; \
    [ -f nginx.conf ] && echo "ℹ️  nginx.conf found (used by nginx service)"; \
    echo "🔧 BlackBugsAI v3 build complete"

# ── Рабочие директории ────────────────────────────────────────────────────
RUN mkdir -p \
    /app/data \
    /app/logs \
    /app/matrix_workspace/tools \
    /app/matrix_workspace/artifacts \
    /app/matrix_workspace/repos \
    /app/neo_workspace/tools \
    /app/neo_workspace/artifacts \
    /app/fish_data/pages \
    /app/fish_data/logs

# ── Права ─────────────────────────────────────────────────────────────────
RUN useradd -r -u 1001 -m -d /app -s /bin/bash blackbugs 2>/dev/null || true && \
    chown -R blackbugs:blackbugs /app 2>/dev/null || true

# ── Expose ────────────────────────────────────────────────────────────────
EXPOSE 8080 5100

# ── Health ────────────────────────────────────────────────────────────────
HEALTHCHECK --interval=20s --timeout=8s --start-period=30s --retries=5 \
    CMD curl -sf http://localhost:8080/health || exit 1

# ── Entrypoint ────────────────────────────────────────────────────────────
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
