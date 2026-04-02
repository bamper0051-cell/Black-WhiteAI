"""
remote_control.py — BlackBugsAI Remote Control Module
Безопасное управление своим сервером через Telegram и Admin Panel

Функции:
  • Shell-терминал (с whitelist команд + GOD bypass)
  • Мониторинг процессов и ресурсов (psutil)
  • Управление Docker-контейнерами
  • Интерактивный PTY для отладки (локальный reverse shell)
"""
from __future__ import annotations
import os, sys, re, time, json, subprocess, threading, queue, pty, select
from pathlib import Path
from typing import Optional, Callable

BASE_DIR = Path(__file__).parent

# ══════════════════════════════════════════════════════════════════════════════
#  Конфигурация безопасности
# ══════════════════════════════════════════════════════════════════════════════

# Команды разрешены без ограничений для всех ADM+
SHELL_WHITELIST_PATTERNS = [
    r'^ls\b', r'^pwd$', r'^cat\s', r'^echo\b', r'^grep\b', r'^find\b',
    r'^ps\b', r'^top\b', r'^df\b', r'^du\b', r'^free\b', r'^uname\b',
    r'^whoami$', r'^id$', r'^env$', r'^which\b', r'^type\b', r'^date$',
    r'^uptime$', r'^hostname$', r'^netstat\b', r'^ss\b', r'^ip\b',
    r'^curl\b', r'^wget\b', r'^ping\b', r'^nslookup\b', r'^dig\b',
    r'^python3?\b', r'^pip\b', r'^git\b',
    r'^docker\b', r'^docker-compose\b',
    r'^systemctl\b', r'^journalctl\b', r'^service\b',
    r'^tail\b', r'^head\b', r'^wc\b', r'^sort\b', r'^uniq\b', r'^awk\b',
    r'^sed\b', r'^cut\b', r'^tr\b', r'^tee\b',
    r'^mkdir\b', r'^touch\b', r'^cp\b', r'^mv\b', r'^rm\b',
    r'^chmod\b', r'^chown\b',
    r'^kill\b', r'^pkill\b',
    r'^nano\b', r'^vi\b', r'^vim\b',
]

# Команды запрещены явно (даже для ADM)
SHELL_BLACKLIST = [
    'rm -rf /', 'mkfs', 'dd if=/dev/zero', ':(){:|:&};:',
    'chmod 777 /', '> /dev/sda', 'fork bomb',
]

def _dec(b) -> str:
    if not b: return ""
    if isinstance(b, str): return b
    for enc in ("utf-8", "cp1251", "cp866", "latin-1"):
        try: return b.decode(enc)
        except: pass
    return b.decode("utf-8", errors="replace")


def check_command_allowed(cmd: str, is_god: bool = False) -> tuple[bool, str]:
    """Проверяет разрешена ли команда. Возвращает (allowed, reason)."""
    cmd_strip = cmd.strip()
    if not cmd_strip:
        return False, "Пустая команда"

    # GOD может всё (кроме явно деструктивного)
    for blocked in SHELL_BLACKLIST:
        if blocked in cmd_strip.lower():
            return False, f"Команда заблокирована: содержит '{blocked}'"

    if is_god:
        return True, ""

    # ADM/VIP — только whitelist
    for pattern in SHELL_WHITELIST_PATTERNS:
        if re.match(pattern, cmd_strip, re.IGNORECASE):
            return True, ""

    return False, f"Команда не в whitelist. GOD-аккаунт может выполнять любые команды."


# ══════════════════════════════════════════════════════════════════════════════
#  Shell Executor
# ══════════════════════════════════════════════════════════════════════════════

# Активные shell-сессии: chat_id -> ShellSession
_sessions: dict[str, "ShellSession"] = {}
_sessions_lock = threading.Lock()


class ShellSession:
    """Интерактивная shell-сессия через PTY."""

    def __init__(self, chat_id: str):
        self.chat_id = chat_id
        self.cwd = str(BASE_DIR)
        self.env = {**os.environ, "TERM": "xterm-256color", "COLUMNS": "80", "LINES": "24"}
        self.output_queue: queue.Queue = queue.Queue()
        self.created = time.time()
        self.last_used = time.time()
        self._proc = None

    def run(self, cmd: str, timeout: int = 30) -> tuple[bool, str]:
        """Выполняет команду, возвращает (ok, output)."""
        self.last_used = time.time()

        # cd — меняем рабочую директорию
        if cmd.strip().startswith("cd "):
            new_dir = cmd.strip()[3:].strip().strip('"').strip("'")
            if new_dir == "~" or not new_dir:
                new_dir = str(Path.home())
            elif not os.path.isabs(new_dir):
                new_dir = str(Path(self.cwd) / new_dir)
            if os.path.isdir(new_dir):
                self.cwd = str(Path(new_dir).resolve())
                return True, f"📁 {self.cwd}"
            return False, f"❌ Директория не найдена: {new_dir}"

        try:
            r = subprocess.run(
                cmd, shell=True,
                capture_output=True,
                timeout=timeout,
                cwd=self.cwd,
                env=self.env,
            )
            stdout = _dec(r.stdout)
            stderr = _dec(r.stderr)
            out = (stdout + stderr).strip()
            ok = r.returncode == 0

            # Лимит вывода — Telegram max
            if len(out) > 3800:
                out = out[:1800] + "\n...\n[обрезано]\n..." + out[-800:]

            return ok, out or "(нет вывода)"

        except subprocess.TimeoutExpired:
            return False, f"⏰ Таймаут {timeout}с"
        except Exception as e:
            return False, f"❌ {e}"

    def get_prompt(self) -> str:
        cwd_short = self.cwd.replace(str(Path.home()), "~")
        return f"[{cwd_short}]$ "


def get_session(chat_id: str) -> ShellSession:
    with _sessions_lock:
        if chat_id not in _sessions:
            _sessions[chat_id] = ShellSession(chat_id)
        return _sessions[chat_id]


def close_session(chat_id: str):
    with _sessions_lock:
        _sessions.pop(chat_id, None)


# ══════════════════════════════════════════════════════════════════════════════
#  System Monitor
# ══════════════════════════════════════════════════════════════════════════════

def get_system_info() -> dict:
    """Собирает информацию о системе."""
    info = {
        "cpu": None, "memory": None, "disk": None,
        "processes": [], "load": None, "uptime": None,
    }
    try:
        import psutil

        # CPU
        cpu_pct = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        info["cpu"] = {"percent": cpu_pct, "cores": cpu_count}

        # Memory
        mem = psutil.virtual_memory()
        info["memory"] = {
            "total_gb": round(mem.total / 1024**3, 1),
            "used_gb":  round(mem.used  / 1024**3, 1),
            "percent":  mem.percent,
        }

        # Disk
        disk = psutil.disk_usage('/')
        info["disk"] = {
            "total_gb": round(disk.total / 1024**3, 1),
            "used_gb":  round(disk.used  / 1024**3, 1),
            "percent":  round(disk.percent, 1),
        }

        # Top processes by CPU
        procs = []
        for p in psutil.process_iter(['pid','name','cpu_percent','memory_percent','status']):
            try:
                procs.append(p.info)
            except Exception:
                pass
        procs.sort(key=lambda x: x.get('cpu_percent') or 0, reverse=True)
        info["processes"] = procs[:10]

        # Load average
        try:
            load = os.getloadavg()
            info["load"] = {"1m": round(load[0],2), "5m": round(load[1],2), "15m": round(load[2],2)}
        except Exception:
            pass

        # Uptime
        boot = psutil.boot_time()
        uptime_sec = time.time() - boot
        h, r = divmod(int(uptime_sec), 3600)
        m, s = divmod(r, 60)
        info["uptime"] = f"{h}ч {m}м"

    except ImportError:
        # Fallback без psutil
        r = subprocess.run(["free", "-h"], capture_output=True)
        info["memory"] = {"raw": _dec(r.stdout)[:200]}
        r2 = subprocess.run(["df", "-h", "/"], capture_output=True)
        info["disk"] = {"raw": _dec(r2.stdout)[:200]}

    return info


def format_system_info(info: dict) -> str:
    """Форматирует системную информацию для Telegram."""
    lines = ["🖥 <b>Система</b>\n"]

    if info.get("uptime"):
        lines.append(f"⏱ Аптайм: {info['uptime']}")

    if info.get("cpu"):
        cpu = info["cpu"]
        bar = _bar(cpu['percent'])
        lines.append(f"🔥 CPU: {bar} {cpu['percent']}% ({cpu['cores']} ядер)")

    if info.get("memory"):
        m = info["memory"]
        if "percent" in m:
            bar = _bar(m['percent'])
            lines.append(f"💾 RAM: {bar} {m['used_gb']}/{m['total_gb']} GB ({m['percent']}%)")
        elif "raw" in m:
            lines.append(f"💾 RAM:\n{m['raw']}")

    if info.get("disk"):
        d = info["disk"]
        if "percent" in d:
            bar = _bar(d['percent'])
            lines.append(f"💿 Диск: {bar} {d['used_gb']}/{d['total_gb']} GB ({d['percent']}%)")
        elif "raw" in d:
            lines.append(f"💿 Диск:\n{d['raw']}")

    if info.get("load"):
        l = info["load"]
        lines.append(f"📊 Load: {l['1m']} / {l['5m']} / {l['15m']}")

    if info.get("processes"):
        lines.append("\n<b>Top процессы (CPU):</b>")
        for p in info["processes"][:5]:
            cpu = p.get("cpu_percent") or 0
            mem = p.get("memory_percent") or 0
            if cpu > 0.1:
                lines.append(f"  {p['name'][:20]:<20} CPU:{cpu:5.1f}% MEM:{mem:4.1f}%")

    return "\n".join(lines)


def _bar(pct: float, width: int = 10) -> str:
    filled = int(pct / 100 * width)
    return "█" * filled + "░" * (width - filled)


# ══════════════════════════════════════════════════════════════════════════════
#  Docker Manager
# ══════════════════════════════════════════════════════════════════════════════

def _docker(args: list, timeout: int = 30) -> tuple[bool, str]:
    r = subprocess.run(
        ["docker"] + args,
        capture_output=True, timeout=timeout,
    )
    out = (_dec(r.stdout) + _dec(r.stderr)).strip()
    return r.returncode == 0, out


def docker_list() -> list[dict]:
    """Список всех контейнеров."""
    ok, out = _docker(["ps", "-a", "--format",
        "{{.ID}}|{{.Names}}|{{.Status}}|{{.Image}}|{{.Ports}}"])
    if not ok:
        return []
    containers = []
    for line in out.splitlines():
        if not line.strip(): continue
        parts = line.split("|")
        if len(parts) >= 4:
            containers.append({
                "id":     parts[0][:12],
                "name":   parts[1],
                "status": parts[2],
                "image":  parts[3],
                "ports":  parts[4] if len(parts) > 4 else "",
                "running": parts[2].startswith("Up"),
            })
    return containers


def docker_action(container: str, action: str) -> tuple[bool, str]:
    """start/stop/restart/logs/inspect контейнера."""
    valid = {"start", "stop", "restart", "pause", "unpause", "rm"}
    if action not in valid and action != "logs":
        return False, f"Неизвестное действие: {action}"

    if action == "logs":
        ok, out = _docker(["logs", "--tail=50", container], timeout=15)
    elif action == "rm":
        ok, out = _docker(["rm", "-f", container])
    else:
        ok, out = _docker([action, container])

    return ok, out[:2000] if out else ("✅" if ok else "❌")


def docker_stats() -> str:
    """Статистика использования ресурсов контейнерами."""
    ok, out = _docker(["stats", "--no-stream", "--format",
        "{{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"], timeout=15)
    if not ok or not out:
        return "Docker stats недоступен"
    lines = ["<b>Docker Stats:</b>"]
    for line in out.splitlines()[:10]:
        if line.strip():
            parts = line.split("\t")
            if len(parts) >= 3:
                lines.append(f"  {parts[0]:<20} CPU:{parts[1]:<8} MEM:{parts[2]}")
    return "\n".join(lines)


def format_docker_list(containers: list) -> str:
    if not containers:
        return "🐳 Контейнеры не найдены"
    lines = ["🐳 <b>Docker контейнеры:</b>\n"]
    for c in containers:
        icon = "🟢" if c["running"] else "🔴"
        lines.append(f"{icon} <code>{c['name']}</code>")
        lines.append(f"   {c['status']}")
        if c["ports"]:
            lines.append(f"   🔌 {c['ports'][:60]}")
        lines.append("")
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
#  Интерактивный PTY (локальная отладка)
# ══════════════════════════════════════════════════════════════════════════════

_pty_sessions: dict[str, dict] = {}


def pty_start(chat_id: str, cmd: str = "/bin/bash") -> bool:
    """Запускает интерактивный PTY-процесс для отладки."""
    if chat_id in _pty_sessions:
        pty_stop(chat_id)

    try:
        master_fd, slave_fd = pty.openpty()
        proc = subprocess.Popen(
            [cmd], stdin=slave_fd, stdout=slave_fd, stderr=slave_fd,
            close_fds=True, cwd=str(BASE_DIR),
            env={**os.environ, "TERM": "xterm-256color"},
        )
        os.close(slave_fd)
        _pty_sessions[chat_id] = {
            "proc": proc, "fd": master_fd,
            "created": time.time(), "buffer": "",
        }
        return True
    except Exception as e:
        return False


def pty_write(chat_id: str, text: str) -> tuple[bool, str]:
    """Отправляет ввод в PTY."""
    sess = _pty_sessions.get(chat_id)
    if not sess:
        return False, "PTY сессия не активна"
    try:
        os.write(sess["fd"], (text + "\n").encode("utf-8"))
        time.sleep(0.3)
        output = _pty_read(sess["fd"])
        return True, output[:2000]
    except Exception as e:
        return False, str(e)


def _pty_read(fd: int, timeout: float = 1.0) -> str:
    output = b""
    deadline = time.time() + timeout
    while time.time() < deadline:
        r, _, _ = select.select([fd], [], [], 0.1)
        if r:
            try:
                chunk = os.read(fd, 4096)
                if chunk: output += chunk
                else: break
            except OSError: break
    # Убираем ANSI escape sequences
    text = _dec(output)
    text = re.sub(r'\x1b\[[0-9;]*[mKHJABCDGl]', '', text)
    text = re.sub(r'\x1b\([AB]', '', text)
    return text.strip()


def pty_stop(chat_id: str):
    sess = _pty_sessions.pop(chat_id, None)
    if sess:
        try:
            sess["proc"].terminate()
            os.close(sess["fd"])
        except Exception:
            pass


def pty_is_active(chat_id: str) -> bool:
    sess = _pty_sessions.get(chat_id)
    if not sess: return False
    return sess["proc"].poll() is None


# ══════════════════════════════════════════════════════════════════════════════
#  Cleanup старых сессий
# ══════════════════════════════════════════════════════════════════════════════

def _cleanup_loop():
    while True:
        time.sleep(300)  # каждые 5 минут
        now = time.time()
        with _sessions_lock:
            stale = [cid for cid, s in _sessions.items()
                     if now - s.last_used > 1800]  # 30 минут неактивности
            for cid in stale:
                del _sessions[cid]
        # PTY
        dead = [cid for cid, s in _pty_sessions.items()
                if s["proc"].poll() is not None]
        for cid in dead:
            pty_stop(cid)


threading.Thread(target=_cleanup_loop, daemon=True, name="rc-cleanup").start()
