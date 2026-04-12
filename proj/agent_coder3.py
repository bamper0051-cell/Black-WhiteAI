# -*- coding: utf-8 -*-
"""AGENT_CODER3 — гибридный агент-кодер.
Мозг: orchestration / planning / reporting в стиле BlackBugsAI.
Руки: более прямой coder-flow в стиле automuvie_v4.4.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from coder3.engine import run_agent_coder3 as _run_engine
from coder3.reporting import format_report_text

CODER3_MODES = {
    'quick': '⚡ Быстрый код',
    'autofix': '🔧 Автофикс',
    'project': '🗂 Проект',
    'review': '🔍 Review',
    'sandbox': '🧪 Sandbox',
}


def render_coder3_welcome(provider: str, model: str) -> str:
    return (
        '🛠 <b>Агент-кодер 3</b> — обновлённый гибридный режим\n\n'
        'Пайплайн:\n'
        '1. Interpretation\n'
        '2. Planning\n'
        '3. Tool Selection\n'
        '4. Tool Execution\n'
        '5. Observation\n'
        '6. Reasoning / Synthesis\n'
        '7. Validation\n'
        '8. Final Response\n\n'
        '🧠 <b>Мозг:</b> routing, план, риск, отчёт, state\n'
        '🧰 <b>Руки:</b> scaffold, review, autofix, sandbox, package\n\n'
        'Режимы:\n'
        '• ⚡ Быстрый код\n'
        '• 🔧 Автофикс\n'
        '• 🗂 Проект\n'
        '• 🔍 Review\n'
        '• 🧪 Sandbox\n\n'
        'Модель: <b>{} / {}</b>'
    ).format(provider, model)


def build_coder3_menu(btn: Callable[..., Any], kb: Callable[..., Any], back_btn: Callable[..., Any],
                      back_target: str = 'menu_agent'):
    return kb(
        [btn('⚡ Быстрый код', 'coder3:quick'), btn('🔧 Автофикс', 'coder3:autofix')],
        [btn('🗂 Проект', 'coder3:project'), btn('🔍 Review', 'coder3:review')],
        [btn('🧪 Sandbox', 'coder3:sandbox')],
        [back_btn(back_target)],
    )


def render_mode_prompt(mode: str) -> str:
    prompts = {
        'quick': '⚡ <b>Быстрый код</b>\n\nОпиши, что написать: скрипт, функцию, мини-бота, модуль или scaffold.',
        'autofix': '🔧 <b>Автофикс</b>\n\nПришли код, traceback или текст ошибки. Пайплайн: analyze → hypothesis → patch → validate → retry.',
        'project': '🗂 <b>Проект</b>\n\nОпиши задачу по проекту: новая фича, переразбор структуры, пересборка архива, модульная интеграция.',
        'review': '🔍 <b>Review</b>\n\nПришли код или описание проекта — агент соберёт находки, риски и следующие шаги.',
        'sandbox': '🧪 <b>Sandbox</b>\n\nПришли Python-код. Агент прогонит синтаксис, выполнит sandbox и вернёт stdout/stderr.',
    }
    return prompts.get(mode, 'Опиши задачу для Агент-кодера 3.')


def handle_coder3_mode_select(chat_id: int,
                              mode: str,
                              wait_state: Dict[int, str],
                              send_message: Callable[..., Any],
                              kb: Callable[..., Any],
                              btn: Callable[..., Any]):
    wait_state[chat_id] = 'coder3_input:' + mode
    send_message(
        render_mode_prompt(mode),
        chat_id,
        reply_markup=kb([btn('❌ Отмена', 'agent_code3_start')])
    )


def run_agent_coder3(chat_id: int,
                     text: str,
                     mode: str,
                     on_status: Optional[Callable[[str], Any]] = None,
                     send_message: Optional[Callable[..., Any]] = None,
                     send_document: Optional[Callable[..., Any]] = None,
                     project_root: str = '.') -> Dict[str, Any]:
    if on_status:
        on_status('🧠 AGENT_CODER3: interpretation → planning → execution...')
    result = _run_engine(
        task_text=text,
        mode=mode,
        chat_id=chat_id,
        role='user',
        dry_run=False,
        project_root=project_root,
    )
    if on_status:
        on_status('🧠 AGENT_CODER3 завершил execution, validation и packaging.')
    if send_message:
        send_message(format_report_text(result), chat_id)
    return result
