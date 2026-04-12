"""
agents/operator.py — AGENT OPERATOR
Owner only. Meta-agent: controls and coordinates all other agents.
Can delegate sub-tasks to NEO, MATRIX, SMITH, etc.
"""
from core.agent_base import AgentBase, AgentResult
from core import tool_registry as TR
import time, json, re


class AgentOperator(AgentBase):
    """🎯 Мета-агент: оркестрация всех агентов, review/fix/analyze"""

    NAME = "OPERATOR"
    EMOJI = "🎯"
    ACCESS = ["god", "owner"]
    MODES = ["auto", "orchestrate", "review", "fix", "analyze"]

    SYSTEM_PROMPT = """Ты — AGENT OPERATOR, мета-агент BlackBugsAI.
Ты управляешь другими агентами: NEO, MATRIX, SMITH, TANKER, ANDERSON, PYTHIA.

Твоя задача — разбить сложную задачу на подзадачи и делегировать каждую
наиболее подходящему агенту.

Агенты:
- NEO: self-tool gen, sandbox, GitHub install, OSINT, pentest
- MATRIX: unified coder/pentester/osint
- SMITH: autofix pipeline, security audit, orchestration
- TANKER: multitool, code chains (публичный)
- ANDERSON: vulnerability analysis, code fixing
- PYTHIA: quick coding, project scaffold, review

Ответ — JSON:
{"subtasks": [
  {"agent": "neo", "task": "описание подзадачи", "priority": 1},
  {"agent": "smith", "task": "...", "priority": 2}
], "strategy": "описание стратегии"}"""

    def execute(self, task, chat_id, files=None, mode="auto", on_status=None):
        """OPERATOR: decompose → delegate to agents → merge results."""
        t0 = time.time()
        self._status_fn = on_status
        self.status(f"{self.EMOJI} OPERATOR анализирует задачу...")

        # 1. Decompose task into subtasks
        plan = self._decompose(task)
        subtasks = plan.get("subtasks", [])
        strategy = plan.get("strategy", "Sequential execution")
        self.status(f"📋 Стратегия: {strategy}")
        self.status(f"📋 Подзадачи: {len(subtasks)}")

        if not subtasks:
            # Fallback: single task via PYTHIA
            subtasks = [{"agent": "pythia", "task": task, "priority": 1}]

        # 2. Execute each subtask
        results = []
        all_files = []
        steps_log = []
        generated = []

        for i, st in enumerate(sorted(subtasks, key=lambda x: x.get("priority", 5))):
            agent_name = st.get("agent", "pythia")
            sub_task = st.get("task", task)
            self.status(f"[{i+1}/{len(subtasks)}] → {agent_name.upper()}: {sub_task[:50]}...")

            try:
                from agents import create_agent
                agent = create_agent(agent_name)
                if not agent:
                    agent = create_agent("pythia")

                result = agent.execute(
                    task=sub_task, chat_id=chat_id,
                    files=files, mode="auto", on_status=on_status,
                )
                results.append(result)
                all_files.extend(result.files)
                generated.extend(result.generated_tools)
                steps_log.append({
                    "id": i+1, "description": f"[{agent_name}] {sub_task[:60]}",
                    "tool": agent_name, "ok": result.ok,
                    "output": result.answer[:300], "error": result.error,
                    "ts": time.strftime('%H:%M:%S'), "files": result.files,
                })
            except Exception as exc:
                steps_log.append({
                    "id": i+1, "description": f"[{agent_name}] {sub_task[:60]}",
                    "tool": agent_name, "ok": False,
                    "output": "", "error": str(exc)[:300],
                    "ts": time.strftime('%H:%M:%S'), "files": [],
                })

        # 3. Merge results
        answers = [r.answer for r in results if r.ok and r.answer]
        final = "\n\n---\n\n".join(answers) if answers else "Ошибка во всех подзадачах"

        # Summarize if multiple
        if len(answers) > 1:
            try:
                summary = self.llm(
                    f"Задача: {task}\n\nРезультаты агентов:\n{final[:2000]}\n\nСинтезируй финальный ответ.",
                    "Объедини результаты кратко.", 1000)
                if summary and len(summary) > 20:
                    final = summary
            except Exception:
                pass

        duration = time.time() - t0
        zip_path = self._build_zip(task, {"subtasks": subtasks, "strategy": strategy},
                                    steps_log, final, all_files, generated)

        self.status(f"{'✅' if any(r.ok for r in results) else '⚠️'} OPERATOR — {duration:.1f}с")

        return AgentResult(
            ok=any(r.ok for r in results),
            answer=final, zip_path=zip_path,
            files=list(set(all_files)),
            steps_log=steps_log,
            generated_tools=generated,
            mode=mode, agent=self.NAME, duration=duration,
        )

    def _decompose(self, task: str) -> dict:
        """Use LLM to decompose task into agent subtasks."""
        result = self.llm_json(
            f"Задача: {task}\n\nРазбей на подзадачи для агентов.",
            self.SYSTEM_PROMPT)
        if result and "subtasks" in result:
            return result
        # Fallback: single task
        return {"subtasks": [{"agent": "pythia", "task": task, "priority": 1}],
                "strategy": "Single agent execution"}
