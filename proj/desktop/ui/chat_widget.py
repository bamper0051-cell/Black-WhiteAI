"""
Chat widget — the main conversation UI.
Supports streaming output, Markdown rendering, code blocks with Run buttons.
"""
from __future__ import annotations

import re
import threading
from datetime import datetime
from typing import Callable

from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtGui import QFont, QKeyEvent, QTextCursor
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton,
    QSizePolicy, QTextBrowser, QTextEdit,
    QVBoxLayout, QWidget,
)

from core.config import config
from core.history import history_manager
from core.llm_engine import llm_engine
from core.providers import provider_client
from core.sandbox import extract_code_blocks, run_code


# ── Inference thread ──────────────────────────────────────────────────────────

class InferenceThread(QThread):
    token_received = Signal(str)
    finished = Signal(str)  # full response
    error = Signal(str)

    def __init__(self, messages: list[dict], provider: str, stop_event: threading.Event):
        super().__init__()
        self._messages = messages
        self._provider = provider
        self._stop = stop_event
        self._full = []

    def run(self) -> None:
        try:
            sys_prompt = config.get("system_prompt", "")
            if self._provider == "local":
                user_msg = self._messages[-1]["content"] if self._messages else ""
                history = self._messages[:-1]
                gen = llm_engine.stream(user_msg, system_prompt=sys_prompt, history=history,
                                        stop_event=self._stop)
            else:
                # Prepend system prompt
                all_msgs = []
                if sys_prompt:
                    all_msgs.append({"role": "system", "content": sys_prompt})
                all_msgs.extend(self._messages)
                gen = provider_client.stream(all_msgs, stop_event=self._stop)

            for token in gen:
                if self._stop.is_set():
                    break
                self._full.append(token)
                self.token_received.emit(token)

            self.finished.emit("".join(self._full))
        except Exception as exc:
            self.error.emit(str(exc))


# ── Message bubble renderer ───────────────────────────────────────────────────

def _render_html(text: str, role: str) -> str:
    """Convert markdown-ish text to HTML for QTextBrowser."""
    escaped = (text
               .replace("&", "&amp;")
               .replace("<", "&lt;")
               .replace(">", "&gt;"))

    # Code blocks → pre/code
    def replace_code(m):
        lang = m.group(1) or ""
        code = m.group(2).replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
        return (
            f'<pre style="background:#0d1117;color:#c9d1d9;padding:10px;'
            f'border-radius:8px;font-family:Consolas,monospace;font-size:12px;">'
            f'<code lang="{lang}">{m.group(2)}</code></pre>'
        )

    escaped = re.sub(r"```(\w*)\n?(.*?)```", replace_code, escaped, flags=re.DOTALL)

    # Inline code
    escaped = re.sub(r"`([^`]+)`", r'<code style="background:#1e293b;padding:2px 5px;border-radius:4px;">\1</code>', escaped)

    # Bold
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escaped)

    # Newlines
    escaped = escaped.replace("\n", "<br>")

    if role == "user":
        bg = "#1d4ed8"
        align = "right"
        text_color = "#ffffff"
    elif role == "assistant":
        bg = "#1e293b"
        align = "left"
        text_color = "#e2e8f0"
    else:
        bg = "#334155"
        align = "left"
        text_color = "#94a3b8"

    ts = datetime.now().strftime("%H:%M")

    return (
        f'<div style="margin:6px 0;text-align:{align};">'
        f'<div style="display:inline-block;max-width:78%;background:{bg};color:{text_color};'
        f'padding:10px 14px;border-radius:14px;text-align:left;">'
        f'{escaped}'
        f'<div style="font-size:11px;color:rgba(255,255,255,0.4);margin-top:6px;text-align:right;">{ts}</div>'
        f'</div></div><br>'
    )


# ── Chat widget ───────────────────────────────────────────────────────────────

class ChatWidget(QWidget):
    message_sent = Signal(str)       # user text
    response_ready = Signal(str)     # assistant response

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._conversation_id: str | None = None
        self._messages: list[dict] = []
        self._inference_thread: InferenceThread | None = None
        self._stop_event = threading.Event()
        self._streaming_buffer = []
        self._is_streaming = False

        self._setup_ui()
        self._new_conversation()

    # ── UI setup ──────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Chat display
        self._chat_view = QTextBrowser()
        self._chat_view.setObjectName("chatView")
        self._chat_view.setOpenExternalLinks(True)
        self._chat_view.setReadOnly(True)
        self._chat_view.setHtml(self._welcome_html())
        layout.addWidget(self._chat_view)

        # Input area
        input_frame = QFrame()
        input_frame.setObjectName("inputArea")
        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(16, 10, 16, 10)
        input_layout.setSpacing(8)

        self._input = QTextEdit()
        self._input.setObjectName("inputField")
        self._input.setPlaceholderText("Send a message... (Enter to send, Shift+Enter for newline)")
        self._input.setMaximumHeight(100)
        self._input.setMinimumHeight(44)
        self._input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self._input.installEventFilter(self)
        input_layout.addWidget(self._input)

        btn_layout = QVBoxLayout()
        self._send_btn = QPushButton("Send")
        self._send_btn.setObjectName("sendBtn")
        self._send_btn.clicked.connect(self._on_send)

        self._stop_btn = QPushButton("Stop")
        self._stop_btn.setObjectName("stopBtn")
        self._stop_btn.setVisible(False)
        self._stop_btn.clicked.connect(self._on_stop)

        btn_layout.addWidget(self._send_btn)
        btn_layout.addWidget(self._stop_btn)
        input_layout.addLayout(btn_layout)

        layout.addWidget(input_frame)

    def eventFilter(self, obj, event) -> bool:
        if obj is self._input and isinstance(event, QKeyEvent):
            if event.key() == Qt.Key_Return and not (event.modifiers() & Qt.ShiftModifier):
                self._on_send()
                return True
        return super().eventFilter(obj, event)

    # ── Conversation management ───────────────────────────────────────────────

    def _new_conversation(self) -> None:
        provider = config.get("provider", "local")
        model = config.get("selected_model_path", "") or config.get("selected_api_model", "")
        self._conversation_id = history_manager.new_conversation(provider=provider, model=model)
        self._messages = []

    def load_conversation(self, conversation_id: str) -> None:
        self._conversation_id = conversation_id
        self._messages = history_manager.get_messages(conversation_id)
        self._redraw_history()

    def new_chat(self) -> None:
        self._new_conversation()
        self._chat_view.setHtml(self._welcome_html())

    def _redraw_history(self) -> None:
        html = self._welcome_html()
        for msg in self._messages:
            html += _render_html(msg["content"], msg["role"])
        self._chat_view.setHtml(html)
        self._scroll_bottom()

    # ── Send / receive ────────────────────────────────────────────────────────

    def _on_send(self) -> None:
        text = self._input.toPlainText().strip()
        if not text or self._is_streaming:
            return

        self._input.clear()
        self._append_message(text, "user")
        self._messages.append({"role": "user", "content": text})
        if self._conversation_id:
            history_manager.save_message(self._conversation_id, "user", text)

        self.message_sent.emit(text)
        self._start_inference()

    def _on_stop(self) -> None:
        self._stop_event.set()

    def _start_inference(self) -> None:
        self._stop_event.clear()
        self._is_streaming = True
        self._send_btn.setVisible(False)
        self._stop_btn.setVisible(True)
        self._streaming_buffer = []

        # Placeholder for streaming response
        self._chat_view.append('<div id="streaming" style="margin:6px 0;">'
                               '<div style="display:inline-block;background:#1e293b;'
                               'color:#94a3b8;padding:10px 14px;border-radius:14px;">'
                               '⏳ Thinking...</div></div>')

        provider = config.get("provider", "local")
        self._inference_thread = InferenceThread(self._messages.copy(), provider, self._stop_event)
        self._inference_thread.token_received.connect(self._on_token)
        self._inference_thread.finished.connect(self._on_inference_done)
        self._inference_thread.error.connect(self._on_inference_error)
        self._inference_thread.start()

    def _on_token(self, token: str) -> None:
        self._streaming_buffer.append(token)
        # Update the streaming placeholder every ~10 tokens for performance
        if len(self._streaming_buffer) % 10 == 0:
            self._update_streaming_display()

    def _update_streaming_display(self) -> None:
        text = "".join(self._streaming_buffer)
        # Rebuild the entire chat with streaming content at the end
        html = self._welcome_html()
        for msg in self._messages:
            html += _render_html(msg["content"], msg["role"])
        html += _render_html(text, "assistant")
        self._chat_view.setHtml(html)
        self._scroll_bottom()

    def _on_inference_done(self, full_text: str) -> None:
        self._is_streaming = False
        self._send_btn.setVisible(True)
        self._stop_btn.setVisible(False)

        if full_text:
            self._messages.append({"role": "assistant", "content": full_text})
            if self._conversation_id:
                history_manager.save_message(self._conversation_id, "assistant", full_text)
            self.response_ready.emit(full_text)

        self._redraw_history()

    def _on_inference_error(self, error: str) -> None:
        self._is_streaming = False
        self._send_btn.setVisible(True)
        self._stop_btn.setVisible(False)
        self._append_message(f"❌ Error: {error}", "assistant")

    def _append_message(self, text: str, role: str) -> None:
        self._chat_view.append(_render_html(text, role))
        self._scroll_bottom()

    def _scroll_bottom(self) -> None:
        sb = self._chat_view.verticalScrollBar()
        sb.setValue(sb.maximum())

    # ── Run code from response ────────────────────────────────────────────────

    def run_code_from_response(self, text: str) -> None:
        """Extract and run the first code block in text."""
        blocks = extract_code_blocks(text)
        if not blocks:
            self._append_message("No code block found in the last response.", "assistant")
            return

        lang, code = blocks[0]
        result = run_code(code, lang)
        output_msg = (
            f"```\n$ Run {lang}\n{result.output}\n"
            f"Exit: {result.exit_code}{'  ⏱ Timed out' if result.timed_out else ''}\n```"
        )
        self._append_message(output_msg, "assistant")

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _welcome_html() -> str:
        return (
            '<div style="text-align:center;padding:40px;color:#334155;">'
            '<div style="font-size:48px">🤖</div>'
            '<div style="font-size:22px;font-weight:700;color:#3b82f6;margin-top:10px">BlackBugsAI</div>'
            '<div style="color:#475569;margin-top:6px">Local & Cloud AI — Chat, Code, Create</div>'
            '</div>'
        )

    def clear_chat(self) -> None:
        if self._conversation_id:
            history_manager.clear_messages(self._conversation_id)
        self._messages = []
        self._chat_view.setHtml(self._welcome_html())
