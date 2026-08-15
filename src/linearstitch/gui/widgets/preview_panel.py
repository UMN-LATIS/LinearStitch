"""Preview panel: horizontal scroll area showing the latest stitched panorama."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QScrollArea, QSizePolicy

_PREVIEW_HEIGHT = 210


class PreviewPanel(QScrollArea):
    """Scroll area that shows a panorama preview image scaled to a fixed height.

    The image fills vertically (up to ``_PREVIEW_HEIGHT`` px) and can be
    scrolled horizontally — ideal for wide stitched panoramas.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("PreviewScrollArea")
        self.setWidgetResizable(False)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setMinimumHeight(_PREVIEW_HEIGHT + 4)

        self._label = QLabel("No preview yet — results will appear here after stitching.")
        self._label.setObjectName("PreviewLabel")
        self._label.setAlignment(Qt.AlignCenter)
        self._label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self._label.setMinimumWidth(500)
        self._label.setFixedHeight(_PREVIEW_HEIGHT)
        self.setWidget(self._label)

    def show_preview(self, path: str) -> None:
        """Load *path* and display it scaled to the panel height."""
        pixmap = QPixmap(path)
        if pixmap.isNull():
            return
        scaled = pixmap.scaledToHeight(_PREVIEW_HEIGHT, Qt.SmoothTransformation)
        self._label.setPixmap(scaled)
        self._label.setFixedWidth(max(scaled.width(), self.viewport().width()))
        self._label.setToolTip(path)
        # scroll back to the left for each new preview
        self.horizontalScrollBar().setValue(0)
