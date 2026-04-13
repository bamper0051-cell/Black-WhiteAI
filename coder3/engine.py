# -*- coding: utf-8 -*-
"""
coder3/engine.py — Исполнительный движок для autofix / review / sandbox.
quick и project теперь идут через АГЕНТ_СМИТ (agent_coder3.py).
"""
from __future__ import annotations

from typing import Dict, Optional

from .autofix import run_autofix
from .modes import run_project_mode, run_quick_mode, run_review_mode, run_sandbox_mode
from .planner_adapter import build_plan
from .tools_adapter import Coder3ToolAdapter


def _validate_result(adapter: Coder3ToolAdapter, payload: Dict) -> Dict:
    warnings = []
    for artifact in adapter.artifacts:
        if artifact.endswith('.json'):
            text = adapter.read_project_text(artifact) if not artifact.startswith('workspace/') else ''
            if text:
                valid = adapter.validate_json(text)
                if not valid['ok']:
                    warnings.append(f'Invalid JSON in {artifact}: {valid["error"]}')
        if artifact.endswith('.zip'):
            import os
            if not (adapter.project_root / artifact).exists() and not (adapter.workspace / artifact).exists():
                # try absolute path
                if not os.path.exists(str(artifact)):
                    warnings.append(f'Zip artifact missing: {artifact}')
    if not payload.get('ok', False):
        warnings.append('Mode returned non-ok result.')
    return {'ok': not warnings, 'checks': len(adapter.artifacts), 'warnings': warnings}


def _fallback_payload(task_text: str) -> Dict:
    return {
        'ok': False,
        'summary': 'Нужна более точная задача, код или ошибка для обработки.',
        'details': {'task_excerpt': task_text[:300]},
    }


def run_agent_coder3(
    task_text: str,
    mode: str = 'auto',
    chat_id: Optional[int] = None,
    role: str = 'user',
    dry_run: bool = False,
    project_root: str = '.',
) -> Dict:
    plan           = build_plan(task_text, requested_mode=mode, role=role, dry_run=dry_run)
    interpretation = plan.get('interpretation', {})
    adapter        = Coder3ToolAdapter(project_root=project_root)
    selected       = plan['mode']
    adapter.observe('interpretation', interpretation)
    adapter.log(f'chat_id={chat_id} role={role} mode={selected}')

    if dry_run:
        return {
            'ok': True, 'skill': 'agent_coder3', 'mode': selected,
            'steps': plan['steps'], 'tools': plan['tools'],
            'changes': 0, 'artifacts': [], 'failed': 0,
            'summary': 'Dry-run completed. No files were changed.',
            'details': {'chat_id': chat_id},
            'interpretation': interpretation,
            'validation': {'ok': True, 'checks': 0, 'warnings': []},
            'observations': adapter.observations, 'logs': adapter.logs,
        }

    if selected == 'quick':
        payload = run_quick_mode(task_text, adapter)
    elif selected == 'autofix':
        payload = run_autofix(task_text, adapter)
    elif selected == 'project':
        payload = run_project_mode(task_text, adapter)
    elif selected == 'review':
        payload = run_review_mode(task_text, adapter)
    elif selected == 'sandbox':
        payload = run_sandbox_mode(task_text, adapter)
    else:
        payload = _fallback_payload(task_text)

    adapter.observe('reasoning', {
        'selected_mode': selected,
        'ok': payload.get('ok', False),
        'summary': payload.get('summary', ''),
    })
    validation = _validate_result(adapter, payload)
    adapter.observe('validation', validation)

    return {
        'ok':            payload.get('ok', False),
        'skill':         'agent_coder3',
        'mode':          selected,
        'steps':         plan['steps'],
        'tools':         plan['tools'],
        'changes':       len(adapter.changes),
        'artifacts':     adapter.artifacts,
        'failed':        0 if payload.get('ok') else 1,
        'summary':       payload.get('summary', ''),
        'details':       payload.get('details', {}),
        'interpretation':interpretation,
        'validation':    validation,
        'observations':  adapter.observations,
        'logs':          adapter.logs,
    }
