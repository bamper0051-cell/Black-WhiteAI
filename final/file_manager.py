"""
file_manager.py — Файловый менеджер для ИИ-чата.

Позволяет просматривать, открывать, отправлять и удалять файлы/папки
прямо из Telegram-чата. Каждое деструктивное действие требует подтверждения.
"""

import os
import shutil
import zipfile
import tarfile
import time
from pathlib import Path

# Корень для файлового менеджера — домашняя директория Termux
HOME = os.path.expanduser("~")
BOT_DIR = os.path.dirname(os.path.abspath(__file__))

# Типы файлов → иконки
_ICONS = {
    'dir':  '📁',
    '.py':  '🐍', '.js':  '📜', '.ts':  '📜', '.html': '🌐', '.css': '🎨',
    '.txt': '📄', '.md':  '📝', '.csv': '📊', '.json': '🔧', '.xml': '🔧',
    '.zip': '📦', '.rar': '📦', '.tar': '📦', '.gz':   '📦', '.7z':  '📦',
    '.mp3': '🎵', '.mp4': '🎬', '.avi': '🎬', '.mkv':  '🎬', '.wav': '🎵',
    '.jpg': '🖼',  '.jpeg':'🖼',  '.png': '🖼',  '.gif':  '🖼',  '.webp':'🖼',
    '.pdf': '📕', '.docx':'📃', '.xlsx':'📊', '.pptx': '📊',
    '.sh':  '⚙️', '.env':  '🔑', '.db':  '🗃',
}

def _icon(path):
    if os.path.isdir(path):
        return _ICONS['dir']
    ext = os.path.splitext(path)[1].lower()
    return _ICONS.get(ext, '📄')

def _size_str(path):
    try:
        if os.path.isdir(path):
            total = sum(
                os.path.getsize(os.path.join(dp, f))
                for dp, dn, fns in os.walk(path) for f in fns
            )
            return f"{total // 1024} KB"
        s = os.path.getsize(path)
        if s > 1024 * 1024:
            return f"{s // 1024 // 1024} MB"
        return f"{s // 1024} KB"
    except Exception:
        return "?"

def _mtime(path):
    try:
        return time.strftime('%d.%m %H:%M', time.localtime(os.path.getmtime(path)))
    except Exception:
        return ""


def list_dir(path, max_items=30):
    """
    Возвращает (items_list, parent_path, error_str).
    items_list — список dict с ключами: name, path, icon, size, mtime, is_dir
    """
    if not os.path.exists(path):
        return [], None, f"❌ Путь не найден: {path}"
    if not os.path.isdir(path):
        return [], None, f"❌ Это файл, а не директория: {path}"

    try:
        entries = sorted(os.scandir(path), key=lambda e: (not e.is_dir(), e.name.lower()))
        items = []
        for entry in entries[:max_items]:
            items.append({
                'name':   entry.name,
                'path':   entry.path,
                'icon':   _icon(entry.path),
                'size':   _size_str(entry.path),
                'mtime':  _mtime(entry.path),
                'is_dir': entry.is_dir(),
            })
        parent = str(Path(path).parent) if path != HOME else None
        return items, parent, None
    except PermissionError:
        return [], None, f"❌ Нет доступа к {path}"
    except Exception as e:
        return [], None, f"❌ {e}"


def format_listing(path, items, parent):
    """Форматирует листинг для Telegram (HTML)."""
    lines = [f"📂 <b>{path}</b>\n"]
    if not items:
        lines.append("<i>(пусто)</i>")
    for item in items:
        name = item['name']
        size = item['size']
        mt   = item['mtime']
        icon = item['icon']
        if item['is_dir']:
            lines.append(f"{icon} <b>{name}/</b>  <i>{size}</i>")
        else:
            lines.append(f"{icon} {name}  <i>{size} · {mt}</i>")
    return "\n".join(lines)


def read_file_preview(path, max_chars=3000):
    """Читает текстовый файл и возвращает превью."""
    ext = os.path.splitext(path)[1].lower()
    # Бинарные форматы — не читаем как текст
    if ext in ('.zip', '.rar', '.gz', '.tar', '.7z', '.mp3', '.mp4',
               '.avi', '.mkv', '.jpg', '.jpeg', '.png', '.gif',
               '.pdf', '.docx', '.xlsx', '.db'):
        return None, f"⚠️ Бинарный файл ({ext}) — превью недоступно"
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read(max_chars)
        truncated = os.path.getsize(path) > max_chars
        return content, "…(обрезано)" if truncated else None
    except Exception as e:
        return None, f"❌ {e}"


def list_archive(path):
    """Показывает содержимое архива."""
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext == '.zip':
            with zipfile.ZipFile(path) as zf:
                names = zf.namelist()
        elif ext in ('.tar', '.gz', '.bz2', '.xz'):
            with tarfile.open(path) as tf:
                names = tf.getnames()
        else:
            return f"⚠️ Неподдерживаемый формат архива: {ext}"
        lines = [f"📦 <b>{os.path.basename(path)}</b> ({len(names)} файлов):"]
        for name in names[:30]:
            lines.append(f"  • {name}")
        if len(names) > 30:
            lines.append(f"  … и ещё {len(names) - 30}")
        return "\n".join(lines)
    except Exception as e:
        return f"❌ Ошибка чтения архива: {e}"


def delete_path(path):
    """Удаляет файл или директорию. Возвращает (ok, message)."""
    try:
        if os.path.isdir(path):
            shutil.rmtree(path)
            return True, f"✅ Папка удалена: {path}"
        else:
            os.remove(path)
            return True, f"✅ Файл удалён: {path}"
    except Exception as e:
        return False, f"❌ Ошибка удаления: {e}"


def rename_path(src, new_name):
    """Переименовывает файл/папку. Возвращает (ok, new_path, message)."""
    new_path = os.path.join(os.path.dirname(src), new_name)
    try:
        os.rename(src, new_path)
        return True, new_path, f"✅ Переименовано: {os.path.basename(src)} → {new_name}"
    except Exception as e:
        return False, None, f"❌ {e}"


def is_safe_path(path, root=None):
    """Проверяет что путь не выходит за пределы root (HOME по умолчанию)."""
    root = root or HOME
    try:
        return os.path.realpath(path).startswith(os.path.realpath(root))
    except Exception:
        return False


def quick_stats(path):
    """Быстрая статистика директории."""
    files = dirs = 0
    total_size = 0
    try:
        for dp, dn, fns in os.walk(path):
            dirs  += len(dn)
            files += len(fns)
            for f in fns:
                try:
                    total_size += os.path.getsize(os.path.join(dp, f))
                except Exception:
                    pass
    except Exception:
        pass
    return {
        'files': files,
        'dirs':  dirs,
        'size':  total_size,
        'size_str': f"{total_size // 1024 // 1024} MB" if total_size > 1024*1024
                    else f"{total_size // 1024} KB"
    }
