import sqlite3
from datetime import datetime

DB_PATH = 'automuvie.db'
def init_users_table():
    with sqlite3.connect(DB_PATH) as db:
        db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                registered_at TEXT,
                llm_provider TEXT DEFAULT 'openai',
                llm_model TEXT DEFAULT 'gpt-4o-mini',
                tts_provider TEXT DEFAULT 'edge',
                tts_voice TEXT DEFAULT 'ru-RU-DmitryNeural',
                rewrite_style TEXT DEFAULT 'troll',
                created_at TEXT
            )
        ''')
        db.commit()

def get_or_create_user(chat_id, username='', first_name='', last_name=''):
    with sqlite3.connect(DB_PATH) as db:
        cur = db.execute('SELECT * FROM users WHERE user_id = ?', (chat_id,))
        row = cur.fetchone()
        if row:
            return dict(zip([col[0] for col in cur.description], row))
        else:
            now = datetime.now().isoformat()
            db.execute('''
                INSERT INTO users 
                (user_id, username, first_name, last_name, registered_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (chat_id, username, first_name, last_name, now, now))
            db.commit()
            return get_or_create_user(chat_id)  # рекурсивный вызов

def get_user_setting(user_id, key):
    with sqlite3.connect(DB_PATH) as db:
        cur = db.execute(f'SELECT {key} FROM users WHERE user_id = ?', (user_id,))
        row = cur.fetchone()
        if row:
            return row[0]
        return None  # fallback на глобальные настройки будет в вызывающем коде

def set_user_setting(user_id, key, value):
    with sqlite3.connect(DB_PATH) as db:
        db.execute(f'UPDATE users SET {key} = ? WHERE user_id = ?', (value, user_id))
        db.commit()
def init_db():
    with sqlite3.connect(DB_PATH) as db:
        db.execute('''CREATE TABLE IF NOT EXISTS news (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            source     TEXT,
            title      TEXT,
            url        TEXT UNIQUE,
            content    TEXT,
            rewritten  TEXT,
            mp3_path   TEXT,
            sent       INTEGER DEFAULT 0,
            created_at TEXT
        )''')
        db.commit()
        
        db.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER UNIQUE,
        username TEXT,
        registered_at TEXT,
        role TEXT DEFAULT 'user',
        settings TEXT   -- JSON с настройками (язык, голос, LLM и т.п.)
    )''')

def save_news(source, title, url, content) -> bool:
    try:
        with sqlite3.connect(DB_PATH) as db:
            cur = db.execute(
                'INSERT OR IGNORE INTO news (source,title,url,content,created_at) VALUES (?,?,?,?,?)',
                (source, title, url, content, datetime.now().isoformat())
            )
            db.commit()
            return cur.rowcount > 0
    except Exception as e:
        print(f"  ❌ DB: {e}")
        return False

def get_unprocessed():
    with sqlite3.connect(DB_PATH) as db:
        return db.execute(
            'SELECT id,source,title,url,content FROM news WHERE sent=0 AND rewritten IS NULL'
        ).fetchall()

def update_news(news_id, *, rewritten=None, mp3_path=None, sent=None):
    with sqlite3.connect(DB_PATH) as db:
        if rewritten  is not None: db.execute('UPDATE news SET rewritten=?  WHERE id=?', (rewritten,  news_id))
        if mp3_path   is not None: db.execute('UPDATE news SET mp3_path=?   WHERE id=?', (mp3_path,   news_id))
        if sent       is not None: db.execute('UPDATE news SET sent=?        WHERE id=?', (sent,       news_id))
        db.commit()

def get_stats():
    with sqlite3.connect(DB_PATH) as db:
        total, sent = db.execute('SELECT COUNT(*), COALESCE(SUM(sent),0) FROM news').fetchone()
    return total, sent

def get_today_count():
    today = datetime.now().strftime('%Y-%m-%d')
    with sqlite3.connect(DB_PATH) as db:
        (n,) = db.execute(
            "SELECT COUNT(*) FROM news WHERE created_at LIKE ?", (f'{today}%',)
        ).fetchone()
    return n
