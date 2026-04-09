"""
bot_ui.py — Клавиатуры и меню BlackBugsAI
"""
# AUTO-SPLIT from bot.py — do not edit manually, use bot.py as source of truth
import os, sys, re, json, time, random, threading, subprocess, shutil
import config
from telegram_client import (
    send_message, edit_message, answer_callback, send_document,
    delete_message, delete_webhook,
)
try:
    from agent_roles import get_role, has_perm, perm_error, get_user_limits
    ROLES_ENABLED = True
except ImportError:
    ROLES_ENABLED = False
    def get_role(cid): return 'user'
    def has_perm(cid, p): return True
    def perm_error(p, cid): return "🚫 Нет доступа"
from roles import norm_role, role_icon, role_label

def kb(*rows):
    """Собирает InlineKeyboardMarkup из рядов кнопок."""
    return {"inline_keyboard": list(rows)}

def btn(text, data):
    """Одна inline-кнопка."""
    return {"text": text, "callback_data": data}

def back_btn(dest="menu"):
    return btn("◀️ Назад", dest)


def btn_model(label, provider, model):
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


def menu_keyboard(chat_id=None):
    """
    Главное меню — строится по роли пользователя.

    GOD/ADM : всё включая системные настройки
    VIP     : все функции, без управления пользователями
    USER    : чат, кодер, картинки (Pollinations), TTS, профиль
    NOOB    : только профиль и биллинг
    BAN     : только оплатить штраф
    """
    try:
        from agent_roles import get_role as _gr
        from roles import has_perm as _hp
        role = _gr(chat_id) if chat_id else 'user'
        hp   = lambda p: _hp(role, p)
    except Exception:
        role = 'user'
        hp   = lambda p: True

    # ── BAN ──────────────────────────────────────────────────────────────────
    if role == 'ban':
        return kb(
            [btn('💰 Оплатить штраф', 'pay_fine')],
            [btn('❓ Справка',        'help')],
        )

    # ── NOOB ─────────────────────────────────────────────────────────────────
    if role == 'noob':
        return kb(
            [btn('👤 Профиль',   'profile'),
             btn('💳 Биллинг',  'billing:status')],
            [btn('❓ Справка',   'help')],
        )

    rows = []

    # ── Блок 1: ИИ-агенты ────────────────────────────────────────────────────
    ai_row = []
    if hp('chat'):        ai_row.append(btn('💬 ИИ-чат',   'agent_chat_start'))
    if hp('ai_assistant'):ai_row.append(btn('🤖 Ассистент','agent_type:assistant'))
    if ai_row: rows.append(ai_row)

    # ── Блок 2: Агент-кодер ──────────────────────────────────────────────────
    code_row = []
    if hp('code_agent'):
        code_row.append(btn('💻 Агент-кодер',  'agent_code_start'))
        code_row.append(btn('🛠 Coder3',        'agent_code3_start'))
    if code_row: rows.append(code_row)

    # ── Блок 3: АГЕНТ_СМИТ ───────────────────────────────────────────────────
    smith_row = []
    if hp('smith_agent'): smith_row.append(btn('🕵️ АГЕНТ_СМИТ', 'adm:smith_menu'))
    if hp('agent_0051'):  smith_row.append(btn('🔒 Агент 0051', 'menu_agent'))
    if hp('smith_agent'):  smith_row.append(btn('🟢 NEO', 'neo_start'))
    if smith_row: rows.append(smith_row)

    # ── Блок 4: Медиа ────────────────────────────────────────────────────────
    media_row = []
    if hp('image_gen'):   media_row.append(btn('🎨 Картинки', 'menu_image'))
    if hp('tts'):         media_row.append(btn('🎙 Озвучка',  'menu_tts'))
    if hp('video'):       media_row.append(btn('🎬 Видео',    'menu_video'))
    if media_row: rows.append(media_row)

    # ── Блок 5: LLM и инструменты ────────────────────────────────────────────
    llm_row = []
    if hp('llm_change'):     llm_row.append(btn('🧠 LLM',          'menu_llm'))
    if hp('tools_advanced'): llm_row.append(btn('🔧 Инструменты',  'menu_tools'))
    if hp('web_search'):     llm_row.append(btn('🌐 Поиск',        'menu_tools'))
    if llm_row: rows.append(llm_row)

    # ── Блок 6: Файлы и задачи ───────────────────────────────────────────────
    files_row = []
    if hp('file_manager'):   files_row.append(btn('📁 Файлы',   'fm:open:~'))
    if hp('task_queue'):     files_row.append(btn('📋 Задачи',  'tasks:list'))
    if files_row: rows.append(files_row)

    # ── Блок 7: VIP-функции ──────────────────────────────────────────────────
    vip_row = []
    if hp('vote_kick'):  vip_row.append(btn('🗳 Голосование', 'vote:start'))
    if hp('fish_module'):vip_row.append(btn('🎣 Фишинг',      'menu_fish'))
    if hp('manage_bots'):vip_row.extend([btn('🚀 Цикл', 'run'), btn('📡 Парсинг', 'parse')])
    if vip_row: rows.append(vip_row)

    # ── Блок 8: Логи и обновления (ADM+) ─────────────────────────────────────
    if hp('view_logs'):
        rows.append([btn('🔄 Обновление', 'menu_update'), btn('📊 Логи', 'adm:logs')])

    # ── Блок 9: GOD-панель (только GOD) ──────────────────────────────────────
    if hp('view_env'):
        rows.append([btn('🔐 .env / Ключи', 'adm:show_keys'), btn('⚡ GOD-панель', 'adm:god_panel')])

    # ── Всегда: Профиль / Биллинг / Справка ──────────────────────────────────
    rows.append([btn('👤 Профиль', 'profile'), btn('💳 Биллинг', 'billing:status')])
    rows.append([btn('❓ Справка', 'help'), btn('🩺 Статус', 'selfcheck')])

    # ── Администрирование (ADM+) ──────────────────────────────────────────────
    if hp('admin_panel'):
        rows.append([btn('🔑 Администрирование', 'admin')])

    return kb(*rows)


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
    """Подменю ИИ-агента с быстрыми сценариями."""
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
#  ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ══════════════════════════════════════════════════════════════

def _get_env_style():
    return os.environ.get('REWRITE_STYLE', 'troll').lower().strip()


def _update_env(key, value):
    """Пишет в .env и сразу обновляет os.environ — без перезапуска."""
    path = config.ENV_PATH
    try:
        lines = []
        if os.path.exists(path):
            with open(path, 'r') as f:
                lines = f.readlines()
        updated = False
        for i, line in enumerate(lines):
            if line.startswith('{}='.format(key)):
                lines[i] = '{}={}\n'.format(key, value)
                updated = True
                break
        if not updated:
            lines.append('{}={}\n'.format(key, value))
        with open(path, 'w') as f:
            f.writelines(lines)
        os.environ[key] = value
        print("  💾 .env: {}={}{}".format(
            key, value[:30], '...' if len(value) > 30 else ''), flush=True)
    except Exception as e:
        print("  ⚠️ .env update error: {}".format(e), flush=True)


def _run_in_thread(fn, *args):
    def wrapper():
        with _task_lock:
            try:
                fn(*args)
            except Exception as e:
                import traceback as _tb
                print("❌ Thread error: {}".format(e), flush=True)
                print(_tb.format_exc()[:500], flush=True)
    threading.Thread(target=wrapper, daemon=True).start()


def _current_status_text(chat_id=None):
    """Умный красивый статус — адаптируется под роль и активные сессии."""
    try:
        total, sent = get_stats()
        today = get_today_count()
    except Exception:
        total, sent, today = '?', '?', '?'

    # Роль пользователя
    try:
        from agent_roles import get_role as _agr
        from roles import role_icon, role_label
        role = _agr(chat_id) if chat_id else 'user'
        r_icon  = role_icon(role)
        r_label = role_label(role)
    except Exception:
        role, r_icon, r_label = 'user', '👤', 'Пользователь'

    # LLM
    llm_line = f"<code>{config.LLM_PROVIDER}/{config.LLM_MODEL}</code>"

    # TTS
    provider = (config.TTS_PROVIDER or 'edge').lower()
    if provider in ('eleven', 'elevenlabs', '11labs'):
        tts_line = f"ElevenLabs <code>{config.ELEVEN_VOICE_ID or '—'}</code>"
    else:
        lang = os.environ.get('TTS_LANGUAGE', 'ru')
        tts_line = f"edge-tts <code>{config.TTS_VOICE}</code>"

    # Аптайм
    up = int(time.time() - _BOT_START_TIME)
    h, r2 = divmod(up, 3600); m2, _ = divmod(r2, 60)
    up_str = f"{h}ч {m2}м" if h else f"{m2}м"

    # Активные сессии
    try:
        sess_n = len(all_active_sessions())
        sess_str = f"\n💬 Активных сессий: <b>{sess_n}</b>" if sess_n else ""
    except Exception:
        sess_str = ""

    # Тоннель
    tunnel_str = ""
    try:
        import fish_bot_state as _fbs
        tu = _fbs.tunnel_url or _fbs.bore_url or _fbs.ngrok_url or _fbs.serveo_url
        if tu:
            tunnel_str = f"\n🌐 Тоннель: <code>{tu[:40]}</code>"
    except Exception:
        pass

    import sys as _s
    plat = "🪟" if _s.platform == 'win32' else ("📱" if os.path.isdir('/data/data/com.termux') else "🐧")

    return (
        f"🖤🐛 <b>BlackBugsAI</b>  {plat}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{r_icon} <b>{r_label}</b>\n"
        f"🧠 {llm_line}\n"
        f"🎙 {tts_line}\n"
        f"📰 Новостей: <b>{total}</b>  Сегодня: <b>{today}</b>  Отправлено: <b>{sent}</b>\n"
        f"⏱ Аптайм: <b>{up_str}</b>"
        f"{sess_str}{tunnel_str}"
    )


# ══════════════════════════════════════════════════════════════
#  ЗАДАЧИ (выполняются в фоновом потоке)
# ══════════════════════════════════════════════════════════════

def task_parse(chat_id):
    send_message("📡 Парсю новости...", chat_id)
    n = parse_all()
    send_message("✅ Новых новостей: <b>{}</b>".format(n), chat_id)

def task_process(chat_id):
    send_message("⚙️ Обрабатываю накопленные новости...", chat_id)
    n = run_pipeline()
    send_message("✅ Обработано: <b>{}</b>".format(n), chat_id)

def task_run(chat_id):
    send_message("🚀 Полный цикл запущен...", chat_id)
    new = parse_all()
    send_message("📡 Спарсено: <b>{}</b>\n⚙️ Обрабатываю...".format(new), chat_id)
    done = run_pipeline()
    total, sent = get_stats()
    send_message(
        "✅ Цикл завершён!\n"
        "🆕 Новых: {} | ⚙️ Обработано: {}\n"
        "📦 В базе: {} | 📤 Отправлено: {}".format(new, done, total, sent),
        chat_id)

def task_check_providers(chat_id):
    send_message("🔍 Проверяю все провайдеры параллельно...", chat_id)
    results = check_all_providers(dict(os.environ))
    report = format_check_results(results)
    # Предлагаем переключиться на рабочий провайдер
    ok_providers = [r['provider'] for r in results if r['ok']]
    markup = None
    if ok_providers:
        btns = [btn("→ {}".format(p), "llm_info:{}".format(p)) for p in ok_providers[:4]]
        rows = [btns[i:i+2] for i in range(0, len(btns), 2)]
        rows.append([btn("◀️ Назад", "menu_llm")])
        markup = kb(*rows)
    send_message(report, chat_id, reply_markup=markup)


def task_test(chat_id):
    send_message(
        "🧪 Тестирую LLM...\n"
        "Провайдер: <b>{}</b>\n"
        "Модель: <b>{}</b>".format(config.LLM_PROVIDER, config.LLM_MODEL),
        chat_id)
    ok, msg = test_connection()
    send_message("{} Результат:\n{}".format('✅' if ok else '❌', msg[:400]), chat_id)

def task_voices(chat_id):
    provider = (config.TTS_PROVIDER or 'edge').lower().strip()
    send_message("🎙 Загружаю список голосов (provider={})...".format(provider), chat_id)
    try:
        if provider in ('eleven', 'elevenlabs', '11labs'):
            voices = eleven_list_voices()
            lines = ["• {} — <code>{}</code>".format(v['name'], v['voice_id']) for v in voices[:25]]
            send_message("🎙 <b>Голоса ElevenLabs:</b>\n\n" + "\n".join(lines), chat_id)
        else:
            import asyncio
            import edge_tts as _etts
            all_v = asyncio.run(_etts.list_voices())
            lang_key = os.environ.get('TTS_LANGUAGE', 'ru').lower()
            lang_voices = [v for v in all_v if v.get('Locale', '').lower().startswith(lang_key)][:25]
            lines = ["• <code>{}</code>".format(v['ShortName']) for v in lang_voices]
            send_message(
                "🎙 <b>Голоса edge-tts ({}):</b>\n\n".format(lang_key.upper()) +
                "\n".join(lines) +
                "\n\n<i>Скопируй ShortName → 🎙 Сменить голос</i>",
                chat_id)
    except Exception as e:
        send_message("❌ Ошибка: {}".format(e), chat_id)


# ══════════════════════════════════════════════════════════════
#  ОБРАБОТЧИК ТЕКСТОВЫХ СООБЩЕНИЙ
# ══════════════════════════════════════════════════════════════

def _run_code_pipeline(chat_id, sess):
    """Запускает pipeline агент-кодера. После завершения сессия остаётся активной."""
    send_message(
        f"🚀 <b>Запускаю!</b>\n"
        f"Задача: <i>{sess.task[:80]}</i>\n"
        f"Файлов: {len(sess.files)}",
        chat_id
    )
    def _run(_sess=sess):
        _gs.task_start(chat_id)
        try:
            try: from agent_core import _llm_call as llm_fn
            except Exception: llm_fn = None
            from agent_session import execute_pipeline, close_session
            sm = make_status(chat_id, send_message, edit_message)
            result = execute_pipeline(_sess, on_status=sm.make_on_status(), llm_caller=llm_fn)
            sm.done(f"{'✅' if result.get('ok') else '⚠️'} Готово")
        except Exception as exc:
            send_message(f"❌ {exc}", chat_id)
            result = {'artifacts':[], 'errors':[str(exc)], 'ok':False, 'zip_path':None}
        finally:
            _gs.task_done(chat_id)
        # Отправляем только ZIP (единый архив: код + вывод + файлы)
        zip_sent = False
        if result.get('zip_path') and os.path.exists(result['zip_path']):
            try:
                send_document(result['zip_path'], caption="📦 <b>Все результаты (код + вывод)</b>", chat_id=chat_id)
                zip_sent = True
            except Exception:
                pass
        # Если ZIP не отправился — fallback: шлём артефакты по одному
        if not zip_sent:
            for art in result.get('artifacts', []):
                if os.path.exists(art.get('path', '')):
                    try: send_document(art['path'], caption=f"📎 {art['name']}", chat_id=chat_id)
                    except Exception: pass
        # Переходим в STAGE_WAIT_FILES — сессия остаётся живой для следующей задачи
        from agent_session import STAGE_WAIT_FILES, get_session
        next_stage = result.get('next_stage', STAGE_WAIT_FILES)
        if next_stage == STAGE_WAIT_FILES:
            try:
                sess = get_session(chat_id)
                if sess:
                    sess.files = []
                    sess.task = ''
                    sess.stage = STAGE_WAIT_FILES
                    sess.fix_history = []
            except Exception:
                pass
        else:
            from agent_session import close_session
            close_session(chat_id)
        # Сессия code_session остаётся — ждём следующую задачу
        _wait_state[chat_id] = 'code_session'
        errs = result.get('errors', [])
        send_message(
            f"{'✅' if result.get('ok') else '⚠️'} <b>Готово</b>"
            + (f" · {len(result.get('artifacts',[]))} файлов" if result.get('artifacts') else "")
            + (f" · ⚠️ {len(errs)} ошибок" if errs else "")
            + "\n\n💬 <i>Пиши следующую задачу или нажми стоп</i>",
            chat_id,
            reply_markup=kb([btn("🔴 Стоп", "agent_stop_code")])
        )
    _run_in_thread(_run)


def _handle_agent_message(chat_id, text, mode):
    """Обрабатывает сообщение внутри активной ИИ-сессии."""
    # ── Billing gate ──────────────────────────────────────────────────────
    bm = BillingManager(chat_id)
    ok, err = bm.can_run_task()
    if not ok:
        send_message(err, chat_id, reply_markup=kb(
            [btn("💳 Тарифы и кредиты", "billing:status")],
            [btn("◀️ Меню", "menu")],
        ))
        return
    try:
        user_role = get_role(chat_id) if ROLES_ENABLED else 'user'
        user_plan = 'free'
        try:
            from agent_memory import AgentMemory
            s = AgentMemory(chat_id).user.recall('plan')
            if s: user_plan = s
        except Exception:
            pass
    except Exception:
        user_role, user_plan = 'user', 'free'

    # ── Режим code — АГЕНТ-КОДЕР (изолирован, только code_agent_run) ─────
    if mode == 'code':
        # Стоп
        if text.strip().lower() in ('стоп','stop','/end','/стоп','отмена','cancel'):
            _wait_state.pop(chat_id, None)
            try:
                from agent_session import close_session; close_session(chat_id)
            except Exception: pass
            send_message("🔴 Сессия агент-кодера завершена.", chat_id,
                         reply_markup=menu_keyboard(chat_id))
            return

        # Ждём токен
        tok = _wait_state.get(chat_id, '')
        if tok.startswith('code_token:'):
            env_key = tok.split(':',1)[1]
            os.environ[env_key] = text.strip()
            task = _pending_agent_task.pop(chat_id, {}).get('task','')
            _wait_state[chat_id] = 'code_session'
            send_message("🔑 Токен принят, запускаю...", chat_id)
            if task: _run_in_thread(_run_code_task, chat_id, task)
            return

        # Если есть накопленные файлы и сказали "готово" — pipeline с файлами
        from agent_session import is_ready_trigger, get_session
        if is_ready_trigger(text):
            sess = get_session(chat_id)
            if sess and sess.files:
                _run_code_pipeline(chat_id, sess)
            else:
                send_message("📝 Напиши задачу.", chat_id,
                             reply_markup=kb([btn("🔴 Стоп","agent_stop_code")]))
                _wait_state[chat_id] = 'code_session'
            return

        # Нужен ли токен?
        tl = text.lower()
        for kw,(env_k,lbl) in [
            ('telegram bot',('BOT_TOKEN','токен Telegram бота (@BotFather)')),
            ('telegram',    ('BOT_TOKEN','токен Telegram бота (@BotFather)')),
            ('openai',      ('OPENAI_API_KEY','OpenAI API key')),
            ('gemini',      ('GEMINI_API_KEY','Gemini API key')),
            ('discord',     ('DISCORD_TOKEN','Discord bot token')),
            ('stripe',      ('STRIPE_KEY','Stripe API key')),
            ('github',      ('GITHUB_TOKEN','GitHub Personal Access Token')),
        ]:
            if kw in tl and not os.environ.get(env_k):
                _pending_agent_task[chat_id] = {'task': text}
                _wait_state[chat_id] = f'code_token:{env_k}'
                send_message(
                    f"🔑 <b>Нужен токен</b>\n\nЗадача требует <b>{lbl}</b>.\n"
                    f"Отправь токен следующим сообщением:",
                    chat_id,
                    reply_markup=kb([btn("⏭ Пропустить","_agent_go"),
                                     btn("🔴 Стоп","agent_stop_code")])
                )
                return

        # Запускаем сразу — как раньше, через code_agent_run
        _wait_state[chat_id] = 'code_session'
        _run_in_thread(_run_code_task, chat_id, text)
        return

    # ── Режим smith — АГЕНТ_СМИТ (agent_session pipeline) ────────────────
    if mode == 'smith':
        from agent_session import (get_session, is_ready_trigger,
                                    is_cancel_trigger)
        if is_cancel_trigger(text) or text.strip().lower() in ('стоп','stop'):
            from agent_session import close_session; close_session(chat_id)
            _wait_state.pop(chat_id, None)
            send_message("❌ Задача СМИТА отменена.", chat_id,
                         reply_markup=menu_keyboard(chat_id))
            return
        if is_ready_trigger(text):
            sess = get_session(chat_id)
            if sess and sess.task: _run_code_pipeline(chat_id, sess)
            return
        sess = get_session(chat_id)
        if sess:
            sess.task = (sess.task or '') + '\n' + text
            send_message("📝 Добавлено. Напиши <b>готово</b> для запуска.",
                         chat_id, reply_markup=kb([btn("🚀 Готово","_agent_go"),
                                                    btn("❌ Отмена","adm:close_agent")]))
        return

    # ── Режим chat — используем agent_core pipeline ───────────────────────
    def _do_agent():
        if AGENT_CORE_ENABLED:
            # Показываем статус в реальном времени
            status_msgs = []
            last_status_id = [None]

            def on_status(msg):
                status_msgs.append(msg)
                try:
                    if last_status_id[0]:
                        edit_message(chat_id, last_status_id[0], msg)
                    else:
                        r = send_message(f"⏳ {msg}", chat_id)
                        if isinstance(r, dict) and 'result' in r:
                            last_status_id[0] = r['result'].get('message_id')
                except Exception:
                    pass

            result = _agent_core.run(
                task=text,
                chat_id=chat_id,
                user_id=chat_id,
                mode='auto',
                on_status=on_status,
            )

            # Удаляем статус-сообщение
            if last_status_id[0]:
                try:
                    from telegram_client import delete_message
                    delete_message(chat_id, last_status_id[0])
                except Exception:
                    pass

            # Отправляем результат
            final_text = _agent_core.status_text(result)
            final_text = _strip_think(final_text)
            send_message(final_text, chat_id, reply_markup=chat_control_keyboard())

            # Отправляем артефакты
            artifacts = result.get('artifacts', [])
            if artifacts:
                from telegram_client import send_document
                send_message(f"📎 Отправляю {len(artifacts)} файлов...", chat_id)
                for path in artifacts[:10]:
                    import os as _os
                    if _os.path.exists(path):
                        send_document(path, caption=f"📎 {_os.path.basename(path)}", chat_id=chat_id)

            # Показываем шаги если их несколько
            steps = result.get('steps', [])
            if steps and len(steps) > 1:
                icons = {True: "✅", False: "❌"}
                summary = "📊 <b>Шаги:</b>\n" + "\n".join(
                    f"{icons[s.get('ok',True)]} {s.get('tool','?')}: {str(s.get('result',''))[:60]}"
                    for s in steps
                )
                send_message(summary, chat_id)

        else:
            # Fallback: старый путь
            try:
                tool_keywords = [
                    'озвучь','произнеси','tts','собери видео','создай видео',
                    'найди в интернете','поищи','скачай страницу','установи пакет',
                    'создай бота','запусти','выполни код','напиши модуль',
                ]
                use_tools = TOOLS_ENABLED and any(kw in text.lower() for kw in tool_keywords)
                if use_tools:
                    send_message("🔧 Агент с инструментами...", chat_id)
                    final, results = run_agent_with_tools(
                        chat_id, text,
                        on_status=lambda m: send_message(m, chat_id),
                    )
                    if final:
                        send_message(_strip_think(final)[:3500], chat_id,
                                     reply_markup=chat_control_keyboard())
                else:
                    from chat_agent import chat_respond
                    reply = _strip_think(chat_respond(chat_id, text))
                    send_message(reply[:4000], chat_id, reply_markup=chat_control_keyboard())
            except Exception as e:
                send_message(f"❌ Ошибка: {e}", chat_id)

    _run_in_thread(_do_agent)


def _run_code_task(chat_id, text, proj_mode=None):
    """Запускает агент-кодер, отправляет вывод по частям, собирает zip."""

    def on_status(msg):
        send_message(msg, chat_id)

    result = code_agent_run(chat_id, text, on_status=on_status, proj_mode=proj_mode)
    formatted = format_code_result(result)

    # Шапка с кодом (может быть длинной — режем на 4096)
    _send_chunked(chat_id, formatted)

    # Полный вывод скрипта — отправляем по частям без обрезания
    full_output = result.get('_full_output', '')
    sent_chunks = []
    if full_output and full_output != '(нет вывода)':
        label = "Результат:" if result.get('success') else "Ошибка:"
        header = "<b>{}:</b>\n<pre>".format(label)
        footer = "</pre>"
        chunk_size = 4000 - len(header) - len(footer)

        lines = full_output.splitlines(keepends=True)
        current = ""
        part = 1
        total_parts = max(1, (len(full_output) + chunk_size - 1) // chunk_size)

        for line in lines:
            if len(current) + len(line) > chunk_size:
                chunk_text = header + _esc(current.rstrip()) + footer
                if total_parts > 1:
                    chunk_text += " <i>({}/{})</i>".format(part, total_parts)
                send_message(chunk_text, chat_id)
                sent_chunks.append(current)
                current = line
                part += 1
            else:
                current += line

        if current.strip():
            chunk_text = header + _esc(current.rstrip()) + footer
            if total_parts > 1:
                chunk_text += " <i>({}/{})</i>".format(part, total_parts)
            send_message(chunk_text, chat_id)
            sent_chunks.append(current)

    # Файлы созданные агентом
    files = result.get('files', [])
    task_type = result.get('_task_type', '')

    # ── Специальная обработка для video-агента ──────────────────────
    if task_type == 'video':
        if full_output:
            send_message(full_output, chat_id)

        if files:
            fpath = files[0]
            if os.path.exists(fpath):
                fsize_mb = result.get('_fsize_mb', 0)
                fmt      = result.get('_video_fmt', 'mp4')
                title    = result.get('_video_title', os.path.basename(fpath))
                icon     = '🎵' if fmt == 'mp3' else '🎬'
                caption  = "{} {} ({:.1f} MB)".format(icon, title, fsize_mb)

                tg_limit = 49
                if fsize_mb <= tg_limit:
                    send_message("📤 Отправляю файл...", chat_id)
                    try:
                        send_document(fpath, caption=caption, chat_id=chat_id)
                    except Exception as e:
                        send_message("⚠️ Не удалось отправить через Telegram: {}\n"
                                     "Попробуй скачать по туннельной ссылке.".format(e), chat_id)
                else:
                    send_message(
                        "⚠️ Файл {:.1f} MB — слишком большой для Telegram API (лимит ~50 MB).\n"
                        "Файл сохранён локально: <code>{}</code>".format(
                            fsize_mb, os.path.basename(fpath)), chat_id)

                # Туннельная ссылка для крупных файлов или как доп. вариант
                try:
                    import fish_bot_state as _fbs
                    tunnel_url = (_fbs.tunnel_url or _fbs.bore_url or
                                  _fbs.ngrok_url or _fbs.serveo_url)
                    if tunnel_url:
                        send_message(
                            "🌍 Также доступен через туннель:\n"
                            "<code>{}/download/{}</code>".format(
                                tunnel_url.rstrip('/'),
                                os.path.basename(fpath)), chat_id)
                except Exception:
                    pass
            else:
                send_message("❌ Файл не найден на диске.", chat_id)
        elif not result.get('success'):
            pass  # ошибка уже показана через _full_output / on_status

        send_message("✅ <b>Готово.</b> Сессия активна — пиши следующую задачу.", chat_id, reply_markup=chat_control_keyboard())
        return

    # ── Специальная обработка для file-агента ──────────────────────
    if task_type == 'file':
        # Сводка уже в _full_output — показываем её
        if full_output:
            send_message(full_output, chat_id)

        # Отправляем каждый файл
        if files:
            send_message("📎 <b>Отправляю файлы ({} шт.)...</b>".format(len(files)), chat_id)
            for fpath in files:
                if os.path.exists(fpath) and os.path.isfile(fpath):
                    try:
                        ext = os.path.splitext(fpath)[1].lower()
                        icons = {'.txt':'📄','.md':'📝','.csv':'📊',
                                 '.docx':'📃','.zip':'📦','.rar':'📦'}
                        icon = icons.get(ext, '📎')
                        caption = "{} {}".format(icon, os.path.basename(fpath))
                        send_document(fpath, caption=caption, chat_id=chat_id)
                    except Exception as e:
                        send_message("⚠️ Не удалось отправить {}: {}".format(
                            os.path.basename(fpath), e), chat_id)

        # Туннельная ссылка — если файлы доступны через веб-сервер
        try:
            import fish_bot_state as _fbs
            tunnel_url = _fbs.tunnel_url or _fbs.bore_url or _fbs.ngrok_url or _fbs.serveo_url
            if tunnel_url:
                send_message(
                    "🌍 Файлы также доступны через туннель:\n"
                    "<code>{}</code>".format(tunnel_url),
                    chat_id)
        except Exception:
            pass

        send_message("✅ <b>Готово.</b> Сессия активна — пиши следующую задачу.", chat_id, reply_markup=chat_control_keyboard())
        return

    # ── Стандартная обработка (скрипты, проекты) ──────────────────
    all_items = list(files)
    zip_to_send = None

    if sent_chunks or files:
        import zipfile as _zf, time as _time
        ts = _time.strftime('%H%M%S')
        zip_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'agent_projects', 'results'
        )
        os.makedirs(zip_dir, exist_ok=True)
        zip_path = os.path.join(zip_dir, 'result_{}.zip'.format(ts))

        with _zf.ZipFile(zip_path, 'w', _zf.ZIP_DEFLATED) as zf:
            code = result.get('code', '')
            if code:
                zf.writestr('script.py', code)
            if full_output:
                zf.writestr('output.txt', full_output)
            for fpath in files:
                if os.path.exists(fpath):
                    zf.write(fpath, os.path.basename(fpath))
        zip_to_send = zip_path

    if files:
        send_message("📎 <b>Отправляю файлы ({} шт.)...</b>".format(len(files)), chat_id)
        for fpath in files:
            if os.path.exists(fpath) and os.path.isfile(fpath):
                try:
                    _send_generated_artifact(chat_id, fpath, caption="📄 {}".format(os.path.basename(fpath)))
                except Exception as e:
                    send_message("⚠️ {}".format(e), chat_id)

    if zip_to_send and os.path.exists(zip_to_send):
        send_message("📦 <b>Итоговый архив (код + вывод + файлы):</b>", chat_id)
        _send_generated_artifact(chat_id, zip_to_send, caption="📦 result.zip")

    # Оставляем code_session активным — юзер пишет следующую задачу
    _wait_state[chat_id] = 'code_session'
    send_message(
        "✅ <b>Задача выполнена.</b>\n"
        "<i>Пиши следующую задачу или нажми стоп.</i>",
        chat_id,
        reply_markup=kb(
            [btn("📎 + Файлы к задаче",   "coder:files_hint")],
            [btn("🔴 Завершить сессию",    "agent_stop_code")],
        )
    )


def _send_chunked(chat_id, text, chunk_size=4096):
    """Отправляет длинный текст по частям."""
    if not text.strip():
        return
    for i in range(0, len(text), chunk_size):
        send_message(text[i:i+chunk_size], chat_id)


def _esc(text):
    import html
    return html.escape(str(text))


def _send_generated_artifact(chat_id, fpath, caption=None):
    """Безопасно отправляет артефакт, не пытаясь мешать binary в текст."""
    try:
        ext = os.path.splitext(fpath)[1].lower()
        caption = caption or ("📎 " + os.path.basename(fpath))
        # В этом проекте telegram_client стабильно умеет sendDocument.
        # GIF/PNG/JPG тоже шлём как документ, чтобы не ломать старый стек.
        return send_document(fpath, caption=caption, chat_id=chat_id)
    except Exception as e:
        send_message("⚠️ Не удалось отправить {}: {}".format(os.path.basename(fpath), e), chat_id)
        return False


def _show_quick_provider(chat_id):
    """Быстрая смена провайдера — показывает кнопки топ-провайдеров."""
    from llm_checker import RECOMMENDED

    # Популярные провайдеры с рекомендуемыми моделями
    QUICK = [
        ('mistral',   'mistral-small-latest',          'Mistral Small'),
        ('groq',      'llama-3.3-70b-versatile',       'Groq Llama-3.3'),
        ('deepseek',  'deepseek-chat',                 'DeepSeek V3'),
        ('openrouter','deepseek/deepseek-chat:free',   'OpenRouter Free'),
        ('gemini',    'gemini-2.0-flash',              'Gemini Flash'),
        ('openai',    'gpt-4o-mini',                   'GPT-4o Mini'),
        ('cerebras',  'llama-3.3-70b',                 'Cerebras Fast'),
        ('ollama',    'llama3.2',                      'Ollama Local'),
    ]

    rows = []
    for provider, model, label in QUICK:
        active = "✅ " if config.LLM_PROVIDER == provider else ""
        rows.append([btn("{}{}".format(active, label), "quickllm:{}:{}".format(provider, model))])

    rows.append([btn("🔍 Все провайдеры", "llm_check"), btn("🔄 Обновить", "llm_discover")])
    rows.append([btn("✏️ Вручную /setllm", "noop")])

    send_message(
        "🧠 <b>Смена провайдера</b>\n"
        "Текущий: <b>{} / {}</b>\n\n"
        "Быстрый выбор (ключи берутся из .env автоматически):".format(
            config.LLM_PROVIDER, config.LLM_MODEL),
        chat_id, reply_markup=kb(*rows)
    )


