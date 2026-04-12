#!/usr/bin/env python3
"""
backup.py — BlackBugsAI Project Backup
Создаёт полный архив проекта с версионированием.

Использование:
  python backup.py              # полный бэкап
  python backup.py --code       # только .py + конфиги (без БД)
  python backup.py --db         # только базы данных
  python backup.py --list       # показать существующие бэкапы
  python backup.py --restore X  # восстановить из архива X
"""

import os, sys, zipfile, shutil, argparse, hashlib, json, time
from datetime import datetime
from pathlib import Path

# ─── Конфиг ──────────────────────────────────────────────────────────────────

BASE_DIR    = Path(__file__).parent
BACKUP_DIR  = BASE_DIR / 'backups'
PROJECT     = 'BlackBugsAI'
MAX_BACKUPS = 10   # хранить последних N бэкапов

# Что включаем
INCLUDE_CODE = [
    '*.py', '*.html', '*.yml', '*.yaml', '*.json',
    '*.md', '*.txt', '*.env', '*.env.example',
    'Dockerfile', 'Dockerfile.*', '*.bat', '*.sh',
    '*.cfg', '*.ini', '*.toml',
]

INCLUDE_DB = [
    '*.db', '*.sqlite', '*.sqlite3',
]

# Что исключаем
EXCLUDE_DIRS = {
    '__pycache__', '.git', '.idea', '.vscode',
    'node_modules', 'venv', 'env', '.venv',
    'agent_projects', 'fish_uploads', 'fish_pages',
    'fish_logs', 'artifacts', 'created_bots',
    'qr_codes', 'backups',
}

EXCLUDE_FILES = {
    '*.pyc', '*.pyo', '*.log', '*.tmp', '*.bak',
    '*.backup', 'bot.log', 'bot.log.old',
}

# ─── Утилиты ─────────────────────────────────────────────────────────────────

def ts() -> str:
    return datetime.now().strftime('%Y%m%d_%H%M%S')

def human_size(n: int) -> str:
    for unit in ('B','KB','MB','GB'):
        if n < 1024: return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"

def file_matches(name: str, patterns: list) -> bool:
    import fnmatch
    return any(fnmatch.fnmatch(name, p) for p in patterns)

def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()[:12]

def collect_files(base: Path, include: list, mode: str = 'code') -> list:
    """Собирает файлы для архивирования."""
    result = []
    for item in sorted(base.rglob('*')):
        if item.is_dir():
            continue
        # Пропускаем исключённые директории
        parts = set(item.relative_to(base).parts[:-1])
        if parts & EXCLUDE_DIRS:
            continue
        if item.parent.name in EXCLUDE_DIRS:
            continue
        # Пропускаем исключённые файлы
        if file_matches(item.name, list(EXCLUDE_FILES)):
            continue
        # Только нужные расширения
        if file_matches(item.name, include):
            result.append(item)
    return result

# ─── Команды ─────────────────────────────────────────────────────────────────

def cmd_backup(mode: str = 'full'):
    """Создаёт бэкап."""
    BACKUP_DIR.mkdir(exist_ok=True)

    stamp = ts()
    name  = f"{PROJECT}_{mode}_{stamp}.zip"
    path  = BACKUP_DIR / name

    if mode == 'code':
        include = INCLUDE_CODE
        label   = "код + конфиги"
    elif mode == 'db':
        include = INCLUDE_DB
        label   = "базы данных"
    else:
        include = INCLUDE_CODE + INCLUDE_DB
        label   = "полный бэкап"

    files = collect_files(BASE_DIR, include, mode)

    print(f"\n🗜  {PROJECT} Backup — {label}")
    print(f"   Директория: {BASE_DIR}")
    print(f"   Архив:      {path.name}")
    print(f"   Файлов:     {len(files)}")
    print()

    manifest = {
        'project':   PROJECT,
        'mode':      mode,
        'timestamp': stamp,
        'hostname':  os.uname().nodename if hasattr(os, 'uname') else 'unknown',
        'files':     [],
    }

    total_size = 0
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for f in files:
            arc_name = str(f.relative_to(BASE_DIR))
            try:
                zf.write(f, arc_name)
                size = f.stat().st_size
                total_size += size
                manifest['files'].append({
                    'path': arc_name,
                    'size': size,
                    'sha256': sha256(str(f)) if size < 10*1024*1024 else 'skipped',
                })
                print(f"  ✅ {arc_name:<55} {human_size(size)}")
            except Exception as e:
                print(f"  ⚠️  {arc_name} — {e}")

        # Манифест
        zf.writestr('MANIFEST.json', json.dumps(manifest, indent=2, ensure_ascii=False))
        zf.writestr('RESTORE.md', _restore_readme(name, len(files), total_size))

    zip_size = path.stat().st_size
    ratio    = (1 - zip_size / max(total_size, 1)) * 100

    print(f"\n{'='*60}")
    print(f"  📦 Архив:      {name}")
    print(f"  📏 Исходно:    {human_size(total_size)}")
    print(f"  🗜  Сжато:      {human_size(zip_size)}  ({ratio:.0f}% сжатие)")
    print(f"  📁 Файлов:     {len(files)}")
    print(f"  ✅ Бэкап готов: {path}")
    print(f"{'='*60}\n")

    # Удаляем старые бэкапы
    _rotate_backups(mode)

    return str(path)


def cmd_list():
    """Показывает список бэкапов."""
    BACKUP_DIR.mkdir(exist_ok=True)
    backups = sorted(BACKUP_DIR.glob(f"{PROJECT}_*.zip"), reverse=True)

    if not backups:
        print("📭 Бэкапов нет.")
        return

    print(f"\n📦 Бэкапы {PROJECT}:\n")
    print(f"  {'#':<3} {'Имя':<45} {'Размер':<10} {'Дата'}")
    print(f"  {'-'*80}")
    for i, b in enumerate(backups, 1):
        stat = b.stat()
        dt   = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')
        print(f"  {i:<3} {b.name:<45} {human_size(stat.st_size):<10} {dt}")
    print(f"\n  Всего: {len(backups)} бэкапов\n")


def cmd_restore(archive: str):
    """Восстанавливает из бэкапа."""
    path = Path(archive) if os.path.isabs(archive) else BACKUP_DIR / archive
    if not path.exists():
        # Ищем по номеру
        backups = sorted(BACKUP_DIR.glob(f"{PROJECT}_*.zip"), reverse=True)
        try:
            idx  = int(archive) - 1
            path = backups[idx]
        except (ValueError, IndexError):
            print(f"❌ Архив не найден: {archive}")
            return

    print(f"\n♻️  Восстановление из: {path.name}")
    print("⚠️  Существующие файлы будут перезаписаны!")
    ans = input("Продолжить? [y/N]: ").strip().lower()
    if ans != 'y':
        print("Отменено.")
        return

    # Бэкап текущего состояния перед восстановлением
    print("📦 Сначала создаю бэкап текущего состояния...")
    cmd_backup('code')

    with zipfile.ZipFile(path) as zf:
        members = [m for m in zf.namelist() if m not in ('MANIFEST.json', 'RESTORE.md')]
        print(f"   Восстанавливаю {len(members)} файлов...")
        for m in members:
            target = BASE_DIR / m
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(m) as src, open(target, 'wb') as dst:
                dst.write(src.read())
            print(f"  ✅ {m}")

    print(f"\n✅ Восстановлено из {path.name}\n")


def _rotate_backups(mode: str):
    """Удаляет старые бэкапы, оставляет MAX_BACKUPS."""
    pattern = f"{PROJECT}_{mode}_*.zip"
    backups = sorted(BACKUP_DIR.glob(pattern), reverse=True)
    for old in backups[MAX_BACKUPS:]:
        old.unlink()
        print(f"  🗑  Удалён старый бэкап: {old.name}")


def _restore_readme(name: str, files: int, size: int) -> str:
    return f"""# {PROJECT} Backup — Restore Guide

**Архив:** `{name}`  
**Файлов:** {files}  
**Размер:** {human_size(size)}  
**Создан:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Восстановление

```bash
# Метод 1 — через скрипт
python backup.py --restore {name}

# Метод 2 — вручную
unzip -o {name} -d /путь/к/HACK_TOOLS/

# Метод 3 — Docker
docker cp {name} automuvie:/app/
docker exec automuvie python backup.py --restore {name}
```

## После восстановления

```bash
docker restart automuvie
```
"""

# ─── CLI ─────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    p = argparse.ArgumentParser(
        description='BlackBugsAI Backup Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  python backup.py              Полный бэкап
  python backup.py --code       Только код (без БД)
  python backup.py --db         Только базы данных
  python backup.py --list       Список бэкапов
  python backup.py --restore 1  Восстановить из #1
        """
    )
    g = p.add_mutually_exclusive_group()
    g.add_argument('--code',    action='store_true', help='только .py и конфиги')
    g.add_argument('--db',      action='store_true', help='только базы данных')
    g.add_argument('--list',    action='store_true', help='список бэкапов')
    g.add_argument('--restore', metavar='NAME|NUM',  help='восстановить из архива')
    args = p.parse_args()

    if args.list:
        cmd_list()
    elif args.restore:
        cmd_restore(args.restore)
    elif args.code:
        cmd_backup('code')
    elif args.db:
        cmd_backup('db')
    else:
        cmd_backup('full')
