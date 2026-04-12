"""
agent_matrix_patch.py — патч поверх agent_matrix.py
Применяет: learning loop, skill evolution, трассировка, fix chat_id

Как применить:
  python3 agent_matrix_patch.py
"""
import re
from pathlib import Path

SRC = Path("agent_matrix.py")

# ─── 1. Patch imports ─────────────────────────────────────────────────────────

IMPORT_INSERT = """
# ── Learning Loop + Trace ─────────────────────────────────────────────────────
try:
    from learning_loop import (
        TraceContext, extract_and_save_skill,
        build_skill_context, get_relevant_skills,
    )
    LEARNING_LOOP_OK = True
except ImportError:
    LEARNING_LOOP_OK = False
    class TraceContext:
        def __init__(self, *a, **kw): self.run_id=""; self.steps=[]; self.plan={}
        def add_step(self, *a, **kw): pass
        def finish(self, *a, **kw): return ""
    def build_skill_context(task): return ""
    def extract_and_save_skill(*a, **kw): return None
"""

# ─── 2. Patch run_matrix signature (make chat_id optional) ────────────────────

OLD_SIG = """def run_matrix(
    task: str,
    chat_id: str,
    attached_files: Optional[list] = None,
    on_status: Optional[Callable] = None,
) -> MatrixResult:
    \"\"\"Главный pipeline AGENT MATRIX v2.0.\"\"\""""

NEW_SIG = """def run_matrix(
    task: str,
    chat_id: str = "admin",          # ← default=admin fixes missing chat_id error
    attached_files: Optional[list] = None,
    on_status: Optional[Callable] = None,
    _trace: bool = True,
) -> MatrixResult:
    \"\"\"Главный pipeline AGENT MATRIX v2.0 + Learning Loop.\"\"\""""

# ─── 3. Inject skill context into plan_task ───────────────────────────────────

OLD_PLAN_TASK = """def plan_task(task: str, chat_id: str, attached_files: Optional[list] = None) -> dict:"""

NEW_PLAN_TASK = """def plan_task(task: str, chat_id: str = "admin", attached_files: Optional[list] = None) -> dict:
    # Inject skill context for few-shot learning
    skill_ctx = build_skill_context(task) if LEARNING_LOOP_OK else ""
    if skill_ctx:
        task = task + "\\n\\n" + skill_ctx
"""

# ─── 4. Inject trace + learning at start/end of run_matrix ────────────────────

OLD_RUN_START = """    t0 = time.time()

    def st(msg):
        if on_status: on_status(msg)"""

NEW_RUN_START = """    t0 = time.time()
    _tc = TraceContext(str(chat_id), task) if _trace else TraceContext("_", "_")

    def st(msg):
        if on_status: on_status(msg)"""

OLD_RUN_END = """    return MatrixResult(
        ok=not bool(step_errors),
        answer=answer,
        error=\"; \".join(step_errors),
        zip_path=zip_path,
        tts_path=tts_path,
        files=all_files,
        steps_done=steps_done,
        generated_tools=generated_tools,
    )"""

NEW_RUN_END = """    _mx_result = MatrixResult(
        ok=not bool(step_errors),
        answer=answer,
        error=\"; \".join(step_errors),
        zip_path=zip_path,
        tts_path=tts_path,
        files=all_files,
        steps_done=steps_done,
        generated_tools=generated_tools,
    )

    # ── Learning Loop: сохраняем skill после каждой задачи ───────────────────
    if LEARNING_LOOP_OK and _trace:
        try:
            steps_result = [{"ok": True} for _ in range(steps_done)]
            if step_errors:
                for e in step_errors:
                    steps_result.append({"ok": False, "error": e})
            extract_and_save_skill(
                task=task, tools_used=list(set(
                    s.get("tool_name","") for s in (steps or [])
                    if isinstance(s, dict)
                )),
                steps_result=steps_result,
                final_ok=not bool(step_errors),
                answer=answer[:300],
                llm_call=lambda p, s: _llm(p, s, max_tokens=200),
            )
            _tc.finish(
                ok=not bool(step_errors),
                result=answer[:500],
                error=\"; \".join(step_errors),
            )
        except Exception as _le:
            print(f"⚠️ Learning loop error: {_le}", flush=True)

    return _mx_result"""

def apply_patch():
    if not SRC.exists():
        print(f"❌ {SRC} not found")
        return

    content = SRC.read_text(encoding="utf-8")

    # Check if already patched
    if "LEARNING_LOOP_OK" in content and "default=admin" in content:
        print("ℹ️  agent_matrix.py already patched")
        return

    changes = 0

    # 1. Add imports after existing imports block
    if "from learning_loop import" not in content:
        # Insert after first 'import config' line
        content = content.replace(
            "import config\n",
            "import config\n" + IMPORT_INSERT, 1
        )
        changes += 1
        print("✅ Imports injected")

    # 2. Fix run_matrix signature
    if 'chat_id: str = "admin"' not in content:
        if OLD_SIG in content:
            content = content.replace(OLD_SIG, NEW_SIG)
            changes += 1
            print("✅ run_matrix signature fixed (chat_id default='admin')")
        else:
            # Minimal fix: just make chat_id optional
            content = content.replace(
                "def run_matrix(\n    task: str,\n    chat_id: str,",
                "def run_matrix(\n    task: str,\n    chat_id: str = 'admin',"
            )
            changes += 1
            print("✅ run_matrix chat_id default applied (fallback)")

    # 3. Fix plan_task signature
    if 'chat_id: str = "admin"' not in content:
        content = content.replace(
            'def plan_task(task: str, chat_id: str,',
            'def plan_task(task: str, chat_id: str = "admin",'
        )

    # 4. Fix run_matrix_async
    content = content.replace(
        'def run_matrix_async(task: str, chat_id: str,',
        'def run_matrix_async(task: str, chat_id: str = "admin",'
    )

    # 5. Inject trace context
    if "TraceContext" not in content and "_tc = TraceContext" not in content:
        content = content.replace(OLD_RUN_START, NEW_RUN_START)
        changes += 1
        print("✅ TraceContext injected at run start")

    # 6. Inject learning loop at end
    if "Learning Loop" not in content:
        if OLD_RUN_END in content:
            content = content.replace(OLD_RUN_END, NEW_RUN_END)
            changes += 1
            print("✅ Learning Loop injected at run end")

    # 7. Fix any remaining timeout=60 (paranoia check)
    bad = len(re.findall(r'\btimeout\s*=\s*60\b', content))
    if bad:
        content = re.sub(r'\btimeout\s*=\s*60\b', 'timeout=600', content)
        changes += 1
        print(f"✅ Fixed {bad} remaining timeout=60 → 600")

    # 8. Fix SANDBOX config timeout
    content = content.replace(
        "'timeout_default': int(get('SANDBOX_TIMEOUT', '30'))",
        "'timeout_default': int(get('SANDBOX_TIMEOUT', '600'))"
    )

    # Write back
    SRC.write_text(content, encoding="utf-8")
    print(f"\n✅ agent_matrix.py patched ({changes} changes applied)")

if __name__ == "__main__":
    apply_patch()
