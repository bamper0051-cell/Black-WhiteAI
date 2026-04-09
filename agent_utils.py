# -*- coding: utf-8 -*-
"""
agent_utils.py — Общий инструментарий для всех агентов AGENT_SMITH.

Единый модуль утилит: workspace, упаковка zip, отправка результата,
управление сессией. Все агенты используют эти функции — дублирование исключено.
"""

import os
import io
import uuid
import zipfile
import logging
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional

from aiogram import Bot
from aiogram.types import BufferedInputFile

logger = logging.getLogger(__name__)

# ─── Константы ─────────────────────────────────────────────────────────────
WORKSPACE_BASE = Path(os.getenv("WORKSPACE_BASE", "/tmp/agent_workspaces"))
MAX_ZIP_SIZE_BYTES = 50 * 1024 * 1024   # 50 МБ — лимит прямой отправки в Telegram


# ─── 1. Создание рабочей директории ────────────────────────────────────────

def create_workspace(chat_id: int, prefix: str = "task") -> Path:
    """
    Создаёт уникальную изолированную папку для текущей задачи.

    Путь: WORKSPACE_BASE / <chat_id> / <prefix>_<timestamp>_<uuid4[:8]>

    Returns:
        Path — абсолютный путь к созданной директории.
    """
    ts = datetime.utcnow().strftime("%H%M%S")
    uid = uuid.uuid4().hex[:8]
    workspace = WORKSPACE_BASE / str(chat_id) / f"{prefix}_{ts}_{uid}"
    workspace.mkdir(parents=True, exist_ok=True)
    logger.debug("Workspace created: %s", workspace)
    return workspace


# ─── 2. Сохранение output.txt ───────────────────────────────────────────────

def save_output(workspace: Path, stdout: str = "", stderr: str = "",
                extra: str = "") -> Path:
    """
    Сохраняет вывод выполнения кода в output.txt внутри workspace.

    Содержимое файла:
        === STDOUT ===
        ...
        === STDERR ===
        ...
        === NOTES ===
        ...  (если extra передан)

    Returns:
        Path к output.txt.
    """
    lines = []
    if stdout:
        lines += ["=== STDOUT ===", stdout.strip(), ""]
    if stderr:
        lines += ["=== STDERR ===", stderr.strip(), ""]
    if extra:
        lines += ["=== NOTES ===", extra.strip(), ""]

    output_path = workspace / "output.txt"
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


# ─── 3. Упаковка артефактов в ZIP ──────────────────────────────────────────

def pack_artifacts(
    workspace: Path,
    files: Optional[list[Path]] = None,
    output_text: str = "",
    zip_name: str = "result.zip",
) -> Path:
    """
    Упаковывает артефакты задачи в единый ZIP-архив.

    Логика:
      - Если files=None — берёт ВСЕ файлы из workspace рекурсивно.
      - output.txt создаётся автоматически, если output_text передан.
      - Пустые __pycache__ и .pyc пропускаются.

    Returns:
        Path к созданному zip-файлу.
    """
    if output_text:
        save_output(workspace, stdout=output_text)

    if files is None:
        files = [
            p for p in workspace.rglob("*")
            if p.is_file()
            and "__pycache__" not in p.parts
            and not p.suffix == ".pyc"
        ]

    zip_path = workspace.parent / zip_name
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for fp in files:
            arcname = fp.relative_to(workspace.parent)
            zf.write(fp, arcname)

    size_mb = zip_path.stat().st_size / 1024 / 1024
    logger.info("ZIP packed: %s (%.2f MB, %d files)", zip_path, size_mb, len(files))
    return zip_path


# ─── 4. Отправка ZIP-результата ─────────────────────────────────────────────

async def send_zip_result(
    bot: Bot,
    chat_id: int,
    zip_path: Path,
    caption: str = "✅ Задача выполнена",
    tunnel_url: Optional[str] = None,
) -> None:
    """
    Отправляет zip-архив пользователю.

    - Если архив <= 50 МБ — отправляет как файл напрямую.
    - Если больше — отправляет ссылку на туннель (tunnel_url) или предупреждение.
    """
    try:
        size = zip_path.stat().st_size
    except FileNotFoundError:
        await bot.send_message(chat_id, "⚠️ Архив не найден. Возможно, задача не создала файлов.")
        return

    if size <= MAX_ZIP_SIZE_BYTES:
        data = zip_path.read_bytes()
        doc = BufferedInputFile(data, filename=zip_path.name)
        await bot.send_document(chat_id, doc, caption=caption)
    else:
        size_mb = size / 1024 / 1024
        if tunnel_url:
            msg = (
                f"📦 Архив слишком большой ({size_mb:.1f} МБ).\n"
                f"Скачать: {tunnel_url}"
            )
        else:
            msg = (
                f"⚠️ Архив слишком большой ({size_mb:.1f} МБ) для отправки в Telegram.\n"
                "Свяжитесь с администратором для получения файла."
            )
        await bot.send_message(chat_id, msg)


# ─── 5. Удержание сессии активной ──────────────────────────────────────────

async def keep_session_alive(
    bot: Bot,
    chat_id: int,
    reply_markup=None,
) -> None:
    """
    После выполнения задачи переводит сессию в режим ожидания следующей.

    Отправляет сообщение с кнопками:
      📎 Добавить файлы  |  🔴 Завершить сессию

    Если reply_markup=None — импортирует стандартную клавиатуру из keyboards.py.
    """
    if reply_markup is None:
        try:
            from keyboards import get_session_wait_keyboard
            reply_markup = get_session_wait_keyboard()
        except ImportError:
            pass  # fallback: нет клавиатуры

    text = (
        "⏳ Сессия активна. Жду следующую задачу.\n\n"
        "Можете:\n"
        "• Написать новый запрос\n"
        "• 📎 Прикрепить файлы к следующей задаче\n"
        "• 🔴 Завершить сессию"
    )
    await bot.send_message(chat_id, text, reply_markup=reply_markup)


# ─── 6. Определение типа задачи ────────────────────────────────────────────

TASK_KEYWORDS = {
    "script": [
        "напиши код", "написать код", "сгенерируй код", "скрипт", "python",
        "сгенерируй", "генерируй", "сделай функцию", "реализуй",
        "паролей", "пароли", "генератор",
    ],
    "project": [
        "телеграм бот", "telegram bot", "парсер", "parser", "проект",
        "приложение", "сервис", "микросервис", "несколько файлов",
        "структура проекта", "напиши бот",
    ],
    "image": [
        "нарисуй", "нарисовать", "картинку", "изображение", "image",
        "picture", "generate image", "сгенерируй картинку",
        "анимация", "animation", "gif",
    ],
    "review": [
        "проверь код", "code review", "ревью", "найди ошибки", "что не так",
        "проверь файл",
    ],
    "analyze": [
        "проанализируй", "analyse", "analyze", "разбери", "объясни код",
    ],
}

def detect_task_type(text: str) -> str:
    """
    Определяет тип задачи по тексту запроса.

    Returns:
        Один из: 'script' | 'project' | 'image' | 'review' | 'analyze' | 'quick'
    """
    text_lower = text.lower()
    for task_type, keywords in TASK_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return task_type
    return "quick"  # fallback — быстрая задача


# ─── 7. Очистка workspace ───────────────────────────────────────────────────

def cleanup_workspace(workspace: Path, keep_zip: bool = True) -> None:
    """
    Удаляет рабочую директорию после отправки результата.
    Если keep_zip=True — zip в parent-папке не удаляется.
    """
    import shutil
    try:
        shutil.rmtree(workspace, ignore_errors=True)
        logger.debug("Workspace cleaned: %s", workspace)
    except Exception as e:
        logger.warning("Failed to clean workspace %s: %s", workspace, e)
