# 🤖 АВТОМУВИ v4.4 — AI Telegram Bot Platform

> Автономный многорежимный ИИ-агент с LLM, TTS, Vision, Stable Diffusion, видеомонтажом,
> очередью задач, RBAC-правами, веб-панелью администратора и Docker-поддержкой.

---

## ⚡ Быстрый старт

```bash
# 1. Скопируй .env.example → .env и заполни токены
cp .env.example .env

# 2. Запусти init (создаёт нужные файлы)
init.bat          # Windows
./init.sh         # Linux

# 3. Docker
docker compose up -d

# 4. Открой Admin Panel
# http://localhost:8080/panel
```

---

## 📁 Структура

```
HACK_TOOLS/
├── bot.py                    # Главный файл, polling, роутинг
├── auth_module.py            # Авторизация: капча, регистрация, сессии
├── admin_module.py           # Shell, процессы, управление
├── admin_web.py              # REST API (порт 8080)
├── admin_panel.html          # Веб-панель (открыть в браузере)
├── chat_agent.py             # LLM чат, сессии (persistent в SQLite)
├── agent_tools_registry.py   # 20+ инструментов агента
├── agent_roles.py            # RBAC: роли, права, лимиты
├── task_queue.py             # Очередь задач + воркеры
├── user_settings.py          # Настройки по пользователю
├── structured_logger.py      # JSON логи + healthcheck
├── config.py                 # Конфигурация (читает .env)
├── database.py               # БД новостей
├── file_agent.py             # Анализ файлов
├── file_manager.py           # Файловый менеджер
├── fish_*.py                 # Веб-модуль (Flask, порт 5000)
├── Dockerfile                # Docker образ
├── docker-compose.yml        # Docker Compose
├── entrypoint.sh             # Точка входа Docker
├── .env.example              # Пример конфигурации
├── requirements.txt          # Python зависимости
└── init.bat / init.sh        # Первоначальная настройка
```

---

## 🔑 Конфигурация .env

```env
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
ADMIN_IDS=123456789

# LLM (хотя бы один)
OPENROUTER_API_KEY=sk-or-...
GROQ_API_KEY=gsk_...
GEMINI_API_KEY=AI...

# Admin Panel
ADMIN_WEB_PORT=8080
ADMIN_WEB_TOKEN=your_secret_token

# Vision (для анализа изображений)
OPENAI_API_KEY=sk-...        # GPT-4o Vision
ANTHROPIC_API_KEY=sk-ant-... # Claude Vision
# или GEMINI_API_KEY работает тоже

# WebUI (если используешь A1111)
WEBUI_URL=http://localhost:7860

# TTS
TTS_PROVIDER=edge
TTS_VOICE=ru-RU-DmitryNeural
```

---

## 🤖 Режимы агента

| Кнопка | Режим | Описание |
|--------|-------|----------|
| 🤖 AI Ассистент | `assistant` | Общие задачи, ответы на вопросы |
| ⚙️ AI DevOps | `devops` | Код, скрипты, автоматизация |
| ✍️ AI Content | `content` | Тексты, посты, копирайтинг |
| 🔄 AI Automation | `automation` | Боты, интеграции, задачи |
| 💻 Агент-Кодер | `code` | Написать/запустить/исправить код |
| 💬 ИИ Чат | `chat` | Свободный диалог |

---

## 🔧 Инструменты агента (20+)

| Инструмент | Описание |
|------------|----------|
| `tts` | Озвучка текста (edge-tts / ElevenLabs) |
| `generate_image` | Генерация изображений (4 провайдера) |
| `pollinations_image` | Бесплатная генерация Pollinations |
| `stable_diffusion` | Локальная генерация (diffusers) |
| `webui_generate` | Automatic1111 WebUI API |
| `analyze_image` | Vision: описание/OCR/объекты/QA |
| `vision_telegram` | Анализ фото из Telegram |
| `moviepy_edit` | Видеомонтаж (нарезка, склейка, TTS+видео) |
| `assemble_video` | Сборка видео через ffmpeg |
| `sandbox` | Запуск Python кода |
| `create_bot` | Создать нового Telegram-бота |
| `web_search` | Поиск в интернете |
| `fetch_url` | Скачать страницу |
| `create_file` | Создать файл |
| `install_package` | pip install |
| `self_improve` | Написать новый модуль для бота |
| `run_process` | Запустить скрипт фоново |
| `analyze_task` | Анализ + план выполнения |

---

## 👥 Роли и права

| Роль | Задач/день | Файлов | Агент | Код | Shell |
|------|-----------|--------|-------|-----|-------|
| 👤 user | 20 | 10MB | ✅ | ❌ | ❌ |
| 💎 vip | 100 | 50MB | ✅ | ✅ | ❌ |
| 🔑 admin | 500 | 200MB | ✅ | ✅ | ✅ |
| 👑 owner | ∞ | ∞ | ✅ | ✅ | ✅ |

---

## 🌐 Admin Panel

Открыть: `http://localhost:8080/panel`

- **Дашборд** — статус, пользователи, логи
- **Пользователи** — управление, роли, бан
- **Сообщения** — личные + рассылка
- **Инструменты** — запуск агента, MoviePy UI
- **Процессы** — список, Kill
- **Логи** — реал-тайм, авто-обновление
- **Shell** — команды на сервере
- **Настройки** — .env через форму

---

## 🐳 Docker

```powershell
# Первый раз
init.bat

# Запуск
docker compose up -d

# Логи
docker logs -f automuvie

# Пересборка (после смены Dockerfile/requirements)
docker build --no-cache -t automuvie .
docker compose up -d --force-recreate

# Обновление кода (без пересборки — файлы монтируются)
# Просто скопируй .py файлы в HACK_TOOLS и:
docker restart automuvie
```

---

## 📊 Healthcheck

```
GET http://localhost:8080/health
→ {"status":"ok","uptime":"0h5m30s","db":"ok"}

GET http://localhost:8080/ping
→ {"ok":true,"pong":true}
```

---

## 🔒 Безопасность

- Токены только в `.env`, никогда в коде
- `.env` в `.gitignore`
- Shell доступен только owner/admin
- Sandbox изолирован (30 сек таймаут)
- Vision провайдеры через официальные API
- RBAC: каждое право проверяется индивидуально

---

## 📝 Changelog

### v4.4
- Три типа агента (DevOps / Content / Automation)
- Очередь задач + воркеры
- Персистентные сессии (SQLite)
- RBAC роли и права
- Vision: анализ изображений (GPT-4o / Claude / Gemini)
- Stable Diffusion (diffusers)
- WebUI API (Automatic1111)
- MoviePy видеомонтаж
- Admin Panel с localStorage persistence
- Structured logging + healthcheck
- Docker healthcheck

