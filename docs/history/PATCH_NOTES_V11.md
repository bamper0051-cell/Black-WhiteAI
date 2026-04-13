# AGENT_SMITH — Patch v11 (Admin Panel Root Cause Fix)

## Корневая причина "не работает"

В .env было:
    ADMIN_WEB_TOKEN=8331220893:AAG-OAtsU8Hz...  ← это BOT_TOKEN, не токен панели!

admin_web.py читал ADMIN_WEB_TOKEN один раз при импорте (module-level).
serve_panel() вшивал этот токен в HTML.
Браузер отправлял этот токен в X-Admin-Token заголовке.
Но require_token() тоже читал ADMIN_WEB_TOKEN один раз при старте.
Если .env перезагружался — значения расходились → 401 на всех запросах.

## Исправления

### 1. Ленивое чтение токена (admin_web.py)

require_token() теперь читает токен при КАЖДОМ запросе:
  current_token = os.environ.get('ADMIN_WEB_TOKEN', 'changeme_secret_token')

serve_panel() читает токен при КАЖДОЙ выдаче страницы:
  _fresh_token = os.environ.get('ADMIN_WEB_TOKEN', 'changeme_secret_token')

Токен в HTML обновляется regex-заменой (устойчиво к повторному вшиванию).

### 2. /api/whoami — диагностический эндпоинт (без авторизации)

GET /api/whoami  →  {ok, token_hint: "8331****", token_len: 46, port, base_dir}

Браузер показывает подсказку когда токен неверный:
  "❌ Неверный токен. Подсказка: начинается с 8331****"

### 3. Startup warning (admin_web.py)

При старте бот печатает:
  ⚠️ ADMIN_WEB_TOKEN похож на BOT_TOKEN. Задай отдельный токен.

### 4. auth_module.py — bcrypt optional

import bcrypt обёрнут в try/except.
Fallback на hashlib.sha256 если bcrypt не установлен.
Панель больше не падает на import auth_module при отсутствии bcrypt.

## Настройка

Добавь в .env:
    ADMIN_WEB_TOKEN=my_secret_panel_token_here

Доступ к панели:
    http://your-server-ip:8080/panel
    (токен вшивается автоматически)

Или вручную с токеном:
    http://your-server-ip:8080/panel?token=my_secret_panel_token_here
