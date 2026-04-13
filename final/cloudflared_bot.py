"""
BlackBugsAI — Cloudflared QR Bot
Запускает cloudflared tunnel → получает URL → генерирует QR → отправляет выбранным юзерам
"""
import os, sys, time, subprocess, threading, re, tempfile
import config

# QR генерация (встроенная — без зависимостей)
def _qr_ascii(text: str) -> str:
    """Генерирует ASCII QR через qrcode если есть, иначе fallback."""
    try:
        import qrcode, io
        qr = qrcode.QRCode(border=1, box_size=1)
        qr.add_data(text)
        qr.make(fit=True)
        f = io.StringIO()
        qr.print_ascii(out=f)
        return f.getvalue()
    except ImportError:
        return None

def _qr_image(text: str, out_path: str) -> bool:
    """Сохраняет QR как PNG."""
    try:
        import qrcode
        img = qrcode.make(text)
        img.save(out_path)
        return True
    except ImportError:
        return False


class CloudflaredQRBot:
    def __init__(self):
        self._process = None
        self._url     = None
        self._lock    = threading.Lock()
        self._qr_path = os.path.join(config.BASE_DIR, 'cloudflared_qr.png')

    @property
    def is_running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    @property
    def url(self) -> str | None:
        return self._url

    def start(self, port: int = 5000, on_status=None) -> tuple[bool, str]:
        """Запускает cloudflared и получает URL."""
        if self.is_running:
            return True, self._url or "already running"

        # Проверяем наличие cloudflared
        import shutil
        cf = shutil.which('cloudflared')
        if not cf:
            return False, "cloudflared не найден. Установи: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-update/"

        if on_status: on_status("🌐 Запускаю cloudflared...")

        try:
            self._process = subprocess.Popen(
                [cf, 'tunnel', '--url', f'http://localhost:{port}'],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
        except Exception as e:
            return False, f"Ошибка запуска: {e}"

        # Ждём URL из вывода
        url = None
        deadline = time.time() + 30
        for line in self._process.stdout:
            if time.time() > deadline:
                break
            if on_status: on_status(f"⏳ {line.strip()[:60]}")
            m = re.search(r'https://[a-zA-Z0-9\-]+\.trycloudflare\.com', line)
            if m:
                url = m.group(0)
                break

        if not url:
            self.stop()
            return False, "Не удалось получить URL от cloudflared за 30с"

        self._url = url
        if on_status: on_status(f"✅ Tunnel: {url}")
        return True, url

    def stop(self):
        """Останавливает туннель."""
        if self._process:
            try: self._process.terminate()
            except Exception: pass
            self._process = None
        self._url = None

    def generate_qr(self) -> tuple[bool, str]:
        """Генерирует QR-код для текущего URL."""
        if not self._url:
            return False, "Туннель не запущен"
        ok = _qr_image(self._url, self._qr_path)
        if ok:
            return True, self._qr_path
        return False, "qrcode не установлен: pip install qrcode[pil]"

    def get_qr_ascii(self) -> str | None:
        """ASCII QR для отображения в чате."""
        if not self._url:
            return None
        return _qr_ascii(self._url)

    def status_text(self) -> str:
        if self.is_running:
            return (f"🟢 <b>Tunnel активен</b>\n"
                    f"🔗 <code>{self._url}</code>")
        return "🔴 Tunnel остановлен"


# Глобальный экземпляр
cf_bot = CloudflaredQRBot()


# ─── Telegram-интеграция ─────────────────────────────────────────────────────

def handle_cloudflared_command(chat_id, port: int = 5000):
    """
    Вызывается из bot.py по команде /cloudflared или кнопке.
    Запускает tunnel → создаёт QR → предлагает выбрать юзеров для отправки.
    """
    from telegram_client import send_message, send_document, edit_message
    from auth_module import get_all_users

    send_message("🌐 <b>Cloudflared Tunnel</b>\n\nЗапускаю...", chat_id)

    status_msgs = []
    def on_status(m):
        send_message(m, chat_id)

    ok, result = cf_bot.start(port=port, on_status=on_status)

    if not ok:
        send_message(f"❌ <b>Ошибка:</b>\n{result}", chat_id)
        return

    url = result
    send_message(f"✅ <b>Tunnel активен</b>\n\n🔗 <code>{url}</code>", chat_id)

    # Генерируем QR
    send_message("📸 Генерирую QR-код...", chat_id)
    qr_ok, qr_path = cf_bot.generate_qr()

    if qr_ok:
        send_document(qr_path, caption=f"📱 QR для {url}", chat_id=chat_id)
    else:
        # ASCII fallback
        ascii_qr = cf_bot.get_qr_ascii()
        if ascii_qr:
            send_message(f"📱 <b>QR (ASCII):</b>\n<pre>{ascii_qr[:1000]}</pre>", chat_id)
        else:
            send_message(f"⚠️ QR не сгенерирован. Ссылка:\n<code>{url}</code>", chat_id)

    # Список юзеров для отправки
    users = [u for u in get_all_users()
             if u.get('status') == 'active' and u.get('privilege') != 'banned']

    if not users:
        send_message("ℹ️ Нет активных пользователей для отправки", chat_id)
        return

    # Строим клавиатуру выбора юзеров
    from bot import kb, btn
    rows = []
    for u in users[:20]:  # макс 20 юзеров
        uid   = u['telegram_id']
        name  = u.get('first_name') or u.get('username') or str(uid)
        icon  = {'owner':'👑','admin':'🔑','vip':'💎'}.get(u.get('privilege',''), '👤')
        rows.append([btn(f"{icon} {name}", f"cf_send:{uid}")])
    rows.append([btn("📣 Отправить ВСЕМ", "cf_send:all")])
    rows.append([btn("🛑 Остановить tunnel", "cf_stop")])

    send_message(
        f"👥 <b>Кому отправить QR?</b>\n"
        f"Выбери пользователей:",
        chat_id,
        reply_markup=kb(*rows)
    )


def send_qr_to_user(target_id: int, sender_id: int):
    """Отправляет QR конкретному пользователю."""
    from telegram_client import send_message, send_document

    if not cf_bot.url:
        send_message("❌ Tunnel не запущен", sender_id)
        return

    url = cf_bot.url
    qr_ok, qr_path = cf_bot.generate_qr()

    msg = (f"📱 <b>BlackBugsAI — Доступ</b>\n\n"
           f"🔗 <code>{url}</code>\n\n"
           f"Отсканируй QR или перейди по ссылке")

    if qr_ok and os.path.exists(qr_path):
        send_document(qr_path, caption=msg, chat_id=target_id)
    else:
        send_message(msg, target_id)


def send_qr_to_all(sender_id: int):
    """Отправляет QR всем активным пользователям."""
    from auth_module import get_all_users
    users = [u for u in get_all_users()
             if u.get('status') == 'active' and str(u['telegram_id']) != str(sender_id)]
    sent = 0
    for u in users:
        try:
            send_qr_to_user(u['telegram_id'], sender_id)
            sent += 1
            time.sleep(0.1)
        except Exception:
            pass
    from telegram_client import send_message
    send_message(f"✅ QR отправлен {sent} пользователям", sender_id)
