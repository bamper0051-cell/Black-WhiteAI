"""
admin_module.py — Панель администратора АВТОМУВИ
Управление пользователями, remote control, мониторинг, процессы
"""
import os, sys, subprocess, threading, time, json, sqlite3
from datetime import datetime
import config

def _decode_bytes(b):
    if not b: return ''
    for enc in ('utf-8','cp1251','cp866','latin-1'):
        try: return b.decode(enc)
        except: pass
    return b.decode('utf-8', errors='replace')


# Lazy-импорт из auth_module — чтобы не падать если bcrypt не установлен
def _auth():
    from auth_module import (
        get_user, get_all_users, set_privilege, add_rating,
        format_profile, PRIVILEGE_ICONS, PRIVILEGE_LABELS, auth_session_delete
    )
    return locals()

def get_user(telegram_id):
    from auth_module import get_user as _f; return _f(telegram_id)

def get_all_users():
    from auth_module import get_all_users as _f; return _f()

def set_privilege(tid, priv):
    from auth_module import set_privilege as _f; return _f(tid, priv)

def add_rating(tid, pts=1):
    from auth_module import add_rating as _f; return _f(tid, pts)

def format_profile(tid):
    from auth_module import format_profile as _f; return _f(tid)

def auth_session_delete(tid):
    try:
        from auth_module import auth_session_delete as _f; _f(tid)
    except Exception: pass

try:
    from auth_module import PRIVILEGE_ICONS, PRIVILEGE_LABELS
except Exception:
    PRIVILEGE_ICONS  = {'user':'👤','vip':'💎','admin':'🔑','owner':'👑','banned':'🚫'}
    PRIVILEGE_LABELS = {'user':'Пользователь','vip':'VIP','admin':'Администратор',
                        'owner':'Владелец','banned':'Заблокирован'}

# ─── Конфиг доступа ──────────────────────────────────────────────────────────
# ADMIN_IDS берётся из .env: ADMIN_IDS=123456789,987654321
def _load_admin_ids():
    raw = os.environ.get('ADMIN_IDS', '') or os.environ.get('TELEGRAM_CHAT_ID', '')
    return set(int(x.strip()) for x in raw.replace(';', ',').split(',') if x.strip().isdigit())

def is_god(chat_id) -> bool:
    """GOD роль — полный доступ."""
    ids = _load_admin_ids()
    if int(chat_id) in ids:
        return True
    u = get_user(int(chat_id))
    return bool(u and u.get('privilege') in ('god', 'owner'))

def is_admin(chat_id) -> bool:
    """ADM или GOD."""
    if is_god(chat_id): return True
    u = get_user(int(chat_id))
    return bool(u and u.get('privilege') in ('adm', 'admin'))

def is_owner(chat_id) -> bool:
    """Алиас для is_god (обратная совместимость)."""
    return is_god(chat_id)

def is_vip(chat_id) -> bool:
    u = get_user(int(chat_id))
    return bool(u and u.get('privilege') == 'vip')

def is_banned(chat_id) -> bool:
    u = get_user(int(chat_id))
    return bool(u and u.get('privilege') in ('ban', 'banned') or
                (u and u.get('status') == 'banned'))

def get_role(chat_id) -> str:
    """Возвращает роль пользователя."""
    ids = _load_admin_ids()
    if int(chat_id) in ids:
        return 'god'
    u = get_user(int(chat_id))
    if not u: return 'noob'
    priv = u.get('privilege', 'user')
    # Нормализация старых ролей
    mapping = {'owner': 'god', 'admin': 'adm', 'banned': 'ban'}
    return mapping.get(priv, priv)

def require_admin(chat_id, send_fn):
    if not is_admin(chat_id):
        send_fn("🚫 Нет доступа. Требуются права администратора.", chat_id)
        return False
    return True

# ─── Клавиатуры ──────────────────────────────────────────────────────────────
def kb(*rows):
    return {"inline_keyboard": list(rows)}

def btn(text, data):
    return {"text": text, "callback_data": data}

def admin_main_keyboard():
    return kb(
        [btn("══ 👥 ПОЛЬЗОВАТЕЛИ ══", "adm_noop")],
        [btn("📋 Список пользователей", "adm:users"),
         btn("🔍 Найти юзера",          "adm:find_user")],
        [btn("🚫 Заблокировать",        "adm:ban_list"),
         btn("✅ Разблокировать",        "adm:unban_list")],
        [btn("💎 Выдать привилегию",     "adm:set_priv"),
         btn("⭐ Начислить рейтинг",    "adm:add_rating")],

        [btn("══ 📨 СООБЩЕНИЯ ══",      "adm_noop")],
        [btn("📩 Написать юзеру",        "adm:msg_user"),
         btn("📣 Рассылка всем",         "adm:broadcast")],
        [btn("🔔 Уведомление онлайн",    "adm:notify_online")],

        [btn("══ 🤖 БОТЫ И АГЕНТЫ ══",  "adm_noop")],
        [btn("📋 Активные процессы",     "adm:processes"),
         btn("🤖 АГЕНТ_0051",             "adm:spawn_agent")],
        [btn("🕵️ АГЕНТ_СМИТ",           "adm:smith_menu"),
         btn("💀 Убить процесс",         "adm:kill_proc")],
        [btn("📡 Cloudflared QR",        "adm:cloudflared_qr"),
         btn("🔄 Перезапустить бота",    "adm:restart_bot")],

        [btn("══ 🖥 СИСТЕМА ══",         "adm_noop")],
        [btn("🩺 Системная инфо",        "adm:sysinfo"),
         btn("💻 Выполнить команду",     "adm:exec_cmd")],
        [btn("📁 Файлы бота",            "adm:files"),
         btn("📊 Логи",                  "adm:logs")],
        [btn("⚙️ Изменить .env",        "adm:edit_env"),
         btn("🔄 Reload config",         "adm:reload_config")],

        [btn("══ 🔐 БЕЗОПАСНОСТЬ ══",   "adm_noop")],
        [btn("🗝 Все API ключи",          "adm:show_keys"),
         btn("📜 История команд",        "adm:cmd_history")],
        [btn("☁️ Cloudflared QR",        "adm:cfqr_menu")],

        [btn("◀️ Главное меню",          "menu")],
    )

def user_manage_keyboard(target_id):
    u = get_user(int(target_id))
    priv = u.get('privilege','user') if u else 'user'
    status = u.get('status','') if u else ''
    is_banned = (status == 'banned' or priv == 'banned')
    return kb(
        [btn("👤 Профиль",             f"adm:view_user:{target_id}")],
        [btn("📩 Написать",            f"adm:msg_to:{target_id}"),
         btn("📊 Статистика",          f"adm:user_stats:{target_id}")],
        [btn("──── Привилегии ────",   "adm_noop")],
        [btn("👤 → user",              f"adm:priv:{target_id}:user"),
         btn("💎 → VIP",               f"adm:priv:{target_id}:vip")],
        [btn("🔑 → admin",             f"adm:priv:{target_id}:admin"),
         btn("👑 → owner",             f"adm:priv:{target_id}:owner")],
        [btn("──── Действия ────",     "adm_noop")],
        [btn("✅ Разблокировать" if is_banned else "🚫 Заблокировать",
             f"adm:{'unban' if is_banned else 'ban'}:{target_id}")],
        [btn("🔴 Выбить из сессии",    f"adm:kick:{target_id}"),
         btn("🗑 Удалить аккаунт",     f"adm:delete_user:{target_id}")],
        [btn("◀️ Список",              "adm:users")],
    )

# ─── Хранилище состояний ожидания для admin-диалогов ─────────────────────────
_adm_wait = {}   # chat_id → {'action': str, 'data': dict}

def adm_wait_set(chat_id, action, data=None):
    _adm_wait[str(chat_id)] = {'action': action, 'data': data or {}}

def adm_wait_get(chat_id):
    return _adm_wait.get(str(chat_id))

def adm_wait_clear(chat_id):
    _adm_wait.pop(str(chat_id), None)

# ─── Лог команд администратора ───────────────────────────────────────────────
_cmd_log = []   # список dict {admin, cmd, ts}

def log_admin_cmd(admin_id, cmd):
    _cmd_log.append({'admin': admin_id, 'cmd': cmd, 'ts': datetime.now().strftime('%H:%M:%S')})
    if len(_cmd_log) > 200:
        _cmd_log.pop(0)

# ─── Утилиты ─────────────────────────────────────────────────────────────────
def get_system_info():
    import shutil, platform
    lines = [
        f"🖥  <b>Системная информация</b>\n",
        f"💻  ОС: <b>{platform.system()} {platform.machine()}</b>",
        f"🐍  Python: <b>{sys.version.split()[0]}</b>",
    ]
    # CPU
    try:
        lines.append(f"⚙️  CPU ядер: <b>{os.cpu_count()}</b>")
    except: pass
    # RAM
    try:
        with open('/proc/meminfo') as f:
            minfo = {l.split(':')[0]: int(l.split(':')[1].strip().split()[0])
                     for l in f if ':' in l}
        total = minfo.get('MemTotal',0)//1024
        avail = minfo.get('MemAvailable',0)//1024
        lines.append(f"🧠  RAM: <b>{avail} MB</b> свободно / {total} MB")
    except: pass
    # Disk
    try:
        du = shutil.disk_usage(config.BASE_DIR)
        lines.append(f"💾  Диск: <b>{du.free//1024//1024} MB</b> свободно / {du.total//1024//1024} MB")
    except: pass
    # Uptime бота
    try:
        import bot as _b
        uptime = int(time.time() - _b._BOT_START_TIME)
        h,r = divmod(uptime, 3600); m,s = divmod(r, 60)
        lines.append(f"⏱  Аптайм: <b>{h}ч {m}м {s}с</b>")
    except: pass
    # LLM
    lines.append(f"\n🧠  LLM: <b>{config.LLM_PROVIDER} / {config.LLM_MODEL}</b>")
    lines.append(f"🎙  TTS: <b>{config.TTS_PROVIDER} / {config.TTS_VOICE}</b>")
    return "\n".join(lines)

def list_processes():
    """Список Python-процессов — кросс-платформенно."""
    lines = ["🤖 <b>Активные процессы</b>\n"]
    try:
        import platform
        if platform.system() == 'Windows':
            r = subprocess.run(
                ['tasklist', '/FI', 'IMAGENAME eq python.exe', '/FO', 'CSV'],
                capture_output=True, timeout=5
            )
            for line in _decode_bytes(r.stdout).splitlines()[1:]:  # skip header
                parts = [p.strip('"') for p in line.split('","')]
                if len(parts) >= 5:
                    name, pid, _, _, mem = parts[0], parts[1], parts[2], parts[3], parts[4]
                    lines.append(f"📌 PID <code>{pid}</code>  MEM:{mem}\n   <code>{name}</code>")
            # Также wmic для полных путей
            r2 = subprocess.run(
                ['wmic', 'process', 'where', 'name="python.exe"', 'get',
                 'ProcessId,CommandLine', '/format:csv'],
                capture_output=True, timeout=5
            )
            seen_pids = set()
            for line in r2.stdout.splitlines()[2:]:
                if ',' not in line: continue
                parts2 = line.strip().split(',', 2)
                if len(parts2) >= 3:
                    cmd_line = parts2[1][:70]
                    pid2 = parts2[2].strip()
                    if pid2 and pid2 not in seen_pids:
                        seen_pids.add(pid2)
                        lines.append(f"   cmd: <code>{cmd_line}</code>")
        else:
            r = subprocess.run(['ps', 'aux'], capture_output=True, timeout=5)
            for line in _decode_bytes(r.stdout).splitlines():
                if 'python' in line.lower() and 'grep' not in line:
                    parts = line.split()
                    pid  = parts[1] if len(parts) > 1 else '?'
                    cpu  = parts[2] if len(parts) > 2 else '?'
                    mem  = parts[3] if len(parts) > 3 else '?'
                    cmd  = ' '.join(parts[10:])[:60] if len(parts) > 10 else line[:60]
                    lines.append(f"📌 PID <code>{pid}</code>  CPU:{cpu}%  MEM:{mem}%\n   <code>{cmd}</code>")
    except Exception as e:
        lines.append(f"❌ Ошибка получения процессов: {e}")
    return "\n".join(lines) if len(lines) > 1 else "ℹ️ Нет активных Python-процессов"

def kill_process(pid_str):
    try:
        pid = int(pid_str.strip())
        import platform
        if platform.system() == 'Windows':
            r = subprocess.run(['taskkill', '/F', '/PID', str(pid)],
                               capture_output=True, timeout=5)
            if r.returncode == 0:
                return True, f"✅ Процесс {pid} завершён."
            return False, f"❌ {_decode_bytes(r.stderr).strip() or _decode_bytes(r.stdout).strip()}"
        else:
            os.kill(pid, 9)
            return True, f"✅ Процесс {pid} завершён."
    except Exception as e:
        return False, f"❌ {e}"

def exec_shell(cmd, timeout=15):
    """Выполняет shell-команду, возвращает вывод. Кросс-платформенно."""
    import platform
    try:
        # Windows: cp866/cp1251 в консоли — используем bytes и декодируем безопасно
        if platform.system() == 'Windows':
            r = subprocess.run(
                cmd, shell=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                timeout=timeout, cwd=config.BASE_DIR
            )
            # Пробуем cp866 (CMD), потом cp1251, потом utf-8, потом latin-1
            def _decode(b):
                for enc in ('cp866', 'cp1251', 'utf-8', 'latin-1'):
                    try: return b.decode(enc)
                    except: pass
                return b.decode('latin-1', errors='replace')
            stdout = _decode(_decode_bytes(r.stdout)) if _decode_bytes(r.stdout) else ''
            stderr = _decode(_decode_bytes(r.stderr)) if _decode_bytes(r.stderr) else ''
        else:
            r = subprocess.run(
                cmd, shell=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                timeout=timeout, cwd=config.BASE_DIR
            )
            stdout = (_decode_bytes(r.stdout) or b'').decode('utf-8', errors='replace')
            stderr = (_decode_bytes(r.stderr) or b'').decode('utf-8', errors='replace')

        out = ((stdout or '') + (stderr or '')).strip()
        return True, out[:3000] or '(нет вывода)'
    except subprocess.TimeoutExpired:
        return False, f"⏰ Таймаут {timeout}с"
    except Exception as e:
        return False, str(e)

def get_recent_logs(n=50):
    """Последние N строк из stdout-лога если есть."""
    log_paths = [
        os.path.join(config.BASE_DIR, 'bot.log'),
        os.path.join(config.BASE_DIR, 'automuvie.log'),
        '/tmp/bot_stdout.log',
    ]
    for p in log_paths:
        if os.path.exists(p):
            try:
                with open(p, 'r', errors='replace') as f:
                    lines = f.readlines()
                return "".join(lines[-n:])[-3000:]
            except: pass
    return "ℹ️ Лог-файл не найден. Перенаправь stdout: python bot.py > bot.log 2>&1"

def format_users_list(page=0, per_page=8):
    users = get_all_users()
    # Показываем ВСЕХ пользователей (не только с login)
    total  = len(users)
    start  = page * per_page
    chunk  = users[start:start + per_page]
    lines  = [f"👥 <b>Пользователи</b> ({total} чел.)  стр. {page+1}/{max(1,(total-1)//per_page+1)}\n"]
    for u in chunk:
        priv    = u.get('privilege', 'user')
        icon    = PRIVILEGE_ICONS.get(priv, '👤')
        # Имя: username > login > first_name > ID
        name    = (u.get('username') or u.get('login') or
                   u.get('first_name') or str(u['telegram_id']))
        rating  = u.get('rating', 0)
        status  = u.get('status', 'active')
        has_pin = bool(u.get('pin_hash'))
        s_icon  = '🟢' if status == 'active' else ('🔴' if status == 'banned' else '🟡')
        pin_ico = '🔐' if has_pin else '🔓'
        lines.append(
            f"{s_icon}{pin_ico} {icon} <b>{name}</b>  "
            f"⭐{rating}  <code>{u['telegram_id']}</code>"
        )
    rows = []
    for u in chunk:
        name = (u.get('username') or u.get('login') or
                u.get('first_name') or str(u['telegram_id']))
        rows.append([btn(f"⚙️ {name[:20]}", f"adm:manage:{u['telegram_id']}")])
    # Пагинация
    nav = []
    if page > 0:
        nav.append(btn("◀️", f"adm:users_page:{page-1}"))
    if start + per_page < total:
        nav.append(btn("▶️", f"adm:users_page:{page+1}"))
    if nav:
        rows.append(nav)
    rows.append([btn("◀️ Адм. меню", "admin")])
    return "\n".join(lines), kb(*rows)

def ban_user(target_id):
    from auth_module import get_user as _gu
    import sqlite3 as _sql
    from auth_module import DB_PATH
    with _sql.connect(DB_PATH) as c:
        c.execute("UPDATE users SET status='banned', privilege='banned' WHERE telegram_id=?", (int(target_id),))
        c.commit()
    auth_session_delete(int(target_id))

def unban_user(target_id):
    from auth_module import DB_PATH
    import sqlite3 as _sql
    with _sql.connect(DB_PATH) as c:
        c.execute("UPDATE users SET status='active', privilege='user', login_attempts=0, banned_until=NULL WHERE telegram_id=?",
                  (int(target_id),))
        c.commit()

def delete_user(target_id):
    from auth_module import DB_PATH
    import sqlite3 as _sql
    with _sql.connect(DB_PATH) as c:
        c.execute("DELETE FROM users WHERE telegram_id=?", (int(target_id),))
        c.commit()
    auth_session_delete(int(target_id))
