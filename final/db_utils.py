import sqlite3
from pathlib import Path

DB_PATH = Path("data/telegram.db")

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS entities
                     (id INTEGER PRIMARY KEY, type TEXT, entity_id TEXT, data TEXT)''')
