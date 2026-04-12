"""
autofix.py — автоматически фиксит все "from app." импорты
Запусти: python autofix.py
"""
import os, re

base = os.path.dirname(os.path.abspath(__file__))

REPLACEMENTS = {
    # billing.py
    r'from app\.config\.settings import PLANS': 'import config as _cfg; PLANS = _cfg.PLANS',
    r'from app\.config\.settings import (.+)':  r'import config as _cfg  # \1 available via _cfg',
    # tool_registry.py
    r'from app\.config\.settings import PLANS': 'import config as _cfg; PLANS = _cfg.PLANS',
    # pars.py и другие app imports
    r'from app\.\S+ import (\S+)': r'# REMOVED: from app import \1 — not available in flat structure',
}

SKIP_FILES = {'check_imports.py', 'autofix.py'}

fixed = 0
for fname in os.listdir(base):
    if not fname.endswith('.py'): continue
    if fname in SKIP_FILES: continue
    # Пропускаем bot2.py, botу.py, и.py — это мусорные дубли
    if fname in ('bot2.py', 'botу.py', 'и.py', 'pars.py'): continue

    fpath = os.path.join(base, fname)
    try:
        original = open(fpath, encoding='utf-8', errors='ignore').read()
        content  = original

        for pattern, replacement in REPLACEMENTS.items():
            content = re.sub(pattern, replacement, content)

        if content != original:
            open(fpath, 'w', encoding='utf-8').write(content)
            print(f"✅ Исправлен: {fname}")
            fixed += 1
    except Exception as e:
        print(f"⚠️ {fname}: {e}")

# Удаляем мусорные файлы-дубли
trash = ['bot2.py', 'botу.py', 'и.py']
for f in trash:
    fpath = os.path.join(base, f)
    if os.path.exists(fpath):
        os.remove(fpath)
        print(f"🗑 Удалён дубль: {f}")

print(f"\n✅ Готово. Исправлено файлов: {fixed}")
print("Запусти check_imports.py ещё раз для проверки.")
