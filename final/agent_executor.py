"""
BlackBugsAI — Agent Executor
Выполняет Plan пошагово. Поддерживает зависимости между шагами и multi-agent.
"""
import time, threading
from dataclasses import dataclass, field
from typing import List, Dict, Callable, Optional, Any
from enum import Enum

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
    'research':  'Ты агент-исследователь. Собираешь информацию и анализируешь.',
    'coder':     'Ты агент-разработчик. Пишешь код, исправляешь баги.',
    'video':     'Ты агент-видеопродюсер. Монтируешь видео, создаёшь контент.',
    'analysis':  'Ты агент-аналитик. Анализируешь данные, строишь отчёты.',
}


class Executor:
    def __init__(self, on_status: Callable = None, llm_caller: Callable = None):
        self.on_status = on_status or (lambda m: None)
        self._llm      = llm_caller

    def _status(self, msg: str):
        self.on_status(msg)

    def execute_plan(self, plan, user_id: str = None,
                     chat_id: str = None) -> ExecutionResult:
        """Выполняет план пошагово."""
        from agent_tools_registry import execute_tool
        t0 = time.time()
        step_results: List[StepResult] = []
        all_artifacts: List[str] = []
        tools_used: List[str] = []
        context: Dict[int, str] = {}   # результаты предыдущих шагов

        self._status(f"🚀 {len(plan.steps)} шагов")

        for step in plan.steps:
            # Проверяем зависимости
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

            # Обогащаем args контекстом
            args = dict(step.args) if isinstance(step.args, dict) else {'input': str(step.args)}
            for dep_id in step.depends_on:
                if dep_id in context:
                    args.setdefault(f'prev_{dep_id}', context[dep_id])

            ts = time.time()
            tool_name = step.tool or 'chat'  # guard against None
            ok, result = execute_tool(
                tool_name, args,
                chat_id=chat_id, on_status=self._status,
                user_id=user_id
            )
            duration = time.time() - ts

            status = StepStatus.DONE if ok else StepStatus.FAILED
            sr = StepResult(step.step_id, step.tool, status,
                            result=result if ok else "",
                            error=result if not ok else "",
                            duration_s=duration)

            # Собираем файлы-артефакты из результата
            import re, os
            for fpath in re.findall(r'(?:/[^\s]+\.(?:mp4|mp3|jpg|png|pdf|zip|py|txt|docx))', result):
                if os.path.exists(fpath):
                    sr.artifacts.append(fpath)
                    all_artifacts.append(fpath)

            step_results.append(sr)
            context[step.step_id] = result[:300]
            tools_used.append(step.tool)

            if not ok and not step.optional:
                self._status(f"❌ Шаг {step.step_id} упал")
                break

        # Статус
        done_n = sum(1 for s in step_results if s.status==StepStatus.DONE)
        fail_n = sum(1 for s in step_results if s.status==StepStatus.FAILED)
        overall = 'done' if fail_n==0 else ('failed' if done_n==0 else 'partial')

        # Финальный текст
        results_text = "\n".join(f"[{s.tool}]: {s.result or s.error}" for s in step_results)
        final = self._synthesize(plan.task, results_text)

        # Память
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
        """Параллельные агенты."""
        if not roles:
            kw = task.lower()
            roles = []
            if any(w in kw for w in ['найди','исследуй','search']): roles.append('research')
            if any(w in kw for w in ['код','script','баг','исправь']): roles.append('coder')
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
