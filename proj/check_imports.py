"""
check_imports.py — запусти это чтобы найти все "from app." импорты
python check_imports.py
"""
import os, re

pattern = re.compile(r'^[^#\n]*(?:from|import)\s+app[\.\s]', re.MULTILINE)
base = os.path.dirname(os.path.abspath(__file__))
found = []

for fname in os.listdir(base):
    if not fname.endswith('.py'): continue
    fpath = os.path.join(base, fname)
    try:
        content = open(fpath, encoding='utf-8', errors='ignore').read()
        for i, line in enumerate(content.splitlines(), 1):
            if re.search(r'(?:from|import)\s+app[\.\s]', line) and not line.strip().startswith('#'):
                found.append((fname, i, line.strip()))
    except Exception as e:
        print(f"⚠️ {fname}: {e}")

if found:
    print(f"\n❌ Найдено {len(found)} проблемных строк:\n")
    for fname, lineno, line in found:
        print(f"  {fname}:{lineno}  {line}")
    print("\n💡 Замени эти файлы на новые из outputs/")
else:
    print("✅ Файлов с 'from app.' не найдено — всё чисто")
