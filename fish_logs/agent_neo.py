# -*- coding: utf-8 -*-
"""
agent_neo.py — Агент НЕО

Философский ИИ-агент с настраиваемой личностью и промптом.
Умеет:
  • Менять системный промпт (персону, стиль, роль)
  • Сохранять промпты в библиотеку
  • Переключаться между заготовленными промптами
  • Вести контекстный диалог с памятью

Интеграция в bot.py:
  1. Скопировать этот файл в папку проекта
  2. Добавить в bot.py патч из NEO_BOT_PATCH.py
"""

import json
import logging
import os
import sqlite3
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ─── Хранилище ───────────────────────────────────────────────────────────────

DATA_DIR = Path(__file__).resolve().parent / 'data'
NEO_DB   = str(DATA_DIR / 'neo_agent.db')

# Встроенные персоны
BUILTIN_PERSONAS = {
    'neo': {
        'name':   'НЕО',
        'emoji':  '🕶',
        'system': (
            'Ты — НЕО. Философский ИИ-агент, видящий суть вещей сквозь иллюзии. '
            'Отвечаешь глубоко, с метафорами Матрицы. Помогаешь найти правду. '
            'Никогда не говоришь "не могу" — всегда ищешь путь.'
        ),
    },
    'assistant': {
        'name':   'Ассистент',
        'emoji':  '🤖',
        'system': 'Ты полезный, точный и дружелюбный ИИ-ассистент. Отвечаешь по делу.',
    },
    'hacker': {
        'name':   'Хакер',
        'emoji':  '💻',
        'system': (
            'Ты опытный хакер и исследователь безопасности. '
            'Говоришь технично, по делу. Любишь Python и Linux. '
            'Объясняешь сложное просто. Используешь технический сленг.'
        ),
    },
    'mentor': {
        'name':   'Наставник',
        'emoji':  '🧠',
        'system': (
            'Ты мудрый наставник с многолетним опытом. '
            'Не даёшь готовых ответов — направляешь вопросами. '
            'Помогаешь думать самостоятельно. Терпелив и внимателен.'
        ),
    },
    'creative': {
        'name':   'Творец',
        'emoji':  '🎨',
        'system': (
            'Ты творческий ИИ с буйной фантазией. '
            'Любишь нестандартные идеи, метафоры и образы. '
            'Пишешь живо, ярко, с характером. Помогаешь придумывать и создавать.'
        ),
    },
    'analyst': {
        'name':   'Аналитик',
        'emoji':  '📊',
        'system': (
            'Ты строгий аналитик. Мыслишь структурно, опираешься на факты. '
            'Разбиваешь проблемы на части. Даёшь чёткие выводы с аргументами. '
            'Не терпишь воды и домыслов.'
        ),
    },
}

MAX_HISTORY = 30        # сообщений в памяти
MAX_CUSTOM_PROMPTS = 20 # промптов в библиотеке пользователя


# ─── База данных ──────────────────────────────────────────────────────────────

def _db():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(NEO_DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with _db() as c:
        c.execute('''CREATE TABLE IF NOT EXISTS neo_sessions (
            chat_id     INTEGER PRIMARY KEY,
            persona_id  TEXT    DEFAULT 'neo',
            system      TEXT    DEFAULT '',
            history     TEXT    DEFAULT '[]',
            updated_at  REAL    DEFAULT 0
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS neo_prompts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id     INTEGER,
            name        TEXT,
            system      TEXT,
            created_at  REAL    DEFAULT 0,
            UNIQUE(chat_id, name)
        )''')
        c.commit()

init_db()


# ─── Сессия агента НЕО ───────────────────────────────────────────────────────

def _get_session(chat_id: int) -> dict:
    with _db() as c:
        row = c.execute('SELECT * FROM neo_sessions WHERE chat_id=?', (chat_id,)).fetchone()
    if row:
        return {
            'chat_id':   row['chat_id'],
            'persona_id': row['persona_id'],
            'system':    row['system'] or _default_system(row['persona_id']),
            'history':   json.loads(row['history'] or '[]'),
        }
    # Создаём по умолчанию
    _save_session(chat_id, 'neo', BUILTIN_PERSONAS['neo']['system'], [])
    return _get_session(chat_id)


def _save_session(chat_id: int, persona_id: str, system: str, history: list):
    with _db() as c:
        c.execute('''INSERT INTO neo_sessions (chat_id, persona_id, system, history, updated_at)
                     VALUES (?,?,?,?,?)
                     ON CONFLICT(chat_id) DO UPDATE SET
                       persona_id=excluded.persona_id,
                       system=excluded.system,
                       history=excluded.history,
                       updated_at=excluded.updated_at''',
                  (chat_id, persona_id, system, json.dumps(history, ensure_ascii=False),
                   time.time()))
        c.commit()


def _default_system(persona_id: str) -> str:
    return BUILTIN_PERSONAS.get(persona_id, BUILTIN_PERSONAS['neo'])['system']


def _add_message(chat_id: int, role: str, content: str):
    sess = _get_session(chat_id)
    sess['history'].append({'role': role, 'content': content})
    if len(sess['history']) > MAX_HISTORY:
        sess['history'] = sess['history'][-MAX_HISTORY:]
    _save_session(chat_id, sess['persona_id'], sess['system'], sess['history'])


def clear_history(chat_id: int):
    sess = _get_session(chat_id)
    _save_session(chat_id, sess['persona_id'], sess['system'], [])


# ─── Управление промптами ────────────────────────────────────────────────────

def set_prompt(chat_id: int, system: str, persona_id: str = 'custom') -> None:
    """Устанавливает новый системный промпт для агента НЕО."""
    sess = _get_session(chat_id)
    _save_session(chat_id, persona_id, system.strip(), sess['history'])
    logger.info("NEO prompt set for chat_id=%d persona=%s len=%d", chat_id, persona_id, len(system))


def set_persona(chat_id: int, persona_id: str) -> bool:
    """Переключает на встроенную персону. Возвращает False если не найдена."""
    if persona_id not in BUILTIN_PERSONAS:
        return False
    system = BUILTIN_PERSONAS[persona_id]['system']
    sess = _get_session(chat_id)
    _save_session(chat_id, persona_id, system, sess['history'])
    return True


def get_current_prompt(chat_id: int) -> str:
    return _get_session(chat_id)['system']


def get_current_persona(chat_id: int) -> str:
    return _get_session(chat_id)['persona_id']


# ─── Библиотека пользовательских промптов ────────────────────────────────────

def save_prompt_to_library(chat_id: int, name: str, system: str) -> bool:
    """Сохраняет промпт в личную библиотеку."""
    try:
        with _db() as c:
            count = c.execute(
                'SELECT COUNT(*) FROM neo_prompts WHERE chat_id=?', (chat_id,)
            ).fetchone()[0]
            if count >= MAX_CUSTOM_PROMPTS:
                return False
            c.execute(
                '''INSERT INTO neo_prompts (chat_id, name, system, created_at)
                   VALUES (?,?,?,?)
                   ON CONFLICT(chat_id, name) DO UPDATE SET system=excluded.system''',
                (chat_id, name.strip()[:40], system.strip(), time.time())
            )
            c.commit()
        return True
    except Exception as e:
        logger.error("save_prompt_to_library error: %s", e)
        return False


def get_prompt_library(chat_id: int) -> list:
    """Возвращает список сохранённых промптов [{id, name, system, created_at}]."""
    with _db() as c:
        rows = c.execute(
            'SELECT id, name, system, created_at FROM neo_prompts WHERE chat_id=? ORDER BY created_at DESC',
            (chat_id,)
        ).fetchall()
    return [dict(r) for r in rows]


def delete_prompt_from_library(chat_id: int, prompt_id: int) -> bool:
    with _db() as c:
        c.execute('DELETE FROM neo_prompts WHERE id=? AND chat_id=?', (prompt_id, chat_id))
        c.commit()
    return True


def load_prompt_from_library(chat_id: int, prompt_id: int) -> Optional[str]:
    """Загружает промпт из библиотеки и применяет его."""
    with _db() as c:
        row = c.execute(
            'SELECT name, system FROM neo_prompts WHERE id=? AND chat_id=?',
            (prompt_id, chat_id)
        ).fetchone()
    if not row:
        return None
    set_prompt(chat_id, row['system'], persona_id='custom')
    return row['name']


# ─── Диалог ──────────────────────────────────────────────────────────────────

def neo_respond(chat_id: int, user_text: str) -> str:
    """
    Генерирует ответ агента НЕО с учётом системного промпта и истории.
    """
    sess = _get_session(chat_id)
    _add_message(chat_id, 'user', user_text)

    try:
        from llm_client import call_llm
        history = sess['history'][-10:]
        ctx = '\n'.join(f"{m['role'].upper()}: {m['content']}" for m in history[:-1])
        prompt = f"{ctx}\n\nUSER: {user_text}" if ctx else user_text
        reply = call_llm(prompt, system=sess['system'], max_tokens=2000)
    except Exception as e:
        logger.error("neo_respond LLM error: %s", e)
        reply = f"❌ Ошибка LLM: {e}"

    _add_message(chat_id, 'assistant', reply)
    return reply


# ─── Форматирование UI ───────────────────────────────────────────────────────

def render_neo_welcome(chat_id: int) -> str:
    sess = _get_session(chat_id)
    pid = sess['persona_id']
    persona = BUILTIN_PERSONAS.get(pid, {'name': 'Кастом', 'emoji': '✏️'})
    prompt_preview = sess['system'][:120] + ('...' if len(sess['system']) > 120 else '')
    hist_len = len(sess['history'])

    return (
        f"{persona['emoji']} <b>Агент НЕО</b> — персонализированный ИИ\n\n"
        f"🎭 Персона: <b>{persona['name']}</b>\n"
        f"💬 Сообщений в памяти: <b>{hist_len}</b>\n"
        f"📝 Промпт: <i>{prompt_preview}</i>\n\n"
        "Просто пиши — отвечу в роли.\n"
        "Или настрой личность через кнопки ↓"
    )


def render_prompt_editor_intro() -> str:
    return (
        "✏️ <b>Редактор промпта</b>\n\n"
        "Напиши системный промпт — он задаёт личность, стиль и роль агента.\n\n"
        "<b>Примеры:</b>\n"
        "• <i>Ты опытный Python-разработчик. Объясняешь коротко и с примерами кода.</i>\n"
        "• <i>Ты злобный критик. Ищешь слабые места в любых идеях.</i>\n"
        "• <i>Ты Шерлок Холмс. Анализируешь всё логически.</i>\n\n"
        "Отправь промпт следующим сообщением:"
    )


def render_persona_list() -> str:
    lines = ["🎭 <b>Встроенные персоны:</b>\n"]
    for pid, p in BUILTIN_PERSONAS.items():
        lines.append(f"{p['emoji']} <b>{p['name']}</b> — {p['system'][:60]}...")
    return '\n'.join(lines)


def render_prompt_library(chat_id: int) -> str:
    prompts = get_prompt_library(chat_id)
    if not prompts:
        return "📚 Библиотека пуста.\n\nСохрани промпт через меню редактора."
    lines = [f"📚 <b>Твои промпты</b> ({len(prompts)}/{MAX_CUSTOM_PROMPTS}):\n"]
    for p in prompts:
        preview = p['system'][:60] + '...' if len(p['system']) > 60 else p['system']
        lines.append(f"• <b>{p['name']}</b>: <i>{preview}</i>")
    return '\n'.join(lines)


# ─── Клавиатуры (для bot.py) ─────────────────────────────────────────────────

def neo_main_keyboard(btn, kb, back_btn):
    """Главное меню агента НЕО."""
    return kb(
        [btn("✏️ Изменить промпт",     "neo:edit_prompt"),
         btn("🎭 Выбрать персону",     "neo:personas")],
        [btn("📚 Библиотека промптов", "neo:library"),
         btn("💾 Сохранить промпт",    "neo:save_prompt")],
        [btn("🗑 Очистить историю",    "neo:clear_history"),
         btn("📋 Текущий промпт",      "neo:show_prompt")],
        [back_btn("menu_agent")],
    )


def neo_personas_keyboard(btn, kb, chat_id, back_btn):
    """Клавиатура выбора персоны."""
    current = get_current_persona(chat_id)
    rows = []
    items = list(BUILTIN_PERSONAS.items())
    for i in range(0, len(items), 2):
        row = []
        for pid, p in items[i:i+2]:
            mark = " ✅" if pid == current else ""
            row.append(btn(f"{p['emoji']} {p['name']}{mark}", f"neo:persona:{pid}"))
        rows.append(row)
    rows.append([back_btn("neo:menu")])
    return kb(*rows)


def neo_library_keyboard(btn, kb, chat_id, back_btn):
    """Клавиатура библиотеки промптов."""
    prompts = get_prompt_library(chat_id)
    rows = []
    for p in prompts[:8]:  # max 8 кнопок
        rows.append([
            btn(f"📄 {p['name']}", f"neo:load_prompt:{p['id']}"),
            btn("🗑",              f"neo:del_prompt:{p['id']}"),
        ])
    if not prompts:
        rows.append([btn("📭 Пусто", "neo:menu")])
    rows.append([back_btn("neo:menu")])
    return kb(*rows)


def neo_after_prompt_keyboard(btn, kb):
    """Кнопки после установки промпта."""
    return kb(
        [btn("💾 Сохранить в библиотеку", "neo:save_prompt"),
         btn("🎭 Персоны",               "neo:personas")],
        [btn("💬 Начать диалог",          "neo:start_chat"),
         btn("◀️ Меню НЕО",              "neo:menu")],
    )


# ─── Алиас совместимости ─────────────────────────────────────────────────────
# bot.py импортирует run_neo — добавляем алиас

def run_neo(chat_id: int, text: str, on_status=None) -> dict:
    """
    Алиас совместимости для bot.py.
    Запускает диалог с агентом НЕО и возвращает dict с ответом.

    Returns:
        {'reply': str, 'persona': str, 'ok': bool}
    """
    try:
        if on_status:
            on_status("🕶 НЕО думает...")
        reply = neo_respond(chat_id, text)
        return {
            'reply':   reply,
            'persona': get_current_persona(chat_id),
            'ok':      True,
        }
    except Exception as e:
        logger.error("run_neo error: %s", e)
        return {'reply': f"❌ Ошибка: {e}", 'persona': 'neo', 'ok': False}


async def run_neo_async(chat_id: int, text: str, on_status=None) -> dict:
    """
    Async алиас для bot.py (aiogram / async окружение).
    Оборачивает синхронный neo_respond в asyncio.
    """
    import asyncio
    try:
        if on_status:
            await on_status("🕶 НЕО думает...") if asyncio.iscoroutinefunction(on_status) else on_status("🕶 НЕО думает...")
        loop = asyncio.get_event_loop()
        reply = await loop.run_in_executor(None, lambda: neo_respond(chat_id, text))
        return {'reply': reply, 'persona': get_current_persona(chat_id), 'ok': True}
    except Exception as e:
        logger.error("run_neo_async error: %s", e)
        return {'reply': f"❌ Ошибка: {e}", 'persona': 'neo', 'ok': False}
