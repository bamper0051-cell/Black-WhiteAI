"""
Settings dialog — configure all aspects of the app:
provider, API keys, model params, Telegram, sandbox, API server.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QDoubleSpinBox, QFormLayout, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QScrollArea,
    QSlider, QSpinBox, QTabWidget, QTextEdit,
    QVBoxLayout, QWidget,
)

from core.config import config
from core.providers import PROVIDERS, models_for_provider


class SettingsDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("⚙️ Settings — BlackBugsAI")
        self.setMinimumSize(600, 500)
        self.setModal(True)
        self._setup_ui()
        self._load_values()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(0)

        tabs = QTabWidget()
        layout.addWidget(tabs)

        # ── Provider tab ──────────────────────────────────────────────────────
        tabs.addTab(self._provider_tab(), "🤖 Provider")
        tabs.addTab(self._model_tab(), "🧠 Model Params")
        tabs.addTab(self._system_tab(), "📝 System Prompt")
        tabs.addTab(self._telegram_tab(), "✈️ Telegram")
        tabs.addTab(self._sandbox_tab(), "🐳 Sandbox")
        tabs.addTab(self._api_server_tab(), "🔌 Local API")

        # Buttons
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._save)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _provider_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(12)

        group = QGroupBox("LLM Provider")
        form = QFormLayout(group)

        self._provider_combo = QComboBox()
        for key, label in PROVIDERS.items():
            self._provider_combo.addItem(label, key)
        self._provider_combo.currentIndexChanged.connect(self._on_provider_change)
        form.addRow("Provider:", self._provider_combo)

        self._api_model_combo = QComboBox()
        self._api_model_combo.setEditable(True)
        form.addRow("API Model:", self._api_model_combo)

        lay.addWidget(group)

        # API Keys
        keys_group = QGroupBox("API Keys")
        keys_form = QFormLayout(keys_group)

        self._openai_key = self._make_password("openai_api_key")
        keys_form.addRow("OpenAI Key:", self._openai_key)

        self._anthropic_key = self._make_password("anthropic_api_key")
        keys_form.addRow("Anthropic Key:", self._anthropic_key)

        self._gemini_key = self._make_password("gemini_api_key")
        keys_form.addRow("Gemini Key:", self._gemini_key)

        self._mistral_key = self._make_password("mistral_api_key")
        keys_form.addRow("Mistral Key:", self._mistral_key)

        self._groq_key = self._make_password("groq_api_key")
        keys_form.addRow("Groq Key:", self._groq_key)

        self._ollama_url = QLineEdit()
        keys_form.addRow("Ollama URL:", self._ollama_url)

        self._openai_base = QLineEdit()
        keys_form.addRow("OpenAI Base URL:", self._openai_base)

        lay.addWidget(keys_group)
        lay.addStretch()
        return w

    def _model_tab(self) -> QWidget:
        w = QWidget()
        lay = QFormLayout(w)
        lay.setSpacing(10)

        self._temperature = QDoubleSpinBox()
        self._temperature.setRange(0.0, 2.0)
        self._temperature.setSingleStep(0.05)
        lay.addRow("Temperature:", self._temperature)

        self._top_p = QDoubleSpinBox()
        self._top_p.setRange(0.0, 1.0)
        self._top_p.setSingleStep(0.05)
        lay.addRow("Top P:", self._top_p)

        self._top_k = QSpinBox()
        self._top_k.setRange(1, 200)
        lay.addRow("Top K:", self._top_k)

        self._max_tokens = QSpinBox()
        self._max_tokens.setRange(64, 32768)
        self._max_tokens.setSingleStep(256)
        lay.addRow("Max Tokens:", self._max_tokens)

        self._context_length = QComboBox()
        for ctx in [512, 1024, 2048, 4096, 8192, 16384, 32768]:
            self._context_length.addItem(str(ctx), ctx)
        lay.addRow("Context Length:", self._context_length)

        self._n_gpu_layers = QSpinBox()
        self._n_gpu_layers.setRange(-1, 200)
        lay.addRow("GPU Layers (-1=auto):", self._n_gpu_layers)

        self._n_threads = QSpinBox()
        self._n_threads.setRange(0, 64)
        lay.addRow("CPU Threads (0=auto):", self._n_threads)

        self._repeat_penalty = QDoubleSpinBox()
        self._repeat_penalty.setRange(1.0, 2.0)
        self._repeat_penalty.setSingleStep(0.05)
        lay.addRow("Repeat Penalty:", self._repeat_penalty)

        return w

    def _system_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 12, 12, 12)

        lay.addWidget(QLabel("System Prompt:"))
        self._system_prompt = QTextEdit()
        self._system_prompt.setPlaceholderText("Instructions for the AI...")
        lay.addWidget(self._system_prompt)

        # Quick presets
        presets_layout = QHBoxLayout()
        presets_layout.addWidget(QLabel("Presets:"))
        for name, text in [
            ("Default", "You are BlackBugsAI — a helpful AI assistant. Be concise and clear."),
            ("Coder", "You are an expert software engineer. Write clean, efficient code with explanations."),
            ("Analyst", "You are a data analyst. Provide structured insights and clear visualizations."),
        ]:
            btn = QPushButton(name)
            btn.clicked.connect(lambda checked, t=text: self._system_prompt.setPlainText(t))
            presets_layout.addWidget(btn)
        lay.addLayout(presets_layout)

        return w

    def _telegram_tab(self) -> QWidget:
        w = QWidget()
        lay = QFormLayout(w)
        lay.setSpacing(10)

        self._tg_enabled = QCheckBox("Enable Telegram bridge")
        lay.addRow(self._tg_enabled)

        self._tg_token = self._make_password("telegram_bot_token")
        lay.addRow("Bot Token:", self._tg_token)

        info = QLabel(
            "When enabled, messages sent to the Telegram bot will be\n"
            "processed by the local AI and replied to automatically."
        )
        info.setObjectName("subtitle")
        lay.addRow(info)

        return w

    def _sandbox_tab(self) -> QWidget:
        w = QWidget()
        lay = QFormLayout(w)
        lay.setSpacing(10)

        self._sandbox_enabled = QCheckBox("Enable code sandbox")
        lay.addRow(self._sandbox_enabled)

        self._sandbox_timeout = QSpinBox()
        self._sandbox_timeout.setRange(1, 120)
        self._sandbox_timeout.setSuffix(" seconds")
        lay.addRow("Execution timeout:", self._sandbox_timeout)

        info = QLabel(
            "Code from the editor and extracted from AI responses\n"
            "runs in a restricted subprocess. Dangerous commands are blocked."
        )
        info.setObjectName("subtitle")
        lay.addRow(info)

        return w

    def _api_server_tab(self) -> QWidget:
        w = QWidget()
        lay = QFormLayout(w)
        lay.setSpacing(10)

        self._api_enabled = QCheckBox("Enable local OpenAI-compatible API server")
        lay.addRow(self._api_enabled)

        self._api_port = QSpinBox()
        self._api_port.setRange(1024, 65535)
        lay.addRow("Port:", self._api_port)

        info = QLabel(
            "Exposes POST /v1/chat/completions on localhost.\n"
            "Use as drop-in replacement for OpenAI API in your apps.\n\n"
            "Example: base_url = 'http://localhost:8765/v1'"
        )
        info.setObjectName("subtitle")
        lay.addRow(info)

        return w

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _make_password(self, _key: str) -> QLineEdit:
        le = QLineEdit()
        le.setEchoMode(QLineEdit.Password)
        return le

    def _on_provider_change(self) -> None:
        provider = self._provider_combo.currentData()
        models = models_for_provider(provider)
        self._api_model_combo.clear()
        self._api_model_combo.addItems(models)

        if provider == "ollama":
            from core.providers import ProviderClient
            ollama_models = ProviderClient.get_ollama_models()
            if ollama_models:
                self._api_model_combo.clear()
                self._api_model_combo.addItems(ollama_models)

    def _load_values(self) -> None:
        # Provider
        provider = config.get("provider", "local")
        for i in range(self._provider_combo.count()):
            if self._provider_combo.itemData(i) == provider:
                self._provider_combo.setCurrentIndex(i)
                break
        self._on_provider_change()
        self._api_model_combo.setCurrentText(config.get("selected_api_model", ""))

        # Keys
        self._openai_key.setText(config.get("openai_api_key", ""))
        self._anthropic_key.setText(config.get("anthropic_api_key", ""))
        self._gemini_key.setText(config.get("gemini_api_key", ""))
        self._mistral_key.setText(config.get("mistral_api_key", ""))
        self._groq_key.setText(config.get("groq_api_key", ""))
        self._ollama_url.setText(config.get("ollama_base_url", "http://localhost:11434"))
        self._openai_base.setText(config.get("openai_base_url", "https://api.openai.com/v1"))

        # Model params
        self._temperature.setValue(config.get("temperature", 0.7))
        self._top_p.setValue(config.get("top_p", 0.95))
        self._top_k.setValue(config.get("top_k", 40))
        self._max_tokens.setValue(config.get("max_tokens", 2048))
        self._n_gpu_layers.setValue(config.get("n_gpu_layers", -1))
        self._n_threads.setValue(config.get("n_threads", 0))
        self._repeat_penalty.setValue(config.get("repeat_penalty", 1.1))
        ctx = config.get("context_length", 4096)
        for i in range(self._context_length.count()):
            if self._context_length.itemData(i) == ctx:
                self._context_length.setCurrentIndex(i)
                break

        # System prompt
        self._system_prompt.setPlainText(config.get("system_prompt", ""))

        # Telegram
        self._tg_enabled.setChecked(config.get("telegram_enabled", False))
        self._tg_token.setText(config.get("telegram_bot_token", ""))

        # Sandbox
        self._sandbox_enabled.setChecked(config.get("sandbox_enabled", True))
        self._sandbox_timeout.setValue(config.get("sandbox_timeout", 15))

        # API server
        self._api_enabled.setChecked(config.get("api_server_enabled", False))
        self._api_port.setValue(config.get("api_server_port", 8765))

    def _save(self) -> None:
        config.set("provider", self._provider_combo.currentData())
        config.set("selected_api_model", self._api_model_combo.currentText())
        config.set("openai_api_key", self._openai_key.text())
        config.set("anthropic_api_key", self._anthropic_key.text())
        config.set("gemini_api_key", self._gemini_key.text())
        config.set("mistral_api_key", self._mistral_key.text())
        config.set("groq_api_key", self._groq_key.text())
        config.set("ollama_base_url", self._ollama_url.text())
        config.set("openai_base_url", self._openai_base.text())
        config.set("temperature", self._temperature.value())
        config.set("top_p", self._top_p.value())
        config.set("top_k", self._top_k.value())
        config.set("max_tokens", self._max_tokens.value())
        config.set("n_gpu_layers", self._n_gpu_layers.value())
        config.set("n_threads", self._n_threads.value())
        config.set("repeat_penalty", self._repeat_penalty.value())
        config.set("context_length", self._context_length.currentData())
        config.set("system_prompt", self._system_prompt.toPlainText())
        config.set("telegram_enabled", self._tg_enabled.isChecked())
        config.set("telegram_bot_token", self._tg_token.text())
        config.set("sandbox_enabled", self._sandbox_enabled.isChecked())
        config.set("sandbox_timeout", self._sandbox_timeout.value())
        config.set("api_server_enabled", self._api_enabled.isChecked())
        config.set("api_server_port", self._api_port.value())
        self.accept()
