"""
bot_callbacks.py — Обработчики inline-кнопок BlackBugsAI
"""
# AUTO-SPLIT from bot.py — do not edit manually, use bot.py as source of truth
import os, sys, re, json, time, random, threading, subprocess, shutil
import config
from telegram_client import (
    send_message, edit_message, answer_callback, send_document,
    delete_webhook,
)
try:
    from agent_roles import get_role, has_perm, perm_error, get_user_limits
    ROLES_ENABLED = True
except ImportError:
    ROLES_ENABLED = False
    def get_role(cid): return 'user'
    def has_perm(cid, p): return True
    def perm_error(p, cid): return "🚫 Нет доступа"
from roles import role_icon, role_label

from bot_ui import kb, btn, back_btn, btn_model, menu_keyboard, chat_control_keyboard
from bot_handlers import _handle_agent_message, _run_code_task, _run_code_pipeline

def handle_callback(cq):
    """Центральный роутер для всех нажатий inline-кнопок."""
    cb_id   = cq['id']
    data    = cq.get('data', '')
    chat_id = str(cq['message']['chat']['id'])
    msg_id  = cq['message']['message_id']

    # ══ ГЕЙТ АВТОРИЗАЦИИ ══════════════════════════════════════════════════
    if not is_authenticated(chat_id):
        action_check = data.split(':')[0]
        PIN_ACTIONS = ('captcha_new', 'captcha_hint',
                       'pin_digit', 'pin_ok', 'pin_del', 'pin_forgot')
        if action_check in PIN_ACTIONS:
            from auth_module import auth_handle_callback as _ahcb
            _ahcb(chat_id, data)
            answer_callback(cb_id)
            # Если после обработки юзер авторизован — показываем меню
            if is_authenticated(chat_id):
                send_message(_current_status_text(chat_id), chat_id, reply_markup=menu_keyboard(chat_id))
            return
        answer_callback(cb_id, "🔒 Требуется авторизация", alert=True)
        try:
            step, _ = auth_state_get(chat_id)
        except Exception:
            step = 'idle'
        if step == 'idle':
            auth_start(chat_id)
        return
    # ══ КОНЕЦ ГЕЙТА ════════════════════════════════════════════════════════

    # Разбираем формат "action" или "action:arg"
    action, _, arg = data.partition(':')

    try:
        _route_callback(action, arg, cb_id, chat_id, msg_id)
    except Exception as e:
        # Любая ошибка — сразу показываем пользователю, не глотаем молча
        print("❌ Callback error [{}]: {}".format(data, e), flush=True)
        answer_callback(cb_id, "❌ Ошибка: {}".format(str(e)[:100]), alert=True)
        send_message("❌ Ошибка при обработке кнопки:\n<code>{}</code>".format(e), chat_id)


def _route_smith(arg, cb_id, chat_id, msg_id):
    """Обработчик всех АГЕНТ_СМИТ колбэков."""

    if arg == 'smith_menu':
        edit_message(chat_id, msg_id,
            "🕵️ <b>АГЕНТ_СМИТ</b> — выбери режим:",
            reply_markup=kb(
                [btn("💻 Агент-Кодер (все функции)", "adm:smith_coder")],
                [btn("══ 🖊 КОД ══",              "adm_noop")],
                [btn("🤖 Авто-задача",            "adm:smith:auto"),
                 btn("🧩 Scaffold проект",        "adm:smith:scaffold")],
                [btn("🔧 Patch / Багфикс",        "adm:smith:patch"),
                 btn("📋 Plan-first",             "adm:smith:plan_first")],
                [btn("══ 🤖 TELEGRAM ══",         "adm_noop")],
                [btn("🤖 Telegram бот",           "adm:smith:tg_bot"),
                 btn("🔌 Aiogram бот",            "adm:smith:aiogram_bot")],
                [btn("🎮 Inline-бот",             "adm:smith:inline_bot"),
                 btn("🔔 Уведомления",            "adm:smith:notif_bot")],
                [btn("══ 🌐 ВЕБ ══",              "adm_noop")],
                [btn("⚡ FastAPI сервис",          "adm:smith:fastapi"),
                 btn("🕸 Flask сервер",            "adm:smith:flask")],
                [btn("🕷 Scraper/Парсер",          "adm:smith:scraper"),
                 btn("📡 API клиент",             "adm:smith:api_client")],
                [btn("══ 🖥 АВТОМАТИЗАЦИЯ ══",    "adm_noop")],
                [btn("⌨️ pynput скрипт",          "adm:smith:pynput"),
                 btn("🖱 pyautogui скрипт",       "adm:smith:pyautogui")],
                [btn("⏰ Планировщик",             "adm:smith:scheduler"),
                 btn("🖥 Desktop утилита",        "adm:smith:desktop")],
                [btn("══ 📊 ДАННЫЕ ══",           "adm_noop")],
                [btn("📊 pandas / Excel",         "adm:smith:pandas"),
                 btn("🗄 SQLite / DB",            "adm:smith:sqlite")],
                [btn("📈 Графики matplotlib",     "adm:smith:plots"),
                 btn("🔄 ETL pipeline",           "adm:smith:etl")],
                [btn("══ 🔐 БЕЗОПАСНОСТЬ ══",     "adm_noop")],
                [btn("🔐 Шифрование",             "adm:smith:crypto"),
                 btn("🔑 JWT / Auth",             "adm:smith:jwt")],
                [btn("══ 🎨 МЕДИА ══",            "adm_noop")],
                [btn("🎬 Видео из фото",          "adm:smith:slideshow"),
                 btn("🎙 TTS озвучка",            "adm:smith:tts_task")],
                [btn("🖼 Обработка картинок",     "adm:smith:image_proc"),
                 btn("🎵 Аудио обработка",        "adm:smith:audio_proc")],
                [btn("══ 📦 УТИЛИТЫ ══",          "adm_noop")],
                [btn("🗜 ZIP / архив",             "adm:smith:archiver"),
                 btn("📧 Email скрипт",           "adm:smith:email")],
                [btn("🐳 Docker helper",          "adm:smith:docker"),
                 btn("📝 Markdown / PDF",         "adm:smith:report")],
                [btn("◀️ Адм. меню",              "admin")],
            ))

    elif arg == 'smith_coder':
        edit_message(chat_id, msg_id,
            "🕵️💻 <b>АГЕНТ_СМИТ — Кодер</b>\n\n"
            "🖊 <b>Написать код</b> — опиши задачу, Смит напишет, протестирует и отдаст zip\n"
            "🔍 <b>Ревью кода</b> — найдёт баги, уязвимости, code-smell\n"
            "🔧 <b>Исправить ошибку</b> — вставь код + traceback → авто-фикс x15\n"
            "📦 <b>Создать проект</b> — полная структура с файлами, тестами, README\n"
            "🏖 <b>Sandbox</b> — выполни любой Python-код прямо сейчас\n"
            "🧩 <b>Scaffold</b> — полный шаблон проекта\n"
            "🔄 <b>Рефакторинг</b> — улучшит код, добавит типы\n"
            "🧪 <b>Тесты</b> — напишет pytest тесты\n"
            "📊 <b>Анализ кода</b> — сложность, зависимости\n"
            "🐳 <b>Dockerize</b> — Dockerfile + compose\n\n"
            f"Модель: <b>{config.LLM_PROVIDER} / {config.LLM_MODEL}</b>",
            reply_markup=kb(
                [btn("🖊 Написать код",        "adm:sc:write"),
                 btn("🔍 Ревью кода",          "adm:sc:review")],
                [btn("🔧 Исправить ошибку",    "adm:sc:fix"),
                 btn("📦 Создать проект",      "adm:sc:project")],
                [btn("🏖 Sandbox",             "adm:sc:sandbox"),
                 btn("🤖 Инструменты бота",    "adm:sc:bot_tools")],
                [btn("📁 Создать файл",        "adm:sc:file"),
                 btn("🧩 Scaffold",            "adm:sc:scaffold")],
                [btn("🔄 Рефакторинг",         "adm:sc:refactor"),
                 btn("🧪 Написать тесты",      "adm:sc:tests")],
                [btn("📊 Анализ кода",         "adm:sc:analyze"),
                 btn("🐳 Dockerize",           "adm:sc:dockerize")],
                [btn("◀️ АГЕНТ_СМИТ",          "adm:smith_menu")],
            ))

    elif arg == 'close_agent':
        try:
            from agent_session import close_session
            close_session(chat_id)
        except ImportError:
            pass
        _wait_state.pop(chat_id, None)
        edit_message(chat_id, msg_id, "🤖 Сессия агента закрыта.",
                     reply_markup=kb([btn("◀️ Адм. меню","admin")]))

    elif arg.startswith('smith:'):
        smith_mode = arg.split(':', 1)[1]
        SMITH_TASKS = {
            'auto':         "Опиши задачу для АГЕНТ_СМИТ:",
            'scaffold':     "Опиши что создать (название, функции):",
            'patch':        "Вставь код + описание бага:",
            'plan_first':   "Опиши задачу — сначала покажу план:",
            'tg_bot':       "Телеграм бот на python-telegram-bot v20 с командами /start /help и inline-кнопками",
            'aiogram_bot':  "Telegram бот на aiogram 3.x с FSM и inline-клавиатурами",
            'inline_bot':   "Telegram inline-бот с обработкой inline-запросов",
            'notif_bot':    "Telegram бот с уведомлениями по расписанию через schedule",
            'fastapi':      "FastAPI REST API с CRUD эндпоинтами и pydantic моделями",
            'flask':        "Flask веб-приложение с роутами и REST API",
            'scraper':      "Веб-парсер на requests+BeautifulSoup с сохранением в JSON и CSV",
            'api_client':   "Python REST API клиент с retry, timeout, auth и логированием",
            'pynput':       "Python автоматизация клавиатуры и мыши через pynput: горячие клавиши, макросы",
            'pyautogui':    "GUI автоматизация через pyautogui: поиск, клики, скриншоты",
            'scheduler':    "Планировщик задач через APScheduler с cron-выражениями",
            'desktop':      "Десктопный скрипт для автоматизации системных задач через psutil",
            'pandas':       "Обработка данных: pandas read_csv/excel, фильтры, группировка, экспорт",
            'sqlite':       "Работа с SQLite: создание таблиц, CRUD, sqlalchemy ORM",
            'plots':        "Визуализация данных: matplotlib/seaborn графики, сохранение в PNG",
            'etl':          "ETL pipeline: чтение, трансформация, загрузка в целевой формат",
            'crypto':       "Шифрование файлов через cryptography (Fernet) и hashlib",
            'jwt':          "JWT авторизация: генерация токенов, верификация, refresh",
            'slideshow':    "Собери видео-слайдшоу из изображений. Пришли фото после описания.",
            'tts_task':     "Введи текст для озвучки через edge-tts:",
            'image_proc':   "Обработка изображений через Pillow: resize, crop, filter, watermark",
            'audio_proc':   "Обработка аудио через pydub: конвертация, обрезка, нормализация",
            'archiver':     "Утилита для ZIP/TAR архивов с прогресс-баром",
            'email':        "Отправка email через smtplib с HTML-шаблоном и вложениями",
            'docker':       "Dockerfile + docker-compose.yml для Python приложения",
            'report':       "Генератор отчётов в Markdown и PDF через jinja2",
        }
        task_text = SMITH_TASKS.get(smith_mode, "Опиши задачу:")
        needs_input = smith_mode in ('auto', 'scaffold', 'patch', 'plan_first',
                                      'tts_task', 'slideshow')

        try:
            from agent_session import create_session, STAGE_WAIT_FILES
            sess = create_session(chat_id)
            sess.stage = STAGE_WAIT_FILES
        except Exception:
            pass

        if needs_input:
            _wait_state[chat_id] = 'adm_agent_task'
            edit_message(chat_id, msg_id,
                f"🕵️ <b>АГЕНТ_СМИТ</b> [{smith_mode}]\n\n{task_text}",
                reply_markup=kb([btn("❌ Отмена","adm:close_agent")]))
        else:
            edit_message(chat_id, msg_id,
                f"🕵️ Запускаю: <i>{task_text[:100]}</i>\n\n⏳...",
                reply_markup=kb([btn("❌ Отмена","adm:close_agent")]))
            def _run(_t=task_text, _s=arg):
                try:
                    from agent_session import get_session, create_session, execute_pipeline, close_session, STAGE_WAIT_FILES
                    s = get_session(chat_id) or create_session(chat_id)
                    s.task = _t; s.stage = STAGE_WAIT_FILES; s.touch()
                    from agent_core import _llm_call as llm_fn
                except Exception: llm_fn = None
                try:
                    from agent_session import get_session, create_session, execute_pipeline, close_session, STAGE_WAIT_FILES
                    s2 = get_session(chat_id) or create_session(chat_id)
                    s2.task = _t; s2.stage = STAGE_WAIT_FILES
                    result = execute_pipeline(s2, on_status=lambda m: send_message(m, chat_id), llm_caller=llm_fn)
                    for art in result.get('artifacts', []):
                        if os.path.exists(art.get('path','')):
                            try: send_document(art['path'], caption=f"📎 {art['name']}", chat_id=chat_id)
                            except Exception: pass
                    if result.get('zip_path') and os.path.exists(result['zip_path']):
                        try: send_document(result['zip_path'], caption="📦 Результат", chat_id=chat_id)
                        except Exception: pass
                    errs = result.get('errors', [])
                    send_message(
                        f"{'✅' if result.get('ok') else '⚠️'} СМИТ завершил\n"
                        f"Артефактов: {len(result.get('artifacts',[]))}"
                        + (f"\nОшибок: {len(errs)}" if errs else ""),
                        chat_id,
                        reply_markup=kb([btn("🕵️ Ещё","adm:smith_menu")],[btn("◀️ Адм","admin")])
                    )
                    close_session(chat_id)
                except Exception as e:
                    send_message(f"❌ {e}", chat_id)
            _run_in_thread(_run)

    elif arg.startswith('sc:'):
        sc_mode = arg.split(':', 1)[1]
        SC_PROMPTS = {
            'write':    "🖊 Опиши задачу — Смит напишет и протестирует код:",
            'review':   "🔍 Вставь код для ревью:",
            'fix':      "🔧 Вставь код + traceback ошибки:",
            'project':  "📦 Опиши проект (название, функции, структура):",
            'sandbox':  "🏖 Вставь Python-код для запуска в sandbox:",
            'bot_tools':"🤖 Опиши задачу для агента с инструментами:",
            'file':     "📁 Что создать? (тип, содержимое, название):",
            'scaffold': "🧩 Опиши шаблон проекта (тип: flask/fastapi/bot/cli):",
            'refactor': "🔄 Вставь код для рефакторинга:",
            'tests':    "🧪 Вставь код для которого нужны тесты:",
            'analyze':  "📊 Вставь код для анализа:",
            'dockerize':"🐳 Опиши проект для dockerize:",
        }
        prompt_msg = SC_PROMPTS.get(sc_mode, "Опиши задачу:")
        try:
            from agent_session import create_session, STAGE_WAIT_FILES
            sess = create_session(chat_id)
            sess.stage = STAGE_WAIT_FILES
        except Exception:
            pass
        _wait_state[chat_id] = f'adm_sc_input:{sc_mode}'
        edit_message(chat_id, msg_id,
            f"🕵️💻 <b>СМИТ — {sc_mode.upper()}</b>\n\n{prompt_msg}",
            reply_markup=kb([btn("❌ Отмена","adm:smith_coder")]))


def _route_callback(action, arg, cb_id, chat_id, msg_id):
    """Вся логика роутинга callback-ов."""
    from llm_checker import RECOMMENDED

    # ── Ролевой контроль ─────────────────────────────────────────
    try:
        from roles import has_perm as _hp, perm_denied_msg
        from admin_module import get_role as _gr
        _role = _gr(chat_id)
        def _need(perm: str) -> bool:
            """Проверяет разрешение. Если нет — отправляет сообщение и возвращает False."""
            if _hp(_role, perm):
                return True
            answer_callback(cb_id, "🚫 Нет доступа", alert=True)
            send_message(perm_denied_msg(perm, _role), chat_id,
                         reply_markup=menu_keyboard(chat_id))
            return False
    except Exception:
        _role = 'user'
        def _need(perm): return True

    # Действия требующие конкретных прав
    _PERM_MAP = {
        'agent_chat_start':  'chat',
        'agent_code_start':  'code_agent',
        'agent_code3_start':  'code_agent',
        'menu_image':        'image_gen',
        'menu_tts':          'tts',
        'menu_llm':          'llm_change',
        'menu_fish':         'fish_module',
        'menu_update':       'manage_bots',
        'selfcheck':         'view_logs',
        'run':               'manage_bots',
        'parse':             'manage_bots',
        'env':               'view_env',
        'admin':             'admin_panel',
        'test':              'llm_change',
        'tasks':             'tools_basic',
    }
    if action in _PERM_MAP:
        if not _need(_PERM_MAP[action]):
            return

    # BAN — только штраф и профиль
    if _role == 'ban' and action not in ('pay_fine', 'profile', 'billing', 'menu', 'pin_digit',
                                          'pin_ok', 'pin_del', 'captcha_new'):
        answer_callback(cb_id, "🚫 Аккаунт заблокирован", alert=True)
        return

    # NOOB — только профиль, биллинг, справка
    if _role == 'noob' and action not in ('profile', 'billing', 'help', 'menu', 'pay_fine',
                                           'pin_digit', 'pin_ok', 'pin_del', 'captcha_new'):
        answer_callback(cb_id, "🔰 Нужно повысить роль", alert=True)
        send_message(
            "🔰 <b>Доступ ограничен</b>\n\n"
            "Твоя роль: <b>NOOB</b>\n"
            "Доступно только: профиль и биллинг.\n\n"
            "<i>Обратись к администратору для повышения роли</i>",
            chat_id, reply_markup=menu_keyboard(chat_id))
        return

    # ── Навигация ─────────────────────────────────────────────
    if action == 'menu':
        edit_message(chat_id, msg_id, _current_status_text(chat_id), reply_markup=menu_keyboard(chat_id))
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
        # Показываем модели провайдера и кнопку добавления ключа — 2 клика
        answer_callback(cb_id)
        prov = arg.lower()
        # Проверяем есть ли уже ключ для этого провайдера
        from llm_client import _PROVIDER_KEY_MAP
        key_attr  = _PROVIDER_KEY_MAP.get(prov, 'LLM_API_KEY')
        stored_key = (getattr(config, key_attr, '') or
                      getattr(config, 'LLM_API_KEY', '') or '')
        has_key   = bool(stored_key)

        models = RECOMMENDED.get(prov, [])
        cur_model = config.LLM_MODEL if config.LLM_PROVIDER.lower() == prov else ''

        rows = []
        # Кнопки моделей — 1 на строку (имена бывают длинные)
        for m in models[:8]:
            label = ('✅ ' if m == cur_model else '') + m
            rows.append([btn_model(label, prov, m)])

        # Кнопка ввода ключа
        if prov != 'ollama':
            key_lbl = ('🔑 Обновить ключ' if has_key
                       else '🔑 Добавить API ключ ← НУЖЕН')
            rows.append([btn(key_lbl, 'llm_addkey:{}'.format(prov))])
        else:
            # Ollama без ключа — сразу применяем первую модель
            if not cur_model or config.LLM_PROVIDER.lower() != 'ollama':
                rows.insert(0, [btn('⚡ Применить Ollama (llama3.2)',
                                    'llm_setmodel:ollama:llama3.2')])

        rows.append([btn('✏️ Ввести модель вручную', 'llm_manual:{}'.format(prov))])
        rows.append([back_btn('menu_llm')])

        key_status = ('✅ ключ есть' if has_key
                      else '❌ ключ не задан — нужен для работы')
        edit_message(chat_id, msg_id,
            '🧠 <b>{}</b> | {}'.format(prov.upper(), key_status),
            reply_markup=kb(*rows))

    elif action == 'llm_addkey':
        # Запрос ключа для конкретного провайдера с подсказкой где взять
        answer_callback(cb_id)
        prov = arg.lower()
        key_urls = {
            'groq':       'https://console.groq.com/keys',
            'openai':     'https://platform.openai.com/api-keys',
            'gemini':     'https://aistudio.google.com/apikey',
            'anthropic':  'https://console.anthropic.com/settings/keys',
            'mistral':    'https://console.mistral.ai/api-keys',
            'deepseek':   'https://platform.deepseek.com/api-keys',
            'cerebras':   'https://cloud.cerebras.ai',
            'sambanova':  'https://cloud.sambanova.ai/apis',
            'openrouter': 'https://openrouter.ai/keys',
            'together':   'https://api.together.ai/settings/api-keys',
            'xai':        'https://console.x.ai',
            'cohere':     'https://dashboard.cohere.com/api-keys',
            'hyperbolic': 'https://app.hyperbolic.xyz/settings',
            'huggingface':'https://huggingface.co/settings/tokens',
        }
        url = key_urls.get(prov, '')
        hint = f'\n🔗 Получить ключ: <a href="{url}">{url}</a>' if url else ''
        _wait_state[chat_id] = f'llm_key:{prov}'
        send_message(
            f'🔑 <b>Введи API ключ для {prov.upper()}:</b>{hint}\n\n'
            f'<i>Ключ будет сохранён в .env автоматически</i>',
            chat_id,
            reply_markup=kb([btn('❌ Отмена', f'llm_info:{prov}')]))

    elif action == 'llm_manual':
        # Ввод произвольного имени модели для выбранного провайдера
        answer_callback(cb_id)
        prov = arg.lower()
        _wait_state[chat_id] = f'llm_manual_model:{prov}'
        send_message(
            f'✏️ Введи имя модели для <b>{prov.upper()}</b>:',
            chat_id,
            reply_markup=kb([btn('❌ Отмена', f'llm_info:{prov}')]))

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
        edit_message(chat_id, msg_id, _current_status_text(chat_id), reply_markup=menu_keyboard(chat_id))

    # ══════════════════════════════════════════════════════════
    #  СКАН И АВТО-КОНФИГУРАЦИЯ ПРОВАЙДЕРОВ
    # ══════════════════════════════════════════════════════════
    elif action == 'hub_scan':
        answer_callback(cb_id)
        send_message("🔎 Сканирую провайдеры...", chat_id)
        def _do_hub_scan():
            if _prov_hub:
                text = _prov_hub.format_scan_report()
            else:
                text = "❌ providers_hub недоступен"
            send_message(text, chat_id, reply_markup=kb(
                [btn("⚙️ Авто-конфиг", "hub_autoconfig"),
                 btn("🔌 Тест туннелей", "hub_tunnel_check")],
                [back_btn()],
            ))
        _run_in_thread(_do_hub_scan)

    elif action == 'hub_autoconfig':
        answer_callback(cb_id)
        send_message("⚙️ Авто-конфигурация...", chat_id)
        def _do_hub_autoconfig():
            if not _prov_hub:
                send_message("❌ providers_hub недоступен", chat_id)
                return
            changes = _prov_hub.auto_configure()
            if not changes:
                text = "ℹ️ Конфигурация актуальна, изменений нет."
            else:
                lines = ["✅ <b>Авто-конфигурация применена:</b>\n"]
                for k, v in changes.items():
                    lines.append(f"  • <b>{k}</b>: <code>{v}</code>")
                text = "\n".join(lines)
            send_message(text, chat_id, reply_markup=kb(
                [btn("🔎 Новый скан", "hub_scan"), back_btn()],
            ))
        _run_in_thread(_do_hub_autoconfig)

    elif action == 'hub_tunnel_check':
        answer_callback(cb_id)
        send_message("🔌 Проверяю туннели...", chat_id)
        def _do_tunnel_check():
            import shutil, subprocess
            results = []
            tunnels = [
                ('bore',        'bore',  'bore.pub',     'cargo install bore-cli'),
                ('serveo (ssh)','ssh',   'serveo.net',   'pkg install openssh'),
                ('ngrok',       'ngrok', 'ngrok.com',    'pkg install ngrok'),
                ('cloudflared', 'cloudflared', 'trycloudflare.com', 'pkg install cloudflared'),
            ]
            for name, binary, host, install in tunnels:
                if shutil.which(binary):
                    # Ping check
                    try:
                        r = subprocess.run(
                            ['ping', '-c', '1', '-W', '3', host]
                            if _is_windows() is False else ['ping', '-n', '1', host],
                            capture_output=True, timeout=5
                        )
                        reachable = r.returncode == 0
                    except Exception:
                        reachable = True  # assume ok
                    icon = '✅' if reachable else '⚠️'
                    results.append(f"{icon} <b>{name}</b>: установлен, хост {'доступен' if reachable else 'недоступен'}")
                else:
                    results.append(f"❌ <b>{name}</b>: не установлен → <code>{install}</code>")

            # Check active tunnels
            try:
                fbs = fish_bot_state
                active = []
                if fbs.bore_url:    active.append(f"bore: <code>{fbs.bore_url}</code>")
                if fbs.serveo_url:  active.append(f"serveo: <code>{fbs.serveo_url}</code>")
                if fbs.ngrok_url:   active.append(f"ngrok: <code>{fbs.ngrok_url}</code>")
                if fbs.tunnel_url:  active.append(f"CF: <code>{fbs.tunnel_url}</code>")
                if active:
                    results.append("\n🟢 <b>Активные туннели:</b>")
                    results.extend(active)
                else:
                    results.append("\nℹ️ Активных туннелей нет")
            except Exception:
                pass

            send_message(
                "🔌 <b>Статус туннелей:</b>\n\n" + "\n".join(results),
                chat_id, reply_markup=kb(
                    [btn("🕳 Запустить bore",   "fish:bore_start"),
                     btn("🔑 Запустить serveo", "fish:serveo_start")],
                    [back_btn()],
                ))
        _run_in_thread(_do_tunnel_check)

    elif action == 'hub_set_provider':
        # arg: 'category:provider:model'
        parts = arg.split(':', 2)
        if len(parts) == 3:
            category, provider, model = parts
            answer_callback(cb_id, f"✅ {category}: {provider}")
            if category == 'CODE':
                _update_env('CODE_PROVIDER', provider)
                _update_env('CODE_MODEL', model)
            elif category == 'AGENT':
                _update_env('AGENT_PROVIDER', provider)
                _update_env('AGENT_MODEL', model)
            elif category == 'IMAGE':
                _update_env('IMAGE_PROVIDER', provider)
            elif category == 'TTS':
                config.TTS_PROVIDER = provider
            config.reload()
            edit_message(chat_id, msg_id,
                f"✅ <b>{category}</b> → <code>{provider} / {model}</code>",
                reply_markup=kb([btn("🔎 Скан", "hub_scan"), back_btn()]))
        else:
            answer_callback(cb_id, "❌ Ошибка", alert=True)

    elif action == 'hub_providers_menu':
        # Full providers selection by category
        answer_callback(cb_id)
        category = arg or 'LLM_CHAT'
        if not _prov_hub:
            send_message("❌ providers_hub недоступен", chat_id)
            return
        active = _prov_hub.active_llm(category)
        if not active:
            send_message(f"❌ Нет провайдеров для {category}", chat_id,
                         reply_markup=kb([back_btn()]))
            return
        rows = []
        for p in active[:8]:
            short_cat = category.replace('LLM_', '')
            cb_arg = f"{short_cat}:{p['name']}:{p['model']}"
            rows.append([btn_model(f"{p['name']} / {p['model'][:20]}", p['name'], p['model'])])
        rows.append([back_btn()])
        edit_message(chat_id, msg_id,
            f"📋 <b>Провайдеры {category}:</b>",
            reply_markup=kb(*rows))

    elif action == 'hub_llm_list':
        answer_callback(cb_id)
        if not _prov_hub:
            send_message("❌ providers_hub недоступен", chat_id)
            return
        lines = ["🔎 <b>Все LLM по категориям:</b>\n"]
        for cat, label in [('LLM_CHAT', '💬 Чат'), ('LLM_CODER', '💻 Кодер'), ('LLM_AGENT', '🤖 Агент')]:
            lst = _prov_hub.active_llm(cat)
            if lst:
                names = ', '.join(p['name'] for p in lst[:6])
                lines.append(f"<b>{label}:</b> {names}")
            else:
                lines.append(f"<b>{label}:</b> ❌ нет ключей")
        rows = [
            [btn("⚙️ Авто-конфиг", "hub_autoconfig"),
             btn("🔌 Туннели", "hub_tunnel_check")],
            [btn("💻 Кодер", "hub_providers_menu:LLM_CODER"),
             btn("🤖 Агент", "hub_providers_menu:LLM_AGENT")],
            [back_btn()],
        ]
        edit_message(chat_id, msg_id, "\n".join(lines), reply_markup=kb(*rows))

    elif action == 'hub_tts_menu':
        answer_callback(cb_id)
        if not _prov_hub:
            send_message("❌ providers_hub недоступен", chat_id)
            return
        status = _prov_hub.tts_status()
        lines = ["🎙 <b>TTS провайдеры:</b>\n"]
        rows = []
        for name, info in status.items():
            icon = '✅' if info['available'] else '❌'
            cur = ' ✅' if config.TTS_PROVIDER == name else ''
            lines.append(f"{icon} <b>{name}</b>: {info['desc']}")
            if info['available']:
                rows.append([btn(f"{icon} {name}{cur}", f"hub_set_provider:TTS:{name}:{name}")])
        rows.append([back_btn("menu_tts")])
        edit_message(chat_id, msg_id, "\n".join(lines), reply_markup=kb(*rows))

    elif action == 'hub_image_menu':
        answer_callback(cb_id)
        if not _prov_hub:
            send_message("❌ providers_hub недоступен", chat_id)
            return
        status = _prov_hub.image_status()
        lines = ["🎨 <b>Генерация картинок:</b>\n"]
        rows = []
        for name, info in status.items():
            icon = '✅' if info['available'] else ('🔑' if info['needs_key'] else '⚠️')
            lines.append(f"{icon} <b>{name}</b>: {info['desc']}")
            if info['available']:
                rows.append([btn(f"{icon} {name}", f"hub_set_provider:IMAGE:{name}:{name}")])
            elif info['needs_key']:
                rows.append([btn(f"🔑 Добавить {name.upper()}", f"add_key:{info['env_key']}")])
        rows.append([back_btn("menu_image")])
        edit_message(chat_id, msg_id, "\n".join(lines), reply_markup=kb(*rows))

    elif action == 'bot_stats':
        answer_callback(cb_id, "📈 Статистика...")
        from bot_tools import execute_bot_tool
        def _send(t): send_message(t, chat_id)
        def _sdoc(p): send_document(chat_id, p)
        result = execute_bot_tool('bot_stats', chat_id, _send, _sdoc)
        send_message(result or "📊 Статистика недоступна", chat_id, reply_markup=menu_keyboard(chat_id))

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
            "💻 <b>Кодер</b> — описываешь задачу, агент пишет и запускает Python-код\n"
            "🧩 <b>Кодер 2</b> — классическое меню из automuvie_v4.4\n\n"
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
        from agent_session import create_session, close_session, STAGE_WAIT_FILES
        close_session(chat_id)
        sess = create_session(chat_id)
        sess.stage = STAGE_WAIT_FILES
        _wait_state[chat_id] = 'code_session'
        edit_message(chat_id, msg_id,
            f"💻 <b>АГЕНТ-КОДЕР</b>\n"
            f"<code>{config.LLM_PROVIDER}/{config.LLM_MODEL}</code>\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🖊 <b>Написать задачу</b> — код, картинку, текст, озвучку, поиск\n"
            "🔍 <b>Анализ</b> — файл/код/архив: что это, как улучшить\n"
            "🔧 <b>Фикс</b> — вставь код + traceback → авто-исправление\n"
            "📦 <b>Проект</b> — название → структура → код → ZIP\n"
            "🏖 <b>Sandbox</b> — запусти файл/архив/код прямо сейчас\n"
            "🎬 <b>YouTube</b> — скачать видео или аудио\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "<i>Выбери режим или просто напиши задачу ↓</i>",
            reply_markup=kb(
                [btn("🖊 Написать задачу", "coder:task"),
                 btn("🔍 Анализ",         "coder:analyze")],
                [btn("🔧 Фикс ошибки",   "coder:fix"),
                 btn("📦 Проект",         "coder:project")],
                [btn("🏖 Sandbox",        "coder:sandbox"),
                 btn("🎬 YouTube",        "agent_youtube_start")],
                [btn("🔴 Завершить",      "agent_stop_code"),
                 back_btn("menu_agent")],
            ))

    elif action == 'agent_code3_start' or (action == 'coder3' and not arg):
        answer_callback(cb_id)
        try:
            from agent_coder3 import render_coder3_welcome, build_coder3_menu
            _coder3_text = render_coder3_welcome(config.LLM_PROVIDER, config.LLM_MODEL)
            _coder3_markup = build_coder3_menu(btn, kb, back_btn)
            _edited = edit_message(chat_id, msg_id, _coder3_text, reply_markup=_coder3_markup)
            if not _edited:
                send_message(_coder3_text, chat_id, reply_markup=_coder3_markup)
        except Exception as e:
            send_message('❌ AGENT_CODER3 ошибка: {}'.format(e), chat_id, reply_markup=kb([back_btn('menu_agent')]))

    elif action == 'coder3' and arg:
        answer_callback(cb_id)
        next_mode = arg
        try:
            from agent_coder3 import render_mode_prompt
            _wait_state[chat_id] = 'coder3_input:' + next_mode
            send_message(render_mode_prompt(next_mode), chat_id, reply_markup=kb([btn('❌ Отмена', 'agent_code3_start')]))
        except Exception as e:
            send_message('❌ AGENT_CODER3 ошибка: {}'.format(e), chat_id)

    elif action == 'agent_code2_start':
        answer_callback(cb_id)
        edit_message(chat_id, msg_id,
            "🧩 <b>Агент-кодер 2</b> — классический режим из automuvie_v4.4\n\n"
            "🖊 <b>Написать код</b> — опиши задачу, агент напишет и запустит\n"
            "🔍 <b>Ревью кода</b> — найдёт ошибки и уязвимости\n"
            "🔧 <b>Исправить ошибку</b> — вставь код + traceback\n"
            "📦 <b>Создать проект</b> — многофайловый проект в zip\n"
            "🏖 <b>Sandbox</b> — запусти любой код прямо сейчас\n"
            "🤖 <b>Инструменты бота</b> — агент управляет туннелем, файлами\n"
            "📁 <b>Создать файл</b> — txt/md/csv/docx/zip\n\n"
            "Модель: <b>{} / {}</b>".format(config.LLM_PROVIDER, config.LLM_MODEL),
            reply_markup=kb(
                [btn("🖊 Написать код",       "coder2:write"),
                 btn("🔍 Ревью кода",         "coder2:review")],
                [btn("🔧 Исправить ошибку",   "coder2:fix"),
                 btn("📦 Создать проект",     "coder2:project")],
                [btn("🏖 Sandbox",            "coder2:sandbox"),
                 btn("🤖 Инструменты бота",   "coder2:bot_tools")],
                [btn("📁 Создать файл",       "coder2:file"),
                 btn("🎬 YouTube",            "agent_youtube_start")],
                [back_btn("menu_agent")],
            ))

    # ── AGENT NEO ─────────────────────────────────────────────────────────────
    elif action == 'agent_neo_start':
        answer_callback(cb_id)
        try:
            role = get_role(chat_id)
        except Exception:
            role = 'user'
        if role not in ('god', 'owner', 'adm'):
            send_message("🔒 AGENT NEO доступен только owner/adm.", chat_id,
                         reply_markup=kb([back_btn('menu_agent')]))
            return
        send_message(
            "🧬 <b>AGENT NEO</b> — автономный агент\n\n"
            "Планирует задачи, генерирует инструменты на лету, запускает их в sandbox и возвращает ZIP-артефакт.\n\n"
            "Введи задачу:",
            chat_id,
            reply_markup=kb([btn("❌ Отмена", "menu_agent")])
        )
        _wait_state[chat_id] = 'agent_neo_task'

    elif action == 'agent_neo_locked':
        answer_callback(cb_id)
        send_message("🔒 AGENT NEO требует роль owner или выше.", chat_id,
                     reply_markup=kb([back_btn('menu_agent')]))

    # ── AGENT MATRIX ──────────────────────────────────────────────────────────
    elif action == 'agent_matrix_start':
        answer_callback(cb_id)
        send_message(
            "🔮 <b>AGENT MATRIX</b> — генерация и управление инструментами\n\n"
            "Создаёт кастомные инструменты через LLM, GitHub или hybrid-режим.\n\n"
            "Введи задачу или имя инструмента:",
            chat_id,
            reply_markup=kb([btn("❌ Отмена", "menu_agent")])
        )
        _wait_state[chat_id] = 'agent_matrix_task'

    # ── AGENT MORPHEUS ────────────────────────────────────────────────────────
    elif action == 'agent_morpheus_start':
        answer_callback(cb_id)
        try:
            role = get_role(chat_id)
        except Exception:
            role = 'user'
        if role not in ('god', 'owner'):
            send_message("🔒 AGENT MORPHEUS — только owner/god.", chat_id,
                         reply_markup=kb([back_btn('menu_agent')]))
            return
        send_message(
            "🟣 <b>AGENT MORPHEUS</b> — системный агент\n\n"
            "apt · pip · docker · systemctl · shell · файловая система.\n"
            "Авто-фиксит зависимости. Управляет Docker-контейнерами.\n\n"
            "⚠️ <b>Root-уровень — используй осторожно!</b>\n\nВведи команду:",
            chat_id,
            reply_markup=kb([btn("❌ Отмена", "menu_agent")])
        )
        _wait_state[chat_id] = 'agent_morpheus_task'

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
        from agent_session import get_session, create_session, close_session, STAGE_WAIT_FILES

        # Режимы — устанавливаем задачу и ждём ввода от юзера
        CODER_MODES = {
            'task':       ('🖊 <b>Напиши задачу</b>\n\nМожно всё: код, картинка, текст, поиск, озвучка.', None),
            'write':      ('🖊 <b>Напиши задачу</b>\n\nОпиши что написать.', None),
            'analyze':    ('🔍 <b>Анализ</b>\n\nОтправь файл или вставь текст/код для анализа.', 'analyze'),
            'review':     ('🔍 <b>Ревью кода</b>\n\nВставь код — найду баги и уязвимости.', 'review'),
            'fix':        ('🔧 <b>Фикс ошибки</b>\n\nВставь код + traceback ошибки.', 'fix'),
            'project':    ('📦 <b>Создать проект</b>\n\nОпиши: название, функции, структура.', 'project'),
            'sandbox':    ('🏖 <b>Sandbox</b>\n\nОтправь файл/архив/код для запуска.\nЕсли нужен API TOKEN — я спрошу.', 'sandbox'),
            'bot_tools':  ('🤖 <b>Инструменты бота</b>\n\nЧто сделать?', 'bot_tools'),
            'file':       ('📁 <b>Создать файл</b>\n\nОпиши формат и содержимое (txt/md/csv/docx/zip).', 'file'),
            'files_hint': ('📎 <b>Добавь файлы</b>\n\nОтправь нужные файлы, затем напиши задачу.\nФайлы будут переданы агенту вместе с задачей.', None),
        }

        prompt_text, proj_mode = CODER_MODES.get(arg, ('Опиши задачу:', None))

        # Создаём/обновляем сессию
        close_session(chat_id)
        sess = create_session(chat_id)
        sess.stage = STAGE_WAIT_FILES
        if proj_mode:
            sess.task = f'[{proj_mode}] '  # предзаполняем тип
        sess.touch()
        _wait_state[chat_id] = 'code_session'

        send_message(
            prompt_text + "\n\n<i>Или отправь файл — я сразу начну работать.</i>",
            chat_id,
            reply_markup=kb(
                [btn("🚀 Готово / Запустить", "_agent_go")],
                [btn("🔴 Стоп",              "agent_stop_code")],
            ))

    elif action == 'coder2':
        answer_callback(cb_id)
        mode_map = {
            'write':     ('write',     '🖊 Напиши задачу:'),
            'review':    ('review',    '🔍 Вставь код для ревью:'),
            'fix':       ('fix',       '🔧 Вставь код + ошибку:'),
            'project':   ('project',   '📦 Опиши проект:'),
            'sandbox':   ('sandbox',   '🏖 Вставь код для запуска:'),
            'bot_tools': ('bot_tools', '🤖 Что сделать? (пример: запусти туннель bore)'),
            'file':      ('file',      '📁 Опиши файл (формат + содержимое):'),
        }
        next_mode, prompt_text = mode_map.get(arg, ('write', 'Опиши задачу:'))
        _wait_state[chat_id] = 'coder_input:' + next_mode
        send_message(
            "🧩 <b>Агент-кодер 2</b>\n\n💻 <b>{}</b>\n\n<i>Отправь текст — агент возьмётся за работу.</i>".format(prompt_text),
            chat_id,
            reply_markup=kb([btn("❌ Отмена", "agent_code2_start")]))

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
        free_list = [p['name'] for p in providers if p['works_free']]
        paid_list = [p['name'] for p in providers if not p['works_free'] and p['has_key']]
        info_text = (
            "🎨 <b>Генерация картинок</b>\n\n"
            "🆓 Бесплатно (без ключа): <b>{}</b>\n"
            "💳 Платные (ключ есть): <b>{}</b>\n\n"
            "Нажми кнопку провайдера или просто опиши картинку:".format(
                ", ".join(free_list) or "—",
                ", ".join(paid_list) or "—",
            ))
        edit_message(chat_id, msg_id, info_text,
            reply_markup=kb(
                [btn("🌸 Pollinations (free)", "img_gen:pollinations"),
                 btn("🤗 HuggingFace (free)",  "img_gen:huggingface")],
                [btn("🎯 DALL-E 3",            "img_gen:dalle"),
                 btn("🔮 Stability AI",        "img_gen:stability")],
                [btn("⚡ Авто (лучший)",        "img_gen:auto")],
                [btn("📐 1:1 квадрат",          "img_size:1024x1024"),
                 btn("📱 9:16 вертикаль",       "img_size:576x1024"),
                 btn("🖥 16:9 горизонталь",     "img_size:1024x576")],
                [btn("🎨 Реализм",             "img_style:photorealistic, highly detailed"),
                 btn("🎭 Аниме",               "img_style:anime style, vibrant colors"),
                 btn("🖼 Масло",               "img_style:oil painting, artistic")],
                [btn("🔎 Все провайдеры",       "hub_image_menu"),
                 btn("🔑 Добавить ключ",        "img_add_key")],
                [back_btn()],
            ))

    elif action == 'img_gen':
        answer_callback(cb_id)
        _wait_state[chat_id] = f'img_prompt:{arg}'
        edit_message(chat_id, msg_id,
            "🎨 <b>Провайдер: {}</b>\n\nОпиши картинку на любом языке:\n\n"
            "Примеры:\n"
            "• <i>кот в космосе, стиль аниме</i>\n"
            "• <i>sunset over mountains, photorealistic</i>\n"
            "• <i>киберпанк город ночью, неон</i>".format(arg),
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
            '⚡ Groq DeepSeek R1':  ('groq',       'llama-3.3-70b-versatile',
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
            rows.append([btn_model(f"{label}{mark}", prov, model)])
        rows.append([btn("🔑 Добавить ключ", "llm_add_key"), back_btn("menu_llm")])
        edit_message(chat_id, msg_id, "\n".join(lines), reply_markup=kb(*rows))

    # ══════════════════════════════════════════════════════════
    #  ОБНОВЛЕНИЕ / ДИАГНОСТИКА
    # ══════════════════════════════════════════════════════════
    elif action == 'menu_update':
        answer_callback(cb_id)
        import sys as _sysup
        info = get_bot_info()
        rows = [
            [btn("📦 Проверить зависимости", "update_check_deps")],
            [btn("⬆️ Обновить core пакеты",  "update_upgrade"),
             btn("🔧 Установить пакет",       "update_install")],
            [btn("🔄 Обновить yt-dlp",        "update:ytdlp"),
             btn("📋 Весь pip",               "update:pip")],
            [btn("🔍 Найти рабочий LLM",      "update:llm_scan")],
            [btn("🩺 Самодиагностика",        "update_diag")],
        ]
        # Windows: кнопка установки ffmpeg
        if _sysup.platform == 'win32':
            rows.insert(-1, [btn("🎵 Установить ffmpeg (Windows)", "update:ffmpeg_win")])
        rows.append([back_btn()])
        edit_message(chat_id, msg_id, format_bot_info(info), reply_markup=kb(*rows))

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
        models = RECOMMENDED.get(prov, [])
        if not models:
            send_message(f"❌ Нет рекомендованных моделей для {prov}", chat_id,
                         reply_markup=kb([back_btn("menu_llm")]))
        else:
            rows = []
            for m in models[:8]:
                cur = " ✅" if m == config.LLM_MODEL else ""
                rows.append([btn_model(f"{m}{cur}", prov, m)])
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
                cmd = [sys.executable, '-m', 'pip', 'install', '--upgrade', '-r', reqs] + _pip_flags()
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
                r = _sp.run([sys.executable, '-m', 'pip', 'install', '--upgrade', 'yt-dlp'] + _pip_flags(),
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
                from llm_client import check_all_providers as _cap
                results = _cap(dict(__import__('os').environ))
                ok = [r for r in results if r.get('ok')]
                lines = [f"🆓 <b>Рабочие провайдеры ({len(ok)}/{len(results)}):</b>\n"]
                for r in ok:
                    lines.append(f"✅ {r.get('provider','?')} — {r.get('model','?')}")
                send_message('\n'.join(lines[:20]), chat_id,
                             reply_markup=kb([btn("◀️ Обновление", "menu_update"),
                                              btn("🧠 LLM меню", "menu_llm")]))
            _run_in_thread(_do_scan)

        elif arg == 'ffmpeg_win':
            answer_callback(cb_id, "Устанавливаю ffmpeg...")
            def _do_ffmpeg_win():
                import subprocess as _sp, sys as _sys
                send_message(
                    "🎵 <b>Установка ffmpeg на Windows</b>\n\n"
                    "Пробую через winget...",
                    chat_id)
                # Метод 1: winget
                import shutil as _sh1
                if not _sh1.which('winget'):
                    r1 = type('R', (), {'returncode': 1, 'stdout': '', 'stderr': 'winget not found'})()
                else:
                    r1 = _sp.run(['winget', 'install', 'Gyan.FFmpeg', '--silent', '--accept-package-agreements'],
                             capture_output=True, text=True, timeout=180)
                if r1.returncode == 0:
                    send_message(
                        "✅ <b>ffmpeg установлен через winget!</b>\n"
                        "Перезапусти бота чтобы ffmpeg стал доступен.\n"
                        "<code>python bot.py</code>",
                        chat_id, reply_markup=kb([btn("◀️ Обновление", "menu_update")]))
                    return
                # Метод 2: choco (только если установлен)
                import shutil as _sh2
                if not _sh2.which('choco'):
                    r2 = type('R', (), {'returncode': 1, 'stdout': '', 'stderr': 'choco not found'})()
                else:
                    r2 = _sp.run(['choco', 'install', 'ffmpeg', '-y'],
                                 capture_output=True, text=True, timeout=180)
                if r2.returncode == 0:
                    send_message("✅ <b>ffmpeg установлен через Chocolatey!</b>", chat_id,
                                 reply_markup=kb([btn("◀️ Обновление", "menu_update")]))
                    return
                # Не удалось — даём инструкцию
                send_message(
                    "❌ Авто-установка не удалась.\n\n"
                    "<b>Установи вручную:</b>\n"
                    "1. Скачай с <b>https://ffmpeg.org/download.html</b>\n"
                    "2. Распакуй в <code>C:\\ffmpeg</code>\n"
                    "3. Добавь <code>C:\\ffmpeg\\bin</code> в PATH\n"
                    "4. Перезапусти бота\n\n"
                    "<b>Или через winget:</b>\n"
                    "<code>winget install Gyan.FFmpeg</code>",
                    chat_id, reply_markup=kb([btn("◀️ Обновление", "menu_update")]))
            _run_in_thread(_do_ffmpeg_win)

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

            # ffmpeg install hint on Windows
            import sys as _sys
            if _sys.platform == 'win32':
                try:
                    _sp.run(['ffmpeg', '-version'], capture_output=True, timeout=3)
                except Exception:
                    lines.append("💡 <b>Установка ffmpeg (Windows):</b>")
                    lines.append("  • <code>winget install Gyan.FFmpeg</code>")
                    lines.append("  • или <code>choco install ffmpeg</code>")
                    lines.append("  • или скачай с <b>ffmpeg.org</b> и добавь в PATH")

            # Дисковое место (кросс-платформенно)
            free_mb = _disk_free_mb()
            if free_mb is not None:
                free_str = f"{free_mb:,} MB" if free_mb < 10240 else f"{free_mb // 1024} GB"
                lines.append(f"\n💾 Свободно: <b>{free_str}</b>")

            # RAM
            ram = _ram_info_mb()
            if ram:
                total_mb, avail_mb = ram
                lines.append(f"🧠 RAM: <b>{avail_mb:,} MB</b> / {total_mb:,} MB")

            # CPU count
            try:
                import os as _os2
                cpu = _os2.cpu_count() or '?'
                lines.append(f"⚙️ CPU: <b>{cpu} ядер</b>")
            except Exception:
                pass

            # Аптайм бота
            try:
                uptime_sec = int(time.time() - _BOT_START_TIME)
                h, rem = divmod(uptime_sec, 3600)
                m, s = divmod(rem, 60)
                lines.append(f"⏱ Аптайм: <b>{h}ч {m}м {s}с</b>")
            except Exception:
                pass

            send_message('\n'.join(lines), chat_id,
                reply_markup=kb(
                    [btn("🧪 Тест LLM", "test"),
                     btn("📦 Обновить pip", "update:pip")],
                    [btn("🔄 Обновить yt-dlp", "update:ytdlp"),
                     btn("🔍 Проверить LLM", "check_providers")],
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
            reply_markup=menu_keyboard(chat_id))

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

        if arg == 'tools':
            answer_callback(cb_id, "🤖 Agent pipeline — запускаю!")
            task_text = pending.get('task', '')
            edit_message(chat_id, msg_id,
                "🤖 <b>Agent pipeline</b>\n"
                f"Задача: <i>{task_text[:100]}</i>\n\n"
                "planner → executor → memory",
                reply_markup=None)
            def _do_pipeline(_task=task_text):
                if AGENT_CORE_ENABLED:
                    result = _agent_core.run(
                        task=_task, chat_id=chat_id, user_id=chat_id,
                        mode='scaffold',
                        on_status=lambda m: send_message(m, chat_id),
                    )
                    final = _strip_think(_agent_core.status_text(result))
                    send_message(final, chat_id, reply_markup=chat_control_keyboard())
                    from telegram_client import send_document
                    import os as _os
                    for p in result.get('artifacts', [])[:5]:
                        if _os.path.exists(p):
                            send_document(p, caption=f"📎 {_os.path.basename(p)}", chat_id=chat_id)
                else:
                    # Fallback на старый путь
                    final, results = run_agent_with_tools(
                        chat_id, _task,
                        on_status=lambda m: send_message(m, chat_id),
                    )
                    send_message(_strip_think(final)[:3500] if final else "✅ Готово",
                                 chat_id, reply_markup=chat_control_keyboard())
            _run_in_thread(_do_pipeline)
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

        def _do_llm_check():
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

        _run_in_thread(_do_llm_check)

    elif action == 'llm_pick':
        # Нажата кнопка провайдера из /llm меню
        provider = arg
        answer_callback(cb_id, "✅ {}".format(provider))
        rec = RECOMMENDED.get(provider, [])

        # Применяем провайдер сразу с дефолтной моделью
        default_model = rec[0] if rec else config.LLM_MODEL
        config.LLM_PROVIDER = provider
        config.LLM_MODEL = default_model

        if rec:
            # Показываем выбор модели
            rows = []
            for i in range(0, min(len(rec), 8), 2):
                row = [btn_model(rec[j], provider, rec[j]) for j in range(i, min(i+2, len(rec)))]
                rows.append(row)
            rows.append([btn_model("✅ Оставить {}".format(default_model[:20]), provider, default_model)])
            edit_message(chat_id, msg_id,
                "✅ Провайдер: <b>{}</b>\n\nВыбери модель:".format(provider),
                reply_markup=kb(*rows))
        else:
            # Нет рекомендаций — просто применяем
            edit_message(chat_id, msg_id,
                "✅ Провайдер: <b>{}</b>\nМодель: <code>{}</code>".format(
                    provider, default_model),
                reply_markup=kb([btn("◀️ Меню", "menu_llm")]))

    elif action == 'llm_m':
        # Короткий ID из _mdl_cache → разворачиваем в полный provider:model
        key_val = _mdl_cache.get(arg, '')
        if not key_val:
            answer_callback(cb_id, "❌ Кеш устарел, выбери снова", alert=True)
        else:
            parts = key_val.split(':', 1)
            if len(parts) == 2:
                # Переиспользуем логику llm_setmodel через подстановку
                from llm_client import _PROVIDER_KEY_MAP
                provider, model = parts
                _update_env('LLM_PROVIDER', provider)
                _update_env('LLM_MODEL', model)
                # Подставляем ключ провайдера в LLM_API_KEY
                new_key_attr2 = _PROVIDER_KEY_MAP.get(provider.lower(), '')
                if new_key_attr2:
                    new_key2 = os.environ.get(new_key_attr2, '')
                    if new_key2:
                        _update_env('LLM_API_KEY', new_key2)
                config.reload()
                answer_callback(cb_id, "✅ {}/{}".format(provider, model[:20]))
                key_attr = _PROVIDER_KEY_MAP.get(provider.lower(), 'LLM_API_KEY')
                has_key  = bool(getattr(config, key_attr, '') or getattr(config, 'LLM_API_KEY', ''))
                rows = [[btn("🧪 Тест", "test"), btn("◀️ LLM меню", "menu_llm")]]
                if not has_key and provider.lower() != 'ollama':
                    rows.insert(0, [btn("🔑 Добавить ключ ← НУЖЕН", "llm_addkey:{}".format(provider))])
                edit_message(chat_id, msg_id,
                    "✅ Провайдер: <b>{}</b>\nМодель: <code>{}</code>".format(provider, model),
                    reply_markup=kb(*rows))

    elif action == 'llm_setmodel':
        # arg = "provider:model" — сохраняем в .env немедленно
        parts = arg.split(':', 1)
        if len(parts) == 2:
            provider, model = parts
            _update_env('LLM_PROVIDER', provider)
            _update_env('LLM_MODEL', model)
            # Перенос ключей: при смене провайдера подставляем его ключ в LLM_API_KEY
            from llm_client import _PROVIDER_KEY_MAP as _PKM
            new_key_attr = _PKM.get(provider.lower(), '')
            if new_key_attr:
                new_key = os.environ.get(new_key_attr, '')
                if new_key:
                    _update_env('LLM_API_KEY', new_key)
            config.reload()
            answer_callback(cb_id, "✅ {} / {}".format(provider, model[:25]))
            # Проверяем ключ
            from llm_client import _PROVIDER_KEY_MAP
            key_attr  = _PROVIDER_KEY_MAP.get(provider.lower(), 'LLM_API_KEY')
            has_key   = bool(getattr(config, key_attr, '') or getattr(config, 'LLM_API_KEY', ''))
            if not has_key and provider.lower() != 'ollama':
                rows = [
                    [btn("🔑 Добавить ключ ← НУЖЕН", "llm_addkey:{}".format(provider))],
                    [btn("◀️ LLM меню", "menu_llm")],
                ]
                edit_message(chat_id, msg_id,
                    "✅ Активировано: <b>{}</b> / <code>{}</code>\n\n"                    "⚠️ <b>Нет API ключа!</b> Без него запросы упадут.".format(provider, model),
                    reply_markup=kb(*rows))
            else:
                # Ключ есть — сразу запускаем тест в фоне
                def _quick_test(_prov=provider, _mdl=model, _cid=chat_id):
                    from llm_client import test_connection
                    ok, msg = test_connection()
                    icon = '✅' if ok else '❌'
                    send_message(
                        "{} {} / {}\n{}".format(icon, _prov, _mdl, msg[:200]),
                        _cid,
                        reply_markup=kb([btn("🔄 Сменить модель", "menu_llm"),
                                         btn("◀️ Меню", "menu")])
                    )
                edit_message(chat_id, msg_id,
                    "✅ <b>{}</b> / <code>{}</code> — активировано\n⏳ Тестирую...".format(provider, model),
                    reply_markup=kb([btn("◀️ LLM меню", "menu_llm")]))
                _run_in_thread(_quick_test)
        else:
            answer_callback(cb_id, "❌ Ошибка", alert=True)

    elif action == 'llm_confirm':
        # arg может быть 'provider:model' или 'mN' (из _mdl_cache через btn_model)
        if arg.startswith('m') and arg[1:].isdigit():
            key_val = _mdl_cache.get(arg, '')
            parts = key_val.split(':', 1) if key_val else []
        else:
            parts = arg.split(':', 1)
        provider, model = (parts[0], parts[1]) if len(parts) == 2 else (config.LLM_PROVIDER, config.LLM_MODEL)
        _update_env('LLM_PROVIDER', provider)
        _update_env('LLM_MODEL', model)
        # Подставляем ключ нового провайдера в LLM_API_KEY
        from llm_client import _PROVIDER_KEY_MAP as _PKM_C
        _ck_attr = _PKM_C.get(provider.lower(), '')
        if _ck_attr:
            _ck = os.environ.get(_ck_attr, '')
            if _ck:
                _update_env('LLM_API_KEY', _ck)
        config.reload()
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

    elif action == 'fish_opt_html':
        # fish_opt_html:toggle_name — для загруженных HTML
        answer_callback(cb_id)
        _fish_handle_opt_html(arg, chat_id)


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
        edit_message(chat_id, msg_id, "❌ Отменено.", reply_markup=menu_keyboard(chat_id))

    # ══════════════════════════════════════════════════════════
    #  🔑 АДМИНИСТРАТОР
    # ══════════════════════════════════════════════════════════
    elif action == 'admin':
        if not ADMIN_ENABLED or not is_admin(chat_id):
            answer_callback(cb_id, "🚫 Нет доступа", alert=True); return
        answer_callback(cb_id)
        edit_message(chat_id, msg_id, "🔑 <b>Панель администратора</b>",
                     reply_markup=admin_main_keyboard())

    elif action == 'adm_noop':
        answer_callback(cb_id)

    elif action == 'adm':
        if not ADMIN_ENABLED or not is_admin(chat_id):
            answer_callback(cb_id, "🚫 Нет доступа", alert=True); return
        answer_callback(cb_id)
        log_admin_cmd(chat_id, f"adm:{arg}")

        # ── Пользователи ──────────────────────────────────
        if arg == 'users' or arg.startswith('users_page:'):
            page = int(arg.split(':')[1]) if ':' in arg else 0
            text_u, markup_u = format_users_list(page)
            edit_message(chat_id, msg_id, text_u, reply_markup=markup_u)

        elif arg.startswith('manage:'):
            target = arg.split(':')[1]
            u = get_user(int(target))
            login = (u or {}).get('login','?')
            edit_message(chat_id, msg_id,
                f"⚙️ <b>Управление: {login}</b> (<code>{target}</code>)",
                reply_markup=user_manage_keyboard(target))

        elif arg.startswith('view_user:'):
            target = arg.split(':')[1]
            edit_message(chat_id, msg_id,
                format_profile(int(target)),
                reply_markup=kb([btn("⚙️ Управлять", f"adm:manage:{target}"),
                                  btn("◀️ Назад", "adm:users")]))

        elif arg.startswith('priv:'):
            parts = arg.split(':')
            target, priv = parts[1], parts[2]
            set_privilege(int(target), priv)
            icon = PRIVILEGE_ICONS.get(priv,'👤')
            answer_callback(cb_id, f"✅ {priv} выдано {icon}")
            u = get_user(int(target))
            edit_message(chat_id, msg_id,
                f"✅ Привилегия <b>{priv}</b> {icon} выдана пользователю <code>{target}</code>",
                reply_markup=user_manage_keyboard(target))

        elif arg.startswith('ban:'):
            target = arg.split(':')[1]
            ban_user(target)
            answer_callback(cb_id, "🚫 Заблокирован")
            edit_message(chat_id, msg_id,
                f"🚫 Пользователь <code>{target}</code> заблокирован.",
                reply_markup=user_manage_keyboard(target))

        elif arg.startswith('unban:'):
            target = arg.split(':')[1]
            unban_user(target)
            answer_callback(cb_id, "✅ Разблокирован")
            edit_message(chat_id, msg_id,
                f"✅ Пользователь <code>{target}</code> разблокирован.",
                reply_markup=user_manage_keyboard(target))

        elif arg.startswith('kick:'):
            target = arg.split(':')[1]
            from auth_module import auth_session_delete
            auth_session_delete(int(target))
            answer_callback(cb_id, "🔴 Выбит из сессии")
            send_message(f"🔴 Пользователь <code>{target}</code> выбит из сессии.",
                         chat_id, reply_markup=user_manage_keyboard(target))

        elif arg.startswith('delete_user:'):
            target = arg.split(':')[1]
            delete_user(target)
            answer_callback(cb_id, "🗑 Удалён")
            edit_message(chat_id, msg_id,
                f"🗑 Пользователь <code>{target}</code> удалён.",
                reply_markup=kb([btn("◀️ Список", "adm:users")]))

        # ── Сообщения ─────────────────────────────────────
        elif arg == 'msg_user':
            from admin_module import adm_wait_set
            adm_wait_set(chat_id, 'adm_msg_target')
            send_message("📩 Введи chat_id или @username получателя:", chat_id,
                         reply_markup=kb([btn("❌ Отмена","admin")]))

        elif arg.startswith('msg_to:'):
            target = arg.split(':')[1]
            from admin_module import adm_wait_set
            adm_wait_set(chat_id, 'adm_msg_text', {'target': target})
            send_message(f"✏️ Введи текст сообщения для <code>{target}</code>:", chat_id,
                         reply_markup=kb([btn("❌ Отмена","admin")]))

        elif arg == 'broadcast':
            from admin_module import adm_wait_set
            adm_wait_set(chat_id, 'adm_broadcast')
            all_u = get_all_users()
            active_count = sum(1 for u in all_u if u.get('status')=='active')
            send_message(f"📣 Рассылка <b>всем</b> ({active_count} активных).\n\nВведи текст:", chat_id,
                         reply_markup=kb([btn("❌ Отмена","admin")]))

        elif arg == 'notify_online':
            from admin_module import adm_wait_set
            adm_wait_set(chat_id, 'adm_notify')
            send_message("🔔 Введи текст уведомления:", chat_id,
                         reply_markup=kb([btn("❌ Отмена","admin")]))

        # ── Система ───────────────────────────────────────
        elif arg == 'sysinfo':
            info = get_system_info()
            edit_message(chat_id, msg_id, info,
                         reply_markup=kb([btn("🔄 Обновить","adm:sysinfo"),
                                          btn("◀️ Меню","admin")]))

        elif arg == 'processes':
            procs = list_processes()
            edit_message(chat_id, msg_id, procs,
                         reply_markup=kb([btn("💀 Убить PID","adm:kill_proc"),
                                          btn("🔄 Обновить","adm:processes"),
                                          btn("◀️ Меню","admin")]))

        elif arg == 'kill_proc':
            from admin_module import adm_wait_set
            adm_wait_set(chat_id, 'adm_kill_pid')
            send_message("💀 Введи PID процесса для завершения:", chat_id,
                         reply_markup=kb([btn("❌ Отмена","admin")]))

        elif arg == 'restart_bot':
            answer_callback(cb_id, "🔄 Перезапускаю...")
            send_message("🔄 Бот перезапускается через 3 секунды...", chat_id)
            import threading as _thr, platform as _plat
            def _restart():
                import time as _t
                _t.sleep(3)
                try:
                    if _plat.system() == 'Windows':
                        # Windows: запускаем новый процесс, текущий завершается
                        subprocess.Popen(
                            [sys.executable] + sys.argv,
                            cwd=config.BASE_DIR,
                            creationflags=subprocess.CREATE_NEW_CONSOLE
                        )
                        os._exit(0)
                    else:
                        os.execv(sys.executable, [sys.executable] + sys.argv)
                except Exception as e:
                    send_message(f"❌ Ошибка перезапуска: {e}", chat_id)
            _thr.Thread(target=_restart, daemon=True).start()

        elif arg == 'exec_cmd':
            from admin_module import adm_wait_set
            adm_wait_set(chat_id, 'adm_exec_cmd')
            send_message("💻 Введи shell-команду:", chat_id,
                         reply_markup=kb([btn("❌ Отмена","admin")]))

        elif arg == 'logs':
            logs = get_recent_logs(30)
            send_message(f"📊 <b>Логи (последние 30 строк):</b>\n<pre>{logs[:3000]}</pre>",
                         chat_id, reply_markup=kb([btn("◀️ Адм. меню","admin")]))

        elif arg == 'reload_config':
            config.reload()
            answer_callback(cb_id, "✅ Config перезагружен")
            send_message("✅ Config перезагружен.", chat_id,
                         reply_markup=kb([btn("◀️ Адм. меню","admin")]))

        elif arg == 'show_keys':
            answer_callback(cb_id)
            from admin_module import is_god
            if not is_god(chat_id):
                send_message("⚡ <b>Только GOD</b>\n\nДоступ к API ключам есть только у роли БОГ.", chat_id,
                             reply_markup=kb([btn("◀️ Адм. меню","admin")])); return
            lines = ["🗝 <b>API ключи (.env)</b>\n"]
            key_map = [
                ('BOT_TOKEN','Telegram Token'),
                ('LLM_API_KEY','LLM'),('OPENAI_API_KEY','OpenAI'),
                ('GROQ_API_KEY','Groq'),('GEMINI_API_KEY','Gemini'),
                ('ANTHROPIC_API_KEY','Claude'),('ELEVEN_API_KEY','ElevenLabs'),
                ('OPENROUTER_API_KEY','OpenRouter'),('STABILITY_API_KEY','Stability'),
                ('ADMIN_WEB_TOKEN','Admin Web Token'),
            ]
            for env_k, label in key_map:
                val = os.environ.get(env_k,'')
                if val:
                    lines.append(f"✅ {label}: <code>{val[:6]}...{val[-3:]}</code>")
                else:
                    lines.append(f"❌ {label}: не задан")
            send_message("\n".join(lines), chat_id,
                         reply_markup=kb(
                             [btn("⚙️ Редактировать .env","adm:edit_env")],
                             [btn("◀️ Адм. меню","admin")]
                         ))

        elif arg == 'edit_env':
            answer_callback(cb_id)
            from admin_module import is_god, adm_wait_set
            if not is_god(chat_id):
                send_message("⚡ <b>Только GOD</b>", chat_id); return
            adm_wait_set(chat_id, 'adm_edit_env')
            send_message(
                "⚙️ <b>Редактирование .env</b>\n\n"
                "Введи в формате:\n"
                "<code>КЛЮЧ=значение</code>\n\n"
                "Примеры:\n"
                "<code>GROQ_API_KEY=gsk_xxx</code>\n"
                "<code>LLM_PROVIDER=openai</code>\n\n"
                "⚠️ Изменения применятся сразу",
                chat_id, reply_markup=kb([btn("❌ Отмена","admin")]))

        elif arg == 'god_panel':
            answer_callback(cb_id)
            from admin_module import is_god
            if not is_god(chat_id):
                send_message("⚡ Только GOD", chat_id); return
            users = get_all_users()  # используем глобальный импорт
            by_role = {}
            for u in users:
                r = u.get('privilege','user')
                by_role[r] = by_role.get(r,0) + 1
            stats = "\n".join(f"  {k}: {v}" for k,v in sorted(by_role.items()))
            send_message(
                "⚡ <b>GOD ПАНЕЛЬ</b>\n\n"
                f"👥 Пользователей: {len(users)}\n"
                f"📊 По ролям:\n{stats}\n\n"
                "Управление:",
                chat_id,
                reply_markup=kb(
                    [btn("🗝 API ключи",       "adm:show_keys")],
                    [btn("⚙️ .env",            "adm:edit_env")],
                    [btn("💰 Установить штраф","adm:set_fine")],
                    [btn("👤 Назначить роль",  "adm:set_priv")],
                    [btn("📣 Рассылка",         "adm:broadcast")],
                    [btn("◀️ Адм. меню",        "admin")],
                ))

        elif arg == 'set_fine':
            answer_callback(cb_id)
            from admin_module import is_god, adm_wait_set
            if not is_god(chat_id):
                send_message("⚡ Только GOD", chat_id); return
            current = os.environ.get('BAN_FINE_AMOUNT', '0')
            adm_wait_set(chat_id, 'adm_set_fine')
            send_message(
                f"💰 <b>Штраф за бан</b>\n\n"
                f"Текущий: <b>{current}</b> кредитов\n\n"
                "Введи новую сумму штрафа (в кредитах):",
                chat_id, reply_markup=kb([btn("❌ Отмена","admin")]))

        elif arg == 'cmd_history':
            from admin_module import _cmd_log
            if not _cmd_log:
                send_message("📜 История пуста.", chat_id,
                             reply_markup=kb([btn("◀️ Адм. меню","admin")]))
            else:
                lines = ["📜 <b>История команд:</b>\n"]
                for entry in _cmd_log[-20:]:
                    lines.append(f"<code>{entry['ts']}</code> [{entry['admin']}] {entry['cmd']}")
                send_message("\n".join(lines), chat_id,
                             reply_markup=kb([btn("◀️ Адм. меню","admin")]))

        elif arg == 'find_user':
            from admin_module import adm_wait_set
            adm_wait_set(chat_id, 'adm_find_user')
            send_message("🔍 Введи login, @username или chat_id:", chat_id,
                         reply_markup=kb([btn("❌ Отмена","admin")]))

        elif arg == 'add_rating':
            from admin_module import adm_wait_set
            adm_wait_set(chat_id, 'adm_add_rating')
            send_message("⭐ Введи: <code>chat_id очки</code>\nПример: <code>123456789 100</code>",
                         chat_id, reply_markup=kb([btn("❌ Отмена","admin")]))

        elif arg == 'spawn_agent':
            answer_callback(cb_id)
            try:
                from agent_session import create_session
                create_session(chat_id)
            except ImportError:
                pass
            _wait_state[chat_id] = 'adm_agent_task'
            send_message(
                "🤖 <b>АГЕНТ_0051</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "Автономный агент администратора.\n\n"
                "📝 Опиши задачу\n"
                "📎 Прикрепи файлы (если нужно)\n"
                "✅ Напиши <b>готово</b> для запуска\n\n"
                "<i>Умеет: код, анализ, автоматизация, работа с файлами, сеть, СМИТ-pipeline</i>",
                chat_id,
                reply_markup=kb(
                    [btn("🚀 Готово", "_agent_go")],
                    [btn("❌ Отмена", "adm:close_agent")],
                )
            )

        elif arg == 'smith_menu' or arg.startswith('smith:') or arg == 'smith_coder' or arg.startswith('sc:') or arg == 'close_agent':
            # Делегируем в отдельные elif ниже через перевызов
            _route_smith(arg, cb_id, chat_id, msg_id)
        elif arg == 'smith_coder':
            answer_callback(cb_id)
            edit_message(chat_id, msg_id,
                "🕵️💻 <b>АГЕНТ_СМИТ — Кодер</b>\n\n"
                "🖊 <b>Написать код</b> — опиши задачу, Смит напишет, протестирует и отдаст zip\n"
                "🔍 <b>Ревью кода</b> — найдёт баги, уязвимости, code-smell\n"
                "🔧 <b>Исправить ошибку</b> — вставь код + traceback → авто-фикс x15\n"
                "📦 <b>Создать проект</b> — полная структура с файлами, тестами, README\n"
                "🏖 <b>Sandbox</b> — выполни любой Python-код прямо сейчас\n"
                "🤖 <b>Инструменты бота</b> — управление туннелем, файлами, env\n"
                "📁 <b>Создать файл</b> — txt / md / csv / docx / zip\n"
                "🧩 <b>Scaffold</b> — Смит создаёт полный шаблон проекта\n"
                "🔄 <b>Рефакторинг</b> — улучшит код, добавит типы и docstrings\n"
                "🧪 <b>Тесты</b> — напишет pytest / unittest тесты\n"
                "📊 <b>Анализ кода</b> — сложность, зависимости, метрики\n"
                "🐳 <b>Dockerize</b> — добавит Dockerfile + compose к проекту\n\n"
                f"Модель: <b>{config.LLM_PROVIDER} / {config.LLM_MODEL}</b>",
                reply_markup=kb(
                    [btn("🖊 Написать код",        "adm:sc:write"),
                     btn("🔍 Ревью кода",          "adm:sc:review")],
                    [btn("🔧 Исправить ошибку",    "adm:sc:fix"),
                     btn("📦 Создать проект",      "adm:sc:project")],
                    [btn("🏖 Sandbox",             "adm:sc:sandbox"),
                     btn("🤖 Инструменты бота",    "adm:sc:bot_tools")],
                    [btn("📁 Создать файл",        "adm:sc:file"),
                     btn("🧩 Scaffold",            "adm:sc:scaffold")],
                    [btn("🔄 Рефакторинг",         "adm:sc:refactor"),
                     btn("🧪 Написать тесты",      "adm:sc:tests")],
                    [btn("📊 Анализ кода",         "adm:sc:analyze"),
                     btn("🐳 Dockerize",           "adm:sc:dockerize")],
                    [btn("◀️ АГЕНТ_СМИТ",          "adm:smith_menu")],
                ))

        elif arg.startswith('sc:'):
            answer_callback(cb_id)
            sc_mode = arg.split(':', 1)[1]

            SC_PROMPTS = {
                'write':     ("🖊 Опиши задачу — Смит напишет код, протестирует и отдаст zip:",
                              "напиши рабочий Python-скрипт для задачи: {task}"),
                'review':    ("🔍 Вставь код для ревью (найду баги и уязвимости):",
                              "сделай code review этого кода, найди баги, проблемы безопасности и code-smell:\n{task}"),
                'fix':       ("🔧 Вставь код + traceback ошибки:",
                              "исправь ошибку в этом коде:\n{task}"),
                'project':   ("📦 Опиши проект (название, функции, структура):",
                              "создай полную структуру Python-проекта: {task}\nВключи main.py, requirements.txt, README.md, тесты"),
                'sandbox':   ("🏖 Вставь Python-код для запуска в sandbox:",
                              "запусти и проверь этот код:\n{task}"),
                'bot_tools': ("🤖 Опиши задачу для агента с инструментами бота:",
                              "используй инструменты бота для: {task}"),
                'file':      ("📁 Что создать? (опиши файл: тип, содержимое, название):",
                              "создай файл: {task}"),
                'scaffold':  ("🧩 Опиши шаблон проекта (тип: flask/fastapi/bot/cli/lib):",
                              "создай полный scaffold Python-проекта типа: {task}"),
                'refactor':  ("🔄 Вставь код для рефакторинга:",
                              "отрефактори этот код: добавь типы, docstrings, улучши структуру:\n{task}"),
                'tests':     ("🧪 Вставь код для которого нужны тесты:",
                              "напиши pytest тесты для этого кода с coverage 80%+:\n{task}"),
                'analyze':   ("📊 Вставь код для анализа (метрики, зависимости, сложность):",
                              "проанализируй этот код: цикломатическая сложность, зависимости, проблемные места:\n{task}"),
                'dockerize': ("🐳 Опиши проект (или вставь main.py) для dockerize:",
                              "создай Dockerfile + docker-compose.yml для Python-проекта: {task}"),
            }

            prompt_msg, task_template = SC_PROMPTS.get(sc_mode,
                ("Опиши задачу:", "выполни: {task}"))

            # Для sandbox и bot_tools — используем старый кодер
            if sc_mode in ('sandbox', 'bot_tools'):
                coder_map = {'sandbox': 'sandbox', 'bot_tools': 'bot_tools'}
                _pending_agent_task[chat_id] = {}
                _wait_state[chat_id] = f'coder_wait:{coder_map[sc_mode]}'
                edit_message(chat_id, msg_id, prompt_msg,
                             reply_markup=kb([btn("❌ Отмена", "adm:smith_coder")]))
            else:
                # Создаём сессию СМИТА
                try:
                    from agent_session import create_session, STAGE_WAIT_FILES
                    sess = create_session(chat_id)
                    sess.stage = STAGE_WAIT_FILES
                    sess._sc_template = task_template  # сохраняем шаблон
                    sess._sc_mode = sc_mode
                except Exception:
                    pass
                _wait_state[chat_id] = f'adm_sc_input:{sc_mode}'
                edit_message(chat_id, msg_id,
                    f"🕵️💻 <b>СМИТ — {sc_mode.upper()}</b>\n\n{prompt_msg}",
                    reply_markup=kb([btn("❌ Отмена", "adm:smith_coder")]))
            answer_callback(cb_id)
            smith_mode = arg.split(':', 1)[1]

            # Шаблоны задач для каждого режима
            SMITH_TASKS = {
                'auto':         ("Опиши задачу для АГЕНТ_СМИТ:", None),
                'scaffold':     ("Опиши что создать (название проекта, функции):", 'scaffold'),
                'patch':        ("Вставь код + описание бага для фикса:", 'patch'),
                'plan_first':   ("Опиши задачу — сначала покажу план:", 'plan_first'),
                'tg_bot':       ("Телеграм бот на python-telegram-bot v20 с командами /start /help и inline-кнопками", None),
                'aiogram_bot':  ("Telegram бот на aiogram 3.x с FSM и inline-клавиатурами, команды /start /menu", None),
                'inline_bot':   ("Telegram inline-бот который отвечает на inline-запросы (@bot текст)", None),
                'notif_bot':    ("Telegram бот который отправляет уведомления по расписанию через schedule", None),
                'fastapi':      ("FastAPI REST API с эндпоинтами CRUD, pydantic моделями и swagger docs", None),
                'flask':        ("Flask веб-приложение с роутами, шаблонами Jinja2 и REST API", None),
                'scraper':      ("Веб-парсер на requests+BeautifulSoup с сохранением в JSON и CSV", None),
                'api_client':   ("Python клиент для REST API с retry, timeout, auth и логированием", None),
                'pynput':       ("Python скрипт автоматизации клавиатуры и мыши через pynput: горячие клавиши, макросы", None),
                'pyautogui':    ("Python GUI-автоматизация через pyautogui: поиск элементов, клики, скриншоты", None),
                'scheduler':    ("Python планировщик задач через APScheduler или schedule с cron-выражениями", None),
                'desktop':      ("Python десктопный скрипт для автоматизации системных задач через psutil и subprocess", None),
                'pandas':       ("Python скрипт обработки данных: pandas read_csv/excel, фильтры, группировка, экспорт", None),
                'sqlite':       ("Python работа с SQLite: создание таблиц, CRUD операции, sqlalchemy ORM", None),
                'plots':        ("Python визуализация данных: matplotlib/seaborn графики, сохранение в PNG", None),
                'etl':          ("Python ETL pipeline: чтение источника, трансформация, загрузка в целевой формат", None),
                'crypto':       ("Python шифрование файлов и паролей через cryptography (Fernet) и hashlib", None),
                'jwt':          ("Python JWT авторизация: генерация токенов, верификация, refresh tokens", None),
                'slideshow':    ("Собери видео-слайдшоу из изображений. Пришли фото после описания задачи.", None),
                'tts_task':     ("Озвучь текст через edge-tts в mp3. Введи текст для озвучки:", None),
                'image_proc':   ("Python обработка изображений через Pillow: resize, crop, filter, convert, watermark", None),
                'audio_proc':   ("Python обработка аудио через pydub: конвертация, обрезка, merge, нормализация", None),
                'archiver':     ("Python утилита для создания и распаковки ZIP/TAR архивов с прогресс-баром", None),
                'email':        ("Python скрипт отправки email через smtplib с HTML-шаблоном и вложениями", None),
                'docker':       ("Создай Dockerfile + docker-compose.yml для Python приложения с описанием сервисов", None),
                'report':       ("Python генератор отчётов в Markdown и PDF через jinja2 + weasyprint", None),
            }

            task_text, code_mode = SMITH_TASKS.get(smith_mode, ("Опиши задачу:", None))

            # Создаём сессию
            try:
                from agent_session import create_session, STAGE_WAIT_FILES
                sess = create_session(chat_id)
                sess.task  = task_text if smith_mode not in ('auto','scaffold','patch','plan_first') else ""
                sess.stage = STAGE_WAIT_FILES
                if code_mode:
                    sess.tools_ready = [code_mode]
            except ImportError:
                pass

            if smith_mode in ('auto', 'scaffold', 'patch', 'plan_first'):
                # Ждём ввод от пользователя
                _wait_state[chat_id] = 'adm_agent_task'
                edit_message(chat_id, msg_id,
                    f"🕵️ <b>АГЕНТ_СМИТ</b> [{smith_mode}]\n\n"
                    f"{task_text}\n\n"
                    "Отправь задачу текстом:",
                    reply_markup=kb(
                        [btn("❌ Отмена", "adm:close_agent")],
                    ))
            else:
                # Задача предзаполнена — запускаем сразу или ждём файлы
                needs_files = smith_mode in ('slideshow',)

                if needs_files:
                    _wait_state[chat_id] = 'adm_agent_task'
                    edit_message(chat_id, msg_id,
                        f"🕵️ <b>АГЕНТ_СМИТ</b>\n"
                        f"Задача: <i>{task_text[:100]}</i>\n\n"
                        "📎 Отправь файлы, затем напиши <b>готово</b>",
                        reply_markup=kb(
                            [btn("🚀 Запустить без файлов", "_agent_go")],
                            [btn("❌ Отмена", "adm:close_agent")],
                        ))
                else:
                    # Запускаем сразу
                    edit_message(chat_id, msg_id,
                        f"🕵️ <b>АГЕНТ_СМИТ</b> запускается...\n"
                        f"Задача: <i>{task_text[:120]}</i>",
                        reply_markup=kb([btn("❌ Отмена","adm:close_agent")]))

                    def _run_smith(_task=task_text):
                        try:
                            from agent_session import (create_session, execute_pipeline,
                                                        close_session, STAGE_WAIT_FILES)
                            from agent_core import _llm_call
                            llm_fn = _llm_call
                        except Exception:
                            llm_fn = None
                        try:
                            from agent_session import get_session
                            s = get_session(chat_id)
                            if not s:
                                from agent_session import create_session
                                s = create_session(chat_id)
                            s.task  = _task
                            s.stage = STAGE_WAIT_FILES
                        except Exception as e:
                            send_message(f"❌ Сессия: {e}", chat_id); return

                        result = execute_pipeline(
                            s,
                            on_status=lambda m: send_message(m, chat_id),
                            llm_caller=llm_fn,
                        )
                        from telegram_client import send_document as _sd
                        import os as _os
                        for art in result.get('artifacts', []):
                            if _os.path.exists(art['path']):
                                try: _sd(art['path'], caption=f"📎 {art['name']}", chat_id=chat_id)
                                except Exception: pass
                        if result.get('zip_path') and _os.path.exists(result['zip_path']):
                            try: _sd(result['zip_path'], caption="📦 Все результаты", chat_id=chat_id)
                            except Exception: pass
                        errs = result.get('errors', [])
                        icon = "✅" if result.get('ok') else "⚠️"
                        send_message(
                            f"{icon} АГЕНТ_СМИТ завершил\n"
                            f"Артефактов: {len(result.get('artifacts',[]))}\n"
                            + (f"Ошибок: {len(errs)}" if errs else ""),
                            chat_id,
                            reply_markup=kb(
                                [btn("🕵️ Ещё задача","adm:smith_menu")],
                                [btn("◀️ Адм. меню","admin")],
                            ))
                        try:
                            from agent_session import close_session
                            close_session(chat_id)
                        except Exception: pass
                    _run_in_thread(_run_smith)
            answer_callback(cb_id, "Сессия закрыта")
            try:
                from agent_session import close_session
                close_session(chat_id)
            except ImportError:
                pass
            _wait_state.pop(chat_id, None)
            edit_message(chat_id, msg_id, "🤖 Сессия агента закрыта.",
                         reply_markup=kb([btn("◀️ Адм. меню","admin")]))

        elif arg == 'cloudflared_qr':
            answer_callback(cb_id)
            if not CF_BOT_ENABLED:
                send_message("❌ cloudflared_bot.py не найден в папке бота.", chat_id); return
            edit_message(chat_id, msg_id,
                "📡 <b>Cloudflared Tunnel + QR</b>\n\n"
                "Запустит туннель → получит URL → создаст QR →\n"
                "отправит выбранным пользователям\n\n"
                "Выбери порт:",
                reply_markup=kb(
                    [btn("🌐 Порт 5000 (fish/web)", "adm:cf_start:5000")],
                    [btn("🌐 Порт 8080 (admin panel)", "adm:cf_start:8080")],
                    [btn("🔴 Остановить туннель", "cf_stop"),
                     btn("◀️ Назад", "admin")],
                ))

        elif arg.startswith('cf_start:'):
            answer_callback(cb_id)
            port = int(arg.split(':')[1])
            edit_message(chat_id, msg_id, f"🌐 Запускаю cloudflared на порту {port}...")
            def _cf_start(_port=port, _cid=chat_id):
                if CF_BOT_ENABLED:
                    handle_cloudflared_command(_cid, port=_port)
            _run_in_thread(_cf_start)

        elif arg == 'cfqr_menu':
            answer_callback(cb_id)
            try:
                from cloudflared_qr_bot import get_tunnel_url
                url = get_tunnel_url()
                st  = f"🟢 <code>{url}</code>" if url else "🔴 Не запущен"
            except ImportError:
                st = "⚠️ Модуль не найден"
            edit_message(chat_id, msg_id,
                f"☁️ <b>Cloudflared QR</b>\n\nСтатус: {st}",
                reply_markup=kb(
                    [btn("🚀 Запуск порт 8080",  "adm:cfqr:start:8080"),
                     btn("🚀 Запуск порт 5000",  "adm:cfqr:start:5000")],
                    [btn("📱 Генерить QR",         "adm:cfqr:gen_qr"),
                     btn("📤 Разослать юзерам",   "adm:cfqr:send_users")],
                    [btn("🔗 Показать URL",        "adm:cfqr:show_url"),
                     btn("⏹ Остановить",          "adm:cfqr:stop")],
                    [btn("◀️ Адм. меню",           "admin")],
                ))

        elif arg.startswith('cfqr:'):
            answer_callback(cb_id)
            cfarg = arg[5:]  # убираем 'cfqr:'
            try:
                from cloudflared_qr_bot import (start_cloudflared, stop_cloudflared,
                                                 get_tunnel_url, generate_qr)
            except ImportError as e:
                send_message(f"❌ cloudflared_qr_bot: {e}", chat_id); return

            if cfarg.startswith('start:'):
                port = int(cfarg.split(':')[1])
                send_message(f"☁️ Запускаю cloudflared на порту {port}...", chat_id)
                def _cf_start(p=port):
                    ok, result = start_cloudflared(p)
                    if ok:
                        try:
                            qr_path = generate_qr(result, "BlackBugsAI Tunnel")
                            send_document(qr_path,
                                caption=f"☁️ <b>Туннель активен</b>\n<code>{result}</code>",
                                chat_id=chat_id)
                        except Exception:
                            send_message(f"☁️ <b>Туннель активен</b>\n<code>{result}</code>", chat_id)
                        send_message("📤 Нажми 'Разослать юзерам' чтобы отправить QR", chat_id,
                                     reply_markup=kb([btn("📤 Разослать QR","adm:cfqr:send_users"),
                                                      btn("◀️ Меню CF","adm:cfqr_menu")]))
                    else:
                        send_message(result, chat_id)
                _run_in_thread(_cf_start)

            elif cfarg == 'stop':
                stop_cloudflared()
                send_message("⏹ Туннель остановлен", chat_id,
                             reply_markup=kb([btn("◀️ CF меню","adm:cfqr_menu")]))

            elif cfarg == 'show_url':
                url = get_tunnel_url()
                send_message(f"🔗 <code>{url}</code>" if url else "🔴 Не запущен", chat_id)

            elif cfarg == 'gen_qr':
                url = get_tunnel_url()
                if not url:
                    send_message("❌ Сначала запусти туннель!", chat_id,
                                 reply_markup=kb([btn("🚀 Запустить","adm:cfqr:start:8080")])); return
                def _gen():
                    try:
                        qr_path = generate_qr(url, "BlackBugsAI")
                        send_document(qr_path, caption=f"📱 QR\n<code>{url}</code>", chat_id=chat_id)
                    except Exception as e:
                        send_message(f"❌ QR ошибка: {e}\npip install qrcode[pil]", chat_id)
                _run_in_thread(_gen)

            elif cfarg == 'send_users':
                url = get_tunnel_url()
                if not url:
                    send_message("❌ Сначала запусти туннель!", chat_id,
                                 reply_markup=kb([btn("🚀 Запустить","adm:cfqr:start:8080")])); return
                users = get_all_users()
                active = [u for u in users if u.get('privilege') not in ('banned',)
                          and u.get('status') != 'banned']
                if not active:
                    send_message("👥 Нет активных пользователей", chat_id); return
                rows = []
                for u in active[:15]:
                    name = (u.get('first_name') or u.get('username') or str(u['telegram_id']))[:20]
                    icon = PRIVILEGE_ICONS.get(u.get('privilege','user'),'👤')
                    rows.append([btn(f"{icon} {name}", f"adm:cfqr:to:{u['telegram_id']}")])
                rows.append([btn("📣 Всем активным", "adm:cfqr:all")])
                rows.append([btn("◀️ Назад","adm:cfqr_menu")])
                edit_message(chat_id, msg_id,
                    "📤 <b>Кому отправить QR?</b>",
                    reply_markup={"inline_keyboard": rows})

            elif cfarg.startswith('to:'):
                target = cfarg.split(':')[1]
                url = get_tunnel_url()
                def _send_one(tid=target, u_url=url):
                    try:
                        qr_path = generate_qr(u_url, "BlackBugsAI")
                        send_document(qr_path,
                            caption=f"☁️ <b>Ссылка</b>\n<code>{u_url}</code>",
                            chat_id=tid)
                        u = get_user(tid)
                        name = (u.get('first_name') or str(tid)) if u else tid
                        send_message(f"✅ QR отправлен: <b>{name}</b>", chat_id)
                    except Exception as e:
                        send_message(f"⚠️ Ошибка: {e}", chat_id)
                _run_in_thread(_send_one)

            elif cfarg == 'all':
                url = get_tunnel_url()
                users = [u for u in get_all_users()
                         if u.get('privilege') not in ('banned',) and u.get('status') != 'banned']
                send_message(f"📣 Отправляю {len(users)} пользователям...", chat_id)
                def _send_all():
                    try:
                        qr_path = generate_qr(url, "BlackBugsAI")
                    except Exception as e:
                        send_message(f"❌ QR: {e}", chat_id); return
                    ok = fail = 0
                    for u in users:
                        try:
                            send_document(qr_path,
                                caption=f"☁️ <b>Ссылка</b>\n<code>{url}</code>",
                                chat_id=str(u['telegram_id']))
                            ok += 1; time.sleep(0.05)
                        except Exception:
                            fail += 1
                    send_message(f"✅ {ok} отправлено | ❌ {fail} ошибок", chat_id,
                                 reply_markup=kb([btn("◀️ CF меню","adm:cfqr_menu")]))
                _run_in_thread(_send_all)

        else:
            answer_callback(cb_id, f"❓ Неизвестное adm: {arg}", alert=True)

    # ══════════════════════════════════════════════════════════
    #  ТИП АГЕНТА (3 режима)
    # ══════════════════════════════════════════════════════════
    elif action == 'agent_type':
        answer_callback(cb_id)
        atype = arg or 'assistant'
        if USER_SETTINGS_ENABLED:
            set_setting(chat_id, 'agent_type', atype)
        info = AGENT_TYPES.get(atype, {})
        icon = info.get('icon','🤖')
        name = info.get('name', atype)
        desc = info.get('desc','')
        # Запускаем сессию с нужным системным промтом
        start_session(chat_id, 'chat')
        edit_message(chat_id, msg_id,
            f"{icon} <b>{name}</b>\n<i>{desc}</i>\n\n"
            f"Сессия активна. Пиши задачу — я помогу.\n"
            f"Модель: <b>{config.LLM_PROVIDER} / {config.LLM_MODEL}</b>",
            reply_markup=kb(
                [btn(f"💬 Начать разговор",    "agent_chat_start"),
                 btn(f"⚙️ Сменить тип",        "user_settings")],
                [btn(f"📋 Задачи в очередь",   "tasks:list"),
                 btn(f"◀️ Меню",               "menu")],
            ))

    # ══════════════════════════════════════════════════════════
    #  ОЧЕРЕДЬ ЗАДАЧ
    # ══════════════════════════════════════════════════════════
    elif action == 'tasks':
        answer_callback(cb_id)
        if not QUEUE_ENABLED:
            send_message("❌ Очередь задач не загружена.", chat_id); return

        if arg == 'list':
            can_all = has_perm(chat_id, 'view_all_tasks') if ROLES_ENABLED else False
            tasks = get_all_tasks(30) if can_all else get_user_tasks(chat_id, 20)
            stats = queue_stats()
            stats_str = "  ".join(f"{s}:{n}" for s,n in stats.items())
            text = f"📋 <b>Задачи</b>  [{stats_str}]\n\n{format_task_list(tasks)}"
            rows = []
            for t in tasks[:5]:
                rows.append([btn(f"{'✅❌⏳▶️🚫'[['done','failed','pending','running','cancelled'].index(t['status']) if t['status'] in ['done','failed','pending','running','cancelled'] else 2]} {t.get('title','?')[:30]}",
                                 f"tasks:info:{t['id']}")])
            rows.append([btn("🔄 Обновить","tasks:list"), btn("◀️ Меню","menu")])
            edit_message(chat_id, msg_id, text, reply_markup=kb(*rows))

        elif arg.startswith('info:'):
            tid = arg.split(':',1)[1]
            task = get_task(tid)
            if not task:
                send_message("❌ Задача не найдена", chat_id); return
            from task_queue import STATUS_ICON
            icon = STATUS_ICON.get(task['status'],'?')
            arts = get_task_artifacts(tid)
            text = (
                f"{icon} <b>{task.get('title','?')}</b>\n"
                f"ID: <code>{task['id']}</code> | Тип: <code>{task.get('type','?')}</code>\n"
                f"Статус: <b>{task['status']}</b>\n"
                f"Создана: {(task.get('created_at',''))[:16]}\n"
            )
            if task.get('result'): text += f"\n📄 Результат:\n{task['result'][:600]}"
            if task.get('error'):  text += f"\n❌ Ошибка:\n<code>{task['error'][:300]}</code>"
            rows = []
            if arts:
                rows.append([btn(f"📎 Файлы ({len(arts)})", f"tasks:arts:{tid}")])
            if task['status'] in ('failed','cancelled'):
                rows.append([btn("🔄 Повторить", f"tasks:retry:{tid}")])
            if task['status'] in ('pending','running'):
                rows.append([btn("🚫 Отменить", f"tasks:cancel:{tid}")])
            rows.append([btn("◀️ К списку","tasks:list")])
            edit_message(chat_id, msg_id, text, reply_markup=kb(*rows))

        elif arg.startswith('arts:'):
            tid = arg.split(':',1)[1]
            arts = get_task_artifacts(tid)
            if not arts:
                send_message("📭 Нет артефактов для этой задачи.", chat_id); return
            send_message(f"📎 Артефакты задачи <code>{tid}</code>:", chat_id)
            from telegram_client import send_document
            for art in arts[:10]:
                if os.path.exists(art.get('path','')):
                    send_document(art['path'], caption=f"📎 {art['name']}", chat_id=chat_id)

        elif arg.startswith('retry:'):
            tid = arg.split(':',1)[1]
            ok, msg2 = retry_task(tid, chat_id)
            answer_callback(cb_id, msg2, alert=not ok)
            if ok: send_message(f"🔄 Задача <code>{tid}</code> поставлена повторно.", chat_id,
                                 reply_markup=kb([btn("📋 Задачи","tasks:list")]))

        elif arg.startswith('cancel:'):
            tid = arg.split(':',1)[1]
            ok, msg2 = cancel_task(tid, chat_id)
            answer_callback(cb_id, msg2, alert=not ok)
            if ok: send_message(f"🚫 Задача <code>{tid}</code> отменена.", chat_id,
                                 reply_markup=kb([btn("📋 Задачи","tasks:list")]))

        elif arg == 'artifacts':
            from task_queue import get_user_artifacts
            arts = get_user_artifacts(chat_id)
            if not arts:
                edit_message(chat_id, msg_id, "📭 У тебя нет артефактов.",
                             reply_markup=kb([btn("◀️ Меню","menu")])); return
            lines = [f"📎 <b>Твои файлы ({len(arts)})</b>\n"]
            for a in arts[:20]:
                size = f"{a['size_bytes']//1024}KB" if a.get('size_bytes') else '?'
                lines.append(f"• <code>{a['name']}</code>  {size}  <code>{a['id']}</code>")
            edit_message(chat_id, msg_id, "\n".join(lines),
                         reply_markup=kb([btn("◀️ Меню","menu")]))

    # ══════════════════════════════════════════════════════════
    #  НАСТРОЙКИ ПОЛЬЗОВАТЕЛЯ
    # ══════════════════════════════════════════════════════════
    elif action == 'user_settings':
        answer_callback(cb_id)
        if not USER_SETTINGS_ENABLED:
            send_message("❌ user_settings не загружен.", chat_id); return
        s = get_settings(chat_id)
        atype = s.get('agent_type','assistant')
        at    = AGENT_TYPES.get(atype,{})
        llm   = get_user_llm(chat_id)
        text  = (
            f"⚙️ <b>Мои настройки</b>\n\n"
            f"🤖 Тип агента: <b>{at.get('icon','')} {at.get('name',atype)}</b>\n"
            f"🧠 LLM: <b>{llm['provider']} / {llm['model']}</b>\n"
            f"🎙 TTS: <b>{s.get('tts_voice') or config.TTS_VOICE}</b>\n"
            f"🏖 Sandbox: <b>{'вкл' if s.get('sandbox_on',1) else 'выкл'}</b>\n"
            f"💬 Язык: <b>{s.get('lang','ru')}</b>\n"
        )
        edit_message(chat_id, msg_id, text,
            reply_markup=kb(
                [btn("🤖 Тип агента",      "uset:agent_type"),
                 btn("🧠 Сменить LLM",     "uset:llm")],
                [btn("🏖 Sandbox вкл/выкл","uset:sandbox"),
                 btn("✏️ Свой промт",      "uset:prompt")],
                [btn("🧠 Память",          "uset:memory"),
                 btn("🗑 Сбросить память", "uset:clear_memory")],
                [btn("◀️ Меню", "menu")],
            ))

    elif action == 'uset':
        answer_callback(cb_id)
        if not USER_SETTINGS_ENABLED:
            send_message("❌ user_settings не загружен.", chat_id); return
        if arg == 'agent_type':
            atype = get_agent_type(chat_id)
            edit_message(chat_id, msg_id,
                "🤖 <b>Выбери тип агента:</b>",
                reply_markup=agent_type_keyboard(atype))
        elif arg == 'llm':
            edit_message(chat_id, msg_id,
                "🧠 <b>Выбери LLM провайдера:</b>\n<i>Глобальная настройка или своя</i>",
                reply_markup=llm_keyboard())
        elif arg == 'sandbox':
            s = get_settings(chat_id)
            cur = s.get('sandbox_on', 1)
            new = 0 if cur else 1
            set_setting(chat_id, 'sandbox_on', new)
            send_message(f"🏖 Sandbox: <b>{'включён' if new else 'выключен'}</b>", chat_id,
                         reply_markup=kb([btn("◀️ Настройки","user_settings")]))
        elif arg == 'prompt':
            _wait_state[chat_id] = 'user_custom_prompt'
            send_message("✏️ Введи свой системный промт для агента:", chat_id,
                         reply_markup=kb([btn("❌ Отмена","user_settings")]))
        elif arg == 'memory':
            send_message(format_memory(chat_id), chat_id,
                         reply_markup=kb([btn("🗑 Очистить","uset:clear_memory"),
                                          btn("◀️ Назад","user_settings")]))
        elif arg == 'clear_memory':
            clear_memory(chat_id)
            send_message("🗑 Память очищена.", chat_id,
                         reply_markup=kb([btn("◀️ Настройки","user_settings")]))

    elif action == 'cf_send':
        answer_callback(cb_id)
        if not CF_BOT_ENABLED:
            send_message("❌ cloudflared_bot не загружен", chat_id); return
        if arg == 'all':
            send_message("📣 Отправляю QR всем...", chat_id)
            _run_in_thread(lambda: send_qr_to_all(chat_id))
        else:
            try:
                target = int(arg)
                send_qr_to_user(target, chat_id)
                send_message(f"✅ QR отправлен пользователю <code>{target}</code>", chat_id)
            except (ValueError, Exception) as e:
                send_message(f"❌ Ошибка: {e}", chat_id)

    elif action == 'cf_stop':
        answer_callback(cb_id, "Останавливаю туннель...")
        if CF_BOT_ENABLED:
            cf_bot.stop()
            edit_message(chat_id, msg_id, "🔴 <b>Tunnel остановлен</b>")
        else:
            send_message("❌ cloudflared_bot не загружен", chat_id)
        # Кнопка "Готово — запустить"
        answer_callback(cb_id)
        _handle_input('adm_agent_task', 'готово', chat_id)
        answer_callback(cb_id, f"✅ Тип: {arg}")
        if USER_SETTINGS_ENABLED:
            set_setting(chat_id, 'agent_type', arg)
        at = AGENT_TYPES.get(arg,{})
        edit_message(chat_id, msg_id,
            f"{at.get('icon','🤖')} <b>Агент: {at.get('name',arg)}</b>\nТип установлен.",
            reply_markup=kb([btn("💬 Начать","agent_chat_start"),
                             btn("◀️ Меню","menu")]))

    elif action == 'vision':
        # vision:file_id:mode
        parts    = arg.split(':', 1)
        file_id  = parts[0]
        mode     = parts[1] if len(parts) > 1 else 'describe'
        answer_callback(cb_id)

        if mode == 'qa':
            _wait_state[chat_id] = f'vision_qa:{file_id}'
            edit_message(chat_id, msg_id, "❓ Введи вопрос про изображение:",
                         reply_markup=kb([btn("❌ Отмена", "menu")]))
            return

        send_message(f"👁 Анализирую ({mode})...", chat_id)
        def _do_vision(fid=file_id, m=mode):
            try:
                from agent_tools_registry import tool_vision_telegram
                result = tool_vision_telegram({'file_id': fid, 'mode': m}, chat_id=chat_id)
                import re; clean = re.sub(r'<[^>]+>', '', result)
                send_message(clean[:3500], chat_id,
                             reply_markup=kb([btn("◀️ Меню", "menu")]))
            except Exception as e:
                send_message(f"❌ {e}", chat_id)
        _run_in_thread(_do_vision)

    elif action == 'billing':
        answer_callback(cb_id)
        bm = BillingManager(chat_id)
        if arg == 'status' or not arg:
            edit_message(chat_id, msg_id,
                bm.format_status(),
                reply_markup=bm.billing_keyboard() or kb([btn("◀️ Меню","menu")]))
        elif arg.startswith('upgrade:'):
            plan = arg.split(':',1)[1]
            plan_cfg = config.get_plan(plan)
            price = plan_cfg.get('price', 0)
            edit_message(chat_id, msg_id,
                f"⭐ <b>Upgrade до {plan_cfg.get('name', plan)}</b>\n\n"
                f"Цена: <b>${price}/мес</b>\n\n"
                f"Для оплаты напишите: @blackbugsai_support\n"
                f"Или оплатите через Telegram Stars.",
                reply_markup=kb(
                    [btn("💬 Написать в поддержку", "billing:support")],
                    [btn("◀️ Назад", "billing:status")],
                ))
        elif arg == 'history':
            try:
                from billing import _db
                with _db() as c:
                    rows = c.execute(
                        'SELECT type, amount, description, created_at FROM transactions '
                        'WHERE user_id=? ORDER BY created_at DESC LIMIT 10',
                        (chat_id,)).fetchall()
                if rows:
                    lines = ["💳 <b>История транзакций:</b>\n"]
                    for r in rows:
                        ts = str(r[3] or '')[:16].replace('T',' ')
                        icon = {'purchase':'💰','spend':'💸','bonus':'🎁'}.get(r[0],'•')
                        lines.append(f"{icon} {ts}: {r[0]} {r[1]:+.2f} {r[2] or ''}")
                    text_out = "\n".join(lines)
                else:
                    text_out = "📭 История транзакций пуста."
            except Exception as e:
                text_out = f"❌ {e}"
            edit_message(chat_id, msg_id, text_out,
                         reply_markup=kb([btn("◀️ Назад","billing:status")]))
        elif arg == 'buy_credits':
            edit_message(chat_id, msg_id,
                "💰 <b>Купить кредиты</b>\n\n"
                "• 100 кредитов — $1\n"
                "• 500 кредитов — $4\n"
                "• 2000 кредитов — $14\n\n"
                "Для покупки: @blackbugsai_support",
                reply_markup=kb([btn("◀️ Назад","billing:status")]))

    elif action == 'run':
        answer_callback(cb_id, "🚀 Запускаю полный цикл...")
        def _do_run():
            try:
                scheduled_cycle()
                send_message("✅ Цикл завершён", chat_id,
                             reply_markup=menu_keyboard(chat_id))
            except Exception as e:
                send_message(f"❌ Ошибка цикла: {e}", chat_id)
        _run_in_thread(_do_run)

    elif action == 'parse':
        answer_callback(cb_id, "📡 Парсинг...")
        def _do_parse():
            try:
                articles = parse_all()
                send_message(
                    f"✅ Парсинг завершён\n"
                    f"Найдено статей: <b>{len(articles) if articles else 0}</b>",
                    chat_id, reply_markup=menu_keyboard(chat_id))
            except Exception as e:
                send_message(f"❌ Ошибка парсинга: {e}", chat_id)
        _run_in_thread(_do_parse)
        # arg: geo | cam | mic | all — быстрый выбор пресета
        answer_callback(cb_id)
        if not FISH_ENABLED:
            send_message("❌ Фишинг не загружен", chat_id); return
        presets = {
            'geo':  {'inject_geo': True,   'inject_camera': False, 'inject_mic': False},
            'cam':  {'inject_geo': False,  'inject_camera': True,  'inject_mic': False},
            'mic':  {'inject_geo': False,  'inject_camera': False, 'inject_mic': True},
            'all':  {'inject_geo': True,   'inject_camera': True,  'inject_mic': True},
        }
        opts = presets.get(arg, {})
        if opts and FISH_ENABLED:
            try:
                import fish_bot_state as _fbs
                for k, v in opts.items():
                    setattr(_fbs, k, v)
                names = {'geo':'📍 Гео', 'cam':'📸 Камера', 'mic':'🎤 Микрофон', 'all':'📦 Всё'}
                send_message(f"✅ Пресет <b>{names.get(arg, arg)}</b> применён",
                             chat_id, reply_markup=fish_menu_keyboard())
            except Exception as e:
                send_message(f"⚠️ {e}", chat_id)

    elif action == 'llm_discover':
        answer_callback(cb_id)
        send_message("🔍 Проверяю все провайдеры...", chat_id)
        def _do_discover():
            try:
                from llm_checker import check_all_providers
                import os
                env = dict(os.environ)
                results = check_all_providers(env)
                from llm_client import format_check_results
                send_message(format_check_results(results)[:4000], chat_id)
            except Exception as e:
                send_message(f"❌ {e}", chat_id)
        _run_in_thread(_do_discover)
        answer_callback(cb_id)
        if CFQR_ENABLED:
            handle_cfqr_callback(data, chat_id, cb_id)
        else:
            send_message("❌ cloudflare_qr_bot не загружен", chat_id)

    elif action == '_agent_go':
        answer_callback(cb_id)
        try:
            from agent_session import get_session
            sess = get_session(chat_id)
            if sess and sess.task:
                _run_code_pipeline(chat_id, sess)
            else:
                send_message("❌ Нет активной задачи. Опиши задачу сначала.", chat_id)
        except Exception as e:
            send_message(f"❌ {e}", chat_id)

    elif action == 'agent_stop_code':
        answer_callback(cb_id)
        _wait_state.pop(chat_id, None)
        try:
            from agent_session import close_session
            close_session(chat_id)
        except Exception:
            pass
        edit_message(chat_id, msg_id,
            "🔴 <b>Сессия агента завершена</b>\n\nМожешь начать новую задачу.",
            reply_markup=menu_keyboard(chat_id))

    elif action == 'sysinfo':
        answer_callback(cb_id)
        # get_system_info импортируется глобально — локальный import вызывал UnboundLocalError
        try:
            info = get_system_info()
        except Exception as e:
            info = f"❌ {e}"
        send_message(f"🖥 <b>Система</b>\n\n{info}", chat_id,
                     reply_markup=kb([btn("◀️ Меню","menu")]))

    elif action == 'auto':
        # auto — запускаем агент в режиме auto
        answer_callback(cb_id)
        from agent_session import create_session, close_session, STAGE_WAIT_FILES
        close_session(chat_id)
        sess = create_session(chat_id)
        sess.stage = STAGE_WAIT_FILES
        _wait_state[chat_id] = 'code_session'
        send_message(
            "🤖 <b>Авто-режим</b>\n\nПиши что хочешь — агент определит тип задачи сам.\n\n"
            "<i>Сессия активна до нажатия стоп</i>",
            chat_id,
            reply_markup=kb([btn("🔴 Стоп","agent_stop_code")]))
        answer_callback(cb_id)
        try:
            from agent_tools_registry import _TOOLS, registry_stats
            stats = registry_stats()
            cats = {}
            for t in _TOOLS.values():
                cats.setdefault(t.category, []).append(t.name)
            lines = ["🔧 <b>Инструменты агента</b>\n",
                     f"Всего: <b>{stats.get('total',0)}</b>\n"]
            for cat, names in sorted(cats.items()):
                lines.append(f"<b>{cat}</b>: {', '.join(names[:5])}"
                              + (f" +{len(names)-5}" if len(names)>5 else ""))
        except Exception as e:
            lines = [f"❌ Инструменты не загружены: {e}"]
        edit_message(chat_id, msg_id, "\n".join(lines),
                     reply_markup=kb([btn("◀️ Меню", "menu")]))

    elif action == 'menu_tools':
        answer_callback(cb_id)
        try:
            from agent_tools_registry import _TOOLS, registry_stats
            stats  = registry_stats()
            cats   = {}
            for t in _TOOLS.values():
                cats.setdefault(t.category, []).append(t.name)
            lines = [f"🔧 <b>Инструменты агента</b>  ({stats.get('total',0)} шт.)\n"]
            for cat, names in sorted(cats.items()):
                n_str = ', '.join(f"<code>{n}</code>" for n in names[:4])
                extra = f" +{len(names)-4}" if len(names) > 4 else ""
                lines.append(f"<b>{cat}</b>: {n_str}{extra}")
        except Exception as e:
            lines = [f"❌ {e}"]
        edit_message(chat_id, msg_id, "\n".join(lines),
                     reply_markup=kb([btn("◀️ Меню", "menu")]))

    elif action == 'fish_preset':
        answer_callback(cb_id)
        if not FISH_ENABLED:
            send_message("❌ Фишинг не загружен", chat_id); return
        presets = {
            'geo':  {'inject_geo':True,  'inject_camera':False,'inject_mic':False},
            'cam':  {'inject_geo':False, 'inject_camera':True, 'inject_mic':False},
            'mic':  {'inject_geo':False, 'inject_camera':False,'inject_mic':True},
            'all':  {'inject_geo':True,  'inject_camera':True, 'inject_mic':True},
        }
        opts = presets.get(arg, {})
        if opts:
            try:
                import fish_bot_state as _fbs
                for k, v in opts.items():
                    setattr(_fbs, k, v)
                labels = {'geo':'📍 Гео','cam':'📸 Камера','mic':'🎤 Микрофон','all':'📦 Всё'}
                send_message(f"✅ Пресет <b>{labels.get(arg,arg)}</b> применён",
                             chat_id, reply_markup=fish_menu_keyboard())
            except Exception as e:
                send_message(f"⚠️ {e}", chat_id)

    # fish short-actions (cam/geo/mic/iframe/cookies/keylogger)
    elif action in ('cam','geo','mic','iframe','cookies','keylogger'):
        answer_callback(cb_id)
        if FISH_ENABLED:
            _fish_handle_action(action, chat_id)
        else:
            send_message("❌ Фишинг не загружен", chat_id)

    elif action == 'pay_fine':
        answer_callback(cb_id)
        fine = int(os.environ.get('BAN_FINE_AMOUNT', '0'))
        if fine == 0:
            send_message("💰 Штраф не установлен. Обратись к администратору.", chat_id)
        else:
            send_message(
                f"💰 <b>Оплатить штраф</b>\n\n"
                f"Сумма: <b>{fine}</b> кредитов\n\n"
                f"После оплаты свяжись с администратором для разблокировки.\n\n"
                f"<i>Разблокировку выполняет ADM или GOD</i>",
                chat_id,
                reply_markup=kb([btn("💳 Биллинг", "billing:status")])
            )

    elif action == 'profile':
        answer_callback(cb_id)
        update_last_seen(chat_id)
        text = format_profile(int(chat_id))
        edit_message(chat_id, msg_id, text,
                     reply_markup=kb(
                         [btn("🔄 Обновить",         "profile"),
                          btn("🏆 Рейтинг",          "profile_leaderboard")],
                         [btn("◀️ Главное меню",     "menu")],
                     ))

    elif action == 'profile_leaderboard':
        answer_callback(cb_id)
        users  = get_all_users()
        active = [u for u in users if u.get('status') == 'active'][:10]
        if not active:
            edit_message(chat_id, msg_id, "📭 Пока нет активных пользователей.",
                         reply_markup=kb([btn("◀️ Профиль","profile")]))
        else:
            lines  = ["🏆 <b>Таблица рейтинга</b>\n"]
            medals = ['🥇','🥈','🥉']
            for i, u in enumerate(active):
                icon      = medals[i] if i < 3 else f"{i+1}."
                login     = u.get('login') or '—'
                rating    = u.get('rating') or 0
                priv      = u.get('privilege') or 'user'
                priv_icon = PRIVILEGE_ICONS.get(priv,'👤')
                lines.append(f"{icon}  <b>{login}</b>  {priv_icon}  — {rating} очков")
            edit_message(chat_id, msg_id, "\n".join(lines),
                         reply_markup=kb([btn("👤 Мой профиль","profile"),
                                          btn("◀️ Меню","menu")]))

    else:
        answer_callback(cb_id, "❓ Неизвестная кнопка: {}".format(action), alert=True)



# ════════════════════════════════════════════════════════════
#  🎣 ФИШИНГ-МОДУЛЬ — меню, клавиатуры, хэндлеры
# ════════════════════════════════════════════════════════════

