"""
user_settings.py — Per-user настройки, история, память, изоляция
"""
import os, json, sqlite3, time
from datetime import datetime
import config
from core.db_manager import BLACKBUGS_DB

DB_PATH = str(BLACKBUGS_DB)

def _db():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c

def _migrate():
    with _db() as c:
        for col, t in [
            ("agent_type",    "TEXT DEFAULT 'assistant'"),
            ("llm_provider",  "TEXT"),
            ("llm_model",     "TEXT"),
            ("tts_voice",     "TEXT"),
            ("system_prompt", "TEXT"),
            ("sandbox_on",    "INTEGER DEFAULT 1"),
            ("settings_json", "TEXT DEFAULT '{}'"),
            ("memory_json",   "TEXT DEFAULT '[]'"),
            ("active_task_id","TEXT"),
            ("lang",          "TEXT DEFAULT 'ru'"),
        ]:
            try: c.execute(f"ALTER TABLE users ADD COLUMN {col} {t}"); c.commit()
            except: pass

_migrate()

# ─── Agent types ──────────────────────────────────────────────────────────────

AGENT_TYPES = {
    'assistant': {
        'icon':  '🤖',
        'name':  'AI Ассистент',
        'desc':  'ИИ-помощник и управление задачами',
        'perms': ['use_agent','use_content'],
        'system': 'Ты — умный AI-ассистент. Помогаешь с задачами, отвечаешь на вопросы, анализируешь информацию.',
    },
    'devops': {
        'icon':  '⚙️',
        'name':  'AI DevOps',
        'desc':  'Код, автоматизация, скрипты, деплой',
        'perms': ['use_code_agent','use_devops','use_sandbox','run_shell'],
        'system': 'Ты — опытный DevOps/SRE инженер. Пишешь код, скрипты, настраиваешь автоматизацию. '
                  'Даёшь конкретные команды и готовые решения. Предпочитаешь Python, bash, Docker.',
    },
    'content': {
        'icon':  '✍️',
        'name':  'AI Content',
        'desc':  'Тексты, SEO, SMM, копирайтинг',
        'perms': ['use_agent','use_content'],
        'system': 'Ты — профессиональный копирайтер и контент-стратег. '
                  'Пишешь цепляющие тексты, посты, статьи, описания. '
                  'Адаптируешь стиль под задачу и аудиторию.',
    },
    'automation': {
        'icon':  '🔄',
        'name':  'AI Automation',
        'desc':  'Личная и командная автоматизация',
        'perms': ['use_automation','run_tasks','create_bots'],
        'system': 'Ты — специалист по автоматизации процессов. '
                  'Помогаешь автоматизировать рутину: парсинг, уведомления, интеграции, боты. '
                  'Предлагаешь готовые решения с кодом.',
    },
}

# ─── Getter/Setter ────────────────────────────────────────────────────────────

def get_settings(user_id):
    with _db() as c:
        r = c.execute('SELECT * FROM users WHERE telegram_id=?', (int(user_id),)).fetchone()
        if not r: return {}
        base = dict(r)
        try: base['settings'] = json.loads(base.get('settings_json') or '{}')
        except: base['settings'] = {}
        try: base['memory'] = json.loads(base.get('memory_json') or '[]')
        except: base['memory'] = []
        return base

def set_setting(user_id, key, value):
    allowed_direct = {'agent_type','llm_provider','llm_model','tts_voice',
                      'system_prompt','sandbox_on','active_task_id','lang'}
    if key in allowed_direct:
        with _db() as c:
            c.execute(f'UPDATE users SET {key}=? WHERE telegram_id=?', (value, int(user_id)))
    else:
        s = get_settings(user_id)
        settings = s.get('settings', {})
        settings[key] = value
        with _db() as c:
            c.execute('UPDATE users SET settings_json=? WHERE telegram_id=?',
                      (json.dumps(settings, ensure_ascii=False), int(user_id)))

def get_user_llm(user_id):
    """LLM настройки пользователя (с fallback на глобальные)."""
    s = get_settings(user_id)
    return {
        'provider': s.get('llm_provider') or config.LLM_PROVIDER,
        'model':    s.get('llm_model')    or config.LLM_MODEL,
    }

def get_user_system_prompt(user_id):
    """Системный промт: личный → тип агента → дефолт."""
    s = get_settings(user_id)
    if s.get('system_prompt'):
        return s['system_prompt']
    atype = s.get('agent_type', 'assistant')
    return AGENT_TYPES.get(atype, AGENT_TYPES['assistant'])['system']

def get_agent_type(user_id):
    s = get_settings(user_id)
    return s.get('agent_type', 'assistant')

# ─── Память по задачам ────────────────────────────────────────────────────────

def add_memory(user_id, key, value, max_items=20):
    """Добавляет запись в память пользователя."""
    s = get_settings(user_id)
    memory = s.get('memory', [])
    memory.append({'key': key, 'value': str(value)[:500], 'ts': datetime.now().isoformat()})
    if len(memory) > max_items:
        memory = memory[-max_items:]
    with _db() as c:
        c.execute('UPDATE users SET memory_json=? WHERE telegram_id=?',
                  (json.dumps(memory, ensure_ascii=False), int(user_id)))

def get_memory(user_id):
    s = get_settings(user_id)
    return s.get('memory', [])

def clear_memory(user_id):
    with _db() as c:
        c.execute("UPDATE users SET memory_json='[]' WHERE telegram_id=?", (int(user_id),))

def format_memory(user_id):
    mem = get_memory(user_id)
    if not mem:
        return "🧠 Память пуста."
    lines = [f"🧠 <b>Память ({len(mem)} записей)</b>\n"]
    for m in mem[-10:]:
        ts = (m.get('ts',''))[:16].replace('T',' ')
        lines.append(f"<code>{ts}</code> <b>{m['key']}</b>: {m['value'][:100]}")
    return "\n".join(lines)

# ─── Клавиатура выбора типа агента ───────────────────────────────────────────

def agent_type_keyboard(current=None):
    rows = []
    for k, v in AGENT_TYPES.items():
        mark = " ✅" if k == current else ""
        rows.append([{"text": f"{v['icon']} {v['name']}{mark}",
                      "callback_data": f"set_agent_type:{k}"}])
    return {"inline_keyboard": rows}

def format_agent_type_info(atype):
    t = AGENT_TYPES.get(atype, AGENT_TYPES['assistant'])
    return (
        f"{t['icon']} <b>{t['name']}</b>\n"
        f"<i>{t['desc']}</i>\n\n"
        f"<b>Системный промт:</b>\n<code>{t['system'][:200]}...</code>"
    )
