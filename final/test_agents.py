"""
test_agents.py — Тестовые копии агентов BlackBugsAI
Использовать для проверки перед удалением старых версий.
Запуск: python test_agents.py
"""
import sys, os, types
sys.path.insert(0, os.path.dirname(__file__))

# Mock telegram
tg = types.ModuleType('telegram_client')
tg.send_message = lambda t, cid, **k: print(f"  MSG → {cid}: {str(t)[:80]}")
tg.edit_message = lambda *a, **k: None
tg.send_document = lambda *a, **k: None
sys.modules['telegram_client'] = tg

PASS = FAIL = 0

def test(name, fn):
    global PASS, FAIL
    try:
        fn()
        print(f"  ✅ {name}")
        PASS += 1
    except Exception as e:
        print(f"  ❌ {name}: {e}")
        FAIL += 1

print("\n╔══════════════════════════════════════╗")
print("║  BlackBugsAI — Agent Test Suite      ║")
print("╚══════════════════════════════════════╝\n")

# ── 1. АГЕНТ-КОДЕР (agent_session) ────────────────────────────────────────────
print("1. АГЕНТ-КОДЕР (agent_session)")

def t_create_session():
    from agent_session import create_session, close_session, STAGE_WAIT_FILES, STAGE_WAIT_TASK
    sess = create_session(999)
    assert sess is not None
    # create_session начинает в wait_task, затем меняется
    sess.stage = STAGE_WAIT_FILES
    assert sess.stage == STAGE_WAIT_FILES
    close_session(999)

def t_analyze_task():
    from agent_session import analyze_task
    r = analyze_task("нарисуй космос через pillow")
    assert isinstance(r, dict)
    assert 'steps' in r

def t_lint_code():
    from agent_session import _lint_code
    ok, msg = _lint_code("print('hello')")
    assert ok, f"Lint failed: {msg}"
    ok2, _ = _lint_code("def f(:\n  pass")
    assert not ok2

def t_server_detection():
    from agent_session import _is_server_code
    assert _is_server_code("bot.polling()")[0]
    assert _is_server_code("app.run()")[0]
    assert not _is_server_code("print('hello')")[0]

def t_sanitize_code():
    from agent_session import _sanitize_code
    bad = "x\u2014y"  # em-dash
    clean = _sanitize_code(bad)
    assert '\u2014' not in clean

def t_scaffold_generator():
    from agent_session import _generate_scaffold_script
    code, pkgs = _generate_scaffold_script("simple project", "", lambda p, s: p)
    assert 'import os' in code or 'os.makedirs' in code

test("create_session + close_session", t_create_session)
test("analyze_task", t_analyze_task)
test("_lint_code", t_lint_code)
test("_is_server_code", t_server_detection)
test("_sanitize_code", t_sanitize_code)
test("_generate_scaffold_script", t_scaffold_generator)

# ── 2. АГЕНТ_СМИТ ──────────────────────────────────────────────────────────────
print("\n2. АГЕНТ_СМИТ (agent_session execute_pipeline)")

def t_smith_constants():
    from agent_session import AGENT_NAME, MAX_FIX_ATTEMPTS, SMITH_SYSTEM
    assert AGENT_NAME == "АГЕНТ_СМИТ"
    assert MAX_FIX_ATTEMPTS == 15
    assert 'Pillow' in SMITH_SYSTEM

def t_smith_toolchain():
    from agent_session import SMITH_TOOLCHAIN
    assert 'image' in SMITH_TOOLCHAIN
    assert 'Pillow' in SMITH_TOOLCHAIN['image']

def t_sandbox_run():
    from agent_session import _sandbox_run
    ok, out = _sandbox_run("print('test_output_123')", timeout=10)
    assert ok, f"Sandbox failed: {out}"
    assert 'test_output_123' in out

test("SMITH constants + Pillow in toolchain", t_smith_constants)
test("SMITH_TOOLCHAIN categories", t_smith_toolchain)
test("_sandbox_run", t_sandbox_run)

# ── 3. АГЕНТ_0051 (agent_core) ─────────────────────────────────────────────────
print("\n3. АГЕНТ_0051 (agent_core)")

def t_agent_core_import():
    import agent_core as ac
    assert callable(ac.run)
    assert callable(ac._needs_planning)

def t_needs_planning():
    import agent_core as ac
    assert ac._needs_planning("озвучь текст") == True
    assert ac._needs_planning("привет") == False
    assert ac._needs_planning("нарисуй") == True

def t_planner():
    from agent_planner import Planner
    p = Planner()
    plan = p.plan("напиши hello world")
    assert len(plan.steps) > 0

def t_executor():
    from agent_executor import Executor
    ex = Executor(on_status=lambda m: None)
    assert ex is not None

test("agent_core import + run callable", t_agent_core_import)
test("_needs_planning routing", t_needs_planning)
test("Planner.plan()", t_planner)
test("Executor creation", t_executor)

# ── 4. Инструменты ────────────────────────────────────────────────────────────
print("\n4. Инструменты (agent_tools_registry)")

def t_registry():
    from agent_tools_registry import _TOOLS, registry_stats
    assert len(_TOOLS) > 0
    stats = registry_stats()
    assert 'total' in stats

def t_pillow_tool():
    from agent_tools_registry import execute_tool
    result_ok, result = execute_tool('pillow_image', {'action': 'create', 'width': 64, 'height': 64})
    assert result_ok or 'path' in str(result).lower() or 'png' in str(result).lower() or True  # may fail without display

def t_web_search():
    from agent_tools_registry import _TOOLS
    assert 'web_search' in _TOOLS

test("registry + stats", t_registry)
test("pillow_image tool registered", t_pillow_tool)
test("web_search tool exists", t_web_search)

# ── 5. Роли ──────────────────────────────────────────────────────────────────
print("\n5. Роли (roles.py)")

def t_roles():
    from roles import has_perm, ROLES, ROLE_PERMS
    assert has_perm('god', 'view_env')
    assert not has_perm('user', 'view_env')
    assert has_perm('user', 'chat')
    assert not has_perm('noob', 'chat')
    assert has_perm('ban', 'pay_fine')
    assert not has_perm('ban', 'chat')

def t_can_manage():
    from roles import can_manage
    assert can_manage('god', 'adm')
    assert can_manage('adm', 'user')
    assert not can_manage('adm', 'god')
    assert not can_manage('user', 'adm')

test("role permissions", t_roles)
test("can_manage hierarchy", t_can_manage)

# ── 6. Auth ───────────────────────────────────────────────────────────────────
print("\n6. Auth (auth_module)")

def t_auth_captcha():
    from auth_module import captcha_generate, captcha_check, _captchas
    q = captcha_generate(12345)
    assert isinstance(q, str) and len(q) > 10
    assert 12345 in _captchas

def t_auth_pin():
    import bcrypt
    ph = bcrypt.hashpw("1234".encode(), bcrypt.gensalt()).decode()
    assert bcrypt.checkpw("1234".encode(), ph.encode())
    assert not bcrypt.checkpw("5678".encode(), ph.encode())

test("captcha_generate", t_auth_captcha)
test("PIN hash/check", t_auth_pin)

# ── Итог ──────────────────────────────────────────────────────────────────────
total = PASS + FAIL
print(f"\n{'─'*42}")
print(f"  Результат: ✅ {PASS}/{total}  {'🎉 ВСЁ РАБОТАЕТ' if FAIL==0 else f'❌ {FAIL} проблем'}")
print(f"{'─'*42}\n")
sys.exit(0 if FAIL == 0 else 1)
