<div align="center">

```
 ██████╗ ██╗      █████╗  ██████╗██╗  ██╗██████╗ ██╗   ██╗ ██████╗ ███████╗ █████╗ ██╗
 ██╔══██╗██║     ██╔══██╗██╔════╝██║ ██╔╝██╔══██╗██║   ██║██╔════╝ ██╔════╝██╔══██╗██║
 ██████╔╝██║     ███████║██║     █████╔╝ ██████╔╝██║   ██║██║  ███╗███████╗███████║██║
 ██╔══██╗██║     ██╔══██║██║     ██╔═██╗ ██╔══██╗██║   ██║██║   ██║╚════██║██╔══██║██║
 ██████╔╝███████╗██║  ██║╚██████╗██║  ██╗██████╔╝╚██████╔╝╚██████╔╝███████║██║  ██║██║
 ╚═════╝ ╚══════╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝╚═════╝  ╚═════╝  ╚═════╝ ╚══════╝╚═╝  ╚═╝╚═╝
```

**Autonomous AI Agent Platform**

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED.svg)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Brand](https://img.shields.io/badge/Brand-BlackBugsAI-black.svg)](https://blackbugsai.com)

</div>

---

## 🖤 Что это

**BlackBugsAI** — автономная AI-платформа с marketplace инструментов.
Пользователь описывает задачу → агент планирует → инструменты выполняют → результат в Telegram.

---

## 🏗 Архитектура

```
┌─────────────────────────────────────────────────────────┐
│                    INTERFACE LAYER                       │
│  Telegram Bot  │  REST API  │  Web Admin Dashboard      │
│  (принять, показать статус, вернуть результат)          │
└────────────────────┬────────────────────────────────────┘
                     ↓ Task
┌─────────────────────────────────────────────────────────┐
│                    AGENT CORE                           │
│  Planner → Executor → Memory → Tool Router             │
│  (думает, планирует, координирует, помнит)             │
└────────────────────┬────────────────────────────────────┘
                     ↓ Tool calls
┌─────────────────────────────────────────────────────────┐
│                    TOOL LAYER                           │
│  TTS │ STT │ Video │ Code │ Shell │ Web │ Files │ PDF   │
│  (выполняет конкретные действия)                       │
└────────────────────┬────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────┐
│                   INFRASTRUCTURE                        │
│  SQLite/Postgres │ Queue │ Auth │ Billing │ Proxy/Tor   │
│  (хранит, очередь, авторизует, тарифицирует)           │
└─────────────────────────────────────────────────────────┘
```

### Директории

```
blackbugsai/
├── app/
│   ├── interfaces/
│   │   ├── telegram/      # handlers, keyboards, commands
│   │   ├── api/           # REST API endpoints
│   │   └── web/           # Admin dashboard (Flask)
│   ├── agent/
│   │   ├── core/          # AgentCore — главная точка входа
│   │   ├── planner/       # Planner — анализ и план
│   │   ├── executor/      # Executor — выполнение шагов
│   │   ├── memory/        # Memory — история и контекст
│   │   └── sessions/      # SessionManager
│   ├── tools/
│   │   ├── media/         # TTS, STT, Video, Image
│   │   ├── code/          # Python sandbox, Code agent
│   │   ├── system/        # Shell, Files, ZIP
│   │   └── network/       # Web fetch, Proxy/Tor
│   ├── auth/              # JWT, RBAC, Billing
│   ├── db/                # DB models, migrations
│   ├── queue/             # Task queue workers
│   ├── config/            # settings.py, .env
│   └── logs/              # Structured logging
├── plugins/               # Пользовательские инструменты
├── data/                  # БД, артефакты, логи
├── docker-compose.yml
├── Dockerfile
├── .env.example
└── README.md
```

---

## 💰 Монетизация

| Тариф | Цена | Задач/день | Инструменты |
|-------|------|-----------|-------------|
| 🆓 Free | $0 | 10 | Базовые |
| ⭐ Pro | $9.99/мес | 100 | Все |
| 🚀 Business | $49.99/мес | ∞ | Все + API + White-label |
| 🏢 Enterprise | По договору | ∞ | Всё + SLA + кастом |

**Варианты:**
- **Кредиты** — купи пачку, трать на инструменты
- **Подписка** — ежемесячно, безлимит в рамках плана
- **White-label** — ставишь платформу клиенту, подключаешь кастомные инструменты
- **Dev Ecosystem** — другие разработчики пишут плагины, получают % от запусков

---

## 🛠 Tool Marketplace

Каждый инструмент описывается схемой:

```python
@register_tool(
    name="tts",
    description="Синтез речи из текста",
    category="media",
    permissions=["user"],
    timeout=30,
    cost=0.1,           # кредитов за запуск
    sandbox=SandboxLevel.SOFT,
    tags=["voice", "audio"],
    input_schema={"properties": {"text": {}, "voice": {}}, "required": ["text"]}
)
def tool_tts(args, chat_id=None, on_status=None): ...
```

### Категории инструментов

| Категория | Инструменты |
|-----------|-------------|
| 🎵 Media | TTS, STT, Video edit, Image gen, Subtitles |
| 💻 Code | Python sandbox, Code agent (patch/scaffold), Linter |
| ⚙️ System | Shell, File manager, ZIP builder, Dependency checker |
| 🌐 Network | Web fetch, Scraper, Proxy/Tor |
| 📄 Productivity | PDF export, Report generator, Summary |
| 🤖 Bot infra | Create bot, Create command, Docker helper |

---

## 🤖 Multi-Agent система

```
Задача: "Исследуй рынок, напиши отчёт, озвучь и пришли PDF"
         ↓
Orchestrator Agent
    ├── Research Agent → web_search, fetch_url
    ├── Analysis Agent → summarize, structure
    ├── Voice Agent    → tts
    └── Report Agent   → pdf_export, telegram_send
```

---

## 🔒 Безопасность

- Токены только в `.env`, никогда в коде
- Sandbox изолирован (Docker или restricted Python)
- Опасные инструменты отключены для `user`/`vip`
- JWT авторизация для API
- Rate limiting по IP и user_id
- Прокси/Tor для анонимности исходящих запросов

---

## 🚀 Быстрый старт

```bash
# 1. Клонировать
git clone https://github.com/blackbugsai/platform

# 2. Настроить
cp .env.example .env
# Заполнить TELEGRAM_BOT_TOKEN, LLM_API_KEY, ADMIN_IDS

# 3. Запустить
docker compose up -d

# 4. Открыть панель
# http://localhost:8080/panel
```

---

## 🆕 Уникальные фишки

1. **Code Agent Pipeline** — анализ → план → код → тест → diff → rollback
2. **Agent Memory** — помнит задачи и предпочтения пользователя
3. **Tool Marketplace** — плагины с метаданными, правами, лимитами
4. **Multi-Agent** — параллельные агенты для сложных задач
5. **Plan-First Mode** — показывает план до выполнения
6. **Proxy/Tor** — анонимность для веб-запросов
7. **Billing в Telegram** — оплата через Telegram Stars
8. **White-label** — платформа под брендом клиента

---

<div align="center">
Made with 🖤 by <b>BlackBugsAI</b>
</div>
