# AGENT_SMITH — Patch Notes v2

## Новые и изменённые файлы

### roles.py — Role System v3
- Добавлена роль **PRO** (между VIP и USER)
- Новые разрешения для AGENT_CODER3: `coder3_quick`, `coder3_autofix`,
  `coder3_project`, `coder3_sandbox`, `coder3_review`
- Новые разрешения для АГЕНТ_СМИТ: `smith_templates`, `smith_custom`,
  `agent_pipeline`
- Лимиты токенов на задачу (`TOKEN_LIMITS`)
- Функция `roles_table()` для команды /roles
- Матрица прав:
  - noob  → только `coder3_quick`, чат
  - user  → coder3 basic (quick+sandbox), smith_agent
  - pro   → coder3 full + smith basic
  - vip   → всё + smith full + agent_0051
  - adm   → всё + admin панель
  - god   → всё без ограничений

### agent_roles.py — RBAC адаптер v3
- Функции `coder3_perm(mode, chat_id)` — проверка права режима
- Функция `smith_perm(chat_id, ...)` — проверка прав АГЕНТ_СМИТ
- Функция `get_user_limits(chat_id)` — лимиты пользователя
- Обратная совместимость с auth_module

### agent_coder3.py — Полная пересборка (v2)
**Новая архитектура:**
- AGENT_CODER3 = оркестратор, анализирует запрос и выбирает шаблон
- АГЕНТ_СМИТ = исполнитель, получает шаблон и генерирует код
- Режимы quick/project → делегируются АГЕНТ_СМИТ
- Режимы autofix/review/sandbox → coder3/engine

**SMITH_TEMPLATES — 14 шаблонов:**
  📜 script          — Python-скрипт
  🔧 util            — Утилита с CLI
  🤖 telegram_bot    — Telegram-бот (aiogram/telebot)
  🎮 discord_bot     — Discord-бот
  ⚡ fastapi         — FastAPI сервис
  🌶 flask           — Flask-приложение
  🕷 scraper         — Парсер/скрейпер
  📊 data_pipeline   — Data pipeline (pandas/polars)
  🧠 llm_tool        — LLM-инструмент (OpenAI/Anthropic/Gemini)
  🖼 image_tool      — Работа с изображениями (Pillow)
  🎬 animation       — Анимация/GIF
  🗄 db_tool         — Работа с БД (SQLite/PostgreSQL/MongoDB)
  ⚙️ automation      — Автоматизация (schedule/watchdog)
  🏗 project_scaffold — Scaffold проекта
  🖥 cli_app         — CLI-приложение (rich/typer/click)
  🔐 crypto_tool     — Крипто/безопасность

**Пайплайн:**
  1. _route_to_mode()  — определяет режим (quick/autofix/project/...)
  2. _select_template() — выбирает шаблон СМИТ по тексту задачи
  3. Проверка прав роли (coder3_perm)
  4. _run_via_smith() — создаёт AgentSession, передаёт шаблон как system-промпт
  5. execute_pipeline() возвращает zip
  6. ZIP отправляется через send_document
  7. Сессия продолжается (кнопка СТОП)

### coder3/engine.py
- Незначительные улучшения валидации
- Лучшая обработка zip-артефактов

---
*Предыдущие патчи (v1) включены в этот архив как актуальные версии файлов.*
