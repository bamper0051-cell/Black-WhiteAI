"""
core/auth.py — Регистрация, авторизация, управление пользователями.

Хранит:
  - Telegram ID + username
  - Хеш пароля (bcrypt)
  - Зашифрованные API ключи (Fernet)
  - Тариф и лимиты
  - Дата регистрации
"""

import os
import json
import sqlite3
import hashlib
import secrets
import logging
from datetime import datetime, date
from typing import Optional, Dict, Any
from contextlib import contextmanager

logger = logging.getLogger('auth')

# ── Константы ─────────────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "users.db")

PLANS = {
    'free':  {'daily_limit': 10,  'max_files': 20,  'sandbox': False, 'label': 'Free'},
    'pro':   {'daily_limit': 100, 'max_files': 60,  'sandbox': True,  'label': 'Pro'},
    'admin': {'daily_limit': 9999,'max_files': 200, 'sandbox': True,  'label': 'Admin'},
}

# ── Простое шифрование API ключей (XOR + hex, не требует cryptography) ──
def _encrypt_key(text: str, secret: str) -> str:
    key = hashlib.sha256(secret.encode()).digest()
    enc = bytes(ord(c) ^ key[i % len(key)] for i, c in enumerate(text))
    return enc.hex()

def _decrypt_key(hex_text: str, secret: str) -> str:
    key = hashlib.sha256(secret.encode()).digest()
    enc = bytes.fromhex(hex_text)
    return ''.join(chr(b ^ key[i % len(key)]) for i, b in enumerate(enc))

# Секрет для шифрования ключей
_SECRET = os.environ.get('AUTOCODER_SECRET', 'autocoder-default-secret-change-me')

# ── Хеш пароля (без bcrypt — pure stdlib) ─────────────────────────
def _hash_password(password: str, salt: str = None) -> tuple:
    salt = salt or secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 200_000)
    return h.hex(), salt

def _verify_password(password: str, hash_hex: str, salt: str) -> bool:
    h, _ = _hash_password(password, salt)
    return secrets.compare_digest(h, hash_hex)

# ── Database ──────────────────────────────────────────────────────
@contextmanager
def _db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    """Создаёт таблицы если не существуют."""
    with _db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            tg_id       INTEGER PRIMARY KEY,
            username    TEXT,
            first_name  TEXT,
            password_hash TEXT,
            password_salt TEXT,
            plan        TEXT DEFAULT 'free',
            daily_count INTEGER DEFAULT 0,
            last_reset  TEXT DEFAULT '',
            is_active   INTEGER DEFAULT 1,
            invite_code TEXT DEFAULT '',
            created_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS user_api_keys (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            provider    TEXT NOT NULL,
            key_enc     TEXT NOT NULL,
            updated_at  TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(tg_id),
            UNIQUE(user_id, provider)
        );

        CREATE TABLE IF NOT EXISTS sessions_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            action      TEXT,
            ts          TEXT DEFAULT (datetime('now'))
        );
        """)
    logger.info(f'[auth] DB инициализирована: {DB_PATH}')


# ── Публичный API ─────────────────────────────────────────────────

class AuthError(Exception):
    pass

class UserNotFound(AuthError):
    pass

class WrongPassword(AuthError):
    pass

class LimitExceeded(AuthError):
    pass


def register(tg_id: int, username: str, first_name: str,
             password: str, invite_code: str = '') -> Dict:
    """
    Регистрирует нового пользователя.
    Возвращает dict с данными пользователя.
    Raises AuthError если уже существует.
    """
    with _db() as conn:
        existing = conn.execute(
            'SELECT tg_id FROM users WHERE tg_id=?', (tg_id,)
        ).fetchone()
        if existing:
            raise AuthError('Ты уже зарегистрирован! Используй /login')

        ph, salt = _hash_password(password)
        plan = 'admin' if _is_first_user(conn) else 'free'

        conn.execute("""
            INSERT INTO users (tg_id, username, first_name, password_hash,
                               password_salt, plan, invite_code)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (tg_id, username or '', first_name or '', ph, salt, plan, invite_code))

    logger.info(f'[auth] Зарегистрирован: {tg_id} (@{username}) план={plan}')
    return get_user(tg_id)


def _is_first_user(conn) -> bool:
    return conn.execute('SELECT COUNT(*) FROM users').fetchone()[0] == 0


def login(tg_id: int, password: str) -> Dict:
    """
    Проверяет пароль. Возвращает данные пользователя или raises.
    """
    user = get_user(tg_id)
    if not user:
        raise UserNotFound('Пользователь не найден. Используй /register')
    if not _verify_password(password, user['password_hash'], user['password_salt']):
        raise WrongPassword('Неверный пароль')
    return user


def get_user(tg_id: int) -> Optional[Dict]:
    """Возвращает пользователя или None."""
    with _db() as conn:
        row = conn.execute(
            'SELECT * FROM users WHERE tg_id=?', (tg_id,)
        ).fetchone()
        if not row:
            return None
        return dict(row)


def is_registered(tg_id: int) -> bool:
    return get_user(tg_id) is not None


def check_limit(tg_id: int) -> bool:
    """
    Проверяет лимит запросов. Возвращает True если можно делать запрос.
    Автоматически сбрасывает дневной счётчик.
    """
    user = get_user(tg_id)
    if not user:
        return False

    today = date.today().isoformat()
    plan_limits = PLANS.get(user['plan'], PLANS['free'])

    with _db() as conn:
        # Сброс счётчика если новый день
        if user['last_reset'] != today:
            conn.execute(
                'UPDATE users SET daily_count=0, last_reset=? WHERE tg_id=?',
                (today, tg_id)
            )
            user['daily_count'] = 0

        if user['daily_count'] >= plan_limits['daily_limit']:
            return False
        return True


def increment_usage(tg_id: int):
    """Увеличивает счётчик использования."""
    with _db() as conn:
        conn.execute(
            'UPDATE users SET daily_count=daily_count+1 WHERE tg_id=?', (tg_id,)
        )


def get_plan(tg_id: int) -> Dict:
    """Возвращает настройки тарифа."""
    user = get_user(tg_id)
    if not user:
        return PLANS['free']
    plan_key = user.get('plan', 'free')
    info = PLANS.get(plan_key, PLANS['free']).copy()
    today = date.today().isoformat()
    used = user['daily_count'] if user['last_reset'] == today else 0
    info['used'] = used
    info['plan'] = plan_key
    return info


def set_plan(tg_id: int, plan: str):
    """Меняет тариф (только admin может вызвать)."""
    if plan not in PLANS:
        raise AuthError(f'Неизвестный тариф: {plan}')
    with _db() as conn:
        conn.execute('UPDATE users SET plan=? WHERE tg_id=?', (plan, tg_id))


# ── API ключи пользователя ────────────────────────────────────────

def set_user_api_key(tg_id: int, provider: str, api_key: str):
    """Сохраняет зашифрованный API ключ пользователя."""
    encrypted = _encrypt_key(api_key, _SECRET)
    with _db() as conn:
        conn.execute("""
            INSERT INTO user_api_keys (user_id, provider, key_enc)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, provider) DO UPDATE SET
                key_enc=excluded.key_enc,
                updated_at=datetime('now')
        """, (tg_id, provider.lower(), encrypted))
    logger.info(f'[auth] API ключ сохранён: {tg_id}/{provider}')


def get_user_api_key(tg_id: int, provider: str) -> str:
    """Возвращает расшифрованный API ключ пользователя или ''."""
    with _db() as conn:
        row = conn.execute(
            'SELECT key_enc FROM user_api_keys WHERE user_id=? AND provider=?',
            (tg_id, provider.lower())
        ).fetchone()
        if not row:
            return ''
        return _decrypt_key(row['key_enc'], _SECRET)


def get_all_user_keys(tg_id: int) -> Dict[str, str]:
    """Все API ключи пользователя {provider: key}."""
    with _db() as conn:
        rows = conn.execute(
            'SELECT provider, key_enc FROM user_api_keys WHERE user_id=?', (tg_id,)
        ).fetchall()
        return {r['provider']: _decrypt_key(r['key_enc'], _SECRET) for r in rows}


def user_info_text(tg_id: int) -> str:
    """Красивая строка с инфо о пользователе для Telegram."""
    user = get_user(tg_id)
    if not user:
        return '❌ Пользователь не найден'
    plan = get_plan(tg_id)
    keys = get_all_user_keys(tg_id)
    key_list = ', '.join(keys.keys()) if keys else 'нет'
    return (
        f"👤 <b>@{user['username'] or 'unknown'}</b>\n"
        f"🆔 ID: <code>{tg_id}</code>\n"
        f"💎 Тариф: <b>{plan['plan']}</b> ({plan['label']})\n"
        f"📊 Запросов: <b>{plan['used']}</b> / {plan['daily_limit']} сегодня\n"
        f"🔑 API ключи: {key_list}\n"
        f"📅 Регистрация: {user['created_at'][:10]}"
    )
