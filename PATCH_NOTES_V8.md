# AGENT_SMITH -- Patch Notes v8

## 1. llm_router.py (NEW)

Per-agent LLM selection. Each agent uses its own provider/model from .env:

  SMITH_PROVIDER / SMITH_MODEL    -- AGENT_SMITH
  CODER_PROVIDER / CODER_MODEL    -- chat_agent code tasks
  CODER3_PROVIDER / CODER3_MODEL  -- AGENT_CODER3
  CHAT_PROVIDER  / CHAT_MODEL     -- chat mode
  AGENT_PROVIDER / AGENT_MODEL    -- agent_core (planner/executor)
  FIX_PROVIDER   / FIX_MODEL      -- autofix specialist

Falls back to global LLM_PROVIDER/MODEL if not set.

API:
  call_llm_for("smith", prompt, system)  -- direct call
  get_llm_for("coder")                   -- returns callable
  llm_status()                           -- HTML admin summary
  set_agent_llm("smith", "claude", "claude-3-5-sonnet")  -- set + persist

## 2. mail_agent.py (NEW)

SMTP email sending. Config in .env:
  MAIL_HOST / MAIL_PORT / MAIL_USER / MAIL_PASS / MAIL_FROM
  MAIL_TLS=true (STARTTLS) or MAIL_SSL=true (direct SSL port 465)

API:
  send_mail("to@example.com", "Subject", "Body")
  send_mail(["a@b.com","c@d.com"], "Report", "See attachment",
            attachments=["/tmp/report.pdf"])
  send_admin_notification("Alert!", "Something happened")
  is_configured() -> bool
  mail_status()   -> HTML string for admin panel

Admin email: set ADMIN_EMAIL or GOD_EMAIL in .env

## 3. agent_session.py

AGENT_SMITH now uses llm_router "smith" role when no llm_caller passed.
Falls back to standard call_llm if llm_router unavailable.

## 4. agent_core.py

agent_core._llm_call now uses llm_router "agent" role.
Falls back to standard call_llm if llm_router unavailable.

## 5. admin_module.py

New admin panel sections:
  НАСТРОЙКИ now includes:
  - 📧 Mail  -- mail_status() in chat
  - 🧠 LLM агентов -- llm_status() + per-agent LLM settings
  - 🤖 Провайдеры -- provider health check

## 6. bot_main.py

_help_text() completely rewritten -- comprehensive role-aware help:

  Sections shown per role:
  - 💬 ИИ-ЧАТ (if chat/ai_assistant perm)
  - 💻 АГЕНТ-КОДЕР with /fix /analyze examples
  - 🕵️ АГЕНТЫ (smith/0051) with template examples
  - 🎨 МЕДИА (image/tts/video) with examples
  - 🧠 LLM -- provider list, /llm command
  - 📧 МАЙЛ -- shown if mail is configured
  - 🔑 АДМИН -- /run /parse /env for admins
  - 📋 ВСЕ КОМАНДЫ -- full command list filtered by role
