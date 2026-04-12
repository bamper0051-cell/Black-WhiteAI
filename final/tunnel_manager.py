"""
tunnel_manager.py — BlackBugsAI v5
AUTO-PORT tunnel management.

Architecture:
  Fish (cloudflare/bore) → port auto-detected from fish_bot_state
  Admin Panel            → different tunnel provider + port

Key principle: Admin never uses the same provider+port as Fish.
"""
from __future__ import annotations
import os, re, subprocess, threading, time, shutil, socket
from typing import Optional

# ── State ─────────────────────────────────────────────────────────────────────
_lock    = threading.Lock()
_proc: Optional[subprocess.Popen] = None
_url     = ""
_log     = []
_status  = "stopped"
_provider = ""
_LOG_MAX  = 80


def _add_log(line: str):
    _log.append(line.rstrip()[:300])
    if len(_log) > _LOG_MAX:
        _log.pop(0)


def _free_port(start: int = 8080, skip: set = None) -> int:
    """Find a free TCP port starting from `start`, skipping ports in `skip`."""
    skip = skip or set()
    for port in range(start, start + 100):
        if port in skip:
            continue
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(("0.0.0.0", port))
                return port
        except OSError:
            continue
    return start  # fallback


def _fish_ports() -> set:
    """Return ports currently used by fish module tunnels."""
    ports = set()
    try:
        import fish_bot_state as fbs
        import fish_config
        ports.add(fish_config.SERVER_PORT)  # fish Flask port (default 5000)
    except Exception:
        ports.add(5000)
    return ports


def _fish_provider() -> str:
    """Return which tunnel provider fish is using (cloudflared/bore/ngrok/serveo)."""
    try:
        import fish_bot_state as fbs
        if fbs.tunnel_process and fbs.tunnel_url:
            return "cloudflared"
        if fbs.bore_process and fbs.bore_url:
            return "bore"
        if fbs.ngrok_process and fbs.ngrok_url:
            return "ngrok"
        if fbs.serveo_process and fbs.serveo_url:
            return "serveo"
    except Exception:
        pass
    return ""


def _admin_port() -> int:
    """Get admin panel port, ensuring no conflict with fish."""
    admin_env = int(os.environ.get("ADMIN_WEB_PORT", 8080))
    fish = _fish_ports()
    if admin_env not in fish:
        return admin_env
    # Port conflicts — find next free one
    alt = _free_port(8090, skip=fish)
    _add_log(f"⚠️ Port {admin_env} conflict with fish → using {alt}")
    return alt


# ══════════════════════════════════════════════════════════════════════════════
#  BORE
# ══════════════════════════════════════════════════════════════════════════════

def _start_bore(port: int, server: str = "bore.pub") -> bool:
    global _proc, _url, _status, _provider
    bore = shutil.which("bore") or "/usr/local/bin/bore"
    if not os.path.exists(bore):
        # Try to install
        _add_log("📦 bore not found — trying to install...")
        try:
            import sys
            subprocess.run([sys.executable, "-m", "pip", "install", "bore",
                            "-q", "--break-system-packages"], capture_output=True, timeout=60)
        except Exception:
            pass
        bore = shutil.which("bore") or "/usr/local/bin/bore"
    if not os.path.exists(bore):
        _add_log("❌ bore binary not found. Rebuild Docker image.")
        _status = "error"
        return False

    # Check if fish is already using bore on same server
    fish_prov = _fish_provider()
    if fish_prov == "bore":
        _add_log(f"ℹ️ Fish uses bore too — both can coexist (different random ports on bore.pub)")

    cmd = [bore, "local", str(port), "--to", server]
    _add_log(f"▶ {' '.join(cmd)}")
    try:
        _proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, text=True, bufsize=1)
    except Exception as e:
        _add_log(f"❌ Failed to start bore: {e}")
        _status = "error"
        return False

    _status = "starting"
    _provider = "bore"

    def _reader():
        global _url, _status
        try:
            for line in _proc.stdout:
                _add_log(line.rstrip())
                m = re.search(r"bore\.pub:(\d+)", line)
                if not m:
                    m = re.search(r"listening at ([^\s]+:\d+)", line, re.IGNORECASE)
                if m:
                    port_str = m.group(1) if ":" not in m.group(1) else m.group(1).split(":")[-1]
                    _url = f"http://{server}:{port_str}"
                    _status = "running"
                    _add_log(f"✅ Admin Panel URL: {_url}/panel")
        except Exception:
            pass
        if _status not in ("stopped", "running"):
            _status = "error"
            _add_log("⚠️ bore exited unexpectedly")

    threading.Thread(target=_reader, daemon=True, name="bore-admin").start()
    return True


# ══════════════════════════════════════════════════════════════════════════════
#  CLOUDFLARED (separate from fish — fish uses port 5000, admin uses 8080)
# ══════════════════════════════════════════════════════════════════════════════

def _start_cloudflared(port: int) -> bool:
    global _proc, _url, _status, _provider
    cf = shutil.which("cloudflared") or "/usr/local/bin/cloudflared"
    if not os.path.exists(cf):
        _add_log("❌ cloudflared not found")
        _status = "error"
        return False

    fish_prov = _fish_provider()
    if fish_prov == "cloudflared":
        _add_log("⚠️ Fish already uses cloudflared. Both Quick Tunnels may conflict.")
        _add_log("   Recommendation: use bore for admin instead.")

    cmd = [cf, "tunnel", "--url", f"http://localhost:{port}", "--no-autoupdate"]
    _add_log(f"▶ {' '.join(cmd)}")
    try:
        _proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, text=True, bufsize=1)
    except Exception as e:
        _add_log(f"❌ {e}")
        _status = "error"
        return False

    _status = "starting"
    _provider = "cloudflared"

    def _reader():
        global _url, _status
        try:
            for line in _proc.stdout:
                _add_log(line.rstrip())
                m = re.search(r"https://[a-z0-9\-]+\.trycloudflare\.com", line)
                if m:
                    _url = m.group(0)
                    _status = "running"
                    _add_log(f"✅ Admin Panel URL: {_url}/panel")
        except Exception:
            pass
        if _status not in ("stopped", "running"):
            _status = "error"

    threading.Thread(target=_reader, daemon=True, name="cf-admin").start()
    return True


# ══════════════════════════════════════════════════════════════════════════════
#  LOCALTUNNEL
# ══════════════════════════════════════════════════════════════════════════════

def _start_localtunnel(port: int) -> bool:
    global _proc, _url, _status, _provider
    lt = shutil.which("lt") or shutil.which("localtunnel")
    npx = shutil.which("npx")

    if not lt and not npx:
        _add_log("📦 Installing localtunnel via npm...")
        try:
            r = subprocess.run(["npm", "install", "-g", "localtunnel"],
                               capture_output=True, timeout=120)
            lt = shutil.which("lt")
        except Exception:
            pass

    if not lt and not npx:
        _add_log("❌ npm/lt not available")
        _status = "error"
        return False

    cmd = [lt, "--port", str(port)] if lt else ["npx", "localtunnel", "--port", str(port)]
    _add_log(f"▶ {' '.join(cmd)}")
    try:
        _proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, text=True, bufsize=1)
    except Exception as e:
        _add_log(f"❌ {e}")
        _status = "error"
        return False

    _status = "starting"
    _provider = "localtunnel"

    def _reader():
        global _url, _status
        try:
            for line in _proc.stdout:
                _add_log(line.rstrip())
                m = re.search(r"https://[a-z0-9\-]+\.loca\.lt", line)
                if m:
                    _url = m.group(0)
                    _status = "running"
                    _add_log(f"✅ Admin Panel URL: {_url}/panel")
        except Exception:
            pass
        if _status not in ("stopped", "running"):
            _status = "error"

    threading.Thread(target=_reader, daemon=True, name="lt-admin").start()
    return True


# ══════════════════════════════════════════════════════════════════════════════
#  PUBLIC API
# ══════════════════════════════════════════════════════════════════════════════

def start(provider: str = "bore", port: int = 0, **kwargs) -> dict:
    """
    Start admin tunnel.
    provider: bore | cloudflared | localtunnel
    port: 0 = auto-detect (avoids conflict with fish)
    """
    global _status, _url, _log
    with _lock:
        if _proc and _proc.poll() is None:
            return {"ok": False, "error": "Tunnel already running", "url": _url, "status": _status}
        _url = ""
        _log = []
        _status = "starting"

    # Auto-detect port
    if not port:
        port = _admin_port()

    _add_log(f"🚀 Starting {provider} tunnel on port {port}")
    _add_log(f"   Fish tunnel provider: {_fish_provider() or 'none'}")
    _add_log(f"   Fish ports: {_fish_ports()}")

    provider = provider.lower().strip()
    if provider == "bore":
        ok = _start_bore(port, kwargs.get("server", "bore.pub"))
    elif provider in ("cloudflared", "cf", "cloudflare"):
        ok = _start_cloudflared(port)
    elif provider in ("localtunnel", "lt"):
        ok = _start_localtunnel(port)
    else:
        return {"ok": False, "error": f"Unknown provider: {provider}"}

    # Wait for URL up to 15s
    for _ in range(30):
        time.sleep(0.5)
        if _url:
            break

    return {"ok": ok and bool(_url), "provider": provider, "port": port,
            "url": _url, "status": _status, "log": _log[-15:]}


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
        _add_log("⏹ Tunnel stopped")
    return {"ok": True, "status": "stopped"}


def status() -> dict:
    alive = _proc is not None and _proc.poll() is None
    return {"ok": True, "status": _status, "provider": _provider,
            "url": _url, "alive": alive, "log": list(_log),
            "fish_provider": _fish_provider(), "fish_ports": list(_fish_ports())}


def available_providers() -> list:
    fish_prov = _fish_provider()
    providers = []

    bore_ok = bool(shutil.which("bore") or os.path.exists("/usr/local/bin/bore"))
    providers.append({
        "id": "bore", "name": "bore.pub",
        "https": False, "available": bore_ok,
        "recommended": True,
        "note": "Pre-installed · No account · No conflict with Cloudflare fish tunnel"
              + (" ⚠️ fish also uses bore (different ports, OK)" if fish_prov == "bore" else ""),
    })

    cf_ok = bool(shutil.which("cloudflared") or os.path.exists("/usr/local/bin/cloudflared"))
    providers.append({
        "id": "cloudflared", "name": "Cloudflare Tunnel",
        "https": True, "available": cf_ok,
        "recommended": fish_prov != "cloudflared",
        "note": "HTTPS · No account" + (" ⚠️ Fish already uses Cloudflare — may conflict!" if fish_prov == "cloudflared" else ""),
    })

    lt_ok = bool(shutil.which("lt") or shutil.which("npx"))
    providers.append({
        "id": "localtunnel", "name": "localtunnel.me",
        "https": True, "available": lt_ok,
        "recommended": False,
        "note": "HTTPS · Needs npm · No conflict with Cloudflare",
    })

    return providers
