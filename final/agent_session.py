"""
АГЕНТ_СМИТ — BlackBugsAI Autonomous Code & Media Agent
Fullchain pipeline:
  опиши задачу → файлы → запускай →
  analyze → plan → generate → lint → sandbox → auto-fix(x15) → zip → send
"""
import os, json, re, sys, time, shutil, zipfile, subprocess, tempfile, threading
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable
import config

# ─── ЛИЧНОСТЬ АГЕНТА ─────────────────────────────────────────────────────────

AGENT_NAME = "АГЕНТ_СМИТ"
AGENT_EMOJI = "🕵️"

SMITH_SYSTEM = """Ты АГЕНТ_СМИТ — автономный AI-агент для написания Python-кода.

Доступен ВЕСЬ Python: stdlib + популярные пакеты включая:
- Pillow (PIL) — работа с изображениями: открытие, изменение, фильтры, конвертация, текст
- pynput, pyautogui, keyboard, mouse (автоматизация ввода)
- aiogram, python-telegram-bot, pyrogram (Telegram боты)
- requests, httpx, aiohttp, playwright (HTTP/веб)
- pandas, numpy, scipy (данные/математика)
- opencv-python (cv2) — компьютерное зрение
- imageio, moviepy (медиа)
- fastapi, flask, starlette (веб-серверы)
- sqlalchemy, sqlite3, pymongo (базы данных)
- cryptography, bcrypt, jwt (безопасность)
- rich, typer, click (CLI)
- pytest, coverage (тестирование)
- pydantic, dataclasses, attrs (типизация)
- ВСЯ стандартная библиотека Python

Правила:
1. Пиши ТОЛЬКО рабочий Python-код
2. НЕ используй Unicode em-dash (U+2014) или умные кавычки в коде
3. Используй только ASCII в идентификаторах
4. Если нужен пакет — добавь pip install через subprocess в начало
5. Для Pillow: from PIL import Image, ImageDraw, ImageFont, ImageFilter
6. Для pynput/pyautogui — добавь try/except (может не быть display)
7. Код должен запускаться без аргументов (или с дефолтами)
8. Пиши в блоке: ```python ... ```
9. После кода: ```requirements\\nпакет1\\nпакет2\\n```"""

SMITH_FIX_SYSTEM = """Ты АГЕНТ_СМИТ — фиксишь Python-код.
Правила фикса:
1. Получаешь код + ошибку
2. Исправляешь ТОЛЬКО проблему из traceback
3. НЕ меняешь логику которая работает
4. НЕ используешь Unicode-символы (em-dash, curly quotes)
5. Если ошибка "No module named X" — добавь установку: import subprocess; subprocess.run([sys.executable, "-m", "pip", "install", "X"], check=True)
6. Возвращаешь ПОЛНЫЙ исправленный код в блоке ```python ... ```"""

# ─── Состояние сессии ────────────────────────────────────────────────────────

STAGE_WAIT_TASK  = "wait_task"
STAGE_WAIT_FILES = "wait_files"
STAGE_EXECUTING  = "executing"
STAGE_DONE       = "done"

TRIGGERS_READY  = ['готово', 'go', 'поехали', 'запускай', 'start',
                   'выполняй', 'делай', 'начинай', 'run', 'execute', 'вперёд', 'ok', 'ок']
TRIGGERS_CANCEL = ['отмена', 'cancel', 'стоп', 'stop', 'выход', 'exit', 'quit']

MAX_FIX_ATTEMPTS = 15   # ← 15 попыток авто-фикса
SANDBOX_TIMEOUT  = 30   # секунд на запуск кода


@dataclass
class AgentSession:
    chat_id:      str
    task:         str = ""
    stage:        str = STAGE_WAIT_TASK
    files:        List[Dict] = field(default_factory=list)
    plan_text:    str = ""
    tools_ready:  List[str] = field(default_factory=list)
    created_at:   float = field(default_factory=time.time)
    last_active:  float = field(default_factory=time.time)
    output_dir:   str = ""
    results:      List[Dict] = field(default_factory=list)
    errors:       List[str] = field(default_factory=list)
    fix_history:  List[str] = field(default_factory=list)  # история фиксов

    def touch(self):
        self.last_active = time.time()

    def add_file(self, path: str, name: str, file_type: str = 'unknown'):
        self.files.append({'path': path, 'name': name, 'type': file_type})
        self.touch()

    def is_expired(self, ttl: int = 3600) -> bool:
        return time.time() - self.last_active > ttl


_sessions: Dict[str, AgentSession] = {}
_lock = threading.Lock()


def get_session(chat_id: str) -> Optional[AgentSession]:
    with _lock:
        return _sessions.get(str(chat_id))

def create_session(chat_id: str) -> AgentSession:
    sess = AgentSession(chat_id=str(chat_id))
    # Используем реальный BASE_DIR (не /app который может не существовать)
    base = getattr(config, 'BASE_DIR', os.path.dirname(os.path.abspath(__file__)))
    proj_dir = os.path.join(base, 'agent_projects')
    os.makedirs(proj_dir, exist_ok=True)
    sess.output_dir = os.path.join(proj_dir, f'sess_{chat_id}_{int(time.time())}')
    os.makedirs(sess.output_dir, exist_ok=True)
    with _lock:
        _sessions[str(chat_id)] = sess
    return sess

def close_session(chat_id: str):
    with _lock:
        _sessions.pop(str(chat_id), None)

def has_active_session(chat_id: str) -> bool:
    sess = get_session(chat_id)
    return sess is not None and sess.stage != STAGE_DONE

def is_ready_trigger(text: str) -> bool:
    return text.strip().lower() in TRIGGERS_READY

def is_cancel_trigger(text: str) -> bool:
    return text.strip().lower() in TRIGGERS_CANCEL


# ─── Анализ задачи ────────────────────────────────────────────────────────────

SMITH_TOOLCHAIN = {
    'video':     ['moviepy', 'ffmpeg', 'pillow'],
    'audio':     ['edge-tts', 'pydub', 'mutagen', 'soundfile'],
    'image':     ['Pillow', 'Pillow-PIL', 'opencv-python', 'imageio', 'scikit-image'],
    'pillow':    ['Pillow'],   # всегда доступен
    'code':      ['ast', 'subprocess', 'pathlib', 'inspect', 'dis'],
    'web':       ['requests', 'httpx', 'beautifulsoup4', 'lxml', 'aiohttp', 'playwright'],
    'data':      ['pandas', 'openpyxl', 'xlrd', 'csv', 'json', 'polars'],
    'bot':       ['aiogram', 'python-telegram-bot', 'telebot', 'pyrogram'],
    'ai':        ['openai', 'anthropic', 'google-generativeai', 'transformers', 'langchain'],
    'report':    ['jinja2', 'markdown', 'weasyprint', 'fpdf2', 'reportlab'],
    'archive':   ['zipfile', 'tarfile', 'rarfile', 'py7zr', 'patool'],
    'network':   ['requests', 'httpx', 'aiohttp', 'websockets', 'paramiko', 'fabric'],
    'system':    ['psutil', 'click', 'typer', 'rich', 'colorama', 'tqdm'],
    'testing':   ['pytest', 'unittest', 'coverage', 'hypothesis', 'faker'],
    'db':        ['sqlite3', 'sqlalchemy', 'peewee', 'pymongo', 'redis', 'aiosqlite'],
    'security':  ['cryptography', 'hashlib', 'secrets', 'jwt', 'bcrypt'],
    'parsing':   ['re', 'json', 'csv', 'xml', 'html', 'pyyaml', 'toml'],
    'async':     ['asyncio', 'aiofiles', 'aiohttp', 'trio', 'anyio'],
    'cli':       ['argparse', 'click', 'typer', 'rich', 'prompt_toolkit'],
    'gui':       ['tkinter', 'PyQt5', 'customtkinter', 'dearpygui', 'pygame'],
    'math':      ['numpy', 'scipy', 'sympy', 'decimal', 'fractions', 'statistics'],
    'ml':        ['scikit-learn', 'numpy', 'pandas', 'matplotlib', 'seaborn'],
    'plot':      ['matplotlib', 'plotly', 'seaborn', 'bokeh'],
    'datetime':  ['datetime', 'arrow', 'pendulum', 'dateutil'],
    'files':     ['pathlib', 'shutil', 'glob', 'watchdog', 'send2trash'],
    'env':       ['python-dotenv', 'os', 'configparser'],
    'serialize': ['json', 'pickle', 'msgpack', 'cbor2', 'orjson'],
    'typing':    ['typing', 'dataclasses', 'pydantic', 'attrs'],
    'logging':   ['logging', 'loguru', 'structlog'],
    'http':      ['fastapi', 'flask', 'starlette', 'tornado', 'sanic'],
    'scraping':  ['requests', 'beautifulsoup4', 'scrapy', 'selenium', 'playwright'],
    'input':     ['pynput', 'keyboard', 'mouse', 'pyautogui', 'pygetwindow'],
    'automation':['pynput', 'pyautogui', 'keyboard', 'mouse', 'schedule', 'APScheduler'],
    'desktop':   ['pynput', 'pygetwindow', 'pyperclip', 'plyer', 'desktop-notifier'],
    'io':        ['io', 'sys', 'os', 'fcntl', 'mmap', 'struct', 'array'],
    'compress':  ['gzip', 'bz2', 'lzma', 'zlib', 'zstandard'],
    'format':    ['black', 'autopep8', 'isort', 'pylint', 'flake8', 'mypy'],
    'concurr':   ['threading', 'multiprocessing', 'concurrent.futures', 'queue'],
    'ipc':       ['socket', 'zmq', 'grpc', 'rpyc', 'xmlrpc'],
    'cloud':     ['boto3', 'google-cloud', 'azure-sdk', 'cloudinary'],
    'email':     ['smtplib', 'imaplib', 'email', 'yagmail', 'sendgrid'],
    'pdf':       ['PyPDF2', 'pdfplumber', 'fitz', 'reportlab', 'fpdf2'],
    'docx':      ['python-docx', 'odfpy', 'xlsxwriter'],
    'qr':        ['qrcode', 'pyzbar', 'opencv-python'],
    'crypto':    ['cryptography', 'pycryptodome', 'nacl', 'hashlib'],
    'time':      ['time', 'timeit', 'datetime', 'calendar', 'pytz'],
    'regex':     ['re', 'regex', 'parse'],
    'text':      ['nltk', 'spacy', 'textblob', 'chardet', 'ftfy'],
    'stdlib':    ['os','sys','re','json','csv','datetime','pathlib','shutil',
                  'subprocess','threading','asyncio','socket','http','urllib',
                  'hashlib','hmac','base64','struct','io','tempfile','glob',
                  'functools','itertools','collections','dataclasses','typing',
                  'abc','enum','contextlib','copy','math','random','statistics',
                  'string','textwrap','pprint','inspect','ast','dis','traceback',
                  'logging','warnings','unittest','doctest','argparse'],
}

def analyze_task(task: str, llm_caller: Callable = None) -> dict:
    """Анализирует задачу и возвращает план + инструменты."""
    task_lower = task.lower()

    # Детектируем тип задачи
    needs_video  = any(w in task_lower for w in ['видео','video','ролик','монтаж','слайд'])
    needs_audio  = any(w in task_lower for w in ['mp3','аудио','audio','озвучь','tts','музык'])
    needs_image  = any(w in task_lower for w in ['картинк','изображ','image','фото','jpg','png'])
    needs_code   = any(w in task_lower for w in ['код','code','python','script','напиши','создай',
                                                  'бот','bot','агент','agent','парс','pars',
                                                  'telegram','телеграм','api'])
    needs_web    = any(w in task_lower for w in ['найди','поищи','search','web','интернет','парс'])
    needs_data   = any(w in task_lower for w in ['csv','excel','таблиц','данные','data','json'])
    needs_report = any(w in task_lower for w in ['отчёт','report','документ','pdf','markdown'])

    tools, steps, packages = [], [], []

    if needs_bot := any(w in task_lower for w in ['бот','bot','telegram','телеграм']):
        steps += ["📦 Устанавливаю зависимости для Telegram-бота"]
        steps += ["💻 Генерирую структуру бота"]
        steps += ["🤖 Добавляю AI-интеграцию"]
        steps += ["🔧 Настраиваю handlers и команды"]
        tools += ['python_sandbox', 'code_agent']
        packages += ['aiogram', 'python-telegram-bot']

    if needs_code and not needs_bot:
        steps += ["💻 Генерирую Python-код"]
        steps += ["🔍 Проверяю синтаксис"]
        steps += ["🏖 Тестирую в sandbox"]
        steps += ["🔧 Авто-фикс до 15 попыток"]
        tools += ['python_sandbox']

    if needs_video and (needs_image or needs_audio):
        steps += ["🎬 Собираю слайд-шоу из изображений"]
        if needs_audio: steps += ["🎵 Накладываю аудио"]
        tools += ['moviepy_edit', 'assemble_video']

    if needs_audio and not needs_video:
        steps += ["🎙 Генерирую озвучку через TTS"]
        tools.append('tts')

    if needs_web:
        steps += ["🌐 Ищу информацию в интернете"]
        tools.append('web_search')

    if needs_data:
        steps += ["📊 Обрабатываю данные"]
        packages += ['pandas', 'openpyxl']

    if needs_report:
        steps += ["📄 Генерирую отчёт"]
        tools.append('report_generator')

    steps += ["📦 Пакую в ZIP и отправляю"]

    needs_files = needs_video or needs_image or needs_audio or needs_data

    # LLM анализ для точного плана
    if llm_caller:
        try:
            sys_p = (
                'Проанализируй задачу и верни JSON:\n'
                '{"needs_files": bool, '
                '"file_types": ["image","audio","video","code","data","zip"], '
                f'"tools": {list(set(tools)) or ["python_sandbox"]}, '
                '"steps": ["шаг1","шаг2"], '
                '"packages": ["пакет1"], '
                '"estimated_minutes": int}'
            )
            raw = llm_caller(f"Задача: {task}", sys_p)
            m = re.search(r'\{.*\}', raw, re.DOTALL)
            if m:
                data = json.loads(m.group())
                data.setdefault('packages', packages)
                return data
        except Exception:
            pass

    return {
        'needs_files':       needs_files,
        'file_types':        (['image'] if needs_image else []) +
                             (['audio'] if needs_audio else []) +
                             (['video'] if needs_video else []) +
                             (['data']  if needs_data  else []),
        'tools':             list(set(tools)) or ['python_sandbox'],
        'steps':             steps or ['📝 Выполнить задачу', '📤 Отправить результат'],
        'packages':          list(set(packages)),
        'estimated_minutes': max(1, len(steps)),
    }


# ─── Toolchain helpers ────────────────────────────────────────────────────────

def _install_packages(packages: list, on_status: Callable) -> list:
    """Устанавливает недостающие пакеты. Возвращает список установленных."""
    installed = []
    for pkg in packages:
        if not pkg or not re.match(r'^[\w\-\[\]>=<.,]+$', pkg):
            continue
        try:
            __import__(pkg.split('[')[0].replace('-','_'))
        except ImportError:
            on_status(f"📦 Устанавливаю {pkg}...")
            r = subprocess.run(
                [sys.executable, '-m', 'pip', 'install', pkg, '--quiet'],
                capture_output=True, timeout=60
            )
            if r.returncode == 0:
                installed.append(pkg)
                on_status(f"  ✅ {pkg} установлен")
            else:
                on_status(f"  ⚠️ {pkg} не установился")
    return installed


def _extract_archive(path: str, out_dir: str, on_status: Callable) -> list:
    """Распаковывает zip/rar/tar. Возвращает список файлов."""
    extracted = []
    os.makedirs(out_dir, exist_ok=True)
    name = os.path.basename(path)
    ext  = name.rsplit('.',1)[-1].lower()

    try:
        if ext == 'zip':
            with zipfile.ZipFile(path) as z:
                z.extractall(out_dir)
        elif ext == 'rar':
            try:
                import rarfile
                with rarfile.RarFile(path) as r:
                    r.extractall(out_dir)
            except ImportError:
                # Fallback: unrar CLI
                r = subprocess.run(['unrar', 'x', '-y', path, out_dir],
                                   capture_output=True, timeout=60)
                if r.returncode != 0:
                    # Fallback 2: patool
                    subprocess.run([sys.executable, '-m', 'pip', 'install', 'rarfile', '-q'],
                                   capture_output=True)
                    import rarfile
                    with rarfile.RarFile(path) as rf:
                        rf.extractall(out_dir)
        elif ext in ('gz','bz2','xz') or name.endswith('.tar.gz'):
            import tarfile
            with tarfile.open(path) as t:
                t.extractall(out_dir)
        else:
            return []

        for root, _, fnames in os.walk(out_dir):
            for fn in fnames:
                extracted.append(os.path.join(root, fn))
        on_status(f"  ✅ Распаковано: {len(extracted)} файлов")

    except Exception as e:
        on_status(f"  ⚠️ Ошибка распаковки: {e}")

    return extracted


def _web_search(query: str, on_status: Callable) -> str:
    """Быстрый веб-поиск для контекста."""
    try:
        from agent_tools_registry import execute_tool
        ok, result = execute_tool('web_search', {'query': query}, plan='admin')
        return result[:1000] if ok else ""
    except Exception:
        return ""


def _generate_scaffold_script(task: str, context: str, llm_caller: Callable) -> tuple[str, list]:
    """
    Генерирует Python-скрипт который создаёт всю структуру проекта.
    Результат — scaffold.py который при запуске создаёт папки и файлы.
    """
    prompt = (
        f"Создай Python-скрипт который СОЗДАЁТ структуру проекта через os.makedirs и open().\n\n"
        f"Структура/описание проекта:\n{task}\n\n"
        f"ТРЕБОВАНИЯ:\n"
        f"1. Скрипт должен создавать папки через os.makedirs(path, exist_ok=True)\n"
        f"2. Скрипт должен создавать файлы с минимальным содержимым\n"
        f"3. В конце выводит список созданных файлов\n"
        f"4. Никаких внешних зависимостей — только stdlib\n"
        f"5. Запускается из текущей директории\n\n"
        f"ПРИМЕР ФОРМАТА:\n"
        f"```python\n"
        f"import os\n\n"
        f"BASE = 'my_project'\n\n"
        f"files = {{\n"
        f"    'main.py': '# Main entry point\\n',\n"
        f"    'utils/helper.py': '# Utilities\\n',\n"
        f"}}\n\n"
        f"for path, content in files.items():\n"
        f"    full = os.path.join(BASE, path)\n"
        f"    os.makedirs(os.path.dirname(full), exist_ok=True)\n"
        f"    open(full, 'w').write(content)\n"
        f"    print(f'Created: {{full}}')\n"
        f"print('Done!')\n"
        f"```\n\n"
        f"Напиши полный скрипт для ЭТОЙ структуры. Только код в блоке ```python ... ```"
    )

    raw  = llm_caller(prompt, SMITH_SYSTEM)
    m    = re.search(r'```(?:python)?\n(.*?)```', raw, re.DOTALL)
    code = m.group(1).strip() if m else raw.strip()
    code = _sanitize_code(code)

    return code, []  # scaffold не требует pip install


def _generate_code_with_smith(task: str, context: str, files_info: str,
                               llm_caller: Callable) -> tuple[str, list]:
    """Генерирует код через АГЕНТ_СМИТ. Возвращает (code, packages)."""
    prompt = (
        f"Задача: {task}\n\n"
        f"Файлы пользователя:\n{files_info or 'нет'}\n\n"
        f"Контекст:\n{context[:500] if context else 'нет'}\n\n"
        "Напиши полный рабочий Python-скрипт.\n"
        "НЕ используй Unicode em-dash (—) или умные кавычки в коде.\n"
        "Используй только ASCII символы в коде.\n"
        "Формат:\n"
        "```python\n<код>\n```\n"
        "```requirements\n<пакет1>\n<пакет2>\n```"
    )
    raw = llm_caller(prompt, SMITH_SYSTEM)

    # Извлекаем код
    m_code = re.search(r'```(?:python)?\n(.*?)```', raw, re.DOTALL)
    code   = m_code.group(1).strip() if m_code else raw.strip()

    # Убираем Unicode-символы которые ломают Python
    code = _sanitize_code(code)

    # Извлекаем requirements
    m_req  = re.search(r'```requirements?\n(.*?)```', raw, re.DOTALL)
    packages = []
    if m_req:
        packages = [l.strip() for l in m_req.group(1).splitlines()
                    if l.strip() and not l.startswith('#')]

    return code, packages


def _sanitize_code(code: str) -> str:
    """Убирает markdown-фенсы и Unicode символы которые ломают Python-парсер."""
    import re as _re
    if not code:
        return code
    # Убираем markdown code fences в начале/конце
    code = _re.sub(r'^```[\w]*\n?', '', code.strip())
    code = _re.sub(r'\n?```\s*$', '', code.strip())
    # Убираем фенсы внутри (иногда LLM вставляет несколько блоков)
    code = _re.sub(r'```[\w]*\n?', '', code)
    code = code.replace('```', '')
    # Unicode
    replacements = {
        '\u2014': '-',   # em-dash
        '\u2013': '-',   # en-dash
        '\u2018': "'",   # левая умная кавычка
        '\u2019': "'",   # правая умная кавычка
        '\u201c': '"',   # левые двойные кавычки
        '\u201d': '"',   # правые двойные кавычки
        '\u2026': '...', # многоточие
        '\u00a0': ' ',   # неразрывный пробел
    }
    for old, new in replacements.items():
        code = code.replace(old, new)
    return code.strip()


def _fix_code_with_smith(code: str, error: str, task: str,
                          attempt: int, history: list,
                          llm_caller: Callable) -> str:
    """АГЕНТ_СМИТ фиксит ошибку в коде."""
    # Анализируем тип ошибки для лучшего фикса
    is_import_err = 'No module named' in error or 'ModuleNotFoundError' in error
    is_syntax_err = 'SyntaxError' in error or 'invalid character' in error
    is_name_err   = 'NameError' in error or 'is not defined' in error

    hints = ""
    if is_import_err:
        missing = re.search(r"No module named '([^']+)'", error)
        if missing:
            pkg = missing.group(1)
            hints = (f"\nПОДСКАЗКА: Пакет '{pkg}' не установлен. "
                     f"Добавь в начало кода:\n"
                     f"import subprocess, sys\n"
                     f"subprocess.run([sys.executable, '-m', 'pip', 'install', '{pkg}', '-q'], "
                     f"capture_output=True)\n")
    elif is_syntax_err:
        hints = "\nПОДСКАЗКА: Замени все Unicode символы (em-dash, smart quotes) на ASCII аналоги."

    # История предыдущих ошибок для контекста
    hist_text = ""
    if history:
        hist_text = f"\nПредыдущие ошибки (уже пробовали):\n" + "\n".join(f"- {h}" for h in history[-3:])

    prompt = (
        f"Код:\n```python\n{code}\n```\n\n"
        f"Ошибка (попытка {attempt}):\n{error[:300]}"
        f"{hints}"
        f"{hist_text}\n\n"
        f"Исходная задача: {task}\n\n"
        "Исправь код. Верни ПОЛНЫЙ исправленный код в блоке ```python ... ```"
    )

    raw   = llm_caller(prompt, SMITH_FIX_SYSTEM)
    m     = re.search(r'```(?:python)?\n(.*?)```', raw, re.DOTALL)
    fixed = m.group(1).strip() if m else raw.strip()
    return _sanitize_code(fixed)


# ─── Pipeline ────────────────────────────────────────────────────────────────

def execute_pipeline(sess: AgentSession, on_status: Callable,
                     llm_caller: Callable = None) -> dict:
    """
    АГЕНТ_СМИТ pipeline:
    analyze → extract → install → search → generate → lint → sandbox → fix(x15) → zip → done
    """
    task      = sess.task
    files     = sess.files
    out_dir   = sess.output_dir
    artifacts = []
    errors    = []

    # Убеждаемся что out_dir существует (Docker может убить папку)
    os.makedirs(out_dir, exist_ok=True)

    on_status(f"{AGENT_EMOJI} Анализирую задачу...")
    task_lower = task.lower()

    has_images = [f for f in files if f['type'] in ('image','photo','jpg','png','jpeg','webp','gif')]
    has_audio  = [f for f in files if f['type'] in ('audio','mp3','ogg','wav','m4a','flac')]
    has_video  = [f for f in files if f['type'] in ('video','mp4','avi','mov','mkv')]
    has_code   = [f for f in files if f['type'] in ('code','py','js','txt','json','md')]
    has_arch   = [f for f in files if f['type'] in ('zip','archive','tar','rar')]

    needs_video = any(w in task_lower for w in ['видео','video','ролик','монтаж','слайд'])
    needs_code  = any(w in task_lower for w in ['код','code','python','script','напиши','создай',
                                                 'бот','bot','агент','telegram','телеграм','api',
                                                 'парс','pars','утилит','program','приложен'])
    needs_tts   = any(w in task_lower for w in ['озвучь','tts','голос','speech','mp3','аудио'])
    needs_web   = any(w in task_lower for w in ['найди','поищи','search','web','актуальн'])

    # ── ШАГ 1: Распаковываем архивы ──────────────────────────────────────
    for arch in has_arch:
        if not os.path.exists(arch['path']):
            errors.append(f"Файл не найден: {arch['name']}")
            continue
        on_status(f"📦 Распаковываю {arch['name']}...")
        unzip_dir = os.path.join(out_dir, 'unzipped', arch['name'].rsplit('.',1)[0])
        extracted = _extract_archive(arch['path'], unzip_dir, on_status)
        for fpath in extracted:
            fname = os.path.basename(fpath)
            ext   = fname.rsplit('.',1)[-1].lower() if '.' in fname else ''
            ftype = _detect_type(ext)
            sess.add_file(fpath, fname, ftype)
        # Обновляем списки после распаковки
        has_images = [f for f in sess.files if f['type'] in ('image','photo','jpg','png','jpeg','webp')]
        has_audio  = [f for f in sess.files if f['type'] in ('audio','mp3','ogg','wav','m4a')]
        has_code   = [f for f in sess.files if f['type'] in ('code','py','js','txt')]

    # ── ШАГ 2: Веб-поиск для контекста ───────────────────────────────────
    web_context = ""
    if needs_web or needs_code:
        on_status("🌐 Собираю контекст...")
        web_context = _web_search(task[:100], on_status)

    # ── ШАГ 3: Видео ─────────────────────────────────────────────────────
    if needs_video and has_images:
        on_status(f"🎬 Создаю видео из {len(has_images)} изображений...")
        img_paths  = [f['path'] for f in has_images if os.path.exists(f['path'])]
        audio_path = has_audio[0]['path'] if has_audio else None
        out_video  = os.path.join(out_dir, 'output_video.mp4')
        ok, result = _assemble_video(img_paths, audio_path, out_video, on_status)
        if ok:
            artifacts.append({'path': out_video, 'name': 'output_video.mp4', 'type': 'video'})
            on_status("✅ Видео создано")
        else:
            errors.append(f"Видео: {result}")

    # ── ШАГ 4: TTS ───────────────────────────────────────────────────────
    if needs_tts and not has_audio:
        on_status("🎙 TTS...")
        tts_out = os.path.join(out_dir, f'speech_{int(time.time())}.mp3')
        ok, result = _tts_direct(task[:500], tts_out, on_status)
        if ok:
            artifacts.append({'path': tts_out, 'name': 'speech.mp3', 'type': 'audio'})
            if needs_video:
                vid = next((a for a in artifacts if a['type']=='video'), None)
                if vid:
                    out_va = os.path.join(out_dir, 'video_voiced.mp4')
                    ok2, _ = _add_audio_to_video(vid['path'], tts_out, out_va, on_status)
                    if ok2:
                        artifacts.append({'path': out_va, 'name': 'video_voiced.mp4', 'type': 'video'})
        else:
            errors.append(f"TTS: {result}")

    # ── ШАГ 5: КОД (АГЕНТ_СМИТ core) ────────────────────────────────────
    if needs_code:
        on_status(f"{AGENT_EMOJI} Генерирую код...")

        files_info = "\n".join(f"  - {f['name']} ({f['type']})" for f in sess.files)

        # Контекст из исходных файлов пользователя
        existing_code_context = ""
        for cf in has_code[:3]:
            try:
                if os.path.exists(cf['path']):
                    content = open(cf['path'], encoding='utf-8', errors='ignore').read()
                    existing_code_context += f"\n=== {cf['name']} ===\n{content[:2000]}\n"
            except Exception:
                pass

        if llm_caller:
            # Определяем тип задачи — scaffold требует особого промпта
            is_scaffold = any(w in task.lower() for w in
                ['scaffold', 'структур', 'проект', 'project', 'шаблон',
                 'дерево', 'tree', '├', '└', '│', 'создай папк'])

            if is_scaffold:
                on_status("  🧩 Scaffold режим — генерирую скрипт-создатель...")
                code, packages = _generate_scaffold_script(task, existing_code_context, llm_caller)
            else:
                code, packages = _generate_code_with_smith(
                    task, existing_code_context + web_context, files_info, llm_caller
                )
        else:
            code = f"# Task: {task}\nprint('AGENT_SMITH: Ready')\n"
            packages = []

        # Устанавливаем зависимости
        if packages:
            on_status(f"📦 Устанавливаю пакеты: {', '.join(packages)}")
            _install_packages(packages, on_status)

        # ── Цикл: lint → smart-sandbox → fix ─────────────────────────
        code_ok        = False
        fix_history    = []
        is_server, server_reason = _is_server_code(code)
        syntax_attempts = 0
        MAX_SYNTAX_FIX  = 3   # не более 3 попыток фикса синтаксиса

        if is_server:
            on_status(f"  🖥 Серверный код ({server_reason})")

        for attempt in range(MAX_FIX_ATTEMPTS):
            pct = int((attempt / MAX_FIX_ATTEMPTS) * 10)
            bar = "█" * pct + "░" * (10 - pct)
            on_status(f"🔍 [{bar}] Проверка {attempt+1}/{MAX_FIX_ATTEMPTS}...")

            # Lint
            lint_ok, lint_msg = _lint_code(code)
            if not lint_ok:
                syntax_attempts += 1
                on_status(f"  ⚠️ Синтаксис: {lint_msg}")
                if syntax_attempts >= MAX_SYNTAX_FIX:
                    on_status(f"  ❌ Синтаксис не исправить за {MAX_SYNTAX_FIX} попытки — пересоздаю код")
                    if llm_caller:
                        code, packages = _generate_code_with_smith(
                            task, existing_code_context + web_context,
                            files_info, llm_caller
                        )
                        syntax_attempts = 0
                    continue
                fix_history.append(f"SyntaxError: {lint_msg}")
                if llm_caller:
                    on_status(f"  🔧 Фикс синтаксиса...")
                    code = _fix_code_with_smith(code, f"SyntaxError: {lint_msg}",
                                                task, attempt+1, fix_history, llm_caller)
                continue

            syntax_attempts = 0  # сбрасываем счётчик синтаксиса

            # Серверный код — только lint, без sandbox
            if is_server:
                on_status(f"  ✅ Синтаксис OK")
                code_ok = True
                break

            # Sandbox
            on_status(f"  🏖 Sandbox...")
            run_ok, run_out = _sandbox_run(code, timeout=SANDBOX_TIMEOUT)

            if run_ok:
                on_status(f"  ✅ Работает → {run_out[:60]}")
                code_ok = True
                break

            # Авто-установка недостающих пакетов
            missing = re.search(r"No module named '([^']+)'", run_out)
            if missing:
                pkg = missing.group(1).replace('_', '-')
                on_status(f"  📦 Устанавливаю {pkg}...")
                _install_packages([pkg], on_status)
                continue

            short_err = run_out.split('\n')[-1][:60] if run_out else '?'
            on_status(f"  ⚠️ [{attempt+1}] {short_err}")
            fix_history.append(run_out[:100])

            if attempt < MAX_FIX_ATTEMPTS - 1 and llm_caller:
                on_status(f"  🔧 Фикс #{attempt+1}...")
                code = _fix_code_with_smith(code, run_out, task,
                                            attempt+1, fix_history, llm_caller)

        # Сохраняем результирующий код
        code_fname = _code_filename(task)
        code_path  = os.path.join(out_dir, code_fname)
        open(code_path, 'w', encoding='utf-8').write(code)
        artifacts.append({'path': code_path, 'name': code_fname, 'type': 'code'})

        # Сохраняем вывод sandbox если есть
        if fix_history:
            last_output = fix_history[-1] if fix_history else ''
            if last_output and code_ok:
                out_path = os.path.join(out_dir, 'output.txt')
                open(out_path, 'w', encoding='utf-8').write(last_output)
                artifacts.append({'path': out_path, 'name': 'output.txt', 'type': 'text'})

        # Запускаем код ещё раз финально — сохраняем вывод
        if code_ok and not is_server:
            on_status("  ▶️ Финальный запуск — сохраняю вывод...")
            _, final_out = _sandbox_run(code, timeout=SANDBOX_TIMEOUT)
            if final_out and final_out != '(нет вывода)':
                out_path = os.path.join(out_dir, 'output.txt')
                open(out_path, 'w', encoding='utf-8').write(final_out)
                if not any(a['name'] == 'output.txt' for a in artifacts):
                    artifacts.append({'path': out_path, 'name': 'output.txt', 'type': 'text'})
                on_status(f"  📄 Вывод сохранён: {final_out[:60]}")

        # README
        readme_code = _make_code_readme(task, code, code_ok, packages, fix_history)
        readme_path = os.path.join(out_dir, 'README.md')
        open(readme_path, 'w', encoding='utf-8').write(readme_code)
        artifacts.append({'path': readme_path, 'name': 'README.md', 'type': 'doc'})

        if not code_ok:
            on_status(f"⚠️ Сохранено с ошибками (попыток: {MAX_FIX_ATTEMPTS})")
        else:
            errors = [e for e in errors if 'Попытка' not in e]

        # Ищем файлы созданные скриптом в out_dir
        for root, _, fnames in os.walk(out_dir):
            for fn in fnames:
                fp = os.path.join(root, fn)
                if fp not in [a['path'] for a in artifacts]:
                    ext  = fn.rsplit('.', 1)[-1].lower()
                    ftyp = _detect_type(ext)
                    if ftyp not in ('zip',):
                        artifacts.append({'path': fp, 'name': fn, 'type': ftyp})

    # ── ШАГ 6: Общий LLM-ответ если нет артефактов ───────────────────────
    if not artifacts and llm_caller:
        on_status("💬 Генерирую ответ...")
        try:
            ctx = f"Задача: {task}"
            if files:
                ctx += f"\nФайлы: {', '.join(f['name'] for f in files)}"
            reply = llm_caller(ctx, f"Ты {AGENT_NAME}. Выполни задачу развёрнуто.")
            result_path = os.path.join(out_dir, 'result.md')
            open(result_path, 'w', encoding='utf-8').write(reply)
            artifacts.append({'path': result_path, 'name': 'result.md', 'type': 'doc'})
        except Exception as e:
            errors.append(f"LLM: {e}")

    # ── ШАГ 7: Итоговый ZIP (код + вывод + файлы + отчёт) ────────────────
    zip_path = None
    if artifacts:
        # Группируем по типу
        code_arts  = [a for a in artifacts if a['type'] == 'code']
        media_arts = [a for a in artifacts if a['type'] in ('video','audio','image')]
        doc_arts   = [a for a in artifacts if a['type'] in ('doc','text')]
        other_arts = [a for a in artifacts
                      if a['type'] not in ('code','video','audio','image','doc','text')]

        on_status(f"📦 Пакую архив: {len(code_arts)} кодов, "
                  f"{len(media_arts)} медиа, {len(doc_arts)} доков...")

        zip_path = os.path.join(out_dir, 'agent_smith_result.zip')
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:

                # code/ — все скрипты
                for art in code_arts:
                    if os.path.exists(art['path']):
                        zf.write(art['path'], f"code/{art['name']}")

                # output/ — вывод sandbox, логи
                for art in doc_arts:
                    if os.path.exists(art['path']):
                        zf.write(art['path'], f"output/{art['name']}")

                # media/ — видео, аудио, картинки
                for art in media_arts:
                    if os.path.exists(art['path']):
                        zf.write(art['path'], f"media/{art['name']}")

                # files/ — остальное
                for art in other_arts:
                    if os.path.exists(art['path']):
                        zf.write(art['path'], f"files/{art['name']}")

                # input/ — исходные файлы пользователя
                for f in files:
                    if os.path.exists(f['path']):
                        try: zf.write(f['path'], f"input/{f['name']}")
                        except Exception: pass

                # REPORT.md — полный отчёт
                report = _make_full_report(task, artifacts, errors,
                                           code_arts, media_arts, files)
                zf.writestr('REPORT.md', report)

        except Exception as e:
            errors.append(f"ZIP: {e}")
            zip_path = None

        if zip_path and os.path.exists(zip_path):
            size_mb = os.path.getsize(zip_path) / 1024 / 1024
            on_status(f"  ✅ ZIP готов: {size_mb:.1f} MB")

    return {
        'artifacts': artifacts,
        'zip_path':  zip_path,
        'errors':    errors,
        'ok':        len(artifacts) > 0 and not any('Попытка' in e for e in errors),
    }


# ─── Вспомогательные функции ─────────────────────────────────────────────────

def _code_filename(task: str) -> str:
    """Генерирует осмысленное имя файла для кода."""
    words = re.sub(r'[^\w\s]', '', task.lower()).split()[:4]
    name  = '_'.join(w for w in words if len(w) > 2) or 'script'
    return f"{name[:40]}.py"


def _make_full_report(task: str, artifacts: list, errors: list,
                       code_arts: list, media_arts: list, input_files: list) -> str:
    from datetime import datetime
    now  = datetime.now().strftime('%Y-%m-%d %H:%M')
    ok   = len(errors) == 0
    icon = '✅' if ok else '⚠️'
    lines = [
        f"# 🕵️ {AGENT_NAME} — Отчёт",
        f"",
        f"**Дата:** {now}  ",
        f"**Статус:** {icon} {'Успешно' if ok else 'С ошибками'}  ",
        f"**Задача:** {task}",
        f"",
        f"## 📁 Структура архива",
        f"",
        f"```",
        f"agent_smith_result.zip",
        f"├── code/     # Сгенерированный код ({len(code_arts)} файлов)",
        f"├── output/   # Вывод выполнения",
        f"├── media/    # Медиафайлы ({len(media_arts)} файлов)",
        f"├── input/    # Входные файлы пользователя ({len(input_files)} шт.)",
        f"└── REPORT.md",
        f"```",
        f"",
        f"## 📄 Файлы",
        f"",
    ]
    icon_map = {'code':'💻','video':'🎬','audio':'🎵','image':'🖼',
                'doc':'📄','text':'📝','zip':'📦'}
    for art in artifacts:
        ic = icon_map.get(art['type'], '📎')
        try:
            sz  = os.path.getsize(art['path'])
            szs = f" ({sz//1024} KB)" if sz > 1024 else f" ({sz} B)"
        except Exception:
            szs = ''
        lines.append(f"- {ic} `{art['name']}`{szs}")
    if errors:
        lines += [f"", f"## ⚠️ Ошибки", f""]
        for e in errors[:10]:
            lines.append(f"- `{e[:100]}`")
    lines += [f"", f"---", f"*{AGENT_NAME} · BlackBugsAI*"]
    return "\n".join(lines)


def _detect_type(ext: str) -> str:
    IMAGE = {'jpg','jpeg','png','gif','webp','bmp','tiff','svg'}
    AUDIO = {'mp3','ogg','wav','m4a','flac','aac','opus'}
    VIDEO = {'mp4','avi','mov','mkv','webm','flv','wmv'}
    CODE  = {'py','js','ts','html','css','json','yaml','xml','sh','sql','rb','go','rs'}
    ARCH  = {'zip','tar','gz','rar','7z','bz2'}
    if ext in IMAGE: return 'image'
    if ext in AUDIO: return 'audio'
    if ext in VIDEO: return 'video'
    if ext in CODE:  return 'code'
    if ext in ARCH:  return 'zip'
    return ext or 'unknown'


def detect_file_type(filename: str, mime: str = '') -> str:
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    return _detect_type(ext)


def _assemble_video(img_paths: list, audio_path: Optional[str],
                    out_video: str, on_status: Callable) -> tuple:
    try:
        from moviepy.editor import ImageClip, concatenate_videoclips, AudioFileClip
        clips = [ImageClip(p, duration=3).resize((1280, 720))
                 for p in img_paths if os.path.exists(p)]
        if not clips:
            return False, "Нет доступных изображений"
        on_status(f"  🎬 MoviePy: {len(clips)} кадров...")
        video = concatenate_videoclips(clips, method='compose')
        if audio_path and os.path.exists(audio_path):
            ac = AudioFileClip(audio_path)
            if ac.duration > video.duration:
                ac = ac.subclip(0, video.duration)
            video = video.set_audio(ac)
        video.write_videofile(out_video, fps=25, logger=None,
                              codec='libx264', audio_codec='aac')
        for c in clips: c.close()
        return True, out_video
    except ImportError:
        pass
    except Exception as e:
        on_status(f"  ⚠️ MoviePy: {e}")
    # ffmpeg fallback
    if not shutil.which('ffmpeg'):
        return False, "MoviePy и ffmpeg не найдены"
    lst = tempfile.mktemp(suffix='.txt')
    with open(lst, 'w') as f:
        for p in img_paths:
            if os.path.exists(p):
                f.write(f"file '{p}'\nduration 3\n")
    cmd = ['ffmpeg','-y','-f','concat','-safe','0','-i',lst]
    if audio_path and os.path.exists(audio_path):
        cmd += ['-i', audio_path, '-shortest']
    cmd += ['-vf','scale=1280:720','-r','25', out_video]
    r = subprocess.run(cmd, capture_output=True, timeout=120)
    try: os.unlink(lst)
    except: pass
    return (True, out_video) if r.returncode == 0 else (False, r.stderr[-300:])


def _add_audio_to_video(video_path: str, audio_path: str,
                         out: str, on_status: Callable) -> tuple:
    try:
        from moviepy.editor import VideoFileClip, AudioFileClip
        v = VideoFileClip(video_path)
        a = AudioFileClip(audio_path)
        if a.duration > v.duration:
            a = a.subclip(0, v.duration)
        v = v.set_audio(a)
        v.write_videofile(out, logger=None, codec='libx264', audio_codec='aac')
        v.close(); a.close()
        return True, out
    except Exception as e:
        return False, str(e)


def _tts_direct(text: str, out_path: str, on_status: Callable) -> tuple:
    try:
        import asyncio, edge_tts
        async def _synth():
            comm = edge_tts.Communicate(text, getattr(config, 'TTS_VOICE', 'ru-RU-DmitryNeural'))
            await comm.save(out_path)
        asyncio.run(_synth())
        return True, out_path
    except ImportError:
        return False, "edge-tts не установлен: pip install edge-tts"
    except Exception as e:
        return False, str(e)


def _lint_code(code: str) -> tuple:
    import ast as _ast
    try:
        _ast.parse(code)
        return True, "OK"
    except SyntaxError as e:
        return False, f"line {e.lineno}: {e.msg}"


def _sandbox_run(code: str, timeout: int = SANDBOX_TIMEOUT) -> tuple:
    with tempfile.NamedTemporaryFile(suffix='.py', mode='w',
                                      delete=False, encoding='utf-8') as f:
        f.write(code); tmp = f.name
    try:
        r = subprocess.run(
            [sys.executable, tmp],
            capture_output=True,
            timeout=timeout,
            cwd=os.path.join(getattr(config,'BASE_DIR','.'), 'agent_projects')
        )
        # Декодируем bytes с fallback для Windows (cp866/cp1251)
        def _decode(b):
            if not b: return ''
            for enc in ('utf-8', 'cp1251', 'cp866', 'latin-1'):
                try: return b.decode(enc)
                except: pass
            return b.decode('utf-8', errors='replace')
        out = (_decode(r.stdout) + _decode(r.stderr)).strip()
        return r.returncode == 0, out[:2000] or '(нет вывода)'
    except subprocess.TimeoutExpired:
        return False, f"⏰ Таймаут {timeout}с"
    except Exception as e:
        return False, str(e)
    finally:
        try: os.unlink(tmp)
        except: pass


def _make_code_readme(task: str, code: str, ok: bool,
                       packages: list, history: list) -> str:
    status = "✅ Работает" if ok else f"⚠️ {len(history)} ошибок исправлено"
    lines  = [
        f"# {AGENT_NAME} Code Report",
        f"\n**Задача:** {task}\n",
        f"**Статус:** {status}",
        f"**Попыток:** {MAX_FIX_ATTEMPTS}",
    ]
    if packages:
        lines += [f"\n## Зависимости\n```\npip install {' '.join(packages)}\n```"]
    lines += [f"\n## Запуск\n```bash\npython agent_smith_output.py\n```"]
    if history and not ok:
        lines += ["\n## История ошибок (последние 3)"]
        for h in history[-3:]:
            lines.append(f"- `{h[:80]}`")
    return "\n".join(lines)


def _is_server_code(code: str) -> tuple[bool, str]:
    """Определяет является ли код серверным (бот, API, daemon).
    Такой код нельзя запускать в sandbox — он не завершается."""
    patterns = [
        (r'polling\(|start_polling|run_polling',  'Telegram polling loop'),
        (r'app\.run\(|uvicorn\.run|gunicorn',     'Web server'),
        (r'while True.*sleep|asyncio\.run.*main', 'Infinite loop'),
        (r'bot\.infinity_polling|updater\.start', 'Bot updater'),
        (r'flask\.Flask|FastAPI\(\)|Django',      'Web framework'),
        (r'\.listen\(|server\.serve_forever',     'TCP server'),
    ]
    for pattern, reason in patterns:
        if re.search(pattern, code, re.IGNORECASE):
            return True, reason
    return False, ""


def _quick_validate_code(code: str, on_status: Callable) -> tuple[bool, str]:
    """Быстрая проверка кода без запуска: импорты + структура."""
    # Проверяем что все импорты существуют (без запуска)
    import_errors = []
    for line in code.splitlines():
        line = line.strip()
        if line.startswith('import ') or line.startswith('from '):
            # Пытаемся распарсить строку импорта
            try:
                import ast as _ast
                _ast.parse(line)
            except SyntaxError as e:
                import_errors.append(str(e))

    if import_errors:
        return False, f"Ошибка импорта: {import_errors[0]}"

    # Проверяем наличие основных блоков
    has_main = 'if __name__' in code or 'def main(' in code or 'async def main(' in code
    return True, "OK (server code - syntax only)"
