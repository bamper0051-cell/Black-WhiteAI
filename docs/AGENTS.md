# BlackBugsAI — Документация агентов

## Содержание

1. [Обзор агентной системы](#обзор)
2. [AGENT NEO](#agent-neo)
3. [AGENT MATRIX](#agent-matrix)
4. [AGENT CODER 3](#agent-coder-3)
5. [CHAT AGENT](#chat-agent)
6. [Архитектура агентов](#архитектура)
7. [Цикл Plan→Execute→Observe→Fix→Learn](#цикл)
8. [Tool Registry](#tool-registry)
9. [Добавление нового агента](#добавление-агента)

---

## Обзор

BlackBugsAI использует мультиагентную архитектуру, где каждый агент специализируется на определённых задачах. Агенты могут вызывать инструменты (tools), генерировать собственные инструменты, работать с файловой системой и взаимодействовать с LLM-провайдерами.

```
Пользователь
     │
     ▼
Telegram Bot / Web API
     │
     ▼
 ┌───────────────────────────────────┐
 │         Agent Orchestra           │
 │  ┌─────┐ ┌──────┐ ┌──────┐ ┌───┐ │
 │  │ NEO │ │MATRIX│ │CODE3 │ │CHT│ │
 │  └──┬──┘ └──┬───┘ └──┬───┘ └─┬─┘ │
 └─────┼────────┼─────────┼───────┼──┘
       ▼        ▼         ▼       ▼
    Tools    Tools     Tools   Tools
       │
       ▼
  LLM Router (30+ провайдеров)
```

---

## AGENT NEO

**Файл:** `agent_neo.py` (1,492 строки)

### Описание
Автономный агент с возможностью самогенерации инструментов. При отсутствии нужного инструмента NEO создаёт его сам с помощью SMITH-шаблонов.

### Возможности
- Декомпозиция сложных задач на подзадачи
- Динамическое создание инструментов через LLM
- ZIP-артефакты: `code + input + output + report + logs + tts`
- Гибридный режим LLM: function-calling и JSON-режим
- Изолированный воркспейс `/app/neo_workspace/`

### Воркспейс
```
/app/neo_workspace/
├── tools/        # Сгенерированные инструменты
├── artifacts/    # Результирующие ZIP-файлы
├── osint/        # OSINT-результаты
└── tmp/          # Временные файлы
```

### Запуск
```python
from agent_neo import NeoAgent

agent = NeoAgent(user_id="12345")
result = await agent.run("Проанализируй IP 8.8.8.8 и составь отчёт")
# → result: dict с полями result, artifacts, tools_used
```

### Конфигурация
```python
# В config.py или .env:
NEO_MAX_ITERATIONS = 10        # Максимум итераций
NEO_TOOL_TIMEOUT = 30          # Таймаут инструмента (сек)
NEO_WORKSPACE = "/app/neo_workspace"
```

### Архитектура NEO

```
Задача
  │
  ▼
SMITH (планировщик)
  │
  ├── Нужен инструмент?
  │   ├── Да → Генерация инструмента → Регистрация
  │   └── Нет → Использование существующего
  │
  ▼
Исполнение инструмента
  │
  ├── Ошибка? → AutoFix → Повтор (до 3 раз)
  └── Успех → Следующий шаг
  │
  ▼
ZIP-артефакт (результат + логи + TTS)
```

---

## AGENT MATRIX

**Файл:** `agent_matrix.py` (1,354 строки)

### Описание
Универсальный самоэволюционирующий агент с системой ролей. MATRIX может переключаться между ролями в зависимости от задачи и устанавливать инструменты с GitHub.

### Роли

| Роль | Описание | Ключевые инструменты |
|------|----------|---------------------|
| `coder` | Написание и рефакторинг кода | python_sandbox, git, pip |
| `tester` | Тестирование и QA | pytest, coverage, linter |
| `osint` | OSINT-анализ | nmap, whois, curl, dnslookup |
| `security` | Анализ безопасности | port_scanner, network_sniffer |

### Возможности
- Установка инструментов из GitHub (`git clone` + `pip install`)
- Генерация недостающих инструментов через LLM
- Ролевое переключение в процессе выполнения
- ZIP-артефакты аналогично NEO

### Воркспейс
```
/app/matrix_workspace/
├── tools/        # Сгенерированные инструменты
├── artifacts/    # Результаты
├── repos/        # Склонированные репозитории
└── sandbox/      # Изолированная среда
```

### Запуск
```python
from agent_matrix import MatrixAgent

agent = MatrixAgent(user_id="12345", role="coder")
result = await agent.run("Напиши unit-тесты для функции parse_json")
```

---

## AGENT CODER 3

**Файл:** `agent_coder3.py` (362 строки)

### Описание
Специализированный агент для генерации и выполнения кода с встроенным циклом авто-исправления.

### Особенности
- До 15 попыток авто-исправления при ошибке
- Поддержка нескольких LLM одновременно
- Python-песочница для безопасного исполнения
- Возврат файлов-артефактов

### Цикл авто-исправления
```
Задача
  │
  ▼
Генерация кода (LLM)
  │
  ▼
Запуск в песочнице
  │
  ├── Ошибка? ──► Анализ ошибки
  │                    │
  │               LLM генерирует патч
  │                    │
  │               Повтор (до 15 раз)
  │
  └── Успех → Возврат результата + файлов
```

### Запуск
```python
from agent_coder3 import run_coder3

result = run_coder3(
    user_id="12345",
    task="Напиши скрипт для парсинга CSV и построения графика",
    max_attempts=15
)
# result: { output, files, error, attempts }
```

---

## CHAT AGENT

**Файл:** `chat_agent.py` (2,472 строки)

### Описание
Разговорный агент с поддержкой tool-calling и управлением сессиями. Является основным интерфейсом для конечных пользователей.

### Возможности
- Персистентные сессии (SQLite)
- Вызов инструментов из Tool Registry
- Память разговора (история сообщений)
- Поддержка контекста пользователя

### API
```python
from chat_agent import start_session, chat_respond, is_active, stop_session

# Начало сессии
start_session(user_id, mode='chat')  # mode: chat | code | agent

# Ответ
response = chat_respond(user_id, "Привет! Как дела?")

# Проверка активности
active = is_active(user_id)

# Завершение
stop_session(user_id)
```

### Режимы работы

| Режим | Описание |
|-------|----------|
| `chat` | Обычный разговор |
| `code` | Фокус на генерации и исполнении кода |
| `agent` | Полноценный агент с инструментами |
| `neo` | Перенаправление в AGENT NEO |
| `matrix` | Перенаправление в AGENT MATRIX |

---

## Архитектура

### Компоненты агентной системы

```
agent_core.py        — Базовый класс агента
agent_executor.py    — Исполнитель инструментов
agent_planner.py     — Планировщик задач
agent_memory.py      — Управление памятью/состоянием
agent_roles.py       — Роли и права доступа
agent_session.py     — Управление сессиями
agent_tools_registry.py — Реестр инструментов
neo_tool_library.py  — Библиотека инструментов NEO
```

### Жизненный цикл агента

```python
# 1. Инициализация
agent = Agent(user_id, role, config)

# 2. Планирование
plan = await agent.plan(task)

# 3. Выполнение
for step in plan.steps:
    result = await agent.execute(step)

    # 4. Наблюдение
    obs = agent.observe(result)

    # 5. Исправление при ошибке
    if obs.needs_fix:
        patched = agent.fix(step, obs)
        result = await agent.execute(patched)

    # 6. Обучение
    agent.learn(step, result, obs)

# 7. Артефакты
zip_path = agent.package_artifacts()
```

---

## Цикл Plan→Execute→Observe→Fix→Learn

**Файл:** `plan_execute_cycle.py`

Центральный модуль для управления жизненным циклом задачи.

```python
from plan_execute_cycle import run_cycle

result = run_cycle(
    user_id="12345",
    task_description="Напиши и запусти скрипт hello world",
    context={"language": "python"},
    max_fix_attempts=3,
    llm_fn=my_llm_function,  # опционально
    progress_cb=lambda phase, step, msg: print(f"[{phase}] {step}: {msg}")
)

# result:
# {
#   "cycle_id": "abc12345",
#   "status": "done",      # done | partial | failed
#   "steps_total": 2,
#   "steps_done": 2,
#   "steps_failed": 0,
#   "results": [...],
#   "summary": "✅ Цикл abc12345: 2/2 шагов выполнено",
#   "artifacts": ["artifact_id_1"]
# }
```

### Статусы шагов

| Статус | Описание |
|--------|----------|
| `done` | Шаг выполнен успешно |
| `failed` | Шаг упал, исправление не помогло |
| `partial` | Часть шагов выполнена |

### База знаний (LEARN)

Система сохраняет успешные паттерны исправления:
```
knowledge.db
├── patterns       — Паттерны fix (task_type, error_sig, fix, success)
└── execution_log  — Лог всех выполнений
```

---

## Tool Registry

**Файл:** `agent_tools_registry.py` (1,937 строк)

Центральный реестр всех доступных инструментов с биллингом и правами доступа.

### Структура инструмента
```python
{
    "name": "tool_name",
    "description": "Описание инструмента",
    "category": "code | media | network | osint | utility",
    "requires_perm": "run_code | run_shell | osint | admin",
    "billing_cost": 1,  # токены
    "function": callable
}
```

### Регистрация нового инструмента
```python
from agent_tools_registry import register_tool

@register_tool(
    name="my_tool",
    description="Мой инструмент",
    category="utility",
    requires_perm=None,
    billing_cost=1,
)
def my_tool(args: dict, chat_id: str = None) -> str:
    result = args.get("input", "")
    return f"Результат: {result}"
```

---

## Добавление нового агента

### 1. Создайте файл агента

```python
# my_agent.py
"""
MyAgent — Описание агента
"""
from agent_core import BaseAgent

class MyAgent(BaseAgent):
    NAME = "MY_AGENT"
    DESCRIPTION = "Мой кастомный агент"
    WORKSPACE = "/app/my_workspace"

    async def plan(self, task: str) -> list:
        """Декомпозиция задачи."""
        return [{"name": "Step 1", "type": "chat", "payload": {"text": task}}]

    async def execute(self, step: dict) -> dict:
        """Выполнение шага."""
        # Ваша логика
        return {"success": True, "result": "Готово"}
```

### 2. Зарегистрируйте в bot.py

```python
# В bot.py найди список агентов и добавь:
from my_agent import MyAgent
AVAILABLE_AGENTS["my_agent"] = MyAgent
```

### 3. Добавьте команду Telegram

```python
# В bot_handlers.py:
@dp.message_handler(commands=['my_agent'])
async def cmd_my_agent(message: types.Message):
    agent = MyAgent(user_id=str(message.chat.id))
    result = await agent.run(message.text)
    await message.reply(result.get('summary', 'Готово'))
```

### 4. Тест агента

```python
# tests/test_my_agent.py
import pytest
from my_agent import MyAgent

@pytest.mark.asyncio
async def test_my_agent_basic():
    agent = MyAgent(user_id="test_user")
    result = await agent.run("Тестовая задача")
    assert result['success'] is True
```

---

## Советы и лучшие практики

### Логирование в агентах
```python
from structured_logger import get_logger
logger = get_logger(__name__)

logger.info("Agent started", extra={"user_id": user_id, "task": task[:50]})
logger.error("Step failed", extra={"step": step_name, "error": str(e)})
```

### Изоляция воркспейса
```python
import os
workspace = os.path.join("/app/my_workspace", str(user_id))
os.makedirs(workspace, exist_ok=True)
# Все файлы агента создавай только внутри workspace
```

### Авто-исправление ошибок
```python
from plan_execute_cycle import run_cycle

# Используй run_cycle вместо ручного цикла
result = run_cycle(user_id, task, max_fix_attempts=3)
```

### Биллинг
```python
from billing import charge_user, has_enough_credits

# Проверить баланс
if not has_enough_credits(user_id, cost=5):
    raise ValueError("Недостаточно токенов")

# Списать
charge_user(user_id, cost=5, reason="my_agent_run")
```
