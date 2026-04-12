"""
msg_sender.py — Отправка сообщений другим пользователям и в каналы/группы.

Функции:
  send_to_user(chat_id_or_username, text)  — отправить другому юзеру
  send_to_channel(channel, text)           — в канал/группу
  forward_message(from_chat, msg_id, to_chat) — переслать
  schedule_message(chat_id, text, delay_sec)   — с задержкой
  broadcast(chat_ids, text)               — массовая рассылка
"""

import time
import threading
import requests
import config

def _url(method):
    return f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/{method}"

def _post(method, **kwargs):
    """Делает POST запрос к Telegram API."""
    try:
        r = requests.post(_url(method), json=kwargs, timeout=15)
        data = r.json()
        if data.get('ok'):
            return data.get('result'), None
        return None, data.get('description', 'Unknown error')
    except Exception as e:
        return None, str(e)

# ══════════════════════════════════════════════════════════════════
#  ОТПРАВКА СООБЩЕНИЙ
# ══════════════════════════════════════════════════════════════════

def send_to_user(target, text: str, parse_mode='HTML') -> tuple:
    """
    Отправляет сообщение пользователю.
    target: chat_id (int/str) или @username
    Возвращает (ok: bool, error: str|None)
    """
    result, err = _post('sendMessage',
                        chat_id=str(target),
                        text=text,
                        parse_mode=parse_mode)
    return (result is not None), err


def send_to_channel(channel: str, text: str, parse_mode='HTML') -> tuple:
    """
    Отправляет в канал или группу.
    channel: '@channel_name' или chat_id
    """
    if channel and not channel.startswith('@') and not channel.lstrip('-').isdigit():
        channel = '@' + channel
    return send_to_user(channel, text, parse_mode)


def send_file_to(target, file_path: str, caption: str = '') -> tuple:
    """Отправляет файл пользователю или в канал."""
    try:
        with open(file_path, 'rb') as f:
            r = requests.post(
                _url('sendDocument'),
                data={'chat_id': str(target), 'caption': caption, 'parse_mode': 'HTML'},
                files={'document': f},
                timeout=60
            )
        data = r.json()
        return data.get('ok', False), data.get('description')
    except Exception as e:
        return False, str(e)


def send_photo_to(target, file_path: str, caption: str = '') -> tuple:
    """Отправляет фото пользователю или в канал."""
    try:
        with open(file_path, 'rb') as f:
            r = requests.post(
                _url('sendPhoto'),
                data={'chat_id': str(target), 'caption': caption, 'parse_mode': 'HTML'},
                files={'photo': f},
                timeout=60
            )
        data = r.json()
        return data.get('ok', False), data.get('description')
    except Exception as e:
        return False, str(e)


def forward_message(from_chat_id, message_id: int, to_chat_id) -> tuple:
    """Пересылает сообщение."""
    result, err = _post('forwardMessage',
                        chat_id=str(to_chat_id),
                        from_chat_id=str(from_chat_id),
                        message_id=int(message_id))
    return (result is not None), err


def pin_message(chat_id, message_id: int) -> tuple:
    """Закрепляет сообщение."""
    result, err = _post('pinChatMessage',
                        chat_id=str(chat_id),
                        message_id=int(message_id))
    return (result is not None), err


# ══════════════════════════════════════════════════════════════════
#  ОТЛОЖЕННАЯ ОТПРАВКА
# ══════════════════════════════════════════════════════════════════

_scheduled = []  # список запланированных задач
_schedule_lock = threading.Lock()


def schedule_message(target, text: str, delay_sec: int,
                     on_sent=None, parse_mode='HTML') -> str:
    """
    Запланировать отправку через delay_sec секунд.
    on_sent(ok, err) — колбэк после отправки.
    Возвращает task_id.
    """
    task_id = 'sched_{}'.format(int(time.time()))
    send_at = time.time() + delay_sec

    task = {
        'id':       task_id,
        'target':   target,
        'text':     text,
        'send_at':  send_at,
        'sent':     False,
        'on_sent':  on_sent,
        'parse_mode': parse_mode,
    }
    with _schedule_lock:
        _scheduled.append(task)

    def _run():
        now = time.time()
        wait = send_at - now
        if wait > 0:
            time.sleep(wait)
        ok, err = send_to_user(target, text, parse_mode)
        task['sent'] = True
        if on_sent:
            on_sent(ok, err)

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return task_id


def get_scheduled() -> list:
    """Возвращает список незавершённых задач."""
    now = time.time()
    with _schedule_lock:
        return [t for t in _scheduled if not t['sent']]


def cancel_scheduled(task_id: str) -> bool:
    """Отменяет задачу (если ещё не отправлена)."""
    with _schedule_lock:
        for t in _scheduled:
            if t['id'] == task_id and not t['sent']:
                t['sent'] = True  # помечаем как «отменённую»
                return True
    return False


# ══════════════════════════════════════════════════════════════════
#  РАССЫЛКА
# ══════════════════════════════════════════════════════════════════

def broadcast(targets: list, text: str,
              delay_between=0.5, parse_mode='HTML',
              on_progress=None) -> dict:
    """
    Рассылает сообщение списку пользователей.
    delay_between — пауза между отправками (сек).
    on_progress(sent, total, last_err) — колбэк прогресса.
    
    Возвращает {'sent': int, 'failed': int, 'errors': list}
    """
    sent   = 0
    failed = 0
    errors = []

    for i, target in enumerate(targets):
        ok, err = send_to_user(target, text, parse_mode)
        if ok:
            sent += 1
        else:
            failed += 1
            errors.append({'target': target, 'error': err})
        if on_progress:
            on_progress(sent + failed, len(targets), err)
        if i < len(targets) - 1 and delay_between > 0:
            time.sleep(delay_between)

    return {'sent': sent, 'failed': failed, 'errors': errors[:10]}
