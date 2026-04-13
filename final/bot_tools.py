"""
bot_tools.py — Инструменты бота доступные агенту-кодеру.

Агент может вызывать эти функции через специальные команды вида:
  BOT_TOOL: tunnel_start bore
  BOT_TOOL: save_html <url>
  BOT_TOOL: send_file <path>
  BOT_TOOL: bot_stats

Модуль импортируется из chat_agent.py и bot.py.
"""

import os
import re
import sys
import time
import threading
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ═══════════════════════════════════════════════════════
#  РЕЕСТР ИНСТРУМЕНТОВ
# ═══════════════════════════════════════════════════════

TOOLS_REGISTRY = {}

def _tool(name, description, usage):
    """Декоратор — регистрирует функцию как инструмент агента."""
    def decorator(fn):
        TOOLS_REGISTRY[name] = {
            'fn': fn,
            'description': description,
            'usage': usage,
        }
        return fn
    return decorator


def get_tools_help():
    """Возвращает строку со списком доступных инструментов для системного промпта."""
    lines = ["=== ИНСТРУМЕНТЫ БОТА (BOT_TOOL) ===",
             "Используй в коде: print('BOT_TOOL: <команда> [аргументы]')\n"]
    for name, info in TOOLS_REGISTRY.items():
        lines.append(f"• BOT_TOOL: {info['usage']}")
        lines.append(f"  {info['description']}\n")
    return "\n".join(lines)


def execute_bot_tool(command_line, chat_id, send_fn, send_doc_fn):
    """
    Разбирает строку вида 'tunnel_start bore' и выполняет нужный инструмент.
    send_fn(text, chat_id) — отправить сообщение
    send_doc_fn(path, caption, chat_id) — отправить файл
    Возвращает строку результата.
    """
    parts = command_line.strip().split(None, 1)
    cmd   = parts[0].lower()
    args  = parts[1] if len(parts) > 1 else ''

    if cmd not in TOOLS_REGISTRY:
        return f"❌ Неизвестный инструмент: {cmd}. Доступные: {', '.join(TOOLS_REGISTRY)}"

    try:
        result = TOOLS_REGISTRY[cmd]['fn'](args, chat_id, send_fn, send_doc_fn)
        return result or "✅ Выполнено"
    except Exception as e:
        return f"❌ Ошибка инструмента {cmd}: {e}"


# ═══════════════════════════════════════════════════════
#  ИНСТРУМЕНТ: ТУННЕЛИ
# ═══════════════════════════════════════════════════════

@_tool('tunnel_start',
       'Запускает туннель. Провайдеры: bore (по умолчанию), ngrok, serveo',
       'tunnel_start [bore|ngrok|serveo]')
def tool_tunnel_start(args, chat_id, send_fn, send_doc_fn):
    provider = (args.strip() or 'bore').lower()

    try:
        import fish_bot_state as fbs
        import fish_config as fc
    except ImportError:
        return "❌ fish-модуль не загружен"

    port = fc.SERVER_PORT

    def _start_bore():
        import shutil
        if not shutil.which('bore'):
            send_fn("⚠️ bore не установлен. Ставим...", chat_id)
            subprocess.run(['cargo', 'install', 'bore-cli'], capture_output=True)
        proc = subprocess.Popen(
            ['bore', 'local', str(port), '--to', 'bore.pub'],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
        fbs.bore_process = proc
        for line in proc.stdout:
            m = re.search(r'bore\.pub:(\d+)', line)
            if m:
                fbs.bore_url = f"http://bore.pub:{m.group(1)}"
                send_fn(f"✅ bore туннель: <code>{fbs.bore_url}</code>", chat_id)
                return fbs.bore_url
        return None

    def _start_ngrok():
        proc = subprocess.Popen(
            ['ngrok', 'http', str(port), '--log', 'stdout'],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
        fbs.ngrok_process = proc
        for line in proc.stdout:
            m = re.search(r'url=(https://[^\s]+)', line)
            if m:
                fbs.ngrok_url = m.group(1)
                send_fn(f"✅ ngrok туннель: <code>{fbs.ngrok_url}</code>", chat_id)
                return fbs.ngrok_url
        return None

    def _start_serveo():
        """Запускает serveo с авто-переподключением при обрыве."""
        max_retries = 10
        retry_delay = 5
        for attempt in range(max_retries):
            try:
                proc = subprocess.Popen(
                    ['ssh', '-R', f'80:localhost:{port}', 'serveo.net',
                     '-o', 'StrictHostKeyChecking=no',
                     '-o', 'ServerAliveInterval=30',
                     '-o', 'ServerAliveCountMax=3',
                     '-o', 'ExitOnForwardFailure=yes',
                     '-o', 'ConnectTimeout=15'],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
                )
                fbs.serveo_process = proc
                url_found = False
                for line in proc.stdout:
                    line = line.strip()
                    m = re.search(r'https://\S+serveo\.net', line)
                    if m:
                        fbs.serveo_url = m.group(0)
                        url_found = True
                        if attempt == 0:
                            send_fn(f"✅ serveo: <code>{fbs.serveo_url}</code>", chat_id)
                        else:
                            send_fn(f"🔄 serveo переподключён (попытка {attempt+1}): <code>{fbs.serveo_url}</code>", chat_id)
                proc.wait()
                # Процесс завершился
                fbs.serveo_url = None
                if proc.returncode == 0 or attempt == max_retries - 1:
                    break
                # Переподключаемся
                import time as _t2; _t2.sleep(retry_delay)
            except Exception as e:
                import time as _t3; _t3.sleep(retry_delay)
                continue
        fbs.serveo_url = None
        fbs.serveo_process = None
        return None

    starters = {'bore': _start_bore, 'ngrok': _start_ngrok, 'serveo': _start_serveo}
    fn = starters.get(provider, _start_bore)

    send_fn(f"🚇 Запускаю туннель [{provider}]...", chat_id)
    t = threading.Thread(target=fn, daemon=True)
    t.start()
    t.join(timeout=15)

    try:
        import fish_bot_state as fbs
        url = fbs.tunnel_url or fbs.bore_url or fbs.ngrok_url or fbs.serveo_url
        if url:
            return f"✅ Туннель активен: {url}"
    except Exception:
        pass
    return f"⏳ Туннель [{provider}] запускается в фоне"


@_tool('tunnel_stop', 'Останавливает все активные туннели', 'tunnel_stop')
def tool_tunnel_stop(args, chat_id, send_fn, send_doc_fn):
    try:
        import fish_bot_state as fbs
        stopped = []
        for name, proc_attr, url_attr in [
            ('bore',   'bore_process',   'bore_url'),
            ('ngrok',  'ngrok_process',  'ngrok_url'),
            ('serveo', 'serveo_process', 'serveo_url'),
            ('cf',     'tunnel_process', 'tunnel_url'),
        ]:
            proc = getattr(fbs, proc_attr, None)
            if proc and proc.poll() is None:
                proc.terminate()
                stopped.append(name)
            setattr(fbs, proc_attr, None)
            setattr(fbs, url_attr, None)
        return "✅ Остановлены: " + (", ".join(stopped) or "нет активных")
    except ImportError:
        return "❌ fish-модуль не загружен"


@_tool('tunnel_status', 'Показывает статус и URL активных туннелей', 'tunnel_status')
def tool_tunnel_status(args, chat_id, send_fn, send_doc_fn):
    try:
        import fish_bot_state as fbs
        lines = []
        for name, proc_attr, url_attr in [
            ('bore',   'bore_process',   'bore_url'),
            ('ngrok',  'ngrok_process',  'ngrok_url'),
            ('serveo', 'serveo_process', 'serveo_url'),
            ('cf',     'tunnel_process', 'tunnel_url'),
        ]:
            proc = getattr(fbs, proc_attr, None)
            url  = getattr(fbs, url_attr, None)
            alive = proc and proc.poll() is None
            status = f"🟢 {url}" if (alive and url) else ("🟡 запущен" if alive else "🔴 нет")
            lines.append(f"• {name}: {status}")
        return "\n".join(lines)
    except ImportError:
        return "❌ fish-модуль не загружен"


# ═══════════════════════════════════════════════════════
#  ИНСТРУМЕНТ: HTML-СТРАНИЦЫ
# ═══════════════════════════════════════════════════════

@_tool('save_html',
       'Скачивает URL и сохраняет как активную fish-страницу. Возвращает page_id.',
       'save_html <url>')
def tool_save_html(args, chat_id, send_fn, send_doc_fn):
    url = args.strip()
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    try:
        from fish_downloader import downloader as dl
        send_fn(f"📥 Скачиваю {url}...", chat_id)

        def _status(msg):
            send_fn(msg, chat_id)

        html = dl.download_page(url, on_status=_status)
        pid  = dl.save_page(html, url, 'single')
        dl.set_active_page(pid)
        return f"✅ Сохранено и активировано. page_id={pid}"
    except Exception as e:
        return f"❌ Ошибка: {e}"


@_tool('list_pages', 'Показывает список сохранённых HTML-страниц', 'list_pages')
def tool_list_pages(args, chat_id, send_fn, send_doc_fn):
    try:
        from fish_downloader import downloader as dl
        pages = dl.get_all_pages()
        if not pages:
            return "Нет сохранённых страниц"
        lines = []
        for pid, meta in list(pages.items())[-10:]:
            lines.append(f"• [{pid}] {meta.get('url','?')[:60]} ({meta.get('date','?')})")
        return "\n".join(lines)
    except Exception as e:
        return f"❌ {e}"


@_tool('activate_page',
       'Активирует сохранённую страницу по ID',
       'activate_page <page_id>')
def tool_activate_page(args, chat_id, send_fn, send_doc_fn):
    pid = args.strip()
    try:
        from fish_downloader import downloader as dl
        ok = dl.set_active_page(pid)
        return f"✅ Страница {pid} активирована" if ok else f"❌ Страница {pid} не найдена"
    except Exception as e:
        return f"❌ {e}"


# ═══════════════════════════════════════════════════════
#  ИНСТРУМЕНТ: ФАЙЛЫ
# ═══════════════════════════════════════════════════════

@_tool('send_file',
       'Отправляет файл пользователю в Telegram',
       'send_file <path>')
def tool_send_file(args, chat_id, send_fn, send_doc_fn):
    path = args.strip().strip('"\'')
    if not os.path.isabs(path):
        path = os.path.join(BASE_DIR, path)
    if not os.path.exists(path):
        return f"❌ Файл не найден: {path}"
    try:
        send_doc_fn(path, caption=f"📎 {os.path.basename(path)}", chat_id=chat_id)
        return f"✅ Файл отправлен: {os.path.basename(path)}"
    except Exception as e:
        return f"❌ Ошибка отправки: {e}"


@_tool('read_file',
       'Читает содержимое текстового файла (первые 3000 символов)',
       'read_file <path>')
def tool_read_file(args, chat_id, send_fn, send_doc_fn):
    path = args.strip().strip('"\'')
    if not os.path.isabs(path):
        path = os.path.join(BASE_DIR, path)
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read(3000)
        return f"📄 {path}:\n{content}"
    except Exception as e:
        return f"❌ {e}"


# ═══════════════════════════════════════════════════════
#  ИНСТРУМЕНТ: СТАТИСТИКА БОТА
# ═══════════════════════════════════════════════════════

@_tool('bot_stats', 'Показывает статистику бота (сессии, новости, файлы)', 'bot_stats')
def tool_bot_stats(args, chat_id, send_fn, send_doc_fn):
    lines = ["📊 Статистика бота:"]
    try:
        from chat_agent import all_active_sessions
        sessions = all_active_sessions()
        lines.append(f"• Активных сессий: {len(sessions)}")
    except Exception:
        pass
    try:
        from fish_downloader import downloader as dl
        pages = dl.get_all_pages()
        lines.append(f"• HTML-страниц сохранено: {len(pages)}")
        active = dl.get_active_page_info()
        if active:
            lines.append(f"• Активная страница: {active[1][:50]}")
    except Exception:
        pass
    try:
        import fish_bot_state as fbs
        url = fbs.tunnel_url or fbs.bore_url or fbs.ngrok_url or fbs.serveo_url
        lines.append(f"• Туннель: {url or 'не активен'}")
        lines.append(f"• Flask сервер: {'🟢 работает' if fbs.server_running else '🔴 стоп'}")
    except Exception:
        pass
    # Размер директории бота
    try:
        total = sum(
            os.path.getsize(os.path.join(dp, f))
            for dp, dn, fns in os.walk(BASE_DIR)
            for f in fns
        )
        lines.append(f"• Размер директории: {total // 1024 // 1024} MB")
    except Exception:
        pass
    return "\n".join(lines)
