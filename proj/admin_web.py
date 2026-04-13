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

# ── Health (без токена — для Docker healthcheck) ───────────────────────────────
@app.route('/ping')
def ping():
    """Самый простой эндпоинт — без токена, без зависимостей."""
    return jsonify({'ok': True, 'pong': True, 'port': ADMIN_WEB_PORT}), 200

@app.route('/health')
def health():
    try:
        uptime = int(time.time() - _start_time)
        h, r = divmod(uptime, 3600); m, s = divmod(r, 60)
        # Проверяем БД
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
    data = request.get_json(silent=True) or {}
    task = data.get('task', '').strip()
    if not task:
        return jsonify({'ok': False, 'error': 'task required'}), 400
    steps = []
    try:
        from agent_tools_registry import run_agent_with_tools
        final, results = run_agent_with_tools(
            chat_id=None, user_request=task,
            on_status=lambda m: steps.append({'type': 'status', 'text': str(m)}),
        )
        # Guard against None
        final = final or '✅ Выполнено'
        for r in (results or []):
            steps.append({'type': 'tool', 'tool': str(r.get('tool','')),
                          'ok': bool(r.get('ok')),
                          'result': str(r.get('result',''))[:300]})
        # Собираем артефакты (файлы)
        arts = []
        for r in (results or []):
            res_str = str(r.get('result',''))
            for line in res_str.splitlines():
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

# ── Static panel ─────────────────────────────────────────────────────────────
@app.route('/panel')
@app.route('/panel/')
def serve_panel():
    panel = os.path.join(BASE, 'admin_panel.html')
    if os.path.exists(panel):
        return send_file(panel)
    return '<h1>admin_panel.html not found</h1><p>Place admin_panel.html in the bot folder.</p>', 404

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
