"""
task_queue.py — Очередь задач АВТОМУВИ
Статусы: pending / running / done / failed / cancelled
Поддержка: повтор, артефакты, уведомления, изоляция по пользователю
"""
import os, json, time, sqlite3, threading, traceback, uuid
from datetime import datetime
import config

DB_PATH = os.path.join(getattr(config, 'DATA_DIR', None) or config.BASE_DIR, 'tasks.db')
ARTIFACTS_DIR = os.path.join(config.BASE_DIR, 'artifacts')
os.makedirs(getattr(config, 'DATA_DIR', None) or config.BASE_DIR, exist_ok=True)
os.makedirs(ARTIFACTS_DIR, exist_ok=True)

# ─── Инициализация БД ─────────────────────────────────────────────────────────

def init_tasks_db():
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    with sqlite3.connect(DB_PATH) as c:
        c.executescript('''
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                type TEXT NOT NULL,
                title TEXT,
                payload TEXT,
                status TEXT DEFAULT 'pending',
                result TEXT,
                error TEXT,
                artifacts TEXT,
                retry_count INTEGER DEFAULT 0,
                max_retries INTEGER DEFAULT 2,
                created_at TEXT,
                started_at TEXT,
                finished_at TEXT,
                notify_on_done INTEGER DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS artifacts (
                id TEXT PRIMARY KEY,
                task_id TEXT,
                user_id TEXT,
                name TEXT,
                path TEXT,
                mime_type TEXT,
                size_bytes INTEGER,
                created_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_tasks_user ON tasks(user_id);
            CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
        ''')

# ─── CRUD ─────────────────────────────────────────────────────────────────────

def create_task(user_id, task_type, title, payload=None, max_retries=2, notify=True):
    """Создаёт задачу и ставит в очередь. Возвращает task_id."""
    task_id = str(uuid.uuid4())[:8]
    now = datetime.now().isoformat()
    with sqlite3.connect(DB_PATH) as c:
        c.execute('''INSERT INTO tasks
            (id, user_id, type, title, payload, status, created_at, max_retries, notify_on_done)
            VALUES (?,?,?,?,?,?,?,?,?)''',
            (task_id, str(user_id), task_type, title,
             json.dumps(payload or {}, ensure_ascii=False),
             'pending', now, max_retries, 1 if notify else 0))
    _task_queue.put(task_id)
    return task_id

def get_task(task_id):
    with sqlite3.connect(DB_PATH) as c:
        c.row_factory = sqlite3.Row
        r = c.execute('SELECT * FROM tasks WHERE id=?', (task_id,)).fetchone()
        return dict(r) if r else None

def get_user_tasks(user_id, limit=20, status=None):
    with sqlite3.connect(DB_PATH) as c:
        c.row_factory = sqlite3.Row
        if status:
            rows = c.execute(
                'SELECT * FROM tasks WHERE user_id=? AND status=? ORDER BY created_at DESC LIMIT ?',
                (str(user_id), status, limit)).fetchall()
        else:
            rows = c.execute(
                'SELECT * FROM tasks WHERE user_id=? ORDER BY created_at DESC LIMIT ?',
                (str(user_id), limit)).fetchall()
        return [dict(r) for r in rows]

def get_all_tasks(limit=50, status=None):
    with sqlite3.connect(DB_PATH) as c:
        c.row_factory = sqlite3.Row
        if status:
            rows = c.execute(
                'SELECT * FROM tasks WHERE status=? ORDER BY created_at DESC LIMIT ?',
                (status, limit)).fetchall()
        else:
            rows = c.execute(
                'SELECT * FROM tasks ORDER BY created_at DESC LIMIT ?',
                (limit,)).fetchall()
        return [dict(r) for r in rows]

def update_task(task_id, **kwargs):
    allowed = {'status','result','error','artifacts','started_at','finished_at','retry_count'}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return
    set_clause = ', '.join(f'{k}=?' for k in fields)
    with sqlite3.connect(DB_PATH) as c:
        c.execute(f'UPDATE tasks SET {set_clause} WHERE id=?',
                  list(fields.values()) + [task_id])

def cancel_task(task_id, user_id=None):
    task = get_task(task_id)
    if not task:
        return False, "Задача не найдена"
    if user_id and task['user_id'] != str(user_id):
        return False, "Не твоя задача"
    if task['status'] in ('done', 'failed', 'cancelled'):
        return False, f"Задача уже {task['status']}"
    update_task(task_id, status='cancelled')
    return True, "Задача отменена"

def retry_task(task_id, user_id=None):
    task = get_task(task_id)
    if not task:
        return False, "Задача не найдена"
    if user_id and task['user_id'] != str(user_id):
        return False, "Не твоя задача"
    if task['status'] not in ('failed', 'cancelled'):
        return False, "Можно повторить только failed/cancelled задачи"
    update_task(task_id, status='pending', error=None, retry_count=task['retry_count']+1)
    _task_queue.put(task_id)
    return True, "Задача поставлена в очередь повторно"

def save_artifact(task_id, user_id, name, path, mime_type='application/octet-stream'):
    """Регистрирует артефакт задачи в БД."""
    art_id = str(uuid.uuid4())[:8]
    size = os.path.getsize(path) if os.path.exists(path) else 0
    with sqlite3.connect(DB_PATH) as c:
        c.execute('''INSERT INTO artifacts (id, task_id, user_id, name, path, mime_type, size_bytes, created_at)
                     VALUES (?,?,?,?,?,?,?,?)''',
                  (art_id, task_id, str(user_id), name, path, mime_type, size, datetime.now().isoformat()))
    # Обновляем список артефактов в задаче
    task = get_task(task_id)
    arts = json.loads(task.get('artifacts') or '[]')
    arts.append({'id': art_id, 'name': name, 'path': path, 'mime': mime_type})
    update_task(task_id, artifacts=json.dumps(arts, ensure_ascii=False))
    return art_id

def get_task_artifacts(task_id):
    with sqlite3.connect(DB_PATH) as c:
        c.row_factory = sqlite3.Row
        return [dict(r) for r in c.execute('SELECT * FROM artifacts WHERE task_id=?', (task_id,)).fetchall()]

def get_user_artifacts(user_id):
    with sqlite3.connect(DB_PATH) as c:
        c.row_factory = sqlite3.Row
        return [dict(r) for r in c.execute(
            'SELECT * FROM artifacts WHERE user_id=? ORDER BY created_at DESC LIMIT 50',
            (str(user_id),)).fetchall()]

def artifact_dir(user_id):
    """Папка артефактов пользователя (изолирована)."""
    d = os.path.join(ARTIFACTS_DIR, str(user_id))
    os.makedirs(d, exist_ok=True)
    return d

# ─── Форматирование ───────────────────────────────────────────────────────────

STATUS_ICON = {
    'pending':   '⏳',
    'running':   '▶️',
    'done':      '✅',
    'failed':    '❌',
    'cancelled': '🚫',
}

def format_task(task):
    icon = STATUS_ICON.get(task['status'], '?')
    ts   = (task.get('created_at') or '')[:16].replace('T', ' ')
    arts = json.loads(task.get('artifacts') or '[]')
    art_str = f" 📎{len(arts)}" if arts else ""
    return (
        f"{icon} <b>{task.get('title','Без названия')}</b>\n"
        f"   ID: <code>{task['id']}</code>  {ts}{art_str}\n"
        f"   Тип: <code>{task.get('type','?')}</code>"
    )

def format_task_list(tasks):
    if not tasks:
        return "📭 Нет задач."
    return "\n\n".join(format_task(t) for t in tasks[:10])

# ─── Worker (фоновый поток) ───────────────────────────────────────────────────
import queue as _queue
_task_queue = _queue.Queue()
_running_tasks = {}   # task_id → thread
_workers_running = False

def _execute_task(task_id):
    """Выполняет одну задачу. Вызывается из worker."""
    task = get_task(task_id)
    if not task or task['status'] not in ('pending',):
        return

    update_task(task_id, status='running', started_at=datetime.now().isoformat())
    user_id  = task['user_id']
    ttype    = task['type']
    payload  = json.loads(task.get('payload') or '{}')

    result = None
    error  = None

    try:
        if ttype == 'chat':
            from chat_agent import chat_respond, start_session, is_active, get_session
            text = payload.get('text','')
            if not is_active(user_id):
                start_session(user_id, 'chat')
            result = chat_respond(user_id, text)

        elif ttype == 'code':
            from chat_agent import code_agent_run, start_session
            start_session(user_id, 'code')
            r = code_agent_run(user_id, payload.get('text',''))
            result = r.get('_full_output','') or r.get('output','') or '✅ Выполнено'
            # Сохраняем файлы как артефакты
            adir = artifact_dir(user_id)
            for fpath in r.get('files', []):
                if os.path.exists(fpath):
                    import shutil
                    dest = os.path.join(adir, os.path.basename(fpath))
                    shutil.copy2(fpath, dest)
                    save_artifact(task_id, user_id, os.path.basename(fpath), dest)

        elif ttype == 'tool':
            from agent_tools_registry import execute_tool
            ok, res = execute_tool(payload.get('tool',''), payload.get('args',''),
                                   chat_id=user_id)
            result = res

        elif ttype == 'tts':
            from agent_tools_registry import tool_tts
            res = tool_tts({'text': payload.get('text',''), 'voice': payload.get('voice','')},
                           chat_id=None)
            result = res
            # Если файл создан — регистрируем артефакт
            if '✅' in res:
                path = res.split(': ')[-1].strip()
                if os.path.exists(path):
                    save_artifact(task_id, user_id, os.path.basename(path), path, 'audio/mpeg')

        elif ttype == 'image':
            from agent_tools_registry import tool_pollinations_image
            res = tool_pollinations_image({'prompt': payload.get('prompt','')}, chat_id=None)
            result = res
            if '✅' in res:
                path = res.split(': ')[-1].strip()
                if os.path.exists(path):
                    save_artifact(task_id, user_id, os.path.basename(path), path, 'image/jpeg')

        elif ttype == 'shell':
            from admin_module import exec_shell
            from agent_roles import has_perm
            if not has_perm(user_id, 'run_shell'):
                raise PermissionError("Нет прав на shell-команды")
            ok, out = exec_shell(payload.get('cmd',''), timeout=30)
            result = out

        else:
            result = f"Неизвестный тип задачи: {ttype}"

    except Exception as e:
        error = f"{type(e).__name__}: {e}\n{traceback.format_exc()[-500:]}"

    now = datetime.now().isoformat()
    if error:
        task_data = get_task(task_id)
        retries   = task_data.get('retry_count', 0)
        max_r     = task_data.get('max_retries', 2)
        if retries < max_r:
            update_task(task_id, status='pending', error=error,
                        retry_count=retries+1, finished_at=now)
            _task_queue.put(task_id)
        else:
            update_task(task_id, status='failed', error=error, finished_at=now)
    else:
        update_task(task_id, status='done', result=str(result)[:2000], finished_at=now)

    # Уведомление пользователю
    task_final = get_task(task_id)
    if task_final and task_final.get('notify_on_done'):
        _notify_user(task_final)


def _notify_user(task):
    """Отправляет уведомление о завершении задачи."""
    try:
        from telegram_client import send_message
        user_id = task['user_id']
        icon    = STATUS_ICON.get(task['status'], '?')
        arts    = json.loads(task.get('artifacts') or '[]')

        msg = (
            f"{icon} <b>Задача завершена</b>\n"
            f"<b>{task.get('title','?')}</b>\n"
            f"ID: <code>{task['id']}</code>\n"
        )
        if task['status'] == 'done' and task.get('result'):
            msg += f"\n📄 Результат:\n{task['result'][:800]}"
        if task['status'] == 'failed' and task.get('error'):
            msg += f"\n❌ Ошибка:\n<code>{task['error'][:400]}</code>"
        if arts:
            msg += f"\n\n📎 Артефактов: {len(arts)}"

        kb = {"inline_keyboard": [[
            {"text": "📋 Детали", "callback_data": f"task:info:{task['id']}"},
            {"text": "📎 Файлы",  "callback_data": f"task:arts:{task['id']}"},
        ]]}
        send_message(msg, user_id, reply_markup=kb)

        # Отправляем файлы-артефакты
        from telegram_client import send_document
        for art in arts[:5]:
            if os.path.exists(art.get('path','')):
                send_document(art['path'], caption=f"📎 {art['name']}", chat_id=user_id)
    except Exception as e:
        print(f"  ⚠️ notify error: {e}", flush=True)


def _worker_loop():
    """Бесконечный цикл обработки задач."""
    print("  ▶️ Task worker запущен", flush=True)
    while True:
        try:
            task_id = _task_queue.get(timeout=5)
            t = threading.Thread(target=_execute_task, args=(task_id,),
                                  name=f"task-{task_id}", daemon=True)
            _running_tasks[task_id] = t
            t.start()
            t.join()  # ждём завершения перед следующей
            _running_tasks.pop(task_id, None)
        except _queue.Empty:
            # Подбираем pending задачи из БД которые могли потеряться
            try:
                with sqlite3.connect(DB_PATH) as c:
                    rows = c.execute(
                        "SELECT id FROM tasks WHERE status='pending' ORDER BY created_at LIMIT 5"
                    ).fetchall()
                for (tid,) in rows:
                    if tid not in _running_tasks:
                        _task_queue.put(tid)
            except Exception:
                pass
        except Exception as e:
            print(f"  ⚠️ worker error: {e}", flush=True)
            time.sleep(2)


def start_workers(n=2):
    """Запускает n воркеров в фоне."""
    global _workers_running
    if _workers_running:
        return
    _workers_running = True
    init_tasks_db()
    for i in range(n):
        t = threading.Thread(target=_worker_loop, name=f"worker-{i}", daemon=True)
        t.start()
    print(f"  ✅ Task queue: {n} workers запущены", flush=True)


def queue_stats():
    """Статистика очереди."""
    with sqlite3.connect(DB_PATH) as c:
        rows = c.execute(
            "SELECT status, COUNT(*) FROM tasks GROUP BY status"
        ).fetchall()
    return {row[0]: row[1] for row in rows}
