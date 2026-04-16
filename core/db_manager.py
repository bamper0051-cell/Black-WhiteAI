"""
core/db_manager.py — Unified Database Path Registry
=====================================================
Единая точка истины для всех путей к SQLite базам данных.

Все БД хранятся в DATA_DIR (/app/data в Docker, ./data локально).
Это позволяет монтировать один volume и не терять данные при rebuild.

Пути:
  BLACKBUGS_DB  — основная БД (пользователи, auth, сессии)
  TASKS_DB      — очередь задач (core/queue_manager.py)
  BRAIN_DB      — обратная связь и рефлексия агентов (agent_brain.py)
  MEMORY_DB     — долгосрочная память агентов (agent_memory.py)
  TOOLS_DB      — registry инструментов агентов (neo/matrix)
  NEWS_DB       — новости/контент (database.py legacy)

МИГРАЦИЯ:
  Старые пути (automuvie.db, auth.db в корне) → data/*.db
  entrypoint.sh копирует старые файлы при первом запуске.
"""
from __future__ import annotations

import os
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

import config

# ── Canonical DB paths (все в DATA_DIR) ──────────────────────────────────────

DATA_DIR = Path(config.DATA_DIR)
DATA_DIR.mkdir(parents=True, exist_ok=True)

BLACKBUGS_DB = DATA_DIR / "blackbugs.db"   # users + auth + sessions
TASKS_DB     = DATA_DIR / "tasks.db"       # task queue
BRAIN_DB     = DATA_DIR / "agent_brain.db" # reflexion + feedback
MEMORY_DB    = DATA_DIR / "memory.db"      # agent long-term memory
TOOLS_DB     = DATA_DIR / "tools.db"       # tool registry
NEWS_DB      = DATA_DIR / "news.db"        # news/content (legacy database.py)

# ── Legacy path aliases (для обратной совместимости) ─────────────────────────
# Модули постепенно переходят на canonical paths выше.
# Не используй эти пути в новом коде.
_LEGACY_PATHS = {
    "automuvie.db": NEWS_DB,
    "auth.db":      BLACKBUGS_DB,
    "tasks.db":     TASKS_DB,
}

# ── Thread-local connection cache ─────────────────────────────────────────────
_local = threading.local()


def get_conn(db_path: Path, *, check_same_thread: bool = False,
             timeout: float = 10.0) -> sqlite3.Connection:
    """
    Возвращает соединение с БД.
    check_same_thread=False нужен для Flask/async использования.
    """
    conn = sqlite3.connect(
        str(db_path),
        check_same_thread=check_same_thread,
        timeout=timeout,
    )
    conn.row_factory = sqlite3.Row   # доступ по имени колонки
    conn.execute("PRAGMA journal_mode=WAL")   # лучше для concurrent reads
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def db_conn(db_path: Path, **kwargs) -> Generator[sqlite3.Connection, None, None]:
    """Context manager — автоматически коммитит и закрывает."""
    conn = get_conn(db_path, **kwargs)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ── Migration helper ──────────────────────────────────────────────────────────

def migrate_legacy_files():
    """
    Переносит старые БД-файлы из корня проекта в DATA_DIR.
    Вызывается один раз при старте (entrypoint.sh или bot.py).

    Стратегия:
    - automuvie.db → NEWS_DB   (copy if target missing)
    - auth.db      → BLACKBUGS_DB (copy if target missing, else merge tables)
    - web_users.db → BLACKBUGS_DB (merge web_users rows if target already exists)
    """
    import shutil
    import sqlite3 as _sq
    base = Path(config.BASE_DIR)
    moved = []

    # ── Simple copy migrations (copy only if target does not exist) ──────────
    simple = [
        (base / "automuvie.db", NEWS_DB),
        (base / "auth.db",      BLACKBUGS_DB),
    ]
    for src, dst in simple:
        if not src.exists():
            continue
        if dst.exists():
            print(f"  ⚠️  db_manager: {src.name} → {dst.name} skipped (target exists)")
            continue
        try:
            shutil.copy2(str(src), str(dst))
            moved.append(f"{src.name} → {dst.name}")
            print(f"  ✅ db_manager: migrated {src.name} → {dst}")
        except Exception as e:
            print(f"  ❌ db_manager: failed to migrate {src.name}: {e}")

    # ── web_users.db → merge rows into blackbugs.db even if target exists ────
    # This prevents account loss when auth.db was migrated first.
    web_src = base / "web_users.db"
    if web_src.exists():
        try:
            src_conn = _sq.connect(str(web_src))
            rows = src_conn.execute(
                "SELECT id, username, pw_hash, role, token, created "
                "FROM web_users"
            ).fetchall()
            src_conn.close()

            if rows:
                dst_conn = _sq.connect(str(BLACKBUGS_DB))
                # Ensure table exists in destination
                dst_conn.execute("""CREATE TABLE IF NOT EXISTS web_users (
                    id       INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    pw_hash  TEXT NOT NULL,
                    role     TEXT DEFAULT 'user',
                    token    TEXT,
                    created  TEXT
                )""")
                inserted = 0
                for row in rows:
                    try:
                        dst_conn.execute(
                            "INSERT OR IGNORE INTO web_users "
                            "(username, pw_hash, role, token, created) "
                            "VALUES (?,?,?,?,?)",
                            (row[1], row[2], row[3], row[4], row[5])
                        )
                        inserted += 1
                    except Exception:
                        pass
                dst_conn.commit()
                dst_conn.close()
                print(f"  ✅ db_manager: merged {inserted} web_users rows from web_users.db")
            moved.append(f"web_users.db → {BLACKBUGS_DB.name} (merge)")
        except Exception as e:
            print(f"  ⚠️  db_manager: web_users.db merge skipped: {e}")

    if moved:
        print(f"  📦 db_manager: migration done ({len(moved)} operation(s))")

    return moved


# ── Schema init ───────────────────────────────────────────────────────────────

def init_all():
    """Инициализирует все схемы. Вызывается при старте один раз."""
    _init_blackbugs_db()
    _init_tasks_db()
    _init_brain_db()
    print("  ✅ db_manager: all schemas initialised")


def _init_blackbugs_db():
    """Основная БД: пользователи, сессии, web_auth."""
    with db_conn(BLACKBUGS_DB) as c:
        c.executescript("""
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

            CREATE TABLE IF NOT EXISTS sessions (
                session_id  TEXT PRIMARY KEY,
                telegram_id INTEGER,
                created_at  REAL,
                expires_at  REAL,
                device_hash TEXT,
                FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
            );

            CREATE TABLE IF NOT EXISTS web_auth (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                username    TEXT UNIQUE,
                pass_hash   TEXT,
                role        TEXT DEFAULT 'admin',
                created_at  REAL
            );

            CREATE INDEX IF NOT EXISTS idx_users_status   ON users(status);
            CREATE INDEX IF NOT EXISTS idx_sessions_tid   ON sessions(telegram_id);
        """)


def _init_tasks_db():
    """Очередь задач — совместима с core/queue_manager.py."""
    with db_conn(TASKS_DB) as c:
        c.executescript("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id     TEXT PRIMARY KEY,
                chat_id     INTEGER,
                text        TEXT,
                agent       TEXT,
                mode        TEXT,
                priority    INTEGER,
                status      TEXT,
                created_at  REAL,
                started_at  REAL,
                finished_at REAL,
                result      TEXT,
                error       TEXT,
                retries     INTEGER DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
            CREATE INDEX IF NOT EXISTS idx_tasks_chat   ON tasks(chat_id);
        """)


def _init_brain_db():
    """Обратная связь и рефлексия агентов — совместима с agent_brain.py."""
    with db_conn(BRAIN_DB) as c:
        c.executescript("""
            CREATE TABLE IF NOT EXISTS feedback (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                ts        REAL,
                chat_id   TEXT,
                agent     TEXT,
                task      TEXT,
                answer    TEXT,
                score     INTEGER,
                comment   TEXT
            );
            CREATE TABLE IF NOT EXISTS reflexion_log (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                ts        REAL,
                agent     TEXT,
                task      TEXT,
                attempt   INTEGER,
                critique  TEXT,
                improved  INTEGER
            );
            CREATE TABLE IF NOT EXISTS agent_graph_runs (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                ts        REAL,
                agent     TEXT,
                chat_id   TEXT,
                task      TEXT,
                nodes     TEXT,
                final_ok  INTEGER
            );
        """)
