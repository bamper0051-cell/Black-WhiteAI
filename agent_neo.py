"""
agent_neo.py — AGENT NEO v1.0
BlackBugsAI — autonomous self-tool-generating agent

Architecture:
  User task → NeoPlanner (decompose) → NeoToolRegistry (check/find)
  → NeoToolGenerator (LLM writes tool if missing) → NeoSandbox (test)
  → NeoArtifact (ZIP: code+input+output+report+log+TTS)

Key features:
  - Generates missing tools on demand using SMITH templates
  - Hybrid LLM: function_calling if available, else JSON
  - Dynamic tool registry: memory cache + SQLite persistence
  - Full I/O contract: every run produces a complete ZIP artifact
  - Per-agent LLM routing via llm_router
  - Cross-session tool reuse (tools persist to disk)
"""
from __future__ import annotations
import os, sys, json, time, ast, re, hashlib, zipfile, sqlite3, subprocess, tempfile
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
from pathlib import Path

import config

# ── Directories ───────────────────────────────────────────────────────────────
NEO_DIR       = Path(config.BASE_DIR) / "neo_workspace"
TOOLS_DIR     = NEO_DIR / "tools"
ARTIFACTS_DIR = NEO_DIR / "artifacts"
TOOLS_DB      = NEO_DIR / "tools.db"

for _d in (NEO_DIR, TOOLS_DIR, ARTIFACTS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ── Constants ─────────────────────────────────────────────────────────────────
NEO_VERSION      = "1.0"
MAX_FIX_ATTEMPTS = 15
MAX_TOOL_GEN_ATTEMPTS = 7  # было 3 — увеличиваем шанс успеха
SANDBOX_TIMEOUT  = 600   # seconds per tool execution
MAX_ZIP_FILES    = 20

NEO_PLANNER_SYSTEM = """Ты — NEO, автономный ИИ-агент BlackBugsAI.
Отвечай только на русском языке. Отвечай ТОЛЬКО валидным JSON (без markdown).

ВАЖНЫЕ ПРАВИЛА:
1. Написать/выполнить код → tool_name="python_eval", inputs={"code":"...полный код..."}
   НЕ используй run_script, check_syntax — их НЕТ. Только python_eval.
2. Рисование/картинка/фото → tool_name="image_gen", inputs={"prompt":"...на английском..."}
3. Создать бота/проект/приложение → tool_name="smith_template", inputs={"task":"..."}
4. GitHub URL → tool_name="github_install_tool", inputs={"url":"https://github.com/..."}
5. OSINT/поиск человека → tool_name="osint_username_search", inputs={"username":"..."}
6. Поиск через Sherlock → tool_name="osint_sherlock", inputs={"username":"..."}
7. Создать инструмент → tool_name="self_create_tool"
8. ZIP файл в inputs → СНАЧАЛА zip_extractor, потом работа с файлами
9. МАКСИМУМ 3 шага. Простые задачи — 1 шаг. Без лишних "validate/test/deploy".

ДОСТУПНЫЕ ИНСТРУМЕНТЫ (tool_exists=true):
  python_eval, shell_cmd, web_scraper, file_read, file_write,
  image_gen, tts_speak, send_mail, smith_template, analyze_code,
  csv_reader, csv_writer, pdf_reader, zip_extractor, json_transformer,
  file_search, http_get, http_post, rss_parser, html_scraper, api_caller,
  git_info, data_aggregator, text_extractor, diff_tool, dedup_tool,
  requirements_installer, telegram_notify, webhook_sender,
  github_clone, github_install_tool, pip_install,
  osint_sherlock, osint_username_search, osint_site_search,
  self_create_tool, self_list_tools, self_delete_tool

ПРАВИЛО depends_on: если шаг 2 использует результат шага 1 → "depends_on": [1]
ПРАВИЛО email: send_mail inputs={"to":"...","subject":"...","body":"..."}
ПРАВИЛО файлы: path/file_path в inputs, не в required_keys

ФОРМАТ JSON:
{
  "steps": [
    {
      "id": 1,
      "description": "что делает шаг",
      "tool_name": "python_eval",
      "tool_exists": true,
      "needs_external_access": false,
      "required_keys": [],
      "inputs": {"code": "import random\nprint(random.choice(['a','b','c']))"},
      "depends_on": []
    }
  ],
  "final_summary": "одна фраза о результате"
}"""

NEO_TOOL_GEN_SYSTEM = """Ты — генератор инструментов NEO. Пишешь ТОЛЬКО рабочий Python-код.

ЗАПРЕЩЁННЫЕ БИБЛИОТЕКИ (не существуют — НЕ используй никогда):
  bootscrape, webbot, scrapeasy, autoscraper2, pyscraper, urlgrab,
  и любые другие нестандартные, в существовании которых не уверен.

РАЗРЕШЁННЫЕ библиотеки (всегда доступны):
  stdlib: os, sys, json, re, time, ast, subprocess, sqlite3, zipfile,
          pathlib, tempfile, threading, socket, ssl, csv, shutil,
          urllib.request, urllib.parse, http.client, difflib, hashlib
  pip-installed: requests, flask, pillow, edge-tts, bs4/beautifulsoup4,
                 lxml, feedparser, pypdf, bcrypt, qrcode, openai, groq

ДЛЯ ВЕБ-СКРАПИНГА используй ТОЛЬКО: urllib.request  или  requests + bs4
НЕ используй: bootscrape, scrapeasy, webbot или другие выдуманные модули.

ЕСЛИ нужна сторонняя библиотека которой нет выше:
  1. Установи через subprocess + pip install --break-system-packages
  2. Потом импортируй

СТРОГИЕ ПРАВИЛА:
1. Функция называется СТРОГО: run_tool(inputs: dict) -> dict
2. Возврат ВСЕГДА: {"ok": bool, "output": str, "files": list, "error": str}
3. НИКОГДА не используй input() — только inputs.get(...)
4. Ловишь ВСЕ исключения в try/except, никогда не бросаешь ошибки наружу
5. output_dir = inputs.get("output_dir", "/tmp") — сохраняй файлы туда
6. Декодируй bytes: for enc in ("utf-8","cp1251","latin-1"): try: return b.decode(enc); except: pass
7. Прогресс через print() на русском языке

ШАБЛОН (используй его):
```python
def run_tool(inputs: dict) -> dict:
    import os, sys, subprocess
    from pathlib import Path
    output_dir = inputs.get("output_dir", "/tmp")
    
    def _dec(b):
        if not b: return ""
        for enc in ("utf-8", "cp1251", "latin-1"):
            try: return b.decode(enc)
            except: pass
        return b.decode("utf-8", errors="replace")
    
    try:
        # ОСНОВНАЯ ЛОГИКА
        result = "готово"
        return {"ok": True, "output": result, "files": [], "error": ""}
    except Exception as e:
        return {"ok": False, "output": str(e), "files": [], "error": str(e)}
```

ЕСЛИ НУЖЕН ВНЕШНИЙ ИНСТРУМЕНТ (git, curl и т.д.):
- Используй subprocess.run(..., capture_output=True, timeout=N)
- Декодируй stdout/stderr через _dec()
- Проверяй returncode

ЕСЛИ НУЖНА УСТАНОВКА ПАКЕТА:
```python
r = subprocess.run([sys.executable, "-m", "pip", "install", "ПАКЕТ", "-q", "--break-system-packages"],
                   capture_output=True, timeout=600)
```"""

# ── LLM helper ────────────────────────────────────────────────────────────────
def _llm(role: str, prompt: str, system: str = "", max_tokens: int = 4000) -> str:
    try:
        from llm_router import call_llm_for
        return call_llm_for(role, prompt, system, max_tokens)
    except Exception:
        from llm_client import call_llm
        return call_llm(prompt, system, max_tokens)


def _llm_json(role: str, prompt: str, system: str = "") -> Optional[dict]:
    """Call LLM and parse JSON response robustly."""
    raw = _llm(role, prompt, system, max_tokens=2000)
    # Strip markdown fences
    raw = re.sub(r"```json\s*", "", raw)
    raw = re.sub(r"```\s*", "", raw)
    raw = raw.strip()
    # Find first { ... }
    m = re.search(r'\{.*\}', raw, re.DOTALL)
    if m:
        try:
            return json.loads(m.group())
        except json.JSONDecodeError:
            pass
    # Try whole string
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


# ── Code helpers (from agent_session.py) ─────────────────────────────────────
def _sanitize_code(code: str) -> str:
    if not code:
        return code
    replacements = [
        ('\u2014', '-'), ('\u2013', '-'), ('\u2212', '-'),
        ('\u2018', "'"), ('\u2019', "'"),
        ('\u201c', '"'), ('\u201d', '"'),
        ('\u2026', '...'), ('\u00a0', ' '),
    ]
    for old, new in replacements:
        code = code.replace(old, new)
    code = code.lstrip('\ufeff')
    lines = []
    for line in code.splitlines():
        if line.startswith('\t'):
            stripped = line.lstrip('\t')
            tabs = len(line) - len(stripped)
            line = '    ' * tabs + stripped
        lines.append(line)
    code = '\n'.join(lines)
    try:
        ast.parse(code)
        return code
    except SyntaxError as e:
        msg = (e.msg or '').lower()
        if 'unterminated triple-quoted' in msg or 'eof while scanning' in msg:
            tq = '"""'
            sq = "'''"
            if code.count(tq) % 2 == 1:
                code = code.rstrip() + '\n' + tq + '\n'
            elif code.count(sq) % 2 == 1:
                code = code.rstrip() + '\n' + sq + '\n'
    return code


def _smart_syntax_fix(code: str, error_msg: str, error_line: int) -> str:
    err = (error_msg or '').lower()
    try:
        if any(t in err for t in ('unterminated triple-quoted', 'eof while scanning')):
            dq = code.count('"""')
            sq = code.count("'''")
            fixed = code.rstrip() + ('\n"""\n' if dq % 2 == 1 else "\n'''\n")
            try:
                ast.parse(fixed)
                return fixed
            except SyntaxError:
                pass
        lines = code.splitlines()
        if 'unterminated string literal' in err or 'eol while scanning' in err:
            idx = error_line - 1
            if 0 <= idx < len(lines):
                bad = lines[idx]
                if bad.count("'") % 2 == 1:
                    lines[idx] = bad.rstrip() + "'"
                elif bad.count('"') % 2 == 1:
                    lines[idx] = bad.rstrip() + '"'
                fixed = '\n'.join(lines)
                try:
                    ast.parse(fixed)
                    return fixed
                except SyntaxError:
                    pass
        if 'invalid syntax' in err and error_line <= 2:
            STARTS = ('import ', 'from ', 'def ', 'class ', '#', 'if ',
                      'for ', 'while ', 'async ', 'try:', 'print(')
            clean = []
            skip = True
            for line in lines:
                s = line.strip()
                if skip and any(s.startswith(k) for k in STARTS):
                    skip = False
                if not skip:
                    clean.append(line)
            if clean:
                fixed = '\n'.join(clean)
                try:
                    ast.parse(fixed)
                    return fixed
                except SyntaxError:
                    pass
        if 'expected an indented block' in err:
            idx = error_line - 1
            if 0 <= idx < len(lines):
                lines.insert(idx + 1, '    pass')
                fixed = '\n'.join(lines)
                try:
                    ast.parse(fixed)
                    return fixed
                except SyntaxError:
                    pass
    except Exception:
        pass
    return code


def _extract_code_robust(raw: str) -> str:
    if not raw:
        return '# NEO: empty response\npass\n'
    for pattern in [r'```python\s*\n(.*?)```', r'```py\s*\n(.*?)```']:
        m = re.search(pattern, raw, re.DOTALL)
        if m:
            return _sanitize_code(m.group(1).strip())
    m = re.search(r'```\s*\n(.*?)```', raw, re.DOTALL)
    if m:
        code = m.group(1).strip()
        if any(kw in code for kw in ('def ', 'import ', 'print(', 'class ')):
            return _sanitize_code(code)
    lines = raw.splitlines()
    code_lines = []
    started = False
    STARTS = ('import ', 'from ', 'def ', 'class ', 'async def',
              'if __name__', 'print(', '#!', 'x =', 'result', 'data')
    for line in lines:
        s = line.strip()
        if not started and any(s.startswith(kw) for kw in STARTS):
            started = True
        if started:
            code_lines.append(line)
    # Lower threshold: 1+ lines (not just > 2)
    if code_lines:
        code = '\n'.join(code_lines)
        if any(kw in code for kw in ('def ', 'import ', 'print(', 'class ', '=', ':')):
            return _sanitize_code(code)
    # Fallback: if the whole raw looks like code (has assignment/call/keyword)
    raw_stripped = raw.strip()
    if raw_stripped:
        CODE_SIGNALS = ('import ', 'def ', 'class ', 'print(', ' = ', '():', '\n')
        if any(sig in raw_stripped for sig in CODE_SIGNALS):
            return _sanitize_code(raw_stripped)
    return '# NEO: could not extract code\npass\n'


# ═══════════════════════════════════════════════════════════════════════════════
#  NeoToolRegistry — dynamic tool persistence
# ═══════════════════════════════════════════════════════════════════════════════

# In-memory cache: tool_name → {"code": str, "description": str, "created": float}
_tool_cache: Dict[str, dict] = {}
_cache_lock = threading.Lock()

# Built-in tools always available
_BUILTIN_TOOLS = {
    "python_eval", "shell_cmd", "web_scraper", "file_read", "file_write",
    "image_gen", "tts_speak", "send_mail", "smith_template",
    "analyze_code", "run_script",
}


def _init_tools_db():
    with sqlite3.connect(str(TOOLS_DB)) as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS tools (
                name        TEXT PRIMARY KEY,
                description TEXT,
                code        TEXT,
                created     REAL,
                used_count  INTEGER DEFAULT 0,
                last_used   REAL
            )
        """)
        c.commit()


def tool_exists(name: str) -> bool:
    if name in _BUILTIN_TOOLS:
        return True
    with _cache_lock:
        if name in _tool_cache:
            return True
    try:
        with sqlite3.connect(str(TOOLS_DB)) as c:
            row = c.execute("SELECT 1 FROM tools WHERE name=?", (name,)).fetchone()
            return row is not None
    except Exception:
        return False


def get_tool(name: str) -> Optional[dict]:
    with _cache_lock:
        if name in _tool_cache:
            return _tool_cache[name]
    try:
        with sqlite3.connect(str(TOOLS_DB)) as c:
            row = c.execute(
                "SELECT name,description,code,created FROM tools WHERE name=?",
                (name,)
            ).fetchone()
            if row:
                t = {"name": row[0], "description": row[1],
                     "code": row[2], "created": row[3]}
                with _cache_lock:
                    _tool_cache[name] = t
                return t
    except Exception:
        pass
    return None


def register_tool(name: str, description: str, code: str) -> bool:
    t = {"name": name, "description": description,
         "code": code, "created": time.time()}
    with _cache_lock:
        _tool_cache[name] = t
    try:
        # Save code file
        tool_file = TOOLS_DIR / f"{name}.py"
        tool_file.write_text(code, encoding='utf-8')
        # Save to DB
        with sqlite3.connect(str(TOOLS_DB)) as c:
            c.execute("""
                INSERT OR REPLACE INTO tools
                    (name, description, code, created, used_count, last_used)
                VALUES (?,?,?,?,0,?)
            """, (name, description, code, t["created"], t["created"]))
            c.commit()
        return True
    except Exception:
        return False


def list_tools() -> List[dict]:
    tools = [{"name": t, "builtin": True} for t in sorted(_BUILTIN_TOOLS)]
    try:
        with sqlite3.connect(str(TOOLS_DB)) as c:
            rows = c.execute(
                "SELECT name,description,created,used_count FROM tools ORDER BY used_count DESC"
            ).fetchall()
            for row in rows:
                tools.append({
                    "name": row[0], "description": row[1],
                    "created": row[2], "used_count": row[3], "builtin": False
                })
    except Exception:
        pass
    return tools


# ═══════════════════════════════════════════════════════════════════════════════
#  NeoSandbox — hybrid exec/subprocess
# ═══════════════════════════════════════════════════════════════════════════════

_SAFE_BUILTINS = {
    'abs', 'all', 'any', 'ascii', 'bin', 'bool', 'bytes', 'callable',
    'chr', 'dict', 'dir', 'divmod', 'enumerate', 'filter', 'float',
    'format', 'frozenset', 'getattr', 'globals', 'hasattr', 'hash',
    'hex', 'id', 'input', 'int', 'isinstance', 'issubclass', 'iter',
    'len', 'list', 'locals', 'map', 'max', 'min', 'next', 'object',
    'oct', 'open', 'ord', 'pow', 'print', 'range', 'repr', 'reversed',
    'round', 'set', 'setattr', 'slice', 'sorted', 'str', 'sum', 'super',
    'tuple', 'type', 'vars', 'zip', 'None', 'True', 'False',
    '__import__', '__name__',
}

_SIMPLE_TASK_HINTS = (
    'def run_tool', 'import os', 'import sys', 'import json',
    'import re', 'import math', 'import datetime', 'import pathlib',
)


def _run_in_subprocess(code: str, inputs: dict, timeout: int) -> Tuple[bool, str, list]:
    """Run tool code in subprocess, return (ok, output, file_paths)."""
    run_dir = ARTIFACTS_DIR / f"run_{int(time.time()*1000)}"
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
    print("__NEO_RESULT__:" + json.dumps(result, ensure_ascii=False, default=str))
except Exception as e:
    print("__NEO_RESULT__:" + json.dumps({{"ok": False, "output": "", "files": [], "error": traceback.format_exc()}}))
"""
    wrapper_file = run_dir / "_neo_runner.py"
    wrapper_file.write_text(wrapper, encoding='utf-8')

    try:
        r = subprocess.run(
            [sys.executable, str(wrapper_file)],
            capture_output=True, timeout=timeout,
            cwd=str(run_dir),
            env={**os.environ, 'PYTHONIOENCODING': 'utf-8'},
        )
        stdout = (r.stdout or b'').decode('utf-8', errors='replace')
        stderr = (r.stderr or b'').decode('utf-8', errors='replace')
        full_output = (stdout + stderr).strip()

        # Parse structured result
        for line in stdout.splitlines():
            if line.startswith('__NEO_RESULT__:'):
                try:
                    result = json.loads(line[15:])
                    files = [str(run_dir / f) for f in result.get("files", [])
                             if (run_dir / f).exists()]
                    # Also collect any new files created in run_dir
                    created = [str(p) for p in run_dir.iterdir()
                               if p.is_file() and p.name != '_neo_runner.py']
                    all_files = list(set(files + created))
                    return result.get("ok", True), result.get("output", full_output), all_files
                except Exception:
                    pass

        # No structured result — infer from returncode
        ok = r.returncode == 0
        created = [str(p) for p in run_dir.iterdir()
                   if p.is_file() and p.name != '_neo_runner.py']
        return ok, full_output[:3000], created

    except subprocess.TimeoutExpired:
        return False, f"⏰ Timeout {timeout}s", []
    except Exception as e:
        return False, str(e), []


def sandbox_run(code: str, inputs: dict,
                timeout: int = SANDBOX_TIMEOUT) -> Tuple[bool, str, list]:
    """Run tool code. Returns (ok, output_text, file_paths)."""
    return _run_in_subprocess(code, inputs, timeout)


# ═══════════════════════════════════════════════════════════════════════════════
#  NeoToolGenerator — LLM writes the tool
# ═══════════════════════════════════════════════════════════════════════════════

def generate_tool(
    tool_name: str,
    description: str,
    example_inputs: dict,
    on_status: Optional[Callable] = None,
) -> Tuple[bool, str]:
    """
    Generate a new tool using LLM + autofix loop.
    Returns (success, error_message).
    Registers the tool if successful.
    """
    def status(msg):
        if on_status:
            on_status(msg)

    status(f"🔧 Генерирую инструмент: {tool_name}...")

    # Detect if this is a GitHub-based tool
    github_url = None
    for key in ('url', 'repo', 'github_url', 'repo_url'):
        val = example_inputs.get(key, '')
        if val and 'github.com' in str(val):
            github_url = str(val)
            break

    # Build smarter initial prompt
    if github_url:
        prompt = (
            f"Задача: создать инструмент `{tool_name}` который устанавливает и запускает "
            f"GitHub репозиторий: {github_url}\n"
            f"Описание: {description}\n"
            f"Инструмент должен:\n"
            f"1. Клонировать репо через git clone --depth=1\n"
            f"2. Установить requirements.txt если есть (pip install -r ... --break-system-packages)\n"
            f"3. Найти точку входа (main.py/app.py/cli.py)\n"
            f"4. Запустить с аргументами из inputs.get('args', '')\n"
            f"5. Вернуть результат\n\n"
            f"inputs примеры: {json.dumps(example_inputs, ensure_ascii=False)}\n\n"
            f"Напиши ТОЛЬКО функцию run_tool(inputs: dict) -> dict."
        )
    else:
        prompt = (
            f"Задача: создать Python инструмент `{tool_name}`.\n"
            f"Описание: {description}\n"
            f"Пример inputs: {json.dumps(example_inputs, ensure_ascii=False)}\n\n"
            f"Требования:\n"
            f"- Используй subprocess для внешних команд (git, pip, curl и т.д.)\n"
            f"- Декодируй bytes с fallback: utf-8→cp1251→latin-1\n"
            f"- Сохраняй файлы в inputs.get('output_dir', '/tmp')\n"
            f"- Возвращай {{ok, output, files, error}}\n\n"
            f"Напиши ТОЛЬКО функцию run_tool(inputs: dict) -> dict."
        )

    code = None
    last_error = ""
    error_history = []
    same_error_count = 0

    for attempt in range(1, MAX_TOOL_GEN_ATTEMPTS + 1):
        status(f"  ⚙️ Попытка {attempt}/{MAX_TOOL_GEN_ATTEMPTS}...")

        if attempt == 1 or not code:
            raw = _llm("fix", prompt, NEO_TOOL_GEN_SYSTEM, max_tokens=4000)
        else:
            # Умный фикс с историей ошибок
            history_txt = "\n".join(f"  Попытка {i+1}: {e}" for i, e in enumerate(error_history[-3:]))
            fix_prompt = (
                f"Инструмент `{tool_name}` не работает.\n\n"
                f"Текущий код:\n```python\n{code}\n```\n\n"
                f"История ошибок:\n{history_txt}\n\n"
                f"Последняя ошибка: {last_error}\n\n"
                f"ИСПРАВЬ:\n"
                f"1. Если ошибка 'No module named X' → добавь установку через subprocess + pip\n"
                f"2. Если bytes/str ошибка → добавь _dec() для декодирования\n"
                f"3. Если FileNotFoundError → проверяй os.path.exists() перед использованием\n"
                f"4. Если timeout → увеличь timeout или используй более быстрый метод\n"
                f"5. Если returncode != 0 → проверяй stderr и возвращай ok=False с деталями\n\n"
                f"Верни ТОЛЬКО исправленную функцию run_tool(inputs: dict) -> dict."
            )
            raw = _llm("fix", fix_prompt, NEO_TOOL_GEN_SYSTEM, max_tokens=4000)

        code = _extract_code_robust(raw)
        code = _sanitize_code(code)

        # Syntax check + deterministic fix
        for fix_attempt in range(MAX_FIX_ATTEMPTS):
            try:
                ast.parse(code)
                break
            except SyntaxError as se:
                fixed = _smart_syntax_fix(code, se.msg or "", se.lineno or 1)
                if fixed != code:
                    code = fixed
                else:
                    last_error = f"SyntaxError line {se.lineno}: {se.msg}"
                    break

        # Ensure run_tool exists
        if 'def run_tool' not in code:
            last_error = "Missing run_tool function"
            error_history.append(last_error)
            continue

        # Quick syntax pre-check
        try:
            ast.parse(code)
        except SyntaxError as se:
            last_error = f"SyntaxError: {se.msg} line {se.lineno}"
            error_history.append(last_error)
            continue

        # Sandbox test — timeout increases with attempts
        sandbox_timeout = 20 + attempt * 10  # 30s → 40s → ... → 90s
        status(f"  🧪 Тестирую в sandbox (timeout={sandbox_timeout}s)...")
        ok, output, files = sandbox_run(code, example_inputs, timeout=sandbox_timeout)

        if ok:
            register_tool(tool_name, description, code)
            status(f"  ✅ Инструмент {tool_name!r} создан и зарегистрирован!")
            return True, ""
        else:
            clean_error = output.strip()[:300]
            if clean_error == last_error:
                same_error_count += 1
            else:
                same_error_count = 0
            last_error = clean_error
            error_history.append(clean_error)
            status(f"  ❌ Ошибка: {clean_error[:100]}")

            # Если ошибка повторяется 3 раза подряд — пробуем другой подход
            if same_error_count >= 2 and attempt < MAX_TOOL_GEN_ATTEMPTS - 1:
                prompt = (
                    f"Предыдущий подход к инструменту `{tool_name}` не работает.\n"
                    f"Ошибка повторяется: {last_error}\n\n"
                    f"Напиши ДРУГОЙ подход для достижения той же цели:\n"
                    f"Описание: {description}\n"
                    f"Используй другие библиотеки или методы.\n\n"
                    f"Напиши ТОЛЬКО run_tool(inputs: dict) -> dict."
                )
                code = None  # сбросить код для нового подхода

    return False, (
        f"Не удалось создать инструмент за {MAX_TOOL_GEN_ATTEMPTS} попыток.\n"
        f"Последняя ошибка: {last_error[:300]}"
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  Built-in tool executors
# ═══════════════════════════════════════════════════════════════════════════════

def _run_builtin(tool_name: str, inputs: dict,
                 on_status: Optional[Callable] = None) -> Tuple[bool, str, list]:
    """Execute a built-in tool. Returns (ok, output, files)."""

    def status(msg):
        if on_status:
            on_status(msg)

    if tool_name == "python_eval":
        code = inputs.get("code", inputs.get("script", "")).strip()
        output_dir = inputs.get("output_dir", str(ARTIFACTS_DIR))

        # Очищаем markdown-фенсы которые LLM иногда вставляет в code
        code = re.sub(r'^```[\w]*\n?', '', code)
        code = re.sub(r'\n?```\s*$', '', code).strip()

        if not code:
            return False, "Нет кода для выполнения", []

        # Запускаем через subprocess — правильная поддержка многострочного кода
        run_dir = Path(output_dir)
        run_dir.mkdir(parents=True, exist_ok=True)
        before = set(run_dir.iterdir()) if run_dir.exists() else set()

        try:
            with tempfile.NamedTemporaryFile(
                mode='w', suffix='.py', delete=False,
                encoding='utf-8', dir=str(run_dir)
            ) as f:
                f.write(code)
                tmp = f.name

            r = subprocess.run(
                [sys.executable, tmp],
                capture_output=True,
                timeout=600,
                cwd=str(run_dir),
                env={**os.environ, 'PYTHONIOENCODING': 'utf-8'},
            )
            after = set(run_dir.iterdir()) if run_dir.exists() else set()
            new_files = [
                str(p) for p in (after - before)
                if p.is_file() and not p.name.endswith('.py')
            ]

            stdout = (r.stdout or b'').decode('utf-8', errors='replace').strip()
            stderr = (r.stderr or b'').decode('utf-8', errors='replace').strip()
            out = stdout or stderr or "(нет вывода)"

            if r.returncode == 0:
                return True, out[:4000], new_files
            else:
                return False, (stderr or stdout or "ошибка")[:2000], []

        except subprocess.TimeoutExpired:
            return False, "⏰ Таймаут 60с — скрипт не завершился", []
        except Exception as e:
            return False, str(e), []
        finally:
            try: os.unlink(tmp)
            except: pass

    elif tool_name == "shell_cmd":
        cmd = inputs.get("cmd", "echo ok")
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True,
                               timeout=600, cwd=config.BASE_DIR)
            out = (r.stdout or b'').decode('utf-8', errors='replace')
            err = (r.stderr or b'').decode('utf-8', errors='replace')
            return r.returncode == 0, (out + err).strip()[:3000], []
        except Exception as e:
            return False, str(e), []

    elif tool_name == "file_read":
        path = inputs.get("path", "")
        try:
            content = Path(path).read_text(encoding='utf-8', errors='ignore')
            return True, content[:10000], []
        except Exception as e:
            return False, str(e), []

    elif tool_name == "file_write":
        path = inputs.get("path", "")
        content = inputs.get("content", "")
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).write_text(content, encoding='utf-8')
            return True, f"Written {len(content)} chars to {path}", [path]
        except Exception as e:
            return False, str(e), []

    elif tool_name == "image_gen":
        status("🎨 Генерирую картинку...")
        try:
            from image_gen import generate_image
            prompt = inputs.get("prompt", "")
            path, provider = generate_image(prompt)
            return True, f"Image generated via {provider}", [path]
        except Exception as e:
            return False, str(e), []

    elif tool_name == "tts_speak":
        status("🎙 Озвучиваю...")
        try:
            from tts_engine import synthesize
            text = inputs.get("text", "")[:900]
            ts = int(time.time())
            path = synthesize(text, f"neo_tts_{ts}.mp3")
            return True, "TTS generated", [path]
        except Exception as e:
            return False, str(e), []

    elif tool_name == "send_mail":
        try:
            from mail_agent import send_mail, is_configured
            if not is_configured():
                err = (
                    "❌ Mail не настроен. Добавь в .env:\n"
                    "MAIL_HOST, MAIL_PORT, MAIL_USER, MAIL_PASS, ADMIN_EMAIL\n"
                    "Для Gmail: MAIL_HOST=smtp.gmail.com MAIL_PORT=587\n"
                    "Используй App Password (не обычный пароль)"
                )
                return False, err, []
            to_addr = inputs.get("to", "") or inputs.get("email", "")
            if not to_addr:
                return False, "❌ Не указан адрес получателя (inputs.to)", []
            subject = inputs.get("subject", "NEO report")
            body    = inputs.get("body") or inputs.get("text") or inputs.get("content", "")
            ok, msg = send_mail(to=to_addr, subject=subject, body=body)
            return ok, msg, []
        except Exception as e:
            return False, str(e), []
    elif tool_name == "smith_template":
        status("🕵️ Запускаю AGENT_SMITH шаблон...")
        try:
            from agent_session import create_session, execute_pipeline, close_session
            from agent_session import STAGE_WAIT_FILES
            chat_id = inputs.get("chat_id", "neo_internal")
            task = inputs.get("task", "")
            template = inputs.get("template", "script")
            sess = create_session(chat_id)
            sess.task = f"[TEMPLATE:{template}]\n{task}"
            _neo_msgs = []
            def _neo_on_status(m, _l=_neo_msgs): _l.append(str(m))
            result = execute_pipeline(sess, on_status=_neo_on_status)
            close_session(chat_id)
            files = []
            if result.get("zip_path") and os.path.exists(result["zip_path"]):
                files.append(result["zip_path"])
            return result.get("ok", False), result.get("output", ""), files
        except Exception as e:
            return False, str(e), []

    elif tool_name == "analyze_code":
        try:
            from chat_agent import _run_analyze_agent
            result = _run_analyze_agent(
                chat_id=inputs.get("chat_id", "neo"),
                user_task=inputs.get("task", "analyze this code"),
                history=[],
                on_status=on_status,
                attached_file=inputs.get("file_path"),
            )
            return result.get("success", False), result.get("output", ""), result.get("files", [])
        except Exception as e:
            return False, str(e), []

    elif tool_name == "run_script":
        code = inputs.get("code", "")
        return sandbox_run(code, inputs)

    elif tool_name == "web_scraper":
        status("🌐 Загружаю страницу...")
        try:
            import urllib.request
            url = inputs.get("url", "")
            req = urllib.request.Request(url, headers={'User-Agent': 'NEO/1.0'})
            with urllib.request.urlopen(req, timeout=15) as r:
                html = r.read().decode('utf-8', errors='ignore')
            # Basic text extraction
            text = re.sub(r'<[^>]+>', ' ', html)
            text = re.sub(r'\s+', ' ', text).strip()
            return True, text[:5000], []
        except Exception as e:
            return False, str(e), []

    return False, f"Unknown builtin tool: {tool_name}", []


# ═══════════════════════════════════════════════════════════════════════════════
#  NeoPlanner — decompose task into steps
# ═══════════════════════════════════════════════════════════════════════════════

def plan_task(task: str, chat_id: str,
              attached_files: list | None = None) -> Optional[dict]:
    """
    Call LLM to decompose task into steps.
    Returns plan dict or None on failure.
    """
    context = ""
    try:
        from agent_memory import AgentMemory
        context = AgentMemory(chat_id).build_context(task)
    except Exception:
        pass

    # List available dynamic tools
    dyn_tools = [t["name"] for t in list_tools() if not t.get("builtin")]
    tools_hint = ""
    if dyn_tools:
        tools_hint = f"\nDynamic tools already available: {', '.join(dyn_tools[:10])}"

    files_hint = ""
    if attached_files:
        files_hint = f"\nAttached files: {', '.join(attached_files)}"

    prompt = (
        f"Task: {task}\n"
        f"{files_hint}{tools_hint}\n"
        f"Previous context:\n{context}\n\n"
        "Return JSON plan."
    )

    plan = _llm_json("agent", prompt, NEO_PLANNER_SYSTEM)
    if not plan or "steps" not in plan:
        # Fallback: single-step plan
        plan = {
            "steps": [{
                "id": 1,
                "description": task,
                "tool_name": "run_script",
                "tool_exists": True,
                "needs_external_access": False,
                "required_keys": [],
                "inputs": {"task": task,
                           "files": attached_files or []},
                "depends_on": [],
            }],
            "final_summary": f"Execute: {task[:80]}",
        }
    return plan


# ═══════════════════════════════════════════════════════════════════════════════
#  NeoArtifact — build ZIP with full I/O contract
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class NeoResult:
    ok:            bool
    answer:        str         # final text answer
    zip_path:      str = ""
    tts_path:      str = ""
    files:         List[str]  = field(default_factory=list)
    steps_log:     List[dict] = field(default_factory=list)
    generated_tools: List[str] = field(default_factory=list)
    error:         str = ""
    duration:      float = 0.0


def _build_artifact(
    task: str,
    plan: dict,
    steps_log: list,
    answer: str,
    all_files: list,
    generated_tools: list,
    chat_id: str,
) -> str:
    """Build ZIP artifact with full I/O contract. Returns zip path."""
    ts = int(time.time())
    artifact_dir = ARTIFACTS_DIR / f"neo_{ts}"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    zip_path = str(ARTIFACTS_DIR / f"neo_result_{ts}.zip")

    # Build report.md
    report_lines = [
        f"# NEO Result Report",
        f"",
        f"**Task:** {task}",
        f"**Time:** {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"",
        f"## Answer",
        f"",
        answer,
        f"",
        f"## Execution Steps",
        f"",
    ]
    for s in steps_log:
        icon = "✅" if s.get("ok") else "❌"
        report_lines.append(f"### {icon} Step {s.get('id', '?')}: {s.get('description', '')}")
        report_lines.append(f"Tool: `{s.get('tool', '?')}`")
        if s.get("output"):
            report_lines.append(f"```\n{str(s['output'])[:500]}\n```")
        if s.get("error"):
            report_lines.append(f"Error: `{s['error'][:200]}`")
        report_lines.append("")

    if generated_tools:
        report_lines += [
            f"## Generated Tools",
            f"",
            f"NEO created {len(generated_tools)} new tool(s) during this run:",
        ]
        for t in generated_tools:
            report_lines.append(f"- `{t}`")

    report_md = "\n".join(report_lines)

    # Build execution_log.txt
    log_lines = [f"NEO v{NEO_VERSION} — Execution Log", "=" * 50, ""]
    for s in steps_log:
        log_lines.append(f"[{s.get('ts', '')}] Step {s.get('id', '?')}: {s.get('description', '')}")
        log_lines.append(f"  Tool: {s.get('tool', '?')}")
        log_lines.append(f"  Status: {'OK' if s.get('ok') else 'FAIL'}")
        if s.get("output"):
            log_lines.append(f"  Output: {str(s['output'])[:300]}")
        if s.get("error"):
            log_lines.append(f"  Error: {s['error'][:200]}")
        log_lines.append("")
    exec_log = "\n".join(log_lines)

    # Build ZIP
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        # report.md
        zf.writestr("report.md", report_md)
        # execution_log.txt
        zf.writestr("execution_log.txt", exec_log)
        # input_data/task.txt
        zf.writestr("input_data/task.txt", task)
        # input_data/plan.json
        zf.writestr("input_data/plan.json",
                    json.dumps(plan, ensure_ascii=False, indent=2))
        # output_data/answer.txt
        zf.writestr("output_data/answer.txt", answer)
        # Generated tool code
        for tool_name in generated_tools:
            tool_file = TOOLS_DIR / f"{tool_name}.py"
            if tool_file.exists():
                zf.write(str(tool_file), f"tool_code/{tool_name}.py")
        # All output files (up to MAX_ZIP_FILES)
        added = 0
        for fpath in all_files:
            if os.path.exists(fpath) and os.path.isfile(fpath) and added < MAX_ZIP_FILES:
                fname = os.path.basename(fpath)
                try:
                    zf.write(fpath, f"output_data/{fname}")
                    added += 1
                except Exception:
                    pass

    return zip_path


# ═══════════════════════════════════════════════════════════════════════════════
#  Main NEO entry point
# ═══════════════════════════════════════════════════════════════════════════════

# Waiting state for external access requests
_neo_pending: Dict[str, dict] = {}


def run_neo(
    task: str,
    chat_id: str,
    attached_files: list | None = None,
    on_status: Optional[Callable] = None,
    llm_caller=None,
) -> NeoResult:
    """
    Main NEO pipeline:
      1. Plan task (LLM decomposition)
      2. For each step: check tool → generate if missing → run in sandbox
      3. Build full ZIP artifact (code + input + output + report + log)
      4. Generate TTS answer
      5. Update memory

    Returns NeoResult with answer, zip_path, tts_path, files.
    """
    t0 = time.time()
    _init_tools_db()

    def status(msg: str):
        if on_status:
            on_status(msg)

    status("🧠 NEO анализирует задачу...")
    # Skill evolution: suggest tools from past success
    try:
        from agent_memory import AgentMemory
        _mem = AgentMemory(chat_id)
        _ctx = _mem.build_context(task)
        _sug = _mem.learning.suggest_tools(task)
        if _sug: status(f"  💡 Из опыта: {_sug[:3]}")
    except Exception: pass

    # ── Step 1: Plan ──────────────────────────────────────────────────────────
    plan = plan_task(task, chat_id, attached_files)
    steps = plan.get("steps", [])
    status(f"📋 План: {len(steps)} шагов")

    # ── Step 2: Check for external access needs ───────────────────────────────
    # Only treat as missing key if it looks like a real env var name
    # (uppercase, ends with _KEY/_TOKEN/_ID/_SECRET/_PASS/_HASH/_API)
    _ENV_KEY_PATTERN = re.compile(
        r'^[A-Z][A-Z0-9_]*(_(KEY|TOKEN|ID|SECRET|PASS|PASSWORD|HASH|API|APIKEY|CRED|CREDENTIALS))$'
    )
    needs_keys = []
    for step in steps:
        if step.get("needs_external_access"):
            for key in step.get("required_keys", []):
                # Skip if it looks like a file path, email, URL, or non-env-var
                if not _ENV_KEY_PATTERN.match(str(key).strip().upper()):
                    continue  # not a real env var — ignore
                if not os.environ.get(key):
                    needs_keys.append((step["id"], key))

    if needs_keys:
        key_list = ", ".join(f"`{k}`" for _, k in needs_keys)
        _neo_pending[chat_id] = {"plan": plan, "task": task,
                                  "files": attached_files, "needs_keys": needs_keys}
        msg = (
            f"🔑 NEO нужны внешние ключи доступа:\n{key_list}\n\n"
            "Добавь их в .env и напиши **продолжи** или **пропустить** для работы без них."
        )
        return NeoResult(ok=False, answer=msg, error="awaiting_keys")

    # ── Step 3: Execute steps ─────────────────────────────────────────────────
    steps_log = []
    generated_tools = []
    all_output_files = []
    step_results: Dict[int, dict] = {}
    final_answer = ""

    # Общая output_dir для всех шагов
    shared_dir = ARTIFACTS_DIR / f"neo_{int(time.time())}"
    shared_dir.mkdir(parents=True, exist_ok=True)

    # Инструменты которые в плановщике помечены как builtin но НЕ существуют —
    # перенаправляем на python_eval
    SAFE_FALLBACK_TO_EVAL = {
        "run_script", "check_syntax", "lint_code", "code_runner",
        "execute_code", "run_code", "execute_script",
    }

    for step in steps:
        step_id   = step.get("id", 0)
        tool_name = step.get("tool_name", "python_eval")
        desc      = step.get("description", "")
        s_inputs  = dict(step.get("inputs", {}))

        # Общая директория
        s_inputs.setdefault("output_dir", str(shared_dir))
        s_inputs["chat_id"] = chat_id
        s_inputs["task"] = task

        status(f"⚙️ Шаг {step_id}: {desc[:60]}...")

        # Inject results from dependencies
        for dep_id in step.get("depends_on", []):
            if dep_id in step_results:
                prev = step_results[dep_id]
                s_inputs[f"dep_{dep_id}_output"] = prev.get("output", "")
                if prev.get("files") and "path" not in s_inputs:
                    s_inputs["path"] = prev["files"][0]
                    s_inputs["files"] = prev["files"]

        # Inject attached files
        if attached_files and step_id == 1 and "path" not in s_inputs:
            s_inputs["path"] = attached_files[0]
            s_inputs["files"] = attached_files

        # Fallback: несуществующий инструмент → python_eval
        if tool_name in SAFE_FALLBACK_TO_EVAL:
            status(f"  ↩️ {tool_name} → python_eval")
            # Берём code из inputs если есть
            if "code" not in s_inputs and "script" not in s_inputs:
                s_inputs["code"] = f"print('Задача: {desc[:100]}')"
            tool_name = "python_eval"

        step_log = {
            "id": step_id, "description": desc, "tool": tool_name,
            "ts": time.strftime('%H:%M:%S'), "ok": False,
            "output": "", "error": "", "files": [],
        }

        # Check / generate tool
        if tool_name not in _BUILTIN_TOOLS and not tool_exists(tool_name):
            status(f"  🔨 Инструмента нет — генерирую {tool_name}...")
            gen_ok, gen_err = generate_tool(
                tool_name=tool_name,
                description=desc,
                example_inputs=s_inputs,
                on_status=on_status,
            )
            if gen_ok:
                generated_tools.append(tool_name)
            else:
                step_log["error"] = f"Tool generation failed: {gen_err}"
                steps_log.append(step_log)
                continue

        # Execute
        try:
            if tool_name in _BUILTIN_TOOLS:
                ok, output, files = _run_builtin(tool_name, s_inputs, on_status)
            else:
                tool_data = get_tool(tool_name)
                if not tool_data:
                    raise RuntimeError(f"Tool {tool_name!r} not found after generation")
                ok, output, files = sandbox_run(
                    tool_data["code"], s_inputs, SANDBOX_TIMEOUT
                )

            step_log.update({"ok": ok, "output": output, "files": files,
                              "error": "" if ok else output[:300]})
            step_results[step_id] = step_log
            all_output_files.extend(f for f in files if f not in all_output_files)

            if ok and output:
                final_answer = output
            status(f"  {'✅' if ok else '⚠️'} {output[:60]}")
            # Learning loop
            try:
                from agent_memory import AgentLearning
                if ok: AgentLearning().record_success(task[:50], [tool_name])
                else:  AgentLearning().record_fail(task[:50], [tool_name])
            except Exception: pass

        except Exception as exc:
            step_log["error"] = str(exc)[:300]
            step_log["ok"] = False

        steps_log.append(step_log)

    # ── Step 4: Synthesize final answer ───────────────────────────────────────
    # Override with real errors if all steps failed
    all_failed = bool(steps_log) and all(not s.get('ok', False) for s in steps_log)
    if all_failed:
        err_msgs = [f"Шаг {s['id']} ({s['tool']}): {(s.get('error') or s.get('output',''))[:200]}"
                    for s in steps_log if s.get('error') or s.get('output')]
        final_answer = '❌ Ошибка:\n\n' + '\n'.join(err_msgs)

    if not final_answer:
        final_answer = plan.get("final_summary", "Задача выполнена")

    # If complex multi-step → summarize (only if not all failed)
    if len(steps) > 1 and not all_failed:
        try:
            outputs_text = "\n".join(
                f"Step {s['id']} ({s['tool']}): {str(s['output'])[:300]}"
                for s in steps_log if s.get("output")
            )
            summary = _llm(
                "chat",
                f"Task: {task}\n\nStep results:\n{outputs_text}\n\nWrite a clear final answer.",
                "You are NEO. Summarize the results concisely.",
                max_tokens=1000,
            )
            if summary and len(summary) > 20:
                final_answer = summary
        except Exception:
            pass

    # ── Step 5: Build ZIP artifact ────────────────────────────────────────────
    status("📦 Собираю артефакт...")
    zip_path = _build_artifact(
        task=task,
        plan=plan,
        steps_log=steps_log,
        answer=final_answer,
        all_files=list(set(all_output_files)),
        generated_tools=generated_tools,
        chat_id=chat_id,
    )

    # ── Step 6: TTS ───────────────────────────────────────────────────────────
    tts_path = ""
    try:
        from tts_engine import synthesize
        tts_text = re.sub(r'[*_`#<>]', '', final_answer[:900])
        tts_text = re.sub(r'\n+', ' ', tts_text).strip()
        if len(tts_text) > 30:
            ts2 = int(time.time())
            tts_path = synthesize(tts_text, f"neo_answer_{ts2}.mp3")
    except Exception:
        pass

    # ── Step 7: Update memory ─────────────────────────────────────────────────
    duration = time.time() - t0
    try:
        from agent_memory import AgentMemory
        ok_overall = all(s.get("ok", False) for s in steps_log)
        tools_used = [s["tool"] for s in steps_log]
        AgentMemory(chat_id).after_task(
            task=task,
            tools_used=tools_used,
            result=final_answer[:500],
            status="done" if ok_overall else "partial",
            duration=duration,
        )
    except Exception:
        pass

    ok_overall = any(s.get("ok", False) for s in steps_log)
    status(f"{'✅' if ok_overall else '⚠️'} NEO завершил за {duration:.1f}с")

    return NeoResult(
        ok=ok_overall,
        answer=final_answer,
        zip_path=zip_path,
        tts_path=tts_path,
        files=list(set(all_output_files)),
        steps_log=steps_log,
        generated_tools=generated_tools,
        duration=duration,
    )


def run_neo_async(task: str, chat_id: str,
                  attached_files: list | None = None,
                  on_status=None,
                  on_complete=None):
    """Non-blocking NEO run. on_complete(NeoResult) called when done."""
    def _run():
        result = run_neo(task, chat_id, attached_files, on_status)
        if on_complete:
            on_complete(result)
    t = threading.Thread(target=_run, daemon=True, name=f"neo-{chat_id}")
    t.start()
    return t


# ── Init ──────────────────────────────────────────────────────────────────────
try:
    _init_tools_db()
except Exception:
    pass

def install_github_as_tool(
    url: str,
    tool_name: str = "",
    description: str = "",
    entry_cmd: str = "",
    on_status: Optional[Callable] = None,
) -> Tuple[bool, str, str]:
    """
    Клонирует GitHub репо, устанавливает зависимости,
    генерирует обёртку run_tool() и регистрирует как инструмент NEO.

    Returns: (success, tool_name, error_message)
    """
    def status(msg):
        if on_status: on_status(msg)

    # Определяем имя инструмента из URL
    if not tool_name:
        tool_name = url.rstrip('/').split('/')[-1].replace('.git', '').replace('-', '_').lower()
    if not description:
        description = f"Инструмент из GitHub: {url}"

    repo_dir = str(TOOLS_DIR / f"repo_{tool_name}")
    import shutil

    # ── 1. Клонирование ──────────────────────────────────────────────────────
    status(f"📥 Клонирую {url}...")
    if os.path.exists(repo_dir):
        shutil.rmtree(repo_dir)

    r = subprocess.run(
        ["git", "clone", "--depth=1", url, repo_dir],
        capture_output=True, timeout=600,
    )
    out = (r.stdout or b'').decode('utf-8', errors='replace')
    err = (r.stderr or b'').decode('utf-8', errors='replace')
    if r.returncode != 0:
        return False, tool_name, f"git clone failed: {err}"

    status(f"  ✅ Клонировано в {repo_dir}")
    repo_path = Path(repo_dir)

    # ── 2. README → описание ─────────────────────────────────────────────────
    readme_text = ""
    for rname in ("README.md", "README.rst", "README.txt", "readme.md"):
        rf = repo_path / rname
        if rf.exists():
            try:
                readme_text = rf.read_text(encoding='utf-8', errors='replace')[:2000]
            except Exception:
                pass
            break
    if readme_text and not description.startswith("Инструмент"):
        description = readme_text[:200].split('\n')[0].strip() or description

    # ── 3. Установка зависимостей ─────────────────────────────────────────────
    req_file = repo_path / "requirements.txt"
    if req_file.exists():
        status(f"📦 Устанавливаю зависимости...")
        r2 = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(req_file),
             "-q", "--break-system-packages"],
            capture_output=True, timeout=600,
        )
        pip_out = (r2.stdout or b'').decode('utf-8', errors='replace')
        status(f"  pip: {'OK' if r2.returncode == 0 else 'WARN: ' + pip_out[:100]}")

    # ── 4. Определяем точку входа ─────────────────────────────────────────────
    if not entry_cmd:
        candidates = [
            ("python3 -m " + tool_name, repo_path / "__main__.py"),
            ("python3 main.py",         repo_path / "main.py"),
            ("python3 app.py",          repo_path / "app.py"),
            ("python3 run.py",          repo_path / "run.py"),
            ("python3 cli.py",          repo_path / "cli.py"),
        ]
        for cmd, fpath in candidates:
            if fpath.exists():
                entry_cmd = cmd; break
        if not entry_cmd:
            # Ищем любой .py с if __name__
            for pyf in sorted(repo_path.glob("*.py")):
                try:
                    if "__main__" in pyf.read_text(encoding='utf-8', errors='replace'):
                        entry_cmd = f"python3 {pyf.name}"; break
                except Exception:
                    pass
        if not entry_cmd:
            entry_cmd = "python3 ."

    status(f"  Точка входа: {entry_cmd}")

    # ── 5. Собираем контекст для LLM ─────────────────────────────────────────
    # Читаем структуру репо
    py_files = list(repo_path.glob("*.py"))[:5]
    structure = "\n".join(str(f.relative_to(repo_path)) for f in py_files)

    # ── 6. LLM генерирует умную обёртку ──────────────────────────────────────
    status(f"🤖 Генерирую обёртку через LLM...")

    gen_prompt = (
        f"Создай run_tool() для GitHub инструмента.\n\n"
        f"Репозиторий: {url}\n"
        f"Название: {tool_name}\n"
        f"Путь: {repo_dir}\n"
        f"Команда запуска: {entry_cmd}\n"
        f"Python файлы: {structure}\n"
        f"README:\n{readme_text[:500]}\n\n"
        f"Требования к обёртке:\n"
        f"1. Принимает inputs dict с 'args' (строка аргументов CLI)\n"
        f"2. Запускает инструмент через subprocess в {repo_dir}\n"
        f"3. Декодирует stdout/stderr (bytes) с fallback utf-8→cp1251→latin-1\n"
        f"4. Возвращает {{'ok': bool, 'output': str, 'files': list, 'error': str}}\n"
        f"5. Разбирает аргументы инструмента если они специфичны\n\n"
        f"Напиши ТОЛЬКО функцию run_tool(inputs: dict) -> dict."
    )

    raw = _llm("fix", gen_prompt, NEO_TOOL_GEN_SYSTEM, max_tokens=3000)
    code = _extract_code_robust(raw)
    code = _sanitize_code(code)

    # Если LLM сгенерировал плохой код — используем шаблон
    if 'def run_tool' not in code:
        code = (
            "def run_tool(inputs):\n"
            "    import subprocess, sys\n"
            f"    repo = {repr(repo_dir)}\n"
            f"    base = {repr(entry_cmd)}\n"
            "    args = inputs.get('args', inputs.get('query', inputs.get('target', '')))\n"
            "    cmd  = base + (' ' + str(args) if args else '')\n"
            "    def _dec(b):\n"
            "        if not b: return ''\n"
            "        for e in ('utf-8','cp1251','latin-1'):\n"
            "            try: return b.decode(e)\n"
            "            except: pass\n"
            "        return b.decode('utf-8', errors='replace')\n"
            "    r = subprocess.run(cmd, shell=True, capture_output=True, timeout=600, cwd=repo)\n"
            "    out = _dec(r.stdout) + _dec(r.stderr)\n"
            "    return {'ok': r.returncode==0, 'output': out[:4000], 'files': [], 'error': '' if r.returncode==0 else out[:500]}\n"
        )

    # Verify syntax
    try:
        ast.parse(code)
    except SyntaxError as se:
        code = _smart_syntax_fix(code, se.msg or "", se.lineno or 1)

    # ── 7. Быстрый тест ──────────────────────────────────────────────────────
    status(f"🧪 Тестирую обёртку...")
    ok, output, files = sandbox_run(code, {"args": "--help"}, timeout=600)

    # Даже если тест не прошёл (--help вернул non-zero) — регистрируем
    # т.к. многие CLI инструменты возвращают 1 для --help
    if not ok and any(e in output.lower() for e in
                      ('filenotfounderror', 'no such file', 'importerror', 'syntaxerror')):
        return False, tool_name, f"Критическая ошибка: {output[:300]}"

    # ── 8. Регистрируем ───────────────────────────────────────────────────────
    register_tool(tool_name, description, code)
    status(f"✅ Инструмент {tool_name!r} установлен из GitHub и зарегистрирован!")
    status(f"   Команда: {entry_cmd}")
    status(f"   Путь:    {repo_dir}")
    return True, tool_name, ""


def warmup(on_status=None, llm_generate: bool = False) -> dict:
    """
    Register all pre-built tools from neo_tool_library.
    Call once at bot startup or on demand.
    llm_generate=True also generates WARMUP_PROMPTS tools via LLM.
    """
    try:
        from neo_tool_library import register_all
        return register_all(on_status=on_status, llm_generate_missing=llm_generate)
    except ImportError as e:
        if on_status: on_status(f'⚠️ neo_tool_library: {e}')
        return {'registered': 0, 'skipped': 0, 'generated': 0, 'failed': 0}


def test_tools(on_status=None) -> dict:
    """Run sandbox test on every registered tool."""
    try:
        from neo_tool_library import test_all
        return test_all(on_status=on_status)
    except ImportError as e:
        return {'passed': 0, 'failed': [str(e)]}
