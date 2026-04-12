"""
plan_execute_cycle.py — Цикл Plan → Execute → Observe → Fix → Learn

Усиленный цикл выполнения задач через task_queue + autofix:
  PLAN    → Декомпозиция задачи на шаги
  EXECUTE → Выполнение каждого шага
  OBSERVE → Наблюдение: успех / ошибка / частичный результат
  FIX     → Авто-исправление при ошибке (LLM patch)
  LEARN   → Сохранение паттернов успеха в базе знаний

Использование:
    from plan_execute_cycle import run_cycle
    result = run_cycle(user_id, task_description, context={})
"""

import os
import json
import time
import uuid
import sqlite3
import traceback
from datetime import datetime
from typing import Optional

import config
from task_queue import (
    create_task, get_task, update_task, save_artifact,
    artifact_dir, DB_PATH
)

# ─── База знаний (паттерны успеха/ошибок) ─────────────────────────────────────

KNOWLEDGE_DB = os.path.join(
    getattr(config, 'DATA_DIR', None) or config.BASE_DIR,
    'knowledge.db'
)

def _init_knowledge_db():
    os.makedirs(os.path.dirname(KNOWLEDGE_DB), exist_ok=True)
    with sqlite3.connect(KNOWLEDGE_DB) as c:
        c.executescript('''
            CREATE TABLE IF NOT EXISTS patterns (
                id TEXT PRIMARY KEY,
                task_type TEXT,
                error_signature TEXT,
                fix_applied TEXT,
                success INTEGER DEFAULT 0,
                used_count INTEGER DEFAULT 0,
                created_at TEXT,
                updated_at TEXT
            );
            CREATE TABLE IF NOT EXISTS execution_log (
                id TEXT PRIMARY KEY,
                cycle_id TEXT,
                step_index INTEGER,
                step_name TEXT,
                status TEXT,
                result TEXT,
                error TEXT,
                fix_attempted INTEGER DEFAULT 0,
                duration_ms INTEGER,
                created_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_patterns_type ON patterns(task_type);
            CREATE INDEX IF NOT EXISTS idx_log_cycle ON execution_log(cycle_id);
        ''')

_init_knowledge_db()


# ─── Статусы цикла ─────────────────────────────────────────────────────────────

CYCLE_STATUS = {
    'planning':  '🧠 Планирование...',
    'executing': '⚙️ Выполняется...',
    'observing': '🔭 Наблюдение...',
    'fixing':    '🔧 Авто-исправление...',
    'learning':  '📚 Обучение...',
    'done':      '✅ Завершено',
    'failed':    '❌ Ошибка',
}


# ─── Планирование (PLAN) ───────────────────────────────────────────────────────

def plan_task(task_description: str, context: dict, llm_fn=None) -> list[dict]:
    """
    Декомпозирует задачу на список шагов.
    Каждый шаг: { name, type, payload, expected_output }
    """
    # Простой эвристический планировщик (без LLM)
    steps = []

    desc_lower = task_description.lower()

    if any(kw in desc_lower for kw in ['код', 'code', 'написать', 'script', 'python']):
        steps.append({
            'name': 'Генерация кода',
            'type': 'code',
            'payload': {'text': task_description},
            'expected_output': 'code_file',
        })
        steps.append({
            'name': 'Тест кода',
            'type': 'code_test',
            'payload': {'text': f'Проверь и запусти: {task_description}'},
            'expected_output': 'test_passed',
        })

    elif any(kw in desc_lower for kw in ['картинк', 'image', 'изображени', 'нарисуй']):
        steps.append({
            'name': 'Генерация изображения',
            'type': 'image',
            'payload': {'prompt': task_description},
            'expected_output': 'image_file',
        })

    elif any(kw in desc_lower for kw in ['голос', 'озвучь', 'tts', 'speech']):
        steps.append({
            'name': 'TTS синтез',
            'type': 'tts',
            'payload': {'text': task_description},
            'expected_output': 'audio_file',
        })

    elif any(kw in desc_lower for kw in ['shell', 'команда', 'terminal', 'bash']):
        steps.append({
            'name': 'Shell-команда',
            'type': 'shell',
            'payload': {'cmd': task_description},
            'expected_output': 'output',
        })

    else:
        # Общий чат-ответ
        steps.append({
            'name': 'Обработка запроса',
            'type': 'chat',
            'payload': {'text': task_description},
            'expected_output': 'text_response',
        })

    # Если передан LLM — используем его для улучшенного планирования
    if llm_fn:
        try:
            prompt = (
                f"Разбей следующую задачу на 2-5 конкретных шагов. "
                f"Верни JSON-список: [{{\"name\": str, \"type\": str, \"payload\": dict}}]\n\n"
                f"Задача: {task_description}\n"
                f"Контекст: {json.dumps(context, ensure_ascii=False)[:500]}"
            )
            raw = llm_fn(prompt)
            parsed = _extract_json(raw)
            if isinstance(parsed, list) and parsed:
                steps = parsed
        except Exception:
            pass  # Фолбэк на эвристику

    return steps


def _extract_json(text: str):
    """Извлекает JSON из текста LLM."""
    import re
    match = re.search(r'\[.*\]', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except Exception:
            pass
    return None


# ─── Выполнение (EXECUTE) ──────────────────────────────────────────────────────

def execute_step(step: dict, user_id: str, task_id: str) -> dict:
    """
    Выполняет один шаг. Возвращает:
    { success: bool, result: str, error: str, artifacts: list }
    """
    start = time.time()
    step_type = step.get('type', 'chat')
    payload = step.get('payload', {})
    result = None
    error = None
    artifacts = []

    try:
        if step_type == 'chat':
            from chat_agent import chat_respond, start_session, is_active
            if not is_active(user_id):
                start_session(user_id, 'chat')
            result = chat_respond(user_id, payload.get('text', ''))

        elif step_type in ('code', 'code_test'):
            from chat_agent import code_agent_run, start_session
            start_session(user_id, 'code')
            r = code_agent_run(user_id, payload.get('text', ''))
            result = r.get('_full_output', '') or r.get('output', '') or '✅ Выполнено'
            adir = artifact_dir(user_id)
            for fpath in r.get('files', []):
                if os.path.exists(fpath):
                    import shutil
                    dest = os.path.join(adir, os.path.basename(fpath))
                    shutil.copy2(fpath, dest)
                    art_id = save_artifact(task_id, user_id, os.path.basename(fpath), dest)
                    artifacts.append(art_id)

        elif step_type == 'image':
            from agent_tools_registry import tool_pollinations_image
            result = tool_pollinations_image({'prompt': payload.get('prompt', '')}, chat_id=None)

        elif step_type == 'tts':
            from agent_tools_registry import tool_tts
            result = tool_tts({'text': payload.get('text', ''), 'voice': ''}, chat_id=None)

        elif step_type == 'shell':
            from admin_module import exec_shell
            from agent_roles import has_perm
            if not has_perm(user_id, 'run_shell'):
                raise PermissionError("Нет прав на shell")
            ok, out = exec_shell(payload.get('cmd', ''), timeout=30)
            result = out

        elif step_type == 'tool':
            from agent_tools_registry import execute_tool
            ok, res = execute_tool(
                payload.get('tool', ''), payload.get('args', ''), chat_id=user_id
            )
            result = res

        else:
            result = f"Неизвестный тип шага: {step_type}"

    except Exception as e:
        error = f"{type(e).__name__}: {e}\n{traceback.format_exc()[-800:]}"

    duration_ms = int((time.time() - start) * 1000)
    success = error is None and result is not None

    return {
        'success': success,
        'result': str(result)[:2000] if result else None,
        'error': error,
        'artifacts': artifacts,
        'duration_ms': duration_ms,
    }


# ─── Наблюдение (OBSERVE) ─────────────────────────────────────────────────────

def observe_result(step: dict, execution: dict) -> dict:
    """
    Анализирует результат шага и определяет нужен ли FIX.
    Возвращает: { needs_fix: bool, error_signature: str, severity: str }
    """
    if execution['success']:
        return {'needs_fix': False, 'error_signature': None, 'severity': 'none'}

    error = execution.get('error', '') or ''

    # Классификация ошибок
    if 'ModuleNotFoundError' in error or 'ImportError' in error:
        sig = 'import_error'
        severity = 'high'
    elif 'SyntaxError' in error:
        sig = 'syntax_error'
        severity = 'high'
    elif 'PermissionError' in error:
        sig = 'permission_error'
        severity = 'medium'
    elif 'TimeoutError' in error or 'timeout' in error.lower():
        sig = 'timeout_error'
        severity = 'medium'
    elif 'ConnectionError' in error or 'ConnectionRefused' in error:
        sig = 'connection_error'
        severity = 'low'
    elif 'KeyError' in error or 'AttributeError' in error:
        sig = 'code_error'
        severity = 'high'
    else:
        sig = 'unknown_error'
        severity = 'medium'

    return {
        'needs_fix': True,
        'error_signature': sig,
        'severity': severity,
        'error_text': error[:500],
    }


# ─── Исправление (FIX) ────────────────────────────────────────────────────────

def fix_step(step: dict, observation: dict, user_id: str, llm_fn=None) -> dict:
    """
    Пытается исправить шаг на основе наблюдения.
    Возвращает модифицированный шаг или None если исправление невозможно.
    """
    sig = observation.get('error_signature', 'unknown_error')
    error_text = observation.get('error_text', '')

    # Ищем известный патч в базе знаний
    known_fix = _lookup_known_fix(step.get('type', ''), sig)
    if known_fix:
        patched_step = dict(step)
        patched_step['_fix_applied'] = known_fix
        patched_step['_fix_source'] = 'knowledge_base'
        return patched_step

    # Специфичные исправления по типу ошибки
    patched_step = dict(step)

    if sig == 'import_error':
        patched_step['payload'] = dict(step.get('payload', {}))
        text = patched_step['payload'].get('text', '')
        patched_step['payload']['text'] = (
            f"ОШИБКА ИМПОРТА. Напиши код без внешних зависимостей или "
            f"добавь pip install в начало. Задача: {text}"
        )
        patched_step['_fix_applied'] = 'suggest_install_or_stdlib'

    elif sig == 'syntax_error':
        patched_step['payload'] = dict(step.get('payload', {}))
        text = patched_step['payload'].get('text', '')
        patched_step['payload']['text'] = (
            f"СИНТАКСИЧЕСКАЯ ОШИБКА: {error_text[:200]}\n"
            f"Перепиши код исправив синтаксис. Задача: {text}"
        )
        patched_step['_fix_applied'] = 'rewrite_with_syntax_fix'

    elif sig == 'timeout_error':
        patched_step['payload'] = dict(step.get('payload', {}))
        patched_step['payload']['timeout'] = 60  # увеличиваем таймаут
        patched_step['_fix_applied'] = 'increase_timeout'

    elif sig == 'connection_error':
        # Попробуем повтор с задержкой
        time.sleep(2)
        patched_step['_fix_applied'] = 'retry_after_delay'

    else:
        # Используем LLM для генерации патча
        if llm_fn:
            try:
                fix_prompt = (
                    f"Задача: {step.get('name')}\n"
                    f"Тип: {step.get('type')}\n"
                    f"Ошибка: {error_text[:300]}\n\n"
                    f"Как исправить? Верни JSON с полем 'patch_instruction' (строка)."
                )
                raw = llm_fn(fix_prompt)
                parsed = _extract_json(raw) or {}
                if isinstance(parsed, dict) and parsed.get('patch_instruction'):
                    patched_step['payload'] = dict(step.get('payload', {}))
                    patched_step['payload']['text'] = (
                        f"{parsed['patch_instruction']}\n"
                        f"Исходная задача: {patched_step['payload'].get('text', '')}"
                    )
                    patched_step['_fix_applied'] = f"llm_patch: {parsed['patch_instruction'][:100]}"
            except Exception:
                return None
        else:
            return None  # Нет возможности исправить

    return patched_step


def _lookup_known_fix(task_type: str, error_sig: str) -> Optional[str]:
    """Ищет проверенный патч в базе знаний."""
    try:
        with sqlite3.connect(KNOWLEDGE_DB) as c:
            row = c.execute(
                "SELECT fix_applied FROM patterns "
                "WHERE task_type=? AND error_signature=? AND success=1 "
                "ORDER BY used_count DESC LIMIT 1",
                (task_type, error_sig)
            ).fetchone()
            return row[0] if row else None
    except Exception:
        return None


# ─── Обучение (LEARN) ─────────────────────────────────────────────────────────

def learn_from_execution(
    cycle_id: str,
    step: dict,
    execution: dict,
    fix_applied: Optional[str] = None
):
    """Сохраняет результат в базу знаний."""
    try:
        step_id = str(uuid.uuid4())[:8]
        now = datetime.now().isoformat()

        # Логируем шаг
        with sqlite3.connect(KNOWLEDGE_DB) as c:
            c.execute(
                "INSERT INTO execution_log "
                "(id, cycle_id, step_index, step_name, status, result, error, "
                " fix_attempted, duration_ms, created_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    step_id, cycle_id,
                    step.get('_index', 0),
                    step.get('name', ''),
                    'done' if execution['success'] else 'failed',
                    (execution.get('result') or '')[:500],
                    (execution.get('error') or '')[:500],
                    1 if fix_applied else 0,
                    execution.get('duration_ms', 0),
                    now,
                )
            )

        # Обновляем паттерн если был fix
        if fix_applied:
            _update_pattern(
                task_type=step.get('type', ''),
                error_sig=step.get('_error_sig', 'unknown'),
                fix=fix_applied,
                success=execution['success'],
            )
    except Exception:
        pass  # Обучение не должно ломать основной цикл


def _update_pattern(task_type: str, error_sig: str, fix: str, success: bool):
    try:
        with sqlite3.connect(KNOWLEDGE_DB) as c:
            existing = c.execute(
                "SELECT id, used_count FROM patterns "
                "WHERE task_type=? AND error_signature=? AND fix_applied=?",
                (task_type, error_sig, fix)
            ).fetchone()
            now = datetime.now().isoformat()
            if existing:
                c.execute(
                    "UPDATE patterns SET used_count=?, success=?, updated_at=? WHERE id=?",
                    (existing[1] + 1, 1 if success else 0, now, existing[0])
                )
            else:
                c.execute(
                    "INSERT INTO patterns "
                    "(id, task_type, error_signature, fix_applied, success, used_count, "
                    " created_at, updated_at) "
                    "VALUES (?,?,?,?,?,?,?,?)",
                    (str(uuid.uuid4())[:8], task_type, error_sig, fix,
                     1 if success else 0, 1, now, now)
                )
    except Exception:
        pass


# ─── Главный цикл ─────────────────────────────────────────────────────────────

def run_cycle(
    user_id: str,
    task_description: str,
    context: dict = None,
    max_fix_attempts: int = 3,
    llm_fn=None,
    progress_cb=None,
) -> dict:
    """
    Запускает полный цикл Plan→Execute→Observe→Fix→Learn.

    Args:
        user_id:          ID пользователя
        task_description: Описание задачи
        context:          Дополнительный контекст
        max_fix_attempts: Максимум попыток авто-исправления на шаг
        llm_fn:           Функция LLM для планирования и fix (опционально)
        progress_cb:      Коллбэк прогресса: fn(phase, step_name, message)

    Returns:
        {
          cycle_id, status, steps_total, steps_done, steps_failed,
          results: [{ step, success, result, fix_applied }],
          summary: str,
          artifacts: [str]
        }
    """
    context = context or {}
    cycle_id = str(uuid.uuid4())[:8]
    all_artifacts = []
    step_results = []

    def _progress(phase: str, step_name: str, msg: str):
        if progress_cb:
            try:
                progress_cb(phase, step_name, msg)
            except Exception:
                pass

    # ── PLAN ──────────────────────────────────────────────────────────────────
    _progress('planning', '', CYCLE_STATUS['planning'])
    steps = plan_task(task_description, context, llm_fn=llm_fn)

    steps_total = len(steps)
    steps_done = 0
    steps_failed = 0

    for idx, step in enumerate(steps):
        step['_index'] = idx
        step_name = step.get('name', f'Шаг {idx+1}')

        # ── EXECUTE ───────────────────────────────────────────────────────────
        _progress('executing', step_name, CYCLE_STATUS['executing'])
        execution = execute_step(step, user_id, cycle_id)

        # ── OBSERVE ───────────────────────────────────────────────────────────
        _progress('observing', step_name, CYCLE_STATUS['observing'])
        observation = observe_result(step, execution)

        fix_applied = None
        attempt = 0

        # ── FIX ───────────────────────────────────────────────────────────────
        while observation['needs_fix'] and attempt < max_fix_attempts:
            attempt += 1
            _progress('fixing', step_name,
                      f"{CYCLE_STATUS['fixing']} (попытка {attempt}/{max_fix_attempts})")

            step['_error_sig'] = observation.get('error_signature', 'unknown')
            patched = fix_step(step, observation, user_id, llm_fn=llm_fn)

            if patched is None:
                break  # Не можем исправить

            fix_applied = patched.get('_fix_applied', 'unknown')
            execution = execute_step(patched, user_id, cycle_id)
            observation = observe_result(patched, execution)

            if execution['success']:
                step = patched  # Используем патч для обучения
                break

        # ── LEARN ─────────────────────────────────────────────────────────────
        _progress('learning', step_name, CYCLE_STATUS['learning'])
        learn_from_execution(cycle_id, step, execution, fix_applied)

        # Собираем результаты
        if execution['success']:
            steps_done += 1
        else:
            steps_failed += 1

        all_artifacts.extend(execution.get('artifacts', []))

        step_results.append({
            'step': step_name,
            'type': step.get('type'),
            'success': execution['success'],
            'result': execution.get('result'),
            'error': execution.get('error'),
            'fix_applied': fix_applied,
            'fix_attempts': attempt,
            'duration_ms': execution.get('duration_ms', 0),
        })

    # ── Итог ──────────────────────────────────────────────────────────────────
    overall_success = steps_failed == 0
    status = 'done' if overall_success else ('partial' if steps_done > 0 else 'failed')

    icon = '✅' if overall_success else ('⚠️' if status == 'partial' else '❌')
    summary = (
        f"{icon} Цикл {cycle_id}: {steps_done}/{steps_total} шагов выполнено"
        + (f", {steps_failed} ошибок" if steps_failed else "")
    )

    _progress(status, '', summary)

    return {
        'cycle_id': cycle_id,
        'status': status,
        'steps_total': steps_total,
        'steps_done': steps_done,
        'steps_failed': steps_failed,
        'results': step_results,
        'summary': summary,
        'artifacts': all_artifacts,
    }


# ─── Интеграция с task_queue ──────────────────────────────────────────────────

def queue_cycle_task(user_id: str, task_description: str, context: dict = None) -> str:
    """
    Ставит задачу-цикл в очередь task_queue.
    Возвращает task_id.
    """
    return create_task(
        user_id=user_id,
        task_type='cycle',
        title=task_description[:80],
        payload={
            'description': task_description,
            'context': context or {},
        },
        max_retries=1,
        notify=True,
    )


def get_cycle_knowledge_stats() -> dict:
    """Статистика базы знаний."""
    try:
        with sqlite3.connect(KNOWLEDGE_DB) as c:
            patterns = c.execute("SELECT COUNT(*) FROM patterns").fetchone()[0]
            successes = c.execute(
                "SELECT COUNT(*) FROM patterns WHERE success=1"
            ).fetchone()[0]
            logs = c.execute("SELECT COUNT(*) FROM execution_log").fetchone()[0]
        return {
            'total_patterns': patterns,
            'successful_patterns': successes,
            'total_executions': logs,
        }
    except Exception:
        return {}
