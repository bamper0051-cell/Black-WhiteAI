# AGENT_SMITH — Patch Notes v4

## Файлы

### roles.py — Role System v3 (полная пересборка)

**Новая роль PRO** (между VIP и USER).

**Матрица привилегий:**

| Роль | Задач/день | Токенов | Файл МБ | Авто-фиксов | Sandbox |
|------|-----------|---------|---------|-------------|---------|
| god  | ∞         | ∞       | 500     | 20          | 120с    |
| adm  | ∞         | 32 000  | 200     | 15          | 90с     |
| vip  | 500       | 16 000  | 100     | 15          | 60с     |
| pro  | 200       | 8 000   | 50      | 10          | 45с     |
| user | 50        | 4 000   | 20      | 6           | 30с     |
| noob | 10        | 2 000   | 5       | 3           | 15с     |
| ban  | 0         | 0       | 0       | 0           | 0с      |

**Доступ к CODER3/СМИТ:**
- noob  → только `coder3_quick`
- user  → `coder3_quick` + `coder3_sandbox` + `smith_agent`
- pro   → все режимы CODER3 + SMITH basic (без шаблонов/custom)
- vip+  → всё включая `smith_templates`, `smith_custom`, `agent_0051`

**Новые функции:**
- `get_limits(role)` → dict с лимитами
- `get_limit(role, key)` → конкретный лимит
- `get_restrictions(role)` → список запрещённых прав
- `roles_summary()` → HTML-таблица для /roles
- `user_card(role)` → карточка прав для конкретной роли
- `perm_denied_msg()` теперь показывает минимальную роль для апгрейда

### agent_roles.py — RBAC адаптер v3

Новые хелперы:
- `get_sandbox_timeout(chat_id)` — таймаут sandbox по роли
- `get_fix_attempts(chat_id)` — кол-во попыток авто-фикса по роли
- `get_max_tokens(chat_id)` — лимит токенов по роли
- `get_max_file_mb(chat_id)` — лимит файла по роли
- `coder3_perm(mode, chat_id)` — проверка права режима CODER3
- `smith_perm(chat_id, ...)` — проверка прав АГЕНТ_СМИТ

### bot.py — Fix: UnboundLocalError get_system_info

**Баг:** `❌ Callback error [adm:sysinfo]: cannot access local variable
'get_system_info' where it is not associated with a value`

**Причина:** В функции `_route_callback` на строке ~6092 был локальный импорт:
```python
from admin_module import get_system_info  # ← делает ВСЕ вхождения локальными
```
Python обнаруживал этот локальный импорт и помечал `get_system_info`
как локальную переменную во ВСЕЙ функции — поэтому использование на
строке ~5142 (до импорта) падало с `UnboundLocalError`.

**Исправление:** Удалён дублирующий локальный `from admin_module import
get_system_info`. Функция теперь использует глобальный импорт из строки 30.
