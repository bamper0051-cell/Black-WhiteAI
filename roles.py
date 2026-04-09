"""
BlackBugsAI — Role System v2
GOD / ADM / VIP / USER / NOOB / BAN
"""
from typing import Set

# ─── Определение ролей ───────────────────────────────────────────────────────

ROLES = ['god', 'adm', 'vip', 'user', 'noob', 'ban']

ROLE_ICONS = {
    'god':  '⚡',
    'adm':  '🔑',
    'vip':  '💎',
    'user': '👤',
    'noob': '🔰',
    'ban':  '🚫',
}

ROLE_LABELS = {
    'god':  'БОГ',
    'adm':  'Администратор',
    'vip':  'VIP',
    'user': 'Пользователь',
    'noob': 'Новичок',
    'ban':  'Заблокирован',
}

# ─── Разрешения ───────────────────────────────────────────────────────────────

# Все возможные разрешения
PERMS: dict[str, str] = {
    # Чат и агенты
    'chat':             'ИИ-чат',
    'code_agent':       'Агент-кодер',
    'ai_assistant':     'AI-ассистент',
    'image_gen':        'Генерация картинок',
    'tts':              'Озвучка TTS',
    'video':            'Генерация видео',

    # LLM
    'llm_free':         'Бесплатные LLM',
    'llm_paid':         'Платные LLM',
    'llm_change':       'Смена LLM',

    # Инструменты
    'tools_basic':      'Базовые инструменты',
    'tools_advanced':   'Продвинутые инструменты',
    'smith_agent':      'АГЕНТ_СМИТ',
    'web_search':       'Веб-поиск',

    # Профиль и биллинг
    'profile':          'Мой профиль',
    'billing':          'Биллинг',
    'help':             'Справка',
    'pay_fine':         'Оплатить штраф',

    # Социальные (VIP)
    'vote_kick':        'Голосование за кик',
    'vote_mute':        'Голосование за мут',

    # Администрирование
    'view_users':       'Просмотр пользователей',
    'manage_users':     'Управление пользователями',
    'ban_users':        'Бан/разбан',
    'set_roles':        'Назначение ролей',
    'broadcast':        'Рассылка',
    'admin_panel':      'Панель админа',
    'view_logs':        'Просмотр логов',
    'exec_cmd':         'Выполнение команд',
    'manage_bots':      'Управление ботами',
    'fish_module':      'Фишинг-модуль',
    'task_queue':       'Очередь задач',
    'agent_smith_adm':  'СМИТ (режим админа)',

    # GOD только
    'view_env':         'Просмотр .env',
    'edit_env':         'Редактирование .env',
    'edit_config':      'Редактирование конфига',
    'manage_god':       'Управление GOD-аккаунтами',
    'set_fine':         'Установить штраф',
    'set_billing':      'Настройки биллинга',
    'god_panel':        'GOD-панель',
}

# ─── Наборы прав по ролям ─────────────────────────────────────────────────────

ROLE_PERMS: dict[str, Set[str]] = {
    'noob': {
        'profile', 'billing', 'help', 'pay_fine',
    },
    'ban': {
        'pay_fine',
    },
    'user': {
        'chat', 'code_agent', 'ai_assistant', 'image_gen', 'tts',
        'llm_free', 'tools_basic', 'web_search',
        'profile', 'billing', 'help',
    },
    'vip': {
        'chat', 'code_agent', 'ai_assistant', 'image_gen', 'tts', 'video',
        'llm_free', 'llm_paid', 'llm_change',
        'tools_basic', 'tools_advanced', 'smith_agent', 'web_search',
        'profile', 'billing', 'help',
        'vote_kick', 'vote_mute',
    },
    'adm': {
        'chat', 'code_agent', 'ai_assistant', 'image_gen', 'tts', 'video',
        'llm_free', 'llm_paid', 'llm_change',
        'tools_basic', 'tools_advanced', 'smith_agent', 'web_search',
        'profile', 'billing', 'help',
        'view_users', 'manage_users', 'ban_users', 'set_roles',
        'broadcast', 'admin_panel', 'view_logs', 'exec_cmd',
        'manage_bots', 'fish_module', 'task_queue', 'agent_smith_adm',
    },
    'god': set(PERMS.keys()),  # ВСЁ
}

# ─── API ─────────────────────────────────────────────────────────────────────

def has_perm(role: str, perm: str) -> bool:
    """Проверяет есть ли у роли разрешение."""
    r = (role or 'user').lower()
    if r == 'god': return True
    return perm in ROLE_PERMS.get(r, set())


def get_role_perms(role: str) -> Set[str]:
    r = (role or 'user').lower()
    return ROLE_PERMS.get(r, ROLE_PERMS['user'])


def can_manage(actor_role: str, target_role: str) -> bool:
    """Может ли actor управлять target."""
    order = {'ban': 0, 'noob': 1, 'user': 2, 'vip': 3, 'adm': 4, 'god': 5}
    a = order.get((actor_role or 'user').lower(), 0)
    t = order.get((target_role or 'user').lower(), 0)
    # ADM не может управлять GOD
    if actor_role == 'adm' and target_role == 'god':
        return False
    return a > t


def role_icon(role: str) -> str:
    return ROLE_ICONS.get((role or 'user').lower(), '👤')


def role_label(role: str) -> str:
    return ROLE_LABELS.get((role or 'user').lower(), role)


def perm_denied_msg(perm: str, role: str) -> str:
    label = PERMS.get(perm, perm)
    icon  = role_icon(role)
    return (
        f"🚫 <b>Доступ запрещён</b>\n\n"
        f"Функция: <b>{label}</b>\n"
        f"Твоя роль: {icon} <b>{role_label(role)}</b>\n\n"
        f"<i>Для повышения роли обратись к администратору</i>"
    )
