"""
CloudflareQR Bot — запускает cloudflared, захватывает QR/URL, рассылает выбранным юзерам
Команды: /qr — запустить, выбрать юзеров, отправить QR
"""
import os, sys, re, time, subprocess, threading, tempfile
import config

try:
    import qrcode
    QR_ENABLED = True
except ImportError:
    QR_ENABLED = False

from telegram_client import send_message, send_document, get_updates, answer_callback
from auth_module import get_all_users, PRIVILEGE_ICONS

_tunnel_proc = None
_tunnel_url  = None
_tunnel_lock = threading.Lock()


def _start_cloudflared(port: int = 5000) -> tuple[bool, str]:
    """Запускает cloudflared и ждёт URL."""
    global _tunnel_proc, _tunnel_url
    import shutil

    cf = shutil.which('cloudflared') or shutil.which('cloudflared.exe')
    if not cf:
        return False, "cloudflared не найден"

    with _tunnel_lock:
        if _tunnel_proc and _tunnel_proc.poll() is None:
            _tunnel_proc.terminate()
            time.sleep(1)

        proc = subprocess.Popen(
            [cf, 'tunnel', '--url', f'http://localhost:{port}'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, bufsize=1
        )
        _tunnel_proc = proc

    # Ждём URL (до 30 сек)
    url = None
    deadline = time.time() + 30
    while time.time() < deadline:
        line = proc.stderr.readline()
        m = re.search(r'https://[\w\-]+\.trycloudflare\.com', line)
        if m:
            url = m.group()
            break
        if proc.poll() is not None:
            break
        time.sleep(0.2)

    if url:
        _tunnel_url = url
        return True, url
    return False, "URL не получен за 30с"


def _make_qr(url: str) -> str:
    """Генерирует QR-код и сохраняет как PNG. Возвращает путь."""
    out = os.path.join(config.BASE_DIR, 'agent_projects', f'qr_{int(time.time())}.png')
    os.makedirs(os.path.dirname(out), exist_ok=True)

    if QR_ENABLED:
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(out)
        return out

    # Fallback: ASCII QR через qrcode CLI
    try:
        r = subprocess.run(['qr', url], capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            with open(out.replace('.png', '.txt'), 'w') as f:
                f.write(r.stdout)
            return out.replace('.png', '.txt')
    except Exception:
        pass

    # Fallback: текстовый файл с URL
    txt = out.replace('.png', '.txt')
    open(txt, 'w').write(f"URL: {url}\n\nУстанови qrcode: pip install qrcode[pil]")
    return txt


def _user_select_keyboard(users: list, selected: set) -> dict:
    """Клавиатура выбора пользователей для рассылки."""
    rows = []
    for u in users[:20]:
        tid  = u['telegram_id']
        name = u.get('username') or u.get('first_name') or str(tid)
        icon = PRIVILEGE_ICONS.get(u.get('privilege', 'user'), '👤')
        mark = "✅ " if tid in selected else ""
        rows.append([{"text": f"{mark}{icon} {name}",
                      "callback_data": f"cfqr_sel:{tid}"}])
    rows.append([
        {"text": "✅ Выбрать всех", "callback_data": "cfqr_all"},
        {"text": "❌ Снять всех",   "callback_data": "cfqr_none"},
    ])
    rows.append([{"text": "📤 Отправить выбранным", "callback_data": "cfqr_send"}])
    rows.append([{"text": "🔄 Новый тоннель",      "callback_data": "cfqr_new"},
                 {"text": "◀️ Отмена",             "callback_data": "cfqr_cancel"}])
    return {"inline_keyboard": rows}


# ── Состояние бота ────────────────────────────────────────────────────────────
_state = {}   # chat_id -> {url, qr_path, selected: set}


def handle_qr_command(chat_id: int, port: int = 5000):
    """Обрабатывает команду /qr — запускает тоннель."""
    send_message("🌐 Запускаю cloudflared тоннель...", chat_id)
    ok, result = _start_cloudflared(port)
    if not ok:
        send_message(f"❌ Ошибка: {result}", chat_id); return

    url = result
    send_message(f"✅ Тоннель запущен!\n<code>{url}</code>", chat_id)

    # Генерируем QR
    send_message("🔲 Генерирую QR-код...", chat_id)
    qr_path = _make_qr(url)

    # Отправляем QR
    if qr_path.endswith('.png'):
        send_document(qr_path, caption=f"🔲 QR для: <code>{url}</code>", chat_id=chat_id)
    else:
        content = open(qr_path).read()
        send_message(f"🔲 QR-код:\n<code>{content[:500]}</code>\n\nURL: <code>{url}</code>",
                     chat_id)

    # Сохраняем состояние
    users = [u for u in get_all_users() if u.get('status') == 'active']
    _state[chat_id] = {'url': url, 'qr_path': qr_path, 'selected': set()}

    # Показываем выбор пользователей
    kb = _user_select_keyboard(users, set())
    send_message(
        f"📤 <b>Кому отправить QR?</b>\n\n"
        f"URL: <code>{url}</code>\n"
        f"Пользователей онлайн: {len(users)}",
        chat_id,
        reply_markup=kb
    )


def handle_cfqr_callback(action: str, chat_id: int, cb_id: str = ""):
    """Обрабатывает колбэки выбора юзеров и отправки."""
    state = _state.get(chat_id, {})
    users = [u for u in get_all_users() if u.get('status') == 'active']

    if action.startswith('cfqr_sel:'):
        tid = int(action.split(':')[1])
        sel = state.get('selected', set())
        if tid in sel:
            sel.discard(tid)
        else:
            sel.add(tid)
        state['selected'] = sel
        _state[chat_id] = state
        kb = _user_select_keyboard(users, sel)
        send_message(f"✅ Выбрано: {len(sel)} чел.", chat_id, reply_markup=kb)

    elif action == 'cfqr_all':
        sel = {u['telegram_id'] for u in users}
        state['selected'] = sel
        _state[chat_id] = state
        kb = _user_select_keyboard(users, sel)
        send_message(f"✅ Выбрано всех: {len(sel)} чел.", chat_id, reply_markup=kb)

    elif action == 'cfqr_none':
        state['selected'] = set()
        _state[chat_id] = state
        kb = _user_select_keyboard(users, set())
        send_message("❌ Выбор снят", chat_id, reply_markup=kb)

    elif action == 'cfqr_send':
        sel  = state.get('selected', set())
        url  = state.get('url', '')
        qr_path = state.get('qr_path', '')
        if not sel:
            send_message("⚠️ Выбери хотя бы одного пользователя", chat_id); return

        sent = failed = 0
        for tid in sel:
            try:
                send_message(
                    f"🌐 <b>Новый тоннель доступен!</b>\n\n"
                    f"🔗 <code>{url}</code>",
                    tid
                )
                if qr_path and os.path.exists(qr_path):
                    send_document(qr_path, caption="🔲 QR-код для подключения", chat_id=tid)
                sent += 1
                time.sleep(0.05)
            except Exception:
                failed += 1

        send_message(
            f"📤 <b>Отправлено!</b>\n"
            f"✅ Успешно: {sent}\n"
            f"❌ Ошибок: {failed}",
            chat_id,
            reply_markup={"inline_keyboard": [[
                {"text": "🔄 Новый тоннель", "callback_data": "cfqr_new"},
                {"text": "◀️ Готово",        "callback_data": "cfqr_cancel"},
            ]]}
        )

    elif action == 'cfqr_new':
        _state.pop(chat_id, None)
        handle_qr_command(chat_id)

    elif action == 'cfqr_cancel':
        _state.pop(chat_id, None)
        send_message("✅ Готово.", chat_id)
