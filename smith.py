"""
agents/smith.py — AGENT SMITH (Observer)
Admin+. Autonomous pipeline + 15 autofix + smart syntax repair.
Security audit, auto-fix, orchestration, event sourcing.
"""
from core.agent_base import AgentBase, AgentResult
from core.agent_brain import BrainMixin
from core import tool_registry as TR
import time, ast, re


class AgentSmith(BrainMixin, AgentBase):
    """🕵️ Автономный pipeline: plan→generate→lint→sandbox→autofix(x15)→ZIP"""

    NAME = "SMITH"
    EMOJI = "🕵️"
    ACCESS = ["god", "owner", "adm"]
    MODES = ["auto", "code", "autofix", "security", "orchestrate"]

    SYSTEM_PROMPT = """Ты — АГЕНТ_СМИТ, автономный AI-агент для написания Python-кода.
Пиши ТОЛЬКО рабочий Python-код.
Правила:
1. НЕ используй Unicode em-dash (U+2014) или умные кавычки в коде
2. Код должен запускаться без аргументов
3. Пиши в блоке: ```python ... ```
4. Если нужен пакет — добавь pip install через subprocess"""

    # Brain настройки
    BRAIN_REFLEXION = False   # Smith — кодер, рефлексия через autofix
    BRAIN_LINTING   = True    # ruff для кода
    BRAIN_DELEGATE  = True    # Smith может делегировать MATRIX/NEO
    BRAIN_MIN_SCORE = 6

    MAX_AUTOFIX = 15

    def execute(self, task, chat_id, files=None, mode="auto", on_status=None):
        """SMITH pipeline with extended autofix and security audit."""
        self._status_fn = on_status

        if mode == "security":
            return self._security_audit(task, chat_id, files)
        if mode == "orchestrate":
            return self._orchestrate(task, chat_id, files)

        # Default: delegate to agent_session.py (existing SMITH pipeline)
        try:
            return self._run_smith_pipeline(task, chat_id, files)
        except Exception:
            # Fallback to base pipeline
            return super().execute(task, chat_id, files, mode, on_status)

    def _run_smith_pipeline(self, task, chat_id, files):
        """Use existing agent_session.py SMITH pipeline."""
        from agent_session import create_session, execute_pipeline, close_session
        import os

        t0 = time.time()
        cid = str(chat_id)
        sess = create_session(cid)
        sess.task = task

        result = execute_pipeline(sess, on_status=self._status_fn)
        close_session(cid)

        zip_path = result.get("zip_path", "")
        answer = result.get("output", "SMITH pipeline завершён")
        fls = []
        if zip_path and os.path.exists(zip_path):
            fls.append(zip_path)

        return AgentResult(
            ok=result.get("ok", False), answer=answer,
            zip_path=zip_path, files=fls,
            agent=self.NAME, mode="code",
            duration=time.time() - t0,
        )

    def _security_audit(self, task, chat_id, files):
        """Run security audit on provided code/project."""
        self.status("🔒 Security Audit...")
        # Use pip-audit + bandit + ast analysis
        steps = [
            {"id": 1, "description": "Статический анализ кода", "tool_name": "analyze_code",
             "tool_exists": True, "inputs": {"task": task, "file_path": files[0] if files else ""},
             "depends_on": []},
        ]
        plan = {"steps": steps, "final_summary": "Security audit"}
        # Run through base pipeline
        return super().execute(task, chat_id, files, "security", self._status_fn)

    def _orchestrate(self, task, chat_id, files):
        """Orchestrate multiple agents for complex tasks."""
        self.status("🎭 Оркестрация...")
        # For now, delegate to base pipeline
        return super().execute(task, chat_id, files, "orchestrate", self._status_fn)
