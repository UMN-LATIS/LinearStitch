"""Application bootstrap: a single PySide6 ``QApplication``."""

from __future__ import annotations

import sys
from importlib import resources

from PySide6.QtWidgets import QApplication

from .branding import current_brand
from .config import Settings
from .gui.main_window import MainWindow


def _load_stylesheet() -> str:
    try:
        return (
            resources.files("linearstitch.gui.resources")
            .joinpath("app.qss")
            .read_text(encoding="utf-8")
        )
    except (FileNotFoundError, ModuleNotFoundError):
        return ""


def run() -> int:
    """Create the application, show the main window and run the event loop."""

    brand = current_brand()

    app = QApplication(sys.argv)
    app.setApplicationName(brand.name)
    app.setApplicationDisplayName(brand.window_title)
    app.setStyleSheet(_load_stylesheet())

    settings = Settings()
    window = MainWindow(settings, brand)
    window.show()

    return app.exec()
