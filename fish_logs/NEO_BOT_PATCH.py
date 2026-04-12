"""
NEO_BOT_PATCH.py — Инструкции по интеграции агента НЕО в bot.py
=================================================================

Добавить в bot.py в 4 местах. Ctrl+F по якорным строкам.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ПАТЧ 1 — Импорт модуля (после блока try/except cloudflare_qr_bot)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Найти строку (~строка 100):
    try:
        import graceful_shutdown as _gs

Вставить ПЕРЕД ней:

    try:
        from agent_neo import (
            neo_respond, set_prompt, set_persona, get_current_prompt,
            get_current_persona, clear_history, neo_main_keyboard,
            neo_personas_keyboard, neo_library_keyboard,
            neo_after_prompt_keyboard, render_neo_welcome,
            render_prompt_editor_intro, render_persona_list,
            render_prompt_library, save_prompt_to_library,
            load_prompt_from_library, delete_prompt_from_library,
            BUILTIN_PERSONAS,
        )
        NEO_ENABLED = True
    except ImportError as _ne:
        NEO_ENABLED = False
        print(f"  ⚠️ agent_neo не загружен: {_ne}", flush=True)


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ПАТЧ 2 — Кнопка в меню (menu_keyboard)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Найти строку (~строка 527):
    if hp('chat'):      row1.append(btn("💬 ИИ-Чат",       "agent_chat_start"))
    if hp('code_agent'): row1.append(btn("💻 Агент-Кодер",  "agent_code_start"))

Добавить ПОСЛЕ (в том же блоке if hp('chat') or hp('code_agent')):

        if NEO_ENABLED and hp('ai_assistant'):
            rows.append([btn("🕶 Агент НЕО", "neo:start")])


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ПАТЧ 3 — Обработка wait_state (в handle_text / _handle_wait_state)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Найти блок (~строка 1593):
    if chat_id in _wait_state:
        state = _wait_state[chat_id]

Добавить ВНУТРИ блока if, перед строкой `if state == 'custom_prompt':`:

        # ── НЕО: ввод промпта ──────────────────────────────────────────────
        if state == 'neo_set_prompt' and NEO_ENABLED:
            _wait_state.pop(chat_id, None)
            set_prompt(chat_id, text)
            preview = text[:200] + ('...' if len(text) > 200 else '')
            send_message(
                f"✅ <b>Промпт НЕО обновлён!</b>\\n\\n<i>{preview}</i>\\n\\n"
                "Агент НЕО теперь будет отвечать в этой роли.",
                chat_id,
                reply_markup=neo_after_prompt_keyboard(btn, kb)
            )
            return

        if state == 'neo_save_name' and NEO_ENABLED:
            _wait_state.pop(chat_id, None)
            prompt_to_save = _neo_pending_prompt.pop(chat_id, get_current_prompt(chat_id))
            name = text.strip()[:40]
            ok = save_prompt_to_library(chat_id, name, prompt_to_save)
            if ok:
                send_message(
                    f"💾 Промпт <b>{name}</b> сохранён в библиотеку.",
                    chat_id,
                    reply_markup=kb([btn("📚 Библиотека", "neo:library"),
                                     btn("◀️ Меню НЕО",  "neo:menu")])
                )
            else:
                send_message(
                    f"⚠️ Не удалось сохранить (лимит {MAX_CUSTOM_PROMPTS} промптов).",
                    chat_id,
                    reply_markup=kb([btn("◀️ Меню НЕО", "neo:menu")])
                )
            return

        # ── НЕО: диалог ────────────────────────────────────────────────────
        if state == 'neo_chat' and NEO_ENABLED:
            def _neo_do():
                reply = neo_respond(chat_id, text)
                send_message(
                    reply[:4000],
                    chat_id,
                    reply_markup=kb(
                        [btn("✏️ Промпт", "neo:edit_prompt"),
                         btn("🎭 Персона", "neo:personas")],
                        [btn("🔴 Завершить", "neo:stop")]
                    )
                )
            _run_in_thread(_neo_do)
            return


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ПАТЧ 4 — Callback-обработчики (в handle_callback, блок elif action ==)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Найти строку (~строка 3411):
    elif action == 'menu_agent':

Вставить ПЕРЕД ней весь блок ниже:

    # ════════════════════════════════════════════════════════
    #  АГЕНТ НЕО
    # ════════════════════════════════════════════════════════

    elif action == 'neo' and arg == 'start':
        answer_callback(cb_id)
        if not NEO_ENABLED:
            send_message("❌ agent_neo не загружен.", chat_id)
            return
        _wait_state[chat_id] = 'neo_chat'
        edit_message(chat_id, msg_id,
            render_neo_welcome(chat_id),
            reply_markup=neo_main_keyboard(btn, kb, back_btn))

    elif action == 'neo' and arg == 'menu':
        answer_callback(cb_id)
        _wait_state[chat_id] = 'neo_chat'
        edit_message(chat_id, msg_id,
            render_neo_welcome(chat_id),
            reply_markup=neo_main_keyboard(btn, kb, back_btn))

    elif action == 'neo' and arg == 'edit_prompt':
        answer_callback(cb_id)
        _wait_state[chat_id] = 'neo_set_prompt'
        edit_message(chat_id, msg_id,
            render_prompt_editor_intro(),
            reply_markup=kb([btn("❌ Отмена", "neo:menu")]))

    elif action == 'neo' and arg == 'personas':
        answer_callback(cb_id)
        edit_message(chat_id, msg_id,
            render_persona_list(),
            reply_markup=neo_personas_keyboard(btn, kb, chat_id, back_btn))

    elif action == 'neo' and arg and arg.startswith('persona:'):
        answer_callback(cb_id)
        pid = arg.split(':', 1)[1]
        if set_persona(chat_id, pid):
            p = BUILTIN_PERSONAS[pid]
            _wait_state[chat_id] = 'neo_chat'
            edit_message(chat_id, msg_id,
                f"{p['emoji']} <b>Персона {p['name']} активирована!</b>\\n\\n"
                f"<i>{p['system'][:200]}</i>\\n\\nПиши — отвечу в роли.",
                reply_markup=neo_main_keyboard(btn, kb, back_btn))
        else:
            answer_callback(cb_id, "Персона не найдена")

    elif action == 'neo' and arg == 'show_prompt':
        answer_callback(cb_id)
        current = get_current_prompt(chat_id)
        pid = get_current_persona(chat_id)
        p = BUILTIN_PERSONAS.get(pid, {'name': 'Кастом', 'emoji': '✏️'})
        send_message(
            f"📋 <b>Текущий промпт</b> [{p['emoji']} {p['name']}]:\\n\\n"
            f"<pre>{current[:1000]}</pre>",
            chat_id,
            reply_markup=kb(
                [btn("✏️ Изменить", "neo:edit_prompt"),
                 btn("◀️ Меню",    "neo:menu")]
            )
        )

    elif action == 'neo' and arg == 'clear_history':
        answer_callback(cb_id)
        clear_history(chat_id)
        edit_message(chat_id, msg_id,
            "🗑 <b>История очищена.</b>\\n\\nАгент НЕО не помнит прошлых сообщений.",
            reply_markup=neo_main_keyboard(btn, kb, back_btn))

    elif action == 'neo' and arg == 'library':
        answer_callback(cb_id)
        edit_message(chat_id, msg_id,
            render_prompt_library(chat_id),
            reply_markup=neo_library_keyboard(btn, kb, chat_id, back_btn))

    elif action == 'neo' and arg == 'save_prompt':
        answer_callback(cb_id)
        current = get_current_prompt(chat_id)
        _neo_pending_prompt[chat_id] = current
        _wait_state[chat_id] = 'neo_save_name'
        send_message(
            f"💾 <b>Сохранить промпт</b>\\n\\n"
            f"<i>{current[:150]}...</i>\\n\\n"
            "Придумай название (до 40 символов):",
            chat_id,
            reply_markup=kb([btn("❌ Отмена", "neo:menu")])
        )

    elif action == 'neo' and arg and arg.startswith('load_prompt:'):
        answer_callback(cb_id)
        prompt_id = int(arg.split(':', 1)[1])
        name = load_prompt_from_library(chat_id, prompt_id)
        if name:
            _wait_state[chat_id] = 'neo_chat'
            edit_message(chat_id, msg_id,
                f"✅ Промпт <b>{name}</b> загружен и активирован.\\n\\nПиши — отвечу в новой роли.",
                reply_markup=neo_main_keyboard(btn, kb, back_btn))
        else:
            answer_callback(cb_id, "Промпт не найден")

    elif action == 'neo' and arg and arg.startswith('del_prompt:'):
        answer_callback(cb_id)
        prompt_id = int(arg.split(':', 1)[1])
        delete_prompt_from_library(chat_id, prompt_id)
        edit_message(chat_id, msg_id,
            render_prompt_library(chat_id),
            reply_markup=neo_library_keyboard(btn, kb, chat_id, back_btn))

    elif action == 'neo' and arg == 'start_chat':
        answer_callback(cb_id)
        _wait_state[chat_id] = 'neo_chat'
        send_message(
            "💬 Пиши — агент НЕО отвечает.",
            chat_id,
            reply_markup=kb(
                [btn("✏️ Промпт", "neo:edit_prompt"), btn("🎭 Персона", "neo:personas")],
                [btn("🔴 Завершить", "neo:stop")]
            )
        )

    elif action == 'neo' and arg == 'stop':
        answer_callback(cb_id)
        _wait_state.pop(chat_id, None)
        edit_message(chat_id, msg_id,
            "🔴 Сессия НЕО завершена.",
            reply_markup=kb([btn("🕶 Снова НЕО", "neo:start"),
                             btn("◀️ Меню",      "menu")]))


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ПАТЧ 5 — Глобальная переменная (рядом с _wait_state)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Найти строку (~445):
    _wait_state = {}

Добавить после неё:

    _neo_pending_prompt = {}   # chat_id → промпт ожидающий имени для сохранения


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ПАТЧ 6 — Разбор callback data (в handle_callback, начало функции)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Найти строку где разбирается data на action/arg, примерно:
    parts  = data.split(':', 1)
    action = parts[0]
    arg    = parts[1] if len(parts) > 1 else ''

Убедиться что для neo:persona:neo и neo:load_prompt:5 разбор работает.
Если action берётся только как первый сегмент — нужно добавить:

    # Для neo: action='neo', arg='persona:neo' или 'load_prompt:5'
    # Это уже обрабатывается через arg.startswith(...) в патче 4 ✅


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ПРОВЕРКА ПОСЛЕ ИНТЕГРАЦИИ
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Запустить:
    python bot.py

Ожидаемый лог (успех):
    ✅ Нет строки "agent_neo не загружен"

В боте:
    /menu → должна появиться кнопка "🕶 Агент НЕО"
    Нажать → открывается меню НЕО
    "✏️ Изменить промпт" → вводим текст → промпт применяется
    "🎭 Выбрать персону" → переключаем персону
    "💾 Сохранить промпт" → вводим имя → сохраняется в библиотеку
    "📚 Библиотека" → список + кнопки загрузки/удаления
    Пишем текст → НЕО отвечает в заданной роли
"""
