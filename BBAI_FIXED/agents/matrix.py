"""
agents/matrix.py — AGENT MATRIX
Owner only. Unified super-agent: Coder + Tester + OSINT + Pentester.
Self-tool gen + GitHub install + multitool.
"""
from core.agent_base import AgentBase, AgentResult
from core import tool_registry as TR
import time, re


class AgentMatrix(AgentBase):
    """🟥 Универсальный агент: Coder + OSINT + Pentester + self-tool gen"""

    NAME = "MATRIX"
    EMOJI = "🟥"
    ACCESS = ["god", "owner"]
    MODES = ["auto", "code", "test", "osint", "pentest", "project", "review", "sandbox"]

    SYSTEM_PROMPT = """Ты — AGENT MATRIX, универсальный AI-агент BlackBugsAI.
Роли: Кодер · Тестер · OSINT · Pentester · Оркестратор.
Отвечай ТОЛЬКО на русском.

[КОДЕР] Python/JS/Bash — subprocess, PIL, asyncio
[ТЕСТЕР] pytest, coverage, ast.parse, pip-audit
[OSINT] Sherlock, GitHub API, WHOIS, DNS, публичные профили
[PENTESTER] nmap, nuclei, whatweb, testssl, sqlmap, nikto, gobuster (ТОЛЬКО авторизованные цели)
[ОРКЕСТРАТОР] Декомпозиция → выполнение → сборка результатов

def run_tool(inputs: dict) -> dict → {"ok": bool, "output": str, "files": list, "error": str}"""

    def execute(self, task, chat_id, files=None, mode="auto", on_status=None):
        """MATRIX auto-detects mode and runs enhanced pipeline."""
        self._status_fn = on_status
        if mode == "auto":
            mode = self._detect_mode(task)
        self.status(f"{self.EMOJI} MATRIX [{mode}]...")
        return super().execute(task, chat_id, files, mode, on_status)

    def _detect_mode(self, task: str) -> str:
        t = task.lower()
        if any(k in t for k in ["nmap", "scan", "pentest", "пентест", "порт", "уязвим"]):
            return "pentest"
        if any(k in t for k in ["osint", "sherlock", "username", "whois", "dns"]):
            return "osint"
        if any(k in t for k in ["тест", "test", "pytest", "coverage"]):
            return "test"
        if any(k in t for k in ["проект", "project", "структур"]):
            return "project"
        if any(k in t for k in ["ревью", "review", "проверь код"]):
            return "review"
        return "code"
