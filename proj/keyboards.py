"""
BlackBugsAI — Keyboards
Все inline-клавиатуры бота.
"""
from __future__ import annotations

def kb(*rows):
    """Строит inline_keyboard из списка рядов кнопок."""
    return {"inline_keyboard": [list(r) for r in rows]}

def btn(text, data):
    return {"text": text, "callback_data": data}

def back_btn(dest="menu"):
    return btn("◀️ Меню", dest)

def btn_model(label, provider, model):
    return btn(label, f"llm_set:{provider}:{model}")

    """Собирает InlineKeyboardMarkup из рядов кнопок."""
    return {"inline_keyboard": list(rows)}
    """Одна inline-кнопка."""
    return {"text": text, "callback_data": data}
    return btn("◀️ Назад", dest)
    """Кнопка выбора модели с автоматическим кешированием длинных ID.
    Если callback_data > 60 байт — используем _mdl_cache."""
    raw = "llm_setmodel:{}:{}".format(provider, model)
    if len(raw.encode()) <= 60:
        return btn(label, raw)
    # Кеш: ищем существующий ключ
    key_val = "{}:{}".format(provider, model)
    existing = next((k for k, v in _mdl_cache.items() if v == key_val), None)
    if not existing:
        existing = "m{}".format(len(_mdl_cache))
        _mdl_cache[existing] = key_val
    return btn(label, "llm_m:{}".format(existing))
def menu_keyboard():
    return kb(
        [btn("💬 ИИ-чат", "agent_chat_start"), btn("💻 Кодер", "agent_code_start")],
        [btn("🧩 Кодер 2", "agent_code2_start"), btn("🛠 Кодер 3", "agent_code3_start")],
        [btn("📁 Файлы", "tasks:artifacts")],
        [btn("🎨 Картинки", "menu_image"), btn("🎙 Озвучка", "menu_tts")],
        [btn("🧠 LLM", "menu_llm"), btn("📋 Задачи", "tasks:list")],
        [btn("👤 Профиль", "profile"), btn("❓ Справка", "help")],
    )
def style_keyboard():
    current = _get_env_style()
    rows = []
    keys = list(STYLES.keys())
    for i in range(0, len(keys), 2):
        pair = keys[i:i+2]
        row = []
        for k in pair:
            s = STYLES[k]
            mark = " ✅" if k == current else ""
            row.append(btn("{} {}{}".format(s['emoji'], s['name'], mark), "style:{}".format(k)))
        rows.append(row)
    rows.append([btn("✏️ Задать свой промт", "set_custom_prompt")])
    rows.append([back_btn()])
    return kb(*rows)
def tts_keyboard():
    provider = (config.TTS_PROVIDER or 'edge').lower().strip()
    edge_mark = " ✅" if provider == 'edge' else ""
    eleven_mark = " ✅" if provider != 'edge' else ""
    return kb(
        [btn("edge-tts (бесплатно){}".format(edge_mark), "tts_prov:edge"),
         btn("ElevenLabs{}".format(eleven_mark),          "tts_prov:elevenlabs")],
        [btn("🌍 Язык озвучки (edge)",  "menu_lang")],
        [btn("🎙 Сменить голос",        "set_voice")],
        [btn("📋 Список голосов",       "voices")],
        [back_btn()],
    )
def lang_keyboard():
    current = (os.environ.get('TTS_LANGUAGE', 'ru') or 'ru').lower()
    rows = []
    keys = list(TTS_LANGUAGES.keys())
    for i in range(0, len(keys), 2):
        pair = keys[i:i+2]
        row = []
        for k in pair:
            l = TTS_LANGUAGES[k]
            mark = " ✅" if k == current else ""
            row.append(btn("{}{}".format(l['name'], mark), "lang:{}".format(k)))
        rows.append(row)
    rows.append([back_btn("menu_tts")])
    return kb(*rows)
def llm_keyboard():
    cur = config.LLM_PROVIDER.lower().strip()
    cur_m = config.LLM_MODEL
    def lbl(name, key):
        mark = " ✅" if cur == key else ""
        return btn("{}{}".format(name, mark), "llm_info:{}".format(key))
    # Быстрые кнопки для топ-моделей (провайдер + модель за 1 клик)
    from llm_checker import RECOMMENDED as _REC
    def quick(emoji, prov, model_idx=0):
        models = _REC.get(prov, [])
        if not models: return None
        m = models[min(model_idx, len(models)-1)]
        mark = " ✅" if (cur == prov and cur_m == m) else ""
        return btn_model("{} {}{}".format(emoji, prov.upper(), mark), prov, m)
    q_groq  = quick("⚡", "groq")
    q_gem   = quick("💎", "gemini")
    q_cbr   = quick("🧠", "cerebras")
    q_or    = quick("🌐", "openrouter", 4)  # free model
    q_snova = quick("🔥", "sambanova")
    q_ds    = quick("🐋", "deepseek")
    quick_rows = []
    row1 = [b for b in [q_groq, q_gem] if b]
    row2 = [b for b in [q_cbr, q_or] if b]
    row3 = [b for b in [q_snova, q_ds] if b]
    if row1: quick_rows.append(row1)
    if row2: quick_rows.append(row2)
    if row3: quick_rows.append(row3)
    return kb(
        *quick_rows,
        # ── Все провайдеры (для ручного выбора) ──────────
        [lbl("🔵 OpenAI",   "openai"),  lbl("🟣 Claude",    "claude")],
        [lbl("🟡 Mistral",  "mistral"), lbl("✖ xAI",        "xai")],
        [lbl("🦙 Llama",   "llama"),   lbl("🤖 Ollama",    "ollama")],
        [btn("📋 Все провайдеры",  "llm_all_providers")],
        # ── Действия ─────────────────────────────────────
        [btn("🔑 Добавить API ключ","llm_add_key"),
         btn("✏️ Ввести вручную",   "set_llm")],
        [btn("🔍 Проверить все",     "llm_check"),
         btn("🆓 Бесплатные",        "llm_free")],
        [btn("🧪 Тест текущего",    "test"),
         btn("🔄 Выбрать модель",   "llm_pick_current")],
        [back_btn()],
    )
def project_mode_keyboard():
    """Выбор режима генерации проекта перед стартом."""
    return kb(
        [btn("🧩 Двухэтапный план",    "proj_mode:plan")],
        [btn("📄 Один файл за раз",    "proj_mode:onebyone")],
        [btn("🏗 Скаффолдер-скрипт",  "proj_mode:scaffold")],
        [btn("❌ Отмена",              "proj_mode:cancel")],
    )
def agent_keyboard(chat_id=None):
    """Подменю ИИ-агента."""
    active = is_active(chat_id) if chat_id else False
    info = session_info(chat_id) if active else None
    rows = []
    if active and info:
        mode_label = "💬 Чат" if info['mode'] == 'chat' else "💻 Кодер"
        rows.append([btn("🟢 Сессия: {} · {} сообщ. · {}".format(
            mode_label, info['messages'], info['elapsed']), "agent_status")])
        rows.append([btn("🔴 Завершить сессию", "agent_end")])
    else:
        rows.append([btn("💬 ИИ-чат", "agent_chat_start"), btn("💻 Кодер", "agent_code_start")])
        rows.append([btn("🧩 Кодер 2", "agent_code2_start"), btn("🛠 Кодер 3", "agent_code3_start")])
        rows.append([btn("🎬 YouTube", "agent_youtube_start")])
    rows.append([btn("📁 Файловый менеджер", "fm:open:~"), btn("🔧 Инструменты", "agent_tools_menu")])
    rows.append([btn("ℹ️ Как пользоваться", "agent_help")])
    rows.append([back_btn()])
    return kb(*rows)
def after_file_keyboard():
    """Что делать с файлом после анализа."""
    return kb(
        [btn("🔍 Найти ошибки",        "file_action:review"),
         btn("🔧 Исправить ошибки",    "file_action:fix")],
        [btn("📖 Объяснить код",       "file_action:explain"),
         btn("🚀 Улучшить/расширить",  "file_action:improve")],
        [btn("🏗 Создать на основе",    "file_action:build"),
         btn("✏️ Свой запрос",         "file_action:custom")],
        [btn("🔴 Закрыть",             "file_action:close")],
    )
def chat_control_keyboard(mode='chat'):
    """Кнопки управления внутри ИИ-сессии."""
    rows = [
        [btn("🗑 Очистить историю", "agent_clear"),
         btn("🔴 Завершить",        "agent_end")],
        [btn("📊 Статус сессии",   "agent_status"),
         btn("◀️ Главное меню",    "menu")],
    ]
    if mode == 'chat':
        rows.insert(1, [
            btn("🌐 Поиск в сети",   "chat_fn:websearch"),
            btn("📁 Мои файлы",      "fm:open:~"),
        ])
        rows.insert(2, [
            btn("🔧 Инструменты",    "agent_tools_menu"),
            btn("🎭 Сменить роль",   "chat_fn:persona"),
        ])
    return kb(*rows)
# ══════════════════════════════════════════════════════════════