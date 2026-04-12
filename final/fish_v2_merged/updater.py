"""
updater.py — Механизм авто-обновления бота.

Поддерживает:
  1. Обновление pip-пакетов (yt-dlp, edge-tts, requests и др.)
  2. Проверка и скачивание новой версии бота с GitHub (если задан репо)
  3. Самодиагностика — проверка всех зависимостей
  4. Отчёт об установленных версиях
"""

import os
import sys
import subprocess
import json
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Пакеты которые стоит держать актуальными
CORE_PACKAGES = [
    'requests', 'python-dotenv', 'flask',
    'edge-tts', 'yt-dlp',
]
OPTIONAL_PACKAGES = [
    'openai', 'anthropic', 'google-generativeai',
    'mistralai', 'groq', 'cohere', 'python-docx',
    'Pillow',
]

def _run(cmd: list, timeout=120) -> tuple:
    """Запускает команду, возвращает (returncode, stdout, stderr)."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=timeout, encoding='utf-8', errors='replace')
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return -1, '', 'Timeout'
    except Exception as e:
        return -1, '', str(e)


def get_package_versions() -> dict:
    """Возвращает словарь {пакет: версия} для установленных пакетов."""
    rc, out, _ = _run([sys.executable, '-m', 'pip', 'list', '--format=json'])
    if rc != 0:
        return {}
    try:
        pkgs = json.loads(out)
        return {p['name'].lower(): p['version'] for p in pkgs}
    except Exception:
        return {}


def check_dependencies() -> list:
    """
    Проверяет доступность всех зависимостей.
    Возвращает список dict: {name, installed, version, optional}
    """
    installed = get_package_versions()
    results = []

    for pkg in CORE_PACKAGES:
        key = pkg.lower().replace('-', '_').replace('python_', '')
        # Пробуем несколько вариантов имени
        ver = (installed.get(pkg.lower()) or
               installed.get(key) or
               installed.get(pkg.lower().replace('-', '_')))
        results.append({
            'name': pkg, 'installed': bool(ver),
            'version': ver or '—', 'optional': False
        })

    for pkg in OPTIONAL_PACKAGES:
        key = pkg.lower().replace('-', '_')
        ver = installed.get(pkg.lower()) or installed.get(key)
        results.append({
            'name': pkg, 'installed': bool(ver),
            'version': ver or '—', 'optional': True
        })

    return results


def install_package(package: str, upgrade=False) -> tuple:
    """Устанавливает/обновляет пакет. Возвращает (ok, output)."""
    cmd = [sys.executable, '-m', 'pip', 'install']
    if upgrade:
        cmd.append('--upgrade')
    # Для Termux нужен --break-system-packages
    cmd += ['--break-system-packages', '--quiet', package]
    rc, out, err = _run(cmd, timeout=180)
    return rc == 0, (out + err).strip()


def upgrade_core(on_progress=None) -> dict:
    """
    Обновляет все core-пакеты.
    on_progress(package, ok, msg) — колбэк прогресса.
    """
    results = {'ok': [], 'failed': []}
    for pkg in CORE_PACKAGES:
        if on_progress:
            on_progress(pkg, None, f'Обновляю {pkg}...')
        ok, msg = install_package(pkg, upgrade=True)
        if ok:
            results['ok'].append(pkg)
        else:
            results['failed'].append({'pkg': pkg, 'error': msg[:100]})
        if on_progress:
            on_progress(pkg, ok, msg[:100])
    return results


def get_bot_info() -> dict:
    """Возвращает информацию о боте — версия, файлы, размер."""
    info = {
        'version':    '2.1',
        'base_dir':   BASE_DIR,
        'py_version': sys.version.split()[0],
        'files':      [],
        'total_size': 0,
    }
    for fname in sorted(os.listdir(BASE_DIR)):
        if fname.endswith('.py'):
            path = os.path.join(BASE_DIR, fname)
            size = os.path.getsize(path)
            info['files'].append({'name': fname, 'size': size})
            info['total_size'] += size
    return info


def format_deps_report(deps: list) -> str:
    """Форматирует отчёт о зависимостях для Telegram (HTML)."""
    lines = ['📦 <b>Зависимости:</b>\n']
    core    = [d for d in deps if not d['optional']]
    optional= [d for d in deps if d['optional']]

    lines.append('<b>🔧 Основные:</b>')
    for d in core:
        icon = '✅' if d['installed'] else '❌'
        lines.append(f"  {icon} <code>{d['name']}</code> {d['version']}")

    lines.append('\n<b>📚 Опциональные:</b>')
    for d in optional:
        icon = '✅' if d['installed'] else '⬜'
        lines.append(f"  {icon} <code>{d['name']}</code> {d['version']}")

    missing_core = [d['name'] for d in core if not d['installed']]
    if missing_core:
        lines.append(f'\n⚠️ <b>Не установлены (core):</b>')
        lines.append(f"<code>pip install {' '.join(missing_core)} --break-system-packages</code>")

    return '\n'.join(lines)


def format_bot_info(info: dict) -> str:
    """Форматирует информацию о боте."""
    lines = [
        f"🤖 <b>АВТОМУВИ v{info['version']}</b>",
        f"🐍 Python: <code>{info['py_version']}</code>",
        f"📁 Файлов: <b>{len(info['files'])}</b>",
        f"💾 Размер: <b>{info['total_size'] // 1024} KB</b>",
        f"",
        "<b>Файлы:</b>",
    ]
    for f in info['files'][:15]:
        lines.append(f"  • <code>{f['name']}</code> ({f['size']//1024} KB)")
    return '\n'.join(lines)
