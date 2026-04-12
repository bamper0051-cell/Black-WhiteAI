"""
BlackBugsAI — Shell Tool
Безопасное выполнение shell-команд с:
  • allowlist команд
  • таймаутом
  • Windows/Linux совместимостью
  • изоляцией вывода
"""
import os, subprocess, platform, re
import config

# Команды разрешённые без прав admin
SAFE_COMMANDS = frozenset([
    'ls','dir','pwd','echo','cat','head','tail','grep','find','wc',
    'python','python3','pip','pip3','node','npm',
    'ffmpeg','ffprobe','bore','cloudflared',
    'df','du','free','uptime','ps','top','htop',
    'curl','wget','ping','nslookup',
    'git','zip','unzip','tar',
])

def is_safe(cmd: str) -> bool:
    """Проверяет безопасность команды."""
    base = cmd.strip().split()[0].lower() if cmd.strip() else ''
    # Убираем путь если есть
    base = os.path.basename(base)
    return base in SAFE_COMMANDS

def run(cmd: str, timeout: int = 30, cwd: str = None,
        role: str = 'user') -> tuple[bool, str]:
    """
    Выполняет shell-команду.
    role='user'  → только SAFE_COMMANDS
    role='admin' → любые команды
    """
    if not cmd.strip():
        return False, "❌ Пустая команда"

    if role == 'user' and not is_safe(cmd):
        base = cmd.strip().split()[0]
        return False, (f"🚫 Команда <code>{base}</code> заблокирована.\n"
                       f"Разрешены: {', '.join(sorted(SAFE_COMMANDS))}")

    cwd = cwd or config.BASE_DIR
    is_win = platform.system() == 'Windows'

    def _decode(b: bytes) -> str:
        for enc in (['cp866','cp1251','utf-8','latin-1'] if is_win else ['utf-8','latin-1']):
            try: return b.decode(enc)
            except: pass
        return b.decode('utf-8', errors='replace')

    try:
        r = subprocess.run(
            cmd, shell=True, cwd=cwd, timeout=timeout,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        stdout = _decode(r.stdout) if r.stdout else ''
        stderr = _decode(r.stderr) if r.stderr else ''
        out = ((stdout or '') + (stderr or '')).strip()
        return r.returncode == 0, out[:3000] or '(нет вывода)'
    except subprocess.TimeoutExpired:
        return False, f"⏰ Таймаут {timeout}с"
    except Exception as e:
        return False, f"❌ {e}"
