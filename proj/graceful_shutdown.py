"""
BlackBugsAI — Graceful Shutdown
Перехватывает SIGTERM/SIGINT, ждёт завершения активных задач СМИТА,
уведомляет юзеров, чисто останавливает бот.
"""
import signal, threading, time, os
from typing import Set, Callable

_shutdown_event  = threading.Event()   # set → бот должен остановиться
_active_tasks:   Set[str] = set()      # chat_id'ы с активными задачами
_tasks_lock      = threading.Lock()
_notify_fn:      Callable = None       # send_message из bot.py
_WAIT_TIMEOUT    = 60                  # максимум ждём задачи, сек


def register_notify(fn: Callable):
    """Регистрируем send_message."""
    global _notify_fn
    _notify_fn = fn


def task_start(chat_id: str):
    """Вызывается когда агент начинает задачу."""
    with _tasks_lock:
        _active_tasks.add(str(chat_id))


def task_done(chat_id: str):
    """Вызывается когда агент завершил задачу."""
    with _tasks_lock:
        _active_tasks.discard(str(chat_id))


def is_shutting_down() -> bool:
    return _shutdown_event.is_set()


def active_count() -> int:
    with _tasks_lock:
        return len(_active_tasks)


def _shutdown_handler(signum, frame):
    sig_name = {signal.SIGTERM: 'SIGTERM', signal.SIGINT: 'SIGINT'}.get(signum, str(signum))
    print(f"\n⚡ [{sig_name}] Начинаю graceful shutdown...", flush=True)
    _shutdown_event.set()

    # Уведомляем юзеров у которых активны задачи
    with _tasks_lock:
        affected = list(_active_tasks)

    if affected and _notify_fn:
        print(f"  ⏳ Активных задач: {len(affected)} — уведомляю юзеров...", flush=True)
        for cid in affected:
            try:
                _notify_fn(
                    "🔄 <b>Бот перезапускается...</b>\n\n"
                    "Текущая задача будет завершена при следующем запуске.\n"
                    "Отправь задачу заново после перезапуска.",
                    cid
                )
            except Exception:
                pass

    # Ждём завершения задач
    deadline = time.time() + _WAIT_TIMEOUT
    while time.time() < deadline:
        with _tasks_lock:
            remaining = len(_active_tasks)
        if remaining == 0:
            print("  ✅ Все задачи завершены.", flush=True)
            break
        print(f"  ⏳ Жду {remaining} задач... ({int(deadline-time.time())}с)", flush=True)
        time.sleep(2)
    else:
        print(f"  ⚠️ Таймаут — принудительная остановка.", flush=True)

    print("👋 Бот остановлен.", flush=True)
    os._exit(0)


def setup():
    """Регистрирует signal handlers. Вызывать из main()."""
    try:
        signal.signal(signal.SIGTERM, _shutdown_handler)
        signal.signal(signal.SIGINT,  _shutdown_handler)
        print("  ✅ Graceful shutdown: SIGTERM/SIGINT зарегистрированы", flush=True)
    except (OSError, ValueError):
        # Windows или нет терминала
        print("  ⚠️ Graceful shutdown: сигналы недоступны (Windows?)", flush=True)


def poll_should_stop() -> bool:
    """Проверить нужно ли остановить poll loop."""
    return _shutdown_event.is_set()
