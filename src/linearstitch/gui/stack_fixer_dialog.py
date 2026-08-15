"""Stack Fixer dialog — a PySide6 port of the original ``StackFixer.py`` GUI."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..core.stackfix import fix_stack


class StackFixerDialog(QDialog):
    """Shift trailing files forward to realign a stack group with missing images."""

    def __init__(self, start_dir: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Stack Fixer")
        self.setMinimumWidth(520)
        self._start_dir = start_dir
        self._build_ui()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        form = QFormLayout()

        self.source_field = QLineEdit()
        self.source_field.setReadOnly(True)
        browse = QPushButton("Select Stack Group…")
        browse.clicked.connect(self._on_browse)
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.addWidget(self.source_field, 1)
        row_layout.addWidget(browse)
        form.addRow("Stack Group", row)

        self.bad_stack = QLineEdit()
        form.addRow("Name of first bad stack", self.bad_stack)

        self.number = QSpinBox()
        self.number.setRange(1, 9999)
        form.addRow("Number of bad files", self.number)

        outer.addLayout(form)

        buttons = QDialogButtonBox()
        fix_btn = buttons.addButton("Fix", QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.addButton(QDialogButtonBox.StandardButton.Close)
        fix_btn.clicked.connect(self._on_fix)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

    def _on_browse(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, "Select Stack Group", self._start_dir
        )
        if path:
            self.source_field.setText(path)

    def _on_fix(self) -> None:
        source = self.source_field.text()
        if not source or not self.bad_stack.text():
            QMessageBox.warning(self, "Stack Fixer", "Select a stack group and bad stack name.")
            return
        fix_stack(source, self.bad_stack.text(), self.number.value())
        QMessageBox.information(self, "Stack Fixer", "Done.")
