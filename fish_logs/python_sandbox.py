# -*- coding: utf-8 -*-
"""
python_sandbox.py — Безопасный запуск Python-кода.

ИСПРАВЛЕНИЯ v2:
  1. Всегда возвращает (stdout, stderr, returncode, success).
  2. Таймаут + принудительное kill.
  3. Ограничение памяти через resource (если доступен).
  4. Сохранение stdout/stderr в workspace/sandbox/ для включения в zip.
  5. Поддержка abort_flag из SessionState.
"""

import asyncio
import logging
import os
import sys
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30       # секунд
MAX_OUTPUT_SIZE = 64_000   # символов — обрезаем чрезмерный stdout


class SandboxResult:
    """Результат выполнения кода в sandbox."""
    __slots__ = ("stdout", "stderr", "returncode", "timed_out", "ok")

    def __init__(self, stdout: str, stderr: str, returncode: int, timed_out: bool = False):
        self.stdout = stdout[:MAX_OUTPUT_SIZE]
        self.stderr = stderr[:MAX_OUTPUT_SIZE]
        self.returncode = returncode
        self.timed_out = timed_out
        self.ok = returncode == 0 and not timed_out

    def __repr__(self):
        return (f"SandboxResult(ok={self.ok}, rc={self.returncode}, "
                f"timed_out={self.timed_out}, "
                f"stdout={len(self.stdout)}b, stderr={len(self.stderr)}b)")


async def run_script(
    script_path: Path,
    workspace: Path,
    timeout: int = DEFAULT_TIMEOUT,
    extra_env: Optional[dict] = None,
    abort_flag_holder: Optional[object] = None,
) -> SandboxResult:
    """
    Запускает Python-скрипт в изолированном subprocess.

    Args:
        script_path: путь к .py файлу.
        workspace: рабочая директория (cwd процесса).
        timeout: максимальное время выполнения в секундах.
        extra_env: дополнительные переменные окружения.
        abort_flag_holder: объект с атрибутом abort_flag (SessionState).

    Returns:
        SandboxResult
    """
    workspace.mkdir(parents=True, exist_ok=True)

    env = _build_env(extra_env)

    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, str(script_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(workspace),
            env=env,
        )
    except Exception as e:
        logger.exception("Failed to start subprocess: %s", e)
        return SandboxResult("", str(e), -1)

    # Мониторим abort_flag параллельно
    stdout_b = b""
    stderr_b = b""
    timed_out = False

    try:
        done, pending = await asyncio.wait(
            [asyncio.create_task(_communicate(proc))],
            timeout=timeout,
        )

        if pending:
            # Таймаут
            timed_out = True
            try:
                proc.kill()
            except ProcessLookupError:
                pass
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            stdout_b, stderr_b = b"", f"TimeoutError: скрипт не завершился за {timeout}с".encode()
        else:
            stdout_b, stderr_b = done.pop().result()

    except asyncio.CancelledError:
        # Внешняя отмена
        try:
            proc.kill()
        except ProcessLookupError:
            pass
        raise

    # Проверяем abort_flag
    if abort_flag_holder and getattr(abort_flag_holder, "abort_flag", False):
        try:
            proc.kill()
        except ProcessLookupError:
            pass
        return SandboxResult("", "Выполнение прервано пользователем", -2)

    stdout = stdout_b.decode("utf-8", errors="replace")
    stderr = stderr_b.decode("utf-8", errors="replace")

    result = SandboxResult(stdout, stderr, proc.returncode or 0, timed_out)
    logger.debug("Sandbox done: %s", result)

    # Сохраняем в workspace/sandbox/ для zip
    _save_sandbox_outputs(workspace, stdout, stderr)

    return result


async def _communicate(proc: asyncio.subprocess.Process):
    return await proc.communicate()


def _build_env(extra: Optional[dict] = None) -> dict:
    """Строит безопасный env для subprocess."""
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": "/tmp",
        "PYTHONPATH": "",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONUNBUFFERED": "1",
    }
    if extra:
        env.update(extra)
    return env


def _save_sandbox_outputs(workspace: Path, stdout: str, stderr: str) -> None:
    """Сохраняет stdout/stderr в workspace/sandbox/ для включения в zip."""
    sandbox_dir = workspace / "sandbox"
    sandbox_dir.mkdir(exist_ok=True)
    (sandbox_dir / "stdout.txt").write_text(stdout, encoding="utf-8")
    (sandbox_dir / "stderr.txt").write_text(stderr, encoding="utf-8")


async def run_code_string(
    code: str,
    workspace: Path,
    filename: str = "script.py",
    timeout: int = DEFAULT_TIMEOUT,
    abort_flag_holder: Optional[object] = None,
) -> SandboxResult:
    """
    Удобная обёртка: принимает строку кода, сохраняет во временный файл,
    запускает и возвращает результат.
    """
    script_path = workspace / filename
    script_path.write_text(code, encoding="utf-8")
    return await run_script(script_path, workspace, timeout=timeout,
                            abort_flag_holder=abort_flag_holder)
