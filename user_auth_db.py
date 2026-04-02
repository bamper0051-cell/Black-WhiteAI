"""
user_auth_db.py — Модуль работы с базой данных пользователей (регистрация/авторизация).
Хеширование паролей через bcrypt. SQLite хранилище.
"""
import sqlite3
import os
import time

try:
    import bcrypt
    _USE_BCRYPT = True
except ImportError:
    import hashlib
    _USE_BCRYPT = False

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users_auth.db")

def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_auth_db():
    """Создаёт таблицу users если не существует."""
    conn = _get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS web_users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            username    TEXT    UNIQUE NOT NULL,
            password_hash TEXT  NOT NULL,
            created_at  REAL   NOT NULL,
            last_login  REAL
        )
    """)
    conn.commit()
    conn.close()
    print("  ✅ Auth DB initialized:", DB_PATH, flush=True)

def _hash_password(password: str) -> str:
    if _USE_BCRYPT:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    else:
        salt = os.urandom(16).hex()
        h = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
        return f"{salt}${h}"

def _verify_password(password: str, password_hash: str) -> bool:
    if _USE_BCRYPT:
        try:
            return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
        except Exception:
            return False
    else:
        if "$" not in password_hash:
            return False
        salt, h = password_hash.split("$", 1)
        return hashlib.sha256((salt + password).encode("utf-8")).hexdigest() == h

def register_user(username: str, password: str) -> dict:
    """Регистрация нового пользователя. Возвращает dict с результатом."""
    username = username.strip()
    if len(username) < 3:
        return {"ok": False, "error": "Логин должен быть не менее 3 символов"}
    if len(password) < 6:
        return {"ok": False, "error": "Пароль должен быть не менее 6 символов"}

    password_hash = _hash_password(password)

    try:
        conn = _get_conn()
        conn.execute(
            "INSERT INTO web_users (username, password_hash, created_at) VALUES (?, ?, ?)",
            (username, password_hash, time.time()),
        )
        conn.commit()
        conn.close()
        return {"ok": True}
    except sqlite3.IntegrityError:
        return {"ok": False, "error": "Пользователь с таким логином уже существует"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def verify_user(username: str, password: str) -> dict:
    """Проверка логина и пароля."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT * FROM web_users WHERE username = ?", (username,)
    ).fetchone()
    conn.close()

    if not row:
        return {"ok": False, "error": "Неверный логин или пароль"}

    if not _verify_password(password, row["password_hash"]):
        return {"ok": False, "error": "Неверный логин или пароль"}

    # Обновляем last_login
    conn = _get_conn()
    conn.execute(
        "UPDATE web_users SET last_login = ? WHERE id = ?",
        (time.time(), row["id"]),
    )
    conn.commit()
    conn.close()

    return {"ok": True, "user_id": row["id"], "username": row["username"]}

def get_all_web_users() -> list:
    """Список всех зарегистрированных пользователей."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT id, username, created_at, last_login FROM web_users ORDER BY id"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# Автоинициализация при импорте
init_auth_db()