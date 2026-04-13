#!/usr/bin/env bash
set -euo pipefail

echo "== import check =="
python3 - <<'PY'
import bot
import admin_web
import task_queue
import neo_tool_library
import agent_matrix as m

neo_count = len(getattr(neo_tool_library, "_T", {}) or {})
matrix_builtin = len(getattr(m, "_BUILTIN_TOOLS", {}) or {})
matrix_total = len(m.list_tools())

print("bot/admin_web/task_queue imports: OK")
print(f"neo tools available: {neo_count}")
print(f"matrix builtin tools: {matrix_builtin}")
print(f"matrix db tools: {matrix_total}")
PY

echo "== admin health check =="

pkill -f "python3 admin_web.py" 2>/dev/null || true
pkill -f "python admin_web.py" 2>/dev/null || true
sleep 1

python3 - <<'PY' >/tmp/admin_web.log 2>&1 &
import time
import admin_web

admin_web.start_admin_web()
time.sleep(20)
PY
ADMIN_PID=$!

OK=""
for i in $(seq 1 15); do
  for port in 8080 8081 8082 8083 8084; do
    if curl -fsS "http://127.0.0.1:${port}/health" >/tmp/admin_health.json 2>/dev/null; then
      OK="$port"
      break 2
    fi
  done
  sleep 1
done

if [ -n "$OK" ]; then
  echo "admin health port: $OK"
  cat /tmp/admin_health.json
else
  echo "admin_web failed after waiting:"
  echo "--- admin_web.log ---"
  cat /tmp/admin_web.log || true
  echo "--- listening ports ---"
  ss -ltnp | grep -E ':8080|:8081|:8082|:8083|:8084' || true
  kill "$ADMIN_PID" 2>/dev/null || true
  exit 1
fi

kill "$ADMIN_PID" 2>/dev/null || true
wait "$ADMIN_PID" 2>/dev/null || true

echo
echo "== smoke startup OK =="
