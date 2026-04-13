# AGENT_SMITH -- Patch Notes v9 (Admin Panel Fix)

## Root causes (what was broken)

1. `admin_main_keyboard()` called without `chat_id` in 2 places
   -> panel rendered without role-awareness (GOD section shown to everyone or hidden)
   FIX: all calls changed to `admin_main_keyboard(chat_id)`

2. 10 new buttons in admin panel had NO handlers in bot.py:
   ban_list, unban_list, set_priv, files, billing_settings,
   mail_status, mail_test, agent_llm, set_agent_llm:, llm_providers,
   edit_env_raw, manage_god
   -> button click silently triggered "❓ Неизвестное adm:" alert
   FIX: all 12 handlers added in the CORRECT location (inside `elif action == 'adm':` block)

3. user_manage_keyboard(target) called without actor_role in 4 places
   -> ADM could see "god" role button meant only for GOD
   FIX: all calls changed to `user_manage_keyboard(target, actor_role=_role)`

4. Input handlers for new admin actions were missing from `_handle_input`:
   - adm_set_priv: parse "ID role" -> set_privilege with can_manage check
   - adm_set_agent_llm: parse "provider model" -> llm_router.set_agent_llm
   - adm_edit_env_raw: parse "KEY=VALUE" -> write to .env (GOD only)
   FIX: all 3 handlers added after adm_kill_pid in _handle_input

## New handlers added

### Callback handlers (inside `elif action == 'adm':`)

`adm:ban_list`
  Shows list of banned users with clickable manage buttons

`adm:unban_list`
  Shows list of banned users with unban buttons

`adm:set_priv`
  Prompts for "ID role" input, then calls set_privilege with can_manage check

`adm:files`
  Shows Python files in BASE_DIR (count + list of .py files)

`adm:billing_settings`
  Shows current fine amount, button to adm:set_fine

`adm:mail_status`
  Shows mail_agent.mail_status(), test button if configured

`adm:mail_test`
  Sends test email to ADMIN_EMAIL, shows result as alert

`adm:agent_llm`
  Shows llm_router.llm_status(), buttons to set per-agent LLM

`adm:set_agent_llm:{role}`
  Prompts for "provider model" input

`adm:llm_providers`
  Lists all available LLM providers from llm_client._OPENAI_COMPAT

`adm:edit_env_raw`  (GOD only)
  Prompts for "KEY=VALUE" input, writes to .env

`adm:manage_god`  (GOD only)
  Shows current ADMIN_IDS, button to edit

### Input handlers (inside `_handle_input`, after adm_kill_pid)

`adm_set_priv`    -- parse "ID role", validate can_manage, call set_privilege
`adm_set_agent_llm` -- parse "provider model", call llm_router.set_agent_llm
`adm_edit_env_raw`  -- parse "KEY=VALUE", GOD check, write .env + os.environ
