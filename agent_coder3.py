# -*- coding: utf-8 -*-
"""
agent_coder3.py — AGENT_CODER3 (Coder3).

ИСПРАВЛЕНИЯ v2:
  1. Все режимы (quick, project, sandbox, review, autofix) ВСЕГДА создают zip.
  2. sandbox: stdout/stderr → output.txt → zip.
  3. quick без sandbox: zip с пометкой «smoke-run не выполнялся».
  4. project: структура → zip (раньше только на диске).
  5. autofix: все раунды сохраняются, финальный zip включает ВСЕ попытки.
  6. Сессия не закрывается — делегирует agent_session.
"""

import asyncio
import logging
import re
import json
import sys
from pathlib import Path
from typing import Optional

from aiogram import Bot

from agent_utils import create_workspace, pack_artifacts, save_output
from agent_session import SessionState, register_agent

logger = logging.getLogger(__name__)

MAX_AUTOFIX_ROUNDS = 5
SANDBOX_TIMEOUT = 30  # секунд


# ─── Регистрация ─────────────────────────────────────────────────────────────

@register_agent("image")
async def run_image_task(bot: Bot, state: SessionState):
    """Генерация изображений / анимаций — режим quick с matplotlib/PIL."""
    return await _run_coder3(bot, state, mode="quick")

# Остальные типы подхватываются chat_agent; coder3 — специализированный агент.
# Можно перерегистрировать: @register_agent("script") etc.


# ─── Главный диспетчер ───────────────────────────────────────────────────────

async def _run_coder3(bot: Bot, state: SessionState, mode: str = None) -> tuple[Path, str]:
    """
    Определяет режим и запускает coder3 pipeline.
    """
    workspace = state.workspace or create_workspace(state.chat_id, "coder3")
    state.workspace = workspace

    task = state.task_text
    if mode is None:
        mode = _detect_coder3_mode(task)

    logger.info("Coder3 mode=%s for task: %s", mode, task[:60])

    if mode == "project":
        return await _run_project(bot, state, workspace)
    elif mode == "review":
        return await _run_review(bot, state, workspace)
    elif mode == "sandbox":
        return await _run_sandbox_mode(bot, state, workspace)
    else:
        # quick — генерация + попытка запуска
        return await _run_quick(bot, state, workspace)


def _detect_coder3_mode(text: str) -> str:
    text_lower = text.lower()
    if any(k in text_lower for k in ["проект", "project", "структур", "несколько файлов"]):
        return "project"
    if any(k in text_lower for k in ["проверь", "review", "ревью", "найди ошибки"]):
        return "review"
    if any(k in text_lower for k in ["запусти", "выполни", "sandbox"]):
        return "sandbox"
    return "quick"


# ─── Режим quick ─────────────────────────────────────────────────────────────

async def _run_quick(bot: Bot, state: SessionState, workspace: Path) -> tuple[Path, str]:
    """
    Генерация кода + smoke-run (если не GUI/bot).
    ВСЕГДА возвращает zip.
    """
    chat_id = state.chat_id
    task = state.task_text

    await bot.send_message(chat_id, "⚡ Quick mode: генерирую код...")

    code = await _llm_generate(task, mode="quick", context_files=state.files)
    script_path = workspace / "solution.py"
    script_path.write_text(code, encoding="utf-8")

    # Проверяем: это GUI или бот — smoke-run не запускаем
    is_gui_or_bot = _is_gui_or_bot_code(code)

    if is_gui_or_bot:
        note = "ℹ️ Smoke-run пропущен: обнаружен GUI/бот-код (tkinter/aiogram/PyQt)."
        save_output(workspace, extra=note)
        await bot.send_message(chat_id, note)
        zip_path = pack_artifacts(workspace, zip_name="quick_result.zip")
        return zip_path, "✅ Код сгенерирован (smoke-run не выполнялся — GUI/бот)"

    # Запускаем smoke-run
    await bot.send_message(chat_id, "▶️ Smoke-run...")
    stdout, stderr, ok = await _sandbox_run(script_path, workspace)

    if not ok:
        await bot.send_message(chat_id, "🔧 Autofix...")
        script_path, stdout, stderr, ok = await _autofix(bot, state, workspace, code, stderr)

    save_output(workspace, stdout=stdout, stderr=stderr,
                extra="✅ OK" if ok else "⚠️ Завершено с ошибками")
    zip_path = pack_artifacts(workspace, zip_name="quick_result.zip")
    caption = "✅ Quick: выполнено" if ok else "⚠️ Quick: ошибки (см. output.txt)"
    return zip_path, caption


def _is_gui_or_bot_code(code: str) -> bool:
    """Проверяет, содержит ли код GUI/bot-импорты."""
    gui_markers = [
        "import tkinter", "from tkinter", "import PyQt", "from PyQt",
        "import wx", "import kivy", "from kivy",
        "import aiogram", "from aiogram", "import telebot",
        "import discord", "from discord",
    ]
    return any(m in code for m in gui_markers)


# ─── Режим project ────────────────────────────────────────────────────────────

async def _run_project(bot: Bot, state: SessionState, workspace: Path) -> tuple[Path, str]:
    """
    Генерирует структуру проекта и упаковывает в zip.
    ИСПРАВЛЕНИЕ: раньше файлы оставались на диске без zip.
    """
    chat_id = state.chat_id
    task = state.task_text

    await bot.send_message(chat_id, "📐 Проектирую структуру...")

    plan_raw = await _llm_generate(task, mode="project", context_files=state.files)

    # Парсим JSON план
    try:
        plan_raw_clean = re.sub(r"```json|```", "", plan_raw).strip()
        plan = json.loads(plan_raw_clean)
        if not isinstance(plan, list):
            raise ValueError("Not a list")
    except (json.JSONDecodeError, ValueError):
        logger.warning("Project plan parse failed, treating as single file")
        plan = [{"path": "main.py", "content": plan_raw}]

    await bot.send_message(chat_id, f"📂 Создаю {len(plan)} файлов...")

    created = []
    for item in plan:
        rel_path = item.get("path", "file.py")
        content = item.get("content", "# empty")
        fp = workspace / rel_path
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content, encoding="utf-8")
        created.append(fp)

    # README если не создан
    readme = workspace / "README.md"
    if not any(p.name == "README.md" for p in created):
        readme.write_text(
            f"# {task[:60]}\n\nАвтоматически сгенерированный проект.\n\n"
            f"## Файлы\n" + "\n".join(f"- `{p.relative_to(workspace)}`" for p in created),
            encoding="utf-8"
        )
        created.append(readme)

    # ВСЕГДА упаковываем zip
    zip_path = pack_artifacts(workspace, files=created, zip_name="project.zip")
    return zip_path, f"✅ Проект создан: {len(created)} файлов"


# ─── Режим review ─────────────────────────────────────────────────────────────

async def _run_review(bot: Bot, state: SessionState, workspace: Path) -> tuple[Path, str]:
    """Code review загруженных файлов."""
    chat_id = state.chat_id

    if not state.files:
        await bot.send_message(chat_id, "⚠️ Нет файлов для ревью. Приложите код.")
        # Возвращаем пустой zip
        save_output(workspace, extra="Файлы не предоставлены.")
        zip_path = pack_artifacts(workspace, zip_name="review_empty.zip")
        return zip_path, "⚠️ Ревью не выполнено — нет файлов"

    await bot.send_message(chat_id, "🔍 Анализирую код...")

    combined = ""
    for fp in state.files:
        try:
            combined += f"\n\n## {fp.name}\n```python\n{fp.read_text(encoding='utf-8', errors='replace')[:4000]}\n```"
        except Exception:
            pass

    review = await _llm_generate(
        f"Выполни code review следующего кода:\n{combined}",
        mode="review"
    )

    report_path = workspace / "review_report.md"
    report_path.write_text(f"# Code Review Report\n\n{review}", encoding="utf-8")

    zip_path = pack_artifacts(workspace, zip_name="review.zip")
    return zip_path, "✅ Code Review выполнен"


# ─── Режим sandbox (явный запрос выполнения кода) ────────────────────────────

async def _run_sandbox_mode(bot: Bot, state: SessionState, workspace: Path) -> tuple[Path, str]:
    """Запуск предоставленных файлов в sandbox."""
    chat_id = state.chat_id

    script_path = None
    for fp in state.files:
        if fp.suffix == ".py":
            script_path = fp
            break

    if script_path is None:
        # Генерируем код и сразу запускаем
        return await _run_quick(bot, state, workspace)

    await bot.send_message(chat_id, f"▶️ Запускаю {script_path.name}...")
    stdout, stderr, ok = await _sandbox_run(script_path, workspace)

    if not ok:
        await bot.send_message(chat_id, "🔧 Ошибка — запускаю autofix...")
        code = script_path.read_text(encoding="utf-8", errors="replace")
        script_path, stdout, stderr, ok = await _autofix(bot, state, workspace, code, stderr)

    # ИСПРАВЛЕНИЕ: всегда сохраняем output.txt + zip
    save_output(workspace, stdout=stdout, stderr=stderr)
    zip_path = pack_artifacts(workspace, zip_name="sandbox_result.zip")
    caption = "✅ Sandbox: выполнено" if ok else "⚠️ Sandbox: ошибки (см. output.txt)"
    return zip_path, caption


# ─── Autofix ─────────────────────────────────────────────────────────────────

async def _autofix(
    bot: Bot,
    state: SessionState,
    workspace: Path,
    original_code: str,
    original_error: str,
) -> tuple[Path, str, str, bool]:
    """
    ИСПРАВЛЕНИЕ: сохраняет все раунды исправления.
    Все файлы round_N.py попадут в финальный zip через workspace.
    """
    chat_id = state.chat_id
    code = original_code
    error = original_error

    (workspace / "round_0_original.py").write_text(code, encoding="utf-8")
    (workspace / "round_0_error.txt").write_text(error, encoding="utf-8")

    for i in range(1, MAX_AUTOFIX_ROUNDS + 1):
        if state.abort_flag:
            break

        await bot.send_message(chat_id, f"🔄 Autofix раунд {i}/{MAX_AUTOFIX_ROUNDS}...")

        fixed = await _llm_fix(code, error)
        round_file = workspace / f"round_{i}.py"
        round_file.write_text(fixed, encoding="utf-8")

        stdout, stderr, ok = await _sandbox_run(round_file, workspace)

        (workspace / f"round_{i}_output.txt").write_text(
            f"STDOUT:\n{stdout}\nSTDERR:\n{stderr}", encoding="utf-8"
        )

        if ok:
            await bot.send_message(chat_id, f"✅ Исправлено на раунде {i}")
            final = workspace / "solution_fixed.py"
            final.write_text(fixed, encoding="utf-8")
            return final, stdout, stderr, True

        code, error = fixed, stderr

    final = workspace / "solution_fixed.py"
    final.write_text(code, encoding="utf-8")
    return final, "", error, False


# ─── Sandbox runner ──────────────────────────────────────────────────────────

async def _sandbox_run(
    script_path: Path,
    workspace: Path,
    timeout: int = SANDBOX_TIMEOUT,
) -> tuple[str, str, bool]:
    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, str(script_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(workspace),
        )
        try:
            out_b, err_b = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            return "", f"TimeoutError: превышено {timeout}с", False

        stdout = out_b.decode("utf-8", errors="replace")
        stderr = err_b.decode("utf-8", errors="replace")
        return stdout, stderr, proc.returncode == 0

    except Exception as e:
        return "", str(e), False


# ─── LLM-вызовы (подключить реальный клиент) ─────────────────────────────────

async def _llm_generate(task: str, mode: str = "quick", context_files: list = None) -> str:
    from llm_client import get_llm_client
    client = get_llm_client()

    ctx = ""
    if context_files:
        for fp in (context_files or []):
            try:
                ctx += f"\n# {fp.name}:\n{fp.read_text(encoding='utf-8', errors='replace')[:3000]}"
            except Exception:
                pass

    if mode == "project":
        prompt = (
            f"Создай структуру Python-проекта для: {task}\n{ctx}\n"
            "Верни JSON: [{\"path\": \"...\", \"content\": \"...\"}]. Только JSON."
        )
    elif mode == "review":
        prompt = f"Code review:\n{task}"
    else:
        prompt = (
            f"Напиши Python-код для: {task}\n{ctx}\n"
            "Только код, без markdown-блоков."
        )
    return await client.complete(prompt)


async def _llm_fix(code: str, error: str) -> str:
    from llm_client import get_llm_client
    client = get_llm_client()
    prompt = (
        f"Исправь код:\n```python\n{code[:3000]}\n```\n"
        f"Ошибка: {error[:1000]}\n"
        "Верни только исправленный код."
    )
    return await client.complete(prompt)
