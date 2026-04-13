FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    ffmpeg git curl wget openssh-client ca-certificates jq \
    && rm -rf /var/lib/apt/lists/*

# Cloudflared
RUN curl -fsSL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 \
    -o /usr/local/bin/cloudflared \
    && chmod +x /usr/local/bin/cloudflared

# Bore
RUN BORE_VERSION=$(curl -fsSL https://api.github.com/repos/ekzhang/bore/releases/latest \
        | jq -r '.tag_name' | sed 's/^v//') \
    && curl -fsSL "https://github.com/ekzhang/bore/releases/download/v${BORE_VERSION}/bore-v${BORE_VERSION}-x86_64-unknown-linux-musl.tar.gz" \
        -o /tmp/bore.tar.gz \
    && tar -xzf /tmp/bore.tar.gz -C /usr/local/bin/ \
    && chmod +x /usr/local/bin/bore \
    && rm /tmp/bore.tar.gz

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 5000 8080

# Docker healthcheck — пингует /health каждые 30 сек
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

ENTRYPOINT ["/entrypoint.sh"]
