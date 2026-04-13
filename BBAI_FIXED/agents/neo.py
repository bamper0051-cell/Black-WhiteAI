"""
agents/neo.py — AGENT NEO
Owner only. Autonomous self-tool-generating agent.
Multi-file, dynamic sandbox, GitHub install, full ZIP artifacts.
"""
from core.agent_base import AgentBase


class AgentNeo(AgentBase):
    """🟢 Автономный агент с self-tool generation, sandbox, многофайловость"""

    NAME = "NEO"
    EMOJI = "🟢"
    ACCESS = ["god", "owner"]
    MODES = ["auto", "code", "osint", "pentest", "project", "sandbox"]

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
        """NEO pipeline: plan → check/generate tools → sandbox → ZIP → TTS."""
        # NEO uses base pipeline but with extended tool generation
        return super().execute(task, chat_id, files, mode, on_status)
