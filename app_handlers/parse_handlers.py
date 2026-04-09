from __future__ import annotations

def task_parse(chat_id, *, send_message, parse_all):
    send_message("📡 Парсю новости...", chat_id)
    n = parse_all()
    send_message("✅ Новых новостей: <b>{}</b>".format(n), chat_id)

def task_process(chat_id, *, send_message, run_pipeline):
    send_message("⚙️ Обрабатываю накопленные новости...", chat_id)
    n = run_pipeline()
    send_message("✅ Обработано: <b>{}</b>".format(n), chat_id)

def task_run(chat_id, *, send_message, parse_all, run_pipeline, get_stats):
    send_message("🚀 Полный цикл запущен...", chat_id)
    new = parse_all()
    send_message("📡 Спарсено: <b>{}</b>\n⚙️ Обрабатываю...".format(new), chat_id)
    done = run_pipeline()
    total, sent = get_stats()
    send_message(
        "✅ Цикл завершён!\n"
        "🆕 Новых: {} | ⚙️ Обработано: {}\n"
        "📦 В базе: {} | 📤 Отправлено: {}".format(new, done, total, sent),
        chat_id,
    )

def handle_parse_action(
    *,
    cb_id,
    chat_id,
    answer_callback,
    run_in_thread,
    parse_all,
    send_message,
    menu_keyboard,
):
    answer_callback(cb_id, "📡 Парсинг...")

    def _do_parse():
        try:
            articles = parse_all()
            send_message(
                f"✅ Парсинг завершён\n"
                f"Найдено статей: <b>{len(articles) if articles else 0}</b>",
                chat_id,
                reply_markup=menu_keyboard(chat_id),
            )
        except Exception as e:
            send_message(f"❌ Ошибка парсинга: {e}", chat_id)

    run_in_thread(_do_parse)


def handle_run_action(
    *,
    cb_id,
    chat_id,
    answer_callback,
    run_in_thread,
    scheduled_cycle,
    send_message,
    menu_keyboard,
):
    answer_callback(cb_id, "🚀 Запускаю полный цикл...")

    def _do_run():
        try:
            scheduled_cycle()
            send_message("✅ Цикл завершён", chat_id, reply_markup=menu_keyboard(chat_id))
        except Exception as e:
            send_message(f"❌ Ошибка цикла: {e}", chat_id)

    run_in_thread(_do_run)


def handle_task_command(
    *,
    cmd,
    chat_id,
    guard_lock,
    run_in_thread,
    task_run,
    task_parse,
    task_process,
):
    task_map = {
        '/run': task_run,
        '/parse': task_parse,
        '/process': task_process,
    }
    task_fn = task_map.get(cmd)
    if task_fn is None:
        return False
    guard_lock(chat_id) or run_in_thread(task_fn, chat_id)
    return True
