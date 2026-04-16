"""
BlackBugsAI — Auth Module v3
Вход: капча → PIN (только PIN, без логина/пароля)
Дизайн: киберпанк ASCII + анимированные арты
"""
import os, random, time, sqlite3, hashlib, re
import bcrypt
import config
from core.db_manager import BLACKBUGS_DB

# Canonical path: data/blackbugs.db (was: auth.db in project root)
DB_PATH = str(BLACKBUGS_DB)

MAX_ATTEMPTS   = 5
CAPTCHA_TTL    = 300   # 5 минут
PIN_LENGTH     = 4     # длина PIN-кода
CAPTCHA_TYPES  = ['emoji_grid','ascii_art','matrix_decode',
                  'bit_flip','logic_gate','cipher_shift']

PRIVILEGE_ICONS  = {
    'god':  '⚡', 'adm': '🔑', 'vip': '💎',
    'user': '👤', 'noob': '🔰', 'ban': '🚫',
    # legacy aliases
    'owner': '⚡', 'admin': '🔑', 'banned': '🚫',
}
PRIVILEGE_LABELS = {
    'god':  'БОГ',    'adm': 'Администратор', 'vip': 'VIP',
    'user': 'Пользователь', 'noob': 'Новичок', 'ban': 'Заблокирован',
    # legacy
    'owner': 'БОГ', 'admin': 'Администратор', 'banned': 'Заблокирован',
}

# ─── In-memory state ─────────────────────────────────────────────────────────

_captchas      = {}
_pin_attempts  = {}
_auth_state    = {}
_auth_sessions = {}

# ─── DB ──────────────────────────────────────────────────────────────────────

def init_auth_db():
    with sqlite3.connect(DB_PATH) as c:
        c.executescript('''
            CREATE TABLE IF NOT EXISTS users (
                telegram_id   INTEGER PRIMARY KEY,
                username      TEXT,
                first_name    TEXT,
                privilege     TEXT    DEFAULT 'user',
                status        TEXT    DEFAULT 'active',
                pin_hash      TEXT,
                rating        INTEGER DEFAULT 0,
                agent_type    TEXT    DEFAULT 'assistant',
                llm_provider  TEXT,
                llm_model     TEXT,
                tts_voice     TEXT,
                system_prompt TEXT,
                sandbox_on    INTEGER DEFAULT 1,
                settings_json TEXT    DEFAULT '{}',
                memory_json   TEXT    DEFAULT '[]',
                active_task_id TEXT,
                lang          TEXT    DEFAULT 'ru',
                created_at    REAL,
                last_seen     REAL
            );
        ''')
    # Миграция — добавляем недостающие колонки в существующие БД
    _migrate_db()

def _migrate_db():
    """Добавляет недостающие колонки в существующие БД."""
    COLS = [
        ('pin_hash',       'TEXT'),
        ('privilege',      "TEXT DEFAULT 'user'"),
        ('rating',         'INTEGER DEFAULT 0'),
        ('settings_json',  "TEXT DEFAULT '{}'"),
        ('memory_json',    "TEXT DEFAULT '[]'"),
        ('sandbox_on',     'INTEGER DEFAULT 1'),
        ('lang',           "TEXT DEFAULT 'ru'"),
        ('created_at',     'REAL'),
        ('last_seen',      'REAL'),
        ('status',         "TEXT DEFAULT 'active'"),
        ('username',       'TEXT'),
        ('first_name',     'TEXT'),
        ('activity_count', 'INTEGER DEFAULT 0'),
    ]
    with sqlite3.connect(DB_PATH) as c:
        existing = [r[1] for r in c.execute('PRAGMA table_info(users)').fetchall()]
        for col, typedef in COLS:
            if col not in existing:
                try: c.execute(f'ALTER TABLE users ADD COLUMN {col} {typedef}')
                except Exception: pass

def _db():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c

def get_user(telegram_id):
    with _db() as c:
        r = c.execute('SELECT * FROM users WHERE telegram_id=?', (int(telegram_id),)).fetchone()
        return dict(r) if r else None

def get_all_users():
    with _db() as c:
        # Проверяем какие колонки есть — безопасный ORDER BY
        cols = [r[1] for r in c.execute('PRAGMA table_info(users)').fetchall()]
        order = 'created_at DESC' if 'created_at' in cols else 'telegram_id DESC'
        return [dict(r) for r in c.execute(f'SELECT * FROM users ORDER BY {order}').fetchall()]

def create_user(telegram_id, username=None, first_name=None):
    with _db() as c:
        c.execute('''INSERT OR IGNORE INTO users (telegram_id,username,first_name,created_at,last_seen)
                     VALUES (?,?,?,?,?)''',
                  (int(telegram_id), username, first_name, time.time(), time.time()))

def update_last_seen(telegram_id):
    with _db() as c:
        c.execute('UPDATE users SET last_seen=? WHERE telegram_id=?',
                  (time.time(), int(telegram_id)))

def set_privilege(telegram_id, privilege):
    with _db() as c:
        c.execute('UPDATE users SET privilege=? WHERE telegram_id=?',
                  (privilege, int(telegram_id)))
    return True

def add_rating(telegram_id, points):
    with _db() as c:
        c.execute('UPDATE users SET rating=rating+? WHERE telegram_id=?',
                  (int(points), int(telegram_id)))

def is_banned(telegram_id):
    u = get_user(telegram_id)
    return bool(u and (u.get('status') == 'banned' or
                       u.get('privilege') in ('banned', 'ban')))

def has_pin(telegram_id):
    u = get_user(telegram_id)
    return bool(u and u.get('pin_hash'))

def set_pin(telegram_id, pin: str):
    pin_hash = bcrypt.hashpw(pin.encode(), bcrypt.gensalt()).decode()
    with _db() as c:
        # Авто-добавление колонки если отсутствует
        cols = [r[1] for r in c.execute("PRAGMA table_info(users)").fetchall()]
        if 'pin_hash' not in cols:
            c.execute("ALTER TABLE users ADD COLUMN pin_hash TEXT")
        c.execute('UPDATE users SET pin_hash=?, status=? WHERE telegram_id=?',
                  (pin_hash, 'active', int(telegram_id)))

def check_pin(telegram_id, pin: str) -> bool:
    u = get_user(telegram_id)
    if not u or not u.get('pin_hash'):
        return False
    stored = u['pin_hash']
    # Поддержка sha256 fallback
    if stored.startswith('sha256:'):
        import hashlib
        return stored == "sha256:" + hashlib.sha256(pin.encode()).hexdigest()
    try:
        return bcrypt.checkpw(pin.encode(), stored.encode())
    except Exception:
        return False

def format_profile(telegram_id) -> str:
    u = get_user(telegram_id)
    if not u: return "❌ Профиль не найден"
    priv = u.get('privilege','user')
    icon = PRIVILEGE_ICONS.get(priv,'👤')
    name = u.get('first_name') or u.get('username') or 'Агент'
    return (
        f"{icon} <b>{name}</b>\n"
        f"ID: <code>{u['telegram_id']}</code>\n"
        f"Роль: <b>{PRIVILEGE_LABELS.get(priv,priv)}</b>\n"
        f"Рейтинг: ⭐ {u.get('rating',0)}"
    )

def format_users_list(users=None):
    if users is None: users = get_all_users()
    if not users: return "👥 Нет пользователей"
    lines = [f"👥 <b>Пользователи ({len(users)})</b>\n"]
    for u in users[:20]:
        icon = PRIVILEGE_ICONS.get(u.get('privilege','user'),'👤')
        name = u.get('first_name') or u.get('username') or str(u['telegram_id'])
        lines.append(f"{icon} <b>{name}</b> <code>{u['telegram_id']}</code>")
    return "\n".join(lines)

# ─── Session ──────────────────────────────────────────────────────────────────

def auth_state_get(telegram_id):
    return _auth_state.get(str(telegram_id), ('idle', None))

def auth_state_set(telegram_id, step, data=None):
    _auth_state[str(telegram_id)] = (step, data)

def auth_state_clear(telegram_id):
    _auth_state.pop(str(telegram_id), None)

def auth_session_set(telegram_id, data):
    _auth_sessions[str(telegram_id)] = data

def auth_session_get(telegram_id):
    return _auth_sessions.get(str(telegram_id), {})

def auth_session_delete(telegram_id):
    _auth_sessions.pop(str(telegram_id), None)

def is_authenticated(telegram_id):
    return bool(_auth_sessions.get(str(telegram_id), {}).get("authenticated"))

# ─── АРТЫ ────────────────────────────────────────────────────────────────────

_BOOT_FRAMES = [
"""<code>
 ██████╗ ██╗      █████╗  ██████╗██╗  ██╗
 ██╔══██╗██║     ██╔══██╗██╔════╝██║ ██╔╝
 ██████╔╝██║     ███████║██║     █████╔╝
 ██╔══██╗██║     ██╔══██║██║     ██╔═██╗
 ██████╔╝███████╗██║  ██║╚██████╗██║  ██╗
 ╚═════╝ ╚══════╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝
   🖤🐛  BlackBugsAI  |  SYSTEM ACCESS</code>"""
]

_BANNED_ART = """<code>
 ▓█████▄ ▓█████  ███▄    █  ██▓▓█████ ▓█████▄
 ▒██▀ ██▌▓█   ▀  ██ ▀█   █ ▓██▒▓█   ▀ ▒██▀ ██▌
 ░██   █▌▒███   ▓██  ▀█ ██▒▒██▒▒███   ░██   █▌
 ░▓█▄   ▌▒▓█  ▄ ▓██▒  ▐▌██▒░██░▒▓█  ▄ ░▓█▄   ▌
 ░▒████▓ ░▒████▒▒██░   ▓██░░██░░▒████▒░▒████▓
  ▒▒▓  ▒ ░░ ▒░ ░░ ▒░   ▒ ▒ ░▓  ░░ ▒░ ░ ▒▒▓  ▒ </code>

🚫 <b>ACCESS DENIED</b> — обратись к администратору"""

_PIN_ART = """<code>
╔═══════════════════════════╗
║  🔐  BLACKBUGS SECURE     ║
║  ─────────────────────    ║
║  [ • ] [ • ] [ • ] [ • ]  ║
╚═══════════════════════════╝</code>"""

_SUCCESS_ART = """<code>
╔═══════════════════════╗
║  ██████╗ ██╗  ██╗     ║
║ ██╔═══██╗██║ ██╔╝     ║
║ ██║   ██║█████╔╝      ║
║ ██║   ██║██╔═██╗      ║
║ ╚██████╔╝██║  ██╗     ║
║  ╚═════╝ ╚═╝  ╚═╝     ║
║   ACCESS GRANTED  ✅   ║
╚═══════════════════════╝</code>"""

_SET_PIN_ART = """<code>
╔══════════════════════════╗
║  🔑  CREATE YOUR PIN     ║
║  ─────────────────────   ║
║  Минимум 4 цифры         ║
║  Только цифры: 0-9       ║
╚══════════════════════════╝</code>"""

<<<<<<< HEAD
# ─── КАПЧА v4 — чистая и понятная ─────────────────────────────────────────────

def captcha_generate(telegram_id) -> str:
    ctype = random.choice(['simple_math', 'emoji_count', 'word_reverse', 'sequence_next'])

    if ctype == 'simple_math':
        a = random.randint(2, 9)
        b = random.randint(2, 9)
        op = random.choice(['+', '-'])
        result = a + b if op == '+' else a - b
        question = (
            f"🛡 <b>Проверка входа</b>\n\n"
            f"Реши пример: <code>{a} {op} {b}</code>\n"
            f"Ответ напиши цифрами."
        )
        answer = str(result)

    elif ctype == 'emoji_count':
        target = random.choice(['🖤', '⭐', '🔥', '⚡'])
        filler = random.choice(['▫️', '▪️', '⬛'])
        count = random.randint(3, 7)
        cells = [target] * count + [filler] * (12 - count)
        random.shuffle(cells)
        rows = [' '.join(cells[i*4:(i+1)*4]) for i in range(3)]
        question = (
            f"🛡 <b>Проверка входа</b>\n\n"
            f"Сколько символов <b>{target}</b> здесь:\n\n"
            f"<code>{chr(10).join(rows)}</code>"
        )
        answer = str(count)

    elif ctype == 'word_reverse':
        word = random.choice(['CODE', 'BOTS', 'DATA', 'NOVA', 'BLACK'])
        question = (
            f"🛡 <b>Проверка входа</b>\n\n"
            f"Напиши слово наоборот: <code>{word}</code>"
        )
        answer = word[::-1]

    else:  # sequence_next
        start_n = random.randint(2, 6)
        step = random.randint(2, 4)
        seq = [start_n + step * i for i in range(4)]
        question = (
            f"🛡 <b>Проверка входа</b>\n\n"
            f"Продолжи ряд: <code>{' · '.join(map(str, seq))} · ?</code>"
        )
        answer = str(start_n + step * 4)

    _captchas[telegram_id] = {
        "answer": answer.strip().upper(),
        "expires": time.time() + CAPTCHA_TTL,
        "tries": 0,
        "type": ctype,
=======
# ─── КАПЧА v3 — киберпанк ────────────────────────────────────────────────────

def captcha_generate(telegram_id) -> str:
    ctype = random.choice(CAPTCHA_TYPES)

    if ctype == 'emoji_grid':
        # 4x4 грид эмодзи, посчитай целевой
        target = random.choice(['🖤','🐛','🔥','⚡','💀','🕵️','🦾','🤖'])
        filler = random.choice(['⬛','🟫','🟪','🟦','🟩'])
        count  = random.randint(3, 8)
        total  = 16
        cells  = [target]*count + [filler]*(total-count)
        random.shuffle(cells)
        rows   = [''.join(cells[i*4:(i+1)*4]) for i in range(4)]
        grid   = '\n'.join(rows)
        question = (
            f"🎯 <b>GRID SCAN</b>\n\n"
            f"<code>{grid}</code>\n\n"
            f"Сколько <b>{target}</b> в матрице?"
        )
        answer = str(count)

    elif ctype == 'ascii_art':
        # Угадай число по ASCII-арту
        digits_art = {
            '1': ['  █ ',' ██ ','  █ ','  █ ','████'],
            '2': ['████','   █','████','█   ','████'],
            '3': ['████','   █','████','   █','████'],
            '4': ['█  █','█  █','████','   █','   █'],
            '5': ['████','█   ','████','   █','████'],
            '6': ['████','█   ','████','█  █','████'],
            '7': ['████','   █','  █ ',' █  ',' █  '],
            '8': ['████','█  █','████','█  █','████'],
            '9': ['████','█  █','████','   █','████'],
        }
        d1, d2 = random.choice('23456789'), random.choice('23456789')
        art1, art2 = digits_art[d1], digits_art[d2]
        combined = [f"{art1[i]}  {art2[i]}" for i in range(5)]
        question = (
            f"🔢 <b>ASCII DECODE</b>\n\n"
            f"<code>{'┃' + chr(10) + '┃'.join(combined) + chr(10) + '┃'}</code>\n\n"
            f"Что за число? (введи 2 цифры)"
        )
        answer = d1 + d2

    elif ctype == 'matrix_decode':
        # Матрица символов, найди паттерн
        target = random.choice(['01','10','00','11'])
        grid_rows = []
        count = 0
        for _ in range(4):
            row = ''
            for _ in range(6):
                cell = random.choice(['01','10','00','11'])
                if cell == target:
                    count += 1
                row += cell + ' '
            grid_rows.append(row.strip())
        question = (
            f"💾 <b>MATRIX SCAN</b>\n\n"
            f"<code>{'  '.join(['COL'+str(i) for i in range(1,7)])}\n"
            f"{chr(10).join(grid_rows)}</code>\n\n"
            f"Сколько раз встречается <code>{target}</code>?"
        )
        answer = str(count)

    elif ctype == 'bit_flip':
        # XOR задача
        a = random.randint(1, 15)
        b = random.randint(1, 15)
        result = a ^ b
        a_bin = format(a, '04b')
        b_bin = format(b, '04b')
        question = (
            f"⚡ <b>BIT OPERATION</b>\n\n"
            f"<code>"
            f"  {a_bin}  ({a})\n"
            f"⊕ {b_bin}  ({b})\n"
            f"─────────\n"
            f"  ????</code>\n\n"
            f"Результат XOR в десятичном?"
        )
        answer = str(result)

    elif ctype == 'logic_gate':
        # Логический вентиль
        a, b = random.randint(0,1), random.randint(0,1)
        gate = random.choice(['AND','OR','NAND','NOR','XOR'])
        ops  = {'AND': a&b, 'OR': a|b, 'NAND': int(not(a&b)),
                'NOR': int(not(a|b)), 'XOR': a^b}
        result = ops[gate]
        question = (
            f"🔌 <b>LOGIC GATE</b>\n\n"
            f"<code>"
            f"  A={a}  B={b}\n"
            f"  ┌───────┐\n"
            f"  │  {gate:<4} │──→ ?\n"
            f"  └───────┘</code>\n\n"
            f"Выход вентиля {gate}(A,B) = ?"
        )
        answer = str(result)

    else:  # cipher_shift
        # ROT-N шифр
        shift = random.randint(1, 5)
        word  = random.choice(['CODE','HACK','BUGS','BOTS','KEYS','DATA','DARK'])
        encoded = ''.join(chr((ord(c)-65+shift)%26+65) for c in word)
        question = (
            f"🔐 <b>CIPHER DECODE</b>\n\n"
            f"<code>ROT-{shift} шифр:\n{encoded} → ?</code>\n\n"
            f"Каждая буква сдвинута на <b>{shift}</b> назад.\n"
            f"Раскодируй слово:"
        )
        answer = word

    _captchas[telegram_id] = {
        "answer":   answer.strip().upper(),
        "expires":  time.time() + CAPTCHA_TTL,
        "tries":    0,
        "type":     ctype,
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
        "question": question,
    }
    return question

<<<<<<< HEAD
=======

>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
def captcha_check(telegram_id, user_input) -> tuple:
    c = _captchas.get(telegram_id)
    if not c:
        return False, "expired"
    if time.time() > c["expires"]:
        _captchas.pop(telegram_id, None)
        return False, "expired"
    c["tries"] += 1
    if c["tries"] > 4:
        _captchas.pop(telegram_id, None)
        return False, "too_many"
    if user_input.strip().upper() == c["answer"]:
        _captchas.pop(telegram_id, None)
        return True, "ok"
    rem = 4 - c["tries"]
    return False, f"wrong:{rem}"


def captcha_refresh(telegram_id):
    _captchas.pop(telegram_id, None)
    return captcha_generate(telegram_id)


# ─── Auth flow ────────────────────────────────────────────────────────────────

from telegram_client import send_message


def auth_start(chat_id, username=None, first_name=None):
    u = get_user(chat_id)
    if not u:
        create_user(chat_id, username, first_name)
    if is_banned(chat_id):
        send_message(_BANNED_ART, chat_id)
        return

    # Если юзер уже в процессе установки/подтверждения PIN — не сбрасываем
    step, data = auth_state_get(chat_id)
    if step in ('set_pin', 'confirm_pin', 'set_pin_pad', 'confirm_pin_pad', 'reg_nick'):
        if step == 'confirm_pin' and data:
            masked = "●" * len(str(data))
            send_message(
                f"<code>PIN: {masked}</code>\n\n"
                f"🔄 Продолжай — повтори PIN для подтверждения:",
                chat_id
            )
        else:
            send_message("🔑 Продолжай — введи PIN-код:", chat_id)
        return

    # Показываем загрузочный арт
    send_message(random.choice(_BOOT_FRAMES), chat_id)
    time.sleep(0.3)
    if has_pin(chat_id):
        _ask_pin(chat_id)
    else:
        auth_send_captcha(chat_id)


def _ask_pin(chat_id):
    auth_state_set(chat_id, "enter_pin")
    _pin_attempts[chat_id] = 0
    rows = _pin_rows("", "enter_pin")
    send_message(
        f"{_PIN_ART}\n\n"
        f"🔐 <b>Введи PIN-код</b>\n\n"
        f"<code>  ⚪⚪⚪⚪  </code>\n\n"
        f"<i>Нажимай цифры</i>",
        chat_id,
        reply_markup={"inline_keyboard": rows}
    )


def _pbn(label, data=None):
    return {"text": label, "callback_data": data or f"pin_digit:{label}"}


def auth_send_captcha(chat_id):
    question = captcha_generate(chat_id)
    auth_state_set(chat_id, "captcha")
<<<<<<< HEAD
    send_message(
        f"<b>Шаг 1 из 3 · Проверка</b>\n\n"
        f"{question}\n\n"
        f"<i>Если задача неудобная — обнови её.</i>",
        chat_id,
        reply_markup={"inline_keyboard": [[
            {"text": "🔄 Обновить", "callback_data": "captcha_new"},
            {"text": "💡 Подсказка", "callback_data": "captcha_hint"},
=======
    # Прогресс-бар безопасности
    bar = "█" * random.randint(3,7) + "░" * random.randint(3,5)
    send_message(
        f"<code>[ SECURITY CHECK ]</code>\n"
        f"<code>[{bar}]</code>\n\n"
        f"🛡 <b>Докажи что не робот</b>\n\n"
        f"{question}",
        chat_id,
        reply_markup={"inline_keyboard": [[
            {"text": "🔄 Другая задача", "callback_data": "captcha_new"},
            {"text": "💡 Подсказка",     "callback_data": "captcha_hint"},
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
        ]]}
    )


def auth_handle_text(chat_id, text):
    step, data = auth_state_get(chat_id)
    if step == "idle": return
    if   step == "enter_pin":       _step_pin(chat_id, text)
    elif step == "pin_digits":      _step_pin(chat_id, data or text)
    elif step == "captcha":         _step_captcha(chat_id, text)
    elif step == "reg_nick":        _step_reg_nick(chat_id, text)
    elif step == "set_pin":         _step_set_pin(chat_id, text)
    elif step == "set_pin_pad":     _step_set_pin(chat_id, text)
    elif step == "confirm_pin":     _step_confirm_pin(chat_id, text, data)
    elif step == "confirm_pin_pad":
        _, original = auth_state_get(str(chat_id) + "_orig")
        _step_confirm_pin(chat_id, text, original or data)


def _step_pin(chat_id, pin):
    # Принимаем только цифры
    pin = re.sub(r'\D', '', pin.strip())
    if not pin:
        return
    attempts = _pin_attempts.get(chat_id, 0) + 1
    _pin_attempts[chat_id] = attempts

    if check_pin(chat_id, pin):
        _pin_attempts.pop(chat_id, None)
        auth_state_clear(chat_id)
        auth_session_set(chat_id, {"authenticated": True})
        update_last_seen(chat_id)
        u = get_user(chat_id)
        priv = u.get('privilege','user') if u else 'user'
        icon = PRIVILEGE_ICONS.get(priv,'👤')
        name = (u.get('first_name') or u.get('username') or 'Агент') if u else 'Агент'
        send_message(
            f"{_SUCCESS_ART}\n\n"
            f"{icon} Добро пожаловать, <b>{name}</b>\n"
            f"Роль: <b>{PRIVILEGE_LABELS.get(priv,priv)}</b>",
            chat_id
        )
    elif attempts >= MAX_ATTEMPTS:
        _pin_attempts.pop(chat_id, None)
        auth_state_clear(chat_id)
        send_message(
            f"{_BANNED_ART}\n\n🚫 Слишком много попыток. /start через час.",
            chat_id
        )
    else:
        rem  = MAX_ATTEMPTS - attempts
        fill = "🔴" * attempts + "⚫" * rem
        send_message(
            f"❌ <b>Неверный PIN</b>\n\n"
            f"{fill}\n"
            f"Осталось: <b>{rem}</b>",
            chat_id,
            reply_markup={"inline_keyboard": [
                [{"text": "❓ Забыл PIN", "callback_data": "pin_forgot"}]
            ]}
        )


def _step_captcha(chat_id, answer):
    ok, reason = captcha_check(chat_id, answer)
    if ok:
        send_message(
<<<<<<< HEAD
            "✅ <b>Проверка пройдена</b>\n\nТеперь выбери имя профиля.",
=======
            "<code>[ CAPTCHA ] ✅ PASSED</code>\n\n"
            "Проверка пройдена! Выбери никнейм:",
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
            chat_id
        )
        _ask_nickname(chat_id)
    elif reason == "expired":
        auth_send_captcha(chat_id)
    elif reason == "too_many":
        auth_state_clear(chat_id)
<<<<<<< HEAD
        send_message("🚫 Слишком много ошибок. Запусти /start и попробуй ещё раз.", chat_id)
    else:
        rem = reason.split(":")[1] if ":" in reason else "?"
=======
        send_message("🚫 Слишком много ошибок. /start заново.", chat_id)
    else:
        rem  = reason.split(":")[1] if ":" in reason else "?"
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
        new_q = captcha_generate(chat_id)
        auth_state_set(chat_id, "captcha")
        fails = 4 - int(rem) if rem.isdigit() else 1
        fail_bar = "🔴" * fails + "⚫" * (4 - fails)
        send_message(
<<<<<<< HEAD
            f"❌ <b>Ответ неверный</b>\n{fail_bar}\n\n"
            f"Осталось попыток: <b>{rem}</b>\n\n"
            f"Попробуй новую задачу:\n\n{new_q}",
            chat_id,
            reply_markup={"inline_keyboard": [[
                {"text": "🔄 Обновить", "callback_data": "captcha_new"},
=======
            f"<code>[ ACCESS DENIED ] ❌</code>\n"
            f"{fail_bar}\n\n"
            f"Осталось попыток: <b>{rem}</b>\n\n"
            f"🔄 <b>Новая задача:</b>\n\n{new_q}",
            chat_id,
            reply_markup={"inline_keyboard": [[
                {"text": "🔄 Другая",  "callback_data": "captcha_new"},
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
                {"text": "💡 Подсказка", "callback_data": "captcha_hint"},
            ]]}
        )


def _ask_nickname(chat_id):
    """Запрашивает никнейм после капчи."""
    auth_state_set(chat_id, "reg_nick")
    send_message(
<<<<<<< HEAD
        "<b>Шаг 2 из 3 · Никнейм</b>\n\n"
        "Придумай имя для профиля.\n\n"
        "<i>Буквы, цифры, _ и - · от 3 до 24 символов.</i>",
=======
        "👤 <b>Придумай никнейм</b>\n\n"
        "<i>• только буквы, цифры, _ и -\n"
        "• от 3 до 24 символов</i>\n\n"
        "Напиши его:",
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
        chat_id
    )


def _step_reg_nick(chat_id, text: str):
    """Сохраняет ник, потом переходит к PIN."""
    nick = text.strip()
    if not re.match(r'^[\w\-]{3,24}$', nick):
        send_message(
            "❌ Неверный формат.\n"
            "Только буквы/цифры/<code>_</code>/<code>-</code>, 3–24 символа.\n\n"
            "Попробуй снова:",
            chat_id
        )
        return
    # Уникальность
    taken = [u.get('username','').lower() for u in get_all_users() if u.get('username')]
    if nick.lower() in taken:
        send_message(f"❌ Ник <code>{nick}</code> занят. Выбери другой:", chat_id)
        return
    with _db() as c:
        c.execute('UPDATE users SET username=? WHERE telegram_id=?', (nick, int(chat_id)))
    send_message(
<<<<<<< HEAD
        f"✅ Ник <b>{nick}</b> сохранён.\n\nПереходим к защите входа.",
=======
        f"✅ Ник <b>{nick}</b> сохранён!\n\n"
        f"🔑 Теперь создай PIN-код:",
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
        chat_id
    )
    _start_set_pin(chat_id)


def _start_set_pin(chat_id):
    auth_state_set(chat_id, "set_pin_pad", None)
    rows = _pin_rows("", "set_pin_pad")
    send_message(
<<<<<<< HEAD
        "<b>Шаг 3 из 3 · PIN-код</b>\n\n"
        "Придумай PIN для быстрого входа.\n\n"
        "<code>  ⚪⚪⚪⚪  </code>\n\n"
        "<i>Минимум 4 цифры, затем нажми ✅</i>",
=======
        f"{_SET_PIN_ART}\n\n"
        f"🔑 <b>Создай PIN-код</b>\n\n"
        f"<code>  ⚪⚪⚪⚪  </code>\n\n"
        f"<i>Нажми 4+ цифры, затем ✅</i>",
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
        chat_id,
        reply_markup={"inline_keyboard": rows}
    )


def _step_set_pin(chat_id, pin):
    pin = re.sub(r'\D', '', pin.strip())
    if len(pin) < 4:
        send_message("❌ PIN должен быть минимум 4 цифры", chat_id)
        return
    # Сохраняем первый PIN ЯВНО в состояние
    auth_state_set(chat_id, "confirm_pin", pin)
    masked = "●" * len(pin)
    send_message(
<<<<<<< HEAD
        f"<b>Подтверди PIN</b>\n\n<code>{masked}</code>\n\nВведи тот же PIN ещё раз.",
=======
        f"<code>PIN: {masked}</code>\n\n"
        f"🔄 Повтори PIN для подтверждения:",
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
        chat_id
    )


def _step_confirm_pin(chat_id, pin, original):
    pin = re.sub(r'\D', '', pin.strip())

    # Защита: если original потерян — читаем заново из state
    if not original:
        _, original = auth_state_get(chat_id)

    if not original:
        # Состояние потеряно — начинаем заново
        auth_state_set(chat_id, "set_pin")
        send_message("⚠️ Состояние сброшено. Введи PIN заново:", chat_id)
        return

    if pin != str(original):
        auth_state_set(chat_id, "confirm_pin", original)
<<<<<<< HEAD
        send_message("❌ <b>PIN не совпадает</b>\n\nПовтори подтверждение ещё раз.", chat_id)
=======
        send_message("❌ <b>PIN не совпадает</b>\n\nВведи подтверждение ещё раз:", chat_id)
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
        return

    try:
        set_pin(chat_id, pin)
    except Exception as e:
        # bcrypt или DB ошибка — сохраняем PIN простым хешем как fallback
        import hashlib
        simple_hash = hashlib.sha256(pin.encode()).hexdigest()
        with _db() as c:
            c.execute('UPDATE users SET pin_hash=?, status=? WHERE telegram_id=?',
                      ("sha256:" + simple_hash, 'active', int(chat_id)))

    auth_state_clear(chat_id)
    auth_session_set(chat_id, {"authenticated": True})
    update_last_seen(chat_id)
    u = get_user(chat_id)
    priv = u.get('privilege','user') if u else 'user'
    send_message(
<<<<<<< HEAD
        "✅ <b>Регистрация завершена</b>\n\nТеперь вход будет через твой PIN-код.",
=======
        f"{_SUCCESS_ART}\n\n"
        f"✅ <b>PIN установлен!</b>\n\n"
        f"🔐 Следующий вход — только PIN.",
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
        chat_id
    )


def _step_pin_buffer(chat_id, text, buf):
    """PIN-пад: буферизуем нажатия."""
    pass  # обрабатывается через колбэки


def auth_handle_callback(chat_id, data, msg_id=None):
    from telegram_client import send_message, edit_message
    if data == "captcha_new":
        q = captcha_refresh(chat_id)
        auth_state_set(chat_id, "captcha")
<<<<<<< HEAD
        try:
            edit_message(
                chat_id, msg_id,
                f"<b>Шаг 1 из 3 · Проверка</b>\n\n{q}\n\n<i>Если задача неудобная — обнови её.</i>",
                reply_markup={"inline_keyboard": [[
                    {"text": "🔄 Обновить", "callback_data": "captcha_new"},
=======
        bar = "█" * random.randint(3,7) + "░" * random.randint(3,5)
        try:
            edit_message(chat_id, msg_id,
                f"<code>[ SECURITY CHECK ]</code>\n<code>[{bar}]</code>\n\n"
                f"🛡 <b>Новая задача:</b>\n\n{q}",
                reply_markup={"inline_keyboard": [[
                    {"text": "🔄 Другая",    "callback_data": "captcha_new"},
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
                    {"text": "💡 Подсказка", "callback_data": "captcha_hint"},
                ]]}
            )
        except Exception:
<<<<<<< HEAD
            send_message(
                f"<b>Шаг 1 из 3 · Проверка</b>\n\n{q}",
                chat_id,
                reply_markup={"inline_keyboard": [[
                    {"text": "🔄 Обновить", "callback_data": "captcha_new"},
                    {"text": "💡 Подсказка", "callback_data": "captcha_hint"},
                ]]}
            )
=======
            send_message(f"🔄 Новая задача:\n\n{q}", chat_id,
                        reply_markup={"inline_keyboard": [[
                            {"text": "🔄 Другая", "callback_data": "captcha_new"}
                        ]]})
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999

    elif data == "captcha_hint":
        c = _captchas.get(chat_id)
        if not c: return
        hints = {
<<<<<<< HEAD
            'simple_math':  "Просто реши пример",
            'emoji_count':  "Считай только указанный символ",
            'word_reverse': "Прочитай слово справа налево",
            'sequence_next': "Посмотри, какой шаг между числами",
=======
            'emoji_grid':     "Считай внимательно по строкам слева направо",
            'ascii_art':      "Смотри на форму букв — каждые 5 строк одна цифра",
            'matrix_decode':  "Ищи пары битов которые точно совпадают с паттерном",
            'bit_flip':       "XOR: 1⊕1=0, 0⊕0=0, 1⊕0=1, 0⊕1=1",
            'logic_gate':     "AND=умножение, OR=сложение, XOR=разность по модулю 2",
            'cipher_shift':   "Сдвигай каждую букву НАЗАД по алфавиту",
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
        }
        hint = hints.get(c['type'], "Думай логически!")
        send_message(f"💡 <b>Подсказка:</b>\n<i>{hint}</i>", chat_id)

    elif data == "pin_forgot":
        auth_state_clear(chat_id)
        send_message(
            "❓ <b>Забыл PIN?</b>\n\n"
            "Обратись к администратору для сброса.\n"
            "Или напиши /start — пройди капчу заново.",
            chat_id
        )

    elif data.startswith("pin_digit:"):
        digit = data.split(":")[1]
        step, buf = auth_state_get(chat_id)
        if step not in ("enter_pin", "pin_digits", "set_pin_pad", "confirm_pin_pad"):
            # Перезапускаем если состояние потеряно
            if has_pin(chat_id):
                _ask_pin(chat_id)
            return
        buf = (buf or "") + digit
        auth_state_set(chat_id, step if step != "enter_pin" else "pin_digits", buf)
        _update_pin_display(chat_id, buf, step, msg_id)

    elif data == "pin_ok":
        step, buf = auth_state_get(chat_id)
        buf = buf or ""
        if not buf:
            return
        if step in ("enter_pin", "pin_digits"):
            _step_pin(chat_id, buf)
        elif step == "set_pin_pad":
            if len(buf) < 4:
                send_message("❌ PIN минимум 4 цифры", chat_id)
                return
            # Сохраняем оригинал и просим подтверждение
            auth_state_set(str(chat_id) + "_orig", "confirm_orig", buf)
            auth_state_set(chat_id, "confirm_pin", buf)
            _ask_confirm_pin(chat_id)
        elif step == "confirm_pin_pad":
            _, original = auth_state_get(str(chat_id) + "_orig")
            _, fallback = auth_state_get(chat_id)
            _step_confirm_pin(chat_id, buf, original or fallback)

    elif data == "pin_del":
        step, buf = auth_state_get(chat_id)
        buf = buf or ""
        if buf:
            buf = buf[:-1]
            auth_state_set(chat_id, step, buf if buf else None)
            _update_pin_display(chat_id, buf, step, msg_id)

    elif data == "pin_clear":
        step, _ = auth_state_get(chat_id)
        auth_state_set(chat_id, step, None)
        _update_pin_display(chat_id, "", step, msg_id)


def _update_pin_display(chat_id, buf: str, step: str, msg_id=None):
    """Обновляет сообщение с текущим прогрессом ввода PIN."""
    from telegram_client import edit_message, send_message as _sm
    n = len(buf)
    filled   = "🔴" * n
    empty    = "⚪" * max(0, PIN_LENGTH - n)
    dots     = filled + empty

    if step in ("enter_pin", "pin_digits"):
        title = "🔐 Введи PIN-код"
        hint  = f"Введено: {n} цифр{'' if n != PIN_LENGTH else ' — нажми ✅'}"
    else:
        title = "🔑 Создай PIN"
        hint  = f"Введено: {n} цифр{'' if n != PIN_LENGTH else ' — нажми ✅'}"

    text = f"{title}\n\n<code>  {dots}  </code>\n\n<i>{hint}</i>"
    rows = _pin_rows(buf, step)
    try:
        if msg_id:
            edit_message(chat_id, msg_id, text, reply_markup={"inline_keyboard": rows})
        else:
            _sm(text, chat_id, reply_markup={"inline_keyboard": rows})
    except Exception:
        pass


def _pin_rows(buf: str, step: str) -> list:
    """Строит ряды кнопок PIN-пада."""
    digits = list("789456123")
    rows = [
        [_pbn(digits[i]), _pbn(digits[i+1]), _pbn(digits[i+2])]
        for i in range(0, 9, 3)
    ]
    rows.append([
        _pbn("⌫", "pin_del"),
        _pbn("0"),
        _pbn("✅", "pin_ok"),
    ])
    if step in ("enter_pin", "pin_digits"):
        rows.append([{"text": "❓ Забыл PIN", "callback_data": "pin_forgot"}])
    return rows


def _ask_confirm_pin(chat_id):
    """Просит подтвердить PIN."""
    from telegram_client import send_message
    auth_state_set(chat_id, "confirm_pin_pad", None)
    rows = _pin_rows("", "confirm_pin_pad")
    send_message(
        "🔁 <b>Подтверди PIN</b>\n\n"
        "<code>  ⚪⚪⚪⚪  </code>\n\n"
        "<i>Введи тот же PIN ещё раз</i>",
        chat_id,
        reply_markup={"inline_keyboard": rows}
    )


def auth_handle_pin_callback(data: str, chat_id: int) -> bool:
    """
    Совместимость с bot.py который импортирует это имя.
    Делегирует в auth_handle_callback.
    Возвращает True если аутентификация завершена.
    """
    was_auth = is_authenticated(chat_id)
    auth_handle_callback(chat_id, data)
    return (not was_auth) and is_authenticated(chat_id)
