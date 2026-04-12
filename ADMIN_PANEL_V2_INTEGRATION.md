# ADMIN PANEL V2 — интеграция

## Что это
Новый модуль `admin_panel_ui.py`, который даёт удобную многофункциональную админ-панель:
- дашборд
- пользователи
- роли
- агенты
- задачи
- система
- логи
- безопасность
- конфиг
- инструменты
- обслуживание

## 1) Импорт в bot.py

```python
from admin_panel_ui import (
    build_admin_main,
    build_dashboard,
    build_users_panel,
    build_roles_panel,
    build_agents_panel,
    build_tasks_panel,
    build_system_panel,
    build_logs_panel,
    build_security_panel,
    build_config_panel,
    build_tools_panel,
    build_maintenance_panel,
)
```

## 2) Добавь новый callback-роутер в `_route_callback(...)`

```python
elif action == 'adm2':
    answer_callback(cb_id)

    # тут можно собрать реальные метрики из своих модулей
    stats = {
        "users_total": 0,
        "tasks_total": 0,
        "workers": "n/a",
        "queue_pending": 0,
        "llm": "n/a",
        "tts": "n/a",
        "by_role": {},
    }

    if arg in ('main', ''):
        text, markup = build_admin_main(chat_id, btn, kb, stats=stats, role='adm')
        try:
            edit_message(chat_id, msg_id, text, reply_markup=markup)
        except Exception:
            send_message(text, chat_id, reply_markup=markup)

    elif arg == 'dashboard':
        text, markup = build_dashboard(btn, kb, metrics=stats)
        try:
            edit_message(chat_id, msg_id, text, reply_markup=markup)
        except Exception:
            send_message(text, chat_id, reply_markup=markup)

    elif arg == 'users':
        preview = []
        text, markup = build_users_panel(btn, kb, preview=preview)
        try:
            edit_message(chat_id, msg_id, text, reply_markup=markup)
        except Exception:
            send_message(text, chat_id, reply_markup=markup)

    elif arg == 'roles':
        text, markup = build_roles_panel(btn, kb, role_stats=stats.get("by_role", {}))
        try:
            edit_message(chat_id, msg_id, text, reply_markup=markup)
        except Exception:
            send_message(text, chat_id, reply_markup=markup)

    elif arg == 'agents':
        text, markup = build_agents_panel(btn, kb)
        try:
            edit_message(chat_id, msg_id, text, reply_markup=markup)
        except Exception:
            send_message(text, chat_id, reply_markup=markup)

    elif arg == 'tasks':
        text, markup = build_tasks_panel(btn, kb, stats=stats)
        try:
            edit_message(chat_id, msg_id, text, reply_markup=markup)
        except Exception:
            send_message(text, chat_id, reply_markup=markup)

    elif arg == 'system':
        sysinfo = "Открой 'adm:sysinfo' для детальной информации."
        text, markup = build_system_panel(btn, kb, sysinfo=sysinfo)
        try:
            edit_message(chat_id, msg_id, text, reply_markup=markup)
        except Exception:
            send_message(text, chat_id, reply_markup=markup)

    elif arg == 'logs':
        text, markup = build_logs_panel(btn, kb)
        try:
            edit_message(chat_id, msg_id, text, reply_markup=markup)
        except Exception:
            send_message(text, chat_id, reply_markup=markup)

    elif arg == 'security':
        text, markup = build_security_panel(btn, kb)
        try:
            edit_message(chat_id, msg_id, text, reply_markup=markup)
        except Exception:
            send_message(text, chat_id, reply_markup=markup)

    elif arg == 'config':
        text, markup = build_config_panel(btn, kb)
        try:
            edit_message(chat_id, msg_id, text, reply_markup=markup)
        except Exception:
            send_message(text, chat_id, reply_markup=markup)

    elif arg == 'tools':
        text, markup = build_tools_panel(btn, kb)
        try:
            edit_message(chat_id, msg_id, text, reply_markup=markup)
        except Exception:
            send_message(text, chat_id, reply_markup=markup)

    elif arg == 'maintenance':
        text, markup = build_maintenance_panel(btn, kb)
        try:
            edit_message(chat_id, msg_id, text, reply_markup=markup)
        except Exception:
            send_message(text, chat_id, reply_markup=markup)

    elif arg == 'refresh':
        text, markup = build_admin_main(chat_id, btn, kb, stats=stats, role='adm')
        try:
            edit_message(chat_id, msg_id, text, reply_markup=markup)
        except Exception:
            send_message(text, chat_id, reply_markup=markup)
```

## 3) Кнопка входа
Добавь в нужное меню кнопку:

```python
btn("🛡 Админка v2", "adm2:main")
```

## 4) Что реально хорошо сделать дальше
- заполнять `stats` из `database.py`, `auth_module.py`, очереди задач и логов
- подключить реальные actions:
  - поиск пользователя
  - блок/разбан
  - бэкап базы
  - очистка темпа
  - просмотр traces AGENT_CODER3
