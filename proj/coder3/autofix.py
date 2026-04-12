# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Dict, List

from .tools_adapter import Coder3ToolAdapter


COMMON_FIX_HINTS = {
    'unexpected eof while parsing': 'Похоже, не закрыта скобка, кавычка или блок.',
    'expected an indented block': 'После def/if/for/while нужен отступленный блок.',
    'invalid syntax': 'Синтаксис сломан: проверь двоеточия, скобки и лишние символы.',
    'nameerror': 'В коде используется имя, которое не объявлено.',
    'modulenotfounderror': 'Не хватает пакета или импорт указывает не туда.',
}


def _repair_code(code: str, error: Dict) -> str:
    lines = code.splitlines()
    line_no = max((error.get('line') or 1) - 1, 0)
    error_line = lines[line_no] if line_no < len(lines) else ''

    if error_line.strip().startswith(('def ', 'if ', 'elif ', 'for ', 'while ', 'class ', 'try', 'except', 'else')) and not error_line.rstrip().endswith(':'):
        lines[line_no] = error_line.rstrip() + ':'
    if '\t' in code:
        lines = [ln.replace('\t', '    ') for ln in lines]
    if error.get('text', '').count('"') % 2 == 1:
        lines[line_no] = error_line + '"'
    if error.get('text', '').count("'") % 2 == 1:
        lines[line_no] = error_line + "'"
    fixed = '\n'.join(lines)
    if fixed == code:
        fixed = '# FIXME: manual review required\n' + code
    return fixed


def _extract_candidate(task_text: str, adapter: Coder3ToolAdapter) -> str:
    blocks = adapter.extract_python_blocks(task_text)
    if blocks:
        return blocks[0]
    tb = adapter.extract_traceback(task_text)
    if tb:
        return '# Traceback captured\n' + tb + '\n'
    return task_text.strip()


def run_autofix(task_text: str, adapter: Coder3ToolAdapter, max_rounds: int = 3) -> Dict:
    candidate = _extract_candidate(task_text, adapter)
    adapter.create_file('autofix/original_input.txt', task_text)
    history: List[Dict] = []

    for round_no in range(1, max_rounds + 1):
        check = adapter.check_python(candidate)
        history.append({'round': round_no, 'check': check})
        if check['ok']:
            adapter.create_file('autofix/fixed_candidate.py', candidate)
            package = adapter.package_workspace('autofix_bundle.zip')
            return {
                'ok': True,
                'summary': f'Автофикс завершён за {round_no} итерац.',
                'details': {'history': history, 'package': package},
            }
        candidate = _repair_code(candidate, check)
        adapter.create_file(f'autofix/round_{round_no}.py', candidate)

    final_check = adapter.check_python(candidate)
    hint = COMMON_FIX_HINTS.get(final_check.get('error', '').lower().split('(')[0], 'Нужен живой контекст проекта и traceback.')
    package = adapter.package_workspace('autofix_bundle_failed.zip')
    return {
        'ok': False,
        'summary': 'Автофикс сделал безопасные попытки, но ручной доразбор ещё нужен.',
        'details': {'history': history, 'final': final_check, 'hint': hint, 'package': package},
    }
