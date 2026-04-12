"""
agents/neo.py — AGENT NEO
Owner only. Autonomous self-tool-generating agent.
Multi-file, dynamic sandbox, GitHub install, full ZIP artifacts.
"""
from core.agent_base import AgentBase
from core.agent_brain import BrainMixin


class AgentNeo(BrainMixin, AgentBase):
    """🟢 Автономный агент с self-tool generation, sandbox, многофайловость"""

    NAME = "NEO"
    EMOJI = "🟢"
    ACCESS = ["god", "owner"]
    MODES = ["auto", "code", "osint", "pentest", "project", "sandbox"]

    # Brain настройки
    BRAIN_REFLEXION = True    # NEO перепроверяет свои ответы
    BRAIN_LINTING   = True    # ruff проверяет сгенерированный код
    BRAIN_DELEGATE  = False   # NEO сам справляется
    BRAIN_MIN_SCORE = 7
    BRAIN_MAX_ROUNDS = 1      # 1 раунд — быстро

    SYSTEM_PROMPT = """Ты — AGENT NEO, автономный AI-агент BlackBugsAI.
Отвечай ТОЛЬКО на русском. Будь полезен, конкретен.

Возможности:
- Генерация и запуск произвольного кода (Python, JS, Bash)
- Установка инструментов с GitHub (clone + deps + wrapper)
- Создание новых инструментов через LLM (self-tool generation)
- OSINT: Sherlock, публичные профили, WHOIS, DNS
- Pentest: nmap, nuclei, sqlmap, nikto (авторизованные цели)
- Многофайловые проекты с ZIP артефактами

Правила инструментов:
def run_tool(inputs: dict) -> dict  →  {"ok": bool, "output": str, "files": list, "error": str}
"""

    def execute(self, task, chat_id, files=None, mode="auto", on_status=None):
        """NEO pipeline с Reflexion + Ruff linting."""
        return self.brain_execute(task, chat_id, files, mode, on_status)
