# AGENT_SMITH -- Patch Notes v5

## 1. roles.py -- Role System v3 (точно по ТЗ)

### Роли и права:

GOD  -- Все привилегии без исключений. Единственный кто видит .env и ключи.
         Устанавливает стоимость штрафа. Управляет всеми включая ADM.

ADM  -- Почти как GOD. Исключения:
         - НЕ может просматривать/редактировать .env
         - НЕ может управлять GOD-пользователями (can_manage('adm','god') = False)
         - Нет god_panel, manage_god, view_env, edit_env, set_fine

VIP  -- Все функции бота. Исключения:
         - НЕТ доступа к информации о других пользователях
         - НЕ может кикать/банить
         - МОЖЕТ запустить голосование (кик / мут до 90 мин) -- vote_kick, vote_mute

USER -- Первый вход. Доступ:
         - Бесплатные LLM (llm_free)
         - ИИ-чат (chat)
         - Агент-кодер (code_agent) + coder3_quick + coder3_sandbox
         - AI ассистент (ai_assistant)
         - Генерация картинок ТОЛЬКО Pollinations (image_gen БЕЗ image_gen_paid)
         - Озвучка TTS
         - Смена LLM (в пределах бесплатных)
         - Профиль, Биллинг, Справка, Веб-поиск

NOOB -- Только: Мой профиль + Биллинг + Справка

BAN  -- Только: Оплатить штраф (стоимость устанавливает GOD через set_fine)

### Новые функции roles.py:
- `get_limits(role)` -- dict лимитов (daily_tasks, max_tokens, sandbox_timeout...)
- `get_limit(role, key)` -- конкретный лимит
- `can_manage(a, b)` -- ADM не может управлять GOD
- `roles_summary()` -- HTML-таблица ролей
- `user_card(role)` -- карточка прав пользователя
- `perm_denied_msg()` -- показывает минимальную роль для апгрейда

## 2. agent_roles.py -- RBAC адаптер v3

- `get_role(chat_id)` -- сначала проверяет admin_module (admin_ids файл), потом DB
- `coder3_perm(mode, chat_id)` -- проверка права режима CODER3
- `smith_perm(chat_id, ...)` -- проверка прав АГЕНТ_СМИТ
- `get_sandbox_timeout(chat_id)` -- таймаут по роли
- `get_fix_attempts(chat_id)` -- попыток авто-фикса по роли
- `get_max_tokens(chat_id)` -- лимит токенов
- `get_max_file_mb(chat_id)` -- лимит файла

## 3. auth_module.py -- синхронизация PRIVILEGE_ICONS/LABELS

PRIVILEGE_ICONS и PRIVILEGE_LABELS теперь импортируются из roles.py --
единственный источник истины. Fallback на хардкод если roles.py недоступен.

## 4. Разбивка bot.py (8651 строк -> 5 логичных модулей)

bot_ui.py       (~1000 строк) -- Клавиатуры и меню
  - kb(), btn(), back_btn(), btn_model()
  - menu_keyboard() -- переписан по ролям
  - style_keyboard(), tts_keyboard(), llm_keyboard()
  - agent_keyboard(), chat_control_keyboard()
  - _current_status_text()

bot_handlers.py (~1318 строк) -- Текстовые сообщения
  - handle_text() -- главный обработчик текста
  - _handle_agent_message() -- агент-режим
  - _run_code_task(), _run_code_pipeline()
  - _handle_input() -- обработчик состояний ожидания

bot_callbacks.py (~3515 строк) -- Inline кнопки
  - handle_callback() -- главный диспетчер
  - _route_callback() -- маршрутизатор действий
  - _route_smith() -- АГЕНТ_СМИТ колбэки

bot_fish.py     (~1634 строк) -- Фишинг-модуль
  - fish_menu_keyboard()
  - Все _fish_* функции

bot_main.py     (~878 строк) -- Точка входа
  - _help_text() -- ПЕРЕПИСАН, показывает только доступные функции по роли
  - scheduled_cycle(), poll(), main()
  - handle_photo(), handle_document()

## 5. Исправления

- bot.py: UnboundLocalError get_system_info в adm:sysinfo -- исправлен в v4
- menu_keyboard: get_role теперь через agent_roles (не admin_module напрямую)
- _help_text: role-aware -- NOOB видит только профиль/биллинг,
  BAN видит только оплатить штраф, USER видит свои функции
