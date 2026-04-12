"""
core/tool_registry.py — Unified Tool Registry v3.0
Self-tool generation + GitHub install + pentest tools + multitool.

All agents share this registry. Tools persist in SQLite.
"""
from __future__ import annotations
import os, sys, re, ast, json, time, subprocess, sqlite3, shutil, threading
from pathlib import Path
from typing import Optional, Callable, Tuple, List, Dict
import config

TOOLS_DIR     = Path(config.BASE_DIR) / "tools"
REPOS_DIR     = Path(config.BASE_DIR) / "repos"
SANDBOX_DIR   = Path(config.BASE_DIR) / "sandbox"
TOOLS_DB      = Path(config.DATA_DIR) / "tools.db"

for _d in (TOOLS_DIR, REPOS_DIR, SANDBOX_DIR):
    _d.mkdir(parents=True, exist_ok=True)

SANDBOX_TIMEOUT = 60
MAX_TOOL_GEN    = 7
MAX_AUTOFIX     = 15

# ═══════════════════════════════════════════════════════════════════════════════
#  Built-in tool sets
# ═══════════════════════════════════════════════════════════════════════════════

BUILTIN_TOOLS = {
    "python_eval", "shell_cmd", "web_scraper", "file_read", "file_write",
    "image_gen", "tts_speak", "send_mail", "smith_template",
    "analyze_code", "run_script", "csv_reader", "csv_writer",
    "pdf_reader", "zip_extractor", "json_transformer", "file_search",
    "http_get", "http_post", "rss_parser", "html_scraper", "api_caller",
    "git_info", "data_aggregator", "text_extractor", "diff_tool",
    "dedup_tool", "requirements_installer", "telegram_notify",
    "webhook_sender", "github_clone", "pip_install",
    "osint_sherlock", "osint_username_search", "osint_site_search",
    "self_create_tool", "self_list_tools", "self_delete_tool",
}

PENTEST_TOOLS = {
    "nmap_scan", "nuclei_scan", "whatweb_scan", "testssl_scan",
    "sqlmap_scan", "nikto_scan", "gobuster_scan", "metasploit_run",
}

ALL_BUILTINS = BUILTIN_TOOLS | PENTEST_TOOLS

# ═══════════════════════════════════════════════════════════════════════════════
#  Registry (SQLite + cache)
# ═══════════════════════════════════════════════════════════════════════════════

_cache: Dict[str, dict] = {}
_lock = threading.Lock()


def _init_db():
    with sqlite3.connect(str(TOOLS_DB)) as c:
        c.execute("""CREATE TABLE IF NOT EXISTS tools (
            name TEXT PRIMARY KEY, description TEXT, code TEXT,
            created REAL, used_count INTEGER DEFAULT 0,
            last_used REAL, source TEXT DEFAULT 'generated'
        )""")
        c.commit()

try:
    _init_db()
except Exception:
    pass


def exists(name: str) -> bool:
    if name in ALL_BUILTINS:
        return True
    with _lock:
        if name in _cache:
            return True
    try:
        with sqlite3.connect(str(TOOLS_DB)) as c:
            return c.execute("SELECT 1 FROM tools WHERE name=?", (name,)).fetchone() is not None
    except Exception:
        return False


def get(name: str) -> Optional[dict]:
    with _lock:
        if name in _cache:
            return _cache[name]
    try:
        with sqlite3.connect(str(TOOLS_DB)) as c:
            row = c.execute("SELECT name,description,code,created,source FROM tools WHERE name=?",
                            (name,)).fetchone()
            if row:
                t = {"name": row[0], "description": row[1], "code": row[2],
                     "created": row[3], "source": row[4]}
                with _lock:
                    _cache[name] = t
                return t
    except Exception:
        pass
    return None


def register(name: str, description: str, code: str,
             source: str = "generated", **_kw) -> bool:
    t = {"name": name, "description": description, "code": code,
         "created": time.time(), "source": source}
    with _lock:
        _cache[name] = t
    try:
        (TOOLS_DIR / f"{name}.py").write_text(code, encoding='utf-8')
        with sqlite3.connect(str(TOOLS_DB)) as c:
            c.execute("""INSERT OR REPLACE INTO tools
                (name,description,code,created,used_count,last_used,source)
                VALUES (?,?,?,?,0,?,?)""",
                (name, description, code, t["created"], t["created"], source))
            c.commit()
        return True
    except Exception:
        return False


def delete(name: str) -> bool:
    with _lock:
        _cache.pop(name, None)
    try:
        with sqlite3.connect(str(TOOLS_DB)) as c:
            c.execute("DELETE FROM tools WHERE name=?", (name,))
            c.commit()
        tf = TOOLS_DIR / f"{name}.py"
        if tf.exists():
            tf.unlink()
        return True
    except Exception:
        return False


def list_all() -> List[dict]:
    tools = [{"name": n, "builtin": True, "type": "builtin"} for n in sorted(BUILTIN_TOOLS)]
    tools += [{"name": n, "builtin": True, "type": "pentest"} for n in sorted(PENTEST_TOOLS)]
    try:
        with sqlite3.connect(str(TOOLS_DB)) as c:
            for row in c.execute("SELECT name,description,created,used_count,source FROM tools ORDER BY used_count DESC"):
                tools.append({"name": row[0], "description": row[1], "created": row[2],
                              "used_count": row[3], "source": row[4], "builtin": False, "type": "dynamic"})
    except Exception:
        pass
    return tools


def bump_usage(name: str):
    try:
        with sqlite3.connect(str(TOOLS_DB)) as c:
            c.execute("UPDATE tools SET used_count=used_count+1, last_used=? WHERE name=?",
                      (time.time(), name))
            c.commit()
    except Exception:
        pass


def stats() -> dict:
    tools = list_all()
    return {
        "total": len(tools),
        "builtin": sum(1 for t in tools if t.get("type") == "builtin"),
        "pentest": sum(1 for t in tools if t.get("type") == "pentest"),
        "dynamic": sum(1 for t in tools if t.get("type") == "dynamic"),
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  Sandbox execution
# ═══════════════════════════════════════════════════════════════════════════════

def _dec(b: bytes) -> str:
    if not b:
        return ""
    for enc in ("utf-8", "cp1251", "latin-1"):
        try:
            return b.decode(enc)
        except Exception:
            pass
    return b.decode("utf-8", errors="replace")


def sandbox_run(code: str, inputs: dict, timeout: int = SANDBOX_TIMEOUT) -> Tuple[bool, str, list]:
    """Run tool code in subprocess sandbox. Returns (ok, output, files)."""
    run_dir = SANDBOX_DIR / f"run_{int(time.time()*1000)}_{os.getpid()}"
    run_dir.mkdir(parents=True, exist_ok=True)
    inputs_with_dir = {**inputs, "output_dir": str(run_dir)}

    wrapper = f"""
import sys, json, traceback
sys.path.insert(0, {repr(str(TOOLS_DIR))})
sys.path.insert(0, {repr(config.BASE_DIR)})
{code}
inputs = {repr(inputs_with_dir)}
try:
    result = run_tool(inputs)
    print("__RESULT__:" + json.dumps(result, ensure_ascii=False, default=str))
except Exception:
    print("__RESULT__:" + json.dumps({{"ok":False,"output":"","files":[],"error":traceback.format_exc()}}))
"""
    wf = run_dir / "_runner.py"
    wf.write_text(wrapper, encoding='utf-8')
    try:
        r = subprocess.run([sys.executable, str(wf)], capture_output=True,
                           timeout=timeout, cwd=str(run_dir),
                           env={**os.environ, 'PYTHONIOENCODING': 'utf-8'})
        stdout = _dec(r.stdout)
        stderr = _dec(r.stderr)
        full = (stdout + stderr).strip()
        for line in stdout.splitlines():
            if line.startswith('__RESULT__:'):
                try:
                    res = json.loads(line[11:])
                    files = [str(run_dir / f) for f in res.get("files", []) if (run_dir / f).exists()]
                    created = [str(p) for p in run_dir.iterdir() if p.is_file() and p.name != '_runner.py']
                    return res.get("ok", True), res.get("output", full), list(set(files + created))
                except Exception:
                    pass
        created = [str(p) for p in run_dir.iterdir() if p.is_file() and p.name != '_runner.py']
        return r.returncode == 0, full[:3000], created
    except subprocess.TimeoutExpired:
        return False, f"Timeout {timeout}s", []
    except Exception as e:
        return False, str(e), []


# ═══════════════════════════════════════════════════════════════════════════════
#  Built-in tool executors
# ═══════════════════════════════════════════════════════════════════════════════

def run_builtin(name: str, inputs: dict, on_status: Callable = None) -> Tuple[bool, str, list]:
    """Execute a built-in tool."""
    st = on_status or (lambda m: None)

    if name == "python_eval":
        try:
            return True, str(eval(compile(inputs.get("code",""), '<eval>', 'eval'))), []
        except Exception as e:
            return False, str(e), []

    elif name == "shell_cmd":
        try:
            r = subprocess.run(inputs.get("cmd","echo ok"), shell=True,
                               capture_output=True, timeout=30, cwd=config.BASE_DIR)
            return r.returncode == 0, (_dec(r.stdout) + _dec(r.stderr)).strip()[:3000], []
        except Exception as e:
            return False, str(e), []

    elif name == "file_read":
        p = inputs.get("path", "")
        try:
            if os.path.isdir(p):
                return True, f"Dir: {', '.join(os.listdir(p)[:30])}", []
            return True, Path(p).read_text(encoding='utf-8', errors='ignore')[:10000], []
        except Exception as e:
            return False, str(e), []

    elif name == "file_write":
        p = inputs.get("path", "")
        c = inputs.get("content", "")
        try:
            Path(p).parent.mkdir(parents=True, exist_ok=True)
            Path(p).write_text(c, encoding='utf-8')
            return True, f"Written {len(c)} chars", [p]
        except Exception as e:
            return False, str(e), []

    elif name == "image_gen":
        st("Генерирую картинку...")
        try:
            from image_gen import generate_image
            path, prov = generate_image(inputs.get("prompt", ""))
            return True, f"Image via {prov}", [path]
        except Exception as e:
            return False, str(e), []

    elif name == "tts_speak":
        st("Озвучиваю...")
        try:
            from tts_engine import synthesize
            p = synthesize(inputs.get("text","")[:900], f"tts_{int(time.time())}.mp3")
            return True, "TTS ok", [p]
        except Exception as e:
            return False, str(e), []

    elif name == "smith_template":
        st("SMITH pipeline...")
        try:
            from agent_session import create_session, execute_pipeline, close_session
            cid = f"tool_{int(time.time())}"
            sess = create_session(cid)
            sess.task = inputs.get("task", "")
            res = execute_pipeline(sess, on_status=on_status)
            close_session(cid)
            files = []
            if res.get("zip_path") and os.path.exists(res["zip_path"]):
                files.append(res["zip_path"])
            return res.get("ok", False), res.get("output", ""), files
        except Exception as e:
            return False, str(e), []

    elif name == "web_scraper":
        try:
            import urllib.request
            url = inputs.get("url", "")
            req = urllib.request.Request(url, headers={'User-Agent': 'BlackBugsAI/3.0'})
            with urllib.request.urlopen(req, timeout=15) as r:
                html = r.read().decode('utf-8', errors='ignore')
            text = re.sub(r'<[^>]+>', ' ', html)
            return True, re.sub(r'\s+', ' ', text).strip()[:5000], []
        except Exception as e:
            return False, str(e), []

    # Fallback: check neo_tool_library
    return False, f"Builtin '{name}' — execute via tool library", []


def run_pentest(name: str, inputs: dict, on_status: Callable = None) -> Tuple[bool, str, list]:
    """Execute pentest tools via shell."""
    st = on_status or (lambda m: None)
    target = inputs.get("target", inputs.get("host", inputs.get("url", ""))).strip()
    if not target:
        return False, "Нужен target", []
    args = inputs.get("args", "")
    ts = int(time.time())
    out_dir = inputs.get("output_dir", str(SANDBOX_DIR))
    out_file = f"{out_dir}/{name}_{ts}.txt"

    cmds = {
        "nmap_scan":     f"nmap {inputs.get('flags','-sV -sC')} -oN {out_file} {target} {args}",
        "nuclei_scan":   f"nuclei -u {target} -severity {inputs.get('severity','medium,high,critical')} -o {out_file} {args}",
        "whatweb_scan":  f"whatweb {target} {args} | tee {out_file}",
        "testssl_scan":  f"testssl --quiet --color 0 {target} {args} | tee {out_file}",
        "sqlmap_scan":   f"sqlmap -u '{target}' --level={inputs.get('level','1')} --risk={inputs.get('risk','1')} --batch --random-agent {args} | tee {out_file}",
        "nikto_scan":    f"nikto -h {target} {args} -o {out_file} -Format txt",
        "gobuster_scan": f"gobuster dir -u {target} -w {inputs.get('wordlist','/usr/share/wordlists/dirb/common.txt')} {args} -o {out_file}",
        "metasploit_run": f"msfconsole -q -x 'db_nmap -sV {target}; exit' | tee {out_file}",
    }
    cmd = cmds.get(name)
    if not cmd:
        return False, f"Unknown pentest tool: {name}", []
    st(f"🔍 {name}: {target}...")
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True,
                           timeout=int(inputs.get("timeout", 300)), cwd=out_dir)
        out = _dec(r.stdout) + _dec(r.stderr)
        files = [out_file] if os.path.exists(out_file) else []
        return r.returncode == 0 or bool(out.strip()), out.strip()[:4000], files
    except subprocess.TimeoutExpired:
        files = [out_file] if os.path.exists(out_file) else []
        return False, f"Timeout", files
    except Exception as e:
        return False, str(e), []


def execute(name: str, inputs: dict, on_status: Callable = None) -> Tuple[bool, str, list]:
    """Universal tool executor — builtin, pentest, or dynamic."""
    bump_usage(name)
    if name in BUILTIN_TOOLS:
        ok, out, files = run_builtin(name, inputs, on_status)
        if not ok and "execute via tool library" in out:
            # Fallback to neo_tool_library registered code
            tool = get(name)
            if tool and tool.get("code"):
                return sandbox_run(tool["code"], inputs)
        return ok, out, files
    if name in PENTEST_TOOLS:
        return run_pentest(name, inputs, on_status)
    # Dynamic tool
    tool = get(name)
    if tool and tool.get("code"):
        return sandbox_run(tool["code"], inputs)
    return False, f"Tool not found: {name}", []


# ═══════════════════════════════════════════════════════════════════════════════
#  Self-tool generation (LLM)
# ═══════════════════════════════════════════════════════════════════════════════

TOOL_GEN_SYSTEM = """Ты — генератор инструментов. Пишешь ТОЛЬКО рабочий Python-код.
Функция: def run_tool(inputs: dict) -> dict
Возврат: {"ok": bool, "output": str, "files": list, "error": str}
output_dir = inputs.get("output_dir", "/tmp")
Декодируй bytes: for enc in ("utf-8","cp1251","latin-1"): try: return b.decode(enc)
Все исключения в try/except. Прогресс через print().
pip: subprocess.run([sys.executable,"-m","pip","install",PKG,"-q","--break-system-packages"])"""


def _llm(prompt: str, system: str = "", max_tokens: int = 4000) -> str:
    try:
        from llm_router import call_llm_for
        return call_llm_for("fix", prompt, system, max_tokens)
    except Exception:
        from llm_client import call_llm
        return call_llm(prompt, system, max_tokens)


def _extract_code(raw: str) -> str:
    if not raw:
        return 'pass'
    for pat in [r'```python\s*\n(.*?)```', r'```py\s*\n(.*?)```', r'```\s*\n(.*?)```']:
        m = re.search(pat, raw, re.DOTALL)
        if m:
            return m.group(1).strip()
    lines, started = [], False
    for line in raw.splitlines():
        s = line.strip()
        if not started and any(s.startswith(k) for k in ('import','from','def','class','#!','async')):
            started = True
        if started:
            lines.append(line)
    return '\n'.join(lines) if lines else raw.strip()


def _sanitize(code: str) -> str:
    for old, new in [('\u2014','-'),('\u2013','-'),('\u2018',"'"),('\u2019',"'"),('\u201c','"'),('\u201d','"')]:
        code = code.replace(old, new)
    return code


def generate_tool(name: str, description: str, example_inputs: dict,
                  on_status: Callable = None) -> Tuple[bool, str]:
    """Generate a new tool using LLM + autofix loop."""
    st = on_status or (lambda m: None)
    st(f"🔧 Генерирую: {name}...")

    prompt = (f"Создай инструмент `{name}`.\nОписание: {description}\n"
              f"inputs: {json.dumps(example_inputs, ensure_ascii=False)}\n"
              f"Напиши ТОЛЬКО run_tool(inputs: dict) -> dict.")

    code = None
    last_error = ""
    for attempt in range(1, MAX_TOOL_GEN + 1):
        st(f"  Попытка {attempt}/{MAX_TOOL_GEN}...")
        if attempt == 1 or not code:
            raw = _llm(prompt, TOOL_GEN_SYSTEM)
        else:
            raw = _llm(f"Код:\n```python\n{code}\n```\nОшибка: {last_error}\nИсправь. ТОЛЬКО run_tool().",
                       TOOL_GEN_SYSTEM)
        code = _sanitize(_extract_code(raw))
        if 'def run_tool' not in code:
            last_error = "Missing run_tool"
            continue
        try:
            ast.parse(code)
        except SyntaxError as se:
            last_error = f"SyntaxError line {se.lineno}: {se.msg}"
            continue
        ok, output, _ = sandbox_run(code, example_inputs, timeout=20 + attempt * 10)
        if ok:
            register(name, description, code)
            st(f"  ✅ {name} создан!")
            return True, ""
        last_error = output[:300]
    return False, f"Не создан за {MAX_TOOL_GEN} попыток: {last_error}"


def install_github(url: str, tool_name: str = "", description: str = "",
                   on_status: Callable = None) -> Tuple[bool, str, str]:
    """Clone GitHub repo, install deps, generate wrapper, register."""
    st = on_status or (lambda m: None)
    if not tool_name:
        tool_name = url.rstrip('/').split('/')[-1].replace('.git','').replace('-','_').lower()
    repo_dir = str(REPOS_DIR / f"repo_{tool_name}")
    st(f"📥 Клонирую {url}...")
    if os.path.exists(repo_dir):
        shutil.rmtree(repo_dir)
    r = subprocess.run(["git","clone","--depth=1",url,repo_dir], capture_output=True, timeout=120)
    if r.returncode != 0:
        return False, tool_name, f"git clone failed: {_dec(r.stderr)}"
    req = Path(repo_dir) / "requirements.txt"
    if req.exists():
        subprocess.run([sys.executable,"-m","pip","install","-r",str(req),"-q","--break-system-packages"],
                       capture_output=True, timeout=300)
    # Find entry
    entry = "python3 ."
    for cmd, fp in [("python3 main.py","main.py"),("python3 app.py","app.py"),("python3 cli.py","cli.py")]:
        if (Path(repo_dir)/fp).exists():
            entry = cmd; break
    code = (
        "def run_tool(inputs):\n"
        "    import subprocess, sys\n"
        f"    repo = {repr(repo_dir)}\n"
        f"    base = {repr(entry)}\n"
        "    args = inputs.get('args', inputs.get('query', ''))\n"
        "    cmd = base + (' ' + str(args) if args else '')\n"
        "    def _d(b):\n"
        "        if not b: return ''\n"
        "        for e in ('utf-8','cp1251','latin-1'):\n"
        "            try: return b.decode(e)\n"
        "            except: pass\n"
        "        return b.decode('utf-8',errors='replace')\n"
        "    r = subprocess.run(cmd, shell=True, capture_output=True, timeout=120, cwd=repo)\n"
        "    out = _d(r.stdout) + _d(r.stderr)\n"
        "    return {'ok':r.returncode==0,'output':out[:4000],'files':[],'error':'' if r.returncode==0 else out[:500]}\n"
    )
    register(tool_name, description or f"GitHub: {url}", code, source="github")
    st(f"✅ {tool_name} установлен!")
    return True, tool_name, ""


def warmup(on_status: Callable = None) -> dict:
    """Register all tools from neo_tool_library."""
    _init_db()
    try:
        from neo_tool_library import register_all
        return register_all(on_status=on_status)
    except ImportError as e:
        return {"registered": 0, "skipped": 0, "failed": 0, "error": str(e)}
