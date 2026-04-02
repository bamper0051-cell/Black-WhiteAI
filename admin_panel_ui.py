# admin_panel_ui.py
# -*- coding: utf-8 -*-
"""
Удобная и многофункциональная админ-панель для Telegram-бота.
Модуль не привязан жёстко к telebot/aiogram: он только формирует текст и кнопки.

Ожидает от проекта:
- btn(text, callback_data) -> button
- kb(*rows) -> reply_markup
"""

from datetime import datetime


def _safe_len(x):
    try:
        return len(x)
    except Exception:
        return 0


def _fmt_role_stats(by_role: dict | None) -> str:
    if not by_role:
        return "нет данных"
    parts = []
    for k, v in sorted(by_role.items()):
        parts.append(f"• {k}: {v}")
    return "\n".join(parts)


def build_admin_main(chat_id, btn, kb, stats=None, role='adm'):
    stats = stats or {}
    users_total = stats.get('users_total', 0)
    tasks_total = stats.get('tasks_total', 0)
    workers = stats.get('workers', 'n/a')
    queue_pending = stats.get('queue_pending', 'n/a')
    llm = stats.get('llm', 'unknown')
    tts = stats.get('tts', 'unknown')
    role_stats = _fmt_role_stats(stats.get('by_role', {}))

    text = (
        "🛡 <b>АДМИН-ПАНЕЛЬ v2</b>\n\n"
        f"👤 Роль: <b>{role}</b>\n"
        f"👥 Пользователи: <b>{users_total}</b>\n"
        f"📦 Задачи: <b>{tasks_total}</b>\n"
        f"🧵 Workers: <b>{workers}</b>\n"
        f"⏳ Queue pending: <b>{queue_pending}</b>\n"
        f"🧠 LLM: <code>{llm}</code>\n"
        f"🎙 TTS: <code>{tts}</code>\n\n"
        f"📊 <b>Роли:</b>\n{role_stats}\n\n"
        "Выбери раздел:"
    )
    markup = kb(
        [btn("📊 Дашборд", "adm2:dashboard"), btn("👥 Пользователи", "adm2:users")],
        [btn("🪪 Роли", "adm2:roles"), btn("🤖 Агенты", "adm2:agents")],
        [btn("📦 Задачи", "adm2:tasks"), btn("🖥 Система", "adm2:system")],
        [btn("📜 Логи", "adm2:logs"), btn("🔐 Безопасность", "adm2:security")],
        [btn("⚙️ Конфиг", "adm2:config"), btn("🧰 Инструменты", "adm2:tools")],
        [btn("🧹 Обслуживание", "adm2:maintenance"), btn("♻️ Обновить", "adm2:refresh")],
        [btn("◀️ Назад", "menu")],
    )
    return text, markup


def build_dashboard(btn, kb, metrics=None):
    metrics = metrics or {}
    text = (
        "📊 <b>Дашборд</b>\n\n"
        f"🕒 Время: <code>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</code>\n"
        f"👥 Пользователи: <b>{metrics.get('users_total', 0)}</b>\n"
        f"🟢 Активные сегодня: <b>{metrics.get('active_today', 0)}</b>\n"
        f"📦 Всего задач: <b>{metrics.get('tasks_total', 0)}</b>\n"
        f"⏳ В очереди: <b>{metrics.get('queue_pending', 0)}</b>\n"
        f"✅ Успешно: <b>{metrics.get('tasks_ok', 0)}</b>\n"
        f"❌ Ошибок: <b>{metrics.get('tasks_failed', 0)}</b>\n"
        f"🤖 Кодер2: <b>{metrics.get('coder2_runs', 0)}</b>\n"
        f"🛠 Кодер3: <b>{metrics.get('coder3_runs', 0)}</b>\n"
        f"🕵️ SMITH: <b>{metrics.get('smith_runs', 0)}</b>\n"
        f"💾 DB size: <b>{metrics.get('db_size', 'n/a')}</b>\n"
        f"🧵 Workers: <b>{metrics.get('workers', 'n/a')}</b>\n"
    )
    markup = kb(
        [btn("♻️ Обновить", "adm2:dashboard"), btn("📜 События", "adm2:logs_recent")],
        [btn("📦 Задачи", "adm2:tasks"), btn("🖥 Система", "adm2:system")],
        [btn("◀️ Админка", "adm2:main")],
    )
    return text, markup


def build_users_panel(btn, kb, preview=None):
    preview = preview or []
    lines = ["👥 <b>Пользователи</b>\n"]
    if not preview:
        lines.append("Пока пусто.")
    else:
        for u in preview[:10]:
            uid = u.get('id') or u.get('telegram_id') or u.get('user_id', '?')
            role = u.get('role') or u.get('privilege', 'user')
            name = u.get('username') or u.get('first_name') or 'без имени'
            lines.append(f"• <code>{uid}</code> @{name} — <b>{role}</b>")

    text = "\n".join(lines)
    markup = kb(
        [btn("🔍 Найти", "adm2:user_find"), btn("➕ Добавить/зарегистрировать", "adm2:user_add")],
        [btn("🪪 Назначить роль", "adm2:user_set_role"), btn("🚫 Блок/разбан", "adm2:user_ban")],
        [btn("📨 Рассылка", "adm2:broadcast"), btn("⭐ Рейтинг/штраф", "adm2:user_points")],
        [btn("♻️ Обновить", "adm2:users"), btn("◀️ Админка", "adm2:main")],
    )
    return text, markup


def build_roles_panel(btn, kb, role_stats=None):
    text = (
        "🪪 <b>Роли и права</b>\n\n"
        f"{_fmt_role_stats(role_stats or {})}\n\n"
        "Действия:"
    )
    markup = kb(
        [btn("👤 Назначить роль", "adm2:user_set_role"), btn("📋 Матрица прав", "adm2:roles_matrix")],
        [btn("🔰 Сбросить роль", "adm2:role_reset"), btn("🔒 Ограничения", "adm2:security")],
        [btn("◀️ Админка", "adm2:main")],
    )
    return text, markup


def build_agents_panel(btn, kb):
    text = (
        "🤖 <b>Управление агентами</b>\n\n"
        "Здесь можно запускать и контролировать режимы:\n"
        "• Кодер 1\n"
        "• Кодер 2\n"
        "• Кодер 3\n"
        "• AGENT_0051\n"
        "• AGENT SMITH\n"
    )
    markup = kb(
        [btn("🤖 Кодер 1", "adm2:agent_c1"), btn("🧩 Кодер 2", "adm2:agent_c2")],
        [btn("🛠 Кодер 3", "adm2:agent_c3"), btn("🕵️ AGENT_0051", "adm2:agent_0051")],
        [btn("🧠 SMITH", "adm2:agent_smith"), btn("📈 Статистика", "adm2:agent_stats")],
        [btn("◀️ Админка", "adm2:main")],
    )
    return text, markup


def build_tasks_panel(btn, kb, stats=None):
    stats = stats or {}
    text = (
        "📦 <b>Задачи и очередь</b>\n\n"
        f"⏳ В очереди: <b>{stats.get('queue_pending', 0)}</b>\n"
        f"🟡 В работе: <b>{stats.get('running', 0)}</b>\n"
        f"✅ Успешно: <b>{stats.get('ok', 0)}</b>\n"
        f"❌ Ошибок: <b>{stats.get('failed', 0)}</b>\n"
    )
    markup = kb(
        [btn("📜 Последние задачи", "adm2:tasks_recent"), btn("🧵 Workers", "adm2:tasks_workers")],
        [btn("⏹ Остановить task", "adm2:task_stop"), btn("🗑 Очистить очередь", "adm2:tasks_clear")],
        [btn("♻️ Обновить", "adm2:tasks"), btn("◀️ Админка", "adm2:main")],
    )
    return text, markup


def build_system_panel(btn, kb, sysinfo="Система недоступна"):
    text = (
        "🖥 <b>Система</b>\n\n"
        f"{sysinfo}"
    )
    markup = kb(
        [btn("📊 Sysinfo", "adm:sysinfo"), btn("📁 Диски", "adm2:system_disks")],
        [btn("🧠 Память", "adm2:system_mem"), btn("⚙️ Процессы", "adm2:system_proc")],
        [btn("🧵 Сервисы", "adm2:system_services"), btn("🐳 Docker", "adm2:system_docker")],
        [btn("◀️ Админка", "adm2:main")],
    )
    return text, markup


def build_logs_panel(btn, kb):
    text = (
        "📜 <b>Логи и аудит</b>\n\n"
        "• История команд\n"
        "• Ошибки\n"
        "• Последние callback\n"
        "• Agent traces\n"
        "• Security events\n"
    )
    markup = kb(
        [btn("📜 История команд", "adm:cmd_history"), btn("❌ Ошибки", "adm2:logs_errors")],
        [btn("🧠 Agent traces", "adm2:logs_agents"), btn("🔐 Security", "adm2:logs_security")],
        [btn("📦 Queue logs", "adm2:logs_queue"), btn("◀️ Админка", "adm2:main")],
    )
    return text, markup


def build_security_panel(btn, kb):
    text = (
        "🔐 <b>Безопасность</b>\n\n"
        "• PIN / капча\n"
        "• Блокировки\n"
        "• Штрафы\n"
        "• Роли / права\n"
        "• Опасные инструменты\n"
    )
    markup = kb(
        [btn("🔒 Заблокировать", "adm2:sec_block"), btn("🔓 Разблокировать", "adm2:sec_unblock")],
        [btn("💰 Штраф", "adm:set_fine"), btn("👤 Назначить роль", "adm:set_priv")],
        [btn("🧾 Audit", "adm2:logs_security"), btn("◀️ Админка", "adm2:main")],
    )
    return text, markup


def build_config_panel(btn, kb):
    text = (
        "⚙️ <b>Конфиг и окружение</b>\n\n"
        "• LLM/TTS\n"
        "• .env\n"
        "• API ключи\n"
        "• Флаги режима\n"
    )
    markup = kb(
        [btn("🗝 API ключи", "adm:show_keys"), btn("⚙️ .env", "adm:edit_env")],
        [btn("🧠 LLM", "menu_llm"), btn("🎙 TTS", "menu_tts")],
        [btn("◀️ Админка", "adm2:main")],
    )
    return text, markup


def build_tools_panel(btn, kb):
    text = (
        "🧰 <b>Инструменты</b>\n\n"
        "• Selfcheck\n"
        "• Sandbox\n"
        "• Agents test\n"
        "• Quick actions\n"
    )
    markup = kb(
        [btn("🧪 Selfcheck", "selfcheck"), btn("🛠 Кодер 3", "agent_code3_start")],
        [btn("🧩 Кодер 2", "agent_code2_start"), btn("🕵️ AGENT_0051", "menu_agent")],
        [btn("◀️ Админка", "adm2:main")],
    )
    return text, markup


def build_maintenance_panel(btn, kb):
    text = (
        "🧹 <b>Обслуживание</b>\n\n"
        "• Очистка временных файлов\n"
        "• Перезапуск worker-ов\n"
        "• Ротация логов\n"
        "• Бэкап БД\n"
    )
    markup = kb(
        [btn("🧽 Temp cleanup", "adm2:maint_cleanup"), btn("🧵 Restart workers", "adm2:maint_workers")],
        [btn("💾 Backup DB", "adm2:maint_backup"), btn("📜 Rotate logs", "adm2:maint_rotate_logs")],
        [btn("◀️ Админка", "adm2:main")],
    )
    return text, markup
