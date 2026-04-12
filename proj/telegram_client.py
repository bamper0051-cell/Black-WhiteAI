import requests, config

def _url(method):
    return f'https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/{method}'

def _safe_html(text):
    """
    Оставляет только теги которые Telegram поддерживает в parse_mode=HTML.
    Всё остальное экранирует. Закрывает незакрытые теги.
    Обрабатывает скрейпнутый HTML без падения.
    """
    import re, html as _html
    ALLOWED = {'b', 'strong', 'i', 'em', 'u', 'ins', 's', 'strike',
               'del', 'code', 'pre', 'a', 'tg-spoiler', 'blockquote'}
    STRIP_WITH_CONTENT = {'script', 'style', 'head', 'noscript', 'svg',
                          'iframe', 'canvas', 'object', 'embed', 'video',
                          'audio', 'template', 'slot', 'portal'}
    text = str(text)

    # 1. Удаляем нежелательные блоки вместе с содержимым
    for tag in STRIP_WITH_CONTENT:
        text = re.sub(
            r'<{tag}[^>]*>.*?</{tag}>'.format(tag=tag),
            '', text, flags=re.DOTALL | re.IGNORECASE
        )

    # 2. Удаляем оставшиеся одиночные теги STRIP_WITH_CONTENT
    for tag in STRIP_WITH_CONTENT:
        text = re.sub(r'</?{tag}[^>]*>'.format(tag=tag), '', text,
                      flags=re.IGNORECASE)

    # 3. Обрабатываем все оставшиеся теги
    def replace_tag(m):
        full = m.group(0)
        name_m = re.match(r'</?([a-zA-Z][a-zA-Z0-9-]*)', full)
        if not name_m:
            return _html.escape(full)
        tag_name = name_m.group(1).lower()
        if tag_name in ALLOWED:
            if tag_name == 'a' and not full.startswith('</'):
                href = re.search(r'href=["\'](https?://[^"\']+)["\'\']',
                                  full, re.IGNORECASE)
                if href:
                    # Экранируем спецсимволы в href кроме допустимых URL
                    safe_href = href.group(1).replace('"', '%22')
                    return '<a href="{}">'.format(safe_href)
                return ''
            if full.startswith('</'):
                return '</{}>'.format(tag_name)
            # pre/code — без атрибутов
            return '<{}>'.format(tag_name)
        return _html.escape(full)

    result = re.sub(r'<[^>]{0,2000}>', replace_tag, text, flags=re.DOTALL)

    # 4. Экранируем одиночные < и > которые остались вне тегов
    # (бывает в скрейпнутом коде: "x < y", "for (int i=0; i<n; i++)")
    def escape_loose(m):
        pos = m.start()
        ch  = m.group(0)
        # Если это часть тега — оставляем (уже обработано выше)
        before = result[:pos] if pos > 0 else ''
        # Считаем открытые < без закрытых >
        return _html.escape(ch)

    # Экранируем < > которые не часть разрешённых тегов
    # После replace_tag все разрешённые теги уже в правильном виде,
    # поэтому все оставшиеся < > — это текстовые символы
    def protect_allowed(text):
        """Заменяем разрешённые теги на плейсхолдеры, экранируем остальное, возвращаем."""
        placeholders = {}
        counter = [0]
        def _save(m):
            k = f'\x00TAG{counter[0]}\x00'
            placeholders[k] = m.group(0)
            counter[0] += 1
            return k
        # Сохраняем разрешённые теги
        protected = re.sub(
            r'</?(?:b|strong|i|em|u|ins|s|strike|del|code|pre|blockquote|tg-spoiler)'
            r'(?:\s[^>]*)?>|<a href="[^"]*">|</a>',
            _save, text, flags=re.IGNORECASE
        )
        # Экранируем оставшиеся < >
        protected = protected.replace('<', '&lt;').replace('>', '&gt;')
        # Восстанавливаем
        for k, v in placeholders.items():
            protected = protected.replace(k, v)
        return protected

    result = protect_allowed(result)

    # 5. Закрываем незакрытые теги
    stack = []
    for m in re.finditer(r'<(/?)([a-zA-Z][a-zA-Z0-9-]*)(?:\s[^>]*)?>', result):
        closing, tag = m.group(1), m.group(2).lower()
        if tag not in ALLOWED:
            continue
        if closing:
            for i in range(len(stack) - 1, -1, -1):
                if stack[i] == tag:
                    stack = stack[:i]
                    break
        elif tag not in ('br', 'hr'):
            stack.append(tag)
    for tag in reversed(stack):
        result += '</{}>'.format(tag)

    return result

def send_message(text: str, chat_id=None, reply_markup=None):
    # Пустые сообщения — пропускаем или заменяем нулевым пробелом если есть кнопки
    import html as _html_mod
    text = str(text)
    if not text.strip():
        if reply_markup:
            text = "\u200b"  # zero-width space — Telegram принимает
        else:
            return {}

    safe = _safe_html(text)
    MAX = 4000  # Telegram лимит 4096, берём с запасом

    def _send_one(chunk, markup=None):
        payload = {
            'chat_id': chat_id or config.TELEGRAM_CHAT_ID,
            'text': chunk,
            'parse_mode': 'HTML',
        }
        if markup:
            payload['reply_markup'] = markup
        try:
            r = requests.post(_url('sendMessage'), json=payload, timeout=30)
            if r.ok:
                return r.json().get('result', {})
            err_text = r.text
            if 'parse_mode' in err_text or "can\'t parse" in err_text or 'Bad Request' in err_text:
                import re as _re
                payload2 = {
                    'chat_id': chat_id or config.TELEGRAM_CHAT_ID,
                    'text': _html_mod.unescape(_re.sub(r'<[^>]+>', '', chunk))[:MAX],
                }
                if markup:
                    payload2['reply_markup'] = markup
                r2 = requests.post(_url('sendMessage'), json=payload2, timeout=30)
                if r2.ok:
                    return r2.json().get('result', {})
            print(f"  ⚠️ send_message error: {r.status_code} {r.text[:200]}", flush=True)
        except Exception as e:
            print(f"  ⚠️ send_message exception: {e}", flush=True)
        return {}

    # Разбиваем на чанки если текст длиннее лимита
    if len(safe) <= MAX:
        return _send_one(safe, reply_markup)

    # Длинный текст — шлём частями, кнопки только к последней
    chunks = []
    while safe:
        if len(safe) <= MAX:
            chunks.append(safe)
            break
        # Ищем хорошее место для разрыва
        cut = safe.rfind('\n', 0, MAX)
        if cut < MAX // 2:
            cut = MAX
        chunks.append(safe[:cut])
        safe = safe[cut:]
    result = {}
    for i, chunk in enumerate(chunks):
        mkp = reply_markup if i == len(chunks) - 1 else None
        result = _send_one(chunk, mkp)
    return result


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
