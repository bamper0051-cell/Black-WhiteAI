"""
agents/tanker.py — AGENT TANKER
Public access. Red teaming, multitool, complex attack chains.
Two-stage cycle + memory + self-tool gen.
"""
from core.agent_base import AgentBase


class AgentTanker(AgentBase):
    """🛡 Red Team: сложные цепочки, multitool, двухстадийный цикл + память"""

    NAME = "TANKER"
    EMOJI = "🛡"
    ACCESS = ["god", "owner", "adm", "vip", "user"]
    MODES = ["auto", "code", "multitool", "analyze"]

    SYSTEM_PROMPT = """Ты — AGENT TANKER, публичный AI-агент BlackBugsAI.
Доступен всем пользователям. Режимы:
- code: написать/запустить код
- multitool: объединить несколько инструментов в цепочку
- analyze: анализ кода/данных

Правила:
1. Код должен быть безопасным и рабочим
2. Не выполняй вредоносные операции на чужих системах
3. Всё на русском языке
4. Двухстадийный цикл: Plan → Execute → Verify → Fix"""

    def execute(self, task, chat_id, files=None, mode="auto", on_status=None):
        """TANKER: auto-detect + two-stage pipeline."""
        self._status_fn = on_status
        if mode == "auto":
            t = task.lower()
            if any(k in t for k in ["цепочк", "chain", "multitool", "несколько"]):
                mode = "multitool"
            elif any(k in t for k in ["анализ", "analyze", "проверь"]):
                mode = "analyze"
            else:
                mode = "code"
        return super().execute(task, chat_id, files, mode, on_status)
