"""
BlackBugsAI — Cloudflared QR Bot
Запускает cloudflared tunnel → генерирует QR → отправляет выбранным юзерам
"""
import os, re, subprocess, threading, time, tempfile
import config

_tunnel_proc = None
_tunnel_url  = None


def start_cloudflared(port: int = 8080) -> tuple[bool, str]:
    """Запускает cloudflared и возвращает (ok, url)."""
    global _tunnel_proc, _tunnel_url
    _tunnel_url = None

    if _tunnel_proc and _tunnel_proc.poll() is None:
        stop_cloudflared()

    try:
        import shutil
        cf = shutil.which('cloudflared') or 'cloudflared'
        _tunnel_proc = subprocess.Popen(
            [cf, 'tunnel', '--url', f'http://localhost:{port}'],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1
        )
    except FileNotFoundError:
        return False, "❌ cloudflared не найден. Установи: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-manage/installation/"

    # Ждём URL в stdout (до 20 сек)
    url = None
    deadline = time.time() + 20
    for line in _tunnel_proc.stdout:
        if time.time() > deadline:
            break
        m = re.search(r'https://[a-z0-9\-]+\.trycloudflare\.com', line)
        if m:
            url = m.group(0)
            _tunnel_url = url
            break

    if not url:
        return False, "❌ Не удалось получить URL от cloudflared"

    return True, url


def stop_cloudflared():
    global _tunnel_proc, _tunnel_url
    if _tunnel_proc:
        try: _tunnel_proc.terminate(); _tunnel_proc.wait(timeout=3)
        except Exception: pass
        _tunnel_proc = None
    _tunnel_url = None


def get_tunnel_url() -> str | None:
    return _tunnel_url


def generate_qr(text: str, title: str = "") -> str:
    """Генерирует QR-код, возвращает путь к PNG."""
    out = os.path.join(config.BASE_DIR, 'agent_projects', f'qr_{int(time.time())}.png')
    os.makedirs(os.path.dirname(out), exist_ok=True)

    try:
        import qrcode
        from PIL import Image, ImageDraw, ImageFont

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10, border=4
        )
        qr.add_data(text)
        qr.make(fit=True)

        # Киберпанк стиль — чёрный фон, зелёные точки
        qr_img = qr.make_image(
            fill_color="#00ff41",   # matrix green
            back_color="#0a0a0a"    # dark bg
        ).convert('RGB')

        # Добавляем заголовок если есть
        if title:
            w, h = qr_img.size
            header_h = 50
            full = Image.new('RGB', (w, h + header_h), (10, 10, 10))
            full.paste(qr_img, (0, header_h))
            draw = ImageDraw.Draw(full)
            try:
                font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 20)
            except Exception:
                font = ImageFont.load_default()
            draw.text((10, 10), f"🖤 {title}", fill="#00ff41", font=font)
            full.save(out, 'PNG')
        else:
            qr_img.save(out, 'PNG')

        return out

    except ImportError:
        # Fallback: текстовый QR через qrcode без Pillow
        try:
            import qrcode
            qr = qrcode.make(text)
            qr.save(out)
            return out
        except ImportError:
            # Последний fallback: генерим через subprocess qrencode
            r = subprocess.run(['qrencode', '-o', out, text], capture_output=True)
            if r.returncode == 0:
                return out
            raise RuntimeError("qrcode не установлен: pip install qrcode[pil]")


# ─── Обработчики в bot.py ─────────────────────────────────────────────────────

def handle_cf_qr_menu(chat_id, send_msg_fn, kb_fn, btn_fn):
    """Главное меню cloudflared QR."""
    url = get_tunnel_url()
    status = f"🟢 Активен: <code>{url}</code>" if url else "🔴 Не запущен"
    return send_msg_fn(
        f"☁️ <b>Cloudflared QR</b>\n\n"
        f"Статус: {status}\n\n"
        "Запускает туннель → генерирует QR-код → рассылает юзерам",
        chat_id,
        reply_markup=kb_fn(
            [btn_fn("🚀 Запустить туннель",    "cfqr:start"),
             btn_fn("⏹ Остановить",           "cfqr:stop")],
            [btn_fn("📱 Сгенерить QR",         "cfqr:gen_qr"),
             btn_fn("📤 Разослать QR юзерам",  "cfqr:send_users")],
            [btn_fn("🔗 Показать URL",         "cfqr:show_url"),
             btn_fn("⚙️ Порт (сейчас 8080)",  "cfqr:set_port")],
            [btn_fn("◀️ Адм. меню",            "admin")],
        )
    )
