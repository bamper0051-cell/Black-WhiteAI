import requests, config

def _url(method):
    return f'https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/{method}'

def _safe_html(text):
    """
    Оставляет только теги которые Telegram поддерживает.
    Всё остальное экранирует. Автоматически закрывает незакрытые теги.
    """
    import re, html as _html
    ALLOWED = {'b', 'strong', 'i', 'em', 'u', 'ins', 's', 'strike',
               'del', 'code', 'pre', 'a', 'tg-spoiler', 'blockquote'}
    text = str(text)

    def replace_tag(m):
        full = m.group(0)
        tag  = re.match(r'</?([a-zA-Z][a-zA-Z0-9]*)', full)
        if tag and tag.group(1).lower() in ALLOWED:
            return full
        return _html.escape(full)

    result = re.sub(r'<[^>]+>', replace_tag, text)

    # Закрываем незакрытые теги через простой стек
    stack = []
    for m in re.finditer(r'<(/?)([a-zA-Z][a-zA-Z0-9]*)[^>]*>', result):
        closing, tag = m.group(1), m.group(2).lower()
        if tag not in ALLOWED:
            continue
        if closing:
            if stack and stack[-1] == tag:
                stack.pop()
        else:
            stack.append(tag)
    for tag in reversed(stack):
        result += '</{}>'.format(tag)

    return result

def send_message(text: str, chat_id=None, reply_markup=None):
    # Пустые сообщения — пропускаем или заменяем нулевым пробелом если есть кнопки
    text = str(text)
    if not text.strip():
        if reply_markup:
            text = "\u200b"  # zero-width space — Telegram принимает
        else:
            return {}
    payload = {
        'chat_id': chat_id or config.TELEGRAM_CHAT_ID,
        'text': _safe_html(str(text)),
        'parse_mode': 'HTML',
    }
    if reply_markup:
        payload['reply_markup'] = reply_markup
    try:
        r = requests.post(_url('sendMessage'), json=payload, timeout=30)
        if r.ok:
            return r.json().get('result', {})
        else:
            print(f"  ⚠️ send_message error: {r.status_code} {r.text[:200]}", flush=True)
    except Exception as e:
        print(f"  ⚠️ send_message exception: {e}", flush=True)
    return {}

def edit_message(chat_id, message_id, text, reply_markup=None):
    payload = {
        'chat_id': chat_id,
        'message_id': message_id,
        'text': _safe_html(str(text)),
        'parse_mode': 'HTML',
    }
    if reply_markup:
        payload['reply_markup'] = reply_markup
    try:
        r = requests.post(_url('editMessageText'), json=payload, timeout=30)
        if not r.ok:
            err = r.json().get('description', '')
            # "message is not modified" — не ошибка, просто игнорируем
            if 'not modified' not in err:
                print(f"  ⚠️ edit_message error: {err}", flush=True)
        return r.ok
    except Exception as e:
        print(f"  ⚠️ edit_message exception: {e}", flush=True)
        return False

def answer_callback(callback_id, text='', alert=False):
    try:
        requests.post(_url('answerCallbackQuery'), json={
            'callback_query_id': callback_id,
            'text': text,
            'show_alert': alert,
        }, timeout=10)
    except Exception as e:
        print(f"  ⚠️ answer_callback exception: {e}", flush=True)

def send_audio(path, caption='', chat_id=None):
    try:
        with open(path, 'rb') as f:
            r = requests.post(_url('sendAudio'),
                data={'chat_id': chat_id or config.TELEGRAM_CHAT_ID,
                      'caption': caption[:1024]},
                files={'audio': f}, timeout=90)
        return r.ok
    except Exception as e:
        print(f"  ⚠️ send_audio exception: {e}", flush=True)
        return False

def send_document(path, caption='', chat_id=None):
    try:
        with open(path, 'rb') as f:
            r = requests.post(_url('sendDocument'),
                data={'chat_id': chat_id or config.TELEGRAM_CHAT_ID,
                      'caption': caption[:1024]},
                files={'document': f}, timeout=60)
        return r.ok
    except Exception as e:
        print(f"  ⚠️ send_document exception: {e}", flush=True)
        return False

def delete_webhook():
    """Удаляет вебхук — необходимо перед long polling."""
    try:
        r = requests.post(_url('deleteWebhook'), json={'drop_pending_updates': False}, timeout=10)
        data = r.json()
        if data.get('result'):
            print("  ✅ Webhook удалён.", flush=True)
        else:
            print(f"  ℹ️ deleteWebhook: {data}", flush=True)
    except Exception as e:
        print(f"  ⚠️ deleteWebhook exception: {e}", flush=True)

_409_count = 0

def get_updates(offset=0):
    global _409_count
    try:
        r = requests.get(_url('getUpdates'), params={
            'offset': offset,
            'timeout': 25,
            # Явно указываем типы апдейтов, включая callback_query
            'allowed_updates': '["message","callback_query"]',
        }, timeout=30)
        if r.ok:
            _409_count = 0
            return r.json().get('result', [])
        elif r.status_code == 409:
            _409_count += 1
            if _409_count == 1:
                print('  ⚠️ 409 Conflict — бот запущен в двух местах!', flush=True)
                print('     Останови другой экземпляр. Жду...', flush=True)
            elif _409_count % 10 == 0:
                print(f'  ⏳ Всё ещё 409 ({_409_count} раз)...', flush=True)
            import time as _t409; _t409.sleep(5)
        else:
            print(f"  ⚠️ getUpdates error: {r.status_code}", flush=True)
    except Exception as e:
        print(f"  ⚠️ getUpdates exception: {e}", flush=True)
    return []


def get_file_path(file_id):
    """Получает путь к файлу на серверах Telegram."""
    try:
        r = requests.get(_url('getFile'), params={'file_id': file_id}, timeout=15)
        if r.ok:
            return r.json().get('result', {}).get('file_path')
    except Exception as e:
        print("  ⚠️ getFile exception: {}".format(e), flush=True)
    return None

def download_file(file_id, dest_path):
    """Скачивает файл с Telegram и сохраняет по dest_path. Возвращает True/False."""
    file_path = get_file_path(file_id)
    if not file_path:
        return False
    url = "https://api.telegram.org/file/bot{}/{}".format(config.TELEGRAM_BOT_TOKEN, file_path)
    try:
        r = requests.get(url, timeout=60, stream=True)
        r.raise_for_status()
        with open(dest_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print("  ⚠️ download_file exception: {}".format(e), flush=True)
        return False
