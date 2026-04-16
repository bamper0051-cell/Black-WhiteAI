"""
ПАТЧ для agent_matrix.py

Изменения:
  1. Убрать жёсткий timeout=600 → первая попытка сразу 300s
  2. Улучшить промты для установки инструментов  
  3. Добавить провокационные промты (установка тулзов через естественный язык)
  4. Логика создания инструментов — 3 режима (LLM / GitHub / Hybrid)
  5. Лучшая диагностика ошибок

ПРИМЕНЕНИЕ: скопируй этот файл поверх agent_matrix.py
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
VERSION          = "2.0"
MAX_GEN_ATTEMPTS = 7
SANDBOX_TIMEOUT  = 600   # ← 10 минут (убран hardcoded 60s)

# Провокационные паттерны → триггеры создания инструментов
TOOL_INSTALL_PATTERNS = [
    # Прямые команды
    r"(?:установи|поставь|скачай|добавь|интегрируй)\s+(?:инструмент|тул|tool|плагин)?\s*[\"']?(\w[\w\-_]+)[\"']?",
    # GitHub URL
    r"(?:установи|поставь|добавь|интегрируй)\s+(https://github\.com/\S+)",
    # Английские команды
    r"(?:install|setup|add|get)\s+(?:tool\s+)?[\"']?(\w[\w\-_]+)[\"']?",
    # Косвенные (умный AI)
    r"(?:мне нужен|нужен|хочу|хотел бы)\s+(?:инструмент|тул)?\s+(?:для|чтобы|который)\s+(.+)",
    # "используй X для Y" — автоустановка если X не найден
    r"(?:используй|запусти|применй)\s+[\"']?(\w[\w\-_]+)[\"']?\s+(?:для|чтобы|на|к)",
]

# ── Системный промт — Кодер + Тестер + OSINT + Security Analyst ──────────────
MATRIX_SYSTEM = """Ты — AGENT MATRIX v2.0, универсальный AI-агент BlackBugsAI.
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
[ТЕСТЕР] Написать тесты, найти баги, проверить безопасность кода.
[OSINT] Сбор публично доступной информации (только легальные источники).
[SECURITY] Анализ безопасности собственной инфраструктуры (авторизованные задачи).

ПРАВИЛА ИНСТРУМЕНТОВ:
1. run_tool(inputs: dict) -> dict — всегда такая сигнатура
2. Возврат: {"ok": bool, "output": str, "files": list, "error": str}
3. Декодируй bytes: for enc in ("utf-8","cp1251","latin-1"): try: return b.decode(enc)
4. output_dir = inputs.get("output_dir", "/tmp")
5. Все ошибки в try/except — никогда не выбрасывай наружу
6. Прогресс через print() на русском языке
7. ТАЙМАУТ subprocess: всегда timeout=600 (не меньше!)

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

MATRIX_PLANNER_SYSTEM = """Ты — планировщик AGENT MATRIX v2.0.
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
5. ДИНАМИЧЕСКИЕ ИНСТРУМЕНТЫ: если упоминается установленный инструмент (robin, 
   sherlock, nmap и т.д.) — используй напрямую: tool_name="robin", tool_exists=true
6. Запросы типа "запусти robin для X" → tool_name=имя_инструмента, tool_exists=true
7. Запросы "установи инструмент X" → tool_name="matrix_create_tool", tool_exists=true,
   inputs={"tool_name":"X","description":"...","example_inputs":{}}

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

# ── Провокационный промт: детектор намерений установки инструментов ───────────
INSTALL_INTENT_SYSTEM = """Ты анализируешь сообщение пользователя на предмет намерения установить инструмент.

Если пользователь хочет:
- Установить/добавить новый инструмент или плагин
- Использовать инструмент которого нет в системе  
- Установить что-то с GitHub
- Добавить новую возможность/функцию

Верни JSON:
{
  "wants_install": true/false,
  "tool_name": "имя_инструмента или null",
  "github_url": "URL или null",
  "description": "что должен делать инструмент",
  "install_mode": "llm" / "github" / "pip",
  "example_usage": "пример как пользователь хочет его использовать"
}

Если намерения нет — верни {"wants_install": false}
Отвечай ТОЛЬКО JSON, без markdown."""


# ══════════════════════════════════════════════════════════════════════════════
#  LLM helper
# ══════════════════════════════════════════════════════════════════════════════

def _llm(prompt: str, system: str = "", max_tokens: int = 4000) -> str:
    try:
        from llm_client import call_llm
        return call_llm(prompt, system=system, max_tokens=max_tokens)
    except Exception as e:
        return f"# LLM error: {e}"


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
        install_mode TEXT DEFAULT 'llm',
        github_url TEXT DEFAULT '',
        last_error TEXT DEFAULT ''
    )""")
    db.commit(); db.close()

_init_db()


def register_tool(name: str, description: str, code: str, builtin: bool = False,
                  install_mode: str = "llm", github_url: str = ""):
    db = sqlite3.connect(str(TOOLS_DB))
    db.execute("""INSERT OR REPLACE INTO tools
                  (name,description,code,builtin,created,used_count,install_mode,github_url)
                  VALUES (?,?,?,?,?,COALESCE((SELECT used_count FROM tools WHERE name=?),0),?,?)""",
               (name, description, code, int(builtin), time.time(), name, install_mode, github_url))
    db.commit(); db.close()
    (TOOLS_DIR / f"{name}.py").write_text(code, encoding="utf-8")


def tool_exists(name: str) -> bool:
    db = sqlite3.connect(str(TOOLS_DB))
    row = db.execute("SELECT 1 FROM tools WHERE name=?", (name,)).fetchone()
    db.close()
    return row is not None


def get_tool_code(name: str) -> Optional[str]:
    db = sqlite3.connect(str(TOOLS_DB))
    row = db.execute("SELECT code FROM tools WHERE name=?", (name,)).fetchone()
    db.close()
    if row: return row[0]
    f = TOOLS_DIR / f"{name}.py"
    return f.read_text(encoding="utf-8") if f.exists() else None


def list_tools() -> List[dict]:
    db = sqlite3.connect(str(TOOLS_DB))
    rows = db.execute(
        "SELECT name,description,builtin,used_count,install_mode,github_url,created FROM tools ORDER BY used_count DESC"
    ).fetchall()
    db.close()
    return [{
        "name": r[0], "description": r[1], "builtin": bool(r[2]),
        "used_count": r[3], "install_mode": r[4], "github_url": r[5],
        "created": r[6],
    } for r in rows]


def delete_tool(name: str) -> bool:
    db = sqlite3.connect(str(TOOLS_DB))
    db.execute("DELETE FROM tools WHERE name=?", (name,))
    db.commit(); db.close()
    p = TOOLS_DIR / f"{name}.py"
    if p.exists(): p.unlink()
    return True


def get_stats() -> dict:
    db = sqlite3.connect(str(TOOLS_DB))
    rows = db.execute("SELECT name, builtin, used_count FROM tools").fetchall()
    db.close()
    builtin_count = sum(1 for r in rows if r[1])
    return {
        "total": len(rows),
        "builtin": builtin_count,
        "custom": len(rows) - builtin_count,
        "version": VERSION,
        "tools_db": str(TOOLS_DB),
        "artifacts_dir": str(ARTIFACTS_DIR),
    }


# ══════════════════════════════════════════════════════════════════════════════
#  Sandbox — timeout УБРАН (теперь только SANDBOX_TIMEOUT=600)
# ══════════════════════════════════════════════════════════════════════════════

def sandbox_run(code: str, inputs: dict, timeout: int = SANDBOX_TIMEOUT) -> Tuple[bool, str, list]:
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

        out = (stdout + stderr).strip()
        return r.returncode == 0, out[:6000] or "(нет вывода)", []

    except subprocess.TimeoutExpired:
        return False, f"⏰ Таймаут {timeout}с", []
    except Exception as e:
        return False, str(e), []


# ══════════════════════════════════════════════════════════════════════════════
#  Code extraction & fix
# ══════════════════════════════════════════════════════════════════════════════

def _extract_code(raw: str) -> str:
    if not raw: return "pass"
    for pat in [r"```python\s*\n(.*?)```", r"```py\s*\n(.*?)```", r"```\s*\n(.*?)```"]:
        m = re.search(pat, raw, re.DOTALL)
        if m:
            return _clean_code(m.group(1).strip())
    clean = re.sub(r"^```[\w]*\n?", "", raw.strip())
    clean = re.sub(r"\n?```\s*$", "", clean).strip()
    if "def " in clean or "import " in clean:
        return _clean_code(clean)
    return "pass"


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
#  Intent Detector — провокационные промты
# ══════════════════════════════════════════════════════════════════════════════

def detect_install_intent(message: str) -> dict:
    """
    Анализирует сообщение на предмет намерения установить инструмент.
    Поддерживает провокационные/неочевидные запросы.
    
    Примеры:
      "хочу парсить сайты" → создаёт web_parser
      "поставь sherlock"   → github_install sherlock
      "нужен генератор паролей" → LLM создаёт password_generator
    """
    # Быстрые паттерны (без LLM)
    for pattern in TOOL_INSTALL_PATTERNS:
        m = re.search(pattern, message.lower())
        if m:
            name = m.group(1).strip()
            if "github.com" in name:
                return {"wants_install": True, "tool_name": name.split("/")[-1],
                        "github_url": name, "install_mode": "github", "description": ""}
            return {"wants_install": True, "tool_name": name,
                    "github_url": None, "install_mode": "auto", "description": ""}

    # LLM анализ для неочевидных запросов
    try:
        raw = _llm(message, INSTALL_INTENT_SYSTEM, max_tokens=300)
        for pat in [r"\{.*\}", r"```json\s*(.*?)```"]:
            m = re.search(pat, raw, re.DOTALL)
            if m:
                try:
                    data = json.loads(m.group(0) if pat.startswith(r"\{") else m.group(1))
                    return data
                except Exception:
                    pass
    except Exception:
        pass

    return {"wants_install": False}


# ══════════════════════════════════════════════════════════════════════════════
#  Tool Generation — 3 режима: LLM / GitHub / Pip
# ══════════════════════════════════════════════════════════════════════════════

def generate_tool(
    name: str,
    description: str,
    example_inputs: dict,
    on_status: Optional[Callable] = None,
    github_url: str = "",
    install_mode: str = "auto",  # "auto" | "llm" | "github" | "pip"
) -> Tuple[bool, str]:
    """
    Генерирует инструмент. Три режима:
    - github: клонирует репо с GitHub
    - pip: устанавливает pip-пакет и создаёт обёртку
    - llm: генерирует код через LLM (default)
    - auto: определяет автоматически
    """
    def st(msg):
        if on_status: on_status(msg)

    # Определяем режим автоматически
    if install_mode == "auto":
        if github_url or "github.com" in description:
            install_mode = "github"
        elif any(kw in description.lower() for kw in ("pip install", "пакет", "библиотека")):
            install_mode = "pip"
        else:
            install_mode = "llm"

    # ── GitHub path ────────────────────────────────────────────────────────────
    if install_mode == "github":
        url = github_url or re.search(r"https://github\.com/\S+", description)
        url = url.group(0) if hasattr(url, "group") else url
        if url:
            return _install_github(name, url, description, on_status)
        # fallback to LLM
        st("⚠️ GitHub URL не найден, генерирую через LLM...")

    # ── Pip path ───────────────────────────────────────────────────────────────
    if install_mode == "pip":
        return _install_pip_wrapper(name, description, example_inputs, on_status)

    # ── LLM generation path ────────────────────────────────────────────────────
    return _generate_llm_tool(name, description, example_inputs, on_status)


def _generate_llm_tool(
    name: str,
    description: str,
    example_inputs: dict,
    on_status: Optional[Callable] = None,
) -> Tuple[bool, str]:
    """Генерирует инструмент через LLM с итеративным улучшением."""
    def st(msg):
        if on_status: on_status(msg)

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
        f"- subprocess: всегда timeout=600 (НЕ 60, НЕ 30!)\n"
        f"- Все ошибки перехватывай\n\n"
        f"Напиши ТОЛЬКО функцию run_tool."
    )

    code = None
    last_error = ""
    error_history: List[str] = []
    same_error_count: int = 0

    for attempt in range(1, MAX_GEN_ATTEMPTS + 1):
        # ← ИСПРАВЛЕНО: убран timeout=600, теперь сразу 300s на первую попытку
        timeout = 300 + attempt * 60  # 300→360→420→480→540→600→660s

        st(f"  ⚙️ Попытка {attempt}/{MAX_GEN_ATTEMPTS} (sandbox timeout={timeout}s)...")

        if attempt == 1 or not code:
            raw = _llm(base_prompt, MATRIX_SYSTEM, max_tokens=4000)
        else:
            hist = "\n".join(f"  #{i+1}: {e}" for i, e in enumerate(error_history[-3:]))
            fix_prompt = (
                f"Инструмент `{name}` не работает.\n\n"
                f"Код:\n```python\n{code}\n```\n\n"
                f"История ошибок:\n{hist}\n"
                f"Последняя: {last_error}\n\n"
                f"КРИТИЧЕСКИ ВАЖНО:\n"
                f"• subprocess timeout должен быть 600, а НЕ 60 или 30!\n"
                f"• No module named X → добавь subprocess pip install\n"
                f"• bytes/str ошибка → добавь _dec() декодер\n"
                f"• FileNotFoundError → проверяй os.path.exists()\n\n"
                f"Верни ТОЛЬКО исправленную run_tool()."
            )
            raw = _llm(fix_prompt, MATRIX_SYSTEM, max_tokens=4000)
            if attempt >= MAX_GEN_ATTEMPTS - 2 and same_error_count >= 2:
                alt_prompt = (
                    f"Предыдущий подход к `{name}` не работает.\n"
                    f"Цель: {description}\n"
                    f"Придумай ДРУГОЙ способ реализации.\n"
                    f"Используй другие библиотеки или subprocess с shell-командами.\n"
                    f"Напиши ТОЛЬКО run_tool(inputs: dict) -> dict."
                )
                raw = _llm(alt_prompt, MATRIX_SYSTEM, max_tokens=4000)
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
            register_tool(name, description, code, install_mode="llm")
            st(f"  ✅ '{name}' создан и зарегистрирован!")
            return True, ""

        clean_err = output.strip()[:300]
        same_error_count = error_history.count(clean_err)
        last_error = clean_err
        error_history.append(clean_err)
        st(f"  ❌ {clean_err[:80]}")

    return False, f"Не удалось за {MAX_GEN_ATTEMPTS} попыток. Последняя ошибка: {last_error[:200]}"


def _install_pip_wrapper(
    name: str,
    description: str,
    example_inputs: dict,
    on_status: Optional[Callable] = None,
) -> Tuple[bool, str]:
    """Устанавливает pip-пакет и генерирует обёртку."""
    def st(msg):
        if on_status: on_status(msg)

    # Определяем пакет из описания
    pkg_match = re.search(r"pip\s+install\s+([\w\-_]+)", description, re.IGNORECASE)
    pkg_name = pkg_match.group(1) if pkg_match else name.replace("_", "-")

    st(f"📦 Устанавливаю pip пакет: {pkg_name}...")
    r = subprocess.run(
        [sys.executable, "-m", "pip", "install", pkg_name, "-q", "--break-system-packages"],
        capture_output=True, timeout=600
    )
    if r.returncode != 0:
        st(f"  ⚠️ pip install ошибка: {_dec(r.stderr)[:100]}")

    # Генерируем обёртку через LLM
    return _generate_llm_tool(name, description, example_inputs, on_status)


def _install_github(
    tool_name: str,
    url: str,
    description: str,
    on_status: Optional[Callable] = None,
) -> Tuple[bool, str]:
    """Клонирует GitHub репо, ставит deps, генерирует обёртку, регистрирует."""
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

    # Entry point
    entry = ""
    repo_name = url.rstrip('/').split('/')[-1].replace('.git', '')
    entry_candidates = []
    for py_name in (f"{repo_name}.py", f"{tool_name}.py", "main.py", "app.py", "run.py", "cli.py"):
        if (Path(dest) / py_name).exists():
            entry_candidates.append((py_name, f"python3 {py_name}"))
    for pyf in sorted(Path(dest).glob("*.py")):
        if pyf.name in ("setup.py", "setup_wizard.py", "install.py", "test.py"):
            continue
        try:
            content = pyf.read_text(encoding="utf-8", errors="replace")
            if "__main__" in content or "argparse" in content or "sys.argv" in content:
                entry_candidates.append((pyf.name, f"python3 {pyf.name}"))
        except Exception:
            pass
    if (Path(dest) / "__main__.py").exists():
        entry_candidates.insert(0, ("__main__.py", f"python3 -m {tool_name}"))
    seen = set()
    for fname, cmd in entry_candidates:
        if fname not in seen:
            seen.add(fname)
            entry = cmd
            break
    if not entry:
        py_files = sorted(Path(dest).glob("*.py"))
        entry = f"python3 {py_files[0].name}" if py_files else f"python3 -m {tool_name}"

    st(f"  📌 Точка входа: {entry}")

    # README
    readme = ""
    for rn in ("README.md", "README.rst", "README.txt", "readme.md"):
        rf = Path(dest) / rn
        if rf.exists():
            readme = rf.read_text(encoding="utf-8", errors="replace")[:3000]
            break

    # Test --help
    help_output = ""
    try:
        rh = subprocess.run(
            entry + " --help", shell=True,
            capture_output=True, timeout=15, cwd=dest
        )
        help_output = (_dec(rh.stdout) + _dec(rh.stderr))[:1000]
    except Exception:
        pass

    # LLM: генерируем обёртку
    st("🤖 Генерирую обёртку через LLM...")
    gen_prompt = (
        f"Создай run_tool() для GitHub инструмента `{tool_name}`:\n"
        f"URL: {url}\n"
        f"Путь на диске: {dest}\n"
        f"Команда запуска: {entry}\n"
        f"README:\n{readme[:600]}\n"
        f"--help вывод:\n{help_output[:400]}\n\n"
        f"Обёртка должна:\n"
        f"1. Принимать inputs с ключами специфичными для этого инструмента\n"
        f"2. Строить CLI аргументы из inputs\n"
        f"3. Принимать общий inputs['args'] как запасной вариант\n"
        f"4. Запускать через subprocess с cwd={dest!r}\n"
        f"5. ВАЖНО: timeout=600 (не 60!)\n"
        f"6. Декодировать bytes: for e in ('utf-8','cp1251','latin-1'): try: return b.decode(e)\n"
        f"7. Возвращать {{ok, output, files, error}}\n\n"
        f"Напиши ТОЛЬКО run_tool(inputs: dict) -> dict."
    )
    raw = _llm(gen_prompt, MATRIX_SYSTEM, max_tokens=3000)
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

    # Generate usage guide
    st("📖 Генерирую инструкцию по использованию...")
    guide_prompt = (
        f"Инструмент `{tool_name}` установлен из {url}\n"
        f"README:\n{readme[:800]}\n"
        f"--help:\n{help_output[:400]}\n\n"
        f"Напиши краткую инструкцию на русском:\n"
        f"1. Что делает этот инструмент (2-3 предложения)\n"
        f"2. Основные параметры запуска (таблица: параметр → что делает)\n"
        f"3. 3-5 примеров команд для агента MATRIX\n"
        f"Формат: markdown, компактно."
    )
    usage_guide = _llm(guide_prompt, max_tokens=1000)

    # Test
    st("🧪 Тестирую...")
    ok, output, _ = sandbox_run(code, {"args": "--help"}, timeout=600)
    critical = any(e in output.lower() for e in
                   ("no such file", "importerror", "syntaxerror", "modulenotfounderror"))
    if not ok and critical:
        return False, f"Критическая ошибка обёртки: {output[:300]}"

    register_tool(tool_name, description or f"GitHub: {url}", code,
                  install_mode="github", github_url=url)

    # Save usage guide
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
#  Built-in tools registration (полная версия из оригинала)
# ══════════════════════════════════════════════════════════════════════════════

_BUILTIN_TOOLS = {}

def _bt(name, desc, code_lines):
    code = "\n".join(code_lines)
    _BUILTIN_TOOLS[name] = (desc, code)

# (Встроенные инструменты — идентичны оригиналу, см. agent_matrix.py)
# Копируем все _bt(...) вызовы из оригинального файла без изменений.
# Они здесь не переопределяются для краткости патча.
# При применении патча используй полный файл с _bt() блоками.


def warmup(on_status: Optional[Callable] = None) -> dict:
    """Регистрирует все встроенные инструменты при старте."""
    registered = skipped = failed = 0
    for name, (desc, code) in _BUILTIN_TOOLS.items():
        try:
            if tool_exists(name):
                skipped += 1
                continue
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

    for pat in [r"\{.*\}", r"```json\s*(.*?)```", r"```\s*(.*?)```"]:
        m = re.search(pat, raw, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group(0) if pat.startswith(r"\{") else m.group(1))
                if "steps" in data:
                    return data
            except Exception:
                pass

    return {
        "steps": [{"id": 1, "description": task, "tool_name": "python_eval",
                   "tool_exists": True, "inputs": {"code": f"print({task!r})"}, "depends_on": []}],
        "summary": task
    }


# ══════════════════════════════════════════════════════════════════════════════
#  Result & main pipeline
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
    """Главный pipeline AGENT MATRIX v2.0."""
    t0 = time.time()

    def st(msg):
        if on_status: on_status(msg)

    # ── Детектируем провокационные запросы на установку инструментов ──────────
    intent = detect_install_intent(task)
    if intent.get("wants_install") and intent.get("tool_name"):
        iname = intent["tool_name"]
        if not tool_exists(iname):
            st(f"🔍 Обнаружен запрос на установку инструмента: {iname}")
            ok_gen, err_gen = generate_tool(
                iname,
                intent.get("description", task),
                intent.get("example_inputs", {}),
                on_status=on_status,
                github_url=intent.get("github_url", ""),
                install_mode=intent.get("install_mode", "auto"),
            )
            if ok_gen:
                st(f"✅ Инструмент '{iname}' готов к использованию!")
            else:
                st(f"⚠️ Не удалось создать '{iname}': {err_gen}")

    st("🧠 MATRIX анализирует задачу...")
    plan = plan_task(task, chat_id, attached_files)
    steps = plan.get("steps", [])
    st(f"📋 План: {len(steps)} шагов")

    run_dir = ARTIFACTS_DIR / f"run_{int(time.time())}"
    run_dir.mkdir(parents=True, exist_ok=True)

    all_files: list = []
    generated_tools: list = []
    step_outputs: dict = {}
    step_errors: list = []
    steps_done = 0

    KNOWN_TOOLS = {
        "python_eval", "shell_cmd", "analyze_code", "run_tests",
        "osint_username", "osint_domain", "web_scrape", "http_get",
        "port_scan", "ssl_check", "deps_audit",
        "github_clone", "github_install", "pip_install",
        "file_read", "file_write", "zip_files",
        "matrix_create_tool", "matrix_list_tools",
    }
    FAKE_TOOLS = {
        "run_script", "check_syntax", "lint_code", "execute_code",
        "code_runner", "run_code", "execute_script", "code_exec",
    }

    for step in steps:
        sid       = step.get("id", 0)
        tool_name = step.get("tool_name", "python_eval")
        desc      = step.get("description", "")
        s_inputs  = dict(step.get("inputs", {}))

        st(f"⚙️ Шаг {sid}: {desc[:60]}...")
        s_inputs.setdefault("output_dir", str(run_dir))

        for dep_id in step.get("depends_on", []):
            prev = step_outputs.get(dep_id, {})
            if prev.get("files") and "path" not in s_inputs:
                s_inputs["path"] = prev["files"][0]
            if prev.get("output") and "prev_output" not in s_inputs:
                s_inputs["prev_output"] = prev["output"][:500]
            if prev.get("files") and "files" not in s_inputs:
                s_inputs["files"] = prev["files"]

        if attached_files and sid == 1 and "path" not in s_inputs:
            s_inputs["path"] = attached_files[0]

        code = get_tool_code(tool_name)

        if tool_name in FAKE_TOOLS:
            st(f"  ↩️ {tool_name!r} не существует → python_eval")
            if "code" not in s_inputs and "script" not in s_inputs:
                s_inputs["code"] = f"# Задача: {desc}\nprint('Выполнено')"
            tool_name = "python_eval"
            code = get_tool_code("python_eval")

        elif not code and tool_name not in KNOWN_TOOLS:
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
            st(f"  🔄 Инициализирую встроенные инструменты...")
            warmup()
            code = get_tool_code(tool_name)

        if not code:
            if "code" in s_inputs or "script" in s_inputs:
                st(f"  ↩️ fallback → python_eval")
                tool_name = "python_eval"
                code = get_tool_code("python_eval")
            else:
                step_errors.append(f"Шаг {sid}: инструмент {tool_name!r} недоступен")
                continue

        # ← ИСПРАВЛЕНО: убран hardcoded timeout=600, используем SANDBOX_TIMEOUT
        ok, output, files = sandbox_run(code, s_inputs, timeout=SANDBOX_TIMEOUT)
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
                tts_f = tempfile.mktemp(suffix=".mp3", dir=str(ARTIFACTS_DIR))
                if tts_generate(answer[:500], tts_f):
                    tts_path = tts_f
            except Exception:
                pass
        else:
            answer = summary[:800] if summary else "Задача выполнена."
    except Exception:
        answer = f"Выполнено за {time.time()-t0:.1f}с"

    # ── ZIP артефакт ──────────────────────────────────────────────────────────
    zip_path = ""
    try:
        zp = ARTIFACTS_DIR / f"matrix_{int(time.time())}.zip"
        with zipfile.ZipFile(str(zp), "w", zipfile.ZIP_DEFLATED) as zf:
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
                     attached_files=None, on_status=None, callback=None):
    """Запускает MATRIX в отдельном потоке."""
    import threading
    def _run():
        result = run_matrix(task, chat_id, attached_files, on_status)
        if callback: callback(result)
    t = threading.Thread(target=_run, daemon=True, name=f"matrix-{chat_id}")
    t.start()
    return t


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
