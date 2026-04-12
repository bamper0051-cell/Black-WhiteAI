# BlackBugsAI Backup — Restore Guide

**Архив:** `BlackBugsAI_full_20260321_003758.zip`  
**Файлов:** 195  
**Размер:** 6.4 MB  
**Создан:** 2026-03-21 00:38:14

## Восстановление

```bash
# Метод 1 — через скрипт
python backup.py --restore BlackBugsAI_full_20260321_003758.zip

# Метод 2 — вручную
unzip -o BlackBugsAI_full_20260321_003758.zip -d /путь/к/HACK_TOOLS/

# Метод 3 — Docker
docker cp BlackBugsAI_full_20260321_003758.zip automuvie:/app/
docker exec automuvie python backup.py --restore BlackBugsAI_full_20260321_003758.zip
```

## После восстановления

```bash
docker restart automuvie
```
