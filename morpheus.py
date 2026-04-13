"""
agents/morpheus.py — AGENT MORPHEUS
Owner/God only. Root-level system agent.
Executes: apt, pip, docker, systemctl, shell, file system ops.
Auto-fixes dependencies. Spawns/manages Docker containers.
"""
from __future__ import annotations
import os, re, json, time, subprocess, shutil, threading
from pathlib import Path
from typing import Optional, Callable, List, Dict, Tuple
from core.agent_base import AgentBase
from core.agent_brain import BrainMixin, CodeLinter, AgentResult
import config

# ── Константы ─────────────────────────────────────────────────────────────────
MORPHEUS_DIR   = Path(config.BASE_DIR) / "morpheus_workspace"
TOOLS_DIR      = MORPHEUS_DIR / "tools"
CONTAINERS_DIR = MORPHEUS_DIR / "containers"
LOGS_DIR       = MORPHEUS_DIR / "logs"
MAX_AUTOFIX    = 5      # максимум авто-фиксов зависимостей
CMD_TIMEOUT    = 300    # timeout на системные команды (сек)
DOCKER_TIMEOUT = 600    # timeout на docker build/run

for _d in (MORPHEUS_DIR, TOOLS_DIR, CONTAINERS_DIR, LOGS_DIR):
    _d.mkdir(parents=True, exist_ok=True)


# ══════════════════════════════════════════════════════════════════════════════
#  КОМАНДЫ: WHITELIST / BLACKLIST
# ══════════════════════════════════════════════════════════════════════════════

# Абсолютно запрещено даже для owner
MORPHEUS_BLACKLIST = [
    "rm -rf /",
    "mkfs",
    "dd if=/dev/zero of=/dev/sd",
    ":(){:|:&};:",          # fork bomb
    "> /dev/sda",
    "chmod -R 777 /",
    "chown -R nobody /",
    "wipefs",
    "shred /dev/",
]

# Команды требующие подтверждения (опасные но разрешённые owner)
MORPHEUS_CONFIRM = [
    r"^rm\s+-rf\s+/",
    r"^systemctl\s+(stop|disable)\s+docker",
    r"^docker\s+(rm|rmi|system\s+prune)\s+-f",
    r"^pkill\s+-9\s+python",
]

# Все остальные команды — разрешены для owner/god через Morpheus
MORPHEUS_SYSTEM_PROMPT = """Ты — AGENT MORPHEUS, системный root-агент BlackBugsAI.
Доступен ТОЛЬКО владельцу системы (owner/god).

ВОЗМОЖНОСТИ:
- Системные команды: apt-get, apt, pip, npm, cargo, go get
- Docker: build, run, exec, inspect, logs, stop, rm, network
- Файловая система: полный доступ (read/write/delete)
- Сервисы: systemctl start/stop/restart/status
- Мониторинг: ps, top, df, free, netstat, journalctl
- Git: clone, pull, push, checkout
- Анализ репозиториев и генерация Dockerfile

ПРИНЦИПЫ РАБОТЫ:
1. Выполняй команды последовательно — каждая следующая учитывает вывод предыдущей
2. При ошибке зависимостей — АВТОМАТИЧЕСКИ исправляй: ищи пакет, устанавливай, повторяй
3. Если команда вернула non-zero — анализируй stderr и предлагай фикс
4. Логируй ВСЕ команды с timestamps
5. При работе с Docker — создавай изолированные контейнеры

ФОРМАТ ПЛАНА:
{"steps": [
  {"id": 1, "description": "...", "cmd": "bash-команда", "tool": "shell|apt|docker|pip|git|analyze", 
   "inputs": {}, "depends_on": [], "critical": true/false}
], "summary": "..."}

ТИПЫ ШАГОВ:
- shell: произвольная bash-команда
- apt: apt-get install / apt-get update
- pip: pip install
- npm: npm install
- docker_build: docker build
- docker_run: docker run
- docker_exec: docker exec
- git_clone: git clone + анализ
- analyze_repo: читает README/requirements/Dockerfile и строит план
- generate_dockerfile: генерирует Dockerfile для репозитория
- autofix: автоматический фикс ошибки из предыдущего шага
"""

MORPHEUS_PLANNER_SYSTEM = """Ты планировщик AGENT MORPHEUS. Анализируй задачу и верни JSON план.
Отвечай ТОЛЬКО валидным JSON без markdown.

ФОРМАТ:
{
  "steps": [
    {
      "id": 1,
      "description": "Описание шага",
      "tool": "shell|apt|pip|docker_build|docker_run|docker_exec|git_clone|analyze_repo|generate_dockerfile",
      "cmd": "конкретная команда для выполнения",
      "inputs": {"key": "val"},
      "depends_on": [],
      "critical": true
    }
  ],
  "summary": "Краткий итог что будет сделано"
}

ПРАВИЛА:
1. apt → всегда начинай с apt-get update если устанавливаешь новые пакеты
2. Docker репо → git_clone → analyze_repo → generate_dockerfile → docker_build → docker_run
3. Зависимости Python → pip install -r requirements.txt
4. При ошибке предусмотри шаг autofix
5. Команды КОНКРЕТНЫЕ — без заглушек типа '<ваш_пакет>'
"""


# ══════════════════════════════════════════════════════════════════════════════
#  СИСТЕМНЫЙ ИСПОЛНИТЕЛЬ
# ══════════════════════════════════════════════════════════════════════════════

def _dec(b) -> str:
    """Decode bytes to str with fallback."""
    if not b: return ""
    if isinstance(b, str): return b
    for enc in ("utf-8", "cp1251", "cp866", "latin-1"):
        try: return b.decode(enc)
        except: pass
    return b.decode("utf-8", errors="replace")


def _is_blacklisted(cmd: str) -> Tuple[bool, str]:
    """Check if command is absolutely forbidden."""
    cmd_low = cmd.strip().lower()
    for blocked in MORPHEUS_BLACKLIST:
        if blocked in cmd_low:
            return True, f"🚫 Заблокировано: содержит '{blocked}'"
    return False, ""


def _log_cmd(cmd: str, result: str, ok: bool):
    """Log every executed command."""
    log_file = LOGS_DIR / f"morpheus_{time.strftime('%Y-%m-%d')}.log"
    entry = f"[{time.strftime('%H:%M:%S')}] {'✅' if ok else '❌'} {cmd[:200]}\n{result[:500]}\n---\n"
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception:
        pass


def run_system_cmd(
    cmd: str,
    cwd: str = "/",
    timeout: int = CMD_TIMEOUT,
    env: dict = None,
) -> Tuple[bool, str]:
    """
    Execute system command as root inside container.
    Returns (success, output).
    """
    blocked, reason = _is_blacklisted(cmd)
    if blocked:
        return False, reason

    _env = dict(os.environ)
    if env:
        _env.update(env)
    # Ensure non-interactive apt
    _env["DEBIAN_FRONTEND"] = "noninteractive"

    try:
        r = subprocess.run(
            cmd, shell=True, capture_output=True,
            timeout=timeout, cwd=cwd, env=_env,
        )
        out = (_dec(r.stdout) + _dec(r.stderr)).strip()
        ok = r.returncode == 0
        _log_cmd(cmd, out, ok)
        return ok, out[:8000]
    except subprocess.TimeoutExpired:
        _log_cmd(cmd, "TIMEOUT", False)
        return False, f"⏰ Timeout ({timeout}s): {cmd[:100]}"
    except Exception as e:
        _log_cmd(cmd, str(e), False)
        return False, f"❌ Ошибка: {e}"


def _detect_missing_dep(error_output: str) -> Optional[str]:
    """
    Parse error output and detect missing dependency.
    Returns package name or None.
    """
    patterns = [
        r"No module named '([^']+)'",
        r"ModuleNotFoundError: No module named '([^']+)'",
        r"ImportError: cannot import name '([^']+)'",
        r"command not found: (\S+)",
        r"(\S+): not found",
        r"Package '([^']+)' has no installation candidate",
        r"ERROR: Could not find a version that satisfies the requirement (\S+)",
        r"npm ERR! Cannot find module '([^']+)'",
        r"go: cannot find module providing ([^\s:]+)",
    ]
    for pattern in patterns:
        m = re.search(pattern, error_output, re.IGNORECASE)
        if m:
            pkg = m.group(1).split(".")[0]  # Take top-level package
            return pkg
    return None


def _auto_install_dep(pkg: str, error_ctx: str, on_status: Callable = None) -> Tuple[bool, str]:
    """
    Try to install missing dependency.
    Attempts: pip → apt → npm in order.
    """
    def st(msg):
        if on_status: on_status(msg)

    # Determine install method from context
    if "import" in error_ctx.lower() or "module" in error_ctx.lower():
        # Python package
        st(f"📦 Устанавливаю Python пакет: {pkg}")
        ok, out = run_system_cmd(
            f"pip install {pkg} --break-system-packages -q", timeout=120
        )
        if ok:
            return True, f"pip install {pkg} ✅"
        # Try apt python3-pkg
        apt_pkg = f"python3-{pkg.replace('_', '-').lower()}"
        st(f"📦 Попытка через apt: {apt_pkg}")
        ok2, out2 = run_system_cmd(
            f"apt-get install -y {apt_pkg} -qq", timeout=120
        )
        if ok2:
            return True, f"apt install {apt_pkg} ✅"
        return False, f"Не удалось установить {pkg}: pip={out[:100]} apt={out2[:100]}"

    elif "not found" in error_ctx.lower() or "command" in error_ctx.lower():
        # System binary
        st(f"🔧 Устанавливаю системный пакет: {pkg}")
        ok, out = run_system_cmd(
            f"apt-get update -qq && apt-get install -y {pkg} -qq", timeout=180
        )
        return ok, f"apt install {pkg}: {'✅' if ok else out[:200]}"

    else:
        # Try pip first, then apt
        for installer in [
            f"pip install {pkg} --break-system-packages -q",
            f"apt-get install -y {pkg} -qq",
        ]:
            ok, out = run_system_cmd(installer, timeout=120)
            if ok:
                return True, f"{installer} ✅"
        return False, f"Не удалось установить {pkg}"


# ══════════════════════════════════════════════════════════════════════════════
#  DOCKER HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def docker_build(build_dir: str, tag: str, on_status: Callable = None) -> Tuple[bool, str]:
    """Build Docker image."""
    def st(msg):
        if on_status: on_status(msg)
    st(f"🐳 Собираю образ {tag}...")
    ok, out = run_system_cmd(
        f"docker build -t {tag} {build_dir}", timeout=DOCKER_TIMEOUT
    )
    return ok, out


def docker_run(
    image: str, name: str = "", ports: str = "", volumes: str = "",
    env_vars: str = "", cmd: str = "", detach: bool = True,
    on_status: Callable = None,
) -> Tuple[bool, str]:
    """Run Docker container."""
    def st(msg):
        if on_status: on_status(msg)

    args = ["docker", "run"]
    if detach: args.append("-d")
    args += ["--rm"] if not detach else []
    if name: args += ["--name", name]
    if ports: args += ["-p", ports]
    if volumes: args += ["-v", volumes]
    if env_vars: args += ["-e", env_vars]
    args.append(image)
    if cmd: args += cmd.split()

    full_cmd = " ".join(args)
    st(f"🚀 Запускаю контейнер: {name or image}")
    ok, out = run_system_cmd(full_cmd, timeout=DOCKER_TIMEOUT)
    return ok, out


def docker_exec(container: str, cmd: str, on_status: Callable = None) -> Tuple[bool, str]:
    """Execute command inside running container."""
    full = f"docker exec {container} sh -c {repr(cmd)}"
    if on_status: on_status(f"🔧 exec [{container}]: {cmd[:60]}")
    return run_system_cmd(full, timeout=CMD_TIMEOUT)


def analyze_repo(repo_path: str) -> dict:
    """
    Analyze repository structure and determine:
    - project type (Python/Node/Go/Ruby/etc.)
    - entry point
    - dependencies file
    - existing Dockerfile
    - suggested run command
    """
    p = Path(repo_path)
    info = {
        "type": "unknown",
        "has_dockerfile": False,
        "deps_file": None,
        "entry": None,
        "run_cmd": None,
        "readme": "",
        "port": None,
    }

    # Detect type
    if (p / "requirements.txt").exists() or (p / "setup.py").exists() or (p / "pyproject.toml").exists():
        info["type"] = "python"
        info["deps_file"] = "requirements.txt"
        info["run_cmd"] = "python3 main.py" if (p / "main.py").exists() else "python3 app.py"
    elif (p / "package.json").exists():
        info["type"] = "node"
        info["deps_file"] = "package.json"
        info["run_cmd"] = "npm start"
    elif (p / "go.mod").exists():
        info["type"] = "go"
        info["run_cmd"] = "go run ."
    elif (p / "Cargo.toml").exists():
        info["type"] = "rust"
        info["run_cmd"] = "cargo run"
    elif (p / "Gemfile").exists():
        info["type"] = "ruby"
        info["run_cmd"] = "ruby app.rb"

    # Check Dockerfile
    if (p / "Dockerfile").exists():
        info["has_dockerfile"] = True

    # Find entry point
    for entry in ("main.py", "app.py", "run.py", "server.py", "bot.py", "index.js", "server.js"):
        if (p / entry).exists():
            info["entry"] = entry
            break

    # Read README
    for rname in ("README.md", "README.rst", "README.txt"):
        rf = p / rname
        if rf.exists():
            try:
                info["readme"] = rf.read_text(encoding="utf-8", errors="replace")[:2000]
            except Exception:
                pass
            break

    # Detect port from README or entry files
    readme_lower = info["readme"].lower()
    for port_hint in ("port 8080", "port 3000", "port 5000", "port 8000", ":8080", ":3000"):
        if port_hint in readme_lower:
            info["port"] = port_hint.replace("port ", "").replace(":", "")
            break

    return info


def generate_dockerfile(repo_info: dict, project_name: str) -> str:
    """Generate Dockerfile based on repo analysis."""
    ptype = repo_info.get("type", "python")
    deps  = repo_info.get("deps_file", "requirements.txt")
    run   = repo_info.get("run_cmd", "python3 main.py")
    port  = repo_info.get("port", "8080")

    if ptype == "python":
        return f"""FROM python:3.11-slim
LABEL project="{project_name}"
WORKDIR /app
RUN apt-get update && apt-get install -y git curl wget gcc g++ --no-install-recommends && rm -rf /var/lib/apt/lists/*
COPY {deps or 'requirements.txt'} .
RUN pip install -r {deps or 'requirements.txt'} --break-system-packages || true
COPY . .
EXPOSE {port}
CMD {json.dumps(run.split())}
"""
    elif ptype == "node":
        return f"""FROM node:20-slim
LABEL project="{project_name}"
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
EXPOSE {port}
CMD ["npm", "start"]
"""
    elif ptype == "go":
        return f"""FROM golang:1.21-alpine AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN go build -o main .

FROM alpine:latest
WORKDIR /root/
COPY --from=builder /app/main .
EXPOSE {port}
CMD ["./main"]
"""
    else:
        return f"""FROM ubuntu:22.04
LABEL project="{project_name}"
WORKDIR /app
RUN apt-get update && apt-get install -y python3 python3-pip nodejs npm curl wget git
COPY . .
EXPOSE {port}
CMD ["bash", "-c", "{run}"]
"""


# ══════════════════════════════════════════════════════════════════════════════
#  AGENT MORPHEUS
# ══════════════════════════════════════════════════════════════════════════════

class AgentMorpheus(BrainMixin, AgentBase):
    """🔵 Root-агент. Системные команды, apt/pip/docker, авто-фикс зависимостей."""

    NAME   = "MORPHEUS"
    EMOJI  = "🔵"
    ACCESS = ["god", "owner"]   # ТОЛЬКО owner и god
    MODES  = ["auto", "shell", "apt", "docker", "repo", "fix"]

    # Brain настройки
    BRAIN_REFLEXION = False   # Системные команды — не рефлексируем
    BRAIN_LINTING   = True    # ruff для скриптов
    BRAIN_DELEGATE  = False   # Morpheus — root, сам всё делает

    SYSTEM_PROMPT = MORPHEUS_SYSTEM_PROMPT

    def execute(
        self,
        task:       str,
        chat_id:    int,
        files:      list = None,
        mode:       str = "auto",
        on_status:  Callable = None,
    ) -> AgentResult:
        t0 = time.time()
        self._status_fn = on_status

        def st(msg):
            self.status(msg)
            _log_cmd(f"[STATUS] {msg}", "", True)

        st(f"🔵 MORPHEUS [{mode}] получил задачу...")

        # ── Detect mode ───────────────────────────────────────────────────────
        task_low = task.lower()
        if mode == "auto":
            if any(kw in task_low for kw in ("apt", "apt-get", "установи пакет", "install package")):
                mode = "apt"
            elif any(kw in task_low for kw in ("docker", "контейнер", "образ", "build")):
                mode = "docker"
            elif any(kw in task_low for kw in ("github.com", "gitlab.com", "клонируй", "clone")):
                mode = "repo"
            elif any(kw in task_low for kw in ("исправь", "fix", "зависимост", "ошибка зависим")):
                mode = "fix"
            else:
                mode = "shell"

        st(f"  Режим: {mode}")

        # ── Route to handler ──────────────────────────────────────────────────
        if mode == "repo":
            return self._handle_repo(task, chat_id, files, on_status, t0)
        elif mode == "apt":
            return self._handle_apt(task, chat_id, on_status, t0)
        elif mode == "docker":
            return self._handle_docker(task, chat_id, on_status, t0)
        elif mode == "fix":
            return self._handle_autofix(task, chat_id, on_status, t0)
        else:
            return self._handle_shell(task, chat_id, files, on_status, t0)

    # ──────────────────────────────────────────────────────────────────────────
    #  SHELL режим — общие команды
    # ──────────────────────────────────────────────────────────────────────────
    def _handle_shell(self, task, chat_id, files, on_status, t0) -> AgentResult:
        def st(m): self.status(m)

        # Если задача выглядит как прямая команда — выполняем сразу
        direct_cmd_patterns = [r"^[a-z]+\s", r"^/", r"^\$\s*(.+)"]
        is_direct = any(re.match(p, task.strip()) for p in direct_cmd_patterns)

        if is_direct or len(task) < 120:
            # Try as direct shell command
            cmd = task.strip().lstrip("$ ")
            blocked, reason = _is_blacklisted(cmd)
            if blocked:
                return AgentResult(ok=False, error=reason, agent="MORPHEUS",
                                   mode="shell", duration=time.time()-t0)
            st(f"⚡ Выполняю: {cmd[:80]}")
            ok, out = run_system_cmd(cmd)
            if ok:
                return AgentResult(ok=True, answer=f"✅ ```\n{out[:3000]}\n```",
                                   agent="MORPHEUS", mode="shell", duration=time.time()-t0)

        # LLM-планирование для сложных задач
        st("🧠 Планирую через LLM...")
        plan = self.llm_json(
            f"Задача: {task}\nФайлы: {files or []}\nВерни JSON план системных команд.",
            MORPHEUS_PLANNER_SYSTEM
        )
        if not plan:
            return AgentResult(ok=False, error="LLM не вернул план", agent="MORPHEUS",
                               mode="shell", duration=time.time()-t0)

        return self._execute_plan(plan, task, on_status, t0)

    # ──────────────────────────────────────────────────────────────────────────
    #  APT режим — установка системных пакетов
    # ──────────────────────────────────────────────────────────────────────────
    def _handle_apt(self, task, chat_id, on_status, t0) -> AgentResult:
        def st(m): self.status(m)

        # Extract package names from task
        pkg_match = re.findall(
            r"(?:apt(?:-get)?\s+install\s+|установи\s+|install\s+)([a-zA-Z0-9\-_\s]+?)(?:\s|$|,|\.|и\s)",
            task, re.IGNORECASE
        )
        packages = []
        for match in pkg_match:
            packages.extend(match.strip().split())
        # Fallback: ask LLM what to install
        if not packages:
            raw = self.llm(
                f"Задача: {task}\nКакие apt-пакеты нужно установить? Верни ТОЛЬКО список пакетов через пробел.",
                max_tokens=200
            )
            packages = raw.strip().split()

        packages = [p for p in packages if re.match(r'^[a-zA-Z0-9\-_\.]+$', p)]
        if not packages:
            return AgentResult(ok=False, error="Не удалось определить пакеты для установки",
                               agent="MORPHEUS", mode="apt", duration=time.time()-t0)

        st(f"📦 Обновляю индекс пакетов...")
        ok_upd, out_upd = run_system_cmd("apt-get update -qq", timeout=120)

        results = []
        all_ok = True
        for pkg in packages[:20]:  # max 20 packages at once
            st(f"📦 Устанавливаю: {pkg}")
            ok, out = run_system_cmd(
                f"apt-get install -y {pkg} -qq --no-install-recommends",
                timeout=180
            )
            results.append(f"{'✅' if ok else '❌'} {pkg}: {out[:100] if not ok else 'установлен'}")
            if not ok:
                all_ok = False

        answer = "📦 **Результат установки пакетов:**\n" + "\n".join(results)
        return AgentResult(ok=all_ok, answer=answer, agent="MORPHEUS",
                           mode="apt", duration=time.time()-t0)

    # ──────────────────────────────────────────────────────────────────────────
    #  DOCKER режим
    # ──────────────────────────────────────────────────────────────────────────
    def _handle_docker(self, task, chat_id, on_status, t0) -> AgentResult:
        def st(m): self.status(m)

        st("🐳 Планирую Docker операции...")
        plan = self.llm_json(
            f"Задача: {task}\nВерни JSON план Docker операций.",
            MORPHEUS_PLANNER_SYSTEM
        )
        if not plan:
            # Direct docker command
            cmd = task.strip()
            if not cmd.startswith("docker"):
                cmd = "docker " + cmd
            ok, out = run_system_cmd(cmd, timeout=DOCKER_TIMEOUT)
            return AgentResult(ok=ok, answer=f"{'✅' if ok else '❌'} ```\n{out[:3000]}\n```",
                               agent="MORPHEUS", mode="docker", duration=time.time()-t0)

        return self._execute_plan(plan, task, on_status, t0)

    # ──────────────────────────────────────────────────────────────────────────
    #  REPO режим — клонирование + анализ + Docker + run
    # ──────────────────────────────────────────────────────────────────────────
    def _handle_repo(self, task, chat_id, files, on_status, t0) -> AgentResult:
        def st(m): self.status(m)

        # Extract GitHub URL
        url_match = re.search(r'https?://github\.com/[\w\-]+/[\w\-\.]+', task)
        if not url_match:
            url_match = re.search(r'github\.com/[\w\-]+/[\w\-\.]+', task)
        if not url_match:
            return AgentResult(ok=False, error="GitHub URL не найден в задаче",
                               agent="MORPHEUS", mode="repo", duration=time.time()-t0)

        url = url_match.group(0)
        if not url.startswith("http"):
            url = "https://" + url

        repo_name = url.rstrip("/").split("/")[-1].replace(".git", "")
        dest = str(CONTAINERS_DIR / repo_name)

        # 1. Clone
        st(f"📥 Клонирую {url}...")
        ok, out = run_system_cmd(
            f"git clone --depth=1 {url} {dest}", timeout=180
        )
        if not ok:
            return AgentResult(ok=False, error=f"git clone failed: {out[:300]}",
                               agent="MORPHEUS", mode="repo", duration=time.time()-t0)
        st(f"  ✅ Клонировано в {dest}")

        # 2. Analyze
        st("🔍 Анализирую репозиторий...")
        repo_info = analyze_repo(dest)
        st(f"  Тип: {repo_info['type']} | Точка входа: {repo_info.get('entry', '?')}")

        # 3. Generate or use Dockerfile
        if not repo_info["has_dockerfile"]:
            st("📝 Генерирую Dockerfile...")
            dockerfile_content = generate_dockerfile(repo_info, repo_name)
            try:
                # Ask LLM to improve Dockerfile based on README
                if repo_info["readme"]:
                    improved = self.llm(
                        f"Улучши Dockerfile для проекта:\nREADME:\n{repo_info['readme'][:800]}\n"
                        f"Текущий Dockerfile:\n{dockerfile_content}\n"
                        f"Тип проекта: {repo_info['type']}\n"
                        f"Верни ТОЛЬКО содержимое Dockerfile без markdown.",
                        max_tokens=1000
                    )
                    # Validate it looks like a Dockerfile
                    if "FROM " in improved and "CMD" in improved:
                        dockerfile_content = improved.strip()
            except Exception:
                pass

            df_path = Path(dest) / "Dockerfile"
            df_path.write_text(dockerfile_content, encoding="utf-8")
            st(f"  ✅ Dockerfile создан")
        else:
            st("  ✅ Dockerfile уже есть")

        # 4. Install deps (native, not Docker — for quick test)
        if repo_info["type"] == "python" and repo_info["deps_file"]:
            deps_file = Path(dest) / repo_info["deps_file"]
            if deps_file.exists():
                st(f"📦 Устанавливаю Python зависимости...")
                ok_deps, out_deps = run_system_cmd(
                    f"pip install -r {deps_file} --break-system-packages -q",
                    cwd=dest, timeout=300
                )
                if not ok_deps:
                    st(f"  ⚠️ Некоторые зависимости не установились — авто-фикс...")
                    self._autofix_deps(out_deps, dest, on_status)

        # 5. Build Docker image
        tag = f"morpheus/{repo_name.lower()}:latest"
        st(f"🐳 Собираю Docker образ {tag}...")
        ok_build, out_build = docker_build(dest, tag, on_status)
        if not ok_build:
            st(f"  ⚠️ Ошибка сборки, пробую авто-фикс...")
            # Auto-fix: install missing deps and retry
            missing = _detect_missing_dep(out_build)
            if missing:
                ok_fix, fix_msg = _auto_install_dep(missing, out_build, on_status)
                if ok_fix:
                    st(f"  ✅ Зависимость {missing} установлена, пересобираю...")
                    ok_build, out_build = docker_build(dest, tag, on_status)

        summary = [
            f"📁 Репозиторий: {url}",
            f"📂 Путь: {dest}",
            f"🔎 Тип: {repo_info['type']}",
            f"📌 Точка входа: {repo_info.get('entry', 'не определена')}",
            f"🐳 Образ: {tag} — {'✅ собран' if ok_build else '❌ ошибка сборки'}",
        ]
        if not ok_build:
            summary.append(f"```\n{out_build[-500:]}\n```")

        answer = "\n".join(summary)
        return AgentResult(
            ok=ok_build,
            answer=answer,
            agent="MORPHEUS",
            mode="repo",
            duration=time.time() - t0,
            files=[dest],
        )

    # ──────────────────────────────────────────────────────────────────────────
    #  AUTOFIX режим — авто-фикс зависимостей
    # ──────────────────────────────────────────────────────────────────────────
    def _handle_autofix(self, task, chat_id, on_status, t0) -> AgentResult:
        def st(m): self.status(m)
        st("🔁 Запускаю авто-фикс зависимостей...")

        fixed = self._autofix_deps(task, "/", on_status)
        answer = "🔁 **Авто-фикс зависимостей:**\n" + "\n".join(fixed)
        return AgentResult(ok=bool(fixed), answer=answer, agent="MORPHEUS",
                           mode="fix", duration=time.time()-t0)

    def _autofix_deps(self, error_output: str, cwd: str, on_status: Callable) -> List[str]:
        """Run auto-fix loop: detect missing dep → install → verify."""
        def st(m): self.status(m)
        fixed = []
        for attempt in range(MAX_AUTOFIX):
            pkg = _detect_missing_dep(error_output)
            if not pkg:
                break
            st(f"  🔁 Фикс {attempt+1}/{MAX_AUTOFIX}: {pkg}")
            ok, msg = _auto_install_dep(pkg, error_output, on_status)
            fixed.append(f"{'✅' if ok else '❌'} {pkg}: {msg}")
            if not ok:
                break
            # Re-run last command to check if error persists
            if "requirements.txt" in error_output:
                req = Path(cwd) / "requirements.txt"
                if req.exists():
                    ok2, error_output = run_system_cmd(
                        f"pip install -r {req} --break-system-packages -q",
                        cwd=cwd, timeout=180
                    )
                    if ok2:
                        fixed.append("✅ requirements.txt установлен полностью")
                        break
            else:
                break
        return fixed

    # ──────────────────────────────────────────────────────────────────────────
    #  PLAN EXECUTOR — выполняет JSON план
    # ──────────────────────────────────────────────────────────────────────────
    def _execute_plan(self, plan: dict, task: str, on_status: Callable, t0: float) -> AgentResult:
        def st(m): self.status(m)

        steps     = plan.get("steps", [])
        results   = []
        all_ok    = True
        all_files = []
        prev_output = ""

        st(f"📋 Выполняю план: {len(steps)} шагов")

        for step in steps:
            sid  = step.get("id", 0)
            desc = step.get("description", "")
            tool = step.get("tool", "shell")
            cmd  = step.get("cmd", "")
            inp  = step.get("inputs", {})
            crit = step.get("critical", True)

            # Inject previous output
            if "{prev_output}" in cmd:
                cmd = cmd.replace("{prev_output}", prev_output[:200])

            st(f"[{sid}/{len(steps)}] {desc[:60]}")

            if not cmd:
                # Synthesize command from tool + inputs
                cmd = self._build_cmd(tool, inp, desc)

            if not cmd:
                st(f"  ⚠️ Нет команды для шага {sid}")
                continue

            # Execute
            blocked, reason = _is_blacklisted(cmd)
            if blocked:
                results.append(f"🚫 Шаг {sid} заблокирован: {reason}")
                if crit:
                    all_ok = False
                    break
                continue

            timeout = DOCKER_TIMEOUT if tool.startswith("docker") else CMD_TIMEOUT
            ok, out = run_system_cmd(cmd, timeout=timeout)
            prev_output = out[:500]

            if ok:
                st(f"  ✅ {out[:80]}")
                results.append(f"✅ Шаг {sid} ({desc[:40]}): {out[:200]}")
            else:
                st(f"  ❌ {out[:100]}")
                # Auto-fix if dependency error
                pkg = _detect_missing_dep(out)
                if pkg:
                    st(f"  🔁 Авто-фикс: {pkg}")
                    fix_ok, fix_msg = _auto_install_dep(pkg, out, on_status)
                    if fix_ok:
                        # Retry step
                        ok2, out2 = run_system_cmd(cmd, timeout=timeout)
                        if ok2:
                            st(f"  ✅ Шаг {sid} исправлен и выполнен")
                            results.append(f"✅ Шаг {sid} (авто-фикс {pkg}): {out2[:200]}")
                            prev_output = out2[:500]
                            continue
                results.append(f"❌ Шаг {sid} ({desc[:40]}): {out[:300]}")
                if crit:
                    all_ok = False

        answer = plan.get("summary", task[:80]) + "\n\n" + "\n".join(results)
        return AgentResult(
            ok=all_ok,
            answer=answer,
            agent="MORPHEUS",
            mode="shell",
            files=all_files,
            duration=time.time() - t0,
        )

    def _build_cmd(self, tool: str, inputs: dict, desc: str) -> str:
        """Build shell command from tool name and inputs."""
        if tool == "apt":
            pkg = inputs.get("package", inputs.get("packages", ""))
            return f"apt-get update -qq && apt-get install -y {pkg} -qq" if pkg else ""
        elif tool == "pip":
            pkg = inputs.get("package", inputs.get("packages", ""))
            return f"pip install {pkg} --break-system-packages -q" if pkg else ""
        elif tool == "git_clone":
            url = inputs.get("url", "")
            dest = inputs.get("dest", str(CONTAINERS_DIR / url.split("/")[-1].replace(".git","")))
            return f"git clone --depth=1 {url} {dest}" if url else ""
        elif tool == "docker_build":
            path = inputs.get("path", ".")
            tag  = inputs.get("tag", "morpheus/app:latest")
            return f"docker build -t {tag} {path}"
        elif tool == "docker_run":
            image = inputs.get("image", "")
            name  = inputs.get("name", "")
            ports = inputs.get("ports", "")
            nc = f"--name {name}" if name else ""
            pc = f"-p {ports}" if ports else ""
            return f"docker run -d {nc} {pc} {image}".strip() if image else ""
        elif tool == "docker_exec":
            container = inputs.get("container", "")
            cmd = inputs.get("cmd", "")
            return f"docker exec {container} sh -c {repr(cmd)}" if container and cmd else ""
        elif tool in ("shell", "bash"):
            return inputs.get("cmd", inputs.get("command", ""))
        return ""
