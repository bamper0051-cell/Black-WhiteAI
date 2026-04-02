# -*- coding: utf-8 -*-
"""
coder3/autofix.py — Autofix для AGENT_CODER3.

ИСПРАВЛЕНИЯ v2:
  1. Все раунды (round_0..N) сохраняются в workspace для включения в zip.
  2. Принимает workspace как обязательный параметр.
  3. Возвращает (fixed_code, stdout, stderr, success, rounds_count).
  4. Поддержка abort_flag.
  5. Вся логика работает через python_sandbox.run_code_string.
"""

import logging
from pathlib import Path
from typing import Optional

from aiogram import Bot

from python_sandbox import run_code_string, SandboxResult

logger = logging.getLogger(__name__)

MAX_ROUNDS = 5


async def run_autofix(
    bot: Bot,
    chat_id: int,
    original_code: str,
    original_error: str,
    workspace: Path,
    abort_flag_holder: Optional[object] = None,
    max_rounds: int = MAX_ROUNDS,
) -> tuple[str, str, str, bool, int]:
    """
    Цикл autofix: LLM исправляет код, sandbox проверяет.

    ИСПРАВЛЕНИЕ: все раунды сохраняются в workspace, попадут в финальный zip.

    Args:
        bot: Bot instance для прогресс-сообщений.
        chat_id: ID чата.
        original_code: исходный код с ошибкой.
        original_error: stderr исходного запуска.
        workspace: рабочая директория.
        abort_flag_holder: объект с .abort_flag (SessionState).
        max_rounds: максимум попыток.

    Returns:
        (final_code, stdout, stderr, success, rounds_used)
    """
    workspace.mkdir(parents=True, exist_ok=True)

    # Сохраняем оригинал
    (workspace / "round_0_original.py").write_text(original_code, encoding="utf-8")
    (workspace / "round_0_error.txt").write_text(original_error, encoding="utf-8")
    logger.info("Autofix started: workspace=%s, max_rounds=%d", workspace, max_rounds)

    code = original_code
    error = original_error

    for attempt in range(1, max_rounds + 1):
        # Проверяем флаг прерывания
        if abort_flag_holder and getattr(abort_flag_holder, "abort_flag", False):
            logger.info("Autofix aborted at round %d", attempt)
            await bot.send_message(chat_id, f"⛔ Autofix прерван на раунде {attempt}.")
            break

        await bot.send_message(chat_id, f"🔄 Autofix: раунд {attempt}/{max_rounds}...")

        # LLM исправление
        fixed = await _llm_fix(code, error)

        # Сохраняем раунд
        round_file = workspace / f"round_{attempt}.py"
        round_file.write_text(fixed, encoding="utf-8")

        # Запускаем sandbox
        result: SandboxResult = await run_code_string(
            fixed,
            workspace=workspace,
            filename=f"_autofix_run_{attempt}.py",
            abort_flag_holder=abort_flag_holder,
        )

        # Сохраняем вывод раунда
        (workspace / f"round_{attempt}_stdout.txt").write_text(result.stdout, encoding="utf-8")
        (workspace / f"round_{attempt}_stderr.txt").write_text(result.stderr, encoding="utf-8")

        logger.info("Round %d: ok=%s, rc=%d", attempt, result.ok, result.returncode)

        if result.ok:
            await bot.send_message(chat_id, f"✅ Autofix успешен на раунде {attempt}!")
            # Сохраняем финальный вариант
            (workspace / "solution_fixed.py").write_text(fixed, encoding="utf-8")
            return fixed, result.stdout, result.stderr, True, attempt

        code = fixed
        error = result.stderr

    # Все попытки провалились
    await bot.send_message(
        chat_id,
        f"⚠️ Autofix: все {max_rounds} попыток неудачны.\n"
        "Архив содержит все версии — проверьте вручную."
    )
    (workspace / "solution_fixed.py").write_text(code, encoding="utf-8")
    return code, "", error, False, max_rounds


async def _llm_fix(code: str, error: str) -> str:
    """LLM-исправление кода. Подключить реальный llm_client."""
    try:
        from llm_client import get_llm_client
        client = get_llm_client()
        prompt = (
            f"Исправь Python-код:\n```python\n{code[:4000]}\n```\n\n"
            f"Ошибка выполнения:\n{error[:1000]}\n\n"
            "Верни ТОЛЬКО исправленный Python-код без пояснений и markdown."
        )
        return await client.complete(prompt)
    except Exception as e:
        logger.error("LLM fix failed: %s", e)
        return code  # возвращаем оригинал если LLM недоступен
