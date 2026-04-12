"""
Main application window — sidebar + tabs (Chat, Code, Models).
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path

import psutil
from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QMainWindow, QMessageBox, QPushButton, QSizePolicy,
    QSplitter, QStatusBar, QTabWidget, QToolBar, QVBoxLayout, QWidget,
)

from core.config import config
from core.history import history_manager
from core.llm_engine import llm_engine
from core.telegram_bridge import telegram_bridge
from core.api_server import start_server, stop_server, is_running
from ui.chat_widget import ChatWidget
from ui.code_editor import CodeEditorWidget
from ui.models_panel import ModelsPanel
from ui.settings_dialog import SettingsDialog


class HistoryPanel(QWidget):
    def __init__(self, chat_widget: ChatWidget, parent=None) -> None:
        super().__init__(parent)
        self._chat = chat_widget
        self._setup_ui()

    def _setup_ui(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(6)

        hdr = QHBoxLayout()
        title = QLabel("💬 Conversations")
        title.setStyleSheet("font-weight:700;font-size:13px;color:#38bdf8;")
        hdr.addWidget(title)

        new_btn = QPushButton("+")
        new_btn.setMaximumWidth(28)
        new_btn.setMaximumHeight(28)
        new_btn.setToolTip("New chat")
        new_btn.clicked.connect(self._new_chat)
        hdr.addWidget(new_btn)
        lay.addLayout(hdr)

        self._list = QListWidget()
        self._list.itemClicked.connect(self._on_select)
        lay.addWidget(self._list)

        del_btn = QPushButton("🗑 Delete Selected")
        del_btn.clicked.connect(self._delete_selected)
        lay.addWidget(del_btn)

        self.refresh()

    def refresh(self) -> None:
        self._list.clear()
        for conv in history_manager.list_conversations():
            item = QListWidgetItem(conv["title"][:40])
            item.setData(Qt.UserRole, conv["id"])
            item.setToolTip(f"{conv['provider']} • {conv.get('updated_at', '')}")
            self._list.addItem(item)

    def _on_select(self, item: QListWidgetItem) -> None:
        conv_id = item.data(Qt.UserRole)
        if conv_id:
            self._chat.load_conversation(conv_id)

    def _new_chat(self) -> None:
        self._chat.new_chat()
        self.refresh()

    def _delete_selected(self) -> None:
        item = self._list.currentItem()
        if not item:
            return
        conv_id = item.data(Qt.UserRole)
        if conv_id:
            history_manager.delete_conversation(conv_id)
            self.refresh()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("🤖 BlackBugsAI")
        self.setMinimumSize(1100, 700)
        self.resize(1280, 800)

        self._setup_ui()
        self._setup_menu()
        self._setup_statusbar()
        self._setup_status_timer()
        self._start_optional_services()

    def _setup_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Main splitter: sidebar | content
        splitter = QSplitter(Qt.Horizontal)

        # ── Left sidebar ──────────────────────────────────────────────────────
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(240)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(8, 12, 8, 12)
        side_layout.setSpacing(4)

        # Logo
        logo = QLabel("🤖 BlackBugsAI")
        logo.setStyleSheet("font-weight:800;font-size:16px;color:#38bdf8;padding:8px 8px 12px;")
        side_layout.addWidget(logo)

        # Provider badge
        self._provider_badge = QLabel()
        self._provider_badge.setObjectName("subtitle")
        self._provider_badge.setStyleSheet("color:#64748b;padding:0 8px 8px;font-size:12px;")
        side_layout.addWidget(self._provider_badge)
        self._update_provider_badge()

        # Tabs: Chat history
        self._history_panel = None  # set after chat widget

        side_layout.addStretch()

        # Settings button
        settings_btn = QPushButton("⚙️  Settings")
        settings_btn.clicked.connect(self._open_settings)
        side_layout.addWidget(settings_btn)

        splitter.addWidget(sidebar)

        # ── Right content ─────────────────────────────────────────────────────
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # ── Toolbar ───────────────────────────────────────────────────────────
        toolbar = QToolBar()
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(16, 16))

        self._new_chat_btn = QPushButton("➕ New Chat")
        self._new_chat_btn.setFlat(True)
        toolbar.addWidget(self._new_chat_btn)

        toolbar.addSeparator()

        self._provider_label = QLabel()
        self._provider_label.setStyleSheet("color:#94a3b8;padding:0 8px;")
        toolbar.addWidget(self._provider_label)

        toolbar.addSeparator()

        run_code_btn = QPushButton("▶ Run Code from Response")
        run_code_btn.setFlat(True)
        toolbar.addWidget(run_code_btn)

        toolbar.addSeparator()

        self._tg_status = QLabel("Telegram: off")
        self._tg_status.setStyleSheet("color:#64748b;padding:0 8px;font-size:12px;")
        toolbar.addWidget(self._tg_status)

        right_layout.addWidget(toolbar)

        # ── Main tabs ─────────────────────────────────────────────────────────
        self._tabs = QTabWidget()
        self._tabs.setTabPosition(QTabWidget.North)

        # Chat tab
        self._chat = ChatWidget()
        self._tabs.addTab(self._chat, "💬 Chat")

        # Code editor tab
        self._code_editor = CodeEditorWidget()
        self._tabs.addTab(self._code_editor, "💻 Code")

        # Models tab
        self._models_panel = ModelsPanel()
        self._models_panel.model_loaded.connect(self._on_model_loaded)
        self._tabs.addTab(self._models_panel, "📦 Models")

        right_layout.addWidget(self._tabs)
        splitter.addWidget(right)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        main_layout.addWidget(splitter)

        # History panel in sidebar
        self._history_panel = HistoryPanel(self._chat, sidebar)
        side_layout.insertWidget(2, self._history_panel)
        side_layout.setStretchFactor(self._history_panel, 1)

        # Connections
        self._new_chat_btn.clicked.connect(self._new_chat)
        run_code_btn.clicked.connect(lambda: self._chat.run_code_from_response(
            self._chat._messages[-1]["content"] if self._chat._messages else ""
        ))
        self._chat.message_sent.connect(lambda _: self._history_panel.refresh())
        self._chat.response_ready.connect(self._code_editor.set_code)  # auto-populate code tab

        self._update_provider_label()

    def _setup_menu(self) -> None:
        menu = self.menuBar()

        file_menu = menu.addMenu("File")
        file_menu.addAction("New Chat", self._new_chat, "Ctrl+N")
        file_menu.addSeparator()
        file_menu.addAction("Settings...", self._open_settings, "Ctrl+,")
        file_menu.addSeparator()
        file_menu.addAction("Quit", self.close, "Ctrl+Q")

        model_menu = menu.addMenu("Model")
        model_menu.addAction("Load Model...", lambda: self._tabs.setCurrentIndex(2))
        model_menu.addAction("Unload Model", llm_engine.unload)
        model_menu.addAction("Open Models Folder", ModelsPanel._open_models_dir)

        view_menu = menu.addMenu("View")
        view_menu.addAction("Chat", lambda: self._tabs.setCurrentIndex(0), "Ctrl+1")
        view_menu.addAction("Code Editor", lambda: self._tabs.setCurrentIndex(1), "Ctrl+2")
        view_menu.addAction("Models", lambda: self._tabs.setCurrentIndex(2), "Ctrl+3")

        help_menu = menu.addMenu("Help")
        help_menu.addAction("About", self._show_about)
        help_menu.addAction("API Server Info", self._show_api_info)

    def _setup_statusbar(self) -> None:
        self._statusbar = QStatusBar()
        self.setStatusBar(self._statusbar)
        self._status_model = QLabel("No model")
        self._status_provider = QLabel("local")
        self._status_mem = QLabel("")
        self._statusbar.addWidget(self._status_model)
        self._statusbar.addWidget(QLabel(" | "))
        self._statusbar.addWidget(self._status_provider)
        self._statusbar.addPermanentWidget(self._status_mem)

    def _setup_status_timer(self) -> None:
        timer = QTimer(self)
        timer.timeout.connect(self._refresh_status)
        timer.start(5000)
        self._refresh_status()

    def _refresh_status(self) -> None:
        provider = config.get("provider", "local")
        model_name = llm_engine.model_name if llm_engine.is_loaded else "—"
        self._status_model.setText(f"Model: {model_name}")
        self._status_provider.setText(f"Provider: {provider}")

        mem = psutil.virtual_memory()
        self._status_mem.setText(f"RAM: {mem.percent:.0f}%  |  {mem.used // 1024 ** 3}GB / {mem.total // 1024 ** 3}GB")

    # ── Services ──────────────────────────────────────────────────────────────

    def _start_optional_services(self) -> None:
        # API server
        if config.get("api_server_enabled", False):
            start_server()
            port = config.get("api_server_port", 8765)
            self._statusbar.showMessage(f"✅ API server running on port {port}", 5000)

        # Telegram
        if config.get("telegram_enabled", False):
            token = config.get("telegram_bot_token", "")
            if token:
                telegram_bridge.on_status_change = self._tg_status.setText
                telegram_bridge.on_message = self._handle_telegram_message
                telegram_bridge.start(token)

    def _handle_telegram_message(self, text: str, chat_id: int) -> str:
        """Synchronous Telegram message handler — runs LLM and returns reply."""
        provider = config.get("provider", "local")
        messages = [{"role": "user", "content": text}]

        if provider == "local" and llm_engine.is_loaded:
            tokens = list(llm_engine.stream(text, system_prompt=config.get("system_prompt", "")))
            return "".join(tokens)
        else:
            tokens = list(telegram_bridge.on_message and [] or [])
            from core.providers import provider_client
            return "".join(provider_client.stream(messages))

    # ── Actions ───────────────────────────────────────────────────────────────

    def _new_chat(self) -> None:
        self._chat.new_chat()
        self._history_panel.refresh()
        self._tabs.setCurrentIndex(0)

    def _open_settings(self) -> None:
        dlg = SettingsDialog(self)
        if dlg.exec():
            self._update_provider_badge()
            self._update_provider_label()
            # Restart services if config changed
            if config.get("api_server_enabled") and not is_running():
                start_server()
            elif not config.get("api_server_enabled") and is_running():
                stop_server()

    def _on_model_loaded(self, model_name: str) -> None:
        self._refresh_status()
        self._statusbar.showMessage(f"✅ Model loaded: {model_name}", 4000)

    def _update_provider_badge(self) -> None:
        provider = config.get("provider", "local")
        model = config.get("selected_model_path", "") or config.get("selected_api_model", "")
        short = Path(model).stem if model else provider
        self._provider_badge.setText(f"🔧 {short[:28]}")

    def _update_provider_label(self) -> None:
        provider = config.get("provider", "local")
        icons = {
            "local": "💻", "openai": "🟢", "anthropic": "🔵",
            "gemini": "🌈", "mistral": "🌊", "groq": "⚡", "ollama": "🦙",
        }
        self._provider_label.setText(f"{icons.get(provider, '🤖')} {provider}")

    def _show_about(self) -> None:
        QMessageBox.about(
            self, "About BlackBugsAI",
            "<b>BlackBugsAI Desktop</b> v1.0.0<br><br>"
            "Local &amp; Cloud LLM client<br>"
            "Supports GGUF models via llama.cpp<br>"
            "OpenAI, Anthropic, Gemini, Mistral, Groq, Ollama<br><br>"
            "© 2026 BlackBugsAI",
        )

    def _show_api_info(self) -> None:
        port = config.get("api_server_port", 8765)
        status = "🟢 Running" if is_running() else "🔴 Stopped"
        QMessageBox.information(
            self, "Local API Server",
            f"Status: {status}\n\n"
            f"Endpoint: http://localhost:{port}/v1\n\n"
            f"Use as OpenAI-compatible API:\n"
            f"client = OpenAI(base_url='http://localhost:{port}/v1', api_key='local')",
        )

    def closeEvent(self, event) -> None:
        telegram_bridge.stop()
        stop_server()
        super().closeEvent(event)
