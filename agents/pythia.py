"""
agents/pythia.py — AGENT PYTHIA
Public. Coder agent: quick, autofix, project, review, sandbox.
Separate orchestrator with own sandbox + multi-file support.
"""
from core.agent_base import AgentBase, AgentResult
import time, os


class AgentPythia(AgentBase):
    """💻 Кодер: quick/project/review/sandbox/autofix + многофайловость"""

    NAME = "PYTHIA"
    EMOJI = "💻"
    ACCESS = ["god", "owner", "adm", "vip", "user"]
    MODES = ["auto", "quick", "autofix", "project", "review", "sandbox"]

    SYSTEM_PROMPT = """Ты — AGENT PYTHIA, кодер-агент BlackBugsAI.
Доступен всем пользователям.

Режимы:
- quick: быстрая генерация + smoke-run
- autofix: до 5 попыток исправления
- project: многофайловый проект
- review: code review
- sandbox: запуск кода в песочнице

Правила:
1. Пиши чистый, рабочий Python
2. Добавляй docstrings и type hints
3. Обрабатывай исключения
4. ```python ... ``` для кода
5. Проверяй через ast.parse перед отправкой"""

    def execute(self, task, chat_id, files=None, mode="auto", on_status=None):
        self._status_fn = on_status

        if mode == "auto":
            t = task.lower()
            if any(k in t for k in ["проект", "project", "структур", "несколько файлов"]):
                mode = "project"
            elif any(k in t for k in ["ревью", "review", "проверь код"]):
                mode = "review"
            elif any(k in t for k in ["запусти", "sandbox", "выполни"]):
                mode = "sandbox"
            else:
                mode = "quick"

        # Try coder3 first for advanced modes
        if mode in ("project", "review"):
            try:
                return self._run_coder3(task, chat_id, files, mode)
            except Exception:
                pass

        # Default: base pipeline
        return super().execute(task, chat_id, files, mode, on_status)

    def _run_coder3(self, task, chat_id, files, mode):
        """Delegate to coder3 engine if available."""
        t0 = time.time()
        try:
            from coder3.engine import run_coder3
            result = run_coder3(task, mode=mode, workspace=None)
            return AgentResult(
                ok=result.get("ok", False),
                answer=result.get("output", "Coder3 завершён"),
                zip_path=result.get("zip_path", ""),
                files=result.get("files", []),
                agent=self.NAME, mode=mode,
                duration=time.time() - t0,
            )
        except ImportError:
            raise  # Let caller handle fallback
