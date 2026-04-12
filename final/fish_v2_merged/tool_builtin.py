"""
core/tools/builtin.py — Встроенные инструменты агента.

Регистрирует все базовые инструменты в registry.
"""

import os
import sys
import json
import time
import shutil
import logging
import subprocess
import urllib.request
import urllib.parse

logger = logging.getLogger('tools.builtin')


# ── TTS — Text to Speech ──────────────────────────────────────────

def tool_tts(user_id: int, args: dict, session, bot=None) -> dict:
    """
    Озвучивает текст через edge-tts.
    args: {text, voice?, output_path?}
    returns: {success, file_path, error}
    """
    text  = args.get('text', '').strip()
    voice = args.get('voice', 'ru-RU-DmitryNeural')
    if not text:
        return {'success': False, 'error': 'Нет текста для озвучки'}

    out_dir  = session.files_dir
    out_file = os.path.join(out_dir, f'tts_{int(time.time())}.mp3')

    try:
        result = subprocess.run(
            ['edge-tts', '--voice', voice, '--text', text, '--write-media', out_file],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode == 0 and os.path.exists(out_file):
            return {'success': True, 'file_path': out_file,
                    'message': f'Аудио создано: {os.path.basename(out_file)}'}
        return {'success': False, 'error': result.stderr[:300]}
    except FileNotFoundError:
        return {'success': False, 'error': 'edge-tts не установлен. pip install edge-tts'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


# ── Code Execution ────────────────────────────────────────────────

def tool_code(user_id: int, args: dict, session, bot=None) -> dict:
    """
    Пишет и выполняет Python код в sandbox.
    args: {code, description?}
    returns: {success, stdout, stderr, elapsed}
    """
    from sandbox import execute_code, format_result
    code = args.get('code', '')
    if not code:
        return {'success': False, 'error': 'Нет кода для выполнения'}

    result = execute_code(
        code=code,
        user_id=user_id,
        user_dir=session.sandbox_dir,
    )
    return result


# ── Image Generation ──────────────────────────────────────────────

def tool_image(user_id: int, args: dict, session, bot=None) -> dict:
    """
    Генерирует картинку.
    args: {prompt, provider?}
    returns: {success, file_path, error}
    """
    prompt   = args.get('prompt', '')
    provider = args.get('provider', 'pollinations')

    if not prompt:
        return {'success': False, 'error': 'Нет промпта для генерации'}

    out_dir  = session.files_dir
    out_file = os.path.join(out_dir, f'img_{int(time.time())}.png')

    if provider == 'pollinations':
        enc     = urllib.parse.quote(prompt)
        url     = f'https://image.pollinations.ai/prompt/{enc}?width=1024&height=1024&nologo=true'
        try:
            urllib.request.urlretrieve(url, out_file)
            return {'success': True, 'file_path': out_file}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    return {'success': False, 'error': f'Провайдер {provider} не настроен'}


# ── Web Search / Download ─────────────────────────────────────────

def tool_web_search(user_id: int, args: dict, session, bot=None) -> dict:
    """
    Ищет информацию в интернете через DuckDuckGo HTML API.
    args: {query, max_results?}
    returns: {success, results: [{title, url, snippet}]}
    """
    query = args.get('query', '')
    if not query:
        return {'success': False, 'error': 'Нет поискового запроса'}

    max_r = min(args.get('max_results', 5), 10)

    try:
        import re
        enc = urllib.parse.quote_plus(query)
        url = f'https://html.duckduckgo.com/html/?q={enc}'
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (compatible; AutocoderBot/1.0)'
        })
        with urllib.request.urlopen(req, timeout=15) as r:
            html = r.read().decode('utf-8', errors='ignore')

        # Простой парсинг результатов DDG
        results = []
        pattern = re.compile(
            r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>([^<]+)</a>'
            r'.*?<a[^>]+class="result__snippet"[^>]*>([^<]+)</a>',
            re.DOTALL
        )
        for m in pattern.finditer(html):
            url_r, title, snippet = m.groups()
            results.append({
                'url':     url_r.strip(),
                'title':   title.strip(),
                'snippet': snippet.strip()[:200],
            })
            if len(results) >= max_r:
                break

        return {'success': True, 'results': results, 'query': query}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def tool_download(user_id: int, args: dict, session, bot=None) -> dict:
    """
    Скачивает файл по URL.
    args: {url, filename?}
    returns: {success, file_path, size_kb}
    """
    url      = args.get('url', '')
    filename = args.get('filename', f'download_{int(time.time())}')
    if not url:
        return {'success': False, 'error': 'Нет URL'}

    out_path = os.path.join(session.files_dir, filename)
    try:
        urllib.request.urlretrieve(url, out_path)
        size = os.path.getsize(out_path) // 1024
        return {'success': True, 'file_path': out_path, 'size_kb': size}
    except Exception as e:
        return {'success': False, 'error': str(e)}


# ── File Operations ───────────────────────────────────────────────

def tool_files(user_id: int, args: dict, session, bot=None) -> dict:
    """
    Работа с файлами пользователя.
    args: {action: list|read|write|delete, path?, content?}
    """
    action = args.get('action', 'list')
    base   = session.files_dir

    if action == 'list':
        items = []
        for name in os.listdir(base):
            fp   = os.path.join(base, name)
            size = os.path.getsize(fp) // 1024
            items.append({'name': name, 'size_kb': size})
        return {'success': True, 'files': items}

    elif action == 'read':
        path = os.path.join(base, args.get('path', ''))
        if not os.path.exists(path):
            return {'success': False, 'error': 'Файл не найден'}
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read(10000)
        return {'success': True, 'content': content}

    elif action == 'write':
        path    = os.path.join(base, args.get('path', 'output.txt'))
        content = args.get('content', '')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return {'success': True, 'file_path': path}

    elif action == 'delete':
        path = os.path.join(base, args.get('path', ''))
        if os.path.exists(path):
            os.unlink(path)
            return {'success': True}
        return {'success': False, 'error': 'Файл не найден'}

    return {'success': False, 'error': f'Неизвестное действие: {action}'}


# ── Video Assembly ────────────────────────────────────────────────

def tool_video(user_id: int, args: dict, session, bot=None) -> dict:
    """
    Собирает видео из изображений и аудио через ffmpeg.
    args: {images: [path], audio_path?, duration_per_image?, output?}
    returns: {success, file_path}
    """
    images   = args.get('images', [])
    audio    = args.get('audio_path', '')
    duration = args.get('duration_per_image', 3)
    out_name = args.get('output', f'video_{int(time.time())}.mp4')
    out_path = os.path.join(session.files_dir, out_name)

    if not images:
        return {'success': False, 'error': 'Нет изображений'}

    try:
        # Создаём concat-список для ffmpeg
        concat_file = os.path.join(session.sandbox_dir, 'concat.txt')
        with open(concat_file, 'w') as f:
            for img in images:
                f.write(f"file '{img}'\nduration {duration}\n")

        cmd = [
            'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
            '-i', concat_file,
        ]
        if audio and os.path.exists(audio):
            cmd += ['-i', audio, '-shortest']
        cmd += ['-vf', 'fps=25,scale=1280:720:force_original_aspect_ratio=decrease',
                '-c:v', 'libx264', '-pix_fmt', 'yuv420p', out_path]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode == 0:
            return {'success': True, 'file_path': out_path}
        return {'success': False, 'error': result.stderr[-500:]}
    except FileNotFoundError:
        return {'success': False, 'error': 'ffmpeg не установлен'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


# ── Bot Factory ───────────────────────────────────────────────────

def tool_bot_factory(user_id: int, args: dict, session, bot=None) -> dict:
    """
    Создаёт нового Telegram-бота через AutoCoder.
    args: {description, bot_token?}
    returns: {success, project_dir, zip_path}
    """
    description = args.get('description', '')
    if not description:
        return {'success': False, 'error': 'Нет описания бота'}

    try:
        # Добавляем в описание что это Telegram бот
        full_desc = f"Telegram bot: {description}\nUse pyTelegramBotAPI (telebot)"

        # Используем существующий AutoCoder pipeline
        from llm_client import call_llm
        # AutoCoder pipeline используется через llm_client напрямую
        raise NotImplementedError('bot_factory требует autocoder — используй /gen')

        proj_dir = session.projects_dir
        orc = Orchestrator(LLMRouter())
        zip_path = orc.generate(
            description=full_desc,
            run_debug=False,  # быстрее без debug
        )
        return {'success': True, 'zip_path': zip_path,
                'message': f'Бот создан: {os.path.basename(zip_path)}'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


# ── Install Package ───────────────────────────────────────────────

def tool_install(user_id: int, args: dict, session, bot=None) -> dict:
    """
    Устанавливает pip-пакет.
    args: {package}
    """
    package = args.get('package', '')
    if not package:
        return {'success': False, 'error': 'Нет имени пакета'}

    from sandbox import install_package
    ok, output = install_package(user_id, package, session.user_dir)
    return {'success': ok, 'output': output[:500]}


# ── Регистрация всех инструментов ────────────────────────────────

def register_all():
    from tool_registry import registry

    registry.register(
        'tts', 'Озвучить текст (text-to-speech)',
        ['Озвучь это: Привет мир', 'Прочитай вслух текст'],
        tool_tts
    )
    registry.register(
        'code', 'Написать и выполнить Python-код в sandbox',
        ['Вычисли факториал 100', 'Напиши скрипт для...'],
        tool_code
    )
    registry.register(
        'image', 'Сгенерировать изображение по описанию',
        ['Нарисуй кота в космосе', 'Создай картинку: закат'],
        tool_image
    )
    registry.register(
        'web_search', 'Найти информацию в интернете',
        ['Найди последние новости об AI', 'Поищи курс доллара'],
        tool_web_search
    )
    registry.register(
        'download', 'Скачать файл по URL',
        ['Скачай этот файл: https://...', 'Загрузи картинку'],
        tool_download
    )
    registry.register(
        'files', 'Работа с файлами (list/read/write/delete)',
        ['Покажи мои файлы', 'Создай файл с текстом'],
        tool_files
    )
    registry.register(
        'video', 'Собрать видео из картинок и аудио',
        ['Собери видео из этих картинок', 'Создай слайдшоу с озвучкой'],
        tool_video
    )
    registry.register(
        'bot_factory', 'Создать нового Telegram-бота',
        ['Создай бота для напоминаний', 'Сделай бот для погоды'],
        tool_bot_factory
    )
    registry.register(
        'install', 'Установить Python-пакет',
        ['Установи numpy', 'pip install requests'],
        tool_install
    )

    logger.info(f'[tools] Зарегистрировано: {len(registry.tool_names())} инструментов')
