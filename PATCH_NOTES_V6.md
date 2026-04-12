# AGENT_SMITH -- Patch Notes v6 (Roles + Admin Panel)

## Корневые причины сломанных ограничений (было)

1. /env вызывался без проверки view_env -- любой мог увидеть ключи
2. _PERM_MAP в _route_callback не покрывал fm:, tasks:, menu_video, llm_m: и др.
3. admin_main_keyboard показывала .env-кнопки всем ADM (только GOD должен видеть)
4. priv: handler позволял ADM назначить god-роль без проверки can_manage
5. /run /parse /process не проверяли manage_bots -- любой authenticated мог вызвать

## Исправления

### roles.py (без изменений логики -- уже верный по ТЗ)
- GOD: всё включая view_env, set_fine, manage_god
- ADM: без view_env, edit_env, set_fine, manage_god, god_panel
- VIP: все функции + vote_kick/vote_mute. Нет admin функций и .env
- USER: chat, code_agent, image_gen (Pollinations only), tts, llm_free, profile, billing
- NOOB: только profile, billing, help
- BAN: только pay_fine

### admin_module.py -- Обновлённая панель

**admin_main_keyboard(chat_id):**
- Принимает chat_id для определения роли актора
- Секции: Пользователи / Сообщения / Агенты / Система / Настройки
- GOD-панель (5-я секция): видна ТОЛЬКО GOD
  - .env / Ключи, Редактировать .env
  - Штраф BAN, Управление GOD
- Убраны дублирующие кнопки Cloudflared QR

**user_manage_keyboard(target_id, actor_role):**
- Принимает actor_role для фильтрации доступных ролей
- ADM видит кнопки: noob / user / vip / adm / ban
- GOD дополнительно видит кнопку: god
- ADM не может назначить god через UI

### bot.py -- Исправления проверок

**_PERM_MAP расширен:**
  agent_code2_start -> code_agent
  menu_agent        -> agent_0051
  menu_video        -> video
  menu_tools        -> tools_basic
  llm_m             -> llm_change
  fm                -> file_manager
  tasks             -> task_queue
  selfcheck         -> admin_panel (не view_logs)

**Новые гейты:**
- /env команда: проверяет view_env, отказывает если не GOD
- _show_env(): double-check view_env на уровне функции
- /run /parse /process: проверяют manage_bots
- priv: callback: can_manage() -- ADM не может назначить god или adm >= себя
  - Если priv == 'god' и actor != 'god' -- отказ с alert

### auth_module.py
- PRIVILEGE_ICONS/LABELS теперь импортируются из roles.py
  (единый источник истины, fallback если roles.py недоступен)
