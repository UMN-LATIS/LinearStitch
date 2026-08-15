"""Preferences dialog — a Qt form bound to :class:`linearstitch.config.Settings`."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..config import Settings


class PreferencesDialog(QDialog):
    """Edit and persist application settings."""

    def __init__(self, settings: Settings, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("Preferences")
        self.setMinimumWidth(620)

        self._build_ui()
        self._load()

    # -- ui ---------------------------------------------------------------

    def _path_row(self, line_edit: QLineEdit, button: QPushButton) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(line_edit, 1)
        layout.addWidget(button)
        return container

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)

        # --- Paths group ---
        paths_group = QGroupBox("Paths")
        paths_form = QFormLayout(paths_group)

        self.browse_path = QLineEdit()
        browse_btn = QPushButton("Browse…")
        browse_btn.clicked.connect(lambda: self._browse_dir(self.browse_path))
        paths_form.addRow("Browse Path", self._path_row(self.browse_path, browse_btn))

        self.archive_path = QLineEdit()
        archive_btn = QPushButton("Browse…")
        archive_btn.clicked.connect(lambda: self._browse_dir(self.archive_path))
        paths_form.addRow("Archive Path", self._path_row(self.archive_path, archive_btn))

        self.core_path = QLineEdit()
        core_btn = QPushButton("Browse…")
        core_btn.clicked.connect(lambda: self._browse_dir(self.core_path))
        paths_form.addRow("Core Output Path", self._path_row(self.core_path, core_btn))

        outer.addWidget(paths_group)

        # --- Processing group ---
        proc_group = QGroupBox("Processing")
        proc_form = QFormLayout(proc_group)

        self.core_count = QSpinBox()
        self.core_count.setRange(2, 32)
        proc_form.addRow("Core Count", self.core_count)

        self.focus_threshold = QDoubleSpinBox()
        self.focus_threshold.setRange(0, 20)
        self.focus_threshold.setSingleStep(1)
        self.focus_threshold.setDecimals(1)
        proc_form.addRow("Focus Threshold", self.focus_threshold)

        self.overlap = QDoubleSpinBox()
        self.overlap.setRange(0, 1)
        self.overlap.setSingleStep(0.05)
        self.overlap.setDecimals(2)
        proc_form.addRow("Overlap", self.overlap)

        self.vignette_magic = QDoubleSpinBox()
        self.vignette_magic.setRange(0, 20)
        self.vignette_magic.setSingleStep(0.1)
        self.vignette_magic.setDecimals(1)
        proc_form.addRow("Vignette Magic", self.vignette_magic)

        self.stacker = QComboBox()
        self.stacker.addItems(["Zerene", "FocusStack"])
        proc_form.addRow("Stacker", self.stacker)

        self.prune_before = QCheckBox("Prune Before Stacking")
        proc_form.addRow("", self.prune_before)

        self.right_to_left = QCheckBox("Right to Left Core")
        proc_form.addRow("", self.right_to_left)

        outer.addWidget(proc_group)

        # --- Zerene group ---
        zerene_group = QGroupBox("Zerene Stacker")
        zerene_form = QFormLayout(zerene_group)

        self.zerene_path = QLineEdit()
        zerene_btn = QPushButton("Browse…")
        zerene_btn.clicked.connect(lambda: self._browse_dir(self.zerene_path))
        zerene_form.addRow("Zerene Path", self._path_row(self.zerene_path, zerene_btn))

        self.zerene_license = QLineEdit()
        zerene_form.addRow("Zerene License", self.zerene_license)
        self.zerene_launch = QLineEdit()
        zerene_form.addRow("Zerene Launch", self.zerene_launch)
        self.zerene_template = QLineEdit()
        zerene_form.addRow("Zerene Template", self.zerene_template)

        outer.addWidget(zerene_group)

        # --- FocusStack group ---
        fs_group = QGroupBox("FocusStack")
        fs_form = QFormLayout(fs_group)

        self.focus_stack = QLineEdit()
        fs_btn = QPushButton("Browse…")
        fs_btn.clicked.connect(lambda: self._browse_file(self.focus_stack))
        fs_form.addRow("Focus Stack Path", self._path_row(self.focus_stack, fs_btn))

        self.focus_launch = QLineEdit()
        fs_form.addRow("Focus Stack Launch", self.focus_launch)

        outer.addWidget(fs_group)

        # --- Buttons ---
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

    # -- browse helpers ---------------------------------------------------

    def _browse_dir(self, target: QLineEdit) -> None:
        start = target.text() or self.settings.values["BrowsePath"]
        path = QFileDialog.getExistingDirectory(self, "Select Folder", start)
        if path:
            target.setText(path)

    def _browse_file(self, target: QLineEdit) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select File", target.text())
        if path:
            target.setText(path)

    # -- binding ----------------------------------------------------------

    def _load(self) -> None:
        v = self.settings.values
        self.browse_path.setText(v["BrowsePath"])
        self.archive_path.setText(v["ArchivePath"])
        self.core_path.setText(v["CoreOutputPath"])
        self.zerene_path.setText(v["ZereneInstall"])
        self.zerene_license.setText(v["ZereneLicense"])
        self.zerene_launch.setText(v["ZereneLaunchPath"])
        self.zerene_template.setText(v["ZereneTemplateFile"])
        self.core_count.setValue(int(v["CoreCount"]))
        self.vignette_magic.setValue(float(v["VignetteMagic"]))
        self.overlap.setValue(float(v["Overlap"]))
        self.focus_threshold.setValue(float(v["FocusThreshold"]))
        self.focus_stack.setText(v["FocusStackInstall"])
        self.focus_launch.setText(v["FocusStackLaunchPath"])
        self.right_to_left.setChecked(bool(v["RightToLeft"]))
        self.prune_before.setChecked(bool(v["PruneBeforeStacking"]))
        idx = self.stacker.findText(v["StackerSelection"])
        if idx >= 0:
            self.stacker.setCurrentIndex(idx)

    def _on_save(self) -> None:
        v = self.settings.values
        v["BrowsePath"] = self.browse_path.text()
        v["ArchivePath"] = self.archive_path.text()
        v["CoreOutputPath"] = self.core_path.text()
        v["ZereneInstall"] = self.zerene_path.text()
        v["ZereneLicense"] = self.zerene_license.text()
        v["ZereneLaunchPath"] = self.zerene_launch.text()
        v["ZereneTemplateFile"] = self.zerene_template.text()
        v["CoreCount"] = str(self.core_count.value())
        v["VignetteMagic"] = str(self.vignette_magic.value())
        v["Overlap"] = str(self.overlap.value())
        v["FocusThreshold"] = str(self.focus_threshold.value())
        v["FocusStackInstall"] = self.focus_stack.text()
        v["FocusStackLaunchPath"] = self.focus_launch.text()
        v["RightToLeft"] = self.right_to_left.isChecked()
        v["PruneBeforeStacking"] = self.prune_before.isChecked()
        v["StackerSelection"] = self.stacker.currentText()
        self.settings.save()
        self.accept()
