"""
Code editor widget — syntax-highlighted editor with line numbers and a Run button.
Supports Python, JavaScript, Bash output.
"""
from __future__ import annotations

import re

from PySide6.QtCore import Qt, QRect, QSize, Signal
from PySide6.QtGui import (
    QColor, QFont, QPainter, QSyntaxHighlighter, QTextCharFormat, QTextDocument
)
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QPlainTextEdit,
    QPushButton, QTextEdit, QVBoxLayout, QWidget
)

from core.sandbox import run_code


# ── Syntax Highlighter ────────────────────────────────────────────────────────

class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, document: QTextDocument) -> None:
        super().__init__(document)
        self._rules: list[tuple[re.Pattern, QTextCharFormat]] = []

        def fmt(color: str, bold: bool = False, italic: bool = False) -> QTextCharFormat:
            f = QTextCharFormat()
            f.setForeground(QColor(color))
            if bold:
                f.setFontWeight(700)
            if italic:
                f.setFontItalic(True)
            return f

        keywords = [
            "False", "None", "True", "and", "as", "assert", "async", "await",
            "break", "class", "continue", "def", "del", "elif", "else", "except",
            "finally", "for", "from", "global", "if", "import", "in", "is",
            "lambda", "nonlocal", "not", "or", "pass", "raise", "return",
            "try", "while", "with", "yield",
        ]
        for kw in keywords:
            pat = re.compile(r"\b" + kw + r"\b")
            self._rules.append((pat, fmt("#c792ea", bold=True)))

        # Built-ins
        builtins = ["print", "len", "range", "type", "list", "dict", "set",
                    "tuple", "str", "int", "float", "bool", "open", "enumerate",
                    "zip", "map", "filter", "sorted", "sum", "min", "max"]
        for b in builtins:
            self._rules.append((re.compile(r"\b" + b + r"\b"), fmt("#82aaff")))

        # Strings
        self._rules.append((re.compile(r'"[^"\\]*(\\.[^"\\]*)*"'), fmt("#c3e88d")))
        self._rules.append((re.compile(r"'[^'\\]*(\\.[^'\\]*)*'"), fmt("#c3e88d")))

        # Comments
        self._rules.append((re.compile(r"#[^\n]*"), fmt("#546e7a", italic=True)))

        # Decorators
        self._rules.append((re.compile(r"@\w+"), fmt("#ff6e6e")))

        # Numbers
        self._rules.append((re.compile(r"\b\d+\.?\d*\b"), fmt("#f78c6c")))

        # Function names
        self._rules.append((re.compile(r"\bdef\s+(\w+)"), fmt("#82aaff", bold=True)))
        self._rules.append((re.compile(r"\bclass\s+(\w+)"), fmt("#ffcb6b", bold=True)))

    def highlightBlock(self, text: str) -> None:
        for pattern, fmt in self._rules:
            for m in pattern.finditer(text):
                start, end = m.start(), m.end()
                self.setFormat(start, end - start, fmt)


# ── Line number area ──────────────────────────────────────────────────────────

class LineNumberArea(QWidget):
    def __init__(self, editor: "CodeEditorPlain") -> None:
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self) -> QSize:
        return QSize(self._editor._line_number_width(), 0)

    def paintEvent(self, event) -> None:
        self._editor._paint_line_numbers(event)


class CodeEditorPlain(QPlainTextEdit):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("codeEditor")
        font = QFont("Cascadia Code", 13)
        font.setStyleHint(QFont.Monospace)
        self.setFont(font)
        self.setTabStopDistance(28)

        self._line_number_widget = LineNumberArea(self)
        self.blockCountChanged.connect(self._update_line_number_width)
        self.updateRequest.connect(self._update_line_numbers)
        self._update_line_number_width(0)

        self._highlighter = PythonHighlighter(self.document())

    def _line_number_width(self) -> int:
        digits = max(3, len(str(self.blockCount())))
        return 8 + self.fontMetrics().horizontalAdvance("9") * digits

    def _update_line_number_width(self, _) -> None:
        self.setViewportMargins(self._line_number_width(), 0, 0, 0)

    def _update_line_numbers(self, rect, dy) -> None:
        if dy:
            self._line_number_widget.scroll(0, dy)
        else:
            self._line_number_widget.update(0, rect.y(), self._line_number_widget.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_line_number_width(0)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        cr = self.contentsRect()
        self._line_number_widget.setGeometry(
            QRect(cr.left(), cr.top(), self._line_number_width(), cr.height())
        )

    def _paint_line_numbers(self, event) -> None:
        painter = QPainter(self._line_number_widget)
        painter.fillRect(event.rect(), QColor("#0d1117"))
        block = self.firstVisibleBlock()
        block_num = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.setPen(QColor("#3b4048"))
                painter.drawText(
                    0, top, self._line_number_widget.width() - 4,
                    self.fontMetrics().height(),
                    Qt.AlignRight, str(block_num + 1),
                )
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_num += 1


# ── Full code editor tab ──────────────────────────────────────────────────────

class CodeEditorWidget(QWidget):
    code_executed = Signal(str, str)  # code, output

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Toolbar
        toolbar = QHBoxLayout()

        lang_label = QLabel("Language:")
        lang_label.setObjectName("subtitle")
        toolbar.addWidget(lang_label)

        self._lang_combo = QComboBox()
        self._lang_combo.addItems(["python", "javascript", "bash", "shell"])
        self._lang_combo.setMinimumWidth(120)
        toolbar.addWidget(self._lang_combo)

        toolbar.addStretch()

        self._run_btn = QPushButton("▶ Run")
        self._run_btn.setObjectName("sendBtn")
        self._run_btn.setMaximumWidth(80)
        self._run_btn.clicked.connect(self._run_code)
        toolbar.addWidget(self._run_btn)

        self._clear_btn = QPushButton("Clear")
        self._clear_btn.clicked.connect(self._clear)
        toolbar.addWidget(self._clear_btn)

        layout.addLayout(toolbar)

        # Editor
        editor_label = QLabel("Code")
        editor_label.setObjectName("subtitle")
        layout.addWidget(editor_label)

        self._editor = CodeEditorPlain()
        self._editor.setPlaceholderText("# Write or paste code here and press ▶ Run")
        layout.addWidget(self._editor, 3)

        # Output
        output_label = QLabel("Output")
        output_label.setObjectName("subtitle")
        layout.addWidget(output_label)

        self._output = QPlainTextEdit()
        self._output.setReadOnly(True)
        self._output.setObjectName("codeEditor")
        self._output.setPlaceholderText("Output will appear here...")
        self._output.setMaximumHeight(200)
        layout.addWidget(self._output, 1)

    def _run_code(self) -> None:
        code = self._editor.toPlainText()
        if not code.strip():
            return

        lang = self._lang_combo.currentText()
        self._output.setPlainText(f"Running {lang}...\n")
        self._run_btn.setEnabled(False)

        import threading
        def _run():
            result = run_code(code, lang)
            self._output.setPlainText(result.output)
            self._run_btn.setEnabled(True)
            self.code_executed.emit(code, result.output)

        threading.Thread(target=_run, daemon=True).start()

    def _clear(self) -> None:
        self._editor.clear()
        self._output.clear()

    def set_code(self, code: str, language: str = "python") -> None:
        self._editor.setPlainText(code)
        idx = self._lang_combo.findText(language)
        if idx >= 0:
            self._lang_combo.setCurrentIndex(idx)
