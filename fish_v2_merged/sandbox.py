"""
core/sandbox.py — Docker sandbox для изолированного выполнения кода.

Два режима:
  1. subprocess fallback  — выполняет код в изолированном процессе (без Docker)
  2. Docker контейнер     — полная изоляция на пользователя (если Docker доступен)

Docker-контейнер создаётся один раз на пользователя, переиспользуется.
"""

import os
import re
import ast
import sys
import time
import shlex
import signal
import subprocess
import tempfile
import logging
from typing import Optional, Tuple

logger = logging.getLogger('sandbox')

# ── Конфиги ───────────────────────────────────────────────────────
DOCKER_IMAGE   = 'python:3.11-slim'
EXEC_TIMEOUT   = 30    # секунд на выполнение
CONTAINER_MEM  = '256m'
CONTAINER_CPU  = '0.5'
SANDBOX_LABEL  = 'autocoder-sandbox'

# Опасные паттерны — блокируем без Docker
_DANGEROUS = [
    r'import\s+os\s*;?\s*os\.(system|popen|execv|execl)',
    r'subprocess\.(run|Popen|call)',
    r'__import__\s*\(',
    r'open\s*\([^)]*["\']\/[^)]*["\']',   # open('/...')
    r'eval\s*\(',
    r'exec\s*\(',
    r'compile\s*\(',
]
_DANGEROUS_RE = [re.compile(p) for p in _DANGEROUS]

_DOCKER_AVAILABLE: Optional[bool] = None


def _check_docker() -> bool:
    global _DOCKER_AVAILABLE
    if _DOCKER_AVAILABLE is None:
        try:
            result = subprocess.run(
                ['docker', 'info'], capture_output=True, timeout=5
            )
            _DOCKER_AVAILABLE = result.returncode == 0
        except Exception:
            _DOCKER_AVAILABLE = False
        logger.info(f'[sandbox] Docker: {"доступен" if _DOCKER_AVAILABLE else "недоступен"}')
    return _DOCKER_AVAILABLE


def _is_safe(code: str) -> Tuple[bool, str]:
    """Базовая проверка безопасности кода (без Docker)."""
    for pat in _DANGEROUS_RE:
        if pat.search(code):
            return False, f'Запрещённая конструкция: {pat.pattern[:40]}'
    try:
        ast.parse(code)
    except SyntaxError as e:
        return False, f'Синтаксическая ошибка: {e}'
    return True, ''


# ── Subprocess fallback ───────────────────────────────────────────

def _exec_subprocess(code: str, user_dir: str,
                     timeout: int = EXEC_TIMEOUT) -> Tuple[int, str, str]:
    """Выполняет код в отдельном процессе (без Docker)."""
    safe, reason = _is_safe(code)
    if not safe:
        return 1, '', f'[BLOCKED] {reason}'

    with tempfile.NamedTemporaryFile(mode='w', suffix='.py',
                                     dir=user_dir, delete=False) as f:
        f.write(code)
        tmp_path = f.name

    try:
        result = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True, text=True,
            timeout=timeout,
            cwd=user_dir,
            env={**os.environ, 'PYTHONPATH': user_dir},
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, '', f'Timeout ({timeout}s)'
    except Exception as e:
        return 1, '', str(e)
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


# ── Docker sandbox ────────────────────────────────────────────────

def _get_container_name(user_id: int) -> str:
    return f'autocoder-sandbox-{user_id}'


def _container_exists(user_id: int) -> bool:
    name = _get_container_name(user_id)
    result = subprocess.run(
        ['docker', 'ps', '-a', '--filter', f'name={name}', '--format', '{{.Names}}'],
        capture_output=True, text=True, timeout=10
    )
    return name in result.stdout


def _container_running(user_id: int) -> bool:
    name = _get_container_name(user_id)
    result = subprocess.run(
        ['docker', 'ps', '--filter', f'name={name}', '--format', '{{.Names}}'],
        capture_output=True, text=True, timeout=10
    )
    return name in result.stdout


def _start_container(user_id: int, user_dir: str) -> bool:
    """Запускает или создаёт Docker контейнер для пользователя."""
    name = _get_container_name(user_id)
    sandbox_dir = os.path.join(user_dir, 'sandbox')
    os.makedirs(sandbox_dir, exist_ok=True)

    if _container_running(user_id):
        return True

    if _container_exists(user_id):
        # Контейнер есть но остановлен — запускаем
        result = subprocess.run(
            ['docker', 'start', name],
            capture_output=True, timeout=30
        )
        return result.returncode == 0

    # Создаём новый контейнер
    cmd = [
        'docker', 'run', '-d',
        '--name', name,
        '--label', SANDBOX_LABEL,
        '--memory', CONTAINER_MEM,
        '--cpus', CONTAINER_CPU,
        '--network', 'none',       # изоляция сети
        '--read-only',             # readonly filesystem
        '--tmpfs', '/tmp:size=64m',
        '--tmpfs', '/workspace:size=128m',
        '-v', f'{sandbox_dir}:/workspace/data',  # только data rw
        '-w', '/workspace',
        '--user', '1000:1000',     # не root
        DOCKER_IMAGE,
        'sleep', 'infinity',       # держим контейнер живым
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        logger.error(f'[sandbox] Не удалось создать контейнер: {result.stderr}')
        return False
    logger.info(f'[sandbox] Контейнер создан: {name}')
    return True


def _exec_docker(user_id: int, code: str, user_dir: str,
                 timeout: int = EXEC_TIMEOUT) -> Tuple[int, str, str]:
    """Выполняет код в Docker контейнере пользователя."""
    name = _get_container_name(user_id)

    if not _start_container(user_id, user_dir):
        # Fallback на subprocess
        logger.warning('[sandbox] Docker недоступен, fallback subprocess')
        return _exec_subprocess(code, user_dir, timeout)

    # Пишем код во временный файл внутри sandbox
    tmp_name = f'exec_{int(time.time())}.py'
    sandbox_dir = os.path.join(user_dir, 'sandbox')
    code_path = os.path.join(sandbox_dir, tmp_name)

    with open(code_path, 'w') as f:
        f.write(code)

    try:
        result = subprocess.run(
            ['docker', 'exec', name, 'python', f'/workspace/data/{tmp_name}'],
            capture_output=True, text=True,
            timeout=timeout + 5,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        subprocess.run(['docker', 'exec', name, 'pkill', '-f', tmp_name],
                       capture_output=True, timeout=5)
        return 1, '', f'Timeout ({timeout}s)'
    except Exception as e:
        return 1, '', str(e)
    finally:
        try:
            os.unlink(code_path)
        except Exception:
            pass


def stop_container(user_id: int):
    """Останавливает контейнер пользователя."""
    if not _check_docker():
        return
    name = _get_container_name(user_id)
    subprocess.run(['docker', 'stop', name], capture_output=True, timeout=15)
    logger.info(f'[sandbox] Контейнер остановлен: {name}')


def remove_container(user_id: int):
    """Удаляет контейнер пользователя (например при удалении аккаунта)."""
    if not _check_docker():
        return
    name = _get_container_name(user_id)
    subprocess.run(['docker', 'rm', '-f', name], capture_output=True, timeout=15)
    logger.info(f'[sandbox] Контейнер удалён: {name}')


def install_package(user_id: int, package: str,
                    user_dir: str) -> Tuple[bool, str]:
    """Устанавливает pip-пакет в Docker контейнер."""
    if not _check_docker() or not _container_running(user_id):
        # Fallback: системная установка
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', package,
             '--break-system-packages', '--quiet'],
            capture_output=True, text=True, timeout=120
        )
        return result.returncode == 0, result.stdout + result.stderr

    name = _get_container_name(user_id)
    result = subprocess.run(
        ['docker', 'exec', name, 'pip', 'install', package, '--quiet'],
        capture_output=True, text=True, timeout=120
    )
    return result.returncode == 0, result.stdout + result.stderr


# ── Главная функция ───────────────────────────────────────────────

def execute_code(code: str, user_id: int, user_dir: str,
                 timeout: int = EXEC_TIMEOUT,
                 language: str = 'python') -> dict:
    """
    Выполняет код в изолированной среде.

    Returns:
        {
            'success': bool,
            'stdout': str,
            'stderr': str,
            'returncode': int,
            'mode': 'docker' | 'subprocess',
            'elapsed': float,
        }
    """
    start = time.time()

    if language != 'python':
        return {
            'success': False,
            'stdout': '',
            'stderr': f'Язык {language} пока не поддерживается в sandbox',
            'returncode': 1,
            'mode': 'none',
            'elapsed': 0,
        }

    if _check_docker():
        rc, out, err = _exec_docker(user_id, code, user_dir, timeout)
        mode = 'docker'
    else:
        rc, out, err = _exec_subprocess(code, user_dir, timeout)
        mode = 'subprocess'

    elapsed = time.time() - start
    return {
        'success':    rc == 0,
        'stdout':     out[:4000],
        'stderr':     err[:2000],
        'returncode': rc,
        'mode':       mode,
        'elapsed':    round(elapsed, 2),
    }


def format_result(result: dict) -> str:
    """Форматирует результат для Telegram."""
    icon  = '✅' if result['success'] else '❌'
    mode  = '🐳' if result['mode'] == 'docker' else '⚙️'
    parts = [f"{icon} {mode} Выполнено за {result['elapsed']}с"]

    if result['stdout']:
        out = result['stdout'][:1500]
        parts.append(f"<b>Output:</b>\n<pre>{out}</pre>")

    if result['stderr']:
        err = result['stderr'][:800]
        parts.append(f"<b>Stderr:</b>\n<pre>{err}</pre>")

    if not result['stdout'] and not result['stderr']:
        parts.append('(нет вывода)')

    return '\n'.join(parts)
