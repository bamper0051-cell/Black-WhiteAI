ROLES RESTORE PACK

Положи в корень проекта:
- roles.py
- agent_roles.py

Что вернёт:
1) menu_keyboard() и _route_callback() снова смогут брать роли/права
2) import в bot.py:
   from agent_roles import has_perm, get_role, perm_error, check_daily_tasks, ROLE_PERMS
   перестанет падать в fallback
3) проверки из bot.py:
   from roles import has_perm as _hp, perm_denied_msg
   снова будут работать

Откуда берётся роль:
- из auth_module.get_user(chat_id)['privilege']

Какие роли:
- god / adm / vip / user / noob / ban

Важно:
- это возвращает RBAC-слой
- сами данные роли уже должны лежать в users.privilege (auth_module.py у тебя это поле уже использует)
