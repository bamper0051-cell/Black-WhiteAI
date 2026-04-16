"""
structured_logger.py — Structured logging для АВТОМУВИ
JSON логи + last_error + healthcheck endpoint
"""
import os, sys, json, time, threading, traceback
from datetime import datetime
import config
from core.db_manager import BLACKBUGS_DB

LOG_PATH   = os.path.join(config.BASE_DIR, 'bot.log')
LOG_MAX_MB = 10

_buffer = []       # последние N записей in-memory
_buffer_max = 1000
_lock = threading.Lock()
_last_error = None
_health = {
    'started_at': time.time(),
    'last_update': time.time(),
    'errors_total': 0,
    'tasks_done': 0,
    'tasks_failed': 0,
    'llm_calls': 0,
}

LEVELS = ('DEBUG','INFO','WARN','ERROR','CRITICAL')

def log(level, component, message, user_id=None, task_id=None, extra=None):
    global _last_error
    level = level.upper()
    entry = {
        'ts':        datetime.now().isoformat(timespec='seconds'),
        'level':     level,
        'component': component,
        'msg':       str(message)[:1000],
    }
    if user_id: entry['user_id'] = str(user_id)
    if task_id: entry['task_id'] = str(task_id)
    if extra:   entry['extra'] = extra

    # Console
    icon = {'DEBUG':'🔵','INFO':'⚪','WARN':'🟡','ERROR':'🔴','CRITICAL':'💀'}.get(level,'⚪')
    print(f"{icon} [{entry['ts']}] [{component}] {message}", flush=True)

    # In-memory buffer
    with _lock:
        _buffer.append(entry)
        if len(_buffer) > _buffer_max:
            _buffer.pop(0)

    # Track errors
    if level in ('ERROR','CRITICAL'):
        _last_error = entry
        _health['errors_total'] += 1

    # File log (async write)
    threading.Thread(target=_write_log, args=(entry,), daemon=True).start()


def _write_log(entry):
    try:
        # Ротация если файл > LOG_MAX_MB
        if os.path.exists(LOG_PATH) and os.path.getsize(LOG_PATH) > LOG_MAX_MB * 1024 * 1024:
            os.rename(LOG_PATH, LOG_PATH + '.old')
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    except Exception:
        pass


def get_logs(n=100, level=None, component=None, user_id=None):
    with _lock:
        items = list(_buffer)
    if level:
        items = [x for x in items if x['level'] == level.upper()]
    if component:
        items = [x for x in items if x.get('component','').lower() == component.lower()]
    if user_id:
        items = [x for x in items if x.get('user_id') == str(user_id)]
    return items[-n:]


def get_last_error():
    return _last_error


def healthcheck():
    """Возвращает dict статуса для /health эндпоинта."""
    uptime = int(time.time() - _health['started_at'])
    h, r = divmod(uptime, 3600); m, s = divmod(r, 60)

    # Проверяем БД
    db_ok = True
    try:
        import sqlite3
        with sqlite3.connect(str(BLACKBUGS_DB)) as c:
            c.execute('SELECT 1')
    except Exception:
        db_ok = False

    # LLM ping (быстрый)
    llm_ok = True
    try:
        from llm_client import test_connection
        ok, _ = test_connection()
        llm_ok = ok
    except Exception:
        llm_ok = False

    return {
        'status':       'ok' if db_ok else 'degraded',
        'uptime':       f'{h}h{m}m{s}s',
        'uptime_sec':   uptime,
        'db':           'ok' if db_ok else 'error',
        'llm':          'ok' if llm_ok else 'error',
        'errors_total': _health['errors_total'],
        'last_error':   _last_error,
        'tasks_done':   _health['tasks_done'],
        'tasks_failed': _health['tasks_failed'],
        'llm_calls':    _health['llm_calls'],
        'log_buffer':   len(_buffer),
    }


def inc(key):
    if key in _health:
        _health[key] += 1
    _health['last_update'] = time.time()


# Удобные алиасы
def debug(comp, msg, **kw):    log('DEBUG',    comp, msg, **kw)
def info(comp, msg, **kw):     log('INFO',     comp, msg, **kw)
def warn(comp, msg, **kw):     log('WARN',     comp, msg, **kw)
def error(comp, msg, **kw):    log('ERROR',    comp, msg, **kw)
def critical(comp, msg, **kw): log('CRITICAL', comp, msg, **kw)


class ComponentLogger:
    """Logger привязанный к компоненту."""
    def __init__(self, name):
        self.name = name
    def debug(self, msg, **kw):    debug(self.name, msg, **kw)
    def info(self, msg, **kw):     info(self.name, msg, **kw)
    def warn(self, msg, **kw):     warn(self.name, msg, **kw)
    def error(self, msg, **kw):    error(self.name, msg, **kw)
    def critical(self, msg, **kw): critical(self.name, msg, **kw)
