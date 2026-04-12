"""
core/agent_base.py — Base Agent Class
All agents inherit from this. Provides: LLM, tools, memory, sandbox, artifact builder.
"""
from __future__ import annotations
import os, re, json, time, ast, zipfile, threading
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Callable, List, Dict, Tuple
import config
from core import tool_registry as TR


@dataclass
class AgentResult:
    ok:         bool = False
    answer:     str = ""
    zip_path:   str = ""
    tts_path:   str = ""
    files:      List[str] = field(default_factory=list)
    steps_log:  List[dict] = field(default_factory=list)
    generated_tools: List[str] = field(default_factory=list)
    mode:       str = "auto"
    agent:      str = ""
    error:      str = ""
    duration:   float = 0.0

    def to_dict(self) -> dict:
        return {
            "ok": self.ok, "answer": self.answer[:2000], "zip_path": self.zip_path,
            "tts_path": self.tts_path, "files": self.files[:20],
            "mode": self.mode, "agent": self.agent, "error": self.error,
            "duration": self.duration, "generated_tools": self.generated_tools,
            "steps": len(self.steps_log),
        }


PLANNER_SYSTEM = """Ты — планировщик AI-агента. Анализируй задачу и верни JSON.
Отвечай ТОЛЬКО валидным JSON без markdown.

ВСТРОЕННЫЕ ИНСТРУМЕНТЫ (tool_exists=true):
  python_eval, shell_cmd, web_scraper, file_read, file_write,
  image_gen, tts_speak, send_mail, smith_template, analyze_code, run_script,
  csv_reader, csv_writer, pdf_reader, zip_extractor, json_transformer, file_search,
  http_get, http_post, rss_parser, html_scraper, api_caller, git_info,
  data_aggregator, text_extractor, diff_tool, dedup_tool,
  requirements_installer, telegram_notify, webhook_sender,
  github_clone, github_install_tool, pip_install,
  osint_sherlock, osint_username_search, osint_site_search,
  self_create_tool, self_list_tools, self_delete_tool,
  nmap_scan, nuclei_scan, whatweb_scan, testssl_scan,
  sqlmap_scan, nikto_scan, gobuster_scan, metasploit_run

ПРАВИЛА:
1. Минимум шагов: 1-4 для простых задач
2. GitHub URL → github_install_tool
3. Изображение → image_gen (prompt на английском)
4. OSINT → osint_sherlock / osint_username_search
5. Сканирование → nmap_scan / nuclei_scan

ФОРМАТ:
{"steps":[{"id":1,"description":"...","tool_name":"...","tool_exists":true,
  "inputs":{"key":"val"},"depends_on":[]}],
 "final_summary":"..."}"""


class AgentBase:
    """Base class for all BlackBugsAI agents."""

    NAME = "base"
    EMOJI = "🤖"
    SYSTEM_PROMPT = "Ты AI-агент BlackBugsAI. Отвечай на русском."
    MODES = ["auto"]
    ACCESS = ["god", "owner", "adm", "vip", "user"]  # who can use

    def __init__(self):
        self._status_fn: Optional[Callable] = None

    def status(self, msg: str):
        if self._status_fn:
            self._status_fn(msg)

    # ── LLM helpers ───────────────────────────────────────────────────────────

    def llm(self, prompt: str, system: str = "", max_tokens: int = 4000, role: str = "agent") -> str:
        try:
            from llm_router import call_llm_for
            return call_llm_for(role, prompt, system or self.SYSTEM_PROMPT, max_tokens)
        except Exception:
            from llm_client import call_llm
            return call_llm(prompt, system or self.SYSTEM_PROMPT, max_tokens)

    def llm_json(self, prompt: str, system: str = "") -> Optional[dict]:
        raw = self.llm(prompt, system, max_tokens=3000)
        raw = re.sub(r"```json\s*", "", raw)
        raw = re.sub(r"```\s*", "", raw)
        m = re.search(r'\{.*\}', raw.strip(), re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except json.JSONDecodeError:
                pass
        return None

    # ── Tool execution ────────────────────────────────────────────────────────

    def run_tool(self, name: str, inputs: dict) -> Tuple[bool, str, list]:
        return TR.execute(name, inputs, on_status=self._status_fn)

    def generate_tool(self, name: str, desc: str, inputs: dict) -> Tuple[bool, str]:
        return TR.generate_tool(name, desc, inputs, on_status=self._status_fn)

    def install_github_tool(self, url: str, name: str = "") -> Tuple[bool, str, str]:
        return TR.install_github(url, name, on_status=self._status_fn)

    # ── Planning ──────────────────────────────────────────────────────────────

    def plan(self, task: str, chat_id: str, files: list = None) -> dict:
        """Create execution plan via LLM."""
        context = ""
        try:
            from core.memory_store import MemoryStore
            context = MemoryStore.build_context(chat_id, task)
        except Exception:
            pass

        dyn = [t["name"] for t in TR.list_all() if not t.get("builtin")]
        hints = f"\nДинамические инструменты: {', '.join(dyn[:15])}" if dyn else ""
        fhints = f"\nФайлы: {', '.join(files)}" if files else ""

        prompt = f"Задача: {task}{fhints}{hints}\nКонтекст:\n{context}\n\nВерни JSON план."
        plan = self.llm_json(prompt, PLANNER_SYSTEM)
        if not plan or "steps" not in plan:
            plan = {"steps": [{"id": 1, "description": task, "tool_name": "run_script",
                                "tool_exists": True, "inputs": {"task": task}, "depends_on": []}],
                    "final_summary": task[:80]}
        return plan

    # ── Execution pipeline ────────────────────────────────────────────────────

    def execute(self, task: str, chat_id: int, files: list = None,
                mode: str = "auto", on_status: Callable = None) -> AgentResult:
        """Main execution pipeline — override in subclasses for custom logic."""
        t0 = time.time()
        self._status_fn = on_status
        self.status(f"{self.EMOJI} {self.NAME} [{mode}] анализирует...")

        plan = self.plan(task, str(chat_id), files)
        steps = plan.get("steps", [])
        self.status(f"📋 План: {len(steps)} шагов")

        steps_log = []
        generated = []
        all_files = []
        step_results: Dict[int, dict] = {}
        final_answer = ""

        for step in steps:
            sid = step.get("id", 0)
            tool = step.get("tool_name", "run_script")
            desc = step.get("description", "")
            sinp = dict(step.get("inputs", {}))
            self.status(f"[{sid}/{len(steps)}] {desc[:60]}...")

            # Inject deps
            for dep in step.get("depends_on", []):
                if dep in step_results:
                    sinp[f"dep_{dep}_output"] = step_results[dep].get("output", "")
            if files:
                sinp.setdefault("files", files)
            sinp["chat_id"] = str(chat_id)
            sinp["task"] = task

            slog = {"id": sid, "description": desc, "tool": tool,
                    "ts": time.strftime('%H:%M:%S'), "ok": False,
                    "output": "", "error": "", "files": []}

            # Check/generate tool
            if not TR.exists(tool):
                self.status(f"  🔨 Генерирую {tool}...")
                gen_ok, gen_err = self.generate_tool(tool, desc, sinp)
                if gen_ok:
                    generated.append(tool)
                else:
                    slog["error"] = f"Gen failed: {gen_err}"
                    steps_log.append(slog)
                    continue

            # Execute
            try:
                ok, output, fls = self.run_tool(tool, sinp)
                slog.update({"ok": ok, "output": output, "files": fls,
                              "error": "" if ok else output[:300]})
                step_results[sid] = slog
                all_files.extend(fls)
                if ok and output:
                    final_answer = output
            except Exception as exc:
                slog["error"] = str(exc)[:300]

            steps_log.append(slog)

        # Synthesize answer
        all_failed = bool(steps_log) and all(not s.get('ok') for s in steps_log)
        if all_failed:
            msgs = [f"Шаг {s['id']}: {(s.get('error') or s.get('output',''))[:200]}" for s in steps_log]
            final_answer = "Ошибка:\n" + "\n".join(msgs)
        if not final_answer:
            final_answer = plan.get("final_summary", "Задача выполнена")

        # Multi-step summary
        if len(steps) > 1 and not all_failed:
            try:
                out_text = "\n".join(f"Step {s['id']}: {str(s['output'])[:300]}" for s in steps_log if s.get("output"))
                summary = self.llm(f"Task: {task}\n\nResults:\n{out_text}\n\nИтог на русском.",
                                   "Summarize concisely.", 1000)
                if summary and len(summary) > 20:
                    final_answer = summary
            except Exception:
                pass

        # Build artifact
        zip_path = self._build_zip(task, plan, steps_log, final_answer, all_files, generated)

        # TTS
        tts_path = self._tts(final_answer)

        # Memory
        duration = time.time() - t0
        self._save_memory(str(chat_id), task, steps_log, final_answer, duration)

        ok_overall = any(s.get("ok") for s in steps_log)
        self.status(f"{'✅' if ok_overall else '⚠️'} {self.NAME} [{mode}] — {duration:.1f}с")

        return AgentResult(
            ok=ok_overall, answer=final_answer, zip_path=zip_path,
            tts_path=tts_path, files=list(set(all_files)),
            steps_log=steps_log, generated_tools=generated,
            mode=mode, agent=self.NAME, duration=duration,
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _build_zip(self, task, plan, steps_log, answer, all_files, generated) -> str:
        ts = int(time.time())
        artifacts_dir = Path(config.BASE_DIR) / "artifacts"
        artifacts_dir.mkdir(exist_ok=True)
        zip_path = str(artifacts_dir / f"{self.NAME}_{ts}.zip")

        report = [f"# {self.NAME} Report", f"Task: {task}",
                  f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}", "", "## Answer", answer, ""]
        for s in steps_log:
            icon = "OK" if s.get("ok") else "FAIL"
            report.append(f"### [{icon}] Step {s.get('id')}: {s.get('description')}")
            if s.get("output"):
                report.append(f"```\n{str(s['output'])[:500]}\n```")

        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("report.md", "\n".join(report))
                zf.writestr("plan.json", json.dumps(plan, ensure_ascii=False, indent=2))
                zf.writestr("answer.txt", answer)
                added = 0
                for fp in all_files:
                    if os.path.isfile(fp) and added < 30:
                        try:
                            zf.write(fp, f"output/{os.path.basename(fp)}")
                            added += 1
                        except Exception:
                            pass
                for tn in generated:
                    tf = TR.TOOLS_DIR / f"{tn}.py"
                    if tf.exists():
                        zf.write(str(tf), f"tools/{tn}.py")
        except Exception:
            pass
        return zip_path

    def _tts(self, text: str) -> str:
        try:
            from tts_engine import synthesize
            clean = re.sub(r'[*_`#<>]', '', text[:900])
            clean = re.sub(r'\n+', ' ', clean).strip()
            if len(clean) > 30:
                return synthesize(clean, f"{self.NAME}_{int(time.time())}.mp3")
        except Exception:
            pass
        return ""

    def _save_memory(self, chat_id, task, steps_log, answer, duration):
        try:
            from core.memory_store import MemoryStore
            MemoryStore.after_task(
                chat_id, task, [s["tool"] for s in steps_log],
                answer[:500], "done" if any(s.get("ok") for s in steps_log) else "error",
                duration)
        except Exception:
            pass
