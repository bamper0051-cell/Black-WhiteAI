"""
BlackBugsAI — Agent Executor (обновлённый)
Выполняет план пошагово. Поддерживает генерацию инструментов, кэширование, возврат артефактов.
"""
import time
import threading
import ast
import base64
import re
import os
from dataclasses import dataclass, field
from typing import List, Dict, Callable, Optional, Any, Tuple
from enum import Enum

# Подключаем кэш
import agent_tool_cache as cache

class StepStatus(str, Enum):
    PENDING  = "pending"
    RUNNING  = "running"
    DONE     = "done"
    FAILED   = "failed"
    SKIPPED  = "skipped"

@dataclass
class StepResult:
    step_id:   int
    tool:      str
    status:    StepStatus
    result:    str = ""
    error:     str = ""
    duration_s: float = 0.0
    artifacts: List[str] = field(default_factory=list)

@dataclass
class ExecutionResult:
    task:       str
    status:     str          # done | failed | partial
    steps:      List[StepResult]
    final_text: str = ""
    artifacts:  List[str] = field(default_factory=list)
    duration_s: float = 0.0

    def to_summary(self) -> str:
        icon = {'done':'✅','failed':'❌','partial':'⚠️'}.get(self.status,'?')
        done  = sum(1 for s in self.steps if s.status==StepStatus.DONE)
        fail  = sum(1 for s in self.steps if s.status==StepStatus.FAILED)
        lines = [f"{icon} <b>Результат</b> [{self.status}]"]
        if self.final_text:
            lines.append(self.final_text[:800])
        lines.append(f"\n⏱ {self.duration_s:.1f}с  ✅{done}  ❌{fail}")
        if self.artifacts:
            lines.append(f"📎 Файлов: {len(self.artifacts)}")
        return "\n".join(lines)


AGENT_ROLES = {
    'research':   'Ты агент-исследователь. Собираешь информацию и анализируешь.',
    'coder':      'Ты агент-разработчик. Пишешь код, исправляешь баги.',
    'video':      'Ты агент-видеопродюсер. Монтируешь видео, создаёшь контент.',
    'analysis':   'Ты агент-аналитик. Анализируешь данные, строишь отчёты.',
    'tool_builder':'Ты агент-сборщик инструментов. Генерируешь код, компилируешь, сохраняешь в кэш.',
}


class Executor:
    def __init__(self, on_status: Callable = None, llm_caller: Callable = None):
        self.on_status = on_status or (lambda m: None)
        self._llm      = llm_caller

    def _status(self, msg: str):
        self.on_status(msg)

    def execute_plan(self, plan, user_id: str = None,
                     chat_id: str = None) -> ExecutionResult:
        from agent_tools_registry import execute_tool
        t0 = time.time()
        step_results: List[StepResult] = []
        all_artifacts: List[str] = []
        tools_used: List[str] = []
        context: Dict[int, str] = {}

        self._status(f"🚀 {len(plan.steps)} шагов")

        for step in plan.steps:
            # Проверка зависимостей
            if step.depends_on:
                failed_deps = [d for d in step.depends_on
                               if any(r.step_id==d and r.status==StepStatus.FAILED
                                      for r in step_results)]
                if failed_deps:
                    if step.optional:
                        step_results.append(StepResult(step.step_id, step.tool,
                                                        StepStatus.SKIPPED,
                                                        result="Пропущен"))
                        continue
                    else:
                        step_results.append(StepResult(step.step_id, step.tool,
                                                        StepStatus.FAILED,
                                                        error=f"Зависимости не выполнены: {failed_deps}"))
                        break

            self._status(f"▶️ Шаг {step.step_id}/{len(plan.steps)}: {step.description}")

            # Подготовка аргументов
            args = dict(step.args) if isinstance(step.args, dict) else {'input': str(step.args)}
            for dep_id in step.depends_on:
                if dep_id in context:
                    args.setdefault(f'prev_{dep_id}', context[dep_id])

            # Вызов инструмента с поддержкой возврата (ok, result, artifacts)
            ts = time.time()
            tool_name = step.tool or 'chat'
            ok, result, artifacts = self._call_tool_with_artifacts(
                tool_name, args, chat_id=chat_id, user_id=user_id, step=step
            )
            duration = time.time() - ts

            status = StepStatus.DONE if ok else StepStatus.FAILED
            sr = StepResult(step.step_id, step.tool, status,
                            result=result if ok else "",
                            error=result if not ok else "",
                            duration_s=duration,
                            artifacts=artifacts)

            step_results.append(sr)
            context[step.step_id] = result[:300]
            tools_used.append(step.tool)
            all_artifacts.extend(artifacts)

            if not ok and not step.optional:
                self._status(f"❌ Шаг {step.step_id} упал")
                break

        # Итоговый статус
        done_n = sum(1 for s in step_results if s.status==StepStatus.DONE)
        fail_n = sum(1 for s in step_results if s.status==StepStatus.FAILED)
        overall = 'done' if fail_n==0 else ('failed' if done_n==0 else 'partial')

        # Синтез финального текста
        results_text = "\n".join(f"[{s.tool}]: {s.result or s.error}" for s in step_results)
        final = self._synthesize(plan.task, results_text)

        # Сохранение в память
        if user_id:
            try:
                from agent_memory import AgentMemory
                AgentMemory(user_id).after_task(
                    plan.task, tools_used, final,
                    status=overall, duration=time.time()-t0
                )
            except Exception:
                pass

        total = time.time() - t0
        self._status(f"{'✅' if overall=='done' else '❌'} Готово за {total:.1f}с")

        return ExecutionResult(
            task=plan.task, status=overall,
            steps=step_results, final_text=final,
            artifacts=all_artifacts, duration_s=total,
        )

    def _call_tool_with_artifacts(self, tool_name: str, args: dict,
                                   chat_id=None, user_id=None, step=None) -> Tuple[bool, str, List[str]]:
        """Вызывает инструмент и преобразует результат в (ok, message, artifacts)."""
        from agent_tools_registry import execute_tool

        # Специальная обработка для self-tool генерации
        if tool_name == 'generate_code':
            return self._generate_code_tool(args, user_id)
        elif tool_name == 'save_tool_cache':
            return self._save_tool_cache_tool(args, user_id)
        elif tool_name == 'return_artifact':
            return self._return_artifact_tool(args, user_id)

        # Стандартный вызов
        ok, result = execute_tool(tool_name, args, chat_id=chat_id,
                                  on_status=self._status, user_id=user_id)
        # Извлечение артефактов из результата (старый способ)
        artifacts = []
        if isinstance(result, str):
            for fpath in re.findall(r'(?:/[^\s]+\.(?:mp4|mp3|jpg|png|pdf|zip|py|txt|docx|exe))', result):
                if os.path.exists(fpath):
                    artifacts.append(fpath)
        return ok, result, artifacts

    # ----- Специализированные инструменты для self-tool generation -----

    def _generate_code_tool(self, args: dict, user_id: str) -> Tuple[bool, str, List[str]]:
        """Генерирует код инструмента по описанию, проверяет синтаксис, повторяет при ошибке."""
        task = args.get('task', '')
        language = args.get('language', 'auto')

        # Определяем язык по описанию
        if language == 'auto':
            if 'powershell' in task.lower() or 'ps1' in task.lower():
                language = 'powershell'
            else:
                language = 'python'  # по умолчанию

        system = f"Ты генерируешь код на {language}. Выдай только код без пояснений."
        prompt = f"Напиши код инструмента по задаче: {task}"
        if not self._llm:
            return False, "Нет LLM для генерации", []

        # Первая попытка
        code = self._llm(prompt, system)
        # Проверка синтаксиса (для Python)
        if language == 'python':
            ok, error = self._check_python_syntax(code)
            if not ok:
                # Повторная попытка с исправлением
                self._status(f"⚠️ Синтаксическая ошибка, исправляем...")
                fix_prompt = f"Код имеет синтаксическую ошибку:\n{error}\n\nИсправь код:\n{code}"
                code = self._llm(fix_prompt, system)
                ok, error = self._check_python_syntax(code)
                if not ok:
                    return False, f"Не удалось исправить синтаксис: {error}", []

        # Сохраняем код во временный файл для артефакта
        filename = f"/tmp/generated_{int(time.time())}.{'ps1' if language == 'powershell' else 'py'}"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(code)
        return True, f"Код сгенерирован ({language})", [filename]

    def _check_python_syntax(self, code: str) -> Tuple[bool, str]:
        try:
            ast.parse(code)
            return True, ""
        except SyntaxError as e:
            return False, str(e)

    def _save_tool_cache_tool(self, args: dict, user_id: str) -> Tuple[bool, str, List[str]]:
        """Сохраняет сгенерированный инструмент в кэш."""
        # Предполагаем, что предыдущий шаг сохранил код в артефакте
        # Нужно извлечь путь к файлу из контекста (через args)
        # Упрощённо: ищем последний артефакт .py или .ps1
        # В реальной реализации лучше передавать явно
        # Здесь для примера: ищем в рабочей директории
        import glob
        py_files = glob.glob("/tmp/generated_*.py")
        ps_files = glob.glob("/tmp/generated_*.ps1")
        files = py_files + ps_files
        if not files:
            return False, "Нет сгенерированного файла для кэширования", []
        latest = max(files, key=os.path.getctime)
        with open(latest, 'r') as f:
            code = f.read()
        name = f"tool_{int(time.time())}"
        lang = 'python' if latest.endswith('.py') else 'powershell'
        cache.save_tool(name, code, lang, {'source_task': args.get('task','')})
        return True, f"Инструмент сохранён как {name}", [latest]

    def _return_artifact_tool(self, args: dict, user_id: str) -> Tuple[bool, str, List[str]]:
        """Возвращает артефакт (может разбить base64 на части)."""
        # Ищем последний сгенерированный файл
        import glob
        py_files = glob.glob("/tmp/generated_*.py")
        ps_files = glob.glob("/tmp/generated_*.ps1")
        files = py_files + ps_files
        if not files:
            return False, "Нет файла для возврата", []
        latest = max(files, key=os.path.getctime)
        # Проверяем размер
        size = os.path.getsize(latest)
        if size < 10000:  # меньше 10KB – отдаём как артефакт
            return True, f"Файл {os.path.basename(latest)} готов", [latest]
        else:
            # Кодируем в base64 и разбиваем на части
            with open(latest, 'rb') as f:
                data = f.read()
            b64 = base64.b64encode(data).decode()
            # Разбиваем по 3000 символов, чтобы не обрезалось
            chunk_size = 3000
            chunks = [b64[i:i+chunk_size] for i in range(0, len(b64), chunk_size)]
            result = f"Файл большой, передаю в base64 ({len(chunks)} частей):\n"
            for idx, chunk in enumerate(chunks, 1):
                result += f"\n--- Часть {idx}/{len(chunks)} ---\n{chunk}\n"
            return True, result, []

    # ----- Остальное без изменений -----

    def _synthesize(self, task: str, results: str) -> str:
        if not self._llm: return results
        try:
            return self._llm(
                f"Задача: {task}\n\nРезультаты:\n{results[:1500]}\n\nИтоговый ответ:",
                "Составь краткий итоговый ответ пользователю."
            )
        except Exception:
            return results

    def run_multi_agent(self, task: str, roles: List[str] = None,
                        user_id: str = None, chat_id: str = None) -> Dict[str, str]:
        """Параллельные агенты (добавлена роль tool_builder)."""
        if not roles:
            kw = task.lower()
            roles = []
            if any(w in kw for w in ['найди','исследуй','search']): roles.append('research')
            if any(w in kw for w in ['код','script','баг','исправь','создай инструмент','сгенерируй']): roles.append('tool_builder')
            if any(w in kw for w in ['видео','video','ролик']): roles.append('video')
            if any(w in kw for w in ['анализ','отчёт','данные']): roles.append('analysis')
            if not roles: roles = ['research']

        results: Dict[str, str] = {}
        lock = threading.Lock()

        def _run(role: str):
            system = AGENT_ROLES.get(role, '')
            prompt = f"Задача: {task}\n\nВыполни свою часть:"
            try:
                r = self._llm(prompt, system) if self._llm else f"[{role}] выполнено"
                with lock: results[role] = r
            except Exception as e:
                with lock: results[role] = f"❌ {e}"

        self._status(f"🤖 {len(roles)} агентов: {', '.join(roles)}")
        threads = [threading.Thread(target=_run, args=(r,), daemon=True) for r in roles]
        for t in threads: t.start()
        for t in threads: t.join(timeout=60)
        return results
