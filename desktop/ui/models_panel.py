"""
Models panel — lists local GGUF models and shows load status.
Allows loading, unloading, and opening the models directory.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QProgressBar, QSizePolicy, QVBoxLayout, QWidget
)

from core.config import config
from core.llm_engine import ModelInfo, llm_engine, MODELS_DIR


class LoadThread(QThread):
    progress = Signal(str)
    finished = Signal(bool)

    def __init__(self, model_path: str) -> None:
        super().__init__()
        self._path = model_path

    def run(self) -> None:
        success = llm_engine.load_model(
            self._path,
            on_progress=lambda msg: self.progress.emit(msg),
        )
        self.finished.emit(success)


class ModelsPanel(QWidget):
    model_loaded = Signal(str)  # model name

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._load_thread: LoadThread | None = None
        self._setup_ui()
        self.refresh_models()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        title = QLabel("📦 Local Models (GGUF)")
        title.setStyleSheet("font-weight: 700; font-size: 14px; color: #38bdf8;")
        layout.addWidget(title)

        subtitle = QLabel(f"📁 {MODELS_DIR}")
        subtitle.setObjectName("subtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        # Open folder button
        open_btn = QPushButton("📂 Open Models Folder")
        open_btn.clicked.connect(self._open_models_dir)
        layout.addWidget(open_btn)

        # Models list
        self._model_list = QListWidget()
        self._model_list.itemDoubleClicked.connect(self._load_selected)
        layout.addWidget(self._model_list)

        # Status
        self._status_label = QLabel("No model loaded")
        self._status_label.setObjectName("subtitle")
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)

        # Progress
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 0)  # indeterminate
        self._progress_bar.setVisible(False)
        layout.addWidget(self._progress_bar)

        # Buttons
        btn_layout = QHBoxLayout()
        self._load_btn = QPushButton("⚡ Load Selected")
        self._load_btn.setObjectName("sendBtn")
        self._load_btn.clicked.connect(self._load_selected)
        btn_layout.addWidget(self._load_btn)

        self._unload_btn = QPushButton("Unload")
        self._unload_btn.clicked.connect(self._unload)
        btn_layout.addWidget(self._unload_btn)

        refresh_btn = QPushButton("🔄")
        refresh_btn.setMaximumWidth(40)
        refresh_btn.clicked.connect(self.refresh_models)
        btn_layout.addWidget(refresh_btn)

        layout.addLayout(btn_layout)

        # Currently loaded info
        self._info_frame = QFrame()
        self._info_frame.setStyleSheet("background:#1e293b;border-radius:8px;padding:8px;")
        info_layout = QVBoxLayout(self._info_frame)
        info_layout.setContentsMargins(8, 8, 8, 8)

        self._loaded_label = QLabel("No model loaded")
        self._loaded_label.setStyleSheet("color:#4ade80;font-weight:600;")
        info_layout.addWidget(self._loaded_label)

        layout.addWidget(self._info_frame)
        layout.addStretch()

        self._update_loaded_label()

    def refresh_models(self) -> None:
        self._model_list.clear()
        models = llm_engine.list_models()

        if not models:
            item = QListWidgetItem("(No .gguf models found — drop files into Models Folder)")
            item.setForeground(Qt.gray)
            item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
            self._model_list.addItem(item)
            return

        for model in models:
            label = f"{model.name}  [{model.size_gb} GB]"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, str(model.path))
            self._model_list.addItem(item)

        # Select currently loaded model
        if llm_engine.is_loaded:
            for i in range(self._model_list.count()):
                it = self._model_list.item(i)
                if it and it.data(Qt.UserRole) == llm_engine._model_path:
                    self._model_list.setCurrentRow(i)
                    break

    def _load_selected(self) -> None:
        item = self._model_list.currentItem()
        if not item:
            return
        model_path = item.data(Qt.UserRole)
        if not model_path:
            return

        self._load_btn.setEnabled(False)
        self._progress_bar.setVisible(True)
        self._status_label.setText("Loading model...")

        self._load_thread = LoadThread(model_path)
        self._load_thread.progress.connect(self._on_progress)
        self._load_thread.finished.connect(self._on_load_finished)
        self._load_thread.start()

        config.set("selected_model_path", model_path)

    def _on_progress(self, msg: str) -> None:
        self._status_label.setText(msg)

    def _on_load_finished(self, success: bool) -> None:
        self._load_btn.setEnabled(True)
        self._progress_bar.setVisible(False)

        if success:
            self._update_loaded_label()
            self.model_loaded.emit(llm_engine.model_name)
            self._status_label.setText("✅ Model loaded successfully")
        else:
            error = llm_engine.load_error or "Unknown error"
            self._status_label.setText(f"❌ {error}")

    def _unload(self) -> None:
        llm_engine.unload()
        self._update_loaded_label()
        self._status_label.setText("Model unloaded")

    def _update_loaded_label(self) -> None:
        if llm_engine.is_loaded:
            info = llm_engine.context_info()
            ctx = info.get("n_ctx", "?")
            self._loaded_label.setText(
                f"✅ {llm_engine.model_name}\n"
                f"Context: {ctx} tokens"
            )
        else:
            self._loaded_label.setText("No model loaded")

    @staticmethod
    def _open_models_dir() -> None:
        path = str(MODELS_DIR)
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.run(["open", path])
        else:
            subprocess.run(["xdg-open", path])
