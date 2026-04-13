# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Dict, Iterable


def _safe(text: str) -> str:
    return str(text).replace('<', '&lt;').replace('>', '&gt;')


def _iter_lines(values: Iterable[str]) -> list[str]:
    return [f'• {_safe(v)}' for v in values if v]


def format_report_text(result: Dict) -> str:
    tools = ', '.join(result.get('tools', []) or ['—'])
    artifacts = result.get('artifacts', []) or []
    failed = result.get('failed', 0)
    interpretation = result.get('interpretation') or {}
    validation = result.get('validation') or {}
    observations = result.get('observations') or []
    details = result.get('details') or {}

    lines = [
        '🧠 <b>AGENT_CODER3</b>',
        f'Режим: <code>{_safe(result.get("mode", "unknown"))}</code>',
        'Skill: <code>agent_coder3</code>',
        '',
        '<b>Interpretation</b>',
        f'• task_type: <code>{_safe(interpretation.get("task_type", "unknown"))}</code>',
        f'• complexity: <code>{_safe(interpretation.get("complexity", "unknown"))}</code>',
        f'• risk: <code>{_safe(interpretation.get("risk", "unknown"))}</code>',
        f'• internet/files/code: <code>{interpretation.get("needs_internet", False)}/{interpretation.get("needs_files", False)}/{interpretation.get("needs_code", False)}</code>',
        '',
        'План:',
    ]
    for idx, step in enumerate(result.get('steps', []), 1):
        lines.append(f'{idx}. {_safe(step)}')
    lines += [
        '',
        'Итог:',
        f'• tools: {_safe(tools)}',
        f'• changes: {result.get("changes", 0)}',
        f'• artifacts: {len(artifacts)}',
        f'• failed: {failed}',
        f'• summary: {_safe(result.get("summary", "—"))}',
        '',
        '<b>Validation</b>',
        f'• ok: <code>{validation.get("ok", False)}</code>',
        f'• checks: <code>{validation.get("checks", 0)}</code>',
    ]
    if validation.get('warnings'):
        lines += ['• warnings:'] + _iter_lines(validation.get('warnings', []))
    if artifacts:
        lines += ['', '<b>Артефакты:</b>']
        for item in artifacts[:12]:
            lines.append(f'• <code>{_safe(item)}</code>')
    if observations:
        lines += ['', '<b>Observation</b>']
        for obs in observations[:6]:
            stage = obs.get('stage', 'stage')
            payload = obs.get('payload', {})
            if isinstance(payload, dict):
                preview = ', '.join(f'{k}={v}' for k, v in list(payload.items())[:3])
            else:
                preview = str(payload)
            lines.append(f'• <code>{_safe(stage)}</code>: {_safe(preview)}')
    if details.get('report', {}).get('findings'):
        lines += ['', '<b>Ключевые находки</b>'] + _iter_lines(details['report'].get('findings', []))
    if details.get('report', {}).get('risks'):
        lines += ['', '<b>Риски</b>'] + _iter_lines(details['report'].get('risks', []))
    runtime = details.get('runtime') or {}
    if runtime.get('stdout'):
        lines += ['', '<b>stdout:</b>', f'<pre>{_safe(str(runtime["stdout"])[:1200])}</pre>']
    if runtime.get('stderr'):
        lines += ['', '<b>stderr:</b>', f'<pre>{_safe(str(runtime["stderr"])[:1200])}</pre>']
    return '\n'.join(lines)
