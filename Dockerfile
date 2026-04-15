FROM python:3.11-slim
WORKDIR /app

# Системные утилиты — включая инструменты для MATRIX (nmap, whois, git)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg git curl wget ca-certificates jq \
    nmap whois procps dnsutils net-tools \
    && rm -rf /var/lib/apt/lists/*

# Cloudflared
RUN curl -fsSL \
    https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 \
    -o /usr/local/bin/cloudflared \
    && chmod +x /usr/local/bin/cloudflared || true

# Bore tunnel
RUN BORE_VER=$(curl -fsSL https://api.github.com/repos/ekzhang/bore/releases/latest \
    | jq -r '.tag_name' | sed 's/^v//') 2>/dev/null \
    && curl -fsSL \
    "https://github.com/ekzhang/bore/releases/download/v${BORE_VER}/bore-v${BORE_VER}-x86_64-unknown-linux-musl.tar.gz" \
    -o /tmp/bore.tar.gz \
    && tar -xzf /tmp/bore.tar.gz -C /usr/local/bin/ \
    && chmod +x /usr/local/bin/bore \
    && rm -f /tmp/bore.tar.gz || true

# Python зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Код
COPY . .
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Рабочие директории агентов
RUN mkdir -p \
    /app/neo_workspace/tools \
    /app/neo_workspace/artifacts \
    /app/neo_workspace/osint \
    /app/matrix_workspace/tools \
    /app/matrix_workspace/artifacts \
    /app/matrix_workspace/repos \
    /app/agent_projects/results \
    /app/agent_projects/uploads \
    /app/artifacts \
    /app/created_bots \
    /app/logs

EXPOSE 5100 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

ENTRYPOINT ["/entrypoint.sh"]
