
BlackBugsAI FULL OVERLAY (n8n-like) — NON-DESTRUCTIVE PATCH

This patch adds:
- Fullscreen React Flow builder overlay (like n8n)
- Hotkey toggle (F2)
- AI pipeline build + run
- SSE live execution highlighting
- Optional Redis worker (extensions/)

IMPORTANT: It does NOT replace your admin_panel.html.

STEPS:

1) Copy folders 'overlay' and 'extensions' into your project root.

2) Open your existing admin_panel.html and add BEFORE </body>:

<script src="/overlay/reactflow-overlay.umd.js"></script>
<script>
  window.AIOverlay.init({ mode: "full", hotkey: "F2" });
</script>

3) Ensure backend endpoints exist (or mount extensions/api_adapters.py):
   POST /api/matrix/run
   GET  /api/jobs/{job_id}/stream
   POST /api/pipeline/generate

4) (Optional but recommended) Add Redis + worker:

docker-compose addition:

services:
  redis:
    image: redis:7
    restart: always

  worker:
    build: .
    command: python extensions/worker.py
    environment:
      - REDIS_HOST=redis
    depends_on:
      - redis

5) Run:
   docker compose up -d --build

6) Open your admin panel and press F2 to toggle the builder.

Notes:
- Uses CDN (React, ReactDOM, ReactFlow) to avoid build changes.
- Keeps your existing UI intact.
