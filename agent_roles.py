"""
agent_roles.py — RBAC система АВТОМУВИ
Роли, права, лимиты, изоляция по пользователям
"""
import os, json, time, sqlite3
from functools import wraps
import config
from core.db_manager import BLACKBUGS_DB

DB_PATH = str(BLACKBUGS_DB)

# ─── Константы прав ───────────────────────────────────────────────────────────
PERM = {
    # Агент
    'use_agent':        'Использовать ИИ-агента',
    'use_code_agent':   'Агент-кодер',
    'use_devops':       'DevOps агент',
    'use_content':      'Content агент',
    'use_automation':   'Automation агент',
    # Задачи
    'run_tasks':        'Запускать задачи',
    'view_own_tasks':   'Видеть свои задачи',
    'view_all_tasks':   'Видеть задачи всех',
    'cancel_tasks':     'Отменять задачи',
    # Файлы/артефакты
    'upload_files':     'Загружать файлы',
    'download_files':   'Скачивать файлы',
    'view_own_files':   'Видеть свои файлы',
    'view_all_files':   'Видеть файлы всех',
    # Боты и сессии
    'create_bots':      'Создавать ботов',
    'create_sessions':  'Создавать сессии',
    # Система
    'view_logs':        'Видеть логи',
    'run_shell':        'Shell-команды',
    'manage_users':     'Управлять пользователями',
    'change_settings':  'Менять настройки бота',
    'use_sandbox':      'Sandbox для кода',
}

# Права по роли
ROLE_PERMS = {
    'banned':  set(),
    'user': {
        'use_agent','use_content','run_tasks','view_own_tasks',
        'upload_files','download_files','view_own_files',
        'create_sessions',
    },
    'vip': {
        'use_agent','use_content','use_code_agent','use_automation',
        'run_tasks','view_own_tasks','cancel_tasks',
        'upload_files','download_files','view_own_files',
        'create_sessions','create_bots','use_sandbox',
    },
    'admin': set(PERM.keys()) - {'manage_users', 'change_settings'},
    'owner': set(PERM.keys()),
}
# admin и owner наследуют всё
ROLE_PERMS['admin'] = set(PERM.keys()) - {'manage_users'}
ROLE_PERMS['owner'] = set(PERM.keys())

# Лимиты по роли (задач в день, размер файла MB, макс сессий)
ROLE_LIMITS = {
    'banned':  {'tasks_per_day': 0,   'file_mb': 0,   'max_sessions': 0,  'history_msgs': 0},
    'user':    {'tasks_per_day': 20,  'file_mb': 10,  'max_sessions': 1,  'history_msgs': 20},
    'vip':     {'tasks_per_day': 100, 'file_mb': 50,  'max_sessions': 3,  'history_msgs': 50},
    'admin':   {'tasks_per_day': 500, 'file_mb': 200, 'max_sessions': 10, 'history_msgs': 100},
    'owner':   {'tasks_per_day': -1,  'file_mb': -1,  'max_sessions': -1, 'history_msgs': 200},
}

# ─── API ──────────────────────────────────────────────────────────────────────

def get_role(chat_id):
    """Возвращает роль пользователя."""
    try:
        with sqlite3.connect(DB_PATH) as c:
            r = c.execute('SELECT privilege FROM users WHERE telegram_id=?',
                          (int(chat_id),)).fetchone()
            return r[0] if r else 'user'
    except Exception:
        return 'user'

def has_perm(chat_id, perm):
    """Проверяет право у пользователя."""
    role = get_role(chat_id)
    return perm in ROLE_PERMS.get(role, set())

def get_limits(chat_id):
    """Возвращает лимиты для пользователя."""
    role = get_role(chat_id)
    return ROLE_LIMITS.get(role, ROLE_LIMITS['user'])

def check_daily_tasks(chat_id):
    """Проверяет не превышен ли дневной лимит задач. Возвращает (ok, used, limit)."""
    limits = get_limits(chat_id)
    max_tasks = limits['tasks_per_day']
    if max_tasks == -1:
        return True, 0, -1
    try:
        with sqlite3.connect(os.path.join(config.BASE_DIR, 'tasks.db')) as c:
            today = time.strftime('%Y-%m-%d')
            row = c.execute(
                "SELECT COUNT(*) FROM tasks WHERE user_id=? AND DATE(created_at)=?",
                (str(chat_id), today)
            ).fetchone()
            used = row[0] if row else 0
            return used < max_tasks, used, max_tasks
    except Exception:
        return True, 0, max_tasks

def require_perm(perm):
    """Декоратор для проверки прав в хендлерах."""
    def decorator(f):
        @wraps(f)
        def wrapper(chat_id, *args, **kwargs):
            if not has_perm(chat_id, perm):
                role = get_role(chat_id)
                return f"🚫 Нет доступа. Твоя роль: <b>{role}</b>\nТребуется право: <code>{PERM.get(perm, perm)}</code>"
            return f(chat_id, *args, **kwargs)
        return wrapper
    return decorator

def perm_error(perm, chat_id):
    """Возвращает текст ошибки доступа."""
    role = get_role(chat_id)
    return (
        f"🚫 <b>Нет доступа</b>\n"
        f"Роль: <b>{role}</b>\n"
        f"Нужно: <code>{PERM.get(perm, perm)}</code>\n\n"
        f"<i>Обратись к администратору для повышения прав.</i>"
    )

def role_keyboard():
    """Клавиатура для смены роли (для админа)."""
    roles = [
        ('👤 user',   'user'),
        ('💎 vip',    'vip'),
        ('🔑 admin',  'admin'),
        ('👑 owner',  'owner'),
        ('🚫 banned', 'banned'),
    ]
    return {"inline_keyboard": [[{"text": t, "callback_data": f"adm:priv_set:{r}"}] for t, r in roles]}

def format_perms(chat_id):
    """Форматирует список прав пользователя."""
    role = get_role(chat_id)
    perms = ROLE_PERMS.get(role, set())
    limits = ROLE_LIMITS.get(role, {})
    lines = [
        f"🔐 <b>Права: {role}</b>\n",
        f"📋 Задач в день: <b>{'∞' if limits.get('tasks_per_day')==-1 else limits.get('tasks_per_day')}</b>",
        f"📁 Файлов макс: <b>{'∞' if limits.get('file_mb')==-1 else str(limits.get('file_mb'))+'MB'}</b>",
        f"💬 Сессий: <b>{'∞' if limits.get('max_sessions')==-1 else limits.get('max_sessions')}</b>",
        "",
        "<b>Доступные функции:</b>",
    ]
    for p, desc in PERM.items():
        icon = "✅" if p in perms else "❌"
        lines.append(f"{icon} {desc}")
    return "\n".join(lines)

# Re-export PLANS from config для совместимости
try:
    import config as _c
    PLANS = _c.PLANS
except Exception:
    PLANS = {}

# ─── Совместимость с новой системой ролей ────────────────────────────────────
try:
    from roles import (has_perm, get_role_perms, can_manage,
                       role_icon, role_label, perm_denied_msg,
                       ROLE_ICONS, ROLE_LABELS, ROLE_PERMS as _NEW_ROLE_PERMS,
                       ROLES, PERMS)
    # Обновляем ROLE_PERMS
    ROLE_PERMS.update(_NEW_ROLE_PERMS)
    # Маппинг старых → новых названий
    _ROLE_MAP = {'owner': 'god', 'admin': 'adm', 'banned': 'ban'}
    PRIVILEGE_ICONS  = ROLE_ICONS
    PRIVILEGE_LABELS = ROLE_LABELS
except ImportError:
    pass
