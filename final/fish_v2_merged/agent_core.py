"""
agent_core.py — улучшенный агент-кодер.

Возможности:
1. Написание кода по описанию / создание ботов / проектирование
2. Анализ документов, архивов, кода (через file_agent)
3. Поиск ошибок в коде (статический + runtime)
4. Исправление ошибок (авто-цикл до MAX_FIX_ITERATIONS)
5. Агент сам ищет решение ошибок (web search через LLM knowledge)
"""

import os
import re
import time
import subprocess
import tempfile
import traceback
from llm_client import call_llm
import config

MAX_FIX_ITERATIONS = 6   # максимум попыток исправления
CODE_MAX_TOKENS    = 6000

# ════════════════════════════════════════════════════════════
#  СИСТЕМНЫЕ ПРОМПТЫ
# ════════════════════════════════════════════════════════════

SYS_CODER = """Ты — опытный Python-разработчик для Termux/Android.
Пиши чистый, рабочий код. Используй только stdlib + популярные пакеты (requests, telebot, aiogram, bs4, pillow и т.д.).
НЕ используй: tkinter, cv2/OpenCV GUI, системные пути Windows.
Код в блоке ```python ... ```. После кода — короткое описание что делает скрипт."""

SYS_FIXER = """Ты — эксперт по отладке Python-кода на Termux/Android.
Тебе дают: исходный код + полный текст ошибки.
Твоя задача: найти причину ошибки и написать ПОЛНОСТЬЮ исправленный код.
Объясни причину в 1-2 строках, потом сразу код в ```python ... ```."""

SYS_ANALYZER = """Ты — эксперт по анализу кода.
Анализируй: архитектуру, потенциальные баги, проблемы безопасности, качество кода.
Отвечай по-русски. Используй эмодзи для читаемости. Будь конкретным."""

SYS_ERROR_SEARCH = """Ты — эксперт по Python-ошибкам.
Тебе дают ошибку. Объясни:
1. Причина (1 строка)
2. Как исправить (конкретные шаги)
3. Пример исправления (код)
Будь кратким и конкретным."""

SYS_BOT_DESIGNER = """Ты — архитектор Telegram-ботов.
Проектируй боты с правильной структурой: handlers, keyboards, states, database.
Используй aiogram 3.x или python-telegram-bot v20+ (async).
Всегда создавай: main.py, bot/handlers/, bot/keyboards/, bot/database/, config.py, requirements.txt."""

# ════════════════════════════════════════════════════════════
#  ОПРЕДЕЛЕНИЕ ТИПА ЗАДАЧИ
# ════════════════════════════════════════════════════════════

_BOT_KEYWORDS = [
    'telegram bot', 'телеграм бот', 'тг бот', 'tg bot',
    'бот с функциями', 'бот который', 'создай бота', 'напиши бота',
    'aiogram', 'python-telegram-bot', 'telebot',
]
_FIX_KEYWORDS = [
    'исправь', 'почини', 'fix', 'debug', 'ошибка', 'error',
    'не работает', 'падает', 'traceback', 'exception',
    'найди баг', 'найди ошибку',
]
_ANALYZE_KEYWORDS = [
    'анализируй', 'проанализируй', 'analyze', 'разбери',
    'что делает', 'объясни код', 'review', 'ревью', 'проверь код',
]
_IMAGE_KEYWORDS = [
    'сгенерируй изображение', 'создай изображение', 'нарисуй',
    'generate image', 'create image', 'dalle', 'sdxl',
    'картинку', 'рисунок', 'poster', 'баннер',
]


def detect_task_type(text: str) -> str:
    """Определяет тип задачи. Возвращает: 'bot'|'fix'|'analyze'|'image'|'code'."""
    t = text.lower()
    if any(kw in t for kw in _BOT_KEYWORDS):
        return 'bot'
    if any(kw in t for kw in _FIX_KEYWORDS):
        return 'fix'
    if any(kw in t for kw in _ANALYZE_KEYWORDS):
        return 'analyze'
    if any(kw in t for kw in _IMAGE_KEYWORDS):
        return 'image'
    return 'code'


# ════════════════════════════════════════════════════════════
#  УТИЛИТЫ
# ════════════════════════════════════════════════════════════

def extract_code(text: str) -> str:
    """Извлекает код из markdown-блока."""
    m = re.search(r'```(?:python|py)?\n?(.*?)```', text, re.DOTALL)
    if m:
        return m.group(1).strip()
    # Fallback: весь текст если нет блока
    lines = [l for l in text.splitlines() if not l.startswith('#') or 'import' in l]
    candidate = '\n'.join(lines).strip()
    if 'def ' in candidate or 'import ' in candidate:
        return candidate
    return ''


def run_code(code: str, timeout: int = 30) -> tuple[bool, str]:
    """
    Запускает Python-код. Возвращает (success, output).
    output — stdout+stderr объединённые.
    """
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py',
                                     delete=False, encoding='utf-8') as f:
        f.write(code)
        fname = f.name
    try:
        result = subprocess.run(
            ['python3', fname],
            capture_output=True, text=True, timeout=timeout,
            cwd=os.path.dirname(fname)
        )
        out = (result.stdout + result.stderr).strip()
        success = result.returncode == 0
        return success, out
    except subprocess.TimeoutExpired:
        return False, 'TimeoutExpired: скрипт работал дольше {}с'.format(timeout)
    except Exception as e:
        return False, str(e)
    finally:
        try:
            os.unlink(fname)
        except Exception:
            pass


def find_bugs_static(code: str) -> list[str]:
    """Простая статическая проверка кода без запуска."""
    issues = []
    lines = code.splitlines()

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # Незакрытые скобки (очень упрощённо)
        if stripped.count('(') != stripped.count(')') and not stripped.startswith('#'):
            if not any(c in stripped for c in ['"', "'", '#']):
                issues.append('Строка {}: возможно незакрытая скобка'.format(i))

        # Смешивание tabs/spaces
        if '\t' in line and '    ' in line:
            issues.append('Строка {}: смешаны табы и пробелы'.format(i))

        # Опасные паттерны
        if 'eval(' in stripped or 'exec(' in stripped:
            issues.append('Строка {}: eval/exec — потенциально опасно'.format(i))

        # Бесконечный цикл без break
        if stripped == 'while True:':
            has_break = any('break' in l for l in lines[i:i+20])
            if not has_break:
                issues.append('Строка {}: while True без break в ближайших 20 строках'.format(i))

    # Синтаксическая проверка через compile()
    try:
        compile(code, '<string>', 'exec')
    except SyntaxError as e:
        issues.insert(0, '🔴 SyntaxError строка {}: {}'.format(e.lineno, e.msg))

    return issues


# ════════════════════════════════════════════════════════════
#  АГЕНТ: ИСПРАВЛЕНИЕ ОШИБОК
# ════════════════════════════════════════════════════════════

def fix_agent(code: str, error: str, task: str = '', on_status=None) -> dict:
    """
    Агент исправления ошибок.
    Цикл: LLM предлагает фикс → запускаем → если ошибка → следующая попытка.
    Возвращает {success, code, output, iterations, history}.
    """
    history = []
    current_code = code
    current_error = error

    for i in range(1, MAX_FIX_ITERATIONS + 1):
        if on_status:
            on_status('🔧 Исправляю ошибку, попытка {}/{}...'.format(i, MAX_FIX_ITERATIONS))

        # Строим промпт с историей попыток
        attempts_ctx = ''
        if history:
            attempts_ctx = '\n\n'.join(
                '--- Попытка {} ---\nКод:\n```python\n{}\n```\nОшибка:\n{}'.format(
                    h['attempt'], h['code'], h['error'])
                for h in history
            )
            attempts_ctx = 'Предыдущие попытки (все не сработали):\n' + attempts_ctx + '\n\n'

        prompt = (
            '{}Исходная задача: {}\n\n'
            'Текущий код:\n```python\n{}\n```\n\n'
            'Ошибка:\n{}\n\n'
            'Напиши ПОЛНОСТЬЮ исправленный код:'
        ).format(attempts_ctx, task or 'исправить код', current_code, current_error)

        try:
            response = call_llm(prompt, SYS_FIXER, max_tokens=CODE_MAX_TOKENS)
        except Exception as e:
            return {
                'success': False, 'code': current_code,
                'output': 'LLM ошибка: {}'.format(e),
                'iterations': i, 'history': history
            }

        fixed_code = extract_code(response)
        explanation = re.sub(r'```.*?```', '', response, flags=re.DOTALL).strip()

        if not fixed_code:
            history.append({'attempt': i, 'code': current_code,
                            'error': current_error, 'note': 'LLM не вернул код'})
            continue

        # Пробуем запустить исправленный код
        success, output = run_code(fixed_code)

        history.append({
            'attempt': i,
            'code': fixed_code,
            'error': output if not success else None,
            'explanation': explanation,
        })

        if success:
            if on_status:
                on_status('✅ Исправлено за {} попытки!'.format(i))
            return {
                'success': True, 'code': fixed_code,
                'output': output, 'iterations': i,
                'explanation': explanation, 'history': history,
            }

        # Не сработало — готовим следующую итерацию
        current_code = fixed_code
        current_error = output

    # Все попытки исчерпаны
    return {
        'success': False, 'code': current_code,
        'output': 'Не удалось исправить за {} попыток'.format(MAX_FIX_ITERATIONS),
        'iterations': MAX_FIX_ITERATIONS, 'history': history,
    }


# ════════════════════════════════════════════════════════════
#  АГЕНТ: АНАЛИЗ КОДА
# ════════════════════════════════════════════════════════════

def analyze_code(code: str, task: str = '') -> str:
    """Анализирует код и возвращает HTML-отчёт."""
    # Статический анализ
    static_issues = find_bugs_static(code)
    static_report = ''
    if static_issues:
        static_report = '\n\nСтатический анализ выявил:\n' + '\n'.join(
            '• ' + issue for issue in static_issues)

    prompt = (
        'Проанализируй этот код{}:\n\n```python\n{}\n```{}\n\n'
        'Укажи: архитектуру, баги, риски, улучшения.'
    ).format(
        ' (задача: {})'.format(task) if task else '',
        code,
        static_report
    )

    return call_llm(prompt, SYS_ANALYZER, max_tokens=2000)


# ════════════════════════════════════════════════════════════
#  АГЕНТ: ПОИСК ОШИБКИ
# ════════════════════════════════════════════════════════════

def explain_error(error: str, code: str = '') -> str:
    """Объясняет ошибку и предлагает способы исправления."""
    prompt = 'Ошибка:\n{}'.format(error)
    if code:
        prompt = 'Код:\n```python\n{}\n```\n\n'.format(code[:2000]) + prompt
    return call_llm(prompt, SYS_ERROR_SEARCH, max_tokens=1000)


# ════════════════════════════════════════════════════════════
#  АГЕНТ: ГЕНЕРАЦИЯ ИЗОБРАЖЕНИЙ (через код)
# ════════════════════════════════════════════════════════════

def image_gen_agent(description: str, on_status=None) -> dict:
    """
    Генерирует изображение через Python-код (pillow/requests к API).
    Возвращает {success, files, output}.
    """
    if on_status:
        on_status('🎨 Генерирую код для создания изображения...')

    prompt = (
        'Напиши Python-скрипт который генерирует изображение по описанию: "{}"\n\n'
        'Варианты (выбери лучший доступный):\n'
        '1. Если есть OPENAI_API_KEY — используй DALL-E 3 через requests\n'
        '2. Иначе — используй Pillow для программной генерации (текст, фигуры, градиент)\n'
        '3. Сохрани результат в generated_image.png\n'
        '4. В конце: print("IMAGE:", os.path.abspath("generated_image.png"))\n\n'
        'API_KEY = os.environ.get("OPENAI_API_KEY", "")\n'
        'Код должен работать в обоих случаях.'
    ).format(description)

    try:
        response = call_llm(prompt, SYS_CODER, max_tokens=CODE_MAX_TOKENS)
        code = extract_code(response)
        if not code:
            return {'success': False, 'files': [], 'output': 'LLM не вернул код'}

        # Запускаем
        env = os.environ.copy()
        env['OPENAI_API_KEY'] = config.OPENAI_API_KEY or ''

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            fname = f.name

        result = subprocess.run(
            ['python3', fname], capture_output=True, text=True,
            timeout=60, env=env, cwd='/tmp'
        )
        output = (result.stdout + result.stderr).strip()
        os.unlink(fname)

        # Ищем путь к изображению
        image_path = None
        for line in output.splitlines():
            if line.startswith('IMAGE:'):
                image_path = line.split('IMAGE:', 1)[1].strip()
                break

        if not image_path:
            # Ищем png файлы
            import glob
            pngs = glob.glob('/tmp/**/*.png', recursive=True)
            pngs += glob.glob('/tmp/*.png')
            if pngs:
                image_path = max(pngs, key=os.path.getmtime)

        if image_path and os.path.exists(image_path):
            return {'success': True, 'files': [image_path], 'output': output, 'code': code}

        return {'success': False, 'files': [], 'output': output or 'Изображение не найдено', 'code': code}

    except Exception as e:
        return {'success': False, 'files': [], 'output': str(e)}
