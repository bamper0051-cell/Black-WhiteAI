"""
BlackBugsAI Desktop — Entry point.
"""
from __future__ import annotations

import sys
import os

# Ensure the desktop/ directory is in sys.path so relative imports work
sys.path.insert(0, os.path.dirname(__file__))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from ui.styles import DARK_THEME
from ui.main_window import MainWindow


def main() -> int:
    # High-DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("BlackBugsAI")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("BlackBugsAI")

    app.setStyleSheet(DARK_THEME)

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
