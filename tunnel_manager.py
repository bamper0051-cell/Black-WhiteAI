"""
tunnel_manager.py — BlackBugsAI v5
Управление туннелями для Admin Panel.

Принцип:
  Fish → Cloudflare (порт 5000) — не трогаем
  Admin → bore / localtunnel / ngrok (порт 8080) — отдельный провайдер

bore уже установлен в Docker образе (/usr/local/bin/bore).
Запускаем его subprocess-ом, парсим порт из stdout.
"""
from __future__ import annotations
import os, re, subprocess, threading, time, shutil
from typing import Optional

# ── State ─────────────────────────────────────────────────────────────────────
_lock    = threading.Lock()
_proc: Optional[subprocess.Popen] = None
_url     = ""
_log     = []        # последние 50 строк лога туннеля
_status  = "stopped" # stopped | starting | running | error
_provider = ""

_LOG_MAX = 50

def _add_log(line: str):
    _log.append(line.rstrip())
    if len(_log) > _LOG_MAX:
        _log.pop(0)


# ══════════════════════════════════════════════════════════════════════════════
#  BORE  (установлен в /usr/local/bin/bore, нет аккаунта не нужно)
#  URL формат: http://bore.pub:PORT   (TCP туннель, без HTTPS)
# ══════════════════════════════════════════════════════════════════════════════

def _start_bore(port: int = 8080, server: str = "bore.pub") -> bool:
    global _proc, _url, _status, _provider
    bore = shutil.which("bore") or "/usr/local/bin/bore"
    if not os.path.exists(bore):
        _add_log("❌ bore не найден — пересобери Docker образ")
        _status = "error"
        return False

    cmd = [bore, "local", str(port), "--to", server]
    _add_log(f"▶ {' '.join(cmd)}")
    _proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True, bufsize=1,
    )
    _status = "starting"
    _provider = "bore"

    def _reader():
        global _url, _status
        for line in _proc.stdout:
            _add_log(line.rstrip())
            # INFO  Listening at bore.pub:XXXXX
            m = re.search(r"bore\.pub:(\d+)", line)
            if m:
                _url = f"http://bore.pub:{m.group(1)}"
                _status = "running"
                _add_log(f"✅ Admin Panel: {_url}/panel")
        if _status != "stopped":
            _status = "error"
            _add_log("⚠️ bore завершился")

    threading.Thread(target=_reader, daemon=True, name="bore-reader").start()
    return True


# ══════════════════════════════════════════════════════════════════════════════
#  LOCALTUNNEL  (npm lt — без аккаунта, HTTPS, случайный субдомен)
#  pip недоступен для lt, но можно через npx или установить node/lt
# ══════════════════════════════════════════════════════════════════════════════

def _start_localtunnel(port: int = 8080) -> bool:
    global _proc, _url, _status, _provider
    # Попробуем установить через pip (есть localtunnel python обёртка)
    # Или через npx если node есть
    npx = shutil.which("npx")
    lt  = shutil.which("lt")

    if not npx and not lt:
        _add_log("📦 Устанавливаю localtunnel...")
        r = subprocess.run(
            ["npm", "install", "-g", "localtunnel"],
            capture_output=True, timeout=120
        )
        lt = shutil.which("lt")
        if not lt:
            _add_log("❌ npm/lt недоступен")
            _status = "error"
            return False

    cmd = (["lt", "--port", str(port)] if lt else
           ["npx", "localtunnel", "--port", str(port)])
    _add_log(f"▶ {' '.join(cmd)}")
    _proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True, bufsize=1,
    )
    _status = "starting"
    _provider = "localtunnel"

    def _reader():
        global _url, _status
        for line in _proc.stdout:
            _add_log(line.rstrip())
            # your url is: https://xxx.loca.lt
            m = re.search(r"https://[a-z0-9\-]+\.loca\.lt", line)
            if m:
                _url = m.group(0)
                _status = "running"
                _add_log(f"✅ Admin Panel: {_url}/panel")
        if _status != "stopped":
            _status = "error"
            _add_log("⚠️ localtunnel завершился")

    threading.Thread(target=_reader, daemon=True, name="lt-reader").start()
    return True


# ══════════════════════════════════════════════════════════════════════════════
#  CLOUDFLARED  — только если fish не использует его на том же порте
#  Используем на порте 8080 (fish — на 5000, конфликта нет)
# ══════════════════════════════════════════════════════════════════════════════

def _start_cloudflared(port: int = 8080) -> bool:
    global _proc, _url, _status, _provider
    cf = shutil.which("cloudflared") or "/usr/local/bin/cloudflared"
    if not os.path.exists(cf):
        _add_log("❌ cloudflared не найден")
        _status = "error"
        return False

    cmd = [cf, "tunnel", "--url", f"http://localhost:{port}", "--no-autoupdate"]
    _add_log(f"▶ {' '.join(cmd)}")
    _proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True, bufsize=1,
    )
    _status = "starting"
    _provider = "cloudflared"

    def _reader():
        global _url, _status
        for line in _proc.stdout:
            _add_log(line.rstrip())
            m = re.search(r"https://[a-z0-9\-]+\.trycloudflare\.com", line)
            if m:
                _url = m.group(0)
                _status = "running"
                _add_log(f"✅ Admin Panel: {_url}/panel")
        if _status != "stopped":
            _status = "error"
            _add_log("⚠️ cloudflared завершился")

    threading.Thread(target=_reader, daemon=True, name="cf-reader").start()
    return True


# ══════════════════════════════════════════════════════════════════════════════
#  PUBLIC API
# ══════════════════════════════════════════════════════════════════════════════

def start(provider: str = "bore", port: int = 0, **kwargs) -> dict:
    """Start tunnel. provider: bore | localtunnel | cloudflared
    Port default: TUNNEL_TARGET_PORT env (80 for nginx, 8080 for direct).
    In Docker with nginx set TUNNEL_TARGET_PORT=80.
    """
    if port == 0:
        port = int(os.environ.get("TUNNEL_TARGET_PORT", os.environ.get("ADMIN_WEB_PORT", 8080)))
    global _status, _url, _log
    with _lock:
        if _proc and _proc.poll() is None:
            return {"ok": False, "error": "Туннель уже запущен", "url": _url, "status": _status}
        _url = ""
        _log = []
        _status = "starting"

    provider = provider.lower().strip()

    if provider == "bore":
        ok = _start_bore(port, kwargs.get("server", "bore.pub"))
    elif provider in ("localtunnel", "lt"):
        ok = _start_localtunnel(port)
    elif provider in ("cloudflared", "cf", "cloudflare"):
        ok = _start_cloudflared(port)
    else:
        return {"ok": False, "error": f"Неизвестный провайдер: {provider}"}

    # Ждём URL до 15 сек
    for _ in range(30):
        time.sleep(0.5)
        if _url:
            break

    return {
        "ok": ok,
        "provider": provider,
        "url": _url,
        "status": _status,
        "log": _log[-10:],
    }


def stop() -> dict:
    global _proc, _url, _status
    with _lock:
        if _proc:
            try:
                _proc.terminate()
                _proc.wait(timeout=5)
            except Exception:
                try: _proc.kill()
                except Exception: pass
            _proc = None
        _url = ""
        _status = "stopped"
        _add_log("⏹ Туннель остановлен")
    return {"ok": True, "status": "stopped"}


def status() -> dict:
    alive = _proc is not None and _proc.poll() is None
    if not alive and _status == "running":
        pass  # будет обновлено reader-треком
    return {
        "ok": True,
        "status": _status,
        "provider": _provider,
        "url": _url,
        "alive": alive,
        "log": list(_log),
    }


def available_providers() -> list:
    """Проверяет какие туннели доступны в системе."""
    providers = []
    if shutil.which("bore") or os.path.exists("/usr/local/bin/bore"):
        providers.append({"id": "bore", "name": "bore.pub", "https": False,
                          "note": "Бесплатно, без аккаунта, TCP порт (http://)"})
    if shutil.which("cloudflared") or os.path.exists("/usr/local/bin/cloudflared"):
        providers.append({"id": "cloudflared", "name": "Cloudflare Tunnel",
                          "https": True, "note": "HTTPS субдомен, но конфликтует с fish если одинаковый порт"})
    if shutil.which("lt") or shutil.which("npx"):
        providers.append({"id": "localtunnel", "name": "localtunnel.me",
                          "https": True, "note": "HTTPS субдомен, нужен npm"})
    if not providers:
        providers.append({"id": "none", "name": "Нет доступных туннелей",
                          "https": False, "note": "Пересобери Docker образ"})
    return providers
