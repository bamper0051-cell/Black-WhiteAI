import sqlite3
from datetime import datetime

DB_PATH = 'automuvie.db'

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
