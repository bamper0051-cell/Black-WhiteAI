"""Dark theme stylesheet for BlackBugsAI desktop."""

DARK_THEME = """
/* ── Global ──────────────────────────────────────────────── */
QWidget {
    background-color: #0f172a;
    color: #e2e8f0;
    font-family: "Segoe UI", "SF Pro Display", sans-serif;
    font-size: 13px;
}

QMainWindow {
    background-color: #0f172a;
}

/* ── Sidebar ─────────────────────────────────────────────── */
#sidebar {
    background-color: #1e293b;
    border-right: 1px solid #334155;
    min-width: 220px;
    max-width: 280px;
}

#sidebar QPushButton {
    background: transparent;
    color: #94a3b8;
    border: none;
    text-align: left;
    padding: 8px 16px;
    border-radius: 8px;
    font-size: 13px;
}

#sidebar QPushButton:hover {
    background-color: #334155;
    color: #e2e8f0;
}

#sidebar QPushButton[active="true"] {
    background-color: #1d4ed8;
    color: white;
}

/* ── Chat View ────────────────────────────────────────────── */
#chatView {
    background-color: #0f172a;
    border: none;
}

/* ── Input Area ───────────────────────────────────────────── */
#inputArea {
    background-color: #1e293b;
    border-top: 1px solid #334155;
}

#inputField {
    background-color: #334155;
    border: 1px solid #475569;
    border-radius: 12px;
    color: #e2e8f0;
    padding: 10px 14px;
    font-size: 14px;
    selection-background-color: #2563eb;
}

#inputField:focus {
    border-color: #3b82f6;
    outline: none;
}

/* ── Buttons ─────────────────────────────────────────────── */
QPushButton#sendBtn {
    background-color: #2563eb;
    color: white;
    border: none;
    border-radius: 10px;
    padding: 10px 20px;
    font-weight: 600;
    font-size: 13px;
    min-width: 80px;
}
QPushButton#sendBtn:hover { background-color: #1d4ed8; }
QPushButton#sendBtn:pressed { background-color: #1e40af; }
QPushButton#sendBtn:disabled { background-color: #475569; }

QPushButton#stopBtn {
    background-color: #dc2626;
    color: white;
    border: none;
    border-radius: 10px;
    padding: 10px 20px;
    font-weight: 600;
}
QPushButton#stopBtn:hover { background-color: #b91c1c; }

QPushButton {
    background-color: #334155;
    color: #e2e8f0;
    border: 1px solid #475569;
    border-radius: 8px;
    padding: 6px 14px;
}
QPushButton:hover { background-color: #475569; }
QPushButton:pressed { background-color: #1d4ed8; }
QPushButton:disabled { color: #64748b; background-color: #1e293b; }

/* ── Toolbar ─────────────────────────────────────────────── */
QToolBar {
    background-color: #1e293b;
    border-bottom: 1px solid #334155;
    spacing: 6px;
    padding: 4px 8px;
}

/* ── Status Bar ───────────────────────────────────────────── */
QStatusBar {
    background-color: #1e293b;
    color: #64748b;
    border-top: 1px solid #334155;
    font-size: 12px;
}

/* ── ComboBox ────────────────────────────────────────────── */
QComboBox {
    background-color: #1e293b;
    border: 1px solid #475569;
    border-radius: 8px;
    color: #e2e8f0;
    padding: 6px 10px;
    min-height: 28px;
}
QComboBox:hover { border-color: #3b82f6; }
QComboBox::drop-down { border: none; padding-right: 8px; }
QComboBox QAbstractItemView {
    background-color: #1e293b;
    border: 1px solid #475569;
    color: #e2e8f0;
    selection-background-color: #1d4ed8;
}

/* ── Labels ──────────────────────────────────────────────── */
QLabel {
    color: #e2e8f0;
}
QLabel#subtitle {
    color: #64748b;
    font-size: 12px;
}

/* ── ScrollBar ────────────────────────────────────────────── */
QScrollBar:vertical {
    background: #1e293b;
    width: 8px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #475569;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover { background: #64748b; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

QScrollBar:horizontal {
    background: #1e293b;
    height: 8px;
    border-radius: 4px;
}
QScrollBar::handle:horizontal {
    background: #475569;
    border-radius: 4px;
    min-width: 30px;
}

/* ── Code editor ─────────────────────────────────────────── */
#codeEditor {
    background-color: #0d1117;
    color: #c9d1d9;
    font-family: "Cascadia Code", "Fira Code", "Consolas", monospace;
    font-size: 13px;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 8px;
}

/* ── Tab widget ──────────────────────────────────────────── */
QTabWidget::pane {
    border: 1px solid #334155;
    border-radius: 8px;
}
QTabBar::tab {
    background-color: #1e293b;
    color: #64748b;
    border: 1px solid transparent;
    padding: 8px 18px;
    border-radius: 6px 6px 0 0;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background-color: #0f172a;
    color: #e2e8f0;
    border-color: #334155;
    border-bottom-color: #0f172a;
}
QTabBar::tab:hover:!selected { background-color: #334155; }

/* ── List widget ─────────────────────────────────────────── */
QListWidget {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    outline: none;
}
QListWidget::item {
    padding: 8px 12px;
    border-radius: 6px;
    color: #cbd5e1;
}
QListWidget::item:selected {
    background-color: #1d4ed8;
    color: white;
}
QListWidget::item:hover:!selected { background-color: #334155; }

/* ── Splitter ────────────────────────────────────────────── */
QSplitter::handle {
    background-color: #334155;
}
QSplitter::handle:horizontal { width: 1px; }
QSplitter::handle:vertical { height: 1px; }

/* ── Dialog ──────────────────────────────────────────────── */
QDialog {
    background-color: #1e293b;
}
QGroupBox {
    border: 1px solid #334155;
    border-radius: 8px;
    margin-top: 12px;
    padding: 12px;
    font-weight: 600;
    color: #94a3b8;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}

/* ── Slider ──────────────────────────────────────────────── */
QSlider::groove:horizontal {
    height: 4px;
    background: #334155;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #3b82f6;
    width: 16px;
    height: 16px;
    margin: -6px 0;
    border-radius: 8px;
}
QSlider::sub-page:horizontal { background: #3b82f6; border-radius: 2px; }

/* ── SpinBox ─────────────────────────────────────────────── */
QSpinBox, QDoubleSpinBox {
    background-color: #1e293b;
    border: 1px solid #475569;
    border-radius: 8px;
    color: #e2e8f0;
    padding: 5px 8px;
}

/* ── LineEdit ────────────────────────────────────────────── */
QLineEdit {
    background-color: #1e293b;
    border: 1px solid #475569;
    border-radius: 8px;
    color: #e2e8f0;
    padding: 6px 10px;
}
QLineEdit:focus { border-color: #3b82f6; }

/* ── TextEdit ────────────────────────────────────────────── */
QTextEdit, QPlainTextEdit {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    color: #e2e8f0;
    padding: 6px;
}

/* ── Checkbox ────────────────────────────────────────────── */
QCheckBox {
    color: #e2e8f0;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #475569;
    border-radius: 4px;
    background: #1e293b;
}
QCheckBox::indicator:checked {
    background-color: #2563eb;
    border-color: #2563eb;
}

/* ── ProgressBar ─────────────────────────────────────────── */
QProgressBar {
    border: 1px solid #334155;
    border-radius: 6px;
    text-align: center;
    color: #e2e8f0;
    background-color: #1e293b;
}
QProgressBar::chunk {
    background-color: #2563eb;
    border-radius: 5px;
}
"""
