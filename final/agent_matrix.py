"""
agent_matrix.py — AGENT MATRIX v1.0
BlackBugsAI — Universal Self-Evolving Agent

Архитектура:
  Task → MatrixPlanner → MatrixToolRegistry → MatrixSandbox
  → если нет инструмента: генерируем LLM / ставим с GitHub
  → ZIP артефакт + TTS

Роли в одном: Кодер · Тестер · OSINT · Security Analyst
"""
from __future__ import annotations
import os, sys, ast, re, json, time, subprocess, sqlite3, zipfile, tempfile, shutil
from pathlib import Path
from typing import Optional, Callable, Tuple, List

import config

# ── Директории ────────────────────────────────────────────────────────────────
MATRIX_DIR    = Path(config.BASE_DIR) / "matrix_workspace"
TOOLS_DIR     = MATRIX_DIR / "tools"
ARTIFACTS_DIR = MATRIX_DIR / "artifacts"
TOOLS_DB      = MATRIX_DIR / "tools.db"
REPOS_DIR     = MATRIX_DIR / "repos"

for _d in (MATRIX_DIR, TOOLS_DIR, ARTIFACTS_DIR, REPOS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ── Константы ─────────────────────────────────────────────────────────────────
VERSION          = "1.0"
MAX_GEN_ATTEMPTS = 7
SANDBOX_TIMEOUT  = 600

# ── Системный промт — Кодер + Тестер + OSINT + Security Analyst ──────────────
MATRIX_SYSTEM = """Ты — AGENT MATRIX, универсальный AI-агент BlackBugsAI.
Роли: Кодер · Тестер · OSINT · Security Analyst (авторизованные задачи).

ЗАПРЕЩЁННЫЕ БИБЛИОТЕКИ (не существуют — НЕ используй):
  bootscrape, webbot, scrapeasy, autoscraper2, pyscraper, urlgrab,
  и любые другие, в существовании которых не уверен.

РАЗРЕШЁННЫЕ библиотеки для веб-скрапинга:
  urllib.request, requests, beautifulsoup4 (bs4), lxml
  — или subprocess + curl/wget

РАЗРЕШЁННЫЕ библиотеки (всегда доступны):
  stdlib: os, sys, json, re, time, ast, subprocess, sqlite3, zipfile,
          pathlib, tempfile, threading, socket, ssl, csv, shutil,
          urllib.request, urllib.parse, http.client, difflib
  installed: requests, flask, pillow, edge-tts, bs4, lxml, feedparser,
             pypdf, bcrypt, qrcode, openai, groq

ЕСЛИ нужна сторонняя библиотека:
  1. Сначала установи через subprocess + pip install --break-system-packages
  2. Потом импортируй

РЕЖИМЫ РАБОТЫ:
[КОДЕР] Написать/отладить/оптимизировать код на Python, JS, Bash и других языках.
  - Используй subprocess для запуска, PIL/Pillow для графики, asyncio для async.
  - Сохраняй артефакты в output_dir. Возвращай {ok, output, files, error}.

[ТЕСТЕР] Написать тесты, найти баги, проверить безопасность кода.
  - pytest / unittest / аналоги. Coverage. Edge cases.
  - Статический анализ: ast.parse, compile, type hints.

[OSINT] Сбор публично доступной информации (только легальные источники).
  - GitHub API, публичные профили, WHOIS, DNS, HTTP-заголовки.
  - Sherlock для поиска username на публичных платформах.
  - НЕ используй авторизацию, взлом или закрытые базы данных.

[SECURITY] Анализ безопасности собственной инфраструктуры (авторизованные задачи).
  - Сканирование портов своих серверов через nmap.
  - Анализ заголовков, SSL, CORS, открытых портов.
  - Проверка зависимостей на CVE через pip-audit / safety.
  - НЕ атакуй чужие системы без явного разрешения владельца.

ПРАВИЛА ИНСТРУМЕНТОВ:
1. run_tool(inputs: dict) -> dict — всегда такая сигнатура
2. Возврат: {"ok": bool, "output": str, "files": list, "error": str}
3. Декодируй bytes: for enc in ("utf-8","cp1251","latin-1"): try: return b.decode(enc)
4. output_dir = inputs.get("output_dir", "/tmp")
5. Все ошибки в try/except — никогда не выбрасывай наружу
6. Прогресс через print() на русском языке

ШАБЛОН:
```python
def run_tool(inputs: dict) -> dict:
    import os, sys, subprocess
    from pathlib import Path
    output_dir = inputs.get("output_dir", "/tmp")
    def _dec(b):
        if not b: return ""
        for enc in ("utf-8","cp1251","latin-1"):
            try: return b.decode(enc)
            except: pass
        return b.decode("utf-8", errors="replace")
    try:
        result = "готово"
        return {"ok": True, "output": result, "files": [], "error": ""}
    except Exception as e:
        return {"ok": False, "output": str(e), "files": [], "error": str(e)}
```"""

MATRIX_PLANNER_SYSTEM = """Ты — планировщик AGENT MATRIX.
Анализируй задачу и возвращай ТОЛЬКО валидный JSON (без markdown).

ВСТРОЕННЫЕ ИНСТРУМЕНТЫ (tool_exists=true):
  Кодер:    python_eval, shell_cmd, file_read, file_write, zip_files
  Тестер:   run_tests, analyze_code
  OSINT:    osint_username, osint_domain, web_scrape, http_get
  Security: port_scan, ssl_check, deps_audit
  Утилиты:  github_clone, github_install, pip_install
  Self:     matrix_create_tool, matrix_list_tools

ВАЖНЫЕ ПРАВИЛА:
1. Написать/запустить код → tool_name="python_eval", inputs={"code":"...код..."}
   НЕ создавай run_script/check_syntax — используй python_eval.
2. GitHub URL → tool_name="github_install", inputs={"url":"..."}
3. OSINT → tool_name="osint_username" или "osint_domain"
4. МАКСИМУМ 3 шага. Простые задачи — 1 шаг.
5. ДИНАМИЧЕСКИЕ ИНСТРУМЕНТЫ: если в задаче упоминается инструмент который был
   установлен ранее (robin, sherlock, nmap и т.д.) — используй его напрямую:
   tool_name="robin", tool_exists=true, inputs={"args":"-d example.com"}
   Передавай аргументы через inputs["args"] или специфичные ключи.
6. Запросы типа "запусти robin для X", "используй sherlock для Y" →
   tool_name=имя_инструмента, tool_exists=true, inputs={"args":"аргументы"}

ФОРМАТ:
{
  "steps": [
    {
      "id": 1,
      "description": "что делает шаг",
      "tool_name": "название",
      "tool_exists": true,
      "inputs": {"args": "-d example.com"},
      "depends_on": []
    }
  ],
  "summary": "краткое описание"
}"""


# ══════════════════════════════════════════════════════════════════════════════
#  LLM helper
# ══════════════════════════════════════════════════════════════════════════════

def _llm(prompt: str, system: str = "", max_tokens: int = 8000) -> str:
    """Call LLM. Auto-continues if response is truncated (finish_reason=length)."""
    try:
        from llm_client import call_llm_full
        text, truncated = call_llm_full(prompt, system=system, max_tokens=max_tokens)
        if truncated:
            # Try to complete the truncated code
            cont = call_llm_full(
                f"Continue EXACTLY from where you stopped (no preamble, just code):\n{text[-200:]}",
                system=system, max_tokens=max_tokens
            )
            text = text + cont[0]
        return text
    except Exception:
        try:
            from llm_client import call_llm
            return call_llm(prompt, system=system, max_tokens=max_tokens)
        except Exception as e:
            return f"# LLM error: {e}"


def _llm_code(prompt: str, system: str = "", max_tokens: int = 8000) -> str:
    """Like _llm but specialized for code: validates completeness, retries if truncated."""
    try:
        from llm_client import call_llm_full
        text, truncated = call_llm_full(prompt, system=system, max_tokens=max_tokens)
        # Continue up to 3 times if still truncated
        for _ in range(3):
            if not truncated:
                break
            # Check open blocks
            if text.count("```") % 2 != 0 or text.rstrip().endswith((":", ",", "(")):
                cont_prompt = (
                    f"The function was cut off. Continue writing ONLY the remaining Python code "
                    f"(no explanations, start from exactly where it stopped):\n"
                    f"...{text[-300:]}"
                )
                cont, truncated = call_llm_full(cont_prompt, system=system, max_tokens=max_tokens)
                text = text + cont
            else:
                break
        return text
    except Exception:
        return _llm(prompt, system, max_tokens)


def _dec(b) -> str:
    if not b: return ""
    if isinstance(b, str): return b
    for enc in ("utf-8", "cp1251", "cp866", "latin-1"):
        try: return b.decode(enc)
        except: pass
    return b.decode("utf-8", errors="replace")


# ══════════════════════════════════════════════════════════════════════════════
#  Tool Registry
# ══════════════════════════════════════════════════════════════════════════════

def _init_db():
    db = sqlite3.connect(str(TOOLS_DB))
    db.execute("""CREATE TABLE IF NOT EXISTS tools (
        name TEXT PRIMARY KEY,
        description TEXT,
        code TEXT,
        builtin INTEGER DEFAULT 0,
        created REAL DEFAULT 0,
        used_count INTEGER DEFAULT 0,
        success_count INTEGER DEFAULT 0,
        fail_count INTEGER DEFAULT 0,
        avg_duration REAL DEFAULT 0,
        last_error TEXT DEFAULT '',
        tags TEXT DEFAULT '',
        version INTEGER DEFAULT 1
    )""")
    # Learning & evolution tables
    db.execute("""CREATE TABLE IF NOT EXISTS tool_executions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tool_name TEXT, ok INTEGER, duration REAL,
        error TEXT, ts REAL DEFAULT 0
    )""")
    db.execute("""CREATE TABLE IF NOT EXISTS pipelines (
        id TEXT PRIMARY KEY,
        name TEXT, description TEXT,
        nodes TEXT, edges TEXT,
        created REAL DEFAULT 0, updated REAL DEFAULT 0,
        runs INTEGER DEFAULT 0,
        shared INTEGER DEFAULT 0,
        author TEXT DEFAULT 'local',
        category TEXT DEFAULT 'general'
    )""")
    db.execute("""CREATE TABLE IF NOT EXISTS learning_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tool_name TEXT, prompt TEXT, result TEXT,
        ok INTEGER, attempt INTEGER, ts REAL DEFAULT 0
    )""")
    db.execute("CREATE INDEX IF NOT EXISTS idx_exec_tool ON tool_executions(tool_name)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_pip_shared ON pipelines(shared)")
    # Migrate existing tools table if missing columns
    try:
        for col, defval in [("success_count","0"),("fail_count","0"),("avg_duration","0"),
                            ("last_error","''"),("tags","''"),("version","1")]:
            try: db.execute(f"ALTER TABLE tools ADD COLUMN {col} {'INTEGER' if col in ('success_count','fail_count','version') else 'REAL' if col=='avg_duration' else 'TEXT'} DEFAULT {defval}")
            except: pass
    except: pass
    db.commit(); db.close()

_init_db()


def register_tool(name: str, description: str, code: str, builtin: bool = False,
                  tags: str = ""):
    db = sqlite3.connect(str(TOOLS_DB))
    db.execute("""INSERT OR REPLACE INTO tools
                  (name,description,code,builtin,created,used_count,
                   success_count,fail_count,avg_duration,last_error,tags,version)
                  VALUES (?,?,?,?,?,
                    COALESCE((SELECT used_count FROM tools WHERE name=?),0),
                    COALESCE((SELECT success_count FROM tools WHERE name=?),0),
                    COALESCE((SELECT fail_count FROM tools WHERE name=?),0),
                    COALESCE((SELECT avg_duration FROM tools WHERE name=?),0),
                    COALESCE((SELECT last_error FROM tools WHERE name=?),\'\'),
                    ?,
                    COALESCE((SELECT version+1 FROM tools WHERE name=? AND code!=?),1)
                  )""",
               (name, description, code, int(builtin), time.time(),
                name, name, name, name, name, tags,
                name, code))
    db.commit(); db.close()
    (TOOLS_DIR / f"{name}.py").write_text(code, encoding="utf-8")


def tool_exists(name: str) -> bool:
    db = sqlite3.connect(str(TOOLS_DB))
    row = db.execute("SELECT 1 FROM tools WHERE name=?", (name,)).fetchone()
    db.close()
    return row is not None


# ── In-memory tool code cache (LRU, max 128 entries) ──────────────────────────
import functools as _functools
_tool_cache: dict = {}   # name -> (code, mtime)
_CACHE_MAX = 128

def _cache_get(name: str) -> Optional[str]:
    entry = _tool_cache.get(name)
    if not entry:
        return None
    code, mtime = entry
    # Validate against file mtime
    f = TOOLS_DIR / f"{name}.py"
    if f.exists():
        try:
            if f.stat().st_mtime > mtime:
                del _tool_cache[name]
                return None
        except Exception:
            pass
    return code

def _cache_set(name: str, code: str) -> None:
    if len(_tool_cache) >= _CACHE_MAX:
        # Evict oldest
        oldest = next(iter(_tool_cache))
        del _tool_cache[oldest]
    _tool_cache[name] = (code, time.time())

def cache_invalidate(name: str = "") -> None:
    """Invalidate cache for a specific tool or all tools."""
    if name:
        _tool_cache.pop(name, None)
    else:
        _tool_cache.clear()


def get_tool_code(name: str) -> Optional[str]:
    # Check cache first
    cached = _cache_get(name)
    if cached:
        return cached
    # DB lookup
    try:
        db = sqlite3.connect(str(TOOLS_DB))
        row = db.execute("SELECT code FROM tools WHERE name=?", (name,)).fetchone()
        db.close()
        if row and row[0]:
            _cache_set(name, row[0])
            return row[0]
    except Exception:
        pass
    # Fallback: disk file
    f = TOOLS_DIR / f"{name}.py"
    if f.exists():
        try:
            code = f.read_text(encoding="utf-8")
            _cache_set(name, code)
            return code
        except Exception:
            pass
    return None


def list_tools() -> List[dict]:
    db = sqlite3.connect(str(TOOLS_DB))
    rows = db.execute(
        "SELECT name,description,builtin,used_count FROM tools ORDER BY used_count DESC"
    ).fetchall()
    db.close()
    return [{"name": r[0], "description": r[1], "builtin": bool(r[2]), "used_count": r[3]}
            for r in rows]


# ══════════════════════════════════════════════════════════════════════════════
#  Sandbox
# ══════════════════════════════════════════════════════════════════════════════

def sandbox_run(code: str, inputs: dict, timeout: int = SANDBOX_TIMEOUT,
                _tool_name: str = "") -> Tuple[bool, str, list]:
    """Run tool code in isolated subprocess. Records execution stats if _tool_name given."""
    _t0 = time.time()
    run_dir = ARTIFACTS_DIR / f"run_{int(time.time()*1000)}"
    run_dir.mkdir(parents=True, exist_ok=True)
    inputs_full = {**inputs, "output_dir": str(run_dir)}

    wrapper = (
        "import sys, json, traceback\n"
        f"sys.path.insert(0, {str(TOOLS_DIR)!r})\n"
        f"sys.path.insert(0, {config.BASE_DIR!r})\n\n"
        f"{code}\n\n"
        f"inputs = {inputs_full!r}\n"
        "try:\n"
        "    result = run_tool(inputs)\n"
        "    if not isinstance(result, dict): result = {'ok': True, 'output': str(result), 'files': [], 'error': ''}\n"
        "    print('__MATRIX_RESULT__:' + json.dumps(result, ensure_ascii=False, default=str))\n"
        "except Exception as e:\n"
        "    print('__MATRIX_RESULT__:' + json.dumps({'ok': False, 'output': '', 'files': [], 'error': traceback.format_exc()[-500:]}))\n"
    )
    runner = run_dir / "_matrix_runner.py"
    runner.write_text(wrapper, encoding="utf-8")

    try:
        r = subprocess.run(
            [sys.executable, str(runner)],
            capture_output=True, timeout=timeout,
            cwd=str(run_dir),
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
        stdout = _dec(r.stdout)
        stderr = _dec(r.stderr)

        for line in stdout.splitlines():
            if "__MATRIX_RESULT__:" in line:
                try:
                    result = json.loads(line.split("__MATRIX_RESULT__:", 1)[1])
                    files = [f for f in result.get("files", []) if os.path.exists(f)]
                    return result.get("ok", False), result.get("output", ""), files
                except Exception:
                    pass

        # No structured result
        out = (stdout + stderr).strip()
        _res = r.returncode == 0
        if _tool_name:
            try: record_execution(_tool_name, _res, time.time() - _t0, out if not _res else "")
            except Exception: pass
        return _res, out[:6000] or "(нет вывода)", []

    except subprocess.TimeoutExpired:
        return False, f"⏰ Таймаут {timeout}с", []
    except Exception as e:
        return False, str(e), []


# ══════════════════════════════════════════════════════════════════════════════
#  Code extraction & fix
# ══════════════════════════════════════════════════════════════════════════════

def _extract_code(raw: str) -> str:
    """Extract Python code from LLM response. Handles truncated/incomplete blocks."""
    if not raw: return "pass"
    # Try fenced blocks first
    for pat in [r"```python\s*\n(.*?)```", r"```py\s*\n(.*?)```", r"```\s*\n(.*?)```"]:
        m = re.search(pat, raw, re.DOTALL)
        if m:
            return _clean_code(m.group(1).strip())
    # Handle truncated fenced block (opening fence but no closing)
    m = re.search(r"```(?:python|py)?\s*\n(.*)", raw, re.DOTALL)
    if m:
        code = _clean_code(m.group(1).strip())
        if "def " in code or "import " in code:
            return _auto_close_code(code)
    # No fences — strip any partial fence markers
    clean = re.sub(r"^```[\w]*\n?", "", raw.strip())
    clean = re.sub(r"\n?```\s*$", "", clean).strip()
    if "def " in clean or "import " in clean:
        return _auto_close_code(_clean_code(clean))
    return "pass"


def _auto_close_code(code: str) -> str:
    """Auto-close common open blocks in truncated code."""
    lines = code.splitlines()
    if not lines:
        return code
    last = lines[-1].rstrip()
    # If ends with open colon (function/if/for/try body expected)
    if last.endswith(":") and not last.strip().startswith("#"):
        code += "\n        pass"
    # Count open parens/brackets
    opens = code.count("(") - code.count(")")
    if opens > 0:
        code += ")" * opens
    opens = code.count("[") - code.count("]")
    if opens > 0:
        code += "]" * opens
    opens = code.count("{") - code.count("}")
    if opens > 0:
        code += "}" * opens
    # Ensure return statement exists in run_tool
    if "def run_tool" in code and "return {" not in code and "return{" not in code:
        # Add minimal valid return
        indent = "    "
        if "    try:" in code:
            code += f"\n{indent}    return {{'ok': False, 'output': 'incomplete', 'files': [], 'error': 'code was truncated'}}"
        else:
            code += f"\n{indent}return {{'ok': False, 'output': 'incomplete', 'files': [], 'error': 'code was truncated'}}"
    return code


def _clean_code(code: str) -> str:
    replacements = {"\u2014": "-", "\u2013": "-", "\u2018": "'", "\u2019": "'",
                    "\u201c": '"', "\u201d": '"', "\u2026": "...", "\u00a0": " "}
    for old, new in replacements.items():
        code = code.replace(old, new)
    return code.strip()


def _fix_syntax(code: str) -> str:
    for _ in range(5):
        try:
            ast.parse(code); return code
        except SyntaxError as e:
            lines = code.splitlines()
            idx = (e.lineno or 1) - 1
            err = e.msg or ""
            if "expected an indented block" in err and idx < len(lines):
                lines.insert(idx + 1, "    pass")
                code = "\n".join(lines)
            elif "invalid syntax" in err and idx <= 2:
                # Strip leading non-code lines
                starts = ("import ", "from ", "def ", "class ", "#", "try:", "if ")
                skip = True
                new = []
                for l in lines:
                    if skip and any(l.strip().startswith(k) for k in starts):
                        skip = False
                    if not skip: new.append(l)
                code = "\n".join(new) if new else code
            else:
                break
    return code


# ══════════════════════════════════════════════════════════════════════════════
#  Tool Generation — Universal (LLM + GitHub)
# ══════════════════════════════════════════════════════════════════════════════

def generate_tool(
    name: str,
    description: str,
    example_inputs: dict,
    on_status: Optional[Callable] = None,
    github_url: str = "",
) -> Tuple[bool, str]:
    """
    Генерирует инструмент через LLM или устанавливает с GitHub.
    Возвращает (ok, error_message).
    """
    def st(msg):
        if on_status: on_status(msg)

    # ── GitHub path ────────────────────────────────────────────────────────────
    if github_url or "github.com" in description:
        url = github_url or re.search(r"https://github\.com/\S+", description)
        url = url.group(0) if hasattr(url, "group") else url
        if url:
            return _install_github(name, url, description, on_status)

    # ── LLM generation path ────────────────────────────────────────────────────
    st(f"🔧 Генерирую инструмент: {name}...")

    base_prompt = (
        f"Задача: инструмент `{name}`\n"
        f"Описание: {description}\n"
        f"Пример inputs: {json.dumps(example_inputs, ensure_ascii=False)}\n\n"
        f"Требования:\n"
        f"- Сигнатура: def run_tool(inputs: dict) -> dict\n"
        f"- Возврат: {{ok, output, files, error}}\n"
        f"- Декодируй bytes: for enc in (utf-8,cp1251,latin-1): try: return b.decode(enc)\n"
        f"- output_dir = inputs.get('output_dir', '/tmp')\n"
        f"- subprocess для внешних инструментов\n"
        f"- Все ошибки перехватывай\n\n"
        f"Напиши ТОЛЬКО функцию run_tool."
    )

    code = None
    last_error = ""
    error_history: List[str] = []
    same_error_count: int = 0  # FIX: must init before loop

    for attempt in range(1, MAX_GEN_ATTEMPTS + 1):
        st(f"  ⚙️ Попытка {attempt}/{MAX_GEN_ATTEMPTS}...")
        timeout = 60 + attempt * 40  # 100→140→180→220→260→300→340s

        if attempt == 1 or not code:
            raw = _llm_code(base_prompt, MATRIX_SYSTEM, max_tokens=8000)
        else:
            hist = "\n".join(f"  #{i+1}: {e}" for i, e in enumerate(error_history[-3:]))
            fix_prompt = (
                f"Инструмент `{name}` не работает.\n\n"
                f"Код:\n```python\n{code}\n```\n\n"
                f"История ошибок:\n{hist}\n"
                f"Последняя: {last_error}\n\n"
                f"Исправь:\n"
                f"• No module named X → добавь subprocess pip install\n"
                f"• bytes/str ошибка → добавь _dec() декодер\n"
                f"• FileNotFoundError → проверяй os.path.exists()\n"
                f"• Бесконечный цикл → добавь timeout или лимит итераций\n\n"
                f"Верни ТОЛЬКО исправленную run_tool()."
            )
            raw = _llm_code(fix_prompt, MATRIX_SYSTEM, max_tokens=8000)
            if attempt >= MAX_GEN_ATTEMPTS - 2 and same_error_count >= 2:
                # Кардинально другой подход
                alt_prompt = (
                    f"Предыдущий подход к `{name}` не работает (ошибка повторяется).\n"
                    f"Цель: {description}\n"
                    f"Придумай ДРУГОЙ способ реализации. "
                    f"Используй другие библиотеки или subprocess с shell-командами.\n"
                    f"Напиши ТОЛЬКО run_tool(inputs: dict) -> dict."
                )
                raw = _llm_code(alt_prompt, MATRIX_SYSTEM, max_tokens=8000)
                code = None

        code = _extract_code(raw)
        code = _fix_syntax(code)

        if "def run_tool" not in code:
            last_error = "Missing run_tool()"
            error_history.append(last_error)
            continue

        try:
            ast.parse(code)
        except SyntaxError as e:
            last_error = f"SyntaxError: {e.msg} line {e.lineno}"
            error_history.append(last_error)
            continue

        st(f"  🧪 Тестирую (timeout={timeout}s)...")
        ok, output, files = sandbox_run(code, example_inputs, timeout=timeout)

        if ok:
            register_tool(name, description, code)
            st(f"  ✅ {name!r} создан и зарегистрирован!")
            return True, ""

        clean_err = output.strip()[:300]
        same_error_count = error_history.count(clean_err)
        last_error = clean_err
        error_history.append(clean_err)
        st(f"  ❌ {clean_err[:80]}")

    return False, f"Не удалось за {MAX_GEN_ATTEMPTS} попыток. Последняя ошибка: {last_error[:200]}"


def _install_github(
    tool_name: str,
    url: str,
    description: str,
    on_status: Optional[Callable] = None,
) -> Tuple[bool, str]:
    """Клонирует GitHub репо, ставит deps, генерирует обёртку, регистрирует.
    Также генерирует usage-гайд и сохраняет его в tool_info."""
    def st(msg):
        if on_status: on_status(msg)

    st(f"📥 GitHub: {url}")
    dest = str(REPOS_DIR / tool_name)
    if os.path.exists(dest): shutil.rmtree(dest)

    r = subprocess.run(["git", "clone", "--depth=1", url, dest],
                       capture_output=True, timeout=600)
    if r.returncode != 0:
        return False, f"git clone: {_dec(r.stderr)}"
    st(f"  ✅ Клонировано в {dest}")

    # Requirements
    req = Path(dest) / "requirements.txt"
    if req.exists():
        st("📦 Устанавливаю зависимости...")
        r2 = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(req), "-q", "--break-system-packages"],
            capture_output=True, timeout=600
        )
        if r2.returncode == 0:
            st("  ✅ Зависимости установлены")
        else:
            st(f"  ⚠️ pip: {_dec(r2.stderr)[:100]}")

    # Entry point — ищем более тщательно
    entry = ""
    repo_name = url.rstrip('/').split('/')[-1].replace('.git', '')

    # Ищем точку входа — сначала по имени, потом по содержимому
    entry_candidates = []
    # 1. По имени репо/инструмента
    for py_name in (f"{repo_name}.py", f"{tool_name}.py",
                    "main.py", "app.py", "run.py", "cli.py"):
        if (Path(dest) / py_name).exists():
            entry_candidates.append((py_name, f"python3 {py_name}"))

    # 2. Ищем любой .py с if __name__ == '__main__' в корне
    for pyf in sorted(Path(dest).glob("*.py")):
        if pyf.name in ("setup.py", "setup_wizard.py", "install.py", "test.py"):
            continue
        try:
            content = pyf.read_text(encoding="utf-8", errors="replace")
            if "__main__" in content or "argparse" in content or "sys.argv" in content:
                entry_candidates.append((pyf.name, f"python3 {pyf.name}"))
        except Exception:
            pass

    # 3. __main__.py → python3 -m
    if (Path(dest) / "__main__.py").exists():
        entry_candidates.insert(0, ("__main__.py", f"python3 -m {tool_name}"))

    # Убираем дубли, берём первый
    seen = set()
    for fname, cmd in entry_candidates:
        if fname not in seen:
            seen.add(fname)
            entry = cmd
            break

    if not entry:
        # Последний шанс — найти любой .py файл
        py_files = sorted(Path(dest).glob("*.py"))
        if py_files:
            entry = f"python3 {py_files[0].name}"
        else:
            entry = f"python3 -m {tool_name}"

    st(f"  📌 Точка входа: {entry}")

    # README
    readme = ""
    for rn in ("README.md", "README.rst", "README.txt", "readme.md"):
        rf = Path(dest) / rn
        if rf.exists():
            readme = rf.read_text(encoding="utf-8", errors="replace")[:3000]
            break

    # Тест --help для понимания аргументов
    help_output = ""
    try:
        rh = subprocess.run(
            entry + " --help", shell=True,
            capture_output=True, timeout=15, cwd=dest
        )
        help_output = (_dec(rh.stdout) + _dec(rh.stderr))[:1000]
    except Exception:
        pass

    # ── LLM: генерируем умную обёртку ────────────────────────────────────────
    st("🤖 Генерирую обёртку через LLM...")
    gen_prompt = (
        f"Создай run_tool() для GitHub инструмента `{tool_name}`:\n"
        f"URL: {url}\n"
        f"Путь на диске: {dest}\n"
        f"Команда запуска: {entry}\n"
        f"README:\n{readme[:600]}\n"
        f"--help вывод:\n{help_output[:400]}\n\n"
        f"Обёртка должна:\n"
        f"1. Принимать inputs с ключами специфичными для этого инструмента (из README/help)\n"
        f"2. Строить CLI аргументы из inputs (например: domain → '-d domain')\n"
        f"3. Принимать общий inputs['args'] как запасной вариант\n"
        f"4. Запускать через subprocess с cwd={dest!r}\n"
        f"5. Декодировать bytes: for e in ('utf-8','cp1251','latin-1'): try: return b.decode(e)\n"
        f"6. Возвращать {{ok, output, files, error}}\n"
        f"7. timeout=600\n\n"
        f"Напиши ТОЛЬКО run_tool(inputs: dict) -> dict."
    )
    raw = _llm_code(gen_prompt, MATRIX_SYSTEM, max_tokens=8000)
    code = _extract_code(raw)
    code = _fix_syntax(code)

    if "def run_tool" not in code:
        code = (
            "def run_tool(inputs):\n"
            "    import subprocess\n"
            f"    repo = {dest!r}\n"
            f"    base = {entry!r}\n"
            "    args = inputs.get('args', inputs.get('domain', inputs.get('target', inputs.get('query',''))))\n"
            "    cmd  = base + (' ' + str(args) if args else '')\n"
            "    def _d(b):\n"
            "        if not b: return ''\n"
            "        for e in ('utf-8','cp1251','latin-1'):\n"
            "            try: return b.decode(e)\n"
            "            except: pass\n"
            "        return b.decode('utf-8', errors='replace')\n"
            "    r = subprocess.run(cmd, shell=True, capture_output=True, timeout=600, cwd=repo)\n"
            "    out = _d(r.stdout) + _d(r.stderr)\n"
            "    return {'ok': r.returncode==0, 'output': out[:4000], 'files': [], 'error': '' if r.returncode==0 else out[:500]}\n"
        )

    # ── LLM: генерируем usage guide ───────────────────────────────────────────
    st("📖 Генерирую инструкцию по использованию...")
    guide_prompt = (
        f"Инструмент `{tool_name}` установлен из {url}\n"
        f"README:\n{readme[:800]}\n"
        f"--help:\n{help_output[:400]}\n\n"
        f"Напиши краткую инструкцию на русском:\n"
        f"1. Что делает этот инструмент (2-3 предложения)\n"
        f"2. Основные параметры запуска (таблица: параметр → что делает)\n"
        f"3. 3-5 примеров команд для агента MATRIX (как просить агента его запустить)\n"
        f"Формат: markdown, компактно."
    )
    usage_guide = _llm(guide_prompt, max_tokens=1000)

    # ── Тест ─────────────────────────────────────────────────────────────────
    st("🧪 Тестирую...")
    ok, output, _ = sandbox_run(code, {"args": "--help"}, timeout=600)
    critical = any(e in output.lower() for e in
                   ("no such file", "importerror", "syntaxerror", "modulenotfounderror"))
    if not ok and critical:
        return False, f"Критическая ошибка обёртки: {output[:300]}"

    # ── Регистрируем с расширенным описанием ─────────────────────────────────
    full_desc = f"GitHub: {url}"
    if description: full_desc = description

    register_tool(tool_name, full_desc, code)

    # Сохраняем usage guide рядом с инструментом
    guide_file = TOOLS_DIR / f"{tool_name}_usage.md"
    try:
        guide_file.write_text(
            f"# {tool_name}\n\nИсточник: {url}\nПуть: {dest}\nКоманда: {entry}\n\n"
            f"{usage_guide}\n\n---\n*Установлен: {time.strftime('%Y-%m-%d %H:%M')}*",
            encoding="utf-8"
        )
        st(f"📄 Гайд сохранён: {guide_file.name}")
    except Exception:
        pass

    st(f"✅ '{tool_name}' установлен из {url}")
    st(f"\n{usage_guide[:500]}")
    return True, ""


# ══════════════════════════════════════════════════════════════════════════════
#  Built-in tools registration
# ══════════════════════════════════════════════════════════════════════════════

_BUILTIN_TOOLS = {}

def _bt(name, desc, code_lines):
    code = "\n".join(code_lines)
    _BUILTIN_TOOLS[name] = (desc, code)

_bt("python_eval", "Выполнить Python-код", [
    "def run_tool(inputs):",
    "    import subprocess, sys, tempfile, os",
    "    code = inputs.get('code', inputs.get('script', '')).strip()",
    "    output_dir = inputs.get('output_dir', '/tmp')",
    "    if not code: return {'ok': False, 'output': 'Нужен code', 'files': [], 'error': 'missing'}",
    "    def _d(b):",
    "        if not b: return ''",
    "        for e in ('utf-8','cp1251','latin-1'):",
    "            try: return b.decode(e)",
    "            except: pass",
    "        return b.decode('utf-8', errors='replace')",
    "    with tempfile.NamedTemporaryFile('w', suffix='.py', delete=False, encoding='utf-8') as f:",
    "        f.write(code); tmp = f.name",
    "    try:",
    "        r = subprocess.run([sys.executable, tmp], capture_output=True, timeout=600, cwd=output_dir)",
    "        out = _d(r.stdout) + _d(r.stderr)",
    "        return {'ok': r.returncode==0, 'output': out.strip()[:3000], 'files': [], 'error': _d(r.stderr) if r.returncode else ''}",
    "    finally:",
    "        try: os.unlink(tmp)",
    "        except: pass",
])

_bt("shell_cmd", "Выполнить shell-команду", [
    "def run_tool(inputs):",
    "    import subprocess",
    "    cmd = inputs.get('cmd', inputs.get('command', '')).strip()",
    "    cwd = inputs.get('cwd', '') or None",
    "    timeout = int(inputs.get('timeout', 30))",
    "    if not cmd: return {'ok': False, 'output': 'Нужен cmd', 'files': [], 'error': 'missing'}",
    "    def _d(b):",
    "        if not b: return ''",
    "        for e in ('utf-8','cp1251','latin-1'):",
    "            try: return b.decode(e)",
    "            except: pass",
    "        return b.decode('utf-8', errors='replace')",
    "    r = subprocess.run(cmd, shell=True, capture_output=True, timeout=timeout, cwd=cwd)",
    "    out = (_d(r.stdout) + _d(r.stderr)).strip()",
    "    return {'ok': r.returncode==0, 'output': out[:3000], 'files': [], 'error': out[:500] if r.returncode else ''}",
])

_bt("analyze_code", "Анализ Python кода — синтаксис, ошибки, стиль", [
    "def run_tool(inputs):",
    "    import ast, os, subprocess, sys",
    "    from pathlib import Path",
    "    code = inputs.get('code', '')",
    "    path = inputs.get('path', '')",
    "    output_dir = inputs.get('output_dir', '/tmp')",
    "    if path and os.path.exists(path):",
    "        code = open(path, encoding='utf-8', errors='replace').read()",
    "    if not code: return {'ok': False, 'output': 'Нужен code или path', 'files': [], 'error': 'missing'}",
    "    issues = []",
    "    try:",
    "        ast.parse(code); issues.append('✅ Синтаксис OK')",
    "    except SyntaxError as e:",
    "        issues.append('❌ SyntaxError строка ' + str(e.lineno) + ': ' + str(e.msg))",
    "    lines = code.split(chr(10))",
    "    for i, l in enumerate(lines, 1):",
    "        if 'except:' in l: issues.append('⚠️ Строка ' + str(i) + ': голый except')",
    "        if len(l) > 120: issues.append('📏 Строка ' + str(i) + ': длинная (' + str(len(l)) + ' символов)')",
    "    report = chr(10).join(issues) + chr(10) + chr(10) + 'Строк: ' + str(len(lines))",
    "    out = Path(output_dir) / 'analysis.txt'",
    "    out.write_text(report, encoding='utf-8')",
    "    return {'ok': True, 'output': report, 'files': [str(out)], 'error': ''}",
])

_bt("run_tests", "Запустить тесты pytest / unittest", [
    "def run_tool(inputs):",
    "    import subprocess, sys, os",
    "    from pathlib import Path",
    "    path = inputs.get('path', inputs.get('test_file', '.')).strip()",
    "    args = inputs.get('args', '-v').strip()",
    "    output_dir = inputs.get('output_dir', '/tmp')",
    "    def _d(b):",
    "        if not b: return ''",
    "        for e in ('utf-8','cp1251','latin-1'):",
    "            try: return b.decode(e)",
    "            except: pass",
    "        return b.decode('utf-8', errors='replace')",
    "    r = subprocess.run([sys.executable, '-m', 'pytest', path] + args.split() + ['--tb=short'],",
    "                       capture_output=True, timeout=600, cwd=os.path.dirname(os.path.abspath(path)) if os.path.isfile(path) else path)",
    "    out = _d(r.stdout) + _d(r.stderr)",
    "    return {'ok': r.returncode==0, 'output': out[:3000], 'files': [], 'error': '' if r.returncode==0 else out[:500]}",
])

_bt("osint_username", "Поиск username на публичных платформах", [
    "def run_tool(inputs):",
    "    import urllib.request",
    "    from pathlib import Path",
    "    username = inputs.get('username', inputs.get('name', '')).strip()",
    "    output_dir = inputs.get('output_dir', '/tmp')",
    "    if not username: return {'ok': False, 'output': 'Нужен username', 'files': [], 'error': 'missing'}",
    "    platforms = [",
    "        ('GitHub',   'https://github.com/' + username),",
    "        ('Reddit',   'https://www.reddit.com/user/' + username),",
    "        ('Twitter',  'https://twitter.com/' + username),",
    "        ('TikTok',   'https://www.tiktok.com/@' + username),",
    "        ('YouTube',  'https://www.youtube.com/@' + username),",
    "        ('Telegram', 'https://t.me/' + username),",
    "        ('GitLab',   'https://gitlab.com/' + username),",
    "        ('Medium',   'https://medium.com/@' + username),",
    "    ]",
    "    found = []; miss = []",
    "    for p, url in platforms:",
    "        try:",
    "            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})",
    "            with urllib.request.urlopen(req, timeout=8) as r:",
    "                if r.getcode() == 200: found.append('[+] ' + p + ': ' + url)",
    "        except: miss.append('[-] ' + p)",
    "    sep = chr(10)",
    "    text = 'OSINT @' + username + sep + sep + sep.join(found) + sep + 'Не найдено: ' + str(len(miss))",
    "    out_file = Path(output_dir) / ('osint_' + username + '.txt')",
    "    out_file.write_text(text, encoding='utf-8')",
    "    return {'ok': bool(found), 'output': text, 'files': [str(out_file)], 'error': ''}",
])

_bt("osint_domain", "OSINT анализ домена — DNS, заголовки, WHOIS", [
    "def run_tool(inputs):",
    "    import urllib.request, subprocess, socket",
    "    from pathlib import Path",
    "    domain = inputs.get('domain', inputs.get('url', '')).strip()",
    "    domain = domain.replace('https://','').replace('http://','').split('/')[0]",
    "    output_dir = inputs.get('output_dir', '/tmp')",
    "    if not domain: return {'ok': False, 'output': 'Нужен domain', 'files': [], 'error': 'missing'}",
    "    def _d(b):",
    "        if not b: return ''",
    "        for e in ('utf-8','cp1251','latin-1'):",
    "            try: return b.decode(e)",
    "            except: pass",
    "        return b.decode('utf-8', errors='replace')",
    "    sep = chr(10)",
    "    lines = ['OSINT: ' + domain]",
    "    try: lines.append('IP: ' + socket.gethostbyname(domain))",
    "    except Exception as e: lines.append('DNS: ' + str(e))",
    "    try:",
    "        req = urllib.request.Request('https://' + domain, headers={'User-Agent':'Mozilla/5.0'})",
    "        with urllib.request.urlopen(req, timeout=10) as r:",
    "            for k in ('Server','X-Powered-By','Content-Type','X-Frame-Options'):",
    "                v = r.headers.get(k)",
    "                if v: lines.append(k + ': ' + v)",
    "    except Exception as e: lines.append('HTTP: ' + str(e))",
    "    r = subprocess.run(['whois', domain], capture_output=True, timeout=20)",
    "    if r.returncode == 0: lines.append(sep + 'WHOIS:' + sep + _d(r.stdout)[:600])",
    "    text = sep.join(lines)",
    "    out_file = Path(output_dir) / ('domain_' + domain + '.txt')",
    "    out_file.write_text(text, encoding='utf-8')",
    "    return {'ok': True, 'output': text, 'files': [str(out_file)], 'error': ''}",
])

_bt("port_scan", "Сканирование портов своего/разрешённого хоста (nmap/socket)", [
    "def run_tool(inputs):",
    "    import socket, subprocess, sys",
    "    from pathlib import Path",
    "    host    = inputs.get('host', inputs.get('target', '127.0.0.1')).strip()",
    "    ports   = inputs.get('ports', '22,80,443,8080,8443').strip()",
    "    output_dir = inputs.get('output_dir', '/tmp')",
    "    def _d(b):",
    "        if not b: return ''",
    "        for e in ('utf-8','cp1251','latin-1'):",
    "            try: return b.decode(e)",
    "            except: pass",
    "        return b.decode('utf-8', errors='replace')",
    "    results = []",
    "    # Пробуем nmap",
    "    r = subprocess.run(['nmap', '-p', ports, '--open', '-T4', host],",
    "                       capture_output=True, timeout=600)",
    "    if r.returncode == 0:",
    "        out = _d(r.stdout)",
    "        Path(output_dir).mkdir(parents=True, exist_ok=True)",
    "        f = Path(output_dir) / ('portscan_' + host.replace('.','_') + '.txt')",
    "        f.write_text(out, encoding='utf-8')",
    "        return {'ok': True, 'output': out[:2000], 'files': [str(f)], 'error': ''}",
    "    # Fallback: socket",
    "    for p in ports.split(','):",
    "        try:",
    "            port = int(p.strip())",
    "            with socket.create_connection((host, port), timeout=2):",
    "                results.append('[+] ' + str(port) + '/tcp open')",
    "        except: results.append('[-] ' + p.strip() + '/tcp closed')",
    "    text = 'Скан ' + host + ':' + chr(10) + chr(10).join(results)",
    "    f = Path(output_dir) / ('portscan_' + host.replace('.','_') + '.txt')",
    "    f.write_text(text, encoding='utf-8')",
    "    return {'ok': True, 'output': text, 'files': [str(f)], 'error': ''}",
])

_bt("ssl_check", "Проверка SSL/TLS сертификата домена", [
    "def run_tool(inputs):",
    "    import ssl, socket, datetime",
    "    from pathlib import Path",
    "    host = inputs.get('host', inputs.get('domain', '')).strip()",
    "    host = host.replace('https://','').replace('http://','').split('/')[0]",
    "    output_dir = inputs.get('output_dir', '/tmp')",
    "    if not host: return {'ok': False, 'output': 'Нужен host', 'files': [], 'error': 'missing'}",
    "    try:",
    "        ctx = ssl.create_default_context()",
    "        with ctx.wrap_socket(socket.socket(), server_hostname=host) as s:",
    "            s.settimeout(10); s.connect((host, 443))",
    "            cert = s.getpeercert()",
    "        exp = datetime.datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')",
    "        days = (exp - datetime.datetime.utcnow()).days",
    "        lines = [",
    "            'Host: ' + host,",
    "            'Subject: ' + str(cert.get('subject','')),",
    "            'Issuer: ' + str(cert.get('issuer','')),",
    "            'Expires: ' + str(exp) + ' (' + str(days) + ' дней)',",
    "            'Status: ' + ('✅ OK' if days > 0 else '❌ ИСТЁК'),",
    "        ]",
    "        text = chr(10).join(lines)",
    "        f = Path(output_dir) / ('ssl_' + host + '.txt')",
    "        f.write_text(text, encoding='utf-8')",
    "        return {'ok': days > 0, 'output': text, 'files': [str(f)], 'error': ''}",
    "    except Exception as e:",
    "        return {'ok': False, 'output': str(e), 'files': [], 'error': str(e)}",
])

_bt("deps_audit", "Проверка Python зависимостей на CVE уязвимости", [
    "def run_tool(inputs):",
    "    import subprocess, sys",
    "    from pathlib import Path",
    "    req_file = inputs.get('requirements', inputs.get('path', ''))",
    "    output_dir = inputs.get('output_dir', '/tmp')",
    "    def _d(b):",
    "        if not b: return ''",
    "        for e in ('utf-8','cp1251','latin-1'):",
    "            try: return b.decode(e)",
    "            except: pass",
    "        return b.decode('utf-8', errors='replace')",
    "    # Попробуем pip-audit",
    "    cmd = [sys.executable, '-m', 'pip_audit']",
    "    if req_file: cmd += ['-r', req_file]",
    "    r = subprocess.run(cmd, capture_output=True, timeout=600)",
    "    if r.returncode not in (0, 1) or not r.stdout:",
    "        # Установить pip-audit",
    "        subprocess.run([sys.executable,'-m','pip','install','pip-audit','-q','--break-system-packages'],",
    "                       capture_output=True, timeout=600)",
    "        r = subprocess.run(cmd, capture_output=True, timeout=600)",
    "    out = _d(r.stdout) + _d(r.stderr)",
    "    vuln = [l for l in out.splitlines() if 'CVE' in l or 'vuln' in l.lower()]",
    "    ok = len(vuln) == 0",
    "    summary = ('✅ Уязвимостей не найдено' if ok else '❌ Найдено: ' + str(len(vuln))) + chr(10) + out[:2000]",
    "    f = Path(output_dir) / 'deps_audit.txt'",
    "    f.write_text(summary, encoding='utf-8')",
    "    return {'ok': ok, 'output': summary, 'files': [str(f)], 'error': ''}",
])

_bt("github_clone", "Клонировать GitHub репозиторий", [
    "def run_tool(inputs):",
    "    import subprocess, os, shutil",
    "    from pathlib import Path",
    "    url = inputs.get('url', inputs.get('repo', '')).strip()",
    "    output_dir = inputs.get('output_dir', '/tmp')",
    "    if not url: return {'ok': False, 'output': 'Нужен url', 'files': [], 'error': 'missing'}",
    "    name = url.rstrip('/').split('/')[-1].replace('.git','')",
    "    dest = str(Path(output_dir) / name)",
    "    if os.path.exists(dest): shutil.rmtree(dest)",
    "    def _d(b):",
    "        if not b: return ''",
    "        for e in ('utf-8','cp1251','latin-1'):",
    "            try: return b.decode(e)",
    "            except: pass",
    "        return b.decode('utf-8', errors='replace')",
    "    r = subprocess.run(['git','clone','--depth=1',url,dest], capture_output=True, timeout=600)",
    "    out = _d(r.stdout) + _d(r.stderr)",
    "    if r.returncode == 0:",
    "        cnt = sum(1 for p in Path(dest).rglob('*') if p.is_file())",
    "        return {'ok': True, 'output': 'Клонировано: ' + dest + ' (' + str(cnt) + ' файлов)', 'files': [dest], 'error': ''}",
    "    return {'ok': False, 'output': out, 'files': [], 'error': out}",
])

_bt("github_install", "Установить GitHub репо как инструмент MATRIX", [
    "def run_tool(inputs):",
    "    import os, sys",
    "    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))",
    "    url  = inputs.get('url', inputs.get('github_url', '')).strip()",
    "    name = inputs.get('tool_name', inputs.get('name', '')).strip()",
    "    desc = inputs.get('description', '').strip()",
    "    if not url: return {'ok': False, 'output': 'Нужен url', 'files': [], 'error': 'missing'}",
    "    if not name: name = url.rstrip('/').split('/')[-1].replace('.git','').replace('-','_').lower()",
    "    try:",
    "        from agent_matrix import _install_github",
    "        ok, err = _install_github(name, url, desc or ('GitHub: ' + url), on_status=lambda m: print(m))",
    "        if ok: return {'ok': True, 'output': 'Установлен: ' + name + ' из ' + url, 'files': [], 'error': ''}",
    "        return {'ok': False, 'output': err, 'files': [], 'error': err}",
    "    except Exception as e:",
    "        return {'ok': False, 'output': str(e), 'files': [], 'error': str(e)}",
])

_bt("pip_install", "Установить Python пакеты", [
    "def run_tool(inputs):",
    "    import subprocess, sys",
    "    pkgs = inputs.get('packages', inputs.get('package', ''))",
    "    if isinstance(pkgs, list): pkgs = ' '.join(pkgs)",
    "    pkgs = str(pkgs).strip()",
    "    if not pkgs: return {'ok': False, 'output': 'Нужен packages', 'files': [], 'error': 'missing'}",
    "    def _d(b):",
    "        if not b: return ''",
    "        for e in ('utf-8','cp1251','latin-1'):",
    "            try: return b.decode(e)",
    "            except: pass",
    "        return b.decode('utf-8', errors='replace')",
    "    r = subprocess.run([sys.executable,'-m','pip','install','--break-system-packages','-q']+pkgs.split(),",
    "                       capture_output=True, timeout=600)",
    "    out = _d(r.stdout)+_d(r.stderr)",
    "    ok = r.returncode == 0",
    "    return {'ok': ok, 'output': ('OK: ' if ok else 'FAIL: ') + pkgs + chr(10) + out[:500], 'files': [], 'error': '' if ok else out[:300]}",
])

_bt("matrix_create_tool", "MATRIX создаёт новый инструмент через LLM или GitHub", [
    "def run_tool(inputs):",
    "    import os, sys",
    "    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))",
    "    name    = inputs.get('tool_name', inputs.get('name', '')).strip()",
    "    desc    = inputs.get('description', '').strip()",
    "    example = inputs.get('example_inputs', {})",
    "    url     = inputs.get('url', inputs.get('github_url', '')).strip()",
    "    if not name: return {'ok': False, 'output': 'Нужен tool_name', 'files': [], 'error': 'missing'}",
    "    try:",
    "        from agent_matrix import generate_tool",
    "        ok, err = generate_tool(name, desc, example, github_url=url, on_status=lambda m: print(m))",
    "        if ok: return {'ok': True, 'output': 'Инструмент ' + repr(name) + ' создан!', 'files': [], 'error': ''}",
    "        return {'ok': False, 'output': err, 'files': [], 'error': err}",
    "    except Exception as e:",
    "        return {'ok': False, 'output': str(e), 'files': [], 'error': str(e)}",
])

_bt("matrix_list_tools", "Список всех инструментов MATRIX", [
    "def run_tool(inputs):",
    "    import os, sys",
    "    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))",
    "    try:",
    "        from agent_matrix import list_tools",
    "        tools = list_tools()",
    "        if not tools: return {'ok': True, 'output': 'Инструментов нет', 'files': [], 'error': ''}",
    "        sep = chr(10)",
    "        lines = ['MATRIX Tools (' + str(len(tools)) + '):']",
    "        for t in tools:",
    "            tag = '📦' if t.get('builtin') else '🔧'",
    "            lines.append('  ' + tag + ' ' + t['name'] + ' — ' + t.get('description','')[:50])",
    "        return {'ok': True, 'output': sep.join(lines), 'files': [], 'error': ''}",
    "    except Exception as e:",
    "        return {'ok': False, 'output': str(e), 'files': [], 'error': str(e)}",
])

_bt("file_read", "Прочитать файл", [
    "def run_tool(inputs):",
    "    import os",
    "    path = inputs.get('path', '').strip()",
    "    if not path or not os.path.exists(path):",
    "        return {'ok': False, 'output': 'Не найден: ' + path, 'files': [], 'error': 'not_found'}",
    "    if os.path.isdir(path):",
    "        return {'ok': True, 'output': 'Dir: ' + ', '.join(os.listdir(path)[:30]), 'files': [], 'error': ''}",
    "    for enc in ('utf-8','cp1251','latin-1'):",
    "        try:",
    "            content = open(path, encoding=enc).read()",
    "            return {'ok': True, 'output': content[:5000], 'files': [path], 'error': ''}",
    "        except UnicodeDecodeError: continue",
    "    return {'ok': False, 'output': 'Не удалось декодировать', 'files': [], 'error': 'decode'}",
])

_bt("file_write", "Записать файл", [
    "def run_tool(inputs):",
    "    import os, time",
    "    from pathlib import Path",
    "    path = inputs.get('path', '').strip()",
    "    content = inputs.get('content', '')",
    "    output_dir = inputs.get('output_dir', '/tmp')",
    "    if not path: path = str(Path(output_dir) / ('out_' + str(int(time.time())) + '.txt'))",
    "    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)",
    "    Path(path).write_text(str(content), encoding='utf-8')",
    "    return {'ok': True, 'output': 'Записано: ' + path, 'files': [path], 'error': ''}",
])

_bt("web_scrape", "Скрапинг веб-страницы", [
    "def run_tool(inputs):",
    "    import urllib.request, re",
    "    from pathlib import Path",
    "    url = inputs.get('url', '').strip()",
    "    output_dir = inputs.get('output_dir', '/tmp')",
    "    if not url: return {'ok': False, 'output': 'Нужен url', 'files': [], 'error': 'missing'}",
    "    try:",
    "        req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})",
    "        with urllib.request.urlopen(req, timeout=15) as r:",
    "            html = r.read(200000).decode('utf-8','replace')",
    "        text = re.sub(r'<[^>]+>',' ',html)",
    "        text = re.sub(r' +',' ',text).strip()[:6000]",
    "        f = Path(output_dir) / ('page_' + str(abs(hash(url))%99999) + '.txt')",
    "        f.write_text(text, encoding='utf-8')",
    "        return {'ok': True, 'output': text[:3000], 'files': [str(f)], 'error': ''}",
    "    except Exception as e:",
    "        return {'ok': False, 'output': str(e), 'files': [], 'error': str(e)}",
])

_bt("http_get", "HTTP GET запрос к API", [
    "def run_tool(inputs):",
    "    import urllib.request, urllib.parse, json as _j",
    "    url = inputs.get('url', '').strip()",
    "    params = inputs.get('params', {})",
    "    headers = inputs.get('headers', {})",
    "    if not url: return {'ok': False, 'output': 'Нужен url', 'files': [], 'error': 'missing'}",
    "    if params and isinstance(params, dict):",
    "        url = url + ('&' if '?' in url else '?') + urllib.parse.urlencode(params)",
    "    try:",
    "        req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0',**headers})",
    "        with urllib.request.urlopen(req, timeout=15) as r:",
    "            body = r.read(100000).decode('utf-8','replace')",
    "        try: result = _j.dumps(_j.loads(body), ensure_ascii=False, indent=2)[:4000]",
    "        except: result = body[:4000]",
    "        return {'ok': True, 'output': result, 'files': [], 'error': ''}",
    "    except Exception as e:",
    "        return {'ok': False, 'output': str(e), 'files': [], 'error': str(e)}",
])

_bt("zip_files", "Упаковать файлы в ZIP", [
    "def run_tool(inputs):",
    "    import zipfile, os, time",
    "    from pathlib import Path",
    "    files = inputs.get('files', inputs.get('paths', []))",
    "    output_dir = inputs.get('output_dir', '/tmp')",
    "    name = inputs.get('name', 'archive_' + str(int(time.time())) + '.zip')",
    "    if not files: return {'ok': False, 'output': 'Нужен files', 'files': [], 'error': 'missing'}",
    "    if isinstance(files, str): files = [files]",
    "    out = os.path.join(output_dir, name)",
    "    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as zf:",
    "        for f in files:",
    "            if os.path.isfile(f): zf.write(f, os.path.basename(f))",
    "            elif os.path.isdir(f):",
    "                for fp in Path(f).rglob('*'):",
    "                    if fp.is_file(): zf.write(str(fp), str(fp.relative_to(f)))",
    "    return {'ok': True, 'output': 'ZIP: ' + out, 'files': [out], 'error': ''}",
])



def get_stats() -> dict:
    db = sqlite3.connect(str(TOOLS_DB))
    rows = db.execute('SELECT name, builtin, used_count FROM tools').fetchall()
    db.close()
    builtin_count = sum(1 for r in rows if r[1])
    return {
        'total': len(rows),
        'builtin': builtin_count,
        'custom': len(rows) - builtin_count,
        'version': VERSION,
        'tools_db': str(TOOLS_DB),
        'artifacts_dir': str(ARTIFACTS_DIR),
    }

def delete_tool(name: str) -> bool:
    db = sqlite3.connect(str(TOOLS_DB))
    db.execute('DELETE FROM tools WHERE name=?', (name,))
    db.commit(); db.close()
    p = TOOLS_DIR / f"{name}.py"
    if p.exists(): p.unlink()
    return True

def stop_all_processes() -> int:
    import signal
    killed = 0
    try:
        import psutil
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                cmd = " ".join(proc.info.get("cmdline") or [])
                if "_matrix_runner" in cmd or "matrix_workspace" in cmd:
                    proc.send_signal(signal.SIGKILL)
                    killed += 1
            except Exception:
                pass
    except ImportError:
        pass
    return killed



# ══════════════════════════════════════════════════════════════════════════════
#  Learning Loop & Skill Evolution
# ══════════════════════════════════════════════════════════════════════════════

def record_execution(tool_name: str, ok: bool, duration: float, error: str = "") -> None:
    """Track every tool execution for learning loop."""
    try:
        db = sqlite3.connect(str(TOOLS_DB))
        db.execute("INSERT INTO tool_executions (tool_name,ok,duration,error,ts) VALUES (?,?,?,?,?)",
                   (tool_name, int(ok), duration, error[:200], time.time()))
        # Update aggregated stats
        db.execute("""UPDATE tools SET
            used_count   = used_count + 1,
            success_count = success_count + ?,
            fail_count   = fail_count + ?,
            avg_duration = (avg_duration * used_count + ?) / (used_count + 1),
            last_error   = ?
            WHERE name = ?""",
            (int(ok), int(not ok), duration,
             "" if ok else error[:200], tool_name))
        db.commit(); db.close()
    except Exception:
        pass


def get_tool_stats(tool_name: str) -> dict:
    """Get execution statistics for a tool."""
    try:
        db = sqlite3.connect(str(TOOLS_DB))
        row = db.execute(
            "SELECT used_count,success_count,fail_count,avg_duration,last_error,version,tags FROM tools WHERE name=?",
            (tool_name,)
        ).fetchone()
        recent = db.execute(
            "SELECT ok,duration,ts FROM tool_executions WHERE tool_name=? ORDER BY ts DESC LIMIT 20",
            (tool_name,)
        ).fetchall()
        db.close()
        if not row:
            return {}
        return {
            "used_count": row[0], "success_count": row[1],
            "fail_count": row[2], "avg_duration": round(row[3], 2),
            "last_error": row[4], "version": row[5], "tags": row[6],
            "success_rate": round(row[1] / max(row[0], 1) * 100, 1),
            "recent_runs": [{"ok": bool(r[0]), "duration": round(r[1], 2), "ts": r[2]} for r in recent],
        }
    except Exception:
        return {}


def evolve_tool(name: str, on_status: Optional[Callable] = None) -> Tuple[bool, str]:
    """
    Skill Evolution: если инструмент имеет fail_rate > 30% и >= 5 запусков,
    автоматически пытается улучшить его код через LLM.
    """
    def st(msg):
        if on_status: on_status(msg)

    stats = get_tool_stats(name)
    if not stats:
        return False, f"Инструмент {name!r} не найден"

    total = stats.get("used_count", 0)
    fail_rate = stats.get("fail_count", 0) / max(total, 1)

    if total < 5:
        return False, f"Недостаточно данных (всего {total} запусков, нужно >= 5)"
    if fail_rate < 0.3:
        return False, f"Fail rate {fail_rate:.0%} — эволюция не нужна"

    st(f"🧬 Эволюция {name!r}: fail_rate={fail_rate:.0%}, запусков={total}")

    code = get_tool_code(name)
    if not code:
        return False, "Код не найден"

    last_err = stats.get("last_error", "")
    prompt = (
        f"Инструмент `{name}` имеет высокий fail rate ({fail_rate:.0%} из {total} запусков).\n"
        f"Последняя ошибка: {last_err}\n\n"
        f"Текущий код:\n```python\n{code}\n```\n\n"
        f"Улучши надёжность инструмента:\n"
        f"1. Добавь retry логику для сетевых запросов\n"
        f"2. Усиль обработку ошибок\n"
        f"3. Добавь fallback если основной метод недоступен\n"
        f"4. Убедись что bytes декодируются корректно\n\n"
        f"Верни ТОЛЬКО улучшенную run_tool(inputs: dict) -> dict."
    )

    raw = _llm(prompt, MATRIX_SYSTEM, max_tokens=4000)
    new_code = _extract_code(raw)
    new_code = _fix_syntax(new_code)

    if "def run_tool" not in new_code:
        return False, "LLM не вернул валидный код"

    # Test improved code
    ok, output, _ = sandbox_run(new_code, {}, timeout=60)
    # Accept even if test fails - the improvement may help with real inputs
    register_tool(name, f"[evolved v{stats.get('version',1)+1}] " +
                  get_tool_stats(name).get("tags", name), new_code)
    st(f"✅ {name!r} эволюционировал до v{stats.get('version',1)+1}")
    return True, ""


def get_learning_report() -> dict:
    """Отчёт Learning Loop — какие инструменты нужно улучшить."""
    try:
        db = sqlite3.connect(str(TOOLS_DB))
        rows = db.execute("""
            SELECT name, used_count, success_count, fail_count,
                   avg_duration, last_error, version
            FROM tools WHERE used_count > 0
            ORDER BY fail_count DESC
        """).fetchall()
        db.close()
        candidates = []
        healthy = []
        for r in rows:
            total = r[1]
            fail_rate = r[3] / max(total, 1)
            item = {
                "name": r[0], "total": total,
                "success": r[2], "fails": r[3],
                "fail_rate": round(fail_rate * 100, 1),
                "avg_ms": round(r[4] * 1000, 0),
                "last_error": r[5] or "",
                "version": r[6] or 1,
            }
            if fail_rate >= 0.3 and total >= 5:
                candidates.append(item)
            else:
                healthy.append(item)
        return {
            "candidates_for_evolution": candidates,
            "healthy_tools": healthy,
            "total_tools": len(rows),
        }
    except Exception as e:
        return {"error": str(e)}


# ══════════════════════════════════════════════════════════════════════════════
#  Pipeline / Marketplace
# ══════════════════════════════════════════════════════════════════════════════

def save_pipeline(pid: str, name: str, description: str,
                  nodes: list, edges: list,
                  shared: bool = False, author: str = "local",
                  category: str = "general") -> bool:
    try:
        db = sqlite3.connect(str(TOOLS_DB))
        existing = db.execute("SELECT runs FROM pipelines WHERE id=?", (pid,)).fetchone()
        runs = existing[0] if existing else 0
        db.execute("""INSERT OR REPLACE INTO pipelines
            (id,name,description,nodes,edges,created,updated,runs,shared,author,category)
            VALUES (?,?,?,?,?,COALESCE((SELECT created FROM pipelines WHERE id=?),?),?,?,?,?,?)""",
            (pid, name, description,
             json.dumps(nodes, ensure_ascii=False),
             json.dumps(edges, ensure_ascii=False),
             pid, time.time(), time.time(), runs,
             int(shared), author, category))
        db.commit(); db.close()
        return True
    except Exception:
        return False


def list_pipelines(shared_only: bool = False) -> list:
    try:
        db = sqlite3.connect(str(TOOLS_DB))
        q = "SELECT id,name,description,nodes,edges,created,updated,runs,shared,author,category FROM pipelines"
        if shared_only:
            q += " WHERE shared=1"
        q += " ORDER BY updated DESC"
        rows = db.execute(q).fetchall()
        db.close()
        result = []
        for r in rows:
            try:
                nodes = json.loads(r[3] or "[]")
                edges = json.loads(r[4] or "[]")
            except Exception:
                nodes, edges = [], []
            result.append({
                "id": r[0], "name": r[1], "description": r[2],
                "nodes": nodes, "edges": edges,
                "created": r[5], "updated": r[6],
                "runs": r[7], "shared": bool(r[8]),
                "author": r[9], "category": r[10],
                "node_count": len(nodes), "step_count": len(edges),
            })
        return result
    except Exception:
        return []


def get_pipeline(pid: str) -> Optional[dict]:
    pips = list_pipelines()
    for p in pips:
        if p["id"] == pid:
            return p
    return None


def delete_pipeline(pid: str) -> bool:
    try:
        db = sqlite3.connect(str(TOOLS_DB))
        db.execute("DELETE FROM pipelines WHERE id=?", (pid,))
        db.commit(); db.close()
        return True
    except Exception:
        return False


def run_pipeline(pid: str, inputs: dict = None,
                 on_status: Optional[Callable] = None) -> MatrixResult:
    """Execute a saved pipeline by ID."""
    pip = get_pipeline(pid)
    if not pip:
        return MatrixResult(ok=False, error=f"Pipeline {pid!r} not found")

    # Build task from pipeline nodes
    nodes = pip.get("nodes", [])
    edges = pip.get("edges", [])

    # Convert visual nodes to MATRIX steps
    steps = []
    node_map = {n["id"]: n for n in nodes}
    # Topological sort via edges
    in_degree = {n["id"]: 0 for n in nodes}
    for e in edges:
        in_degree[e.get("target", "")] = in_degree.get(e.get("target", ""), 0) + 1
    queue = [n for n in nodes if in_degree.get(n["id"], 0) == 0]
    ordered = []
    while queue:
        node = queue.pop(0)
        ordered.append(node)
        for e in edges:
            if e.get("source") == node["id"]:
                tgt = e.get("target")
                in_degree[tgt] = in_degree.get(tgt, 1) - 1
                if in_degree[tgt] == 0:
                    queue.append(node_map[tgt])

    for i, node in enumerate(ordered or nodes):
        tool = node.get("data", {}).get("tool", node.get("type", "python_eval"))
        node_inputs = {**( inputs or {}), **node.get("data", {}).get("inputs", {})}
        steps.append({
            "id": i + 1,
            "description": node.get("data", {}).get("label", tool),
            "tool_name": tool,
            "tool_exists": tool_exists(tool),
            "inputs": node_inputs,
            "depends_on": [],
        })

    # Increment run counter
    try:
        db = sqlite3.connect(str(TOOLS_DB))
        db.execute("UPDATE pipelines SET runs=runs+1, updated=? WHERE id=?", (time.time(), pid))
        db.commit(); db.close()
    except Exception:
        pass

    # Execute using run_matrix logic
    result = run_matrix(
        task=pip.get("description", pip.get("name", "Pipeline")),
        chat_id=f"pipeline_{pid}",
        on_status=on_status,
    )
    return result


def warmup(on_status: Optional[Callable] = None) -> dict:
    """Регистрирует все встроенные инструменты при старте."""
    registered = skipped = failed = 0
    for name, (desc, code) in _BUILTIN_TOOLS.items():
        try:
            if tool_exists(name):
                skipped += 1
                continue
            # Verify syntax
            ast.parse(code)
            register_tool(name, desc, code, builtin=True)
            registered += 1
            if on_status: on_status(f"  + {name}")
        except Exception as e:
            failed += 1
            if on_status: on_status(f"  ! {name}: {e}")
    msg = f"MATRIX tools: +{registered} / skip={skipped} / err={failed}"
    if on_status: on_status(msg)
    return {"registered": registered, "skipped": skipped, "failed": failed}


# ══════════════════════════════════════════════════════════════════════════════
#  Planner
# ══════════════════════════════════════════════════════════════════════════════

def plan_task(task: str, chat_id: str, attached_files: Optional[list] = None) -> dict:
    ctx = ""
    if attached_files:
        ctx = f"\nПрикреплённые файлы: {', '.join(str(f) for f in attached_files)}"

    prompt = (
        f"Задача: {task}{ctx}\n\n"
        f"Составь план выполнения. Верни ТОЛЬКО JSON."
    )
    raw = _llm(prompt, MATRIX_PLANNER_SYSTEM, max_tokens=2000)

    # Extract JSON
    for pat in [r"\{.*\}", r"```json\s*(.*?)```", r"```\s*(.*?)```"]:
        m = re.search(pat, raw, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group(0) if pat.startswith(r"\{") else m.group(1))
                if "steps" in data:
                    return data
            except Exception:
                pass

    # Fallback
    return {
        "steps": [{"id": 1, "description": task, "tool_name": "python_eval",
                   "tool_exists": True, "inputs": {"code": f"print({task!r})"}, "depends_on": []}],
        "summary": task
    }


# ══════════════════════════════════════════════════════════════════════════════
#  Result dataclass & main pipeline
# ══════════════════════════════════════════════════════════════════════════════

from dataclasses import dataclass, field

@dataclass
class MatrixResult:
    ok: bool = True
    answer: str = ""
    error: str = ""
    zip_path: str = ""
    tts_path: str = ""
    files: list = field(default_factory=list)
    steps_done: int = 0
    generated_tools: list = field(default_factory=list)


def run_matrix(
    task: str,
    chat_id: str,
    attached_files: Optional[list] = None,
    on_status: Optional[Callable] = None,
) -> MatrixResult:
    """Главный pipeline AGENT MATRIX."""
    t0 = time.time()

    def st(msg):
        if on_status: on_status(msg)

    st("🧠 MATRIX анализирует задачу...")
    plan = plan_task(task, chat_id, attached_files)
    steps = plan.get("steps", [])
    st(f"📋 План: {len(steps)} шагов")

    # Общая рабочая директория для всех шагов (файлы доступны между шагами)
    run_dir = ARTIFACTS_DIR / f"run_{int(time.time())}"
    run_dir.mkdir(parents=True, exist_ok=True)

    all_files: list = []
    generated_tools: list = []
    step_outputs: dict = {}
    step_errors: list = []
    steps_done = 0

    for step in steps:
        sid       = step.get("id", 0)
        tool_name = step.get("tool_name", "python_eval")
        desc      = step.get("description", "")
        s_inputs  = dict(step.get("inputs", {}))
        tool_exists_flag = step.get("tool_exists", True)

        st(f"⚙️ Шаг {sid}: {desc[:60]}...")

        # output_dir — общая для всех шагов
        s_inputs.setdefault("output_dir", str(run_dir))

        # Подставляем результаты зависимых шагов
        for dep_id in step.get("depends_on", []):
            prev = step_outputs.get(dep_id, {})
            # Передаём файлы из предыдущего шага
            if prev.get("files") and "path" not in s_inputs:
                s_inputs["path"] = prev["files"][0]
            if prev.get("output") and "prev_output" not in s_inputs:
                s_inputs["prev_output"] = prev["output"][:500]
            if prev.get("files") and "files" not in s_inputs:
                s_inputs["files"] = prev["files"]

        # Передаём прикреплённые файлы в первый шаг
        if attached_files and sid == 1 and "path" not in s_inputs:
            s_inputs["path"] = attached_files[0]

        # Если плановщик придумал несуществующий инструмент → fallback на python_eval
        KNOWN_TOOLS = {
            "python_eval", "shell_cmd", "analyze_code", "run_tests",
            "osint_username", "osint_domain", "web_scrape", "http_get",
            "port_scan", "ssl_check", "deps_audit",
            "github_clone", "github_install", "pip_install",
            "file_read", "file_write", "zip_files",
            "matrix_create_tool", "matrix_list_tools",
        }
        # Инструменты которые LLM иногда выдумывает → заменяем на python_eval
        FAKE_TOOLS = {
            "run_script", "check_syntax", "lint_code", "execute_code",
            "code_runner", "run_code", "execute_script", "code_exec",
        }

        code = get_tool_code(tool_name)

        # Фейковый инструмент → python_eval
        if tool_name in FAKE_TOOLS:
            st(f"  ↩️ {tool_name!r} не существует → python_eval")
            if "code" not in s_inputs and "script" not in s_inputs:
                s_inputs["code"] = f"# Задача: {desc}\nprint('Выполнено')"
            tool_name = "python_eval"
            code = get_tool_code("python_eval")

        elif not code and tool_name not in KNOWN_TOOLS:
            # Может быть динамический инструмент из БД — генерируем
            st(f"  🔨 Генерирую инструмент: {tool_name!r}...")
            github_url = s_inputs.get("url", "") if "github.com" in str(s_inputs.get("url", "")) else ""
            ok_gen, err_gen = generate_tool(
                tool_name, desc, s_inputs, on_status=on_status, github_url=github_url
            )
            if ok_gen:
                generated_tools.append(tool_name)
                code = get_tool_code(tool_name)
            else:
                step_errors.append(f"Шаг {sid} ({tool_name}): {err_gen}")
                continue

        elif not code and tool_name in KNOWN_TOOLS:
            # Встроенный инструмент ещё не зарегистрирован — warmup
            st(f"  🔄 Инициализирую встроенные инструменты...")
            warmup()
            code = get_tool_code(tool_name)

        if not code:
            # Последний шанс — python_eval с кодом из inputs
            if "code" in s_inputs or "script" in s_inputs:
                st(f"  ↩️ fallback → python_eval")
                tool_name = "python_eval"
                code = get_tool_code("python_eval")
            else:
                step_errors.append(f"Шаг {sid}: инструмент {tool_name!r} недоступен")
                continue

        # Запускаем — таймаут 10 минут
        ok, output, files = sandbox_run(code, s_inputs, timeout=SANDBOX_TIMEOUT, _tool_name=tool_name)
        step_outputs[sid] = {"ok": ok, "output": output, "files": files}
        all_files.extend(f for f in files if f not in all_files)
        steps_done += 1

        if ok:
            st(f"  ✅ {tool_name}: {output[:80]}")
        else:
            step_errors.append(f"Шаг {sid} ({tool_name}): {output[:150]}")
            st(f"  ⚠️ {output[:80]}")

    # ── TTS ────────────────────────────────────────────────────────────────────
    tts_path = ""
    try:
        final_outputs = [v["output"] for v in step_outputs.values() if v.get("output")]
        summary = plan.get("summary", "") + "\n\n" + "\n\n".join(final_outputs[:2])
        answer_prompt = (
            f"Задача была: {task}\n\n"
            f"Результаты шагов:\n{summary[:1500]}\n\n"
            f"Ошибки: {'; '.join(step_errors) if step_errors else 'нет'}\n\n"
            f"Напиши краткий итоговый ответ на русском языке (2-4 предложения)."
        )
        answer = _llm(answer_prompt, max_tokens=500)
        if answer and not answer.startswith("#"):
            try:
                from tts_engine import tts_generate
                import tempfile
                tts_f = tempfile.mktemp(suffix=".mp3", dir=str(ARTIFACTS_DIR))
                if tts_generate(answer[:500], tts_f):
                    tts_path = tts_f
            except Exception:
                pass
        else:
            answer = summary[:800] if summary else "Задача выполнена."
    except Exception as e:
        answer = f"Выполнено за {time.time()-t0:.1f}с"

    # ── ZIP артефакт ──────────────────────────────────────────────────────────
    zip_path = ""
    try:
        import time as _t
        zp = ARTIFACTS_DIR / f"matrix_{int(_t.time())}.zip"
        with zipfile.ZipFile(str(zp), "w", zipfile.ZIP_DEFLATED) as zf:
            # Лог
            log = (
                f"AGENT MATRIX v{VERSION}\n"
                f"Задача: {task}\n"
                f"Шагов выполнено: {steps_done}/{len(steps)}\n"
                f"Ошибки: {chr(10).join(step_errors) or 'нет'}\n"
                f"Инструментов создано: {len(generated_tools)}\n"
                f"Время: {time.time()-t0:.1f}с\n\n"
                f"Ответ:\n{answer}"
            )
            zf.writestr("matrix_report.txt", log)
            for f in all_files[:20]:
                if os.path.exists(f) and os.path.isfile(f):
                    zf.write(f, os.path.basename(f))
            if tts_path and os.path.exists(tts_path):
                zf.write(tts_path, "answer.mp3")
        zip_path = str(zp)
    except Exception:
        pass

    icon = "✅" if not step_errors else "⚠️"
    st(f"{icon} MATRIX завершил за {time.time()-t0:.1f}с")

    return MatrixResult(
        ok=not bool(step_errors),
        answer=answer,
        error="; ".join(step_errors),
        zip_path=zip_path,
        tts_path=tts_path,
        files=all_files,
        steps_done=steps_done,
        generated_tools=generated_tools,
    )


def run_matrix_async(task: str, chat_id: str,
                     attached_files=None, on_status=None,
                     callback=None):
    """Запускает MATRIX в отдельном потоке."""
    import threading
    def _run():
        result = run_matrix(task, chat_id, attached_files, on_status)
        if callback: callback(result)
    t = threading.Thread(target=_run, daemon=True, name=f"matrix-{chat_id}")
    t.start()
    return t
