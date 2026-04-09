#!/usr/bin/env bash
set -e

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

python3 admin_web.py >/tmp/admin_web.log 2>&1 &
ADMIN_PID=$!
sleep 4

if curl -fsS http://127.0.0.1:8080/health >/tmp/admin_health.json 2>/dev/null; then
  cat /tmp/admin_health.json
elif curl -fsS http://127.0.0.1:8081/health >/tmp/admin_health.json 2>/dev/null; then
  cat /tmp/admin_health.json
else
  echo "admin_web failed:"
  cat /tmp/admin_web.log
  kill "$ADMIN_PID" 2>/dev/null || true
  exit 1
fi

kill "$ADMIN_PID" 2>/dev/null || true
wait "$ADMIN_PID" 2>/dev/null || true

echo
echo "== smoke startup OK =="
