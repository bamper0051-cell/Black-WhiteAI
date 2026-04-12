# Руководство по интеграции исправлений AGENT_SMITH v2

## Быстрый старт — что заменить

### Шаг 1: Скопировать новые файлы

```bash
# Из папки agent_smith_fix/ → в корень AGENT_SMITH_v1_telegram/
cp agent_utils.py      ../AGENT_SMITH_v1_telegram/
cp keyboards.py        ../AGENT_SMITH_v1_telegram/
cp agent_session.py    ../AGENT_SMITH_v1_telegram/
cp chat_agent.py       ../AGENT_SMITH_v1_telegram/
cp agent_coder3.py     ../AGENT_SMITH_v1_telegram/
cp python_sandbox.py   ../AGENT_SMITH_v1_telegram/
cp pipeline.py         ../AGENT_SMITH_v1_telegram/
cp bot.py              ../AGENT_SMITH_v1_telegram/
cp coder3_autofix.py   ../AGENT_SMITH_v1_telegram/coder3/autofix.py
```

### Шаг 2: Подключить llm_client

В `llm_client.py` должна быть функция `get_llm_client()`:

```python
# llm_client.py — пример интерфейса
class LLMClient:
    async def complete(self, prompt: str) -> str:
        ...  # вызов OpenAI/Anthropic/Ollama

def get_llm_client() -> LLMClient:
    return LLMClient()
```

Все агенты используют `from llm_client import get_llm_client` — совместимо с существующим кодом.

### Шаг 3: Настроить .env

```env
BOT_TOKEN=ваш_токен_бота
WORKSPACE_BASE=/tmp/agent_workspaces   # или любой путь
```

### Шаг 4: Запустить бота

```bash
cd AGENT_SMITH_v1_telegram
python bot.py
```

---

## Изменения в архитектуре

### До исправлений:
```
bot.py → chat_agent.py → (своя логика zip / отправки)
bot.py → agent_coder3.py → (своя логика zip / отправки)
bot.py → agent_session.py → (своя логика zip / отправки)
# ↑ Три разные реализации, несовместимые поведения
```

### После исправлений:
```
bot.py → pipeline.py → agent_session._run_agent()
                              ↓
                    agent_utils.pack_artifacts()
                    agent_utils.send_zip_result()
                    agent_utils.keep_session_alive()
                              ↓
              chat_agent / agent_coder3 (только логика генерации)
```

---

## Регистрация нового агента

```python
# my_agent.py
from agent_session import register_agent, SessionState
from agent_utils import pack_artifacts, save_output
from aiogram import Bot

@register_agent("my_task")   # ← совпадает с detect_task_type() результатом
async def run_my_agent(bot: Bot, state: SessionState) -> tuple:
    workspace = state.workspace

    # 1. Делаем работу
    result_text = "Hello, world!"
    output_file = workspace / "result.txt"
    output_file.write_text(result_text)

    # 2. Сохраняем вывод (обязательно)
    save_output(workspace, stdout=result_text)

    # 3. Упаковываем zip (обязательно)
    zip_path = pack_artifacts(workspace, zip_name="my_result.zip")

    # 4. Возвращаем (zip_path, caption)
    return zip_path, "✅ My задача выполнена"
```

Затем в `pipeline.py` добавить импорт:
```python
import my_agent  # noqa — регистрирует агент через @register_agent
```

---

## Таблица маппинга типов задач

| Фраза в запросе | detect_task_type | Агент | Результат zip |
|-----------------|-----------------|-------|---------------|
| "напиши код", "скрипт", "генерируй" | `script` | chat_agent | script.py + output.txt |
| "100 паролей", "сгенерируй список" | `script` | chat_agent | script.py + output.txt (пароли внутри) |
| "телеграм бот", "парсер", "проект" | `project` | chat_agent | N файлов + README.md |
| "нарисуй", "анимация", "gif", "картинку" | `image` | agent_coder3 | solution.py + animation.gif |
| "проверь код", "ревью", "найди ошибки" | `review` | agent_coder3 | review_report.md |
| остальное | `quick` | chat_agent | solution.py + output.txt |

---

## Часто задаваемые вопросы

**Q: Агент не создаёт zip?**  
A: Убедитесь что агент возвращает `(zip_path, caption)`. Если нет — `agent_session._run_agent` сам вызовет `pack_artifacts(workspace)`.

**Q: Сессия закрывается сама?**  
A: Проверьте что нигде нет `clear_session(chat_id)` после выполнения. Сессия закрывается только по `/stop` или кнопке 🔴 Завершить.

**Q: Файл не попадает в zip?**  
A: Файл должен быть в `state.workspace`. Либо передавайте явный список `files=` в `pack_artifacts()`.

**Q: output.txt пустой?**  
A: Вызывайте `save_output(workspace, stdout=..., stderr=...)` перед `pack_artifacts()`.

**Q: Как добавить поддержку нового типа задачи?**  
A: Добавьте ключевые слова в `TASK_KEYWORDS` в `agent_utils.py` и зарегистрируйте агент через `@register_agent("тип")`.
