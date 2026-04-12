"""
Telegram bridge — connects the desktop app to a Telegram bot.
Receives messages from Telegram and sends them to the LLM, then replies.
"""
from __future__ import annotations

import asyncio
import logging
import threading
from typing import Callable

from core.config import config

log = logging.getLogger(__name__)

_tg_available = False
try:
    from telegram import Update
    from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
    _tg_available = True
except ImportError:
    pass


class TelegramBridge:
    """
    Optional Telegram integration.
    When enabled: messages arrive from Telegram → forwarded to on_message_callback
    → response sent back to Telegram.
    """

    def __init__(self) -> None:
        self._app = None
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._running = False
        self.on_message: Callable[[str, int], str] | None = None  # (text, chat_id) -> reply
        self.on_status_change: Callable[[str], None] | None = None

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self, token: str) -> None:
        if not _tg_available:
            if self.on_status_change:
                self.on_status_change("❌ python-telegram-bot not installed")
            return

        if self._running:
            return

        self._thread = threading.Thread(target=self._run_loop, args=(token,), daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._loop and self._app:
            asyncio.run_coroutine_threadsafe(self._app.stop(), self._loop)

    def _run_loop(self, token: str) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._run_bot(token))

    async def _run_bot(self, token: str) -> None:
        try:
            self._app = Application.builder().token(token).build()
            self._app.add_handler(CommandHandler("start", self._cmd_start))
            self._app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message))

            self._running = True
            if self.on_status_change:
                self.on_status_change("🟢 Telegram connected")

            async with self._app:
                await self._app.start()
                await self._app.updater.start_polling()
                while self._running:
                    await asyncio.sleep(1)
                await self._app.updater.stop()
                await self._app.stop()

        except Exception as e:
            self._running = False
            if self.on_status_change:
                self.on_status_change(f"❌ Telegram error: {e}")

    async def _cmd_start(self, update: Update, ctx) -> None:
        await update.message.reply_text(
            "👋 BlackBugsAI desktop connected!\n"
            "Send any message to chat with the AI."
        )

    async def _handle_message(self, update: Update, ctx) -> None:
        text = update.message.text
        chat_id = update.message.chat_id

        await update.message.reply_text("⏳ Processing...")

        if self.on_message:
            try:
                reply = self.on_message(text, chat_id)
                await update.message.reply_text(reply[:4096])
            except Exception as e:
                await update.message.reply_text(f"❌ Error: {e}")

    def send_message(self, chat_id: int, text: str) -> None:
        """Send a message from the app to a Telegram chat."""
        if self._loop and self._app and self._running:
            asyncio.run_coroutine_threadsafe(
                self._app.bot.send_message(chat_id=chat_id, text=text[:4096]),
                self._loop,
            )


telegram_bridge = TelegramBridge()
