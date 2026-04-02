"""
agent_tools_registry.py — BlackBugsAI Tool Registry
Реестр инструментов AI-агента с поддержкой:
  • тарифных планов (free/pro/business)
  • прав доступа по ролям
  • стоимости (кредиты)
  • схем аргументов
  • статистики запусков
  • sandbox уровней
  • авто-fuzzy поиска инструмента

Формат вызова агентом:
    TOOL: <name>
    ARGS: <json или text>
"""

import os, sys, json, subprocess, threading, time, shutil, importlib, traceback
import config

BASE = config.BASE_DIR

# ─── Авто-установка критических зависимостей ─────────────────────────────────
def _ensure_pillow():
    try:
        from PIL import Image
    except ImportError:
        print("  📦 Устанавливаю Pillow...", flush=True)
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'Pillow', '-q'],
                       capture_output=True)
_ensure_pillow()

# ─── Метаданные инструмента ───────────────────────────────────────────────────

from dataclasses import dataclass, field
from typing import Callable, List, Optional, Any

@dataclass
class ToolMeta:
    name:         str
    desc:         str
    category:     str
    fn:           Callable
    permissions:  List[str] = field(default_factory=lambda: ['user'])
    timeout:      int = 60
    cost:         float = 0.0          # кредиты за вызов
    sandbox:      str = 'soft'         # none | soft | docker
    tags:         List[str] = field(default_factory=list)
    # runtime stats
    runs:         int = 0
    ok_runs:      int = 0
    fail_runs:    int = 0
    avg_ms:       float = 0.0

    @property
    def success_rate(self) -> float:
        return self.ok_runs / self.runs if self.runs else 1.0

    def allows_plan(self, plan: str) -> bool:
        return config.plan_allows_tool(plan, self.name)

    def allows_role(self, role: str) -> bool:
        if role in ('admin', 'owner'): return True
        return role in self.permissions or 'user' in self.permissions


# ─── Реестр ──────────────────────────────────────────────────────────────────

_TOOLS: dict[str, ToolMeta] = {}


def register_tool(name, description, category="general",
                  permissions=None, timeout=60, cost=0.0,
                  sandbox='soft', tags=None):
    """Декоратор для регистрации инструмента."""
    def decorator(fn):
        _TOOLS[name] = ToolMeta(
            name=name, desc=description, fn=fn, category=category,
            permissions=permissions or ['user'],
            timeout=timeout, cost=cost,
            sandbox=sandbox,
            tags=tags or [],
        )
        return fn
    return decorator


def get_tools_list(plan: str = 'free', role: str = 'user') -> str:
    """Строка с описанием доступных инструментов для system-промта агента."""
    by_cat: dict[str, list] = {}
    for t in _TOOLS.values():
        if not t.allows_plan(plan): continue
        if not t.allows_role(role): continue
        by_cat.setdefault(t.category, []).append(t)

    lines = ["📦 ДОСТУПНЫЕ ИНСТРУМЕНТЫ:\n"]
    for cat, tools in sorted(by_cat.items()):
        lines.append(f"[{cat.upper()}]")
        for t in tools:
            cost_str = f" (💳{t.cost})" if t.cost else ""
            lines.append(f"  • {t.name}: {t.desc}{cost_str}")
    return "\n".join(lines)


def execute_tool(name: str, args_raw: Any, chat_id=None, on_status=None,
                 user_id: str = None, plan: str = 'free', role: str = 'user'):
    """Выполняет инструмент. Возвращает (ok: bool, result: str)."""
    # Fuzzy match — ищем похожее имя
    t = _TOOLS.get(name)
    if not t:
        name_lower = name.lower()
        candidates = [k for k in _TOOLS if name_lower in k.lower() or k.lower() in name_lower]
        if candidates:
            t = _TOOLS[candidates[0]]
        else:
            available = ', '.join(sorted(_TOOLS.keys()))
            return False, f"❌ Инструмент '{name}' не найден.\nДоступные: {available}"

    # Проверка тарифа
    if not t.allows_plan(plan):
        return False, (f"❌ Инструмент <b>{t.name}</b> недоступен на тарифе <b>{plan}</b>.\n"
                       f"Upgrade: /billing")

    # Проверка роли
    if not t.allows_role(role):
        return False, f"🚫 Нет прав для инструмента {t.name}. Роль: {role}"

    # Биллинг: списываем кредиты
    if t.cost > 0 and user_id:
        try:
            from billing import BillingManager as _BM
            bm = _BM(user_id)
            if not bm.charge_task(t.name, t.cost):
                return False, f"💳 Недостаточно кредитов для {t.name} (нужно {t.cost}). /billing"
        except ImportError:
            pass  # billing не подключён — пропускаем

    # Парсим аргументы
    try:
        args = json.loads(args_raw) if isinstance(args_raw, str) and str(args_raw).strip().startswith('{') else args_raw
    except Exception:
        args = args_raw

    # Выполнение с таймаутом
    t0 = time.time()
    t.runs += 1
    result_box = [None]
    error_box  = [None]

    def _run():
        try:
            result_box[0] = t.fn(args, chat_id=chat_id, on_status=on_status)
        except Exception as e:
            error_box[0] = f"{type(e).__name__}: {e}\n{traceback.format_exc()[-500:]}"

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    thread.join(timeout=t.timeout)

    elapsed_ms = (time.time() - t0) * 1000
    t.avg_ms = (t.avg_ms * (t.runs - 1) + elapsed_ms) / t.runs

    if thread.is_alive():
        t.fail_runs += 1
        return False, f"⏰ Таймаут {t.timeout}с для инструмента {t.name}"

    if error_box[0]:
        t.fail_runs += 1
        return False, f"❌ Ошибка {t.name}: {error_box[0]}"

    t.ok_runs += 1
    return True, str(result_box[0]) if result_box[0] is not None else "✅ Выполнено"


def parse_tool_calls(text: str) -> list:
    """Парсит TOOL:/ARGS: вызовы из ответа LLM."""
    import re
    calls = []
    for m in re.finditer(r'TOOL:\s*(\S+)\s*\nARGS:\s*(.+?)(?=\nTOOL:|\Z)', text, re.DOTALL):
        calls.append((m.group(1).strip(), m.group(2).strip()))
    for m in re.finditer(r'```tool\s*\n(.+?)```', text, re.DOTALL):
        try:
            data = json.loads(m.group(1))
            calls.append((data.get('tool',''), data.get('args','')))
        except Exception:
            lines = m.group(1).strip().splitlines()
            if lines:
                calls.append((lines[0].strip(), "\n".join(lines[1:]).strip()))
    return calls


def registry_stats() -> dict:
    """Статистика реестра для admin panel."""
    by_cat: dict[str, int] = {}
    for t in _TOOLS.values():
        by_cat[t.category] = by_cat.get(t.category, 0) + 1
    top = sorted(_TOOLS.values(), key=lambda t: t.runs, reverse=True)[:5]
    return {
        'total':      len(_TOOLS),
        'by_category': by_cat,
        'top_tools':  [{'name': t.name, 'runs': t.runs,
                        'rate': round(t.success_rate, 2)} for t in top],
    }

# ─── ИНСТРУМЕНТЫ ──────────────────────────────────────────────────────────────

@register_tool(
    "pillow_image",
    "Обработка изображений через Pillow (PIL). ARGS: {action, input?, output?, width?, height?, text?, color?, font_size?}. "
    "actions: resize | crop | rotate | grayscale | blur | sharpen | thumbnail | watermark | text | convert | info",
    "media",
    permissions=['user'],
    timeout=30,
    sandbox='soft',
    tags=['image','pillow','pil','resize','convert'],
)
def tool_pillow_image(args, chat_id=None, on_status=None):
    import os, time as _t
    from PIL import Image, ImageDraw, ImageFont, ImageFilter

    if isinstance(args, str):
        import json as _j
        try: args = _j.loads(args)
        except: args = {'action': args}

    action     = str(args.get('action', 'info')).lower()
    input_path = args.get('input', '')
    out_dir    = os.path.join(BASE, 'agent_projects')
    os.makedirs(out_dir, exist_ok=True)
    output     = args.get('output', os.path.join(out_dir, f'pil_{int(_t.time())}.png'))

    def _status(m):
        if on_status: on_status(m)

    # Открываем изображение если нужно
    img = None
    if input_path and os.path.exists(input_path):
        img = Image.open(input_path)
    elif action not in ('create', 'text', 'gradient'):
        # Создаём заглушку
        img = Image.new('RGB', (512, 512), color=(50, 50, 80))

    if action == 'info':
        if img:
            return f"📐 {img.size[0]}x{img.size[1]} | {img.mode} | {img.format}"
        return "❌ Файл не найден"

    elif action == 'resize':
        w = int(args.get('width', 512))
        h = int(args.get('height', 512))
        _status(f"🖼 Resize → {w}x{h}")
        img = img.resize((w, h), Image.LANCZOS)
        img.save(output)
        return output

    elif action == 'thumbnail':
        size = int(args.get('size', 256))
        img.thumbnail((size, size), Image.LANCZOS)
        img.save(output)
        return output

    elif action == 'crop':
        x1 = int(args.get('x1', 0)); y1 = int(args.get('y1', 0))
        x2 = int(args.get('x2', img.width)); y2 = int(args.get('y2', img.height))
        img = img.crop((x1, y1, x2, y2))
        img.save(output)
        return output

    elif action == 'rotate':
        deg = int(args.get('degrees', 90))
        img = img.rotate(deg, expand=True)
        img.save(output)
        return output

    elif action == 'grayscale':
        img = img.convert('L').convert('RGB')
        img.save(output)
        return output

    elif action == 'blur':
        radius = float(args.get('radius', 5))
        img = img.filter(ImageFilter.GaussianBlur(radius))
        img.save(output)
        return output

    elif action == 'sharpen':
        img = img.filter(ImageFilter.SHARPEN)
        img.save(output)
        return output

    elif action == 'convert':
        fmt    = str(args.get('format', 'PNG')).upper()
        output = output.rsplit('.', 1)[0] + '.' + fmt.lower()
        img.save(output, format=fmt)
        return output

    elif action in ('text', 'watermark'):
        text  = str(args.get('text', 'BlackBugsAI'))
        color = args.get('color', (255, 255, 255))
        fs    = int(args.get('font_size', 36))
        draw  = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', fs)
        except Exception:
            font = ImageFont.load_default()
        x = int(args.get('x', 10))
        y = int(args.get('y', img.height - fs - 10))
        draw.text((x, y), text, fill=tuple(color) if isinstance(color, list) else color, font=font)
        img.save(output)
        return output

    elif action == 'create':
        w   = int(args.get('width', 512))
        h   = int(args.get('height', 512))
        col = args.get('color', (30, 30, 50))
        img = Image.new('RGB', (w, h), color=tuple(col) if isinstance(col, list) else col)
        img.save(output)
        return output

    return f"❌ Неизвестный action: {action}. Доступны: resize crop rotate grayscale blur sharpen thumbnail watermark text convert info create"

# ── TTS ──────────────────────────────────────────────────────────────────────
@register_tool("tts", "Озвучить текст через TTS (edge-tts или ElevenLabs). ARGS: {text, voice?, lang?}", "media")
def tool_tts(args, chat_id=None, on_status=None):
    import asyncio, tempfile
    if isinstance(args, dict):
        text  = args.get('text', str(args))
        voice = args.get('voice', config.TTS_VOICE)
        lang  = args.get('lang', 'ru')
    else:
        text, voice, lang = str(args), config.TTS_VOICE, 'ru'

    if on_status: on_status("🎙 Генерирую озвучку...")
    provider = config.TTS_PROVIDER.lower()

    out_path = tempfile.mktemp(suffix='.mp3', dir=os.path.join(BASE, 'agent_projects'))
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    if provider in ('eleven', 'elevenlabs', '11labs') and config.ELEVEN_API_KEY:
        try:
            from tts_engine import eleven_tts
            eleven_tts(text, out_path)
        except Exception as e:
            return f"❌ ElevenLabs error: {e}"
    else:
        try:
            import edge_tts as _etts
            async def _run():
                comm = _etts.Communicate(text, voice)
                await comm.save(out_path)
            asyncio.run(_run())
        except Exception as e:
            return f"❌ edge-tts error: {e}"

    if os.path.exists(out_path):
        # Отправляем файл в чат
        if chat_id:
            from telegram_client import send_document
            send_document(out_path, caption=f"🎙 {text[:60]}...", chat_id=chat_id)
        return f"✅ Аудио создано: {out_path}"
    return "❌ Аудио не создано"


# ── ВИДЕО СБОРКА ──────────────────────────────────────────────────────────────
@register_tool("assemble_video",
               "Собрать видео из изображений/аудио/текста через ffmpeg. ARGS: {images:[], audio?, text?, output?}",
               "media")
def tool_assemble_video(args, chat_id=None, on_status=None):
    import tempfile, glob
    if not shutil.which('ffmpeg'):
        return "❌ ffmpeg не установлен. Установи: apt install ffmpeg / pkg install ffmpeg"
    if isinstance(args, str):
        try: args = json.loads(args)
        except: return "❌ Нужен JSON: {images: [...], audio: '...', output: '...'}"

    images  = args.get('images', [])
    audio   = args.get('audio', '')
    output  = args.get('output', os.path.join(BASE, 'agent_projects', f'video_{int(time.time())}.mp4'))
    text    = args.get('text', '')
    fps     = args.get('fps', 1)

    os.makedirs(os.path.dirname(output), exist_ok=True)
    if on_status: on_status(f"🎬 Собираю видео ({len(images)} кадров)...")

    if not images and text:
        # Генерируем слайд с текстом через Pillow
        try:
            from PIL import Image, ImageDraw, ImageFont
            img = Image.new('RGB', (1280, 720), color=(20, 20, 30))
            draw = ImageDraw.Draw(img)
            draw.text((50, 300), text[:200], fill=(255,255,255))
            tmp_img = tempfile.mktemp(suffix='.png')
            img.save(tmp_img)
            images = [tmp_img]
        except ImportError:
            return "❌ Нет Pillow для генерации слайда. pip install Pillow"

    if not images:
        return "❌ Нет изображений для видео"

    # Создаём список файлов для ffmpeg
    list_file = tempfile.mktemp(suffix='.txt')
    with open(list_file, 'w') as f:
        for img in images:
            if os.path.exists(img):
                f.write(f"file '{img}'\nduration {1/fps}\n")

    cmd_parts = ['ffmpeg', '-y', '-f', 'concat', '-safe', '0',
                 '-i', list_file]
    if audio and os.path.exists(audio):
        cmd_parts += ['-i', audio, '-shortest']
    cmd_parts += ['-vf', 'scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720',
                  '-r', '25', output]

    r = subprocess.run(cmd_parts, capture_output=True, text=True, timeout=120)
    try: os.unlink(list_file)
    except: pass

    if r.returncode == 0 and os.path.exists(output):
        if chat_id:
            from telegram_client import send_document
            send_document(output, caption="🎬 Видео готово", chat_id=chat_id)
        return f"✅ Видео создано: {output}"
    return f"❌ ffmpeg error:\n{(r.stderr or r.stdout)[-1000:]}"


# ── ГЕНЕРАЦИЯ ИЗОБРАЖЕНИЯ ────────────────────────────────────────────────────
@register_tool("generate_image",
               "Создать изображение по описанию. ARGS: {prompt, provider?, size?}",
               "media")
def tool_gen_image(args, chat_id=None, on_status=None):
    if isinstance(args, str):
        try: args = json.loads(args)
        except: args = {'prompt': str(args)}
    prompt   = args.get('prompt', str(args))
    provider = args.get('provider', 'auto')
    size     = args.get('size', '1024x1024')
    w, h     = (int(x) for x in size.split('x')) if 'x' in size else (1024, 1024)
    if on_status: on_status(f"🎨 Генерирую: {prompt[:60]}...")

    # Пробуем image_gen если есть
    try:
        from image_gen import generate_image
        path, used = generate_image(prompt, provider=provider, width=w, height=h)
        if chat_id:
            from telegram_client import send_document
            send_document(path, caption=f"🎨 {prompt[:80]}", chat_id=chat_id)
        return f"✅ Изображение: {path} (провайдер: {used})"
    except Exception:
        pass

    # Fallback → pollinations
    if on_status: on_status("🌸 Пробую Pollinations...")
    result = tool_pollinations_image({'prompt': prompt, 'width': w, 'height': h},
                                     chat_id=chat_id, on_status=on_status)
    return result


# ── SANDBOX ───────────────────────────────────────────────────────────────────
@register_tool("sandbox",
               "Запустить Python-код в изолированной среде. ARGS: <код>",
               "code")
def tool_sandbox(args, chat_id=None, on_status=None):
    import tempfile
    code = str(args)
    # Убираем маркеры блока если есть
    import re
    m = re.search(r'```(?:python)?\s*\n(.+?)```', code, re.DOTALL)
    if m: code = m.group(1)

    with tempfile.NamedTemporaryFile(suffix='.py', mode='w', delete=False,
                                     encoding='utf-8') as f:
        f.write(code); tmp = f.name
    try:
        r = subprocess.run([sys.executable, tmp], capture_output=True, text=True,
                           timeout=30, cwd=BASE)
        out = r.stdout[-2000:] or ''
        err = r.stderr[-1000:] or ''
        rc  = r.returncode
        result = f"rc={rc}\n"
        if out: result += f"stdout:\n{out}"
        if err: result += f"\nstderr:\n{err}"
        return result.strip()
    except subprocess.TimeoutExpired:
        return "⏰ Таймаут 30с"
    finally:
        try: os.unlink(tmp)
        except: pass


# ── СОЗДАТЬ НОВЫЙ БОТ ─────────────────────────────────────────────────────────
@register_tool("create_bot",
               "Создать нового Telegram-бота. ARGS: {name, token?, description, features:[]}",
               "bots")
def tool_create_bot(args, chat_id=None, on_status=None):
    if isinstance(args, str):
        try: args = json.loads(args)
        except: args = {'name': str(args), 'description': str(args), 'features': []}

    name     = args.get('name', 'new_bot')
    token    = args.get('token', 'YOUR_TOKEN_HERE')
    desc     = args.get('description', '')
    features = args.get('features', [])

    if on_status: on_status(f"🤖 Создаю бота {name}...")

    # Генерируем через LLM
    from llm_client import call_llm
    prompt = f"""
Создай полный Python-код Telegram-бота с aiogram 3.x.
Название: {name}
Описание: {desc}
Фичи: {', '.join(features) if features else 'базовый бот с меню'}
Токен: {token}

Требования:
- Один файл Python, полностью рабочий
- aiogram 3.x, async/await
- Inline-кнопки для управления
- Обработка ошибок
- Команды /start /help

Верни ТОЛЬКО код, без пояснений.
"""
    code = call_llm(prompt, max_tokens=3000)
    # Очищаем от markdown
    import re
    m = re.search(r'```(?:python)?\s*\n(.+?)```', code, re.DOTALL)
    if m: code = m.group(1)

    # Сохраняем
    bots_dir = os.path.join(BASE, 'created_bots')
    os.makedirs(bots_dir, exist_ok=True)
    bot_path = os.path.join(bots_dir, f'{name}.py')
    req_path = os.path.join(bots_dir, f'{name}_requirements.txt')

    with open(bot_path, 'w', encoding='utf-8') as f:
        f.write(code)
    with open(req_path, 'w') as f:
        f.write("aiogram>=3.0\npython-dotenv\n")

    # Инструкция
    instruction = (
        f"✅ Бот <b>{name}</b> создан!\n\n"
        f"📁 Файл: <code>{bot_path}</code>\n\n"
        f"🚀 Запуск:\n"
        f"<code>pip install -r {req_path}</code>\n"
        f"<code>python {bot_path}</code>\n\n"
        f"🔑 Токен: вставь в начало файла вместо {token}"
    )
    if chat_id:
        from telegram_client import send_message, send_document
        send_document(bot_path, caption=f"🤖 {name}.py", chat_id=chat_id)
        send_message(instruction, chat_id)
    return instruction


# ── ЗАПУСТИТЬ ПРОЦЕСС ─────────────────────────────────────────────────────────
@register_tool("run_process",
               "Запустить Python-скрипт как фоновый процесс. ARGS: {script, args?[], name?}",
               "bots")
def tool_run_process(args, chat_id=None, on_status=None):
    if isinstance(args, str):
        try: args = json.loads(args)
        except: args = {'script': str(args)}
    script  = args.get('script', '')
    extra   = args.get('args', [])
    name    = args.get('name', os.path.basename(script))

    if not os.path.exists(script):
        # Ищем в BASE
        candidate = os.path.join(BASE, script)
        if os.path.exists(candidate):
            script = candidate
        else:
            return f"❌ Файл не найден: {script}"

    cmd = [sys.executable, script] + [str(a) for a in extra]
    try:
        proc = subprocess.Popen(cmd, cwd=BASE,
                                stdout=open(f'/tmp/{name}.log', 'w'),
                                stderr=subprocess.STDOUT)
        _running_procs[name] = {'proc': proc, 'pid': proc.pid, 'script': script, 'started': time.time()}
        return f"✅ Процесс <b>{name}</b> запущен (PID {proc.pid})\nЛог: /tmp/{name}.log"
    except Exception as e:
        return f"❌ {e}"

_running_procs = {}   # name → {proc, pid, script, started}


# ── СПИСОК ПРОЦЕССОВ ─────────────────────────────────────────────────────────
@register_tool("list_processes", "Список запущенных через агента процессов. ARGS: (пусто)", "bots")
def tool_list_procs(args, chat_id=None, on_status=None):
    if not _running_procs:
        return "ℹ️ Нет запущенных через агента процессов"
    lines = ["🤖 <b>Запущенные процессы:</b>\n"]
    for name, info in _running_procs.items():
        alive = info['proc'].poll() is None
        status = "🟢" if alive else "🔴"
        uptime = int(time.time() - info['started'])
        lines.append(f"{status} <b>{name}</b>  PID:{info['pid']}  ⏱{uptime}с\n   <code>{info['script']}</code>")
    return "\n".join(lines)


# ── ОСТАНОВИТЬ ПРОЦЕСС ────────────────────────────────────────────────────────
@register_tool("stop_process", "Остановить процесс по имени или PID. ARGS: name_or_pid", "bots")
def tool_stop_proc(args, chat_id=None, on_status=None):
    name = str(args).strip()
    # По имени из реестра
    if name in _running_procs:
        _running_procs[name]['proc'].terminate()
        _running_procs.pop(name)
        return f"✅ Процесс {name} остановлен."
    # По PID
    try:
        pid = int(name)
        os.kill(pid, 9)
        return f"✅ PID {pid} убит."
    except Exception as e:
        return f"❌ {e}"


# ── САМОУЛУЧШЕНИЕ: написать новый модуль ─────────────────────────────────────
@register_tool("self_improve",
               "Написать новый модуль и интегрировать в бота. ARGS: {task, module_name?}",
               "meta")
def tool_self_improve(args, chat_id=None, on_status=None):
    if isinstance(args, str):
        try: args = json.loads(args)
        except: args = {'task': str(args)}
    task    = args.get('task', str(args))
    modname = args.get('module_name', f"addon_{int(time.time())}")

    if on_status: on_status(f"🧠 Анализирую задачу: {task[:80]}...")

    from llm_client import call_llm
    # Анализ что нужно
    analysis_prompt = f"""
Задача для расширения бота АВТОМУВИ: {task}

Проанализируй:
1. Что нужно создать (модуль/функцию/класс)
2. Какие зависимости нужны (pip-пакеты)
3. Как интегрировать в существующий bot.py
4. Какие команды/кнопки добавить

Ответ в формате JSON:
{{
  "summary": "краткое описание",
  "dependencies": ["pkg1", "pkg2"],
  "module_code": "полный Python-код модуля",
  "bot_integration": "инструкция по интеграции в bot.py (текст)",
  "commands": ["/cmd1", "/cmd2"],
  "risks": "возможные проблемы"
}}
"""
    if on_status: on_status("📝 Пишу код модуля...")
    raw = call_llm(analysis_prompt, max_tokens=4000)
    import re
    m = re.search(r'\{.*\}', raw, re.DOTALL)
    if m:
        try:
            data = json.loads(m.group(0))
        except:
            data = {'summary': task, 'module_code': raw, 'dependencies': [],
                    'bot_integration': 'Смотри код выше', 'commands': [], 'risks': '—'}
    else:
        data = {'summary': task, 'module_code': raw, 'dependencies': [],
                'bot_integration': 'Ручная интеграция требуется', 'commands': [], 'risks': '—'}

    # Сохраняем модуль
    mod_path = os.path.join(BASE, f"{modname}.py")
    with open(mod_path, 'w', encoding='utf-8') as f:
        f.write(data.get('module_code', '# empty'))

    # Проверяем синтаксис
    import ast
    try:
        ast.parse(data.get('module_code',''))
        syntax_ok = True
    except SyntaxError as e:
        syntax_ok = False
        data['risks'] = (data.get('risks','') + f" | SyntaxError: {e}")

    # Устанавливаем зависимости если нужно
    deps_installed = []
    for dep in data.get('dependencies', []):
        try:
            r = subprocess.run([sys.executable, '-m', 'pip', 'install', dep, '-q'],
                               capture_output=True, timeout=60)
            if r.returncode == 0: deps_installed.append(dep)
        except: pass

    result = (
        f"🧠 <b>Самоулучшение:</b> {data.get('summary','')}\n\n"
        f"📁 Модуль: <code>{mod_path}</code>\n"
        f"{'✅ Синтаксис OK' if syntax_ok else '⚠️ Синтаксические ошибки!'}\n"
        f"📦 Установлено: {', '.join(deps_installed) or 'нет'}\n\n"
        f"🔧 <b>Интеграция:</b>\n{data.get('bot_integration','—')[:500]}\n\n"
        f"⚠️ <b>Риски:</b> {data.get('risks','—')}"
    )
    if chat_id:
        from telegram_client import send_message, send_document
        if os.path.exists(mod_path):
            send_document(mod_path, caption=f"🧩 {modname}.py", chat_id=chat_id)
        send_message(result, chat_id)
    return result


# ── POLLINATIONS ─────────────────────────────────────────────────────────────
@register_tool("pollinations_image",
               "Бесплатная генерация картинки через Pollinations AI (без ключа). ARGS: {prompt, width?, height?, model?, seed?}",
               "media")
def tool_pollinations_image(args, chat_id=None, on_status=None):
    import urllib.request, urllib.parse, urllib.error, tempfile, os, time as _t
    if isinstance(args, str):
        try: args = json.loads(args)
        except: args = {'prompt': str(args)}

    prompt  = str(args.get('prompt', args) if not isinstance(args, str) else args)
    width   = int(args.get('width', 1024))
    height  = int(args.get('height', 1024))
    seed    = int(args.get('seed', int(_t.time()) % 99999))
    model   = args.get('model', '')

    if on_status: on_status(f"🌸 Генерирую: {prompt[:60]}...")

    out_path = os.path.join(BASE, 'agent_projects', f'poll_{int(_t.time())}.jpg')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    encoded = urllib.parse.quote(prompt[:500], safe='')

    # Модели в порядке приоритета — без enhance чтобы не получить 500
    models = [model] if model else ['flux', 'turbo', 'flux-realism', '']
    urls = []
    for m in models:
        base_url = f"https://image.pollinations.ai/prompt/{encoded}"
        params = f"width={width}&height={height}&seed={seed}&nologo=true&safe=false"
        if m:
            params += f"&model={m}"
        urls.append(f"{base_url}?{params}")

    last_err = None
    for attempt, url in enumerate(urls):
        try:
            if on_status and attempt > 0:
                on_status(f"  🔄 Попытка {attempt+1} (модель: {models[attempt] or 'default'})...")
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0',
                'Accept': 'image/webp,image/png,image/*,*/*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://pollinations.ai/',
            })
            with urllib.request.urlopen(req, timeout=120) as resp:
                # Проверяем Content-Type
                ct = resp.headers.get('Content-Type', '')
                data = resp.read()

            if 'text' in ct and len(data) < 2000:
                # Сервер вернул ошибку текстом
                last_err = f"API error: {data.decode('utf-8', errors='ignore')[:200]}"
                _t.sleep(2)
                continue

            if len(data) > 5000:
                with open(out_path, 'wb') as f:
                    f.write(data)
                if on_status: on_status(f"  ✅ Готово ({len(data)//1024} KB)")
                if chat_id:
                    from telegram_client import send_document
                    send_document(out_path, caption=f"🌸 {prompt[:80]}", chat_id=chat_id)
                return f"✅ Изображение: {out_path}"

            last_err = f"Слишком маленький ответ: {len(data)} байт"

        except urllib.error.HTTPError as e:
            last_err = f"HTTP {e.code}: {e.reason}"
            if on_status: on_status(f"  ⚠️ {last_err}, пробую другую модель...")
            _t.sleep(3)
        except Exception as e:
            last_err = str(e)
            _t.sleep(2)

    # Все модели не сработали — Pillow fallback
    if on_status: on_status("⚠️ Pollinations недоступен, рисую через Pillow...")
    return _generate_image_pillow(prompt, out_path, width, height, chat_id)


def _generate_image_pillow(prompt, out_path, width=512, height=512, chat_id=None):
    """Fallback генерация изображения через PIL если API недоступны."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        import hashlib, math

        # Детерминированные цвета на основе промта
        h = hashlib.md5(prompt.encode()).hexdigest()
        r1, g1, b1 = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        r2, g2, b2 = int(h[6:8], 16), int(h[8:10], 16), int(h[10:12], 16)

        img = Image.new('RGB', (width, height))
        draw = ImageDraw.Draw(img)

        # Градиентный фон
        for y in range(height):
            t = y / height
            r = int(r1 + (r2 - r1) * t)
            g = int(g1 + (g2 - g1) * t)
            b = int(b1 + (b2 - b1) * t)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        # Декоративные круги
        for i in range(8):
            hi = hashlib.md5(f"{prompt}{i}".encode()).hexdigest()
            cx = int(hi[0:4], 16) % width
            cy = int(hi[4:8], 16) % height
            rad = 30 + int(hi[8:10], 16) % 100
            cr = int(hi[10:12], 16)
            cg = int(hi[12:14], 16)
            cb = int(hi[14:16], 16)
            draw.ellipse([cx-rad, cy-rad, cx+rad, cy+rad],
                         fill=(cr, cg, cb, 128) if hasattr(draw, 'alpha_composite') else (cr, cg, cb))

        # Текст промта
        text = prompt[:40] + ('...' if len(prompt) > 40 else '')
        try:
            font = ImageFont.truetype("arial.ttf", 18)
        except:
            font = ImageFont.load_default()

        # Тень + текст
        tw, th = draw.textbbox((0,0), text, font=font)[2:]
        tx = (width - tw) // 2
        ty = height - 60
        draw.text((tx+2, ty+2), text, fill=(0,0,0,180), font=font)
        draw.text((tx, ty), text, fill=(255,255,255,230), font=font)

        # Watermark
        draw.text((10, 10), "🎨 AI Generated", fill=(255,255,255,150), font=font)

        img.save(out_path, 'JPEG', quality=90)

        if chat_id:
            from telegram_client import send_document
            send_document(out_path, caption=f"🎨 {prompt[:80]}\n<i>(PIL fallback)</i>", chat_id=chat_id)
        return f"✅ Изображение создано через Pillow: {out_path}"
    except ImportError:
        return "❌ PIL не установлен. pip install Pillow"
    except Exception as e:
        return f"❌ PIL fallback error: {e}"


@register_tool("pollinations_text",
               "Бесплатный текстовый ИИ через Pollinations (без ключа). ARGS: {prompt, model?, system?}",
               "llm")
def tool_pollinations_text(args, chat_id=None, on_status=None):
    import urllib.request, urllib.parse, json as _json
    if isinstance(args, str):
        try: args = _json.loads(args)
        except: args = {'prompt': str(args)}

    prompt  = args.get('prompt', str(args))
    model   = args.get('model', 'openai')   # openai | mistral | llama | claude
    system  = args.get('system', 'You are a helpful assistant. Reply in Russian.')

    if on_status: on_status(f"💬 Pollinations text ({model})...")

    payload = _json.dumps({
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": prompt}
        ],
        "model":  model,
        "seed":   42,
        "stream": False
    }).encode()

    req = urllib.request.Request(
        "https://text.pollinations.ai/openai",
        data=payload,
        headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'},
        method='POST'
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = _json.loads(resp.read())
        return data['choices'][0]['message']['content']
    except Exception as e:
        return f"❌ Pollinations text error: {e}"


# ── WEB ПОИСК ─────────────────────────────────────────────────────────────────
@register_tool("web_search",
               "Найти информацию в интернете. ARGS: поисковый запрос",
               "search")
def tool_web_search(args, chat_id=None, on_status=None):
    # Извлекаем строку запроса из любого формата
    if isinstance(args, dict):
        query = str(args.get('query') or args.get('q') or args.get('поисковый запрос') or
                    args.get('search') or args.get('text') or
                    next(iter(args.values()), '')).strip()
    elif isinstance(args, str):
        try:
            import json as _j
            d = _j.loads(args)
            if isinstance(d, dict):
                query = str(d.get('query') or d.get('q') or d.get('поисковый запрос') or
                            next(iter(d.values()), '')).strip()
            else:
                query = args.strip()
        except Exception:
            query = args.strip()
    else:
        query = str(args).strip()

    if not query:
        return "❌ Пустой запрос"

    if on_status: on_status(f"🌐 Ищу: {query[:60]}...")
    try:
        import urllib.request, urllib.parse, json as _json
        encoded = urllib.parse.quote(query)
        url = f"https://ddg-webapp.vercel.app/search?q={encoded}&max_results=5"
        req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = _json.loads(resp.read())
        results = data if isinstance(data, list) else data.get('results', [])
        lines = [f"🔍 <b>Результаты: {query}</b>\n"]
        for r in results[:5]:
            title = r.get('title','')[:60]
            body  = r.get('body','')[:150]
            href  = r.get('href','')
            lines.append(f"<b>{title}</b>\n{body}\n<a href='{href}'>{href[:50]}</a>\n")
        return "\n".join(lines)
    except Exception as e:
        try:
            from llm_client import call_llm
            return call_llm(f"Найди информацию по запросу: {query}. Отвечай кратко и по делу.")
        except Exception:
            return f"❌ Поиск недоступен: {e}"


# ── СКАЧАТЬ СТРАНИЦУ ──────────────────────────────────────────────────────────
@register_tool("fetch_url",
               "Скачать содержимое URL. ARGS: url",
               "search")
def tool_fetch_url(args, chat_id=None, on_status=None):
    import urllib.request, urllib.parse, re as _re
    # Извлекаем URL из разных форматов
    if isinstance(args, dict):
        url = str(args.get('url') or args.get('link') or args.get('href') or
                  next(iter(args.values()), '')).strip()
    elif isinstance(args, str):
        try:
            import json as _j
            d = _j.loads(args)
            url = str(d.get('url') or d.get('link') or next(iter(d.values()), '')).strip()
        except Exception:
            url = args.strip()
    else:
        url = str(args).strip()

    if not url or not url.startswith(('http://', 'https://')):
        return f"❌ Нужен валидный URL (получено: {repr(url)[:60]})"

    # Кодируем не-ASCII символы в URL (кириллица, иероглифы и т.д.)
    try:
        parts = urllib.parse.urlparse(url)
        safe_path  = urllib.parse.quote(parts.path,  safe='/:@!$&\'()*+,;=')
        safe_query = urllib.parse.quote(parts.query, safe='=&+%')
        url = urllib.parse.urlunparse(parts._replace(path=safe_path, query=safe_query))
    except Exception:
        pass

    try:
        req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read(50000).decode('utf-8', errors='replace')
        clean = _re.sub(r'<[^>]+>', ' ', raw)
        clean = _re.sub(r'\s+', ' ', clean).strip()
        return f"✅ {url}\n\n{clean[:3000]}"
    except Exception as e:
        return f"❌ {e}"


# ── ФАЙЛОВЫЕ ОПЕРАЦИИ ─────────────────────────────────────────────────────────
@register_tool("create_file",
               "Создать файл с содержимым. ARGS: {path, content, type?}",
               "files")
def tool_create_file(args, chat_id=None, on_status=None):
    if isinstance(args, str):
        try: args = json.loads(args)
        except: return "❌ Нужен JSON: {path: '...', content: '...'}"
    path    = args.get('path', os.path.join(BASE, 'agent_projects', f'file_{int(time.time())}.txt'))
    content = args.get('content', '')
    if not os.path.isabs(path):
        path = os.path.join(BASE, path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    if chat_id:
        from telegram_client import send_document
        send_document(path, caption=f"📄 {os.path.basename(path)}", chat_id=chat_id)
    return f"✅ Файл создан: {path} ({len(content)} символов)"


# ── УСТАНОВИТЬ ПАКЕТ ──────────────────────────────────────────────────────────
@register_tool("install_package",
               "Установить Python-пакет. ARGS: имя_пакета или список через запятую",
               "system")
def tool_install_pkg(args, chat_id=None, on_status=None):
    pkgs = [p.strip() for p in str(args).split(',') if p.strip()]
    results = []
    for pkg in pkgs:
        if on_status: on_status(f"📦 Устанавливаю {pkg}...")
        flags = ['--break-system-packages'] if os.path.isdir('/data/data/com.termux') else []
        r = subprocess.run([sys.executable, '-m', 'pip', 'install', pkg, '-q'] + flags,
                           capture_output=True, text=True, timeout=120)
        if r.returncode == 0:
            results.append(f"✅ {pkg}")
        else:
            results.append(f"❌ {pkg}: {(r.stderr or r.stdout)[-200:]}")
    return "\n".join(results)


# ── ИНСТРУКЦИЯ (что делать если нет инструмента) ─────────────────────────────
@register_tool("analyze_task",
               "Проанализировать задачу и составить план. ARGS: описание задачи",
               "meta")
def tool_analyze_task(args, chat_id=None, on_status=None):
    task = str(args)
    from llm_client import call_llm
    tools_desc = get_tools_list()
    prompt = f"""
Ты — автономный ИИ-агент с набором инструментов.

{tools_desc}

ЗАДАЧА: {task}

Составь подробный план выполнения:
1. Какие инструменты нужны
2. Порядок шагов
3. Что делать если инструмента нет (какой код написать)
4. Конкретные TOOL:/ARGS: вызовы

Если задача требует написания кода — напиши его и запусти через TOOL: sandbox.
"""
    return call_llm(prompt, max_tokens=2000)


# ─── Агент-оркестратор (полный цикл) ─────────────────────────────────────────
def run_agent_with_tools(chat_id, user_request, on_status=None, max_rounds=5):
    """
    Запускает агента с доступом ко всем инструментам.
    Цикл: LLM → парсит вызовы инструментов → выполняет → передаёт результат обратно LLM.
    """
    from llm_client import call_llm

    system_prompt = f"""Ты — автономный ИИ-агент АВТОМУВИ.
У тебя есть набор инструментов. Чтобы вызвать инструмент, используй формат:
TOOL: <имя_инструмента>
ARGS: <аргументы или JSON>

{get_tools_list()}

Правила:
- Анализируй задачу и выбирай нужные инструменты
- Если нужного инструмента нет — используй sandbox для написания кода
- Сначала используй analyze_task если задача сложная
- После каждого инструмента анализируй результат
- Когда всё готово — дай итоговый ответ без TOOL:
"""
    messages = [{"role": "user", "content": user_request}]
    accumulated_results = []

    for round_n in range(max_rounds):
        if on_status: on_status(f"🤖 Агент думает (раунд {round_n+1}/{max_rounds})...")

        full_context = system_prompt + "\n\n"
        if accumulated_results:
            full_context += "Результаты предыдущих инструментов:\n"
            for r in accumulated_results[-3:]:
                full_context += f"[{r['tool']}]: {r['result'][:500]}\n\n"
        full_context += f"Запрос: {user_request}"

        response = call_llm(full_context, max_tokens=2000)
        calls = parse_tool_calls(response)

        if not calls:
            # Нет вызовов инструментов — финальный ответ
            return response, accumulated_results

        for tool_name, tool_args in calls:
            if on_status: on_status(f"🔧 Выполняю: {tool_name}...")
            ok, result = execute_tool(tool_name, tool_args, chat_id=chat_id, on_status=on_status)
            accumulated_results.append({'tool': tool_name, 'args': tool_args[:100], 'result': result, 'ok': ok})

        # Если все инструменты выполнены успешно — просим финальный ответ
        if all(r['ok'] for r in accumulated_results[-len(calls):]):
            if len(accumulated_results) >= len(calls):
                # Ещё один раунд для финального ответа
                continue



# ── MOVIEPY — продвинутый видеомонтаж ────────────────────────────────────────
@register_tool(
    "moviepy_edit",
    "Видеомонтаж через MoviePy: нарезка, склейка, субтитры, эффекты, TTS+видео. "
    "ARGS: {action, ...params}. "
    "action='concat': склеить видео {clips:[...paths]}. "
    "action='cut': нарезать {input, start, end, output?}. "
    "action='add_audio': наложить аудио {video, audio, output?}. "
    "action='slideshow': слайд-шоу из картинок {images:[...], duration?, audio?, output?}. "
    "action='text_video': видео с текстом и TTS {text, voice?, output?}. "
    "action='speed': изменить скорость {input, factor, output?}. "
    "action='info': инфо о видео {input}.",
    "media"
)
def tool_moviepy_edit(args, chat_id=None, on_status=None):
    if isinstance(args, str):
        try: args = json.loads(args)
        except: args = {'action': args}

    action = args.get('action', 'info')
    out_dir = os.path.join(BASE, 'agent_projects')
    os.makedirs(out_dir, exist_ok=True)

    # Проверяем moviepy
    try:
        from moviepy.editor import (
            VideoFileClip, AudioFileClip, ImageClip, TextClip,
            concatenate_videoclips, CompositeVideoClip, CompositeAudioClip,
            ColorClip
        )
        from moviepy.audio.AudioClip import AudioArrayClip
    except ImportError:
        return ("❌ MoviePy не установлен.\n"
                "Установи: pip install moviepy\n"
                "Для текста также нужен: apt install imagemagick / pip install pillow")

    def _out(suffix='.mp4'):
        return args.get('output') or os.path.join(out_dir, f'mp_{action}_{int(time.time())}{suffix}')

    try:
        # ── info ──────────────────────────────────────────────────────────
        if action == 'info':
            path = args.get('input', '')
            if not os.path.exists(path):
                return f"❌ Файл не найден: {path}"
            clip = VideoFileClip(path)
            info = (
                f"📹 {os.path.basename(path)}\n"
                f"Длительность: {clip.duration:.1f}с\n"
                f"Разрешение: {clip.size[0]}x{clip.size[1]}\n"
                f"FPS: {clip.fps}\n"
                f"Аудио: {'есть' if clip.audio else 'нет'}\n"
                f"Размер: {os.path.getsize(path)//1024}KB"
            )
            clip.close()
            return info

        # ── cut ───────────────────────────────────────────────────────────
        elif action == 'cut':
            path   = args.get('input', '')
            start  = float(args.get('start', 0))
            end    = float(args.get('end', 0))
            if not os.path.exists(path): return f"❌ Файл не найден: {path}"
            if on_status: on_status(f"✂️ Нарезаю {start}с — {end}с...")
            out = _out()
            clip = VideoFileClip(path).subclip(start, end or None)
            clip.write_videofile(out, logger=None, codec='libx264', audio_codec='aac')
            clip.close()
            if chat_id:
                from telegram_client import send_document
                send_document(out, caption=f"✂️ Нарезка {start}с-{end}с", chat_id=chat_id)
            return f"✅ Нарезано: {out}"

        # ── concat ────────────────────────────────────────────────────────
        elif action == 'concat':
            clips_paths = args.get('clips', [])
            if not clips_paths: return "❌ Нужен список clips: [path1, path2, ...]"
            missing = [p for p in clips_paths if not os.path.exists(p)]
            if missing: return f"❌ Не найдены файлы: {missing}"
            if on_status: on_status(f"🔗 Склеиваю {len(clips_paths)} клипов...")
            out = _out()
            clips = [VideoFileClip(p) for p in clips_paths]
            final = concatenate_videoclips(clips, method='compose')
            final.write_videofile(out, logger=None, codec='libx264', audio_codec='aac')
            for c in clips: c.close()
            final.close()
            if chat_id:
                from telegram_client import send_document
                send_document(out, caption=f"🔗 Склеено {len(clips_paths)} клипов", chat_id=chat_id)
            return f"✅ Склеено: {out}"

        # ── add_audio ─────────────────────────────────────────────────────
        elif action == 'add_audio':
            video_path = args.get('video', '')
            audio_path = args.get('audio', '')
            if not os.path.exists(video_path): return f"❌ Видео не найдено: {video_path}"
            if not os.path.exists(audio_path): return f"❌ Аудио не найдено: {audio_path}"
            if on_status: on_status("🎵 Накладываю аудио...")
            out = _out()
            video = VideoFileClip(video_path)
            audio = AudioFileClip(audio_path)
            # Обрезаем аудио если длиннее видео
            if audio.duration > video.duration:
                audio = audio.subclip(0, video.duration)
            video = video.set_audio(audio)
            video.write_videofile(out, logger=None, codec='libx264', audio_codec='aac')
            video.close(); audio.close()
            if chat_id:
                from telegram_client import send_document
                send_document(out, caption="🎵 Видео с аудио", chat_id=chat_id)
            return f"✅ Аудио наложено: {out}"

        # ── slideshow ─────────────────────────────────────────────────────
        elif action == 'slideshow':
            images   = args.get('images', [])
            duration = float(args.get('duration', 3))   # сек на слайд
            audio_p  = args.get('audio', '')
            if not images: return "❌ Нужен список images: [path1, path2, ...]"
            missing = [p for p in images if not os.path.exists(p)]
            if missing: return f"❌ Не найдены: {missing}"
            if on_status: on_status(f"🖼 Слайд-шоу из {len(images)} картинок...")
            out = _out()
            clips = []
            for img_path in images:
                clip = ImageClip(img_path, duration=duration).resize((1280, 720))
                clips.append(clip)
            video = concatenate_videoclips(clips, method='compose')
            if audio_p and os.path.exists(audio_p):
                audio = AudioFileClip(audio_p)
                if audio.duration > video.duration:
                    audio = audio.subclip(0, video.duration)
                video = video.set_audio(audio)
            video.write_videofile(out, fps=25, logger=None, codec='libx264', audio_codec='aac')
            for c in clips: c.close()
            video.close()
            if chat_id:
                from telegram_client import send_document
                send_document(out, caption=f"🖼 Слайд-шоу ({len(images)} слайдов)", chat_id=chat_id)
            return f"✅ Слайд-шоу: {out}"

        # ── text_video — озвучка + субтитры ──────────────────────────────
        elif action == 'text_video':
            text  = args.get('text', '')
            voice = args.get('voice', 'ru-RU-DmitryNeural')
            if not text: return "❌ Нужен text"
            if on_status: on_status("🎤 Генерирую TTS...")

            # TTS
            audio_path = os.path.join(out_dir, f'tts_{int(time.time())}.mp3')
            try:
                import asyncio, edge_tts
                async def _tts():
                    comm = edge_tts.Communicate(text, voice)
                    await comm.save(audio_path)
                asyncio.run(_tts())
            except Exception as e:
                return f"❌ TTS ошибка: {e}"

            if on_status: on_status("🎬 Собираю видео...")

            audio_clip = AudioFileClip(audio_path)
            duration   = audio_clip.duration

            # Фон — тёмный градиент через Pillow
            try:
                from PIL import Image, ImageDraw, ImageFont
                img = Image.new('RGB', (1280, 720), (15, 15, 25))
                draw = ImageDraw.Draw(img)
                # Разбиваем текст на строки
                words = text.split()
                lines, line = [], []
                for w in words:
                    line.append(w)
                    if len(' '.join(line)) > 45:
                        lines.append(' '.join(line[:-1]))
                        line = [w]
                if line: lines.append(' '.join(line))
                # Рисуем текст
                y = 720//2 - len(lines)*30
                for l in lines:
                    draw.text((100, y), l, fill=(220, 220, 255))
                    y += 55
                bg_path = os.path.join(out_dir, f'bg_{int(time.time())}.png')
                img.save(bg_path)
                bg_clip = ImageClip(bg_path, duration=duration)
            except ImportError:
                bg_clip = ColorClip((1280, 720), color=[15, 15, 25], duration=duration)

            final = bg_clip.set_audio(audio_clip)
            out = _out()
            final.write_videofile(out, fps=25, logger=None, codec='libx264', audio_codec='aac')
            audio_clip.close(); final.close()

            if chat_id:
                from telegram_client import send_document
                send_document(out, caption=f"🎬 {text[:60]}...", chat_id=chat_id)
            return f"✅ Видео с озвучкой: {out}"

        # ── speed ─────────────────────────────────────────────────────────
        elif action == 'speed':
            path   = args.get('input', '')
            factor = float(args.get('factor', 1.5))
            if not os.path.exists(path): return f"❌ Файл не найден: {path}"
            if on_status: on_status(f"⚡ Скорость x{factor}...")
            out = _out()
            clip = VideoFileClip(path)
            fast = clip.fx(__import__('moviepy.video.fx.all', fromlist=['speedx']).speedx, factor)
            fast.write_videofile(out, logger=None, codec='libx264', audio_codec='aac')
            clip.close(); fast.close()
            if chat_id:
                from telegram_client import send_document
                send_document(out, caption=f"⚡ Скорость x{factor}", chat_id=chat_id)
            return f"✅ Скорость изменена: {out}"

        else:
            return (f"❌ Неизвестный action: {action}\n"
                    f"Доступные: info, cut, concat, add_audio, slideshow, text_video, speed")

    except Exception as e:
        import traceback
        return f"❌ MoviePy ошибка: {e}\n{traceback.format_exc()[-500:]}"



# ── DIFFUSERS + A1111 WebUI ───────────────────────────────────────────────────
@register_tool(
    "diffuse_image",
    "Генерация изображений через Stable Diffusion (local diffusers или A1111 WebUI API). "
    "ARGS: {prompt, negative_prompt?, mode?, width?, height?, steps?, cfg?, seed?, model?, output?}. "
    "mode='auto'(дефолт) — пробует local→webui→pollinations. "
    "mode='local' — local diffusers (нужен GPU + ~4GB VRAM). "
    "mode='webui' — A1111 API (нужен запущенный --api на WEBUI_URL). "
    "mode='pollinations' — бесплатно без GPU.",
    "media"
)
def tool_diffuse_image(args, chat_id=None, on_status=None):
    if isinstance(args, str):
        try: args = json.loads(args)
        except: args = {'prompt': str(args)}

    prompt   = args.get('prompt', '')
    neg      = args.get('negative_prompt', 'blurry, low quality, deformed, ugly, watermark')
    mode     = args.get('mode', 'auto')
    width    = int(args.get('width',  512))
    height   = int(args.get('height', 512))
    steps    = int(args.get('steps',  20))
    cfg      = float(args.get('cfg', 7.0))
    seed     = int(args.get('seed', -1))
    model    = args.get('model', '')
    out_dir  = os.path.join(BASE, 'agent_projects')
    os.makedirs(out_dir, exist_ok=True)
    out_path = args.get('output') or os.path.join(out_dir, f'sd_{int(time.time())}.png')

    if not prompt:
        return "❌ Нужен prompt"

    errors = []

    # ── 1. Local diffusers ────────────────────────────────────────────────────
    if mode in ('auto', 'local'):
        if on_status: on_status("🖥 Пробую local diffusers...")
        try:
            import torch
            from diffusers import (
                StableDiffusionPipeline,
                StableDiffusionXLPipeline,
                DiffusionPipeline,
                AutoPipelineForText2Image,
            )

            model_id = model or os.environ.get('SD_MODEL', 'runwayml/stable-diffusion-v1-5')
            device   = 'cuda' if torch.cuda.is_available() else 'cpu'
            dtype    = torch.float16 if device == 'cuda' else torch.float32

            if on_status: on_status(f"🔄 Загружаю модель {model_id} на {device}...")

            pipe = AutoPipelineForText2Image.from_pretrained(
                model_id,
                torch_dtype=dtype,
                safety_checker=None,
                requires_safety_checker=False,
            )
            pipe = pipe.to(device)

            # Оптимизации памяти
            if device == 'cuda':
                pipe.enable_attention_slicing()
                try: pipe.enable_xformers_memory_efficient_attention()
                except Exception: pass

            if on_status: on_status(f"🎨 Генерирую ({steps} шагов, {width}x{height})...")

            gen_kwargs = dict(
                prompt=prompt,
                negative_prompt=neg,
                width=width,
                height=height,
                num_inference_steps=steps,
                guidance_scale=cfg,
            )
            if seed >= 0:
                gen_kwargs['generator'] = torch.Generator(device=device).manual_seed(seed)

            result = pipe(**gen_kwargs)
            image  = result.images[0]
            image.save(out_path)
            pipe = None  # освобождаем VRAM

            if chat_id:
                from telegram_client import send_document
                send_document(out_path, caption=f"🖥 SD local: {prompt[:80]}", chat_id=chat_id)
            return f"✅ Local diffusers: {out_path}\nМодель: {model_id} | Device: {device}"

        except ImportError as e:
            errors.append(f"local: diffusers не установлен ({e})")
        except RuntimeError as e:
            if 'CUDA out of memory' in str(e):
                errors.append(f"local: недостаточно VRAM — попробуй меньший размер или другую модель")
            else:
                errors.append(f"local: {e}")
        except Exception as e:
            errors.append(f"local: {e}")
        if mode == 'local':
            return "❌ " + "\n".join(errors)

    # ── 2. A1111 / ComfyUI WebUI API ─────────────────────────────────────────
    if mode in ('auto', 'webui'):
        webui_url = os.environ.get('WEBUI_URL', 'http://localhost:7860')
        if on_status: on_status(f"🌐 Пробую WebUI API: {webui_url}...")
        try:
            import requests as req, base64, io
            from PIL import Image as PILImage

            # A1111 txt2img endpoint
            payload = {
                "prompt":          prompt,
                "negative_prompt": neg,
                "width":           width,
                "height":          height,
                "steps":           steps,
                "cfg_scale":       cfg,
                "seed":            seed,
                "sampler_name":    "DPM++ 2M Karras",
                "save_images":     False,
            }
            if model:
                # Переключаем модель если указана
                try:
                    req.post(f"{webui_url}/sdapi/v1/options",
                             json={"sd_model_checkpoint": model}, timeout=10)
                except Exception: pass

            r = req.post(f"{webui_url}/sdapi/v1/txt2img",
                         json=payload, timeout=120)
            r.raise_for_status()
            data = r.json()

            img_b64 = data['images'][0]
            img = PILImage.open(io.BytesIO(base64.b64decode(img_b64)))
            img.save(out_path)

            info = json.loads(data.get('info', '{}'))
            seed_used = info.get('seed', seed)

            if chat_id:
                from telegram_client import send_document
                send_document(out_path, caption=f"🌐 A1111: {prompt[:80]}", chat_id=chat_id)
            return f"✅ A1111 WebUI: {out_path}\nSeed: {seed_used} | Steps: {steps} | CFG: {cfg}"

        except Exception as e:
            errors.append(f"webui ({webui_url}): {e}")
        if mode == 'webui':
            hint = "\n💡 Запусти A1111 с флагом --api: python launch.py --api"
            return "❌ " + "\n".join(errors) + hint

    # ── 3. Pollinations fallback ──────────────────────────────────────────────
    if mode in ('auto', 'pollinations'):
        if on_status: on_status("🌸 Fallback → Pollinations...")
        result = tool_pollinations_image(
            {'prompt': prompt, 'width': width, 'height': height},
            chat_id=chat_id, on_status=on_status
        )
        if '✅' in result:
            if errors:
                result += f"\n⚠️ Fallback (local/webui недоступны):\n" + "\n".join(f"  • {e}" for e in errors)
            return result
        errors.append(f"pollinations: {result}")

    return "❌ Все методы генерации недоступны:\n" + "\n".join(f"  • {e}" for e in errors)


# ── STABLE DIFFUSION (diffusers) ─────────────────────────────────────────────
@register_tool(
    "stable_diffusion",
    "Генерация изображений через Stable Diffusion локально (diffusers). "
    "ARGS: {prompt, negative_prompt?, model?, steps?, guidance?, width?, height?, seed?, output?}. "
    "model: 'sd15' (быстрый), 'sdxl' (качественный), 'lcm' (очень быстрый). "
    "Требует GPU или мощный CPU + ~4GB RAM.",
    "media"
)
def tool_stable_diffusion(args, chat_id=None, on_status=None):
    if isinstance(args, str):
        try: args = json.loads(args)
        except: args = {'prompt': str(args)}

    prompt   = args.get('prompt', '')
    neg      = args.get('negative_prompt', 'blurry, bad quality, distorted, watermark')
    model_id = args.get('model', 'sd15')
    steps    = int(args.get('steps', 20))
    guidance = float(args.get('guidance', 7.5))
    width    = int(args.get('width', 512))
    height   = int(args.get('height', 512))
    seed     = args.get('seed', None)
    out_path = args.get('output', os.path.join(BASE, 'agent_projects', f'sd_{int(time.time())}.png'))
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    MODEL_IDS = {
        'sd15':  'runwayml/stable-diffusion-v1-5',
        'sdxl':  'stabilityai/stable-diffusion-xl-base-1.0',
        'lcm':   'SimianLuo/LCM_Dreamshaper_v7',
        'sd21':  'stabilityai/stable-diffusion-2-1',
    }
    model_name = MODEL_IDS.get(model_id, model_id)

    if on_status: on_status(f"🎨 SD: загружаю {model_id}...")

    try:
        import torch
        from diffusers import StableDiffusionPipeline, DiffusionPipeline, AutoPipelineForText2Image
    except ImportError:
        return ("❌ diffusers не установлен.\n"
                "Установи: pip install diffusers transformers accelerate torch\n"
                "Для CPU: pip install diffusers transformers accelerate torch --index-url https://download.pytorch.org/whl/cpu")

    try:
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        dtype  = torch.float16 if device == 'cuda' else torch.float32

        if on_status: on_status(f"⚙️ Устройство: {device.upper()}, dtype: {dtype}")

        pipe = AutoPipelineForText2Image.from_pretrained(
            model_name,
            torch_dtype=dtype,
            safety_checker=None,       # убираем цензуру
            requires_safety_checker=False,
            low_cpu_mem_usage=True,
        )
        pipe = pipe.to(device)

        if device == 'cpu':
            pipe.enable_attention_slicing()  # экономим память

        generator = torch.Generator(device=device)
        if seed is not None:
            generator.manual_seed(int(seed))

        if on_status: on_status(f"✨ Генерирую: {prompt[:50]}... ({steps} шагов)")

        result = pipe(
            prompt=prompt,
            negative_prompt=neg,
            num_inference_steps=steps,
            guidance_scale=guidance,
            width=width,
            height=height,
            generator=generator,
        )
        img = result.images[0]
        img.save(out_path)
        pipe = None  # освобождаем память

        if chat_id:
            from telegram_client import send_document
            send_document(out_path, caption=f"🎨 SD: {prompt[:80]}", chat_id=chat_id)

        return f"✅ Изображение: {out_path} ({width}x{height}, {steps} шагов, seed={seed})"

    except Exception as e:
        return f"❌ SD ошибка: {e}"


# ── AUTOMATIC1111 / ComfyUI WebUI API ────────────────────────────────────────
@register_tool(
    "webui_generate",
    "Генерация через Automatic1111 / ComfyUI WebUI API. "
    "ARGS: {prompt, negative_prompt?, steps?, cfg?, width?, height?, sampler?, seed?, webui_url?}. "
    "webui_url по умолчанию: http://localhost:7860. "
    "Требует запущенный Automatic1111 с --api флагом.",
    "media"
)
def tool_webui_generate(args, chat_id=None, on_status=None):
    if isinstance(args, str):
        try: args = json.loads(args)
        except: args = {'prompt': str(args)}

    prompt   = args.get('prompt', '')
    neg      = args.get('negative_prompt', 'blurry, bad quality, watermark')
    steps    = int(args.get('steps', 20))
    cfg      = float(args.get('cfg', 7.0))
    width    = int(args.get('width', 512))
    height   = int(args.get('height', 512))
    sampler  = args.get('sampler', 'Euler a')
    seed     = int(args.get('seed', -1))
    webui_url = args.get('webui_url', os.environ.get('WEBUI_URL', 'http://localhost:7860'))

    if on_status: on_status(f"🖼 WebUI: {webui_url}")

    import urllib.request, base64

    payload = json.dumps({
        "prompt": prompt,
        "negative_prompt": neg,
        "steps": steps,
        "cfg_scale": cfg,
        "width": width,
        "height": height,
        "sampler_name": sampler,
        "seed": seed,
        "save_images": False,
    }).encode()

    try:
        req = urllib.request.Request(
            f"{webui_url.rstrip('/')}/sdapi/v1/txt2img",
            data=payload,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=300) as resp:
            data = json.loads(resp.read())

        img_b64 = data['images'][0]
        img_bytes = base64.b64decode(img_b64)

        out_path = os.path.join(BASE, 'agent_projects', f'webui_{int(time.time())}.png')
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, 'wb') as f:
            f.write(img_bytes)

        # Инфо о генерации из параметров ответа
        info = json.loads(data.get('info', '{}'))
        actual_seed = info.get('seed', seed)

        if chat_id:
            from telegram_client import send_document
            send_document(out_path, caption=f"🖼 WebUI: {prompt[:80]}\nSeed: {actual_seed}", chat_id=chat_id)

        return f"✅ WebUI изображение: {out_path} (seed={actual_seed})"

    except urllib.error.URLError as e:
        return (f"❌ WebUI недоступен: {webui_url}\n"
                f"Ошибка: {e}\n\n"
                f"Запусти Automatic1111 с флагом: --api\n"
                f"Или укажи webui_url в ARGS")
    except Exception as e:
        return f"❌ WebUI ошибка: {e}"


@register_tool(
    "webui_models",
    "Список моделей в Automatic1111 WebUI. ARGS: {webui_url?}",
    "media"
)
def tool_webui_models(args, chat_id=None, on_status=None):
    if isinstance(args, str):
        try: args = json.loads(args)
        except: args = {}
    webui_url = args.get('webui_url', os.environ.get('WEBUI_URL', 'http://localhost:7860'))
    import urllib.request
    try:
        with urllib.request.urlopen(f"{webui_url}/sdapi/v1/sd-models", timeout=10) as r:
            models = json.loads(r.read())
        names = [m.get('model_name','?') for m in models[:20]]
        return f"📋 Модели WebUI ({len(models)} шт.):\n" + "\n".join(f"  • {n}" for n in names)
    except Exception as e:
        return f"❌ WebUI недоступен: {e}"


# ── VISION — понимание изображений ───────────────────────────────────────────
@register_tool(
    "analyze_image",
    "Анализ/описание изображения через Vision LLM (GPT-4o, Claude, Gemini). "
    "ARGS: {image, question?, mode?, provider?}. "
    "image: путь к файлу или URL. "
    "question: вопрос про изображение (по умолчанию: опиши подробно). "
    "mode: 'describe' | 'ocr' | 'detect' | 'qa' | 'compare'. "
    "provider: 'openai' | 'anthropic' | 'gemini' | 'auto'.",
    "media"
)
def tool_analyze_image(args, chat_id=None, on_status=None):
    if isinstance(args, str):
        try: args = json.loads(args)
        except: args = {'image': str(args)}

    image_src = args.get('image', '')
    question  = args.get('question', '')
    mode      = args.get('mode', 'describe')
    provider  = args.get('provider', 'auto')

    # Строим вопрос по режиму
    mode_prompts = {
        'describe': 'Опиши изображение подробно: что на нём изображено, цвета, детали, настроение.',
        'ocr':      'Извлеки весь текст с изображения. Верни только текст, без комментариев.',
        'detect':   'Перечисли все объекты на изображении с их примерными координатами/позицией.',
        'qa':       question or 'Что изображено?',
        'compare':  'Сравни элементы на изображении, найди различия и сходства.',
    }
    prompt = question or mode_prompts.get(mode, mode_prompts['describe'])

    if on_status: on_status(f"👁 Анализирую изображение ({mode})...")

    # Загружаем изображение
    import base64, urllib.request
    img_b64 = None
    mime_type = 'image/jpeg'

    try:
        if image_src.startswith('http'):
            # URL
            req = urllib.request.Request(image_src, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=30) as r:
                img_data = r.read()
                ct = r.headers.get('Content-Type', 'image/jpeg')
                mime_type = ct.split(';')[0].strip()
        elif os.path.exists(image_src):
            # Локальный файл
            with open(image_src, 'rb') as f:
                img_data = f.read()
            ext = os.path.splitext(image_src)[1].lower()
            mime_type = {'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
                         'png': 'image/png', 'gif': 'image/gif',
                         'webp': 'image/webp'}.get(ext[1:], 'image/jpeg')
        else:
            return f"❌ Изображение не найдено: {image_src}"

        img_b64 = base64.standard_b64encode(img_data).decode()
    except Exception as e:
        return f"❌ Ошибка загрузки изображения: {e}"

    # Определяем провайдера
    if provider == 'auto':
        if os.environ.get('OPENAI_API_KEY'):    provider = 'openai'
        elif os.environ.get('ANTHROPIC_API_KEY'): provider = 'anthropic'
        elif os.environ.get('GEMINI_API_KEY'):  provider = 'gemini'
        elif os.environ.get('OPENROUTER_API_KEY'): provider = 'openrouter'
        else:
            return "❌ Нет Vision-совместимого ключа API (OpenAI/Anthropic/Gemini/OpenRouter)"

    result = None

    # ── OpenAI / OpenRouter (GPT-4o, gpt-4-vision) ────────────────────────────
    if provider in ('openai', 'openrouter'):
        import urllib.request
        api_key  = os.environ.get('OPENAI_API_KEY') or os.environ.get('OPENROUTER_API_KEY')
        base_url = ('https://openrouter.ai/api/v1' if provider == 'openrouter'
                    else 'https://api.openai.com/v1')
        model    = ('openai/gpt-4o' if provider == 'openrouter' else 'gpt-4o')

        payload = json.dumps({
            "model": model,
            "max_tokens": 1500,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {
                        "url": f"data:{mime_type};base64,{img_b64}",
                        "detail": "high"
                    }},
                    {"type": "text", "text": prompt}
                ]
            }]
        }).encode()

        try:
            req = urllib.request.Request(
                f"{base_url}/chat/completions",
                data=payload,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {api_key}',
                },
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read())
            result = data['choices'][0]['message']['content']
        except Exception as e:
            result = None
            if on_status: on_status(f"⚠️ {provider} ошибка: {e}, пробую другой...")

    # ── Anthropic (Claude claude-opus-4-5) ─────────────────────────────────────────────
    if result is None and (provider == 'anthropic' or (provider == 'auto' and os.environ.get('ANTHROPIC_API_KEY'))):
        import urllib.request
        api_key = os.environ.get('ANTHROPIC_API_KEY')
        if api_key:
            payload = json.dumps({
                "model": "claude-opus-4-5",
                "max_tokens": 1500,
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {
                            "type": "base64",
                            "media_type": mime_type,
                            "data": img_b64
                        }},
                        {"type": "text", "text": prompt}
                    ]
                }]
            }).encode()
            try:
                req = urllib.request.Request(
                    'https://api.anthropic.com/v1/messages',
                    data=payload,
                    headers={
                        'Content-Type': 'application/json',
                        'x-api-key': api_key,
                        'anthropic-version': '2023-06-01',
                    },
                    method='POST'
                )
                with urllib.request.urlopen(req, timeout=60) as r:
                    data = json.loads(r.read())
                result = data['content'][0]['text']
            except Exception as e:
                if on_status: on_status(f"⚠️ Anthropic ошибка: {e}")

    # ── Gemini Vision ─────────────────────────────────────────────────────────
    if result is None and (provider == 'gemini' or os.environ.get('GEMINI_API_KEY')):
        import urllib.request
        api_key = os.environ.get('GEMINI_API_KEY')
        if api_key:
            payload = json.dumps({
                "contents": [{
                    "parts": [
                        {"inline_data": {"mime_type": mime_type, "data": img_b64}},
                        {"text": prompt}
                    ]
                }]
            }).encode()
            try:
                req = urllib.request.Request(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}",
                    data=payload,
                    headers={'Content-Type': 'application/json'},
                    method='POST'
                )
                with urllib.request.urlopen(req, timeout=60) as r:
                    data = json.loads(r.read())
                result = data['candidates'][0]['content']['parts'][0]['text']
            except Exception as e:
                if on_status: on_status(f"⚠️ Gemini ошибка: {e}")

    if not result:
        return "❌ Все Vision-провайдеры недоступны. Нужен ключ OpenAI/Anthropic/Gemini/OpenRouter."

    # Отправляем результат в чат если нужно
    if chat_id and mode == 'ocr':
        from telegram_client import send_message
        send_message(f"👁 OCR результат:\n<code>{result[:3000]}</code>", chat_id)

    return f"👁 <b>Анализ ({mode})</b>:\n{result}"


# ── VISION для Telegram: пользователь присылает фото ─────────────────────────
@register_tool(
    "vision_telegram",
    "Анализ изображения которое пользователь прислал в Telegram. "
    "ARGS: {file_id, question?, mode?}. "
    "Используй когда пользователь прислал фото и спрашивает про него.",
    "media"
)
def tool_vision_telegram(args, chat_id=None, on_status=None):
    if isinstance(args, str):
        try: args = json.loads(args)
        except: args = {'file_id': str(args)}

    file_id  = args.get('file_id', '')
    question = args.get('question', 'Опиши изображение подробно')
    mode     = args.get('mode', 'describe')

    if not file_id:
        return "❌ Нужен file_id из Telegram"

    if on_status: on_status("📥 Скачиваю фото из Telegram...")

    # Скачиваем файл через Telegram Bot API
    try:
        import urllib.request
        token = os.environ.get('TELEGRAM_BOT_TOKEN', '')
        if not token:
            return "❌ TELEGRAM_BOT_TOKEN не задан"

        # Получаем путь к файлу
        with urllib.request.urlopen(
            f"https://api.telegram.org/bot{token}/getFile?file_id={file_id}",
            timeout=15
        ) as r:
            file_info = json.loads(r.read())

        if not file_info.get('ok'):
            return f"❌ Ошибка getFile: {file_info}"

        file_path = file_info['result']['file_path']
        file_url  = f"https://api.telegram.org/file/bot{token}/{file_path}"

        # Скачиваем
        tmp_path = os.path.join(BASE, 'agent_projects', f'tg_{int(time.time())}.jpg')
        os.makedirs(os.path.dirname(tmp_path), exist_ok=True)

        req = urllib.request.Request(file_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30) as r:
            with open(tmp_path, 'wb') as f:
                f.write(r.read())

    except Exception as e:
        return f"❌ Ошибка скачивания: {e}"

    # Анализируем
    return tool_analyze_image(
        {'image': tmp_path, 'question': question, 'mode': mode},
        chat_id=chat_id, on_status=on_status
    )


    # Финальный ответ после max_rounds
    summary_prompt = (
        f"Задача выполнена. Вот результаты:\n" +
        "\n".join(f"- {r['tool']}: {r['result'][:300]}" for r in accumulated_results) +
        f"\n\nСоставь итоговый ответ для пользователя по запросу: {user_request}"
    )
    final = call_llm(summary_prompt, max_tokens=1000)
    return final, accumulated_results
