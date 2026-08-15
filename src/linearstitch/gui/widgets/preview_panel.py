"""Preview panel: horizontal scroll area showing the latest stitched panorama."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QScrollArea, QSizePolicy

_PREFERRED_HEIGHT = 210
_MIN_IMAGE_HEIGHT = 40


class PreviewPanel(QScrollArea):
    """Scroll area that shows a panorama preview image fitted to the panel height.

    The image fills the available height and can be scrolled horizontally — ideal
    for wide stitched panoramas. It rescales as the panel is resized, so the panel
    never imposes a height floor on the window.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("PreviewScrollArea")
        self.setWidgetResizable(False)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._source: QPixmap | None = None

        self._label = QLabel("No preview yet — results will appear here after stitching.")
        self._label.setObjectName("PreviewLabel")
        self._label.setAlignment(Qt.AlignCenter)
        self._label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setWidget(self._label)

    def sizeHint(self) -> QSize:  # noqa: N802
        return QSize(600, _PREFERRED_HEIGHT)

    def show_preview(self, path: str) -> None:
        """Load *path* and display it fitted to the panel height."""
        pixmap = QPixmap(path)
        if pixmap.isNull():
            return
        self._source = pixmap
        self._label.setToolTip(path)
        self._rescale()
        # scroll back to the left for each new preview
        self.horizontalScrollBar().setValue(0)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._rescale()

    def _rescale(self) -> None:
        viewport = self.viewport()
        if self._source is None:
            self._label.resize(viewport.size())
            return
        height = max(viewport.height(), _MIN_IMAGE_HEIGHT)
        scaled = self._source.scaledToHeight(height, Qt.SmoothTransformation)
        self._label.setPixmap(scaled)
        self._label.resize(max(scaled.width(), viewport.width()), scaled.height())
