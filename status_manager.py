"""
BlackBugsAI — Status Manager
Управляет статусными сообщениями агента.
Вместо спама новыми сообщениями — редактирует одно.
Автоматически создаёт сообщение если нет, редактирует если есть.
"""
import time, threading
from typing import Optional, Callable


class StatusMessage:
    """
    Умный статус агента — одно редактируемое сообщение.
    Показывает последние MAX_LINES строк + таймер.
    """
    MAX_LINES = 10

    def __init__(self, chat_id: str, send_fn: Callable, edit_fn: Callable,
                 delete_fn: Callable = None, prefix: str = ""):
        self.chat_id   = chat_id
        self._send     = send_fn
        self._edit     = edit_fn
        self._delete   = delete_fn
        self.prefix    = prefix
        self._msg_id:  Optional[int] = None
        self._lock     = threading.Lock()
        self._lines    = []           # текущие видимые строки
        self._start    = time.time()

    def _render(self) -> str:
        elapsed = int(time.time() - self._start)
        visible = self._lines[-self.MAX_LINES:]
        body    = "\n".join(visible)
        timer   = f"\n<i>⏱ {elapsed}с</i>"
        return f"{self.prefix}{body}{timer}"

    def update(self, text: str):
        """Заменяет последнюю строку (прогресс одного шага)."""
        with self._lock:
            if self._lines:
                self._lines[-1] = text
            else:
                self._lines.append(text)
            self._flush()

    def append(self, text: str):
        """Добавляет новую строку."""
        with self._lock:
            self._lines.append(text)
            self._flush()

    def _flush(self):
        content = self._render()
        if self._msg_id:
            try:
                self._edit(self.chat_id, self._msg_id, content)
                return
            except Exception:
                self._msg_id = None
        try:
            result = self._send(content, self.chat_id)
            if isinstance(result, dict):
                r = result.get('result', result)
                self._msg_id = r.get('message_id') if isinstance(r, dict) else None
        except Exception:
            pass

    def done(self, text: str, keep: bool = True):
        """Финальный статус."""
        with self._lock:
            elapsed = int(time.time() - self._start)
            content = f"{text}\n<i>⏱ {elapsed}с</i>"
            if self._msg_id:
                try:
                    self._edit(self.chat_id, self._msg_id, content)
                    return
                except Exception:
                    self._msg_id = None
            try:
                self._send(content, self.chat_id)
            except Exception:
                pass

    def make_on_status(self, append: bool = True) -> Callable:
        return self.append if append else self.update


def make_status(chat_id: str, send_fn, edit_fn,
                delete_fn=None, prefix: str = "") -> StatusMessage:
    """Фабрика StatusMessage."""
    return StatusMessage(chat_id, send_fn, edit_fn, delete_fn, prefix)
