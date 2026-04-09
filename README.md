# BlackBugsAI — Multi-Agent Autonomous AI Platform

<div align="center">

```
██████╗ ██╗      █████╗  ██████╗██╗  ██╗    ██╗    ██╗██╗  ██╗██╗████████╗███████╗ █████╗ ██╗
██╔══██╗██║     ██╔══██╗██╔════╝██║ ██╔╝    ██║    ██║██║  ██║██║╚══██╔══╝██╔════╝██╔══██╗██║
██████╔╝██║     ███████║██║     █████╔╝     ██║ █╗ ██║███████║██║   ██║   █████╗  ███████║██║
██╔══██╗██║     ██╔══██║██║     ██╔═██╗     ██║███╗██║██╔══██║██║   ██║   ██╔══╝  ██╔══██║██║
██████╔╝███████╗██║  ██║╚██████╗██║  ██╗    ╚███╔███╔╝██║  ██║██║   ██║   ███████╗██║  ██║██║
╚═════╝ ╚══════╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝     ╚══╝╚══╝ ╚═╝  ╚═╝╚═╝   ╚═╝   ╚══════╝╚═╝  ╚═╝
```

**Автономная мультиагентная AI-платформа с Telegram-интерфейсом**

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED.svg)](https://www.docker.com)
[![License](https://img.shields.io/badge/License-Apache%202.0-green.svg)](LICENSE)
[![LLM](https://img.shields.io/badge/LLM-30%2B%20providers-purple.svg)](#llm-providers)

</div>

---

## Что это?

**BlackBugsAI** — это самоуправляемая AI-платформа, которая:

- Запускает автономных агентов (NEO, MATRIX, Coder3) для решения сложных задач
- Поддерживает 30+ LLM-провайдеров (OpenAI, Anthropic, Groq, Mistral, Google и др.)
- Управляется через Telegram-бота и веб-панель администратора
- Генерирует собственные инструменты по запросу (self-tool-generating)
- Имеет встроенную очередь задач, биллинг, роли пользователей, авто-исправление кода

---

## Архитектура

```
┌─────────────────────────────────────────────────────────┐
│                    BlackBugsAI Platform                  │
├─────────────────┬───────────────────┬───────────────────┤
│  Telegram Bot   │   Admin Web Panel │  Flutter Android  │
│   (bot.py)      │  (admin_web.py)   │      App          │
│   Port: -       │   Port: 8080      │   Mobile UI       │
├─────────────────┴───────────────────┴───────────────────┤
│                    Agent Orchestra                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐  │
│  │ AGENT    │  │ AGENT    │  │ CODER 3  │  │ CHAT   │  │
│  │  NEO     │  │ MATRIX   │  │          │  │ AGENT  │  │
│  └──────────┘  └──────────┘  └──────────┘  └────────┘  │
├─────────────────────────────────────────────────────────┤
│                    Core Services                        │
│  Task Queue │ Auth & Roles │ Billing │ Session Mgmt     │
├─────────────────────────────────────────────────────────┤
│                    LLM Router                           │
│  OpenAI │ Anthropic │ Groq │ Mistral │ Google │ +25    │
├─────────────────────────────────────────────────────────┤
│                    Storage                              │
│     SQLite (tasks, users, artifacts, sessions)          │
└─────────────────────────────────────────────────────────┘
```

---

## Быстрый старт

### Docker (рекомендуется)

```bash
# 1. Клонировать репозиторий
git clone https://github.com/bamper0051-cell/black-whiteai.git
cd black-whiteai

# 2. Создать файл конфигурации
cp .env.example .env
# Отредактировать .env — добавить токены API

# 3. Запустить
docker-compose up -d

# 4. Проверить статус
docker-compose logs -f
```

### Локально (Python)

```bash
# Зависимости
pip install -r requirements.txt

# Запуск
python main.py
```

### Linux/Mac инициализация
```bash
chmod +x init.sh && ./init.sh
```

### Windows
```bat
init.bat
```

---

## Конфигурация

Создайте файл `.env` в корне проекта:

```env
# === Telegram ===
BOT_TOKEN=your_telegram_bot_token
ADMIN_IDS=123456789,987654321

# === LLM Providers (минимум один) ===
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GROQ_API_KEY=gsk_...
MISTRAL_API_KEY=...
GOOGLE_API_KEY=...

# === Admin Web Panel ===
ADMIN_WEB_TOKEN=your_secret_admin_token
ADMIN_WEB_PORT=8080

# === Optional ===
USE_PROXY=false
AUTO_TUNNEL=false        # Cloudflare tunnel
DATA_DIR=/app/data
```

---

## Агенты

### AGENT NEO
Автономный агент, генерирующий инструменты на лету.

- Декомпозирует задачи на под-задачи
- Создаёт отсутствующие инструменты через SMITH-шаблоны
- Сохраняет результаты в ZIP-артефактах (код + входные данные + результат + TTS + логи)
- Поддерживает гибридный LLM (function-calling или JSON)

**Воркспейс:** `/app/neo_workspace/`

### AGENT MATRIX
Универсальный самоэволюционирующий агент с ролями.

**Роли:** Кодер | Тестировщик | OSINT-аналитик | Аналитик безопасности

- Устанавливает инструменты с GitHub
- Генерирует недостающие инструменты через LLM
- ZIP-артефакты на выходе

**Воркспейс:** `/app/matrix_workspace/`

### AGENT CODER 3
Специализированный агент генерации и исполнения кода.

- Поддержка нескольких LLM-провайдеров
- Авто-исправление: до 15 попыток
- Песочница Python для безопасного исполнения

### CHAT AGENT
Разговорный AI-интерфейс с вызовом инструментов и управлением сессиями.

---

## Цикл Plan → Execute → Observe → Fix

```
┌─────────────────────────────────────────────────────┐
│                   Жизненный цикл задачи              │
│                                                     │
│   PLAN ──────► EXECUTE ──────► OBSERVE              │
│     ▲              │               │                │
│     │              │               ▼                │
│     └──── LEARN ◄── FIX ◄──── FAILED?               │
│                                   │                 │
│                                   ▼ (нет)           │
│                                 DONE ✅              │
└─────────────────────────────────────────────────────┘

task_queue.py: pending → running → done/failed
autofix.py:    при failed → анализ → патч → retry (до max_retries)
```

---

## Веб-панель администратора

Доступна на `http://localhost:8080` после запуска.

Возможности:
- Мониторинг задач в реальном времени
- Управление пользователями и ролями
- Просмотр артефактов агентов
- Управление LLM-провайдерами
- Логи и статистика системы
- Выполнение shell-команд (только admin)

Авторизация: Bearer-токен (`ADMIN_TOKEN` из `.env`)

---

## LLM Providers

| Провайдер | Модели | Статус |
|-----------|--------|--------|
| OpenAI | GPT-4o, GPT-4-turbo, GPT-3.5 | ✅ |
| Anthropic | Claude 3.5, Claude 3 | ✅ |
| Groq | Llama3, Mixtral | ✅ |
| Mistral | Mistral-large, Codestral | ✅ |
| Google | Gemini Pro, Gemini Flash | ✅ |
| Ollama | Локальные модели | ✅ |
| + 25 других | — | ✅ |

---

## Возможности

| Функция | Описание |
|---------|----------|
| Multi-LLM | Роутинг между 30+ провайдерами с фолбэком |
| Self-Healing | Агенты автогенерируют недостающие инструменты |
| Code Sandbox | Безопасное выполнение кода с авто-исправлением |
| Billing | Многоуровневые тарифы: free/pro/business/enterprise |
| Admin Panel | Веб-дашборд с REST API |
| Telegram Bot | Полноценный интерфейс для конечных пользователей |
| Media Gen | Изображения, TTS, видео |
| Sessions | Постоянные сессии на SQLite |
| RBAC | Роли и права пользователей |
| Task Queue | Асинхронная очередь с повторами и артефактами |
| OSINT | Сканирование портов, сетевой анализ |
| Tunnel | Cloudflare/Bore туннели (AUTO_TUNNEL=true) |

---

## Структура проекта

```
Black-WhiteAI/
├── main.py                  # Точка входа
├── bot.py                   # Ядро Telegram-бота (9K+ строк)
├── bot_main.py              # Инициализация бота
├── config.py                # Конфигурация и env-переменные
├── requirements.txt         # Зависимости Python
├── Dockerfile               # Docker-образ
├── docker-compose.yml       # Оркестрация сервисов
├── .env.example             # Пример конфигурации
│
├── agents/                  # Агентная система
│   ├── agent_neo.py         # AGENT NEO
│   ├── agent_matrix.py      # AGENT MATRIX
│   ├── chat_agent.py        # Chat Agent
│   ├── agent_coder3.py      # Coder 3
│   ├── agent_planner.py     # Планировщик задач
│   ├── agent_memory.py      # Память агентов
│   └── agent_executor.py    # Исполнитель инструментов
│
├── admin_web.py             # REST API + веб-панель
├── admin_panel.html         # Дашборд (HTML)
│
├── task_queue.py            # Очередь задач
├── autofix.py               # Авто-исправление ошибок
├── llm_router.py            # Роутер LLM-провайдеров
├── auth_module.py           # Аутентификация
├── billing.py               # Биллинг
│
├── android_app/             # Flutter Android-приложение
│   ├── lib/                 # Dart-код
│   ├── pubspec.yaml         # Зависимости Flutter
│   └── README.md            # Документация приложения
│
├── tests/                   # Тесты
│   ├── test_agents.py
│   └── test_admin_web.py
│
└── docs/
    ├── AGENTS.md            # Документация агентов
    └── API.md               # REST API документация
```

---

## Запуск тестов

```bash
# Все тесты
python -m pytest tests/ -v

# Тесты агентов
python -m pytest tests/test_agents.py -v

# Тесты API
python -m pytest tests/test_admin_web.py -v
```

---

## Docker

```bash
# Сборка образа
docker build -t blackbugsai .

# Запуск с docker-compose
docker-compose up -d

# Перезапуск после изменений
docker-compose down && docker-compose up -d --build

# Просмотр логов
docker-compose logs -f --tail=100

# Подключение к контейнеру
docker exec -it automuvie bash
```

---

## Mobile App (Flutter Android)

Приложение для управления BlackBugsAI с мобильного устройства.

- Дашборд с мониторингом агентов в реальном времени
- Управление задачами (создание, отмена, повтор)
- Просмотр артефактов и результатов
- Neon-дизайн с анимациями
- WebSocket для live-обновлений

Подробнее: [android_app/README.md](android_app/README.md)

### Подключение Android App к GCP серверу

1. **На GCP VM запустите проверку сервера**:
   ```bash
   cd ~/Black-WhiteAI
   ./verify_server.sh
   ```
   Скрипт покажет внешний IP, порт и токен для подключения.

2. **Настройте firewall на GCP**:
   ```bash
   gcloud compute firewall-rules create allow-admin-panel \
     --allow tcp:8080 \
     --source-ranges 0.0.0.0/0 \
     --description "Allow BlackBugsAI Admin Panel"
   ```

3. **В Android app введите**:
   - **GCP SERVER IP**: ваш внешний IP (например, `34.XX.XX.XX`)
   - **DOCKER PORT**: `8080`
   - **ADMIN TOKEN**: значение `ADMIN_WEB_TOKEN` из `.env`
   - **USE HTTPS**: выключено (OFF)

4. **Нажмите "ТЕСТ"** для проверки соединения

**Не работает?** См. полное руководство: [TROUBLESHOOTING_ANDROID_CONNECTION.md](TROUBLESHOOTING_ANDROID_CONNECTION.md)

---

## Лицензия

[Apache 2.0](LICENSE) — © 2024 BlackBugsAI

---

## Контрибьюторство

1. Fork репозитория
2. Создайте ветку: `git checkout -b feature/amazing-feature`
3. Commit: `git commit -m 'Add amazing feature'`
4. Push: `git push origin feature/amazing-feature`
5. Откройте Pull Request

---

> **Важно:** Инструменты OSINT и тестирования безопасности предназначены **только для авторизованного тестирования**. Использование в незаконных целях запрещено.
