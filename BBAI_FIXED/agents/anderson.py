"""
agents/anderson.py — MR. ANDERSON
Public. Vulnerability analysis, code fixing, VulnSage pipeline.
Reflection + hybrid pipeline + self-tool gen.
"""
from core.agent_base import AgentBase


class AgentAnderson(AgentBase):
    """🔍 Анализ уязвимостей, исправление кода, рефлексия"""

    NAME = "ANDERSON"
    EMOJI = "🔍"
    ACCESS = ["god", "owner", "adm", "vip", "user"]
    MODES = ["auto", "vuln_scan", "code_fix", "review"]

    SYSTEM_PROMPT = """Ты — MR. ANDERSON, AI-агент для анализа безопасности кода.
Режимы:
- vuln_scan: поиск уязвимостей в коде (SQL injection, XSS, CSRF, path traversal)
- code_fix: автоматическое исправление найденных уязвимостей
- review: полный code review с рекомендациями

Алгоритм:
1. Получи код → проанализируй через ast + паттерны
2. Найди уязвимости → составь отчёт
3. Предложи исправления → сгенерируй патч
4. Рефлексия: проверь что фикс не сломал логику

Всё на русском. Формат: JSON с findings."""

    def execute(self, task, chat_id, files=None, mode="auto", on_status=None):
        self._status_fn = on_status
        if mode == "auto":
            t = task.lower()
            if any(k in t for k in ["уязвим", "vuln", "injection", "xss"]):
                mode = "vuln_scan"
            elif any(k in t for k in ["исправ", "fix", "патч", "patch"]):
                mode = "code_fix"
            else:
                mode = "review"
        return super().execute(task, chat_id, files, mode, on_status)
