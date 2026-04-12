# AGENT_SMITH — Отчёт об ошибках и архитектуре v2
**Дата:** 2026-03-21  
**Версия:** AGENT_SMITH_v1_telegram

---

## 1. Найденные ошибки (по модулям)

### 1.1. `agent_session.py` (AGENT_0051 / Smith)

| # | Ошибка | Критичность | Исправление |
|---|--------|-------------|-------------|
| 1 | После выполнения задачи сессия **закрывается** вместо перехода в WAIT_NEXT | 🔴 Высокая | Добавлен Stage.WAIT_NEXT, сессия остаётся активной |
| 2 | Файлы отправляются **по одному**, нет zip | 🔴 Высокая | Обязательный `pack_artifacts()` перед отправкой |
| 3 | stdout/stderr не всегда сохраняются в output.txt | 🟡 Средняя | `save_output()` вызывается в любом случае (ok и error) |
| 4 | Нет кнопки «Стоп» во время выполнения | 🟡 Средняя | `get_agent_running_keyboard()` отправляется с прогресс-сообщением |
| 5 | Файл добавляется в контекст И сразу запускает задачу | 🟡 Средняя | Файл → Stage.WAIT_FILES → явный запуск по «Готово» |
| 6 | Разные агенты имеют разную логику завершения | 🔴 Высокая | Единый цикл через `_run_agent()` в agent_session |

---

### 1.2. `chat_agent.py` (Coder / Coder2)

| # | Ошибка | Критичность | Исправление |
|---|--------|-------------|-------------|
| 1 | `_run_project_agent`: файлы создаются, zip **не упаковывается** | 🔴 Высокая | `pack_artifacts()` вызывается после всех файлов |
| 2 | `_run_fix_agent`: хранит только **финальную** версию | 🟡 Средняя | Сохраняет round_0..round_N + ошибки каждого раунда |
| 3 | `_run_script_agent`: zip не всегда создаётся при ошибке | 🟡 Средняя | zip создаётся всегда, caption указывает на ошибку |
| 4 | Флаг `code_session` сбрасывается после zip-отправки | 🟡 Средняя | Сессия управляется через agent_session, не в chat_agent |
| 5 | Нет проверки на GUI-код перед sandbox-запуском | 🟢 Низкая | `_is_gui_or_bot_code()` перед запуском |

---

### 1.3. `agent_coder3.py` / `coder3/` (AGENT_CODER3)

| # | Ошибка | Критичность | Исправление |
|---|--------|-------------|-------------|
| 1 | Режим `quick` для GUI-кода: sandbox не запускается, **zip не создаётся** | 🔴 Высокая | Всегда zip; если GUI — пометка «smoke-run пропущен» |
| 2 | Режим `project`: файлы только на диске, **zip не отправляется** | 🔴 Высокая | `pack_artifacts()` после создания всех файлов |
| 3 | Режим `autofix`: только финальная версия в архиве | 🟡 Средняя | Все round_N.py + round_N_output.txt в workspace → zip |
| 4 | Режим `sandbox`: stdout/stderr **не попадают в output.txt** | 🔴 Высокая | `save_output()` вызывается перед `pack_artifacts()` |
| 5 | `review` режим: нет zip — только текстовое сообщение в чат | 🟡 Средняя | Отчёт review_report.md → zip |
| 6 | `coder3/__init__.py` экспортирует только `run_agent_coder3` — внутренние функции недостижимы для тестов | 🟢 Низкая | Документировать публичный API |

---

### 1.4. `autofix.py` (корневой)

| # | Ошибка | Критичность | Исправление |
|---|--------|-------------|-------------|
| 1 | Дублирует логику `coder3/autofix.py` | 🟡 Средняя | Оба модуля переписаны через единый `_autofix()` в agent_utils |
| 2 | Не передаёт workspace — создаёт tmp-директорию, которая не попадает в итоговый zip | 🔴 Высокая | Принимает workspace как параметр |

---

### 1.5. `agent_utils.py` (НОВЫЙ ФАЙЛ)

Отсутствовал — создан с нуля. Устраняет дублирование кода во всех агентах.

---

## 2. Архитектура — единый цикл

```
Пользователь пишет запрос
        │
        ▼
handle_message() [agent_session.py]
        │
        ├── Stage.RUNNING? → "Агент занят" + кнопка ⛔
        ├── Stage.WAIT_FILES + "готово" → _run_agent()
        └── Иначе → detect_task_type() → _run_agent()
                           │
                           ▼
                   _run_agent() [agent_session.py]
                           │
                    1. create_workspace()
                    2. progress_msg + кнопка ⛔
                    3. agent_fn(bot, state) — агент выполняет задачу
                    4. Если zip не вернулся — pack_artifacts(workspace)
                    5. send_zip_result()
                    6. state.stage = WAIT_NEXT
                    7. keep_session_alive() → кнопки 📎 / 🔴
```

### Внутри агента (chat_agent / coder3):

```
agent_fn(bot, state)
    │
    ├── script → _run_script_agent()
    │       ├── _generate_code() [LLM]
    │       ├── _run_code_in_sandbox()
    │       ├── Ошибка? → _run_fix_agent() [round_0..N в workspace]
    │       ├── save_output(workspace, stdout, stderr)
    │       └── pack_artifacts(workspace) → zip
    │
    ├── project → _run_project_agent()
    │       ├── _generate_project_plan() [LLM → JSON]
    │       ├── Создать файлы в workspace
    │       └── pack_artifacts(workspace) → zip  ← ИСПРАВЛЕНО
    │
    └── quick → _run_quick() [coder3]
            ├── _llm_generate()
            ├── GUI/бот? → zip без sandbox  ← ИСПРАВЛЕНО
            ├── Иначе → _sandbox_run()
            ├── Ошибка? → _autofix() [все раунды в workspace]
            ├── save_output()
            └── pack_artifacts() → zip
```

---

## 3. Сценарии — проверка логики

### Сценарий 1: «нарисуй анимацию космос»
```
detect_task_type → "image"
→ register_agent("image") → _run_coder3(mode="quick")
→ _llm_generate("напиши анимацию космос") → matplotlib/PIL код
→ _is_gui_or_bot_code() → False
→ _sandbox_run() → создаёт snowfall.gif / animation.gif
→ save_output(stdout, stderr)
→ pack_artifacts([solution.py, output.txt, animation.gif])
→ send_zip_result() → архив с кодом + gif
→ keep_session_alive() → кнопки 📎 / 🔴
```
✅ Результат: `quick_result.zip` [solution.py + output.txt + animation.gif]

---

### Сценарий 2: «напиши телеграм парсер каналов»
```
detect_task_type → "project" (ключевое слово "парсер")
→ register_agent("project") → _run_project_agent()
→ _generate_project_plan() → JSON [main.py, parser.py, config.py, requirements.txt]
→ Создать файлы в workspace
→ pack_artifacts(все созданные файлы)   ← ИСПРАВЛЕНО: раньше zip не создавался
→ send_zip_result() → архив проекта
→ keep_session_alive()
```
✅ Результат: `project.zip` [main.py + parser.py + config.py + requirements.txt + README.md]

---

### Сценарий 3: «напиши код на python»
```
detect_task_type → "script"
→ _run_script_agent()
→ _generate_code() → script.py
→ _run_code_in_sandbox() → stdout, stderr
→ Ошибка? → _run_fix_agent() → round_0..N.py + output files
→ save_output(workspace, stdout, stderr)
→ pack_artifacts(workspace) → zip [script.py + output.txt + round_*.py]
→ send_zip_result()
→ keep_session_alive()
```
✅ Результат: `script_123.zip` [script.py + output.txt (+ round_*.py если был autofix)]

---

### Сценарий 4: «сгенерируй 100 паролей от 10 до 20 символов»
```
detect_task_type → "script" (ключевое слово "паролей")
→ _run_script_agent()
→ _generate_code(
    "Напиши Python-код: сгенерируй 100 паролей от 10 до 20 символов"
  ) → script.py [import random, string; for i in range(100): print(pwd)]
→ _run_code_in_sandbox() → stdout = "abc123...\nXyz987...\n..." (100 паролей)
→ save_output(workspace, stdout=100_passwords)
→ pack_artifacts(workspace) → zip [script.py + output.txt]
→ send_zip_result()
→ keep_session_alive()
```
✅ Результат: `script_123.zip` [script.py + output.txt с 100 паролями]

---

## 4. Что изменилось в файлах

| Файл | Статус | Ключевые изменения |
|------|--------|--------------------|
| `agent_utils.py` | 🆕 НОВЫЙ | create_workspace, pack_artifacts, send_zip_result, keep_session_alive, detect_task_type |
| `keyboards.py` | ✏️ ПЕРЕПИСАН | Единые кнопки: session_wait, session_files, agent_running, main_menu |
| `agent_session.py` | ✏️ ПЕРЕПИСАН | Stage.WAIT_NEXT, единый _run_agent(), handle_document(), handle_callback() |
| `chat_agent.py` | ✏️ ПЕРЕПИСАН | _run_fix_agent сохраняет раунды, _run_project_agent создаёт zip, единый pack_artifacts |
| `agent_coder3.py` | ✏️ ПЕРЕПИСАН | Все режимы создают zip, GUI-детект, autofix сохраняет раунды |

---

## 5. Правила интеграции

### Как зарегистрировать новый агент:
```python
from agent_session import register_agent, SessionState
from agent_utils import pack_artifacts, save_output

@register_agent("my_task_type")
async def run_my_agent(bot, state: SessionState):
    workspace = state.workspace  # уже создан agent_session
    
    # ... логика агента ...
    result = "output"
    
    # Обязательно:
    save_output(workspace, stdout=result)
    zip_path = pack_artifacts(workspace, zip_name="my_result.zip")
    return zip_path, "✅ Готово"
```

### Правило zip:
> Каждый агент **ОБЯЗАН** вернуть `(zip_path, caption)`.  
> Если агент упал — `agent_session` упаковывает workspace сам.  
> zip всегда содержит `output.txt`.

---

## 6. Известные ограничения

- `llm_client.py` — заглушка, подключить реальный провайдер.
- Sandbox не изолирован на уровне OS (нет Docker/seccomp) — для продакшена нужна доработка `python_sandbox.py`.
- `MAX_ZIP_SIZE_BYTES = 50MB` — для больших проектов нужен tunnel (Cloudflare/ngrok).
- Desktop-агент (`desktop/`) не включён в унификацию — отдельная задача.
