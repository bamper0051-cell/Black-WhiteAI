# AGENT_SMITH — Patch Notes

## Изменённые файлы

### agent_session.py — `execute_pipeline`
**Баги исправлены:**
1. `output.txt` теперь сохраняется ВСЕГДА:
   - При успехе: финальный прогон sandbox → `output.txt`
   - При краше: последний stderr из `fix_history` → `output.txt`
   - При server/bot коде: пометка "sandbox not executed" → `output.txt`
2. `execute_pipeline` теперь возвращает `next_stage: STAGE_WAIT_FILES` вместо молчаливого
   закрытия сессии — `bot.py` читает это поле и сохраняет сессию живой.

### bot.py — `_run_code_pipeline` и `adm_agent_task`
**Баги исправлены:**
1. После завершения pipeline сессия НЕ закрывается — сбрасывается в `STAGE_WAIT_FILES`.
   Пользователь может сразу писать следующую задачу без пересоздания сессии.
2. Отправка результата: сначала ZIP (единый архив), только при ошибке отправки —
   артефакты по одному (fallback). Нет спама отдельными файлами.

### chat_agent.py — `_run_fix_agent`, `_run_script_agent`
**Баги исправлены:**
1. `_run_fix_agent` при успехе:
   - Создаёт `fix_<ts>/fixed_code.py` — исправленный код
   - Создаёт `fix_<ts>/output.txt` — stdout выполнения
   - Сохраняет каждую неудачную итерацию как `attempt_N.py` с комментарием ошибки
   - Все файлы возвращаются в `files` — `bot.py` пакует их в единый zip
2. `_run_script_agent` при успехе:
   - Создаёт `script_<ts>/script.py` + `output.txt`
   - `bot.py` пакует их в zip автоматически

### coder3/modes.py — `run_quick_mode`, `run_sandbox_mode`
**Баги исправлены:**
1. `run_quick_mode` — определяет daemon/bot код через `_DAEMON_MARKERS`:
   - Для daemon: sandbox НЕ запускается, в README пометка "Smoke-run not performed"
   - Для runnable: sandbox запускается, stdout/stderr → `output.txt` в zip
2. `run_sandbox_mode` — добавлен единый `sandbox/output.txt` (stdout+stderr combined)
   в дополнение к раздельным `stdout.txt` и `stderr.txt`

### coder3/autofix.py — `run_autofix`
**Баги исправлены:**
1. Оригинальный код сохраняется как `autofix/round_0.py` — полная история всех итераций
2. При успехе: запускается sandbox на исправленном коде → `autofix/output.txt`
3. При неудаче: `output.txt` содержит финальную ошибку и hint для ручного доразбора
