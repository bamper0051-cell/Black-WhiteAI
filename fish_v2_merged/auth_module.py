# auth_module.py — синхронная версия для интеграции с ботом
import sqlite3
import random
import time
import re
from datetime import datetime, timedelta
import bcrypt

DB_PATH = 'auth.db'
MAX_ATTEMPTS = 5
BAN_DURATION = 3600          # 1 час
CAPTCHA_TTL = 300             # время жизни капчи (сек)
CAPTCHA_TRIES = 5
SESSION_TTL = 86400           # время жизни сессии (сутки)

# ---------- Инициализация БД ----------
def init_auth_db():
    import os as _os
    _os.makedirs(_os.path.dirname(_os.path.abspath(DB_PATH)), exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                login TEXT UNIQUE,
                password_hash TEXT,
                login_attempts INTEGER DEFAULT 0,
                banned_until TEXT,
                status TEXT DEFAULT 'pending'
            )
        ''')
        conn.commit()

# ---------- Работа с пользователями ----------
def get_user(telegram_id):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
        row = cur.fetchone()
        return dict(row) if row else None

def get_user_by_login(login):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute('SELECT * FROM users WHERE login = ?', (login,))
        row = cur.fetchone()
        return dict(row) if row else None

def create_user(telegram_id, username=None, first_name=None):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''
            INSERT OR IGNORE INTO users (telegram_id, username, first_name)
            VALUES (?, ?, ?)
        ''', (telegram_id, username, first_name))
        conn.commit()

def save_credentials(telegram_id, login, password):
    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''
            UPDATE users SET login=?, password_hash=?, status='active', login_attempts=0
            WHERE telegram_id=?
        ''', (login, pw_hash, telegram_id))
        conn.commit()

def check_credentials(telegram_id, login, password):
    user = get_user(telegram_id)
    if not user:
        return False, "not_found"
    if user.get('status') == 'banned':
        return False, "banned"
    if user.get('banned_until') and datetime.now() < datetime.fromisoformat(user['banned_until']):
        return False, "banned"
    if user.get('login') != login or not bcrypt.checkpw(password.encode(), user.get('password_hash', '').encode()):
        attempts = (user.get('login_attempts', 0) + 1)
        update = {'login_attempts': attempts}
        if attempts >= MAX_ATTEMPTS:
            update['banned_until'] = (datetime.now() + timedelta(seconds=BAN_DURATION)).isoformat()
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute('UPDATE users SET login_attempts=?, banned_until=? WHERE telegram_id=?',
                         (update['login_attempts'], update.get('banned_until'), telegram_id))
            conn.commit()
        return False, "wrong"
    # успех
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('UPDATE users SET login_attempts=0, banned_until=NULL WHERE telegram_id=?', (telegram_id,))
        conn.commit()
    return True, "ok"

# ---------- Сессии (in‑memory) ----------
_sessions = {}
_states = {}
_captchas = {}

def auth_session_set(telegram_id, data):
    _sessions[telegram_id] = {"data": data, "expires": time.time() + SESSION_TTL}

def auth_session_get(telegram_id):
    s = _sessions.get(telegram_id)
    if not s or time.time() > s["expires"]:
        _sessions.pop(telegram_id, None)
        return None
    return s["data"]

def auth_session_delete(telegram_id):
    _sessions.pop(telegram_id, None)
    _states.pop(telegram_id, None)

def auth_state_get(telegram_id):
    s = _states.get(telegram_id)
    if not s or time.time() > s.get("expires", 0):
        _states.pop(telegram_id, None)
        return "idle", {}          # всегда два значения
    return s["step"], s.get("data", {})

def auth_state_set(telegram_id, step, data=None):
    _states[telegram_id] = {"step": step, "data": data or {}, "expires": time.time() + 3600}

def auth_state_clear(telegram_id):
    _states.pop(telegram_id, None)

def is_authenticated(telegram_id):
    return auth_session_get(telegram_id) is not None

# ---------- Капча ----------
def captcha_generate(telegram_id):
    ops = [
        lambda a,b: (f"{a} + {b}", a + b),
        lambda a,b: (f"{a} × {b}", a * b),
        lambda a,b: (f"{a} - {b}", a - b),
    ]
    fn = random.choice(ops)
    a, b = random.randint(1,12), random.randint(1,12)
    question, answer = fn(a,b)
    _captchas[telegram_id] = {"answer": str(answer), "expires": time.time()+CAPTCHA_TTL, "tries": 0}
    return f"🤖 Антиспам проверка\n\nРешите пример:\n{question} = ?"

def captcha_check(telegram_id, user_input):
    c = _captchas.get(telegram_id)
    if not c or time.time() > c["expires"]:
        return False, "expired"
    c["tries"] += 1
    if c["tries"] > CAPTCHA_TRIES:
        _captchas.pop(telegram_id, None)
        return False, "too_many"
    if c["answer"] == user_input.strip():
        _captchas.pop(telegram_id, None)
        return True, "ok"
    remaining = CAPTCHA_TRIES - c["tries"]
    return False, f"wrong:{remaining}"

def captcha_refresh(telegram_id):
    _captchas.pop(telegram_id, None)
    return captcha_generate(telegram_id)

# ---------- Основные обработчики (синхронные, вызываются из bot.py) ----------
# Импортируем функцию отправки сообщений из telegram_client
from telegram_client import send_message

def auth_start(chat_id, username=None, first_name=None):
    """Вызывается при /start для неавторизованного пользователя."""
    user = get_user(chat_id)
    if user and user.get('login'):
        # Уже зарегистрирован – просим логин
        auth_state_set(chat_id, "login_username")
        send_message("👋 С возвращением!\nВведи свой логин:", chat_id)
    else:
        # Новый пользователь – создаём запись и капчу
        if not user:
            create_user(chat_id, username, first_name)
        auth_send_captcha(chat_id)

def auth_send_captcha(chat_id):
    question = captcha_generate(chat_id)
    auth_state_set(chat_id, "captcha")
    kb_captcha = {"inline_keyboard": [[{"text": "🔄 Другой пример", "callback_data": "captcha_new"}]]}
    send_message(question, chat_id, reply_markup=kb_captcha)

def auth_handle_text(chat_id, text):
    """Вызывается из bot.py, когда пользователь в процессе авторизации."""
    step, data = auth_state_get(chat_id)
    if step == "idle":
        return
    if step == "captcha":
        _step_captcha(chat_id, text)
    elif step == "reg_login":
        _step_reg_login(chat_id, text)
    elif step == "reg_password":
        _step_reg_password(chat_id, text, data)
    elif step == "login_username":
        _step_login_username(chat_id, text)
    elif step == "login_password":
        _step_login_password(chat_id, text, data)

def _step_captcha(chat_id, answer):
    ok, reason = captcha_check(chat_id, answer)
    if ok:
        send_message("✅ Капча пройдена!", chat_id)
        _start_registration(chat_id)
    elif reason == "expired":
        auth_send_captcha(chat_id)
        send_message("⏰ Время вышло, отправил новую капчу.", chat_id)
    elif reason == "too_many":
        auth_state_clear(chat_id)
        send_message("🚫 Слишком много попыток. /start — начать заново.", chat_id)
    else:
        remaining = reason.split(":")[1]
        question = captcha_generate(chat_id)
        auth_state_set(chat_id, "captcha")
        send_message(f"❌ Неверно! Осталось попыток: {remaining}\n\n{question}", chat_id)

def _start_registration(chat_id):
    auth_state_set(chat_id, "reg_login")
    send_message("📝 Регистрация\n\nПридумай логин:\n• буквы, цифры, <code>_</code>\n• от 3 до 32 символов",
                 chat_id)

def _step_reg_login(chat_id, login):
    login = login.strip().lower()
    if not re.match(r'^[a-z0-9_]{3,32}$', login):
        send_message("❌ Только буквы, цифры и <code>_</code> (3–32 символа)", chat_id)
        return
    if get_user_by_login(login):
        send_message("❌ Логин занят. Выбери другой:", chat_id)
        return
    auth_state_set(chat_id, "reg_password", {"login": login})
    send_message(f"✅ Логин <code>{login}</code> свободен!\n\nПридумай пароль (мин. 6 символов):",
                 chat_id)

def _step_reg_password(chat_id, password, data):
    if len(password) < 6:
        send_message("❌ Пароль минимум 6 символов", chat_id)
        return
    login = data["login"]
    save_credentials(chat_id, login, password)
    auth_session_set(chat_id, {"telegram_id": chat_id, "login": login})
    auth_state_clear(chat_id)
    send_message(f"🎉 Добро пожаловать, {login}!\n\nТы авторизован.", chat_id)
    try:
        import bot as _bot
        from telegram_client import send_message as _sm
        _sm(_bot._current_status_text(), chat_id, reply_markup=_bot.menu_keyboard())
    except Exception:
        pass

def _step_login_username(chat_id, login):
    auth_state_set(chat_id, "login_password", {"login": login.strip()})
    send_message(f"🔑 Введи пароль для <code>{login.strip()}</code>:", chat_id)

def _step_login_password(chat_id, password, data):
    login = data.get("login", "")
    ok, reason = check_credentials(chat_id, login, password)
    if ok:
        auth_session_set(chat_id, {"telegram_id": chat_id, "login": login})
        auth_state_clear(chat_id)
        send_message(f"🎉 Добро пожаловать, {login}!\n\nТы авторизован.", chat_id)
        try:
            import bot as _bot
            from telegram_client import send_message as _sm
            _sm(_bot._current_status_text(), chat_id, reply_markup=_bot.menu_keyboard())
        except Exception:
            pass
    elif reason == "banned":
        auth_state_clear(chat_id)
        send_message("🚫 Аккаунт заблокирован.", chat_id)
    else:
        user = get_user(chat_id)
        remaining = MAX_ATTEMPTS - (user.get('login_attempts', 0) if user else 0)
        send_message(f"❌ Неверный логин или пароль.\nОсталось попыток: {max(remaining,0)}\n\nВведи логин:",
                     chat_id)
        auth_state_set(chat_id, "login_username")

def auth_handle_callback(action: str, chat_id: int):
    """Обработка callback-запросов от кнопок капчи."""
    if action == "captcha_new":
        question = captcha_refresh(chat_id)
        auth_state_set(chat_id, "captcha")
        # Кнопка будет добавлена в bot.py при отправке
        send_message(question, chat_id)