# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, List
import re


@dataclass
class TaskInterpretation:
    user_goal: str
    task_type: str
    mode: str
    needs_internet: bool
    needs_files: bool
    needs_memory: bool
    needs_code: bool
    needs_tables: bool
    is_multi_step: bool
    complexity: str
    risk: str
    confidence: float
    hints: List[str]


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(n in text for n in needles)


def infer_mode(task_text: str, requested_mode: str = 'auto') -> str:
    if requested_mode and requested_mode != 'auto':
        return requested_mode
    text = (task_text or '').lower()
    if _contains_any(text, ('traceback', 'ошибка', 'exception', 'исправ', 'fix', 'bug', 'сломал', 'не работает', 'crash', 'stack trace')) and not _contains_any(text, ('что такое', 'what is', 'объясни', 'расскажи', 'почему')):
        return 'autofix'
    if _contains_any(text, ('обзор', 'review', 'ревью', 'audit', 'аудит', 'проверь код', 'анализ кода', 'оцени', 'разбери')):
        return 'review'
    if _contains_any(text, ('проект', 'project', 'структур', 'модул', 'архитект', 'рефактор', 'пересобери архив', 'zip', 'архив', 'регистрац', 'подключи', 'добавь в проект', 'разнеси')):
        return 'project'
    if _contains_any(text, ('sandbox', 'запусти', 'прогони', 'stdout', 'stderr', 'выполни код', 'тест', 'run this', 'smoke test')):
        return 'sandbox'
    return 'quick'


def interpret_task(task_text: str, requested_mode: str = 'auto') -> TaskInterpretation:
    text = (task_text or '').strip()
    low = text.lower()
    mode = infer_mode(text, requested_mode)

    question_signals = ('что ', 'что?', 'почему', 'зачем', 'как ', 'как?', 'в чем', 'в чём', 'объясни', 'расскажи', 'difference', 'why ')
    create_signals = ('напиши', 'создай', 'сделай', 'сгенер', 'реализуй', 'собери', 'добавь', 'построй', 'нарисуй', 'draw', 'generate', 'build', 'implement')
    media_signals = ('анимация', 'animation', 'матриц', 'matrix', 'изображен', 'image', 'картинк', 'video', 'видео', 'gif', 'canvas', 'pygame', 'terminal rain', 'snow', 'snowfall', 'снег', 'снеж')
    bug_signals = ('traceback', 'ошибка', 'exception', 'не работает', 'сломалось', 'bug', 'fix', 'исправь', 'stack trace')
    review_signals = ('review', 'ревью', 'проверь', 'проанализ', 'оцени', 'audit', 'разбери')
    doc_signals = ('pdf', 'doc', 'документ', 'архив', 'zip', 'readme', 'summary', 'отчёт', 'отчет')
    search_signals = ('найди', 'поиск', 'search', 'google', 'web', 'site', 'url', 'сайт')
    project_signals = ('проект', 'repo', 'репо', 'регистрац', 'структур', 'модул', 'архитект', 'подключи', 'пересобери', 'архив', 'zip')

    is_explainer = _contains_any(low, question_signals) and _contains_any(low, ('что такое', 'what is', 'почему', 'как работает', 'объясни', 'расскажи'))
    creative_request = _contains_any(low, media_signals) and (_contains_any(low, create_signals) or mode == 'quick' or not _contains_any(low, question_signals))

    if (_contains_any(low, bug_signals) and not is_explainer) or mode == 'autofix':
        task_type = 'bug_fix'
    elif creative_request:
        task_type = 'creative_code'
    elif _contains_any(low, project_signals) or mode == 'project':
        task_type = 'project_task'
    elif _contains_any(low, review_signals) or mode == 'review':
        task_type = 'review'
    elif _contains_any(low, doc_signals):
        task_type = 'document_work'
    elif _contains_any(low, search_signals):
        task_type = 'search'
    elif _contains_any(low, question_signals) or is_explainer:
        task_type = 'question'
    elif _contains_any(low, create_signals) or mode in ('quick', 'sandbox'):
        task_type = 'code_generation'
    else:
        task_type = 'code_generation' if mode == 'quick' else 'question'

    needs_internet = _contains_any(low, ('интернет', 'web', 'поиск', 'найди', 'site', 'url', 'api', 'товар', 'цена', 'docs', 'github'))
    needs_files = _contains_any(low, ('файл', 'архив', 'zip', 'pdf', 'doc', 'проект', 'repo', 'readme', 'bot.py', '.py', 'код из файла')) or task_type in ('project_task', 'document_work', 'bug_fix')
    needs_memory = _contains_any(low, ('память', 'контекст', 'история', 'remember', 'session'))
    needs_code = task_type in ('code_generation', 'creative_code', 'project_task', 'bug_fix') or _contains_any(low, ('код', 'python', 'бот', 'script', 'patch'))
    needs_tables = _contains_any(low, ('таблиц', 'csv', 'xlsx', 'json', 'dataframe'))
    is_multi_step = len(re.findall(r'и|then|после|потом|затем', low)) >= 1 or mode in ('project', 'autofix') or task_type in ('project_task', 'document_work')

    if task_type in ('project_task', 'document_work') or mode == 'project':
        complexity = 'high'
    elif task_type in ('bug_fix', 'creative_code') or mode in ('autofix', 'sandbox', 'review'):
        complexity = 'medium'
    else:
        complexity = 'low'

    risk = 'low'
    if needs_internet or mode in ('autofix', 'project', 'sandbox') or task_type in ('bug_fix', 'project_task'):
        risk = 'medium'
    if _contains_any(low, ('удали', 'delete', 'rm ', 'drop database', 'format', 'перезапиши всё', 'truncate', 'wipe')):
        risk = 'high'

    hints: List[str] = []
    if needs_internet:
        hints.append('Task may require internet or API-backed retrieval.')
    if needs_files:
        hints.append('Task references files, repository artifacts, or packaged outputs.')
    if task_type == 'creative_code':
        hints.append('Prefer generating runnable creative code, not a plain text answer.')
    if mode == 'autofix':
        hints.append('Prefer analyze → edit → validate → retry cycle.')
    if mode == 'project':
        hints.append('Prefer scaffold + package deliverable workflow.')
    if mode == 'review':
        hints.append('Prefer read-only diagnostics and recommendations.')

    confidence = 0.92 if requested_mode != 'auto' else 0.90
    return TaskInterpretation(
        user_goal=text[:500],
        task_type=task_type,
        mode=mode,
        needs_internet=needs_internet,
        needs_files=needs_files,
        needs_memory=needs_memory,
        needs_code=needs_code,
        needs_tables=needs_tables,
        is_multi_step=is_multi_step,
        complexity=complexity,
        risk=risk,
        confidence=confidence,
        hints=hints,
    )


def _select_tools(mode: str, interpretation: TaskInterpretation) -> List[str]:
    tools = ['meta.interpret_task', 'meta.plan']
    if interpretation.needs_files:
        tools.append('files.read')
    if interpretation.needs_code:
        tools.append('code.check')
    if mode in ('quick', 'project'):
        tools.extend(['files.create', 'code.scaffold'])
    if interpretation.task_type == 'creative_code':
        tools.extend(['code.template', 'code.package'])
    if mode == 'autofix':
        tools.extend(['files.read', 'code.patch', 'code.validate', 'code.retry'])
    if mode == 'review':
        tools.extend(['code.review', 'output.format'])
    if mode == 'sandbox':
        tools.extend(['code.sandbox', 'code.observe'])
    if interpretation.needs_internet:
        tools.append('search.web')
    return list(dict.fromkeys(tools))


def _build_steps(mode: str, interpretation: TaskInterpretation) -> List[str]:
    steps = [
        'Interpret user intent and classify task type',
        'Build execution plan and pick tools',
    ]
    if interpretation.needs_files:
        steps.append('Collect file/repo observations required for the task')
    if mode == 'quick':
        if interpretation.task_type == 'creative_code':
            steps.extend([
                'Generate runnable creative-code scaffold matching the requested effect',
                'Validate syntax and package artifacts',
            ])
        else:
            steps.extend([
                'Generate direct coder-flow scaffold or code draft',
                'Validate syntax and package artifacts',
            ])
    elif mode == 'autofix':
        steps.extend([
            'Extract code / traceback and build bug hypothesis',
            'Apply safe fix candidates and re-validate',
            'Retry with fallback heuristics if the first fix fails',
        ])
    elif mode == 'project':
        steps.extend([
            'Analyze project request and create deliverable scaffold',
            'Generate packageable artifact set',
            'Validate structure and prepare zip bundle',
        ])
    elif mode == 'review':
        steps.extend([
            'Inspect code/document signals',
            'Synthesize findings, risks, and next actions',
        ])
    elif mode == 'sandbox':
        steps.extend([
            'Run code in sandbox and collect observations',
            'Synthesize runtime signals and validation status',
        ])
    steps.append('Return structured report and final answer')
    return steps


def build_plan(task_text: str, requested_mode: str = 'auto', role: str = 'user', dry_run: bool = False) -> Dict:
    interpretation = interpret_task(task_text, requested_mode=requested_mode)
    return {
        'skill': 'agent_coder3',
        'mode': interpretation.mode,
        'role': role,
        'dry_run': dry_run,
        'risk': interpretation.risk,
        'complexity': interpretation.complexity,
        'interpretation': asdict(interpretation),
        'steps': _build_steps(interpretation.mode, interpretation),
        'tools': _select_tools(interpretation.mode, interpretation),
    }
