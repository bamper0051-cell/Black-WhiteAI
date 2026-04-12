"""
BlackBugsAI — Agent Core
Единая точка входа: planner → executor → memory → result
Используется из bot.py вместо прямых вызовов chat_respond/run_agent_with_tools.
"""
import time
import config
from structured_logger import ComponentLogger

LOG = ComponentLogger('agent_core')


# ─── LLM caller (совместим с существующим llm_client) ────────────────────────

def _llm_call(prompt: str, system: str = '', max_tokens: int = 2000) -> str:
    """LLM вызов — совместим с существующим llm_client."""
    try:
        from llm_client import call_llm
    except ImportError:
        # Fallback: ищем в fish_v2_merged
        import sys, os
        fv2 = os.path.join(os.path.dirname(__file__), 'fish_v2_merged')
        if fv2 not in sys.path:
            sys.path.insert(0, fv2)
        from llm_client import call_llm
    return call_llm(prompt, system, max_tokens)


# ─── Lazy-инициализация компонентов ──────────────────────────────────────────

_planner  = None
_executor = None

def _get_planner():
    global _planner
    if _planner is None:
        try:
            from agent_planner import Planner
            _planner = Planner(llm_caller=_llm_call)
        except ImportError as e:
            LOG.warn(f"agent_planner недоступен: {e}")
    return _planner

def _get_executor(on_status=None):
    from agent_executor import Executor
    return Executor(on_status=on_status or (lambda m: None), llm_caller=_llm_call)


# ─── Определяем нужен ли planner ─────────────────────────────────────────────

_SIMPLE_CHAT_THRESHOLD = 50   # слова — короткий вопрос идёт напрямую в LLM

def _needs_planning(text: str) -> bool:
    """Нужен ли плановщик или достаточно прямого чата."""
    kw_tools = [
        'озвучь','tts','голос','video','видео','ролик','монтаж',
        'картинк','нарисуй','изображ','image',
        'код','script','напиши','исправь','баг','scaffold','patch',
        'найди в','поищи','загугли','search',
        'установи','pip install',
        'создай бота','новый модуль','добавь функцию',
        'moviepy','ffmpeg','архив','zip','pdf',
        'скачай','fetch','парсер',
    ]
    text_lower = text.lower()
    if any(kw in text_lower for kw in kw_tools):
        return True
    # Длинная задача → планируем
    if len(text.split()) > _SIMPLE_CHAT_THRESHOLD:
        return True
    return False


# ─── Главная функция ─────────────────────────────────────────────────────────

def run(task: str, chat_id: str, user_id: str = None,
        mode: str = 'auto', on_status=None,
        plan_first: bool = False) -> dict:
    """
    Основной pipeline:
      task → planner → executor → memory → result

    Возвращает:
      {
        'text':      str,          # текст ответа
        'artifacts': [str],        # пути к файлам
        'steps':     [...],        # шаги выполнения
        'status':    'done|failed|partial',
        'plan':      Plan|None,
        'duration':  float,
      }
    """
    t0      = time.time()
    uid     = str(user_id or chat_id)
    status  = lambda m: on_status(m) if on_status else None

    # Получаем план
    planner = _get_planner()
    plan    = None

    if planner and _needs_planning(task):
        status("🧠 Анализирую задачу...")
        try:
            from agent_planner import PlanMode
            pm = {'patch': PlanMode.PATCH, 'scaffold': PlanMode.SCAFFOLD,
                  'plan_first': PlanMode.PLAN_FIRST}.get(mode, PlanMode.AUTO)

            # Обогащаем контекст памятью
            memory_ctx = ''
            try:
                from agent_memory import AgentMemory
                memory_ctx = AgentMemory(uid).build_context(task)
            except Exception:
                pass

            plan = planner.plan(task, mode=pm, context=memory_ctx)

            if plan_first or mode == 'plan_first':
                # Возвращаем план без выполнения
                return {
                    'text':      plan.to_text(),
                    'artifacts': [],
                    'steps':     [],
                    'status':    'planned',
                    'plan':      plan,
                    'duration':  time.time() - t0,
                }

            status(f"📋 План: {len(plan.steps)} шагов")

        except Exception as e:
            LOG.warn(f"Planner failed: {e}, falling back to direct")
            plan = None

    # Если план есть — исполняем через executor
    if plan and plan.steps:
        executor = _get_executor(on_status=on_status)
        exec_result = executor.execute_plan(plan, user_id=uid, chat_id=chat_id)
        return {
            'text':      exec_result.final_text or exec_result.to_summary(),
            'artifacts': exec_result.artifacts,
            'steps':     [{'tool': s.tool, 'ok': s.status.value == 'done',
                           'result': s.result or s.error}
                          for s in exec_result.steps],
            'status':    exec_result.status,
            'plan':      plan,
            'duration':  time.time() - t0,
        }

    # Fallback: прямой LLM-ответ
    status("💬 Отвечаю...")
    try:
        from chat_agent import chat_respond, is_active, start_session
        if not is_active(uid):
            start_session(uid, 'chat')
        reply = chat_respond(uid, task)
        # Очищаем <think> теги
        import re
        reply = re.sub(r'<think>.*?</think>', '', reply, flags=re.DOTALL).strip()
        # Записываем в память
        try:
            from agent_memory import AgentMemory
            AgentMemory(uid).after_task(task, tools_used=[], result=reply,
                                        status='done', duration=time.time()-t0)
        except Exception:
            pass
        return {
            'text':      reply,
            'artifacts': [],
            'steps':     [],
            'status':    'done',
            'plan':      None,
            'duration':  time.time() - t0,
        }
    except Exception as e:
        LOG.error(f"LLM fallback failed: {e}", user_id=uid)
        return {
            'text':      f"❌ Ошибка: {e}",
            'artifacts': [],
            'steps':     [],
            'status':    'failed',
            'plan':      None,
            'duration':  time.time() - t0,
        }


def run_multi(task: str, chat_id: str, user_id: str = None,
              on_status=None) -> dict:
    """Multi-agent запуск — параллельные агенты для сложных задач."""
    executor = _get_executor(on_status=on_status)
    results  = executor.run_multi_agent(task, user_id=user_id, chat_id=chat_id)
    # Сводим в один текст
    parts = [f"**{role}**:\n{res}" for role, res in results.items()]
    return {
        'text':      "\n\n".join(parts),
        'artifacts': [],
        'steps':     [{'tool': role, 'ok': '❌' not in res, 'result': res[:200]}
                      for role, res in results.items()],
        'status':    'done',
        'plan':      None,
        'duration':  0,
    }


def status_text(result: dict) -> str:
    """Форматирует результат для отправки в Telegram."""
    text = result.get('text', '')
    steps = result.get('steps', [])
    arts  = result.get('artifacts', [])

    if steps and len(steps) > 1:
        step_lines = []
        for s in steps:
            icon = "✅" if s.get('ok') else "❌"
            step_lines.append(f"{icon} {s.get('tool','?')}: {str(s.get('result',''))[:80]}")
        text = "\n".join(step_lines) + ("\n\n" + text if text else "")

    if arts:
        text += f"\n\n📎 Файлов: {len(arts)}"

    return text[:4000] if text else "✅ Готово"
