"""
admin_web.py — REST API + Web Panel для АВТОМУВИ
Порт: ADMIN_WEB_PORT (default 8080)
Auth: X-Admin-Token header или ?token=...
"""
import os, sys, json, time, threading, subprocess, platform
from datetime import datetime
from functools import wraps
from flask import Flask, request, jsonify, send_file

import config

ADMIN_WEB_PORT  = int(os.environ.get('ADMIN_WEB_PORT', 8080))
ADMIN_WEB_TOKEN = os.environ.get('ADMIN_WEB_TOKEN', 'changeme_secret_token')
BASE = config.BASE_DIR

app = Flask(__name__)
app.config['JSON_ENSURE_ASCII'] = False

# ── Log capture (перехватываем print → in-memory буфер) ───────────────────────
_log_buffer = []
_LOG_MAX = 500

class _LogCapture:
    def __init__(self, orig):
        self._orig = orig
    def write(self, text):
        if text.strip():
            _log_buffer.append({
                'ts':   datetime.now().strftime('%H:%M:%S'),
                'text': text.rstrip()[:500],
                'level': 'ERROR' if 'error' in text.lower() or '❌' in text else
                         'WARN'  if 'warn'  in text.lower() or '⚠️' in text else 'INFO',
            })
            if len(_log_buffer) > _LOG_MAX:
                _log_buffer.pop(0)
        self._orig.write(text)
    def flush(self):   self._orig.flush()
    def fileno(self):  return self._orig.fileno()
    def isatty(self):  return False

def install_log_capture():
    sys.stdout = _LogCapture(sys.stdout)
    sys.stderr = _LogCapture(sys.stderr)

# ── Auth ──────────────────────────────────────────────────────────────────────
def require_token(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = (request.headers.get('X-Admin-Token') or
                 request.args.get('token') or
                 (request.get_json(silent=True) or {}).get('token', ''))
        if token != ADMIN_WEB_TOKEN:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return wrapper

# ── CORS ──────────────────────────────────────────────────────────────────────
@app.after_request
def add_cors(resp):
    resp.headers['Access-Control-Allow-Origin']  = '*'
    resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-Admin-Token'
    resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, DELETE, OPTIONS'
    return resp

@app.route('/', defaults={'path': ''}, methods=['OPTIONS'])
@app.route('/<path:path>', methods=['OPTIONS'])
def options_handler(path=''):
    return '', 204

# ── Web Auth (логин/пароль для мобильного приложения) ────────────────────────
import sqlite3 as _sqlite3, hashlib as _hashlib, secrets as _secrets

_WEB_AUTH_DB = os.path.join(BASE, 'web_users.db')

def _init_web_auth():
    with _sqlite3.connect(_WEB_AUTH_DB) as c:
        c.execute('''CREATE TABLE IF NOT EXISTS web_users (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            pw_hash  TEXT NOT NULL,
            role     TEXT DEFAULT 'user',
            token    TEXT,
            created  TEXT
        )''')
        # Создаём admin-аккаунт из ADMIN_WEB_TOKEN если не существует
        existing = c.execute("SELECT id FROM web_users WHERE username='admin'").fetchone()
        if not existing:
            ph = _hashlib.sha256(ADMIN_WEB_TOKEN.encode()).hexdigest()
            c.execute("INSERT INTO web_users (username,pw_hash,role,created) VALUES (?,?,?,?)",
                      ('admin', ph, 'admin', datetime.now().isoformat()))

_init_web_auth()

def _pw_hash(pw: str) -> str:
    return _hashlib.sha256(pw.encode()).hexdigest()

@app.route('/api/auth/register', methods=['POST'])
def api_register():
    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    if not username or not password:
        return jsonify({'error': 'username and password required'}), 400
    if len(username) < 3:
        return jsonify({'error': 'username too short (min 3)'}), 400
    if len(password) < 6:
        return jsonify({'error': 'password too short (min 6)'}), 400
    token = _secrets.token_hex(24)
    try:
        with _sqlite3.connect(_WEB_AUTH_DB) as c:
            c.execute("INSERT INTO web_users (username,pw_hash,role,token,created) VALUES (?,?,?,?,?)",
                      (username, _pw_hash(password), 'user', token, datetime.now().isoformat()))
        return jsonify({'ok': True, 'username': username, 'token': token, 'role': 'user'}), 201
    except _sqlite3.IntegrityError:
        return jsonify({'error': 'username already taken'}), 409

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    if not username or not password:
        return jsonify({'error': 'username and password required'}), 400
    with _sqlite3.connect(_WEB_AUTH_DB) as c:
        c.row_factory = _sqlite3.Row
        row = c.execute("SELECT * FROM web_users WHERE username=?", (username,)).fetchone()
    if not row or row['pw_hash'] != _pw_hash(password):
        return jsonify({'error': 'Invalid credentials'}), 401
    # Выдаём токен (admin получает ADMIN_WEB_TOKEN, обычные — свой)
    api_token = ADMIN_WEB_TOKEN if row['role'] == 'admin' else row['token']
    if not api_token:
        api_token = _secrets.token_hex(24)
        with _sqlite3.connect(_WEB_AUTH_DB) as c:
            c.execute("UPDATE web_users SET token=? WHERE username=?", (api_token, username))
    return jsonify({'ok': True, 'username': username, 'role': row['role'], 'token': api_token}), 200

@app.route('/api/auth/me')
@require_token
def api_auth_me():
    return jsonify({'ok': True, 'token_valid': True, 'server_version': '1.0'}), 200

# ── Health (без токена — для Docker healthcheck) ───────────────────────────────
@app.route('/ping')
def ping():
    """Самый простой эндпоинт — без токена, без зависимостей."""
    return jsonify({'ok': True, 'pong': True, 'port': ADMIN_WEB_PORT}), 200

@app.route('/health')
@app.route('/healthz')
def health():
    try:
        uptime = int(time.time() - _start_time)
        h, r = divmod(uptime, 3600); m, s = divmod(r, 60)
        import sqlite3
        db_ok = True
        try:
            with sqlite3.connect(os.path.join(BASE, 'auth.db')) as c:
                c.execute('SELECT 1')
        except Exception:
            db_ok = False
        return jsonify({
            'status': 'ok' if db_ok else 'degraded',
            'uptime': f'{h}h{m}m{s}s',
            'db': 'ok' if db_ok else 'error',
        }), 200 if db_ok else 503
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 503

@app.route('/readyz')
def readyz():
    """Kubernetes readiness probe — passes once DB is reachable."""
    import sqlite3
    try:
        with sqlite3.connect(os.path.join(BASE, 'auth.db')) as c:
            c.execute('SELECT 1')
        return jsonify({'ready': True}), 200
    except Exception as e:
        return jsonify({'ready': False, 'error': str(e)}), 503

# ── Status ────────────────────────────────────────────────────────────────────
@app.route('/api/status')
@require_token
def api_status():
    try:
        import bot as _bot
        uptime = int(time.time() - _bot._BOT_START_TIME)
    except Exception:
        uptime = int(time.time() - _start_time)

    try:
        import fish_bot_state as _fbs
        tunnel   = _fbs.tunnel_url or _fbs.bore_url or _fbs.ngrok_url or _fbs.serveo_url
        flask_ok = _fbs.server_running
    except Exception:
        tunnel, flask_ok = None, False

    try:
        from auth_module import get_all_users
        users        = get_all_users()
        active_count = sum(1 for u in users if u.get('status') == 'active')
    except Exception:
        users, active_count = [], 0

    try:
        from chat_agent import all_active_sessions
        sessions = len(all_active_sessions())
    except Exception:
        sessions = 0

    # Queue stats
    queue = {}
    try:
        from task_queue import queue_stats
        queue = queue_stats()
    except Exception:
        pass

    h, r = divmod(uptime, 3600); m, s2 = divmod(r, 60)
    return jsonify({
        'ok': True,
        'version': 'v4.4',
        'uptime_sec': uptime,
        'uptime_str': f'{h}ч {m}м {s2}с',
        'llm_provider': config.LLM_PROVIDER,
        'llm_model':    config.LLM_MODEL,
        'tts_provider': config.TTS_PROVIDER,
        'tts_voice':    config.TTS_VOICE,
        'flask_running': flask_ok,
        'tunnel_url':   tunnel,
        'users_total':  len(users),
        'users_active': active_count,
        'active_sessions': sessions,
        'platform':     platform.system(),
        'queue':        queue,
    })

# ── Users ─────────────────────────────────────────────────────────────────────
@app.route('/api/users')
@require_token
def api_users():
    from auth_module import get_all_users
    users = get_all_users()
    return jsonify({'ok': True, 'users': users, 'total': len(users)})

@app.route('/api/users/<int:uid>/priv', methods=['POST'])
@require_token
def api_user_priv(uid):
    data = request.get_json(silent=True) or {}
    from auth_module import set_privilege
    ok = set_privilege(uid, data.get('privilege', 'user'))
    return jsonify({'ok': ok})

@app.route('/api/users/<int:uid>/ban', methods=['POST'])
@require_token
def api_user_ban(uid):
    from admin_module import ban_user
    ban_user(uid)
    return jsonify({'ok': True})

@app.route('/api/users/<int:uid>/unban', methods=['POST'])
@require_token
def api_user_unban(uid):
    from admin_module import unban_user
    unban_user(uid)
    return jsonify({'ok': True})

@app.route('/api/users/<int:uid>/kick', methods=['POST'])
@require_token
def api_user_kick(uid):
    from auth_module import auth_session_delete
    auth_session_delete(uid)
    return jsonify({'ok': True})

@app.route('/api/users/<int:uid>', methods=['DELETE'])
@require_token
def api_user_delete(uid):
    from admin_module import delete_user
    delete_user(uid)
    return jsonify({'ok': True})

# ── Messages ──────────────────────────────────────────────────────────────────
@app.route('/api/msg/user', methods=['POST'])
@require_token
def api_msg_user():
    data   = request.get_json(silent=True) or {}
    target = str(data.get('target', ''))
    text   = data.get('text', '')
    if not target or not text:
        return jsonify({'ok': False, 'error': 'target and text required'}), 400
    from msg_sender import send_to_user
    ok, err = send_to_user(target, text)
    return jsonify({'ok': ok, 'error': err})

@app.route('/api/msg/broadcast', methods=['POST'])
@require_token
def api_msg_broadcast():
    data = request.get_json(silent=True) or {}
    text = data.get('text', '')
    if not text:
        return jsonify({'ok': False, 'error': 'text required'}), 400
    from auth_module import get_all_users
    from msg_sender import send_to_user
    targets = [str(u['telegram_id']) for u in get_all_users()
               if u.get('status') == 'active' and u.get('login')]
    sent = failed = 0
    for t in targets:
        ok2, _ = send_to_user(t, text)
        if ok2: sent += 1
        else:   failed += 1
        time.sleep(0.05)
    return jsonify({'ok': True, 'sent': sent, 'failed': failed})

# ── Processes ─────────────────────────────────────────────────────────────────
@app.route('/api/processes')
@require_token
def api_processes():
    procs = []

    def _decode(b):
        if not b: return ''
        for enc in ('utf-8', 'cp1251', 'cp866', 'latin-1'):
            try: return b.decode(enc)
            except: pass
        return b.decode('utf-8', errors='replace')

    try:
        if platform.system() == 'Windows':
            r = subprocess.run(
                ['tasklist', '/FI', 'IMAGENAME eq python.exe', '/FO', 'CSV'],
                capture_output=True, timeout=5
            )
            stdout = _decode(r.stdout) or ''
            for line in stdout.splitlines()[1:]:
                p = [x.strip('"') for x in line.split('","')]
                if len(p) >= 5:
                    procs.append({
                        'pid':   p[1], 'name': p[0],
                        'mem':   p[4], 'cpu':  '—',
                        'alive': True,
                    })
        else:
            r = subprocess.run(['ps', 'aux'], capture_output=True, timeout=5)
            stdout = _decode(r.stdout) or ''
            for line in stdout.splitlines():
                if 'python' in line.lower() and 'grep' not in line:
                    p = line.split()
                    procs.append({
                        'pid':   p[1] if len(p) > 1 else '?',
                        'cpu':   p[2] if len(p) > 2 else '?',
                        'mem':   p[3] if len(p) > 3 else '?',
                        'name':  ' '.join(p[10:])[:80] if len(p) > 10 else line[:60],
                        'alive': True,
                    })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e), 'processes': []})

    # Добавляем внутренние процессы бота
    try:
        import fish_bot_state as _fbs
        for pname, proc in [
            ('cloudflared', _fbs.tunnel_process),
            ('bore',        _fbs.bore_process),
            ('ngrok',       _fbs.ngrok_process),
            ('serveo',      _fbs.serveo_process),
        ]:
            if proc is not None:
                alive = proc.poll() is None
                procs.insert(0, {
                    'pid':   str(proc.pid) if hasattr(proc,'pid') else '—',
                    'name':  f'[tunnel] {pname}',
                    'cpu':   '—', 'mem': '—',
                    'alive': alive,
                })
    except Exception:
        pass

    return jsonify({'ok': True, 'processes': procs})

@app.route('/api/processes/<pid>/kill', methods=['POST'])
@require_token
def api_kill(pid):
    from admin_module import kill_process
    ok, msg = kill_process(pid)
    return jsonify({'ok': ok, 'message': msg})

# ── Shell ─────────────────────────────────────────────────────────────────────
@app.route('/api/shell', methods=['POST'])
@require_token
def api_shell():
    data = request.get_json(silent=True) or {}
    cmd  = data.get('cmd', '').strip()
    if not cmd:
        return jsonify({'ok': False, 'error': 'cmd required'}), 400
    from admin_module import exec_shell
    ok, out = exec_shell(cmd, timeout=20)
    return jsonify({'ok': ok, 'output': out})

# ── Logs ──────────────────────────────────────────────────────────────────────
@app.route('/api/logs')
@require_token
def api_logs():
    n     = min(int(request.args.get('n', 100)), 500)
    level = request.args.get('level', '').upper()
    uid   = request.args.get('user_id', '')

    # Пробуем structured_logger
    try:
        import structured_logger as slog
        lines    = slog.get_logs(n)
        last_err = slog.get_last_error()
        if level:
            lines = [l for l in lines if l.get('level') == level]
        return jsonify({'ok': True, 'logs': lines, 'last_error': last_err, 'source': 'structured'})
    except Exception:
        pass

    # Fallback: _log_buffer
    lines = list(_log_buffer)
    if level:
        lines = [l for l in lines if l.get('level') == level]
    return jsonify({'ok': True, 'logs': lines[-n:], 'last_error': None, 'source': 'buffer'})

# ── Tasks ─────────────────────────────────────────────────────────────────────
@app.route('/api/tasks')
@require_token
def api_tasks():
    status = request.args.get('status')
    uid    = request.args.get('user_id')
    try:
        from task_queue import get_all_tasks, get_user_tasks, queue_stats
        tasks = get_user_tasks(uid, 50, status) if uid else get_all_tasks(50, status)
        return jsonify({'ok': True, 'tasks': tasks, 'stats': queue_stats()})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e), 'tasks': []})

@app.route('/api/tasks/<tid>/cancel', methods=['POST'])
@require_token
def api_task_cancel(tid):
    try:
        from task_queue import cancel_task
        ok, msg = cancel_task(tid)
        return jsonify({'ok': ok, 'message': msg})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})

@app.route('/api/tasks/<tid>/retry', methods=['POST'])
@require_token
def api_task_retry(tid):
    try:
        from task_queue import retry_task
        ok, msg = retry_task(tid)
        return jsonify({'ok': ok, 'message': msg})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})

# ── Sysinfo ───────────────────────────────────────────────────────────────────
@app.route('/api/sysinfo')
@require_token
def api_sysinfo():
    import shutil
    info = {'os': f'{platform.system()} {platform.machine()}', 'python': platform.python_version(),
            'cpu': os.cpu_count()}
    try:
        with open('/proc/meminfo') as f:
            mi = {l.split(':')[0]: int(l.split(':')[1].strip().split()[0]) for l in f if ':' in l}
        info['ram_total_mb'] = mi.get('MemTotal', 0) // 1024
        info['ram_free_mb']  = mi.get('MemAvailable', 0) // 1024
    except Exception:
        try:
            import psutil; m = psutil.virtual_memory()
            info['ram_total_mb'] = m.total // 1024 // 1024
            info['ram_free_mb']  = m.available // 1024 // 1024
        except Exception:
            pass
    try:
        du = shutil.disk_usage(BASE)
        info['disk_total_gb'] = round(du.total / 1024**3, 1)
        info['disk_free_gb']  = round(du.free  / 1024**3, 1)
    except Exception:
        pass
    keys = {}
    for k in ['GROQ_API_KEY','GEMINI_API_KEY','OPENAI_API_KEY','ANTHROPIC_API_KEY',
              'OPENROUTER_API_KEY','MISTRAL_API_KEY','ELEVEN_API_KEY','STABILITY_API_KEY']:
        keys[k] = bool(os.environ.get(k, ''))
    info['api_keys'] = keys
    return jsonify({'ok': True, **info})

# ── Tools ─────────────────────────────────────────────────────────────────────
# ── Tools ─────────────────────────────────────────────────────────────────────
@app.route('/api/neo/tools')
@require_token
def api_neo_tools():
    """Список инструментов AGENT NEO."""
    try:
        from agent_neo import list_tools
        return jsonify({'ok': True, 'tools': list_tools()})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e), 'tools': []})


@app.route('/api/matrix/tools')
@require_token
def api_matrix_tools():
    """Список инструментов AGENT MATRIX."""
    try:
        from agent_matrix import list_tools
        return jsonify({'ok': True, 'tools': list_tools()})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e), 'tools': []})


@app.route('/api/matrix/run', methods=['POST'])
@require_token
def api_matrix_run():
    """Запустить задачу через AGENT MATRIX."""
    data = request.get_json(silent=True) or {}
    task = data.get('task', '').strip()
    if not task:
        return jsonify({'ok': False, 'error': 'task required'}), 400
    steps = []
    try:
        from agent_matrix import run_matrix
        result = run_matrix(
            task=task,
            chat_id='admin_panel',
            on_status=lambda m: steps.append({'type': 'status', 'text': str(m), 'ok': True}),
        )
        return jsonify({
            'ok': result.ok if result else False,
            'final': result.answer if result else '',
            'result': result.answer if result else '',
            'steps': steps,
            'error': result.error if result else 'No result',
            'generated_tools': getattr(result, 'generated_tools', []),
            'zip_path': getattr(result, 'zip_path', ''),
        })
    except Exception as e:
        import traceback
        return jsonify({'ok': False, 'error': str(e),
                        'trace': traceback.format_exc()[-500:], 'steps': steps})


@app.route('/api/neo/tool/delete', methods=['POST'])
@require_token
def api_neo_tool_delete():
    """Удалить инструмент NEO."""
    data = request.get_json(silent=True) or {}
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'ok': False, 'error': 'name required'}), 400
    try:
        from agent_neo import TOOLS_DB, TOOLS_DIR
        import sqlite3 as _sqlite3
        db = _sqlite3.connect(str(TOOLS_DB))
        db.execute("DELETE FROM tools WHERE name=?", (name,))
        db.commit(); db.close()
        tf = TOOLS_DIR / f"{name}.py"
        if tf.exists(): tf.unlink()
        return jsonify({'ok': True, 'deleted': name})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/matrix/tool/delete', methods=['POST'])
@require_token
def api_matrix_tool_delete():
    """Удалить инструмент MATRIX."""
    data = request.get_json(silent=True) or {}
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'ok': False, 'error': 'name required'}), 400
    try:
        from agent_matrix import TOOLS_DB, TOOLS_DIR
        import sqlite3 as _sqlite3
        db = _sqlite3.connect(str(TOOLS_DB))
        db.execute("DELETE FROM tools WHERE name=?", (name,))
        db.commit(); db.close()
        tf = TOOLS_DIR / f"{name}.py"
        if tf.exists(): tf.unlink()
        return jsonify({'ok': True, 'deleted': name})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/agent/github_install', methods=['POST'])
@require_token
def api_agent_github_install():
    """Клонировать GitHub репо и установить как инструмент агента."""
    data      = request.get_json(silent=True) or {}
    url       = data.get('url', '').strip()
    agent     = data.get('agent', 'matrix').lower()
    tool_name = data.get('tool_name', '').strip()
    desc      = data.get('description', '').strip()
    if not url:
        return jsonify({'ok': False, 'error': 'url required'}), 400
    steps = []
    try:
        if agent == 'neo':
            from agent_neo import install_github_as_tool
            ok, name, err = install_github_as_tool(
                url=url, tool_name=tool_name, description=desc,
                on_status=lambda m: steps.append(m),
            )
        else:
            from agent_matrix import _install_github
            tool_name = tool_name or url.rstrip('/').split('/')[-1].replace('.git','').replace('-','_').lower()
            ok, err = _install_github(tool_name, url, desc, on_status=lambda m: steps.append(m))
            name = tool_name
        if ok:
            return jsonify({'ok': True, 'tool_name': name, 'log': steps})
        return jsonify({'ok': False, 'error': err, 'log': steps})
    except Exception as e:
        import traceback
        return jsonify({'ok': False, 'error': str(e),
                        'trace': traceback.format_exc()[-400:], 'log': steps})


@app.route('/api/agent/create_tool', methods=['POST'])
@require_token
def api_agent_create_tool():
    """Создать новый инструмент через LLM для агента."""
    data    = request.get_json(silent=True) or {}
    agent   = data.get('agent', 'matrix').lower()
    name    = data.get('tool_name', '').strip()
    desc    = data.get('description', '').strip()
    example = data.get('example_inputs', {})
    github  = data.get('github_url', '').strip()
    if not name or not desc:
        return jsonify({'ok': False, 'error': 'tool_name and description required'}), 400
    steps = []
    try:
        if agent == 'neo':
            from agent_neo import generate_tool
            ok, err = generate_tool(name, desc, example, on_status=lambda m: steps.append(m))
        else:
            from agent_matrix import generate_tool
            ok, err = generate_tool(name, desc, example,
                                    on_status=lambda m: steps.append(m),
                                    github_url=github)
        return jsonify({'ok': ok, 'error': err if not ok else '', 'log': steps})
    except Exception as e:
        import traceback
        return jsonify({'ok': False, 'error': str(e),
                        'trace': traceback.format_exc()[-400:], 'log': steps})


@app.route('/api/agent/tools_all')
@require_token
def api_agent_tools_all():
    """Все инструменты NEO + MATRIX объединённо."""
    result = {'neo': [], 'matrix': []}
    try:
        from agent_neo import list_tools as neo_list
        result['neo'] = neo_list()
    except Exception as e:
        result['neo_error'] = str(e)
    try:
        from agent_matrix import list_tools as mx_list
        result['matrix'] = mx_list()
    except Exception as e:
        result['matrix_error'] = str(e)
    return jsonify({'ok': True, **result})


@app.route('/api/agent/tool_usage')
@require_token
def api_agent_tool_usage():
    """Получить usage guide для GitHub инструмента."""
    agent = request.args.get('agent', 'matrix')
    name  = request.args.get('name', '').strip()
    if not name:
        return jsonify({'ok': False, 'error': 'name required'}), 400
    try:
        if agent == 'matrix':
            from agent_matrix import TOOLS_DIR
        else:
            from agent_neo import TOOLS_DIR
        guide = TOOLS_DIR / f"{name}_usage.md"
        if guide.exists():
            return jsonify({'ok': True, 'guide': guide.read_text(encoding='utf-8')})
        return jsonify({'ok': False, 'error': 'Гайд не найден (инструмент установлен без README?)'})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/agent/tool_code')
@require_token
def api_agent_tool_code():
    """Получить исходный код инструмента."""
    agent = request.args.get('agent', 'matrix')
    name  = request.args.get('name', '').strip()
    if not name:
        return jsonify({'ok': False, 'error': 'name required'}), 400
    try:
        if agent == 'neo':
            from agent_neo import get_tool
            t = get_tool(name)
        else:
            from agent_matrix import get_tool_code
            code = get_tool_code(name)
            t = {'code': code} if code else None
        if not t:
            return jsonify({'ok': False, 'error': 'tool not found'})
        return jsonify({'ok': True, 'name': name, 'code': t.get('code', '')})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/tools')
@require_token
def api_tools():
    try:
        from agent_tools_registry import _TOOLS, registry_stats
        tools = []
        for t in _TOOLS.values():
            tools.append({
                'name':        t.name,
                'desc':        t.desc,
                'category':    t.category,
                'permissions': t.permissions,
                'timeout':     t.timeout,
                'cost':        t.cost,
                'sandbox':     t.sandbox,
                'tags':        t.tags,
                'runs':        t.runs,
                'ok_runs':     t.ok_runs,
                'fail_runs':   t.fail_runs,
                'success_rate': round(t.success_rate * 100),
                'avg_ms':      round(t.avg_ms),
            })
        # Сортируем: сначала по категории, потом по имени
        tools.sort(key=lambda x: (x['category'], x['name']))
        return jsonify({'ok': True, 'tools': tools, 'stats': registry_stats()})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e), 'tools': []})

@app.route('/api/agent/run', methods=['POST'])
@require_token
def api_agent_run():
    data       = request.get_json(silent=True) or {}
    task       = data.get('task', '').strip()
    agent      = data.get('agent', 'smith').lower()
    file_path  = data.get('file_path', '')   # путь к загруженному файлу
    if not task:
        return jsonify({'ok': False, 'error': 'task required'}), 400

    # Валидируем путь файла
    attached_files = []
    if file_path:
        real = os.path.realpath(file_path)
        base_real = os.path.realpath(BASE)
        if real.startswith(base_real) and os.path.isfile(real):
            attached_files = [real]

    steps = []

    # ── MATRIX ──
    if agent == 'matrix':
        try:
            from agent_matrix import run_matrix
            result = run_matrix(
                task=task, chat_id='admin_panel',
                attached_files=attached_files or None,
                on_status=lambda m: steps.append({'type':'status','text':str(m),'ok':True}),
            )
            return jsonify({
                'ok': bool(result and result.ok),
                'final': result.answer if result else '',
                'result': result.answer if result else '',
                'steps': steps,
                'error': result.error if result else 'No result',
                'generated_tools': getattr(result, 'generated_tools', []),
                'files': getattr(result, 'files', []),
                'zip_path': getattr(result, 'zip_path', ''),
            })
        except Exception as e:
            import traceback
            return jsonify({'ok': False, 'error': str(e),
                            'trace': traceback.format_exc()[-400:], 'steps': steps})

    # ── NEO ──
    if agent == 'neo':
        try:
            from agent_neo import run_neo
            result = run_neo(
                task=task, chat_id='admin_panel',
                attached_files=attached_files or None,
                on_status=lambda m: steps.append({'type':'status','text':str(m),'ok':True}),
            )
            answer = getattr(result, 'answer', '') or str(result) if result else ''
            return jsonify({
                'ok': bool(result),
                'final': answer[:2000],
                'result': answer[:2000],
                'steps': steps,
                'files': getattr(result, 'files', []),
                'zip_path': getattr(result, 'zip_path', ''),
                'error': getattr(result, 'error', '') if result else 'No result',
            })
        except Exception as e:
            import traceback
            return jsonify({'ok': False, 'error': str(e),
                            'trace': traceback.format_exc()[-400:], 'steps': steps})

    # ── АГЕНТ_СМИТ (default) ──
    try:
        from agent_tools_registry import run_agent_with_tools
        final, results = run_agent_with_tools(
            chat_id=None, user_request=task,
            on_status=lambda m: steps.append({'type': 'status', 'text': str(m)}),
        )
        final = final or '✅ Выполнено'
        for r in (results or []):
            steps.append({'type': 'tool', 'tool': str(r.get('tool','')),
                          'ok': bool(r.get('ok')),
                          'result': str(r.get('result',''))[:300]})
        arts = []
        for r in (results or []):
            for line in str(r.get('result','')).splitlines():
                line = line.strip()
                if os.path.exists(line) and os.path.isfile(line):
                    arts.append(line)
        return jsonify({'ok': True, 'final': str(final), 'steps': steps,
                        'result': str(final), 'artifacts': arts})
    except Exception as e:
        import traceback
        return jsonify({'ok': False, 'error': str(e),
                        'trace': traceback.format_exc()[-500:], 'steps': steps})


# ── File Upload ────────────────────────────────────────────────────────────────
@app.route('/api/files/upload', methods=['POST'])
@require_token
def api_file_upload():
    """Загрузка файлов на сервер."""
    if 'file' not in request.files:
        return jsonify({'ok': False, 'error': 'No file'}), 400
    f = request.files['file']
    if not f.filename:
        return jsonify({'ok': False, 'error': 'No filename'}), 400

    import werkzeug.utils
    safe_name = werkzeug.utils.secure_filename(f.filename)
    upload_dir = os.path.join(BASE, 'agent_projects', 'uploads')
    os.makedirs(upload_dir, exist_ok=True)
    dest = os.path.join(upload_dir, safe_name)
    f.save(dest)
    size = os.path.getsize(dest)
    return jsonify({'ok': True, 'path': dest, 'name': safe_name,
                    'size': size, 'size_hr': _hr_size(size)})


@app.route('/api/files/list')
@require_token
def api_file_list():
    """Список файлов в agent_projects."""
    dirs = [
        os.path.join(BASE, 'agent_projects'),
        os.path.join(BASE, 'agent_projects', 'uploads'),
        os.path.join(BASE, 'artifacts'),
    ]
    files = []
    for d in dirs:
        if not os.path.exists(d): continue
        for fname in sorted(os.listdir(d)):
            fpath = os.path.join(d, fname)
            if os.path.isfile(fpath):
                stat = os.stat(fpath)
                files.append({
                    'name':    fname,
                    'path':    fpath,
                    'size':    stat.st_size,
                    'size_hr': _hr_size(stat.st_size),
                    'mtime':   int(stat.st_mtime),
                    'ext':     fname.rsplit('.', 1)[-1].lower() if '.' in fname else '',
                })
    files.sort(key=lambda x: x['mtime'], reverse=True)
    return jsonify({'ok': True, 'files': files[:100]})


@app.route('/api/files/download')
@require_token
def api_file_download():
    """Скачать файл по пути."""
    from flask import send_file
    path = request.args.get('path', '')
    # Защита: только файлы внутри BASE_DIR
    real = os.path.realpath(path)
    base_real = os.path.realpath(BASE)
    if not real.startswith(base_real) or not os.path.isfile(real):
        return jsonify({'ok': False, 'error': 'File not found or access denied'}), 403
    return send_file(real, as_attachment=True,
                     download_name=os.path.basename(real))


@app.route('/api/files/delete', methods=['POST'])
@require_token
def api_file_delete():
    """Удалить файл."""
    data = request.get_json(silent=True) or {}
    path = data.get('path', '')
    real = os.path.realpath(path)
    base_real = os.path.realpath(BASE)
    if not real.startswith(base_real) or not os.path.isfile(real):
        return jsonify({'ok': False, 'error': 'Not found or denied'}), 403
    os.remove(real)
    return jsonify({'ok': True})


def _hr_size(n):
    for u in ('B','KB','MB','GB'):
        if n < 1024: return f"{n:.1f} {u}"
        n /= 1024
    return f"{n:.1f} GB"

# ── Config ────────────────────────────────────────────────────────────────────
@app.route('/api/config', methods=['GET'])
@require_token
def api_config_get():
    safe = ['LLM_PROVIDER','LLM_MODEL','TTS_PROVIDER','TTS_VOICE','TTS_LANGUAGE',
            'PARSE_INTERVAL_HOURS','ADMIN_IDS','ADMIN_WEB_PORT',
            'CODE_PROVIDER','CODE_MODEL','AGENT_PROVIDER','AGENT_MODEL']
    return jsonify({'ok': True, 'config': {k: os.environ.get(k,'') for k in safe}})

@app.route('/api/config', methods=['POST'])
@require_token
def api_config_set():
    data = request.get_json(silent=True) or {}
    allowed = {'LLM_PROVIDER','LLM_MODEL','LLM_API_KEY','TTS_PROVIDER','TTS_VOICE',
               'TTS_LANGUAGE','GROQ_API_KEY','GEMINI_API_KEY','OPENAI_API_KEY',
               'ANTHROPIC_API_KEY','OPENROUTER_API_KEY','MISTRAL_API_KEY',
               'ELEVEN_API_KEY','ELEVEN_VOICE_ID','STABILITY_API_KEY','ADMIN_IDS',
               'CODE_PROVIDER','CODE_MODEL','AGENT_PROVIDER','AGENT_MODEL'}
    updated = {}
    env_path = config.ENV_PATH
    try:
        lines = open(env_path).readlines() if os.path.exists(env_path) else []
    except Exception:
        lines = []
    for k, v in data.items():
        if k not in allowed or k == 'token': continue
        os.environ[k] = str(v); updated[k] = v
        found = False
        for i, line in enumerate(lines):
            if line.startswith(f'{k}='):
                lines[i] = f'{k}={v}\n'; found = True; break
        if not found:
            lines.append(f'{k}={v}\n')
    try:
        with open(env_path, 'w') as f: f.writelines(lines)
        config.reload()
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})
    return jsonify({'ok': True, 'updated': updated})

# ── Restart ───────────────────────────────────────────────────────────────────
@app.route('/api/restart', methods=['POST'])
@require_token
def api_restart():
    def _do():
        time.sleep(2)
        if platform.system() == 'Windows':
            subprocess.Popen([sys.executable] + sys.argv, cwd=BASE)
            os._exit(0)
        else:
            os.execv(sys.executable, [sys.executable] + sys.argv)
    threading.Thread(target=_do, daemon=True).start()
    return jsonify({'ok': True, 'message': 'Перезапуск через 2с...'})


# ── Tunnel management ─────────────────────────────────────────────────────────
@app.route('/api/tunnel/start', methods=['POST'])
@require_token
def api_tunnel_start():
    """Запустить тоннель (cloudflared или bore)."""
    data  = request.get_json(silent=True) or {}
    ttype = data.get('type', 'cloudflared').lower()
    port  = int(os.environ.get('ADMIN_WEB_PORT', 8080))
    try:
        if ttype == 'cloudflared':
            try:
                from fish_bot_state import _state as fbs
                # Уже запущен?
                if getattr(fbs, 'tunnel_process', None):
                    return jsonify({'ok': True, 'message': 'Cloudflared уже запущен',
                                    'url': getattr(fbs, 'tunnel_url', '')})
            except ImportError:
                pass
            proc = subprocess.Popen(
                ['cloudflared', 'tunnel', '--url', f'http://localhost:{port}'],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT
            )
            # Ждём URL из лога (до 15 сек)
            url = ''
            import re as _re, select as _sel
            deadline = time.time() + 15
            while time.time() < deadline:
                try:
                    line = proc.stdout.readline()
                    if line:
                        text = line.decode('utf-8', errors='replace')
                        m = _re.search(r'https://[\w\-]+\.trycloudflare\.com', text)
                        if m:
                            url = m.group(0); break
                except Exception:
                    break
            try:
                from fish_bot_state import _state as fbs
                fbs.tunnel_process = proc
                fbs.tunnel_url = url
            except ImportError:
                pass
            return jsonify({'ok': True, 'url': url, 'pid': proc.pid})

        elif ttype == 'bore':
            proc = subprocess.Popen(
                ['bore', 'local', str(port), '--to', 'bore.pub'],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT
            )
            url = f'http://bore.pub:{port}'
            try:
                from fish_bot_state import _state as fbs
                fbs.bore_process = proc
                fbs.bore_url = url
            except ImportError:
                pass
            return jsonify({'ok': True, 'url': url, 'pid': proc.pid})

        return jsonify({'ok': False, 'error': f'Неизвестный тип: {ttype}'})
    except FileNotFoundError as e:
        return jsonify({'ok': False, 'error': f'{ttype} не установлен: {e}'})
    except Exception as e:
        import traceback
        return jsonify({'ok': False, 'error': str(e), 'trace': traceback.format_exc()[-300:]})


@app.route('/api/tunnel/stop', methods=['POST'])
@require_token
def api_tunnel_stop():
    """Остановить тоннель."""
    data  = request.get_json(silent=True) or {}
    ttype = data.get('type', 'cloudflared').lower()
    try:
        from fish_bot_state import _state as fbs
        proc_attr = 'tunnel_process' if ttype == 'cloudflared' else 'bore_process'
        url_attr  = 'tunnel_url'     if ttype == 'cloudflared' else 'bore_url'
        proc = getattr(fbs, proc_attr, None)
        if proc:
            proc.terminate()
            setattr(fbs, proc_attr, None)
            setattr(fbs, url_attr, '')
        return jsonify({'ok': True})
    except ImportError:
        # fallback: kill by name
        subprocess.run(['pkill', '-f', ttype], capture_output=True)
        return jsonify({'ok': True, 'note': 'pkill fallback'})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/system')
@require_token
def api_system_info():
    """Системная информация — IP, hostname и т.д."""
    import socket
    info = {
        'ok':       True,
        'hostname': socket.gethostname(),
        'platform': platform.system() + ' ' + platform.release(),
        'python':   platform.python_version(),
        'admin_port': int(os.environ.get('ADMIN_WEB_PORT', 8080)),
    }
    # Local IP
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        info['local_ip'] = s.getsockname()[0]
        s.close()
    except Exception:
        info['local_ip'] = '127.0.0.1'
    return jsonify(info)

# ── Static panel ─────────────────────────────────────────────────────────────
@app.route('/panel')
@app.route('/panel/')
def serve_panel():
    panel = os.path.join(BASE, 'admin_panel.html')
    if os.path.exists(panel):
        return send_file(panel)
    return '<h1>admin_panel.html not found</h1><p>Place admin_panel.html in the bot folder.</p>', 404

# ── Remote Control API ────────────────────────────────────────────────────────

@app.route('/api/rc/shell', methods=['POST'])
@require_token
def api_rc_shell():
    """Выполнить shell команду."""
    data = request.get_json(silent=True) or {}
    cmd  = data.get('cmd', data.get('command', '')).strip()
    cwd  = data.get('cwd', '')
    if not cmd:
        return jsonify({'ok': False, 'error': 'cmd required'}), 400
    try:
        from remote_control import get_session, check_command_allowed
        allowed, reason = check_command_allowed(cmd, is_god=True)  # admin panel = GOD
        if not allowed:
            return jsonify({'ok': False, 'error': reason})
        sess = get_session('admin_panel')
        if cwd: sess.cwd = cwd
        ok, out = sess.run(cmd, timeout=30)
        return jsonify({'ok': ok, 'output': out, 'cwd': sess.cwd, 'prompt': sess.get_prompt()})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/rc/stats')
@require_token
def api_rc_stats():
    """Системная статистика."""
    try:
        from remote_control import get_system_info, docker_stats
        info = get_system_info()
        try: ds = docker_stats()
        except Exception: ds = ""
        return jsonify({'ok': True, 'info': info, 'docker_stats': ds})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/rc/docker')
@require_token
def api_rc_docker_list():
    """Список Docker контейнеров."""
    try:
        from remote_control import docker_list
        return jsonify({'ok': True, 'containers': docker_list()})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/rc/docker/action', methods=['POST'])
@require_token
def api_rc_docker_action():
    """Действие с контейнером: start/stop/restart/logs/rm."""
    data      = request.get_json(silent=True) or {}
    container = data.get('container', '').strip()
    action    = data.get('action', '').strip()
    if not container or not action:
        return jsonify({'ok': False, 'error': 'container and action required'}), 400
    try:
        from remote_control import docker_action
        ok, out = docker_action(container, action)
        return jsonify({'ok': ok, 'output': out})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/rc/pty/start', methods=['POST'])
@require_token
def api_rc_pty_start():
    """Запустить PTY сессию."""
    try:
        from remote_control import pty_start, pty_is_active
        if not pty_is_active('admin_pty'):
            ok = pty_start('admin_pty')
            return jsonify({'ok': ok, 'active': ok})
        return jsonify({'ok': True, 'active': True, 'note': 'already running'})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/rc/pty/write', methods=['POST'])
@require_token
def api_rc_pty_write():
    """Отправить команду в PTY."""
    data = request.get_json(silent=True) or {}
    cmd  = data.get('cmd', '').strip()
    if not cmd:
        return jsonify({'ok': False, 'error': 'cmd required'}), 400
    try:
        from remote_control import pty_write, pty_start, pty_is_active
        if not pty_is_active('admin_pty'):
            pty_start('admin_pty')
        ok, out = pty_write('admin_pty', cmd)
        return jsonify({'ok': ok, 'output': out})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/rc/pty/stop', methods=['POST'])
@require_token
def api_rc_pty_stop():
    """Закрыть PTY сессию."""
    try:
        from remote_control import pty_stop
        pty_stop('admin_pty')
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})


# ── Start ─────────────────────────────────────────────────────────────────────
_start_time = time.time()
_web_started = False   # флаг чтобы не запускать дважды

def _find_free_port(start_port, attempts=5):
    """Ищет свободный порт начиная с start_port."""
    import socket
    for p in range(start_port, start_port + attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(('0.0.0.0', p))
                return p
        except OSError:
            continue
    return None


# ════════════════════════════════════════════════════════════════════════════
#  MODULE APIs  — Learning / Memory / Skills / Tasks / Backup / Models / etc
# ════════════════════════════════════════════════════════════════════════════

@app.route('/api/learning/stats')
@require_token
def api_learning_stats():
    """Learning loop stats — success/fail rates per pattern."""
    try:
        import sqlite3 as _s
        from agent_memory import DB_PATH
        db = _s.connect(str(DB_PATH))
        db.row_factory = _s.Row
        rows = db.execute(
            "SELECT pattern, tool_sequence, success_count, fail_count, updated_at "
            "FROM agent_learning ORDER BY success_count DESC LIMIT 50"
        ).fetchall()
        db.close()
        return jsonify({'ok': True, 'patterns': [dict(r) for r in rows]})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e), 'patterns': []})


@app.route('/api/learning/suggest', methods=['POST'])
@require_token
def api_learning_suggest():
    """Suggest tool sequence for a task based on past success."""
    data = request.get_json(silent=True) or {}
    task = data.get('task', '').strip()
    if not task:
        return jsonify({'ok': False, 'error': 'task required'}), 400
    try:
        from agent_memory import AgentLearning
        tools = AgentLearning().suggest_tools(task)
        return jsonify({'ok': True, 'tools': tools or [], 'task': task})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/learning/clear', methods=['POST'])
@require_token
def api_learning_clear():
    """Clear learning data."""
    try:
        import sqlite3 as _s
        from agent_memory import DB_PATH
        db = _s.connect(str(DB_PATH))
        db.execute("DELETE FROM agent_learning")
        db.commit(); db.close()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/memory/users')
@require_token
def api_memory_users():
    """Task history across all users."""
    try:
        import sqlite3 as _s
        from agent_memory import DB_PATH
        db = _s.connect(str(DB_PATH))
        db.row_factory = _s.Row
        rows = db.execute(
            "SELECT user_id, task, status, duration_s, created_at FROM task_history "
            "ORDER BY created_at DESC LIMIT 100"
        ).fetchall()
        db.close()
        return jsonify({'ok': True, 'history': [dict(r) for r in rows]})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/tasks/queue')
@require_token
def api_tasks_queue():
    """Get all tasks from task queue."""
    try:
        from task_queue import get_all_tasks
        tasks = get_all_tasks(limit=50)
        return jsonify({'ok': True, 'tasks': tasks or []})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e), 'tasks': []})


@app.route('/api/backup/create', methods=['POST'])
@require_token
def api_backup_create():
    """Create project backup."""
    try:
        from backup import collect_files, sha256
        import zipfile, time as _t
        ts = _t.strftime('%Y%m%d_%H%M%S')
        out_path = os.path.join(BASE, f'backup_{ts}.zip')
        files = collect_files(BASE)
        with zipfile.ZipFile(out_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for f in files[:500]:
                try:
                    zf.write(f, os.path.relpath(f, BASE))
                except Exception:
                    pass
        size = os.path.getsize(out_path)
        return jsonify({'ok': True, 'path': out_path, 'size': size,
                        'size_hr': f"{size//1024}KB"})
    except Exception as e:
        import traceback
        return jsonify({'ok': False, 'error': str(e), 'trace': traceback.format_exc()[-300:]})


@app.route('/api/models/discover')
@require_token
def api_models_discover():
    """Discover all available LLM models."""
    try:
        from model_discovery import discover_all, load_cache
        cached = load_cache()
        if cached:
            return jsonify({'ok': True, 'models': cached, 'source': 'cache'})
        models = discover_all()
        return jsonify({'ok': True, 'models': models, 'source': 'live'})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e), 'models': {}})


@app.route('/api/providers/status')
@require_token
def api_providers_status():
    """Check all LLM providers status."""
    try:
        from providers_hub import ProvidersHub
        hub = ProvidersHub()
        return jsonify({
            'ok': True,
            'active_llm':   hub.active_llm(),
            'best_llm':     hub.best_llm(),
            'active_image': hub.active_image(),
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/billing/stats')
@require_token
def api_billing_stats():
    """Billing stats for all users."""
    try:
        from billing import BillingManager
        bm = BillingManager()
        import sqlite3 as _s
        db = _s.connect(str(bm._db_path if hasattr(bm, '_db_path') else os.path.join(BASE, 'auth.db')))
        db.row_factory = _s.Row
        try:
            rows = db.execute("SELECT user_id, plan, credits FROM billing ORDER BY credits DESC LIMIT 50").fetchall()
            return jsonify({'ok': True, 'billing': [dict(r) for r in rows]})
        except Exception:
            return jsonify({'ok': True, 'billing': [], 'note': 'billing table not found'})
        finally:
            db.close()
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/proxy/status')
@require_token
def api_proxy_status():
    """Proxy/Tor status."""
    try:
        from proxy_manager import ProxyManager
        pm = ProxyManager()
        proxy = pm.get_proxy()
        return jsonify({'ok': True, 'proxy': proxy, 'pool_size': len(pm._pool) if hasattr(pm, '_pool') else 0})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/updater/check')
@require_token
def api_updater_check():
    """Check for updates."""
    try:
        from updater import check_dependencies, get_bot_info
        deps = check_dependencies()
        info = get_bot_info()
        return jsonify({'ok': True, 'deps': deps, 'bot': info})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/skills/evolution')
@require_token
def api_skills_evolution():
    """Skill evolution — tools ranked by success rate."""
    try:
        import sqlite3 as _s
        from agent_memory import DB_PATH
        db = _s.connect(str(DB_PATH))
        db.row_factory = _s.Row
        rows = db.execute(
            "SELECT pattern, tool_sequence, success_count, fail_count, "
            "ROUND(CAST(success_count AS FLOAT) / MAX(success_count+fail_count,1) * 100) as rate "
            "FROM agent_learning WHERE success_count+fail_count > 0 "
            "ORDER BY rate DESC, success_count DESC LIMIT 30"
        ).fetchall()
        db.close()
        skills = []
        for r in rows:
            import json as _j
            try: tools = _j.loads(r['tool_sequence'])
            except: tools = [r['tool_sequence']]
            skills.append({
                'pattern': r['pattern'],
                'tools': tools,
                'success': r['success_count'],
                'fail': r['fail_count'],
                'rate': r['rate'],
                'level': 'expert' if r['rate'] >= 80 else 'trained' if r['rate'] >= 50 else 'learning'
            })
        return jsonify({'ok': True, 'skills': skills})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e), 'skills': []})


@app.route('/api/marketplace/pipelines')
@require_token
def api_marketplace_list():
    """List shared pipelines in marketplace."""
    mp_file = os.path.join(BASE, 'marketplace.json')
    try:
        import json as _j
        if os.path.exists(mp_file):
            data = _j.loads(open(mp_file).read())
        else:
            data = []
        return jsonify({'ok': True, 'pipelines': data})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e), 'pipelines': []})


@app.route('/api/marketplace/share', methods=['POST'])
@require_token
def api_marketplace_share():
    """Share a pipeline to marketplace."""
    data = request.get_json(silent=True) or {}
    name   = data.get('name', '').strip()
    desc   = data.get('description', '').strip()
    nodes  = data.get('nodes', [])
    author = data.get('author', 'Anonymous')
    if not name or not nodes:
        return jsonify({'ok': False, 'error': 'name and nodes required'}), 400
    import json as _j, time as _t
    mp_file = os.path.join(BASE, 'marketplace.json')
    pipelines = _j.loads(open(mp_file).read()) if os.path.exists(mp_file) else []
    pipelines.append({
        'id': str(int(_t.time())),
        'name': name,
        'description': desc,
        'author': author,
        'nodes': nodes,
        'created': _t.strftime('%Y-%m-%d %H:%M'),
        'runs': 0,
    })
    open(mp_file, 'w').write(_j.dumps(pipelines, ensure_ascii=False, indent=2))
    return jsonify({'ok': True, 'id': pipelines[-1]['id']})


@app.route('/api/marketplace/import', methods=['POST'])
@require_token
def api_marketplace_import():
    """Import a pipeline from marketplace."""
    data = request.get_json(silent=True) or {}
    pid  = data.get('id', '').strip()
    import json as _j
    mp_file = os.path.join(BASE, 'marketplace.json')
    pipelines = _j.loads(open(mp_file).read()) if os.path.exists(mp_file) else []
    pl = next((p for p in pipelines if p.get('id') == pid), None)
    if not pl:
        return jsonify({'ok': False, 'error': 'Pipeline not found'}), 404
    pl['runs'] = pl.get('runs', 0) + 1
    open(mp_file, 'w').write(_j.dumps(pipelines, ensure_ascii=False, indent=2))
    return jsonify({'ok': True, 'pipeline': pl})


@app.route('/api/workflow/execute', methods=['POST'])
@require_token
def api_workflow_execute():
    """Execute a workflow (list of nodes with agent tasks)."""
    data   = request.get_json(silent=True) or {}
    nodes  = data.get('nodes', [])
    agent  = data.get('agent', 'matrix')
    if not nodes:
        return jsonify({'ok': False, 'error': 'nodes required'}), 400
    results = []
    steps_log = []
    try:
        for node in nodes:
            task = node.get('task') or node.get('label') or node.get('type', '')
            if not task:
                continue
            if agent == 'matrix':
                from agent_matrix import run_matrix
                r = run_matrix(task=task, chat_id='workflow',
                               on_status=lambda m: steps_log.append(m))
                results.append({'node': node.get('id'), 'ok': r.ok if r else False,
                                 'answer': r.answer[:500] if r else ''})
            else:
                from agent_neo import run_neo
                r = run_neo(task=task, chat_id='workflow',
                            on_status=lambda m: steps_log.append(m))
                results.append({'node': node.get('id'), 'ok': bool(r),
                                 'answer': getattr(r, 'answer', '')[:500]})
    except Exception as e:
        import traceback
        return jsonify({'ok': False, 'error': str(e),
                        'trace': traceback.format_exc()[-400:], 'results': results})
    return jsonify({'ok': True, 'results': results, 'log': steps_log[-20:]})


def start_admin_web():
    global _web_started
    if _web_started:
        print("  ℹ️ Admin Web уже запущен", flush=True)
        return None
    _web_started = True

    def _run():
        import logging
        logging.getLogger('werkzeug').setLevel(logging.ERROR)

        port = _find_free_port(ADMIN_WEB_PORT)
        if port is None:
            print(f"  ❌ Admin Web: нет свободного порта (начиная с {ADMIN_WEB_PORT})", flush=True)
            return

        if port != ADMIN_WEB_PORT:
            print(f"  ⚠️ Порт {ADMIN_WEB_PORT} занят, использую {port}", flush=True)

        print(f"  🌐 Admin Panel: http://0.0.0.0:{port}/panel", flush=True)
        print(f"  🔑 Token: {ADMIN_WEB_TOKEN[:8]}...", flush=True)
        install_log_capture()
        try:
            app.run(host='0.0.0.0', port=port,
                    debug=False, threaded=True, use_reloader=False)
        except Exception as e:
            print(f"  ❌ Admin Web упал: {e}", flush=True)

    t = threading.Thread(target=_run, daemon=True, name='admin-web')
    t.start()
    return t


if __name__ == '__main__':
    import logging
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    port = int(os.environ.get('ADMIN_WEB_PORT', 8080))
    print(f"  🌐 Admin Panel (standalone): http://0.0.0.0:{port}/panel", flush=True)
    print(f"  🔑 Token: {ADMIN_WEB_TOKEN[:8]}...", flush=True)
    install_log_capture()
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True, use_reloader=False)
