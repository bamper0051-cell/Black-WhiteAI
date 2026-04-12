"""
core/agent.py — AI-агент с инструментами.

Логика:
  1. Пользователь пишет задачу
  2. Агент через LLM определяет нужные инструменты
  3. Выполняет инструменты последовательно
  4. Если инструмента нет → пишет код сам и запускает в sandbox
  5. Если совсем невозможно → возвращает инструкцию со списком что нужно

Поддерживает multi-step планирование: агент может сам решить
что нужно сначала сгенерить картинку, потом озвучить текст, потом собрать видео.
"""

import json
import logging
from typing import List, Dict, Optional, Callable

logger = logging.getLogger('agent')

# ── Системный промпт агента ───────────────────────────────────────

AGENT_SYSTEM = """Ты AI-агент с доступом к инструментам. 

{tools_list}

Твоя задача: выполнить запрос пользователя используя инструменты.

АЛГОРИТМ:
1. Проанализируй запрос
2. Составь план из шагов (какие инструменты нужны, в каком порядке)
3. Если инструмент есть — используй его
4. Если инструмента нет но можно написать Python-код — используй tool "code"
5. Если задача нереализуема без установки новых вещей — верни инструкцию

ФОРМАТ ОТВЕТА (строго JSON):
{{
  "plan_description": "что ты собираешься делать",
  "steps": [
    {{
      "step": 1,
      "tool": "название_инструмента",
      "args": {{"аргумент": "значение"}},
      "description": "зачем этот шаг",
      "depends_on_step_output": false
    }}
  ],
  "fallback": null
}}

Если задача нереализуема, верни:
{{
  "plan_description": "объяснение почему невозможно",
  "steps": [],
  "fallback": {{
    "type": "instruction",
    "title": "Как это сделать вручную",
    "steps": ["шаг 1", "шаг 2"],
    "packages": ["пакет1", "пакет2"],
    "estimated_time": "5 минут"
  }}
}}

Для задач типа "озвучь текст и собери видео":
- step 1: tool=tts, args={{text: "..."}}
- step 2: tool=image, args={{prompt: "..."}} (если нужна картинка)  
- step 3: tool=video, args={{images: ["{{step2.file_path}}"], audio_path: "{{step1.file_path}}"}}

Используй {{stepN.имя_поля}} для передачи результата шага в следующий.
"""

# ── Планировщик ───────────────────────────────────────────────────

def plan_task(task: str, router, tools_list: str) -> dict:
    """Вызывает LLM для составления плана выполнения задачи."""
    system = AGENT_SYSTEM.format(tools_list=tools_list)
    messages = [
        {'role': 'system', 'content': system},
        {'role': 'user',   'content': f'Задача: {task}'},
    ]
    try:
        return router.chat_json(messages, temperature=0.1, max_tokens=2048)
    except Exception as e:
        logger.error(f'[agent] plan_task failed: {e}')
        return {
            'plan_description': f'Ошибка планирования: {e}',
            'steps': [],
            'fallback': {
                'type': 'instruction',
                'title': 'Не удалось составить план',
                'steps': ['Попробуй переформулировать задачу'],
                'packages': [],
                'estimated_time': 'неизвестно',
            }
        }


# ── Executor ──────────────────────────────────────────────────────

class AgentExecutor:
    """
    Выполняет план агента шаг за шагом.
    
    Поддерживает передачу результатов между шагами через {stepN.field}.
    """

    def __init__(self, user_id: int, session, router,
                 on_status: Callable = None, bot=None):
        self.user_id   = user_id
        self.session   = session
        self.router    = router
        self.on_status = on_status
        self.bot       = bot
        self._results: Dict[int, dict] = {}   # step_num → result

    def _upd(self, msg: str):
        if self.on_status:
            self.on_status(msg)
        logger.info(f'[agent] {msg}')

    def _resolve_args(self, args: dict, step_num: int) -> dict:
        """Подставляет результаты предыдущих шагов в аргументы."""
        import re
        resolved = {}
        for k, v in args.items():
            if isinstance(v, str):
                def replace_ref(m):
                    ref_step = int(m.group(1))
                    field    = m.group(2)
                    prev     = self._results.get(ref_step, {})
                    return str(prev.get(field, m.group(0)))
                v = re.sub(r'\{step(\d+)\.(\w+)\}', replace_ref, v)
            resolved[k] = v
        return resolved

    def execute_step(self, step: dict, step_num: int) -> dict:
        """Выполняет один шаг плана."""
        from tool_registry import registry

        tool_name = step.get('tool', '')
        args      = step.get('args', {})
        desc      = step.get('description', tool_name)

        self._upd(f"⚙️ Шаг {step_num}: {desc}")

        # Подставляем результаты предыдущих шагов
        resolved_args = self._resolve_args(args, step_num)

        # Ищем инструмент
        tool = registry.get(tool_name)
        if not tool:
            # Инструмент не найден → пробуем через code sandbox
            self._upd(f"🔧 Инструмент '{tool_name}' не найден, пишу код...")
            code_result = self._synthesize_tool(tool_name, resolved_args, desc)
            self._results[step_num] = code_result
            return code_result

        # Выполняем инструмент
        try:
            result = tool.execute(
                user_id=self.user_id,
                args=resolved_args,
                session=self.session,
                bot=self.bot,
            )
            if not isinstance(result, dict):
                result = {'success': bool(result), 'output': str(result)}
            self._results[step_num] = result

            if result.get('success'):
                self._upd(f"✅ Шаг {step_num} выполнен")
            else:
                self._upd(f"⚠️ Шаг {step_num}: {result.get('error', '?')}")
            return result
        except Exception as e:
            result = {'success': False, 'error': str(e)}
            self._results[step_num] = result
            self._upd(f"❌ Шаг {step_num} ошибка: {e}")
            return result

    def _synthesize_tool(self, tool_name: str, args: dict, description: str) -> dict:
        """
        Пишет Python-код для выполнения задачи если инструмента нет.
        Запускает в sandbox.
        """
        prompt = (
            f"Write Python code to: {description}\n"
            f"Tool name: {tool_name}\n"
            f"Arguments: {json.dumps(args)}\n\n"
            f"Return ONLY executable Python code, no explanation.\n"
            f"Print the result to stdout.\n"
            f"If you need external packages, add: import subprocess; "
            f"subprocess.run(['pip', 'install', 'package', '-q'])"
        )
        messages = [
            {'role': 'system', 'content': 'Write Python code only. No markdown.'},
            {'role': 'user',   'content': prompt},
        ]
        try:
            code = self.router.chat(messages, temperature=0.1, max_tokens=2048)
            # Убираем markdown если есть
            if '```' in code:
                import re
                m = re.search(r'```(?:python)?\n(.*?)```', code, re.DOTALL)
                if m:
                    code = m.group(1)

            from sandbox import execute_code
            result = execute_code(code, self.user_id, self.session.sandbox_dir)
            result['synthesized_code'] = code[:500]
            return result
        except Exception as e:
            return {'success': False, 'error': f'Не удалось синтезировать инструмент: {e}'}

    def execute_plan(self, plan: dict) -> dict:
        """
        Выполняет весь план.
        Возвращает итоговый результат.
        """
        steps    = plan.get('steps', [])
        fallback = plan.get('fallback')

        if not steps and fallback:
            return {'success': False, 'fallback': fallback, 'results': {}}

        if not steps:
            return {'success': False, 'error': 'Пустой план', 'results': {}}

        self._upd(f"📋 {plan.get('plan_description', 'Выполняю...')}")
        self._upd(f"🔢 Шагов: {len(steps)}")

        step_results = {}
        all_success  = True

        for step in steps:
            step_num = step.get('step', len(step_results) + 1)
            result   = self.execute_step(step, step_num)
            step_results[step_num] = result
            if not result.get('success') and not step.get('optional', False):
                self._upd(f"⛔ Стоп: шаг {step_num} провалился")
                all_success = False
                break

        return {
            'success':  all_success,
            'results':  step_results,
            'fallback': fallback,
        }


# ── Главная функция ───────────────────────────────────────────────

def run_agent(task: str, user_id: int, session, router,
              on_status: Callable = None, bot=None) -> dict:
    """
    Запускает агента для выполнения задачи.
    
    Returns:
        {
            'success': bool,
            'plan': dict,
            'results': dict,
            'summary': str,
            'files': list,  ← пути к созданным файлам
        }
    """
    from tool_registry import registry

    tools_list = registry.tools_prompt()

    if on_status:
        on_status(f"🤔 Анализирую задачу...")

    # 1. Составляем план
    plan = plan_task(task, router, tools_list)

    if on_status:
        desc = plan.get('plan_description', '')[:100]
        on_status(f"📋 План: {desc}")

    # 2. Выполняем
    executor = AgentExecutor(
        user_id=user_id, session=session,
        router=router, on_status=on_status, bot=bot,
    )
    exec_result = executor.execute_plan(plan)

    # 3. Собираем файлы из результатов
    files = []
    for r in exec_result.get('results', {}).values():
        for key in ('file_path', 'zip_path', 'output_path'):
            if key in r and r[key]:
                import os
                if os.path.exists(str(r[key])):
                    files.append(r[key])

    # 4. Итоговое резюме
    summary = _build_summary(plan, exec_result, files)

    return {
        'success':  exec_result.get('success', False),
        'plan':     plan,
        'results':  exec_result.get('results', {}),
        'fallback': exec_result.get('fallback'),
        'files':    files,
        'summary':  summary,
    }


def _build_summary(plan: dict, exec_result: dict, files: list) -> str:
    """Формирует итоговое сообщение для пользователя."""
    parts = []

    if exec_result.get('success'):
        parts.append("✅ <b>Задача выполнена!</b>")
    else:
        parts.append("⚠️ <b>Выполнено с ошибками</b>")

    # Результаты шагов
    for step_num, result in exec_result.get('results', {}).items():
        icon = '✅' if result.get('success') else '❌'
        msg  = result.get('message') or result.get('error') or ''
        if result.get('stdout'):
            msg = result['stdout'][:200]
        parts.append(f"{icon} Шаг {step_num}: {msg[:100]}")

    # Файлы
    if files:
        import os
        parts.append(f"\n📁 <b>Созданные файлы ({len(files)}):</b>")
        for f in files:
            size = os.path.getsize(f) // 1024 if os.path.exists(f) else 0
            parts.append(f"  • {os.path.basename(f)} ({size} KB)")

    # Fallback инструкция
    fallback = exec_result.get('fallback')
    if fallback and fallback.get('type') == 'instruction':
        parts.append(f"\n📖 <b>{fallback.get('title', 'Инструкция')}:</b>")
        for i, step in enumerate(fallback.get('steps', []), 1):
            parts.append(f"  {i}. {step}")
        pkgs = fallback.get('packages', [])
        if pkgs:
            parts.append(f"\n📦 Нужные пакеты: <code>pip install {' '.join(pkgs)}</code>")

    return '\n'.join(parts)
