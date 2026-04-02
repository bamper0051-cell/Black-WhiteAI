"""
BlackBugsAI — Agent Planner
Режимы: auto | patch | scaffold | plan_first | direct
"""
import json, re, time
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Callable
from enum import Enum

class PlanMode(str, Enum):
    AUTO       = "auto"
    PATCH      = "patch"
    SCAFFOLD   = "scaffold"
    PLAN_FIRST = "plan_first"
    DIRECT     = "direct"

@dataclass
class PlanStep:
    step_id:     int
    tool:        str
    args:        Dict[str, Any]
    description: str
    depends_on:  List[int] = field(default_factory=list)
    optional:    bool = False
    estimated_s: int = 10

    def to_text(self) -> str:
        return f"  {self.step_id}. [{self.tool}] {self.description}"

@dataclass
class Plan:
    task:      str
    mode:      PlanMode
    steps:     List[PlanStep]
    reasoning: str = ""
    risks:     List[str] = field(default_factory=list)
    rollback:  str = ""
    created_at: float = field(default_factory=time.time)

    def to_text(self) -> str:
        lines = [f"📋 <b>План</b> [{self.mode.value}]", f"Задача: {self.task}", ""]
        if self.reasoning:
            lines += [f"💭 {self.reasoning}", ""]
        lines.append("Шаги:")
        lines += [s.to_text() for s in self.steps]
        if self.risks:
            lines += ["", "⚠️ Риски: " + ", ".join(self.risks)]
        if self.rollback:
            lines += ["", f"↩️ Откат: {self.rollback}"]
        return "\n".join(lines)


_HEURISTIC_MAP = {
    'tts':               ['озвучь','tts','голос','speech','произнеси'],
    'moviepy_edit':      ['видео','video','ролик','монтаж','moviepy','слайд'],
    'pollinations_image':['картинк','изображ','нарисуй','image','generate','фото'],
    'python_sandbox':    ['запусти код','выполни','sandbox','питон','python'],
    'web_search':        ['найди','поищи','search','загугли','информация о'],
    'fetch_url':         ['скачай страницу','fetch','парс','загрузи сайт'],
    'create_file':       ['создай файл','сохрани в файл','запиши в'],
    'code_agent':        ['напиши код','создай скрипт','scaffold','patch','исправь баг'],
    'install_package':   ['установи пакет','pip install','нужен пакет'],
}

def _heuristic_steps(task: str) -> List[dict]:
    kw = task.lower()
    steps = []
    for tool, keywords in _HEURISTIC_MAP.items():
        if any(k in kw for k in keywords):
            steps.append({
                'step_id': len(steps)+1, 'tool': tool,
                'args': {'input': task},
                'description': f'Выполнить {tool}',
                'depends_on': [], 'optional': False, 'estimated_s': 15,
            })
    if not steps:
        steps = [{'step_id':1,'tool':'chat','args':{'message':task},
                  'description':'Ответить','depends_on':[],'optional':False,'estimated_s':5}]
    return steps


class Planner:
    def __init__(self, llm_caller: Callable = None):
        self._llm = llm_caller

    def plan(self, task: str, mode: PlanMode = PlanMode.AUTO,
             context: str = '') -> Plan:
        """Создаёт план выполнения задачи."""
        # Пробуем LLM-план
        if self._llm:
            try:
                return self._llm_plan(task, mode, context)
            except Exception:
                pass
        # Fallback: эвристика
        return self._heuristic_plan(task, mode)

    def _llm_plan(self, task: str, mode: PlanMode, context: str) -> Plan:
        try:
            from agent_tools_registry import get_tools_list
            tools_ctx = get_tools_list()[:2000]
        except Exception:
            tools_ctx = ""

        system = (
            "Ты планировщик задач. Составь план выполнения в JSON.\n"
            f"Доступные инструменты:\n{tools_ctx}\n\n"
            'Формат: {"mode":"direct","reasoning":"...","risks":[],"rollback":"","steps":['
            '{"step_id":1,"tool":"tts","args":{"text":"привет"},"description":"...","depends_on":[],"optional":false,"estimated_s":10}]}'
        )
        prompt = f"Задача: {task}"
        if context:
            prompt += f"\n\nКонтекст:\n{context[:500]}"

        raw = self._llm(prompt, system)
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        data = json.loads(m.group() if m else raw)
        return self._from_dict(task, data)

    def _heuristic_plan(self, task: str, mode: PlanMode) -> Plan:
        steps_data = _heuristic_steps(task)
        detected_mode = PlanMode.DIRECT if len(steps_data)==1 else PlanMode.AUTO
        return self._from_dict(task, {
            'mode': detected_mode.value,
            'reasoning': 'Эвристический анализ',
            'risks': [], 'rollback': '',
            'steps': steps_data,
        })

    def _from_dict(self, task: str, data: dict) -> Plan:
        steps = [
            PlanStep(
                step_id=s.get('step_id', i+1),
                tool=s.get('tool','chat'),
                args=s.get('args', {'input': task}),
                description=s.get('description',''),
                depends_on=s.get('depends_on',[]),
                optional=s.get('optional',False),
                estimated_s=s.get('estimated_s',10),
            )
            for i, s in enumerate(data.get('steps',[]))
        ]
        try:
            pm = PlanMode(data.get('mode','auto'))
        except ValueError:
            pm = PlanMode.AUTO
        return Plan(
            task=task, mode=pm, steps=steps,
            reasoning=data.get('reasoning',''),
            risks=data.get('risks',[]),
            rollback=data.get('rollback',''),
        )

    def quick_tool(self, task: str) -> Optional[str]:
        """Быстро определяет один нужный инструмент."""
        kw = task.lower()
        for tool, keywords in _HEURISTIC_MAP.items():
            if any(k in kw for k in keywords):
                return tool
        return None
