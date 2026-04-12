"""
file_agent.py — анализ файлов присланных пользователем в Telegram.

Поддерживает:
  .zip / .tar.gz  — распаковывает, показывает структуру, анализирует код
  .py .js .ts .go .rs .cpp .java .kt — анализ кода
  .txt .md .log   — анализ текста
  .json .yaml .toml .env — анализ конфигов
  .csv             — статистика по данным
  прочее           — общая информация о файле
"""

import os
import re
import zipfile
import tarfile
import json
import time
from llm_client import call_llm

UPLOADS_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'agent_projects', 'uploads'
)
os.makedirs(UPLOADS_DIR, exist_ok=True)

# Расширения — текст (можно читать и анализировать)
TEXT_EXTENSIONS = {
    '.py', '.js', '.ts', '.jsx', '.tsx', '.go', '.rs', '.cpp', '.c',
    '.java', '.kt', '.swift', '.rb', '.php', '.sh', '.bash',
    '.txt', '.md', '.log', '.csv', '.json', '.yaml', '.yml',
    '.toml', '.env', '.cfg', '.ini', '.xml', '.html', '.css',
    '.sql', '.dockerfile', 'dockerfile', '.gitignore', '.requirements',
}

MAX_FILE_SIZE    = 20 * 1024 * 1024  # 20 MB — лимит Telegram Bot API
MAX_CONTENT_SIZE = 40_000            # символов — сколько шлём в LLM
MAX_TOKENS_ANALYSIS = 4000


def get_dest_path(filename):
    """Путь куда сохранять скачанный файл."""
    ts = time.strftime('%H%M%S')
    safe = re.sub(r'[^\w.\-]', '_', filename)
    return os.path.join(UPLOADS_DIR, '{}_{}'.format(ts, safe))


def analyze_file(file_path, filename, user_hint='', chat_respond_fn=None):
    """
    Главная точка входа.
    file_path     — путь к скачанному файлу
    filename      — оригинальное имя (для определения типа)
    user_hint     — текст сообщения пользователя (контекст)
    chat_respond_fn — если задан, использует историю чата

    Возвращает строку с результатом анализа (HTML для Telegram).
    """
    ext = os.path.splitext(filename.lower())[1]
    size = os.path.getsize(file_path)
    size_str = _fmt_size(size)

    # Архивы
    if ext == '.zip' or filename.lower().endswith('.zip'):
        return _analyze_zip(file_path, filename, size_str, user_hint)
    if ext in ('.gz', '.tgz') or filename.lower().endswith('.tar.gz'):
        return _analyze_tar(file_path, filename, size_str, user_hint)

    # Текстовые файлы
    if ext in TEXT_EXTENSIONS or _is_text(file_path):
        return _analyze_text_file(file_path, filename, ext, size_str, user_hint)

    # Бинарный / неизвестный
    return (
        "📎 <b>{}</b> — {} — бинарный файл\n\n"
        "Не могу прочитать содержимое напрямую. "
        "Если это архив, переименуй в .zip и пришли снова."
    ).format(filename, size_str)


# ════════════════════════════════════════════════════════════
#  ZIP
# ════════════════════════════════════════════════════════════

def _analyze_zip(file_path, filename, size_str, user_hint):
    try:
        with zipfile.ZipFile(file_path, 'r') as zf:
            names = zf.namelist()
    except zipfile.BadZipFile:
        return "❌ Файл повреждён или не является zip-архивом."

    # Структура архива
    structure = _build_tree(names)

    # Читаем текстовые файлы внутри архива
    code_snippets = []
    total_chars = 0
    with zipfile.ZipFile(file_path, 'r') as zf:
        for name in names:
            ext = os.path.splitext(name.lower())[1]
            if ext not in TEXT_EXTENSIONS:
                continue
            try:
                info = zf.getinfo(name)
                if info.file_size > 200_000:  # пропускаем огромные файлы
                    continue
                data = zf.read(name).decode('utf-8', errors='replace')
                if total_chars + len(data) > MAX_CONTENT_SIZE:
                    data = data[:MAX_CONTENT_SIZE - total_chars] + '\n... (обрезано)'
                code_snippets.append('### {}\n{}'.format(name, data))
                total_chars += len(data)
                if total_chars >= MAX_CONTENT_SIZE:
                    break
            except Exception:
                continue

    # Отправляем в LLM
    content_block = '\n\n'.join(code_snippets) if code_snippets else '(нет текстовых файлов)'
    hint = '\nЗапрос пользователя: "{}"\n'.format(user_hint) if user_hint else ''

    prompt = (
        "Проанализируй этот проект из zip-архива.\n"
        "{}"
        "Структура:\n{}\n\n"
        "Содержимое файлов:\n{}"
    ).format(hint, structure, content_block)

    system = (
        "Ты — опытный разработчик. Анализируешь код и проекты.\n"
        "Дай структурированный анализ:\n"
        "1. Что это за проект и для чего\n"
        "2. Архитектура и основные компоненты\n"
        "3. Ключевые зависимости\n"
        "4. Проблемы, баги, улучшения (если видишь)\n"
        "5. Как запустить\n"
        "Отвечай на русском. Код и имена файлов — в `backticks`."
    )

    try:
        analysis = call_llm(prompt, system, max_tokens=MAX_TOKENS_ANALYSIS)
    except Exception as e:
        analysis = "❌ Ошибка LLM: {}".format(e)

    header = (
        "📦 <b>{}</b> — {}\n"
        "📁 Файлов: {}\n\n"
        "<b>Структура:</b>\n<pre>{}</pre>\n\n"
        "<b>Анализ:</b>\n"
    ).format(filename, size_str, len(names), _escape(structure[:1000]))

    return header + _escape_preserve_code(analysis)


# ════════════════════════════════════════════════════════════
#  TAR.GZ
# ════════════════════════════════════════════════════════════

def _analyze_tar(file_path, filename, size_str, user_hint):
    try:
        with tarfile.open(file_path, 'r:*') as tf:
            names = tf.getnames()
    except Exception as e:
        return "❌ Ошибка чтения архива: {}".format(e)

    structure = _build_tree(names)
    return (
        "📦 <b>{}</b> — {}\n"
        "📁 Файлов: {}\n\n"
        "<b>Структура:</b>\n<pre>{}</pre>\n\n"
        "<i>Для глубокого анализа пришли как .zip</i>"
    ).format(filename, size_str, len(names), _escape(structure[:1500]))


# ════════════════════════════════════════════════════════════
#  ТЕКСТОВЫЙ ФАЙЛ
# ════════════════════════════════════════════════════════════

def _analyze_text_file(file_path, filename, ext, size_str, user_hint):
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read(MAX_CONTENT_SIZE)
        truncated = os.path.getsize(file_path) > MAX_CONTENT_SIZE
    except Exception as e:
        return "❌ Не удалось прочитать файл: {}".format(e)

    hint = 'Запрос пользователя: "{}"\n\n'.format(user_hint) if user_hint else ''

    if ext in ('.csv',):
        system = "Ты аналитик данных. Опиши структуру CSV, типы данных, основную статистику, аномалии. На русском."
    elif ext in ('.json', '.yaml', '.yml', '.toml'):
        system = "Ты разработчик. Объясни структуру и назначение этого конфига/данных. На русском."
    elif ext in ('.py', '.js', '.ts', '.go', '.rs', '.cpp', '.java', '.kt'):
        system = (
            "Ты опытный разработчик. Проанализируй код:\n"
            "1. Что делает этот файл\n2. Основные функции/классы\n"
            "3. Проблемы и улучшения\n4. Качество кода\nНа русском."
        )
    else:
        system = "Ты помощник. Проанализируй содержимое файла и ответь на вопрос пользователя. На русском."

    prompt = "{}Файл {}:\n\n{}{}".format(
        hint, filename, content,
        "\n\n... (файл обрезан, показаны первые символы)" if truncated else ""
    )

    try:
        analysis = call_llm(prompt, system, max_tokens=MAX_TOKENS_ANALYSIS)
    except Exception as e:
        analysis = "❌ Ошибка LLM: {}".format(e)

    lines = len(content.splitlines())
    header = "📄 <b>{}</b> — {} — {} строк\n\n".format(filename, size_str, lines)
    return header + _escape_preserve_code(analysis)


# ════════════════════════════════════════════════════════════
#  УТИЛИТЫ
# ════════════════════════════════════════════════════════════

def _build_tree(names, max_lines=40):
    """Строит дерево файлов из списка путей."""
    lines = []
    seen_dirs = set()
    for name in sorted(names)[:max_lines]:
        parts = name.split('/')
        depth = len(parts) - 1
        indent = '  ' * min(depth, 4)
        display = parts[-1] if parts[-1] else parts[-2] + '/'
        # Показываем директории один раз
        if depth > 0:
            parent = '/'.join(parts[:-1])
            if parent not in seen_dirs:
                seen_dirs.add(parent)
        lines.append('{}📄 {}'.format(indent, display) if parts[-1] else '{}📁 {}'.format(indent, display))
    if len(names) > max_lines:
        lines.append('... и ещё {} файлов'.format(len(names) - max_lines))
    return '\n'.join(lines)

def _is_text(path, sample=512):
    """Эвристика: файл текстовый если первые N байт — валидный UTF-8."""
    try:
        with open(path, 'rb') as f:
            chunk = f.read(sample)
        chunk.decode('utf-8')
        return True
    except Exception:
        return False

def _fmt_size(size):
    if size < 1024:
        return '{} B'.format(size)
    elif size < 1024 ** 2:
        return '{:.1f} KB'.format(size / 1024)
    else:
        return '{:.1f} MB'.format(size / 1024 ** 2)

def _escape(text):
    import html
    return html.escape(str(text))

def _escape_preserve_code(text):
    """
    Экранирует HTML но сохраняет `backtick` блоки как <code>.
    LLM часто возвращает `code` — превращаем в Telegram-теги.
    """
    import html, re
    # Сначала временно помечаем backtick-блоки
    parts = re.split(r'(`[^`\n]+?`)', text)
    result = []
    for part in parts:
        if part.startswith('`') and part.endswith('`') and len(part) > 2:
            inner = html.escape(part[1:-1])
            result.append('<code>{}</code>'.format(inner))
        else:
            result.append(html.escape(part))
    return ''.join(result)
