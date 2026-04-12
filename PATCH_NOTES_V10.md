# AGENT_SMITH -- Patch Notes v10 (Admin Web Panel Fix)

## Root causes ("не работает")

### 1. Token не передавался в браузер
`serve_panel()` отдавал статичный HTML через `send_file()`.
Пользователь видел поля URL + Token, но не знал что вводить.
Token по умолчанию `changeme_secret_token` нигде не показывался.

FIX: `serve_panel()` теперь читает HTML, вшивает актуальный токен и URL:
  ```python
  html = html.replace("let T = localStorage.getItem('bb_tok')||'';",
                      f"let T = localStorage.getItem('bb_tok')||'{ADMIN_WEB_TOKEN}';")
  html = html.replace("let B = localStorage.getItem('bb_url')||'http://localhost:8080';",
                      f"let B = localStorage.getItem('bb_url')||'{actual_url}';")
  ```
  Теперь при открытии /panel браузер автоматически подключается.
  Повторные визиты используют сохранённые значения из localStorage.

### 2. `send_file()` не находил admin_panel.html
Flask искал файл только в BASE_DIR, падал с 404 при разных CWD.

FIX: поиск по 3 путям с fallback:
  - `os.path.join(BASE, 'admin_panel.html')`
  - `os.path.join(os.path.dirname(__file__), 'admin_panel.html')`
  - `'admin_panel.html'` (CWD)

### 3. Кнопки Mail / LLM агентов / Роли / .env делали запросы к несуществующим API

FIX: добавлены 8 новых API endpoints в admin_web.py:

| Endpoint                        | Метод | Описание                      |
|---------------------------------|-------|-------------------------------|
| `/api/mail/status`              | GET   | Статус mail_agent             |
| `/api/mail/send`                | POST  | Отправить письмо              |
| `/api/llm/agents`               | GET   | Per-agent LLM список          |
| `/api/llm/agents/<role>`        | POST  | Установить LLM агента         |
| `/api/roles/summary`            | GET   | Роли + лимиты + права         |
| `/api/users/<uid>/role`         | POST  | Установить роль пользователя  |
| `/api/env`                      | GET   | Показать .env (маскируя ключи)|
| `/api/env`                      | POST  | Изменить .env ключ            |

### 4. Дублирующийся `nav()` в admin_panel.html
Предыдущий патч добавил вторую версию nav() что вызывало конфликт роутинга.
FIX: старая nav() удалена, осталась одна расширенная версия.

## Новые вкладки в панели (admin_panel.html)

📧 **Mail** — статус SMTP, форма отправки письма
🧠 **LLM агентов** — таблица per-agent провайдеров, форма изменения
🔑 **Роли** — карточки ролей с лимитами и правами
🔐 **.env (GOD)** — просмотр .env с маскированием секретов, редактор

## Как открыть панель

После запуска бота в консоли появляется:
  `🌐 Admin Panel: http://0.0.0.0:8080/panel`
  `🔑 Token: changeme_...`

Открыть: `http://<IP>:8080/panel`
Панель автоматически подключится (токен вшит в страницу).

Для кастомного токена в .env:
  `ADMIN_WEB_TOKEN=my_secure_token_here`
