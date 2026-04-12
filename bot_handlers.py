"""
bot_handlers.py — Обработчики текстовых сообщений BlackBugsAI
"""
# AUTO-SPLIT from bot.py — do not edit manually, use bot.py as source of truth
import os, sys, re, json, time, random, threading, subprocess, shutil
import config
from telegram_client import (
    send_message, edit_message, answer_callback, send_document,
    delete_message, delete_webhook,
)
try:
    from agent_roles import get_role, has_perm, perm_error, get_user_limits
    ROLES_ENABLED = True
except ImportError:
    ROLES_ENABLED = False
    def get_role(cid): return 'user'
    def has_perm(cid, p): return True
    def perm_error(p, cid): return "🚫 Нет доступа"
from roles import norm_role, role_icon, role_label

from bot_ui import kb, btn, back_btn, menu_keyboard, chat_control_keyboard

def handle_text(text, chat_id, username=None, first_name=None):
    # ══ ГЛОБАЛЬНЫЙ ГЕЙТ АВТОРИЗАЦИИ ══════════════════════════════════════
    # Сначала всегда обрабатываем капчу/регистрацию/вход
    try:
        step, _ = auth_state_get(chat_id)
    except Exception:
        step = 'idle'

    if step != 'idle':
        try:
            auth_handle_text(chat_id, text.strip())
        except Exception as e:
            import traceback
            err_full = traceback.format_exc()
            print(f"[AUTH] ERROR in auth_handle_text: {type(e).__name__}: {e}\n{err_full}", flush=True)
            # Если ошибка БД — пробуем мигрировать и повторить
            if 'no such column' in str(e):
                try:
                    from auth_module import init_auth_db
                    init_auth_db()
                    auth_handle_text(chat_id, text.strip())
                    return
                except Exception as e2:
                    print(f"[AUTH] Retry after migration failed: {e2}", flush=True)
            send_message(
                f"⚠️ Ошибка: {type(e).__name__}: {e}\n\nПопробуй ещё раз или /start",
                chat_id)
            return
        try:
            step2, _ = auth_state_get(chat_id)
        except Exception:
            step2 = 'idle'
        if step2 == 'idle' and is_authenticated(chat_id):
            send_message(_current_status_text(chat_id), chat_id, reply_markup=menu_keyboard(chat_id))
        return

    # Если не авторизован — запускаем авторизацию с данными профиля
    if not is_authenticated(chat_id):
        auth_start(chat_id, username=username, first_name=first_name)
        return
    # ══ КОНЕЦ ГЕЙТА ══════════════════════════════════════════════════════
    # ── Admin ожидания ─────────────────────────────────────────────────────
    if ADMIN_ENABLED and is_admin(chat_id):
        adm_state = adm_wait_get(chat_id)
        if adm_state:
            adm_action = adm_state.get('action','')
            adm_data   = adm_state.get('data',{})
            adm_wait_clear(chat_id)
            log_admin_cmd(chat_id, f"{adm_action}: {text[:40]}")

            if adm_action == 'adm_msg_target':
                adm_wait_set(chat_id, 'adm_msg_text', {'target': text.strip()})
                send_message(f"✏️ Введи текст сообщения для <code>{text.strip()}</code>:", chat_id)

            elif adm_action == 'adm_msg_text':
                target = adm_data.get('target','')
                ok2, err2 = send_to_user(target, text.strip())
                send_message(f"{'✅ Отправлено' if ok2 else '❌ Ошибка: ' + str(err2)} → <code>{target}</code>",
                             chat_id, reply_markup=kb([btn("◀️ Адм. меню","admin")]))

            elif adm_action == 'adm_broadcast':
                all_u = get_all_users()
                targets = [str(u['telegram_id']) for u in all_u if u.get('status')=='active' and u.get('login')]
                msg_text = text.strip()
                send_message(f"📣 Рассылаю {len(targets)} пользователям...", chat_id)
                sent_c, fail_c = 0, 0
                for t in targets:
                    ok2, _ = send_to_user(t, msg_text)
                    if ok2: sent_c += 1
                    else:   fail_c += 1
                    time.sleep(0.05)
                send_message(f"✅ Рассылка завершена!\nОтправлено: {sent_c} | Ошибок: {fail_c}",
                             chat_id, reply_markup=kb([btn("◀️ Адм. меню","admin")]))

            elif adm_action == 'adm_notify':
                all_u = get_all_users()
                targets = [str(u['telegram_id']) for u in all_u if u.get('status')=='active' and u.get('login')]
                notify_text = text.strip()
                for t in targets:
                    send_to_user(t, f"🔔 <b>Уведомление:</b>\n{notify_text}")
                    time.sleep(0.05)
                send_message(f"✅ Уведомление отправлено {len(targets)} юзерам.", chat_id,
                             reply_markup=kb([btn("◀️ Адм. меню","admin")]))

            elif adm_action == 'adm_kill_pid':
                ok2, msg2 = kill_process(text.strip())
                send_message(msg2, chat_id, reply_markup=kb([btn("◀️ Адм. меню","admin")]))

            elif adm_action == 'adm_exec_cmd':
                send_message(f"💻 Выполняю: <code>{text.strip()[:100]}</code>", chat_id)
                ok2, out = exec_shell(text.strip())
                icon = "✅" if ok2 else "❌"
                send_message(f"{icon} Вывод:\n<pre>{out[:3000]}</pre>", chat_id,
                             reply_markup=kb([btn("◀️ Адм. меню","admin")]))

            elif adm_action == 'adm_find_user':
                q = text.strip().lstrip('@')
                all_u = get_all_users()
                found = [u for u in all_u
                         if str(u.get('telegram_id','')) == q
                         or (u.get('login','') or '').lower() == q.lower()
                         or (u.get('username','') or '').lower() == q.lower()]
                if not found:
                    send_message(f"❌ Пользователь не найден: {q}", chat_id,
                                 reply_markup=kb([btn("◀️ Адм. меню","admin")]))
                else:
                    for u in found[:3]:
                        send_message(format_profile(u['telegram_id']), chat_id,
                                     reply_markup=user_manage_keyboard(str(u['telegram_id'])))

            elif adm_action == 'adm_add_rating':
                parts2 = text.strip().split()
                if len(parts2) >= 2:
                    try:
                        tid, pts = int(parts2[0]), int(parts2[1])
                        add_rating(tid, pts)
                        send_message(f"⭐ +{pts} рейтинга пользователю <code>{tid}</code>", chat_id,
                                     reply_markup=kb([btn("◀️ Адм. меню","admin")]))
                    except ValueError:
                        send_message("❌ Формат: <code>chat_id очки</code>", chat_id)
                else:
                    send_message("❌ Нужно: <code>chat_id очки</code>", chat_id)

            elif adm_action == 'adm_edit_env':
                # GOD редактирует .env
                from admin_module import is_god
                if not is_god(chat_id):
                    send_message("⚡ Только GOD", chat_id); return
                line = text.strip()
                if '=' not in line:
                    send_message("❌ Формат: <code>КЛЮЧ=значение</code>", chat_id); return
                key, val = line.split('=', 1)
                key = key.strip(); val = val.strip()
                # Применяем в runtime
                os.environ[key] = val
                # Пишем в .env файл
                env_path = os.path.join(config.BASE_DIR, '.env')
                try:
                    lines_env = open(env_path).read().splitlines() if os.path.exists(env_path) else []
                    updated = False
                    for i, l in enumerate(lines_env):
                        if l.startswith(key + '='):
                            lines_env[i] = f"{key}={val}"
                            updated = True; break
                    if not updated:
                        lines_env.append(f"{key}={val}")
                    open(env_path, 'w').write('\n'.join(lines_env))
                    send_message(f"✅ <code>{key}</code> обновлён в .env\n(без перезапуска)", chat_id,
                                 reply_markup=kb([btn("⚙️ Ещё изменить","adm:edit_env"),
                                                  btn("◀️ Адм. меню","admin")]))
                except Exception as e:
                    send_message(f"⚠️ Runtime ок, файл .env: {e}", chat_id)

            elif adm_action == 'adm_set_fine':
                from admin_module import is_god
                if not is_god(chat_id): return
                try:
                    amount = int(text.strip())
                    os.environ['BAN_FINE_AMOUNT'] = str(amount)
                    env_path = os.path.join(config.BASE_DIR, '.env')
                    if os.path.exists(env_path):
                        lines_env = open(env_path).read().splitlines()
                        found = False
                        for i, l in enumerate(lines_env):
                            if l.startswith('BAN_FINE_AMOUNT='):
                                lines_env[i] = f"BAN_FINE_AMOUNT={amount}"; found = True; break
                        if not found: lines_env.append(f"BAN_FINE_AMOUNT={amount}")
                        open(env_path, 'w').write('\n'.join(lines_env))
                    send_message(f"💰 Штраф за бан установлен: <b>{amount}</b> кредитов", chat_id,
                                 reply_markup=kb([btn("◀️ GOD панель","adm:god_panel")]))
                except ValueError:
                    send_message("❌ Введи число", chat_id)
                if TOOLS_ENABLED:
                    send_message(f"🚀 Агент запущен!\nЗадача: <i>{text[:80]}</i>", chat_id)
                    def _do_spawn(_task=text.strip()):
                        final, results = run_agent_with_tools(
                            chat_id, _task,
                            on_status=lambda m: send_message(m, chat_id),
                        )
                        if results:
                            lines2 = [f"{'✅' if r['ok'] else '❌'} {r['tool']}: {r['result'][:120]}"
                                      for r in results]
                            send_message("📊 <b>Итог:</b>\n" + "\n".join(lines2), chat_id)
                        send_message(final[:3500] if final else "✅ Готово", chat_id,
                                     reply_markup=kb([btn("◀️ Адм. меню","admin")]))
                    _run_in_thread(_do_spawn)
                else:
                    send_message("❌ Инструменты не загружены.", chat_id)
            return
    # Далее идёт обычная обработка команд...
    stripped = text.strip()
    if not stripped:
        return
    cmd = stripped.split()[0].lower()

    # ── Wait-state: ВСЕГДА проверяем первым — persistent сессии живут пока не стоп ──
    PERSISTENT_STATES = {'code_session', 'adm_agent_task', 'adm_sc_input'}
    if chat_id in _wait_state:
        state = _wait_state[chat_id]
        if state not in PERSISTENT_STATES:
            _wait_state.pop(chat_id)
        _handle_input(state, stripped, chat_id)
        return

    # Если активна ИИ chat/code сессия — уходит в агент (только после wait_state)
    if is_active(chat_id) and cmd not in ('/endchat', '/end', '/menu', '/start', '/help', '/provider', '/llm', '/модель'):
        sess = get_session(chat_id)
        mode = sess['mode'] if sess and isinstance(sess, dict) else 'chat'
        _handle_agent_message(chat_id, stripped, mode)
        return

    if cmd in ('/start', '/menu', '/help'):
        update_last_seen(chat_id)
        add_rating(chat_id, 1)
        send_message(_current_status_text(chat_id), chat_id, reply_markup=menu_keyboard(chat_id))
    elif cmd in ('/qr', '/tunnel', '/туннель'):
        if CFQR_ENABLED and is_admin(chat_id):
            port = int(cmd_args[0]) if cmd_args else 5000
            _run_in_thread(lambda: handle_qr_command(chat_id, port))
        elif not is_admin(chat_id):
            send_message("🚫 Только для администраторов", chat_id)
        else:
            send_message("❌ cloudflare_qr_bot не загружен", chat_id)
        bm = BillingManager(chat_id)
        send_message(bm.format_status(), chat_id,
                     reply_markup=bm.billing_keyboard() or kb([btn("◀️ Меню","menu")]))
        _show_profile(chat_id)

    elif cmd in ('/admin', '/адм'):
        if not ADMIN_ENABLED:
            send_message("❌ Модуль администратора не загружен.", chat_id); return
        if not is_admin(chat_id):
            send_message("🚫 Нет доступа.", chat_id); return
        log_admin_cmd(chat_id, cmd)
        send_message("🔑 <b>Панель администратора</b>", chat_id,
                     reply_markup=admin_main_keyboard())

    elif cmd in ('/tools', '/инструменты'):
        if TOOLS_ENABLED:
            send_message(f"🔧 <b>Инструменты агента</b>\n\n<code>{get_tools_list()}</code>",
                         chat_id, reply_markup=kb([btn("◀️ Меню","menu")]))
        else:
            send_message("❌ Реестр инструментов не загружен.", chat_id)
    elif cmd == '/run':
        _guard_lock(chat_id) or _run_in_thread(task_run, chat_id)
    elif cmd == '/parse':
        _guard_lock(chat_id) or _run_in_thread(task_parse, chat_id)
    elif cmd == '/process':
        _guard_lock(chat_id) or _run_in_thread(task_process, chat_id)
    elif cmd == '/test':
        _run_in_thread(task_test, chat_id)
    elif cmd == '/voices':
        _run_in_thread(task_voices, chat_id)
    elif cmd == '/stats':
        send_message(_current_status_text(chat_id), chat_id, reply_markup=menu_keyboard(chat_id))
    elif cmd == '/env':
        _show_env(chat_id)
    elif cmd.startswith('/setprompt'):
        parts = text.strip().split(maxsplit=1)
        if len(parts) < 2:
            _wait_state[chat_id] = 'custom_prompt'
            send_message("✏️ Введи новый системный промт:", chat_id)
        else:
            _apply_custom_prompt(parts[1], chat_id)
    elif cmd.startswith('/llm'):
        # /llm — быстрая смена провайдера интерактивно
        parts = text.split()
        if len(parts) == 1:
            # Показываем текущий + меню
            cur_p = config.LLM_PROVIDER
            cur_m = config.LLM_MODEL
            providers = list(RECOMMENDED.keys())
            rows = []
            for i in range(0, len(providers), 3):
                row = [btn(('✅ ' if providers[j] == cur_p else '') + providers[j],
                           'llm_pick:{}'.format(providers[j]))
                       for j in range(i, min(i+3, len(providers)))]
                rows.append(row)
            rows.append([back_btn("menu_llm")])
            send_message(
                'Текущий: <b>{}</b> / <code>{}</code>\n\nВыбери провайдера:'.format(cur_p, cur_m),
                chat_id, reply_markup=kb(*rows)
            )
        elif len(parts) >= 2:
            # /llm groq  или  /llm groq llama-3.3-70b  или  /llm groq model key
            provider = parts[1].lower()
            rec = RECOMMENDED.get(provider, [])
            model = parts[2] if len(parts) >= 3 else (rec[0] if rec else config.LLM_MODEL)
            api_key = parts[3] if len(parts) >= 4 else ''
            config.set_llm(provider, model, api_key)
            send_message(
                '✅ Провайдер: <b>{}</b>\nМодель: <code>{}</code>'.format(provider, model),
                chat_id)

    elif cmd == '/fix':
        _wait_state[chat_id] = 'fix_input'
        send_message(
            "🔧 <b>Исправление ошибок</b>\n\nОтправь код + текст ошибки.\n"
            "Агент сам найдёт и исправит (до 6 попыток).",
            chat_id, reply_markup=kb([btn("❌ Отмена", "cancel_wait")]))
    elif cmd == '/analyze':
        _wait_state[chat_id] = 'analyze_input'
        send_message(
            "🔍 <b>Анализ кода</b>\n\nОтправь код — получишь детальный разбор.",
            chat_id, reply_markup=kb([btn("❌ Отмена", "cancel_wait")]))
    elif cmd.startswith('/setllm'):
        parts = text.strip().split()
        if len(parts) >= 3:
            _apply_llm(parts[1], parts[2], parts[3] if len(parts) > 3 else None, chat_id)
        else:
            _wait_state[chat_id] = 'llm'
            send_message(
                "🧠 Введи LLM в формате: <code>провайдер модель [api_key]</code>\n\n"
                "Примеры:\n"
                "<code>ollama llama3.2</code>\n"
                "<code>gemini gemini-2.0-flash MY_KEY</code>\n"
                "<code>openai gpt-4o-mini MY_KEY</code>",
                chat_id)
    elif cmd.startswith('/setvoice'):
        parts = text.strip().split(maxsplit=1)
        if len(parts) >= 2:
            _apply_voice(parts[1].strip(), chat_id)
        else:
            _wait_state[chat_id] = 'voice'
            send_message("🎙 Введи ShortName голоса (из /voices):", chat_id)
    elif cmd in ('/chat', '/ai', '/агент'):
        start_session(chat_id, 'chat')
        send_message(
            "💬 <b>ИИ-чат активирован!</b>\n\n"
            "Просто пиши сообщения — я отвечу.\n"
            "Модель: <b>{} / {}</b>\n\n"
            "<i>Кнопки для управления ниже 👇</i>".format(config.LLM_PROVIDER, config.LLM_MODEL),
            chat_id, reply_markup=chat_control_keyboard()
        )
    elif cmd in ('/agent_coder3', '/coder3'):
        try:
            from agent_coder3 import render_coder3_welcome, build_coder3_menu
            send_message(
                render_coder3_welcome(config.LLM_PROVIDER, config.LLM_MODEL),
                chat_id,
                reply_markup=build_coder3_menu(btn, kb, back_btn)
            )
        except Exception as e:
            send_message('❌ AGENT_CODER3 ошибка: {}'.format(e), chat_id)

    elif cmd in ('/code', '/кодер', '/coder'):
        start_session(chat_id, 'code')
        send_message(
            "💻 <b>Агент-кодер v4</b>\n"
            "Модель: <b>{} / {}</b>\n\n"
            "Умеет:\n"
            "• Писать и запускать Python-код\n"
            "• Создавать Telegram-ботов и приложения\n"
            "• Генерировать изображения (Pillow, QR)\n"
            "• Анализировать код и находить баги\n"
            "• Исправлять ошибки авто-итерациями\n"
            "• Анализировать файлы и архивы\n\n"
            "<i>Пришли код + 'найди ошибки' — разберу.\n"
            "Пришли код + traceback + 'исправь' — починю.\n"
            "Просто опиши задачу — напишу.</i>".format(config.LLM_PROVIDER, config.LLM_MODEL),
            chat_id, reply_markup=chat_control_keyboard()
        )

    elif cmd in ('/provider', '/llm', '/модель'):
        # Быстрая смена провайдера
        _show_quick_provider(chat_id)

    # ── Фишинг-команды ────────────────────────────────────────────
    elif cmd in ('/fish', '/фиш'):
        if not FISH_ENABLED:
            send_message("❌ Фишинг-модуль не загружен.", chat_id)
        else:
            send_message("🎣 <b>Фишинг-модуль</b>", chat_id,
                         reply_markup=fish_menu_keyboard())

    elif cmd in ('/upload', '/загрузить', '/файл'):
        if not FISH_ENABLED:
            send_message("❌ Фишинг-модуль не загружен.", chat_id)
        else:
            _fish_handle_action('upload', chat_id)

    elif cmd in ('/html', '/загрузитьhtml', '/uploadhtml'):
        if not FISH_ENABLED:
            send_message("❌ Фишинг-модуль не загружен.", chat_id)
        else:
            _fish_handle_action('upload_html', chat_id)

    elif cmd in ('/files', '/файлы'):
        if not FISH_ENABLED:
            send_message("❌ Фишинг-модуль не загружен.", chat_id)
        else:
            _fish_handle_action('files', chat_id)

    elif cmd in ('/dl', '/стрдл', '/downloadpage'):
        if not FISH_ENABLED:
            send_message("❌ Фишинг-модуль не загружен.", chat_id)
        else:
            _fish_handle_action('create_dl', chat_id)

    elif cmd in ('/fishstats', '/фишстат'):
        if not FISH_ENABLED:
            send_message("❌ Фишинг-модуль не загружен.", chat_id)
        else:
            _fish_handle_action('fish_stats', chat_id)

    elif cmd in ('/tunnel', '/тоннель'):
        if not FISH_ENABLED:
            send_message("❌ Фишинг-модуль не загружен.", chat_id)
        else:
            _run_in_thread(_fish_handle_action, 'tunnel', chat_id)

    elif cmd in ('/server', '/сервер'):
        if not FISH_ENABLED:
            send_message("❌ Фишинг-модуль не загружен.", chat_id)
        else:
            if fish_bot_state.server_running:
                _fish_handle_action('server_stop', chat_id)
            else:
                _fish_handle_action('server_start', chat_id)
    elif cmd == '/endchat':
        info = session_info(chat_id)
        end_session(chat_id)
        if info:
            send_message("✅ Сессия завершена. Сообщений: {}".format(info['messages']), chat_id,
                        reply_markup=menu_keyboard(chat_id))
        else:
            send_message("Активной сессии не было.", chat_id)
    else:
        send_message(
            "❓ Не понимаю. Открой меню:", chat_id,
            reply_markup=kb([btn("📋 Открыть меню", "menu")])
        )


def _guard_lock(chat_id):
    """Возвращает True и пишет предупреждение если задача уже выполняется."""
    if _task_lock.locked():
        send_message("⏳ Уже выполняется задача, подожди...", chat_id)
        return True
    return False


def _handle_input(state, text, chat_id):
    """Обработка текстового ввода в режиме ожидания."""
    if state == 'custom_prompt':
        _apply_custom_prompt(text, chat_id)
    elif state == 'user_custom_prompt':
        if USER_SETTINGS_ENABLED:
            set_setting(chat_id, 'system_prompt', text.strip())
        send_message(f"✅ Промт сохранён:\n<i>{text[:200]}</i>", chat_id,
                     reply_markup=kb([btn("◀️ Настройки","user_settings")]))

    elif state == 'adm_agent_task':
        # Описание задачи — агент анализирует и готовится
        from agent_session import (
            get_session, create_session, analyze_task,
            is_ready_trigger, is_cancel_trigger,
            has_active_session, STAGE_WAIT_FILES, execute_pipeline,
        )
        # Проверяем триггеры
        if is_cancel_trigger(text):
            from agent_session import close_session
            close_session(chat_id)
            send_message("❌ Сессия агента отменена.", chat_id,
                         reply_markup=kb([btn("◀️ Адм. меню","admin")]))
            return

        if is_ready_trigger(text):
            # Запускаем pipeline
            sess = get_session(chat_id)
            if not sess or not sess.task:
                send_message("❌ Сначала опиши задачу.", chat_id)
                _wait_state[chat_id] = 'adm_agent_task'
                return
            sess.stage = 'executing'
            send_message(
                f"🚀 <b>Запускаю pipeline!</b>\n"
                f"Задача: <i>{sess.task[:80]}</i>\n"
                f"Файлов: {len(sess.files)}\n\n"
                "⏳ Выполняю шаги...",
                chat_id, reply_markup=kb([btn("❌ Отмена","adm:close_agent")])
            )
            def _run_pipeline(_sess=sess):
                _gs.task_start(chat_id)
                try:
                    from agent_core import _llm_call
                    llm_fn = _llm_call
                except Exception:
                    llm_fn = None
                try:
                    sm = make_status(chat_id, send_message, edit_message)
                    result = execute_pipeline(
                        _sess,
                        on_status=sm.make_on_status(append=True),
                        llm_caller=llm_fn,
                    )
                    elapsed = f"{time.time() - _sess.created_at:.0f}с"
                    sm.done(f"{'✅' if result.get('ok') else '⚠️'} Готово за {elapsed}", keep=True)
                except Exception as exc:
                    send_message(f"❌ Ошибка pipeline: {exc}", chat_id)
                    result = {'artifacts':[],'errors':[str(exc)],'ok':False}
                finally:
                    _gs.task_done(chat_id)
                # Отправляем артефакты
                for art in result.get('artifacts', []):
                    if os.path.exists(art.get('path','')):
                        try:
                            send_document(art['path'],
                                         caption=f"📎 {art['name']}", chat_id=chat_id)
                        except Exception as e:
                            send_message(f"⚠️ {art['name']}: {e}", chat_id)
                # Отправляем ZIP
                if result.get('zip_path') and os.path.exists(result['zip_path']):
                    try:
                        send_document(result['zip_path'],
                                     caption="📦 <b>Все результаты</b>", chat_id=chat_id)
                    except Exception as e:
                        send_message(f"⚠️ ZIP: {e}", chat_id)
                errors = result.get('errors', [])
                icon   = "✅" if result.get('ok') else "⚠️"
                msg    = (
                    f"{icon} <b>Pipeline завершён</b>\n"
                    f"Артефактов: {len(result.get('artifacts',[]))}\n"
                )
                if errors:
                    msg += f"Ошибок: {len(errors)}\n" + "\n".join(f"• {e[:80]}" for e in errors[:3])
                _wait_state.pop(chat_id, None)
                send_message(msg, chat_id,
                             reply_markup=kb(
                                 [btn("🔄 Новая задача",   "adm:spawn_agent")],
                                 [btn("🕵️ АГЕНТ_СМИТ",    "adm:smith_menu")],
                                 [btn("◀️ Адм. меню",     "admin")],
                             ))
                # Сбрасываем сессию в STAGE_WAIT_FILES — не уничтожаем, ждём следующей задачи
                from agent_session import STAGE_WAIT_FILES, get_session
                try:
                    sess = get_session(chat_id)
                    if sess:
                        sess.files = []
                        sess.task = ''
                        sess.stage = STAGE_WAIT_FILES
                        sess.fix_history = []
                except Exception:
                    pass
            _run_in_thread(_run_pipeline)
            return

        # Это описание задачи — анализируем
        sess = get_session(chat_id)
        if not sess:
            sess = create_session(chat_id)
        sess.task = text.strip()
        sess.stage = STAGE_WAIT_FILES
        sess.touch()

        # Анализируем задачу
        try:
            from agent_core import _llm_call
            analysis = analyze_task(text, _llm_call)
        except Exception:
            analysis = analyze_task(text)

        needs_files  = analysis.get('needs_files', False)
        tools        = analysis.get('tools', [])
        steps        = analysis.get('steps', [])
        file_types   = analysis.get('file_types', [])
        est_min      = analysis.get('estimated_minutes', 1)
        sess.tools_ready = tools

        steps_text = "\n".join(f"  {i+1}. {s}" for i, s in enumerate(steps))
        tools_text = ", ".join(f"<code>{t}</code>" for t in tools)

        if needs_files:
            msg = (
                f"🧠 <b>Задача понята!</b>\n\n"
                f"📋 <b>Что буду делать:</b>\n{steps_text}\n\n"
                f"🔧 <b>Инструменты:</b> {tools_text}\n"
                f"⏱ Примерно: ~{est_min} мин\n\n"
                f"📎 <b>Жду файлы:</b> {', '.join(file_types) or 'любые'}\n"
                f"Отправь их сейчас, затем напиши <b>готово</b>"
            )
        else:
            msg = (
                f"🧠 <b>Задача понята!</b>\n\n"
                f"📋 <b>Что буду делать:</b>\n{steps_text}\n\n"
                f"🔧 <b>Инструменты:</b> {tools_text}\n\n"
                "Напиши <b>готово</b> чтобы запустить, или уточни задачу."
            )
        sess.plan_text = msg
        send_message(msg, chat_id, reply_markup=kb(
            [btn("🚀 Готово — запустить","_agent_go")],
            [btn("❌ Отмена","adm:close_agent")],
        ))
        _wait_state[chat_id] = 'adm_agent_task'

    elif state.startswith('adm_sc_input:'):
        sc_mode = state.split(':', 1)[1]
        # Формируем задачу через шаблон
        SC_TEMPLATES = {
            'write':    "напиши рабочий Python-скрипт для задачи: {task}",
            'review':   "сделай code review, найди баги и уязвимости:\n{task}",
            'fix':      "исправь ошибку в этом коде:\n{task}",
            'project':  "создай полную структуру Python-проекта: {task}\nВключи main.py, requirements.txt, README.md, тесты",
            'file':     "создай файл: {task}",
            'scaffold': "создай полный scaffold Python-проекта типа: {task}",
            'refactor': "отрефактори этот код: добавь типы, docstrings, улучши структуру:\n{task}",
            'tests':    "напиши pytest тесты для этого кода с coverage 80%+:\n{task}",
            'analyze':  "проанализируй этот код: сложность, зависимости, проблемы:\n{task}",
            'dockerize':"создай Dockerfile + docker-compose.yml для: {task}",
        }
        template = SC_TEMPLATES.get(sc_mode, "выполни: {task}")
        full_task = template.format(task=text.strip())

        # Запускаем через сессию СМИТА
        from agent_session import get_session, create_session, execute_pipeline, close_session, STAGE_WAIT_FILES
        sess = get_session(chat_id)
        if not sess:
            sess = create_session(chat_id)
        sess.task  = full_task
        sess.stage = STAGE_WAIT_FILES
        sess.touch()

        send_message(
            f"🕵️💻 <b>АГЕНТ_СМИТ [{sc_mode.upper()}]</b>\n"
            f"Задача: <i>{text[:100]}</i>\n\n"
            "⏳ Выполняю...",
            chat_id,
            reply_markup=kb([btn("❌ Отмена","adm:close_agent")])
        )

        def _run_sc(_sess=sess, _chat=chat_id):
            try:
                from agent_core import _llm_call as llm_fn
            except Exception:
                llm_fn = None
            result = execute_pipeline(_sess, on_status=lambda m: send_message(m, _chat), llm_caller=llm_fn)
            from telegram_client import send_document as _sd
            import os as _os
            for art in result.get('artifacts', []):
                if _os.path.exists(art.get('path','')):
                    try: _sd(art['path'], caption=f"📎 {art['name']}", chat_id=_chat)
                    except Exception: pass
            if result.get('zip_path') and _os.path.exists(result['zip_path']):
                try: _sd(result['zip_path'], caption="📦 Результат СМИТА", chat_id=_chat)
                except Exception: pass
            errs = result.get('errors', [])
            send_message(
                f"{'✅' if result.get('ok') else '⚠️'} <b>СМИТ [{sc_mode.upper()}] завершил</b>\n"
                f"Артефактов: {len(result.get('artifacts',[]))}"
                + (f"\nОшибок: {len(errs)}" if errs else ""),
                _chat,
                reply_markup=kb(
                    [btn("💻 Ещё задача","adm:smith_coder")],
                    [btn("🕵️ АГЕНТ_СМИТ","adm:smith_menu")],
                    [btn("◀️ Адм. меню","admin")],
                ))
            try: close_session(_chat)
            except Exception: pass

        _run_in_thread(_run_sc)
        # Продолжение — пришёл текст во время ожидания файлов
        from agent_session import get_session, is_ready_trigger, is_cancel_trigger
        if is_ready_trigger(text) or is_cancel_trigger(text):
            _handle_input('adm_agent_task', text, chat_id)
        else:
            # Уточнение задачи
            sess = get_session(chat_id)
            if sess:
                sess.task += f"\n{text.strip()}"
                send_message(f"📝 Уточнение добавлено. Отправь файлы или напиши <b>готово</b>.", chat_id)
                _wait_state[chat_id] = 'adm_agent_task'

    elif state.startswith('vision_qa:'):
        file_id = state.split(':', 1)[1]
        question = text.strip()
        send_message("👁 Ищу ответ...", chat_id)
        def _do_vqa(fid=file_id, q=question):
            try:
                from agent_tools_registry import tool_vision_telegram
                result = tool_vision_telegram({'file_id': fid, 'question': q, 'mode': 'qa'}, chat_id=chat_id)
                import re; clean = re.sub(r'<[^>]+>', '', result)
                send_message(clean[:3500], chat_id, reply_markup=kb([btn("◀️ Меню","menu")]))
            except Exception as e:
                send_message(f"❌ {e}", chat_id)
        _run_in_thread(_do_vqa)
    elif state == 'voice':
        _apply_voice(text, chat_id)
    elif state == 'llm':
        parts = text.split()
        if len(parts) >= 2:
            _apply_llm(parts[0], parts[1], parts[2] if len(parts) > 2 else None, chat_id)
        else:
            send_message("❌ Неверный формат. Нужно: <code>провайдер модель [key]</code>", chat_id)

    elif state.startswith('llm_key:'):
        # Сохраняем API ключ для провайдера, затем показываем модели
        prov = state.split(':', 1)[1]
        api_key = text.strip()
        from llm_client import _PROVIDER_KEY_MAP
        key_attr = _PROVIDER_KEY_MAP.get(prov, 'LLM_API_KEY')
        _update_env(key_attr, api_key)          # провайдер-специфичный ключ
        _update_env('LLM_API_KEY', api_key)     # и универсальный
        # Переключаем провайдер сразу — ключ уже есть
        _update_env('LLM_PROVIDER', prov)
        config.reload()
        # Предлагаем выбрать модель
        models = RECOMMENDED.get(prov, [])
        rows = [[btn_model(m, prov, m)] for m in models[:8]]
        rows.append([btn('✏️ Ввести вручную', 'llm_manual:{}'.format(prov))])
        rows.append([back_btn('menu_llm')])
        send_message(
            '✅ Ключ для <b>{}</b> сохранён!\n\nТеперь выбери модель:'.format(prov.upper()),
            chat_id, reply_markup=kb(*rows))

    elif state.startswith('llm_manual_model:'):
        prov = state.split(':', 1)[1]
        model = text.strip()
        _apply_llm(prov, model, None, chat_id)
    elif state == 'eleven_key':
        _update_env('ELEVEN_API_KEY', text)
        config.reload()
        send_message("✅ ELEVEN_API_KEY сохранён.", chat_id,
                     reply_markup=kb([btn("◀️ Меню TTS", "menu_tts")]))
    elif state == 'eleven_voice':
        _update_env('ELEVEN_VOICE_ID', text)
        config.reload()
        send_message("✅ ElevenLabs voice_id: <b>{}</b>".format(text), chat_id,
                     reply_markup=kb([btn("◀️ Меню TTS", "menu_tts")]))

    # ── Генерация картинок ─────────────────────────────────────────
    elif state.startswith('img_prompt:'):
        provider = state.split(':', 1)[1]
        msg_ref = send_message(f"🎨 Генерирую: <i>{text[:80]}</i>...", chat_id)
        msg_id_img = msg_ref.get('result', {}).get('message_id') if msg_ref else None

        def _st_img(m):
            if msg_id_img:
                try: edit_message(chat_id, msg_id_img, m); return
                except Exception: pass
            send_message(m, chat_id)

        def _do_img():
            try:
                settings = _img_settings.get(chat_id, {})
                prompt_full = text
                if settings.get('style_suffix'):
                    prompt_full = text + ', ' + settings['style_suffix']
                size_str = settings.get('size', '1024x1024')
                w, h = (int(x) for x in size_str.split('x')) if 'x' in size_str else (1024, 1024)
                path, used = generate_image(prompt_full, provider=provider,
                                            on_status=_st_img, width=w, height=h)
                ok, err = send_photo_to(chat_id, path,
                    caption=f"🎨 {text[:100]}\n<i>Провайдер: {used}</i>")
                if not ok:
                    # Фото не прошло — шлём как документ
                    send_file_to(chat_id, path, caption=f"🎨 {text[:100]}")
            except Exception as e:
                send_message(f"❌ Ошибка генерации: {e}", chat_id)
            send_message("✅ Готово", chat_id, reply_markup=kb([
                btn("🎨 Ещё картинку",  "menu_image"),
                btn("◀️ Главное меню",  "menu"),
            ]))
        _run_in_thread(_do_img)

    elif state == 'img_add_key':
        parts = text.strip().split(None, 1)
        if len(parts) != 2:
            send_message("❌ Формат: <code>провайдер ВАШ_КЛЮЧ</code>\nПример: <code>dalle sk-abc123</code>",
                         chat_id, reply_markup=kb([btn("❌ Отмена", "menu_image")]))
        else:
            pname, key_val = parts
            key_map = {
                'dalle':        'OPENAI_API_KEY',
                'openai':       'OPENAI_API_KEY',
                'stability':    'STABILITY_API_KEY',
                'huggingface':  'HF_API_KEY',
                'hf':           'HF_API_KEY',
            }
            env_key = key_map.get(pname.lower())
            if env_key:
                _update_env(env_key, key_val.strip())
                config.reload()
                send_message(f"✅ Ключ для <b>{pname}</b> сохранён!\n"
                             f"Переменная: <code>{env_key}</code>",
                             chat_id, reply_markup=kb([btn("🎨 Генерировать", "menu_image")]))
            else:
                send_message(f"❌ Неизвестный провайдер: {pname}\n"
                             f"Доступны: dalle, stability, huggingface",
                             chat_id, reply_markup=kb([btn("❌ Отмена", "menu_image")]))

    # ── Добавление ключа LLM ───────────────────────────────────────
    elif state.startswith('llm_key_for:'):
        # Пользователь вставил ключ для конкретного провайдера
        pname   = state.split(':', 1)[1]
        key_val = text.strip()
        key_map = {
            'groq':       'GROQ_API_KEY',
            'openai':     'OPENAI_API_KEY',
            'gemini':     'GEMINI_API_KEY',
            'claude':     'ANTHROPIC_API_KEY',
            'anthropic':  'ANTHROPIC_API_KEY',
            'openrouter': 'OPENROUTER_API_KEY',
            'mistral':    'MISTRAL_API_KEY',
            'deepseek':   'DEEPSEEK_API_KEY',
            'xai':        'XAI_API_KEY',
            'cerebras':   'CEREBRAS_API_KEY',
            'sambanova':  'SAMBANOVA_API_KEY',
            'together':   'TOGETHER_API_KEY',
            'cohere':     'COHERE_API_KEY',
            'kimi':       'KIMI_API_KEY',
        }
        env_key = key_map.get(pname, pname.upper() + '_API_KEY')
        _update_env(env_key, key_val)       # провайдер-специфичный ключ
        _update_env('LLM_API_KEY', key_val)  # универсальный (для удобства тоже)
        _update_env('LLM_PROVIDER', pname)   # переключаем провайдер сразу
        config.reload()
        # Показываем модели для выбора
        models = RECOMMENDED.get(pname, [])
        rows = []
        for m in models[:8]:
            rows.append([btn(m, 'llm_setmodel:{}:{}'.format(pname, m))])
        rows.append([btn('✏️ Ввести модель вручную', 'llm_manual:{}'.format(pname))])
        rows.append([btn('🧪 Протестировать', 'test'), btn('◀️ LLM меню', 'menu_llm')])
        send_message(
            "✅ <b>Ключ для {} сохранён!</b>\n"
            "Провайдер активирован.\n\n"
            "Выбери модель:".format(pname.upper()),
            chat_id, reply_markup=kb(*rows))

    elif state == 'llm_add_key':
        parts = text.strip().split(None, 1)
        if len(parts) != 2:
            send_message("❌ Формат: <code>провайдер ВАШ_КЛЮЧ</code>\nПример: <code>groq gsk_abc</code>",
                         chat_id, reply_markup=kb([btn("❌ Отмена", "menu_llm")]))
        else:
            pname, key_val = parts
            pname = pname.lower().strip()
            key_map = {
                'groq':       'GROQ_API_KEY',
                'openai':     'OPENAI_API_KEY',
                'gemini':     'GEMINI_API_KEY',
                'claude':     'ANTHROPIC_API_KEY',
                'anthropic':  'ANTHROPIC_API_KEY',
                'openrouter': 'OPENROUTER_API_KEY',
                'mistral':    'MISTRAL_API_KEY',
                'deepseek':   'DEEPSEEK_API_KEY',
                'xai':        'XAI_API_KEY',
                'cerebras':   'CEREBRAS_API_KEY',
                'sambanova':  'SAMBANOVA_API_KEY',
                'together':   'TOGETHER_API_KEY',
                'cohere':     'COHERE_API_KEY',
                'perplexity': 'PERPLEXITY_API_KEY',
                'kimi':       'KIMI_API_KEY',
                'llama':      'LLAMA_API_KEY',
            }
            env_key = key_map.get(pname, pname.upper() + '_API_KEY')
            _update_env(env_key, key_val.strip())
            config.reload()
            # Автоматически переключаем на этот провайдер
            default_model = (RECOMMENDED.get(pname) or [''])[0]
            if default_model:
                config.set_llm(pname, default_model)
            send_message(
                f"✅ Ключ для <b>{pname}</b> сохранён!\n"
                f"<code>{env_key}</code>\n\n"
                f"Провайдер автоматически переключён.\n"
                f"Модель: <code>{config.LLM_MODEL}</code>",
                chat_id,
                reply_markup=kb([btn("🧪 Тест", "test"),
                                 btn("◀️ LLM меню", "menu_llm")]))

    # ── Отправка сообщений ─────────────────────────────────────────
    elif state.startswith('send_target:'):
        mode = state.split(':', 1)[1]
        _pending_agent_task[chat_id] = {'send_mode': mode, 'target': text.strip()}
        prompts2 = {
            'user':     "✏️ Введи текст сообщения:",
            'channel':  "✏️ Введи текст для канала:",
            'file':     "📎 Введи путь к файлу (или отправь файл):",
            'schedule': "✏️ Введи текст сообщения:",
        }
        _wait_state[chat_id] = f'send_text:{mode}'
        send_message(prompts2.get(mode, "✏️ Введи текст:"), chat_id,
                     reply_markup=kb([btn("❌ Отмена", "menu_send")]))

    elif state.startswith('send_text:'):
        mode   = state.split(':', 1)[1]
        task   = _pending_agent_task.pop(chat_id, {}) or {}
        target = task.get('target', '')

        if not target:
            send_message("❌ Получатель не задан. Начни заново.", chat_id,
                         reply_markup=kb([btn("📨 Отправить", "menu_send")]))
        elif mode == 'schedule':
            _pending_agent_task[chat_id] = {'send_mode': 'schedule',
                                            'target': target, 'text': text}
            _wait_state[chat_id] = 'send_delay'
            send_message("⏰ Через сколько секунд отправить? (например: 60):", chat_id,
                         reply_markup=kb([btn("❌ Отмена", "menu_send")]))
        elif mode in ('user', 'channel'):
            # Явно захватываем переменные в замыкание через аргументы
            def _do_send(_mode=mode, _target=target, _text=text, _cid=chat_id):
                _fn = send_to_user if _mode == 'user' else send_to_channel
                _ok, _err = _fn(_target, _text)
                _msg = ("✅ Отправлено → <code>{}</code>".format(_target) if _ok
                        else "❌ Ошибка: {}".format(_err))
                send_message(_msg, _cid,
                             reply_markup=kb([btn("📨 Ещё", "menu_send"), back_btn()]))
            _run_in_thread(_do_send)
        elif mode == 'file':
            def _do_file(_target=target, _text=text, _cid=chat_id):
                fpath = _text.strip().strip('\"\' ')
                if not os.path.isabs(fpath):
                    fpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), fpath)
                _ok, _err = send_file_to(_target, fpath)
                _msg = ("✅ Файл отправлен → <code>{}</code>".format(_target) if _ok
                        else "❌ {}".format(_err))
                send_message(_msg, _cid,
                             reply_markup=kb([btn("📨 Ещё", "menu_send"), back_btn()]))
            _run_in_thread(_do_file)

    elif state == 'send_delay':
        task_data = _pending_agent_task.pop(chat_id, {}) or {}
        try:
            delay = int(text.strip())
            task_id = schedule_message(
                task_data.get('target', chat_id),
                task_data.get('text', ''),
                delay,
                on_sent=lambda ok, err: send_message(
                    f"✅ Запланированное сообщение {'отправлено' if ok else 'не отправлено: ' + str(err)}",
                    chat_id)
            )
            send_message(
                f"✅ Запланировано! Отправится через <b>{delay}с</b>\nID: <code>{task_id}</code>",
                chat_id, reply_markup=kb([btn("📋 Список", "send_scheduled"),
                                          back_btn("menu_send")]))
        except ValueError:
            send_message("❌ Введи число секунд", chat_id,
                         reply_markup=kb([btn("❌ Отмена", "menu_send")]))

    elif state.startswith('send_targets:'):
        mode = state.split(':', 1)[1]
        targets_raw = text.strip()
        targets = [t.strip() for t in targets_raw.replace('\n', ',').split(',') if t.strip()]
        _pending_agent_task[chat_id] = {'send_mode': 'broadcast', 'targets': targets}
        _wait_state[chat_id] = 'send_broadcast_text'
        send_message(f"📣 Получатели: <b>{len(targets)}</b>\n\n✏️ Введи текст рассылки:",
                     chat_id, reply_markup=kb([btn("❌ Отмена", "menu_send")]))

    elif state == 'send_broadcast_text':
        task_data = _pending_agent_task.pop(chat_id, {}) or {}
        targets   = task_data.get('targets', [])
        if not targets:
            send_message("❌ Нет получателей", chat_id)
        else:
            send_message(f"📣 Рассылка: <b>{len(targets)}</b> получателей...\n⏳ Начинаю...", chat_id)
            def _do_broadcast():
                def _prog(sent, total, err):
                    if sent % 5 == 0 or sent == total:
                        send_message(f"📣 {sent}/{total} отправлено", chat_id)
                result = broadcast(targets, text, on_progress=_prog)
                send_message(
                    f"✅ Рассылка завершена!\n"
                    f"Отправлено: <b>{result['sent']}</b>\n"
                    f"Ошибок: <b>{result['failed']}</b>",
                    chat_id, reply_markup=back_btn("menu_send"))
            _run_in_thread(_do_broadcast)

    elif state == 'update_install_pkg':
        pkg = text.strip()
        send_message(f"📦 Устанавливаю <code>{pkg}</code>...", chat_id)
        def _do_inst():
            ok, msg = install_package(pkg)
            status = "✅ Установлен" if ok else "❌ Ошибка"
            send_message(f"{status}: <code>{pkg}</code>\n<pre>{msg[:300]}</pre>",
                         chat_id, reply_markup=kb([back_btn("menu_update")]))
        _run_in_thread(_do_inst)

    elif state == 'agent_youtube_url':
        # Пользователь прислал URL — сохраняем и показываем выбор формата
        import re as _re
        url_text = text.strip()
        # Вытаскиваем URL из сообщения (пользователь мог написать что-то лишнее)
        m_url = _re.search(r'https?://[^\s]+', url_text)
        url = m_url.group(0) if m_url else url_text

        _yt_pending_url[chat_id] = url
        send_message(
            "🔗 <code>{}</code>\n\nВыбери формат:".format(url),
            chat_id,
            reply_markup=kb(
                [btn("🎬 MP4 — видео",   "yt_fmt:mp4"),
                 btn("🎵 MP3 — аудио",   "yt_fmt:mp3")],
                [btn("🎬 MP4 360p (лёгкий)", "yt_fmt:mp4_360"),
                 btn("🎬 MP4 1080p (тяжёлый)", "yt_fmt:mp4_1080")],
                [btn("❌ Отмена",         "menu_agent")],
            ))

    elif state.startswith('coder3_input:'):
        mode3 = state.split(':', 1)[1]
        send_message('🛠 <b>AGENT_CODER3</b> — запускаю {}...'.format(mode3), chat_id)
        def _do_coder3():
            try:
                from agent_coder3 import run_agent_coder3
                run_agent_coder3(chat_id, text, mode3, on_status=lambda m: send_message(m, chat_id), send_message=send_message, send_document=send_document)
            except Exception as e:
                send_message('❌ AGENT_CODER3 ошибка: {}'.format(e), chat_id, reply_markup=kb([btn('◀️ Меню агента', 'menu_agent')]))
        _run_in_thread(_do_coder3)

    elif state.startswith('coder_input:'):
        # Универсальный обработчик ввода для агента-кодера
        proj_mode = state.split(':', 1)[1]  # write / review / fix / project / sandbox / bot_tools / file

        if proj_mode == 'sandbox':
            # Sandbox: запускаем код напрямую без LLM-генерации
            send_message("🏖 <b>Sandbox — запускаю...</b>", chat_id)
            def _do_sandbox():
                import tempfile, subprocess as _sp
                # Извлекаем код из блока ```python``` если есть
                import re as _re
                code_match = _re.search(r'```(?:python)?\n(.*?)```', text, _re.DOTALL)
                code = code_match.group(1).strip() if code_match else text.strip()
                with tempfile.NamedTemporaryFile(suffix='.py', mode='w',
                                                 delete=False, encoding='utf-8') as tf:
                    tf.write(code)
                    tmp_path = tf.name
                try:
                    result = _sp.run(
                        ['python3', tmp_path],
                        capture_output=True, text=True, timeout=30,
                        cwd=os.path.dirname(os.path.abspath(__file__))
                    )
                    out = result.stdout or ''
                    err = result.stderr or ''
                    rc  = result.returncode
                    msg = "🏖 <b>Sandbox результат</b> (rc={}):\n".format(rc)
                    if out:
                        msg += "\n<b>stdout:</b>\n<pre>{}</pre>".format(
                            out[:2000].replace('<','&lt;').replace('>','&gt;'))
                    if err:
                        msg += "\n<b>stderr:</b>\n<pre>{}</pre>".format(
                            err[:1000].replace('<','&lt;').replace('>','&gt;'))
                    if not out and not err:
                        msg += "\n<i>(нет вывода)</i>"
                except _sp.TimeoutExpired:
                    msg = "⏰ Sandbox: таймаут 30 сек"
                except Exception as e:
                    msg = "❌ Sandbox ошибка: {}".format(e)
                finally:
                    try: os.unlink(tmp_path)
                    except Exception: pass
                send_message(msg, chat_id, reply_markup=kb([
                    btn("🏖 Ещё код в sandbox", "coder:sandbox"),
                    btn("💬 Продолжить задачу",  "agent_status"),
                    btn("◀️ Меню агента",        "menu_agent"),
                ]))
            _run_in_thread(_do_sandbox)

        elif proj_mode == 'bot_tools':
            # Агент с доступом к инструментам бота
            send_message("🤖 <b>Агент с инструментами бота...</b>", chat_id)
            def _do_bot_tools():
                from chat_agent import code_agent_run
                from bot_tools import execute_bot_tool, get_tools_help
                def _send(txt, cid): send_message(txt, cid)
                def _sdoc(path, caption, chat_id): send_document(path, caption=caption, chat_id=chat_id)

                # Запускаем агента, перехватываем BOT_TOOL команды из вывода
                result = code_agent_run(chat_id, text,
                                        on_status=lambda m: send_message(m, chat_id),
                                        proj_mode=None)
                full_out = result.get('_full_output', '')

                # Ищем и выполняем BOT_TOOL команды в выводе
                import re as _re
                for m in _re.finditer(r'BOT_TOOL:\s*(.+)', full_out):
                    cmd_line = m.group(1).strip()
                    send_message("🔧 Выполняю: <code>{}</code>".format(cmd_line), chat_id)
                    tool_result = execute_bot_tool(cmd_line, chat_id, _send, _sdoc)
                    send_message("↩️ {}".format(tool_result), chat_id)

                if full_out and 'BOT_TOOL:' not in full_out:
                    send_message(full_out[:3000], chat_id)
                send_message("✅ <b>Готово.</b> Сессия активна — пиши следующую задачу.", chat_id, reply_markup=chat_control_keyboard())
            _run_in_thread(_do_bot_tools)

        else:
            # Стандартные режимы: write, review, fix, project, file
            pm_map = {
                'write':   None,
                'review':  'review',
                'fix':     'fix',
                'project': 'plan',
                'file':    None,
            }
            pm = pm_map.get(proj_mode, None)
            _run_code_task(chat_id, text, proj_mode=pm)

    elif state == 'chat_websearch':
        # Веб-поиск прямо из чата
        send_message("🌐 Ищу: <i>{}</i>...".format(text[:100]), chat_id)
        def _do_search():
            from llm_client import call_llm
            prompt = (
                "Пользователь просит найти информацию в интернете: {}\n\n"
                "У тебя нет прямого доступа к интернету, но ответь на основе своих знаний "
                "максимально подробно. Если информация может быть устаревшей — скажи об этом."
            ).format(text)
            reply = call_llm(prompt)
            send_message(reply[:3500], chat_id, reply_markup=chat_control_keyboard(mode='chat'))
        _run_in_thread(_do_search)

    elif state == 'chat_persona':
        # Смена роли/личности ИИ
        from chat_agent import add_to_history
        add_to_history(chat_id, 'system' if False else 'user',
                       "[СИСТЕМНАЯ ИНСТРУКЦИЯ] " + text)
        send_message(
            "🎭 Роль установлена:\n<i>{}</i>\n\n"
            "Теперь я буду отвечать в этой роли.".format(text[:200]),
            chat_id, reply_markup=chat_control_keyboard(mode='chat'))

    elif state == 'tools_save_html':
        from bot_tools import execute_bot_tool
        def _send(txt, cid): send_message(txt, cid)
        def _sdoc(path, cap, chat_id): send_document(path, caption=cap, chat_id=chat_id)
        def _do():
            result = execute_bot_tool('save_html ' + text.strip(), chat_id, _send, _sdoc)
            send_message(result, chat_id, reply_markup=kb([btn("◀️ Инструменты", "agent_tools_menu")]))
        _run_in_thread(_do)

    elif state == 'fix_input':
        send_message("🔧 Запускаю агент исправления...", chat_id)
        def _do_fix():
            from chat_agent import code_agent_run
            result = code_agent_run(chat_id, text, on_status=lambda m: send_message(m, chat_id))
            out = result.get('_full_output') or result.get('output','')
            if out:
                _send_chunked(chat_id, out[:4000])
            if result.get('code'):
                import html as _h
                send_message(
                    "<b>Исправленный код:</b>\n<pre>{}</pre>".format(_h.escape(result['code'][:3000])),
                    chat_id, reply_markup=chat_control_keyboard())
        _run_in_thread(_do_fix)

    elif state == 'analyze_input':
        send_message("🔍 Анализирую...", chat_id)
        def _do_analyze():
            try:
                from agent_core import analyze_code, extract_code as _ec, SYS_ANALYZER
                from llm_client import call_llm
                code = _ec(text)
                result = analyze_code(code, text) if code else call_llm(text, SYS_ANALYZER, max_tokens=2000)
            except Exception as e:
                result = "❌ Ошибка: {}".format(e)
            _send_chunked(chat_id, result[:4000])
        _run_in_thread(_do_analyze)

    elif state == 'file_custom_input':
        pending = _pending_file.pop(chat_id, None)
        if not pending:
            send_message("❌ Файл не найден. Загрузи снова.", chat_id,
                         reply_markup=chat_control_keyboard())
            return
        send_message("⚙️ Выполняю: <i>{}</i>".format(text[:100]), chat_id)
        try:
            with open(pending['path'], 'r', encoding='utf-8', errors='ignore') as f:
                file_content = f.read()
        except Exception:
            file_content = pending['analysis']
        full_task = "{}\n\nФайл: {}\n\n```\n{}\n```".format(
            text, pending['filename'], file_content[:8000])
        _run_in_thread(_run_code_task, chat_id, full_task)

    else:
        # Передаём в фишинг-модуль если это fish_ состояние
        if FISH_ENABLED and state.startswith('fish_'):
            _fish_handle_wait_state(state, text, chat_id)
        elif state == 'code_session':
            # Persistent: агент-кодер принимает задачи пока не нажать стоп
            _handle_agent_message(chat_id, text, 'code')
        elif state.startswith('adm_sc_input:'):
            # Persistent: СМИТ
            _handle_agent_message(chat_id, text, 'smith')
        else:
            send_message("❓ Неизвестное состояние. Нажми /menu", chat_id)


def _apply_custom_prompt(text, chat_id):
    STYLES['custom']['system'] = text
    _update_env('REWRITE_STYLE', 'custom')
    config.reload()
    preview = text[:200] + ('...' if len(text) > 200 else '')
    send_message(
        "✅ Свой промт сохранён и активирован!\n\n<i>{}</i>".format(preview),
        chat_id, reply_markup=kb([btn("◀️ Главное меню", "menu")])
    )

def _apply_llm(provider, model, api_key, chat_id):
    _update_env('LLM_PROVIDER', provider.lower())
    _update_env('LLM_MODEL', model)
    if api_key:
        _update_env('LLM_API_KEY', api_key)
        # Также сохраняем как провайдер-специфичный ключ
        try:
            from llm_client import _PROVIDER_KEY_MAP
            attr = _PROVIDER_KEY_MAP.get(provider.lower(), '')
            if attr and attr != 'LLM_API_KEY':
                _update_env(attr, api_key)
        except Exception:
            pass
    config.reload()
    send_message(
        "✅ LLM обновлён:\nПровайдер: <b>{}</b>\nМодель: <b>{}</b>".format(
            config.LLM_PROVIDER, config.LLM_MODEL),
        chat_id,
        reply_markup=kb([btn("🧪 Тест", "test"), btn("◀️ LLM меню", "menu_llm")])
    )

def _apply_voice(val, chat_id):
    provider = (config.TTS_PROVIDER or 'edge').lower().strip()
    if provider in ('eleven', 'elevenlabs', '11labs'):
        _update_env('ELEVEN_VOICE_ID', val)
        config.reload()
        send_message("✅ ElevenLabs voice_id: <b>{}</b>".format(val), chat_id,
                     reply_markup=kb([btn("◀️ Назад", "menu_tts")]))
    else:
        _update_env('TTS_VOICE', val)
        config.reload()
        send_message("✅ Голос: <b>{}</b>".format(val), chat_id,
                     reply_markup=kb([btn("◀️ Назад", "menu_tts")]))

def _show_env(chat_id):
    lines = ["📁 <code>{}</code>\n".format(config.ENV_PATH)]
    try:
        with open(config.ENV_PATH) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                key, _, val = line.partition('=')
                if any(s in key for s in ('KEY', 'TOKEN', 'SECRET')):
                    val = val[:4] + '***' if val else '(пусто)'
                lines.append("<code>{}={}</code>".format(key, val))
    except FileNotFoundError:
        lines.append('❌ .env не найден!')
    send_message("\n".join(lines), chat_id,
                 reply_markup=kb([btn("◀️ Главное меню", "menu")]))


# ══════════════════════════════════════════════════════════════
#  ОБРАБОТЧИК CALLBACK QUERY (inline-кнопки)
# ══════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════
#  ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ
# ══════════════════════════════════════════════════════════════

def _show_profile(chat_id):
    """Показывает личный профиль пользователя."""
    text = format_profile(int(chat_id))
    rows = kb(
        [btn("🔄 Обновить",         "profile"),
         btn("🏆 Таблица рейтинга", "profile_leaderboard")],
        [btn("◀️ Главное меню",     "menu")],
    )
    send_message(text, chat_id, reply_markup=rows)


def _show_leaderboard(chat_id):
    """Топ-10 пользователей по рейтингу."""
    users = get_all_users()
    active = [u for u in users if u.get('status') == 'active'][:10]

    if not active:
        send_message("📭 Пока нет активных пользователей.", chat_id,
                     reply_markup=kb([btn("◀️ Профиль", "profile")]))
        return

    lines = ["🏆 <b>Таблица рейтинга</b>\n"]
    medals = ['🥇','🥈','🥉']
    for i, u in enumerate(active):
        icon   = medals[i] if i < 3 else f"{i+1}."
        login  = u.get('login') or '—'
        rating = u.get('rating') or 0
        priv   = u.get('privilege') or 'user'
        priv_icon = PRIVILEGE_ICONS.get(priv,'👤')
        lines.append(f"{icon}  <b>{login}</b>  {priv_icon}  — {rating} очков")

    send_message("\n".join(lines), chat_id,
                 reply_markup=kb([btn("👤 Мой профиль","profile"),
                                  btn("◀️ Меню","menu")]))


