# -*- coding: utf-8 -*-
"""
chat_agent.py — Агент-кодер + чат-агент AGENT_SMITH.

Экспортирует ВСЕ функции которые требует bot.py (строка 426-428):
  start_session, end_session, get_session, is_active, session_info,
  chat_respond, code_agent_run, format_code_result, all_active_sessions,
  add_to_history
"""

import json
import logging
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Optional, Dict, Any, Callable

logger = logging.getLogger(__name__)

MAX_FIX_ROUNDS = 5
SANDBOX_TIMEOUT = 30

# ─── Хранилище чат-сессий (синхронное) ──────────────────────────────────────

_sessions: Dict[int, Dict] = {}


def start_session(chat_id, mode: str = 'chat') -> None:
    """Открывает чат/кодер сессию. mode: 'chat' | 'code'"""
    _sessions[int(chat_id)] = {
        'mode': mode,
        'history': [],
        'active': True,
        'started': time.time(),
    }
    logger.info("Session started: chat_id=%s mode=%s", chat_id, mode)


def end_session(chat_id) -> None:
    """Завершает сессию."""
    s = _sessions.get(int(chat_id))
    if s:
        s['active'] = False
    logger.info("Session ended: chat_id=%s", chat_id)


def get_session(chat_id) -> Optional[Dict]:
    """Возвращает сессию или None."""
    return _sessions.get(int(chat_id))


def is_active(chat_id) -> bool:
    """True если сессия открыта."""
    s = _sessions.get(int(chat_id))
    return bool(s and s.get('active'))


def session_info(chat_id):
    """
    Возвращает dict с информацией о сессии (bot.py ожидает dict с 'mode' и 'messages'),
    или строку — оба формата поддерживаются.
    """
    s = _sessions.get(int(chat_id))
    if not s:
        return None
    info = {
        'mode':     s.get('mode', 'chat'),
        'messages': len(s.get('history', [])),
        'active':   s.get('active', False),
        'started':  s.get('started', time.time()),
    }
    return info


def all_active_sessions() -> Dict:
    """Все активные сессии {chat_id: session_dict}."""
    return {cid: s for cid, s in _sessions.items() if s.get('active')}


def add_to_history(chat_id, role: str, text: str) -> None:
    """Добавляет сообщение в историю."""
    cid = int(chat_id)
    if cid not in _sessions:
        _sessions[cid] = {'mode': 'chat', 'history': [], 'active': True, 'started': time.time()}
    h = _sessions[cid].setdefault('history', [])
    h.append({'role': role, 'content': text})
    if len(h) > 50:
        _sessions[cid]['history'] = h[-50:]


# ─── Чат-ответ ───────────────────────────────────────────────────────────────

def chat_respond(chat_id, text: str) -> str:
    """Синхронный LLM-ответ с историей контекста."""
    add_to_history(chat_id, 'user', text)
    history = _sessions.get(int(chat_id), {}).get('history', [])

    try:
        from llm_client import call_llm
        ctx = "\n".join(
            f"{m['role'].upper()}: {m['content']}"
            for m in history[-10:-1]
        )
        prompt = f"{ctx}\n\nUSER: {text}" if ctx else text
        reply = call_llm(prompt, system="Ты полезный ИИ-ассистент.", max_tokens=2000)
    except Exception as e:
        logger.error("chat_respond error: %s", e)
        reply = f"❌ Ошибка LLM: {e}"

    add_to_history(chat_id, 'assistant', reply)
    return reply


# ─── Агент-кодер (синхронный) ────────────────────────────────────────────────

def code_agent_run(
    chat_id,
    task: str,
    on_status: Callable = None,
    proj_mode: str = None,
) -> Dict[str, Any]:
    """
    Синхронный агент-кодер.

    Возвращает dict который понимает bot.py:
      success, code, output, _full_output, files, zip_path, errors, _task_type, text
    """
    if on_status is None:
        on_status = lambda m: None

    on_status("🧠 Анализирую задачу...")

    try:
        from agent_utils import detect_task_type, create_workspace, pack_artifacts, save_output
        task_type = proj_mode or detect_task_type(task)
        workspace = create_workspace(int(chat_id), task_type)
    except Exception as e:
        task_type = proj_mode or ("project" if _is_project_task(task) else "script")
        workspace = Path(tempfile.mkdtemp(prefix=f"agent_{chat_id}_"))

    on_status(f"📋 Тип: {task_type}")

    result: Dict[str, Any] = {
        'success': False,
        'code': '',
        'output': '',
        '_full_output': '',
        'files': [],
        'zip_path': None,
        'errors': [],
        '_task_type': task_type,
        'text': '',
    }

    try:
        if task_type == 'project' or _is_project_task(task):
            _run_project_sync(task, workspace, result, on_status)
        else:
            _run_script_sync(task, workspace, result, on_status)

        on_status("📦 Упаковываю архив...")
        try:
            from agent_utils import pack_artifacts, save_output as _so
            zip_path = pack_artifacts(workspace, zip_name=f"result_{chat_id}.zip")
        except Exception:
            import zipfile
            zip_path = workspace.parent / f"result_{chat_id}.zip"
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for fp in workspace.rglob("*"):
                    if fp.is_file() and "__pycache__" not in str(fp):
                        zf.write(fp, fp.relative_to(workspace.parent))

        result['zip_path'] = str(zip_path)
        if str(zip_path) not in result['files']:
            result['files'].append(str(zip_path))
        result['success'] = len(result['errors']) == 0

    except Exception as e:
        logger.exception("code_agent_run fatal: %s", e)
        result['errors'].append(str(e))
        result['_full_output'] = str(e)
        try:
            from agent_utils import pack_artifacts, save_output
            save_output(workspace, stderr=str(e))
            zp = pack_artifacts(workspace, zip_name=f"error_{chat_id}.zip")
            result['zip_path'] = str(zp)
        except Exception:
            pass

    result['text'] = format_code_result(result)
    return result


# ─── Внутренние агенты ───────────────────────────────────────────────────────

def _run_script_sync(task: str, workspace: Path, result: dict, on_status: Callable) -> None:
    """Скрипт: генерация → sandbox → autofix → output.txt"""
    on_status("🤖 Генерирую код...")
    code = _llm_code(task)
    result['code'] = code
    (workspace / "script.py").write_text(code, encoding="utf-8")

    on_status("▶️ Запускаю...")
    stdout, stderr, ok = _sandbox(workspace / "script.py", workspace)
    result['output'] = stdout
    result['_full_output'] = stdout or stderr

    if not ok:
        on_status("🔧 Autofix...")
        code, stdout, stderr, ok = _autofix(task, workspace, code, stderr, on_status)
        result['code'] = code
        result['output'] = stdout
        result['_full_output'] = stdout or stderr

    _write_output(workspace, stdout, stderr, ok)
    if not ok:
        result['errors'].append((stderr or "error")[:400])


def _run_project_sync(task: str, workspace: Path, result: dict, on_status: Callable) -> None:
    """Проект: генерация структуры → файлы → README"""
    on_status("📐 Проектирую структуру...")
    raw = _llm_project(task)
    try:
        plan = json.loads(re.sub(r"```json|```", "", raw).strip())
        if not isinstance(plan, list):
            raise ValueError
    except Exception:
        plan = [{"path": "main.py", "content": raw}]

    on_status(f"📂 Создаю {len(plan)} файлов...")
    for item in plan:
        fp = workspace / item.get("path", "file.py")
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(item.get("content", "# empty"), encoding="utf-8")
        result['files'].append(str(fp))

    readme = workspace / "README.md"
    if not readme.exists():
        readme.write_text(f"# {task[:60]}\n\nФайлов: {len(plan)}\n", encoding="utf-8")

    _write_output(workspace, extra=f"Проект: {len(plan)} файлов")


def _is_project_task(text: str) -> bool:
    kw = ["бот", "bot", "парсер", "parser", "сервис", "service",
          "несколько файлов", "проект", "приложение", "scaffold"]
    return any(k in text.lower() for k in kw)


# ─── Sandbox ─────────────────────────────────────────────────────────────────

def _sandbox(script: Path, cwd: Path, timeout: int = SANDBOX_TIMEOUT) -> tuple:
    try:
        r = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True, text=True,
            timeout=timeout, cwd=str(cwd),
        )
        return r.stdout, r.stderr, r.returncode == 0
    except subprocess.TimeoutExpired:
        return "", f"TimeoutError: >{timeout}с", False
    except Exception as e:
        return "", str(e), False


# ─── Autofix ─────────────────────────────────────────────────────────────────

def _autofix(task: str, workspace: Path, orig_code: str, orig_err: str,
             on_status: Callable) -> tuple:
    (workspace / "round_0_original.py").write_text(orig_code, encoding="utf-8")
    (workspace / "round_0_error.txt").write_text(orig_err, encoding="utf-8")

    code, err = orig_code, orig_err
    for i in range(1, MAX_FIX_ROUNDS + 1):
        on_status(f"🔄 Раунд {i}/{MAX_FIX_ROUNDS}...")
        fixed = _llm_fix(code, err)
        rf = workspace / f"round_{i}.py"
        rf.write_text(fixed, encoding="utf-8")

        stdout, stderr, ok = _sandbox(rf, workspace)
        (workspace / f"round_{i}_output.txt").write_text(
            f"STDOUT:\n{stdout}\nSTDERR:\n{stderr}", encoding="utf-8"
        )

        if ok:
            on_status(f"✅ Исправлено на раунде {i}!")
            final = workspace / "script.py"
            final.write_text(fixed, encoding="utf-8")
            return fixed, stdout, stderr, True

        code, err = fixed, stderr

    on_status(f"⚠️ Autofix не помог за {MAX_FIX_ROUNDS} попыток")
    (workspace / "script.py").write_text(code, encoding="utf-8")
    return code, "", err, False


# ─── output.txt ──────────────────────────────────────────────────────────────

def _write_output(workspace: Path, stdout: str = "", stderr: str = "",
                  ok: bool = True, extra: str = "") -> None:
    try:
        from agent_utils import save_output
        save_output(workspace, stdout=stdout, stderr=stderr,
                    extra=extra or ("✅ OK" if ok else "⚠️ Error"))
    except Exception:
        lines = []
        if stdout: lines += ["=== STDOUT ===", stdout]
        if stderr: lines += ["=== STDERR ===", stderr]
        if extra:  lines += ["=== NOTES ===",  extra]
        (workspace / "output.txt").write_text("\n".join(lines), encoding="utf-8")


# ─── Форматирование ──────────────────────────────────────────────────────────

def format_code_result(result: Dict[str, Any]) -> str:
    ok = result.get('success', False)
    icon = "✅" if ok else "⚠️"
    t = result.get('_task_type', 'script')

    parts = [f"{icon} <b>Агент-кодер</b> [{t}]"]

    code = result.get('code', '')
    if code and len(code) < 2000:
        parts.append(f"\n<pre><code>{_esc(code[:1500])}</code></pre>")

    out = result.get('output', '') or result.get('_full_output', '')
    if out and out != '(нет вывода)':
        parts.append(f"\n<b>Вывод:</b>\n<pre>{_esc(out[:600])}</pre>")

    for e in result.get('errors', [])[:2]:
        parts.append(f"❌ {_esc(str(e)[:200])}")

    zp = result.get('zip_path')
    if zp and os.path.exists(str(zp)):
        parts.append(f"📦 <code>{os.path.basename(str(zp))}</code>")

    return "\n".join(parts)


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ─── LLM-вызовы ──────────────────────────────────────────────────────────────

def _llm_code(task: str) -> str:
    try:
        from llm_client import call_llm
        return call_llm(
            f"Напиши Python-код для: {task}\n\nТолько код, без markdown.",
            system="Ты опытный Python разработчик.", max_tokens=3000
        )
    except Exception as e:
        return f"# Ошибка генерации: {e}\nprint('Hello')"


def _llm_project(task: str) -> str:
    try:
        from llm_client import call_llm
        return call_llm(
            f'Создай Python-проект для: {task}\n\n'
            'Верни JSON: [{{"path":"файл.py","content":"..."}}]. Только JSON.',
            system="Ты Python-архитектор.", max_tokens=4000
        )
    except Exception as e:
        return json.dumps([{"path": "main.py", "content": f"# {task}\nprint('TODO')"}])


def _llm_fix(code: str, error: str) -> str:
    try:
        from llm_client import call_llm
        return call_llm(
            f"Исправь код:\n```python\n{code[:3000]}\n```\nОшибка: {error[:800]}\n\nТолько код.",
            system="Ты Python-разработчик.", max_tokens=3000
        )
    except Exception:
        return code


# ─── Видео-агент ─────────────────────────────────────────────────────────────

def _run_video_agent(
    chat_id,
    task: str,
    on_status: Callable = None,
) -> Dict[str, Any]:
    """
    Видео-агент: скачивает видео / создаёт видео-контент.
    Используется bot.py строка 3499.

    Возвращает:
      {
        'success': bool,
        'files': [str],        # пути к файлам
        '_video_title': str,
        '_fsize_mb': float,
        '_video_fmt': str,     # 'mp4' | 'mp3'
        'errors': [str],
      }
    """
    if on_status is None:
        on_status = lambda m: None

    result: Dict[str, Any] = {
        'success': False,
        'files': [],
        '_video_title': '',
        '_fsize_mb': 0.0,
        '_video_fmt': 'mp4',
        'errors': [],
    }

    try:
        from agent_utils import create_workspace
        workspace = create_workspace(int(chat_id), "video")
    except Exception:
        import tempfile
        workspace = Path(tempfile.mkdtemp(prefix=f"video_{chat_id}_"))

    on_status("🎬 Анализирую видео-задачу...")

    try:
        # Пробуем использовать agent_tools_registry если доступен
        try:
            from agent_tools_registry import execute_tool
            on_status("📥 Скачиваю видео...")
            tool_result = execute_tool('moviepy_edit', {'task': task, 'workspace': str(workspace)})
            files = tool_result.get('files', [])
            if files:
                fpath = files[0]
                fsize = os.path.getsize(fpath) / 1024 / 1024 if os.path.exists(fpath) else 0
                result.update({
                    'success': True,
                    'files': files,
                    '_video_title': os.path.basename(fpath),
                    '_fsize_mb': fsize,
                    '_video_fmt': Path(fpath).suffix.lstrip('.') or 'mp4',
                })
                return result
        except Exception:
            pass

        # Fallback: генерируем код для видео через code_agent_run
        on_status("🤖 Генерирую видео-код...")
        agent_result = code_agent_run(chat_id, task, on_status=on_status, proj_mode='script')

        files = agent_result.get('files', [])
        # Ищем видео-файл в созданных файлах
        video_exts = {'.mp4', '.avi', '.mov', '.mkv', '.mp3', '.webm', '.gif'}
        video_files = [f for f in files if Path(f).suffix.lower() in video_exts]

        if video_files:
            fpath = video_files[0]
            fsize = os.path.getsize(fpath) / 1024 / 1024 if os.path.exists(fpath) else 0
            result.update({
                'success': True,
                'files': video_files,
                '_video_title': os.path.basename(fpath),
                '_fsize_mb': fsize,
                '_video_fmt': Path(fpath).suffix.lstrip('.'),
            })
        else:
            # Нет видео-файла — передаём все файлы
            result['files'] = files
            result['success'] = agent_result.get('success', False)
            result['errors'] = agent_result.get('errors', [])

    except Exception as e:
        logger.exception("_run_video_agent error: %s", e)
        result['errors'].append(str(e))

    return result


# ─── Восстановление сессий после рестарта ────────────────────────────────────

_SESSION_STORE_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'data', 'sessions.json'
)

def restore_sessions() -> list:
    """
    Восстанавливает сессии после рестарта бота из файла sessions.json.
    Возвращает список chat_id у которых были активные сессии.

    bot.py строка 8227: restored_ids = restore_sessions()
    """
    restored = []
    try:
        if not os.path.exists(_SESSION_STORE_FILE):
            return []
        with open(_SESSION_STORE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for cid_str, sess_data in data.items():
            cid = int(cid_str)
            mode = sess_data.get('mode', 'chat')
            history = sess_data.get('history', [])
            _sessions[cid] = {
                'mode':     mode,
                'history':  history[-20:],   # последние 20 сообщений
                'active':   True,
                'started':  sess_data.get('started', time.time()),
            }
            restored.append(cid)
        logger.info("Restored %d sessions from disk", len(restored))
    except Exception as e:
        logger.warning("restore_sessions failed: %s", e)
    return restored


def _save_sessions() -> None:
    """Сохраняет активные сессии на диск (вызывать при graceful shutdown)."""
    try:
        os.makedirs(os.path.dirname(_SESSION_STORE_FILE), exist_ok=True)
        data = {
            str(cid): {
                'mode':    s.get('mode', 'chat'),
                'history': s.get('history', [])[-20:],
                'started': s.get('started', time.time()),
            }
            for cid, s in _sessions.items()
            if s.get('active')
        }
        with open(_SESSION_STORE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info("Saved %d sessions to disk", len(data))
    except Exception as e:
        logger.warning("_save_sessions failed: %s", e)
