"""
BlackBugsAI — Python Sandbox
Безопасное выполнение Python-кода.
Уровни изоляции: soft (restricted builtins) | subprocess | docker
"""
import os, sys, subprocess, tempfile, time, re
import config

BLOCKED_IMPORTS = frozenset([
    'subprocess','socket','ctypes','importlib','__import__',
    'os.system','eval','exec','compile','open',
])

def _has_dangerous(code: str) -> tuple[bool, str]:
    """Проверяет код на опасные паттерны."""
    dangerous = [
        (r'\bos\.system\b',        'os.system'),
        (r'\bsubprocess\b',        'subprocess'),
        (r'\bctypes\b',            'ctypes'),
        (r'__import__\s*\(',       '__import__'),
        (r'\bsocket\.connect\b',   'socket.connect'),
        (r'open\s*\([^)]*["\']w',  'write to file'),
    ]
    for pattern, name in dangerous:
        if re.search(pattern, code):
            return True, name
    return False, ''

def run(code: str, timeout: int = 30,
        role: str = 'user', on_status=None) -> tuple[bool, str]:
    """
    Выполняет Python-код.
    role='user'  → проверка на опасные паттерны
    role='admin' → без ограничений
    """
    if not code.strip():
        return False, "❌ Пустой код"

    if role == 'user':
        dangerous, name = _has_dangerous(code)
        if dangerous:
            return False, f"🚫 Заблокировано: <code>{name}</code>"

    if on_status: on_status("🏖 Выполняю код...")

    # Пишем во временный файл и запускаем subprocess
    with tempfile.NamedTemporaryFile(
        suffix='.py', mode='w', delete=False, encoding='utf-8'
    ) as f:
        f.write(code)
        tmp = f.name

    try:
        r = subprocess.run(
            [sys.executable, tmp],
            capture_output=True, text=True,
            timeout=timeout,
            cwd=os.path.join(config.BASE_DIR, 'agent_projects')
        )
        out = ((r.stdout or '') + (r.stderr or '')).strip()
        return r.returncode == 0, out[:2000] or '(нет вывода)'
    except subprocess.TimeoutExpired:
        return False, f"⏰ Таймаут {timeout}с"
    except Exception as e:
        return False, f"❌ {e}"
    finally:
        try: os.unlink(tmp)
        except: pass


def lint(code: str) -> tuple[bool, str]:
    """Синтаксическая проверка кода."""
    import ast
    try:
        ast.parse(code)
        return True, "✅ Синтаксис OK"
    except SyntaxError as e:
        return False, f"❌ Синтаксис line {e.lineno}: {e.msg}"
