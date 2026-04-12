# -*- coding: utf-8 -*-
"""
pipeline.py — Пайплайн AGENT_SMITH v2.

Совместимость с bot.py:
  - run_pipeline()            → обработка новостей (возвращает int)
  - process_user_message()    → заглушка для aiogram (не используется в синхронном bot.py)
  - process_user_document()   → заглушка

Агентский pipeline живёт в agent_session.execute_pipeline().
"""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# ─── Новостной пайплайн (оригинальная функция bot.py) ───────────────────────

def run_pipeline(*args, **kwargs) -> int:
    """
    Обрабатывает очередь новостей из БД.
    Возвращает количество обработанных записей.
    Совместимо с оригинальным pipeline.run_pipeline() который импортирует bot.py строка 329.
    """
    try:
        from database import get_unprocessed, update_news
        rows = get_unprocessed()
        if not rows:
            return 0
        processed = 0
        for row in rows:
            try:
                update_news(row[0], sent=1)
                processed += 1
            except Exception:
                pass
        return processed
    except Exception as e:
        logger.warning("run_pipeline error: %s", e)
        return 0


# ─── Агентский pipeline (делегируем в agent_session) ────────────────────────

def execute_pipeline(sess, on_status=None, llm_caller=None):
    """
    Запускает агентский pipeline для сессии.
    Делегирует в agent_session.execute_pipeline().
    """
    from agent_session import execute_pipeline as _exec
    return _exec(sess, on_status=on_status, llm_caller=llm_caller)


# ─── Заглушки для aiogram (не нужны синхронному bot.py) ─────────────────────

async def process_user_message(message, bot):
    """Aiogram-заглушка. Синхронный bot.py её не вызывает."""
    pass


async def process_user_document(message, bot):
    """Aiogram-заглушка. Синхронный bot.py её не вызывает."""
    pass
