"""The main application window."""

from __future__ import annotations

import ctypes.util
import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QCheckBox,
    QDockWidget,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..branding import Brand, current_brand
from ..config import Settings
from ..core.pipeline import ProcessingOptions
from ..ipc.listener import IPCListener
from ..workers.manager import WorkerManager
from .preferences_dialog import PreferencesDialog
from .widgets.file_list import FolderListWidget, choose_directories
from .widgets.preview_panel import PreviewPanel


class MainWindow(QMainWindow):
    """Primary window: folder queue, processing options and live log."""

    def __init__(self, settings: Settings, brand: Brand | None = None) -> None:
        super().__init__()
        self.settings = settings
        self.brand = brand or current_brand()

        self.manager = WorkerManager(settings)
        self.manager.signals.message.connect(self._append_log)
        self.manager.signals.progress.connect(self._on_progress)
        self.manager.signals.status.connect(self._on_status)
        self.manager.signals.preview_ready.connect(self._on_preview_ready)
        self.manager.start()

        self.ipc = IPCListener(self.manager.submit_process)
        self.ipc.start()

        self.scale_path = ""

        self.setWindowTitle(self.brand.window_title)
        self.resize(800, 580)
        self._build_menu()
        self._build_ui()
        self._build_docks()
        self.statusBar().showMessage("Ready")

    # -- ui ---------------------------------------------------------------

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        tools_menu = self.menuBar().addMenu("&Tools")
        fix_action = QAction("Fix Stack…", self)
        fix_action.triggered.connect(self._on_fix_stack)
        tools_menu.addAction(fix_action)

        # View menu populated after docks are created in _build_docks()
        self._view_menu = self.menuBar().addMenu("&View")

    def _build_ui(self) -> None:
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        header = QLabel(self.brand.window_title)
        header.setObjectName("HeaderLabel")
        root.addWidget(header)

        # --- Folder queue ---
        folders_group = QGroupBox("Capture Folders")
        folders_layout = QHBoxLayout(folders_group)

        self.folder_list = FolderListWidget()
        folders_layout.addWidget(self.folder_list, 1)

        folder_buttons = QVBoxLayout()
        add_btn = QPushButton("Add…")
        add_btn.clicked.connect(self._on_add)
        remove_btn = QPushButton("Remove")
        remove_btn.clicked.connect(self.folder_list.remove_selected)
        clear_btn = QPushButton("Clear All")
        clear_btn.clicked.connect(self.folder_list.clear_all)
        folder_buttons.addWidget(add_btn)
        folder_buttons.addWidget(remove_btn)
        folder_buttons.addWidget(clear_btn)
        folder_buttons.addStretch(1)
        folders_layout.addLayout(folder_buttons)

        root.addWidget(folders_group)

        # --- Scale image ---
        scale_group = QGroupBox("Scale Reference")
        scale_layout = QHBoxLayout(scale_group)
        select_scale = QPushButton("Select Scale…")
        select_scale.clicked.connect(self._on_select_scale)
        self.scale_field = QLineEdit()
        self.scale_field.setReadOnly(True)
        self.scale_field.setPlaceholderText("Optional scale image prepended to the panorama")
        scale_layout.addWidget(select_scale)
        scale_layout.addWidget(self.scale_field, 1)
        root.addWidget(scale_group)

        # --- Options (2-column grid saves vertical space) ---
        options_group = QGroupBox("Processing Options")
        options_layout = QGridLayout(options_group)
        options_layout.setHorizontalSpacing(24)
        options_layout.setVerticalSpacing(2)

        self.mask_box = QCheckBox("Mask Images")
        self.vertical_core = QCheckBox("Vertical Core")
        self.remove_vignette = QCheckBox("Remove Vignetting")
        self.rotate_image = QCheckBox("Straighten Image")
        self.crop_image = QCheckBox("Crop Image")
        self.crop_image.setChecked(True)
        self.stack_images = QCheckBox("Stack Images")
        self.stack_images.setChecked(True)
        self.archive_images = QCheckBox("Archive Images")
        self.archive_images.setChecked(True)

        if (
            os.name == "nt"
            and ctypes.util.find_library("libvips-42") is None
            and ctypes.util.find_library("libvips") is None
        ):
            self.rotate_image.hide()

        checkboxes = [
            self.mask_box,       self.vertical_core,
            self.remove_vignette, self.rotate_image,
            self.crop_image,     self.stack_images,
            self.archive_images,
        ]
        for i, box in enumerate(checkboxes):
            options_layout.addWidget(box, i // 2, i % 2)

        root.addWidget(options_group)

        # --- Actions ---
        actions = QHBoxLayout()
        prefs_btn = QPushButton("Preferences")
        prefs_btn.clicked.connect(self._on_prefs)
        scan_btn = QPushButton("Scan for Problems")
        scan_btn.clicked.connect(self._on_scan)
        blurry_btn = QPushButton("Remove Blurry Images")
        blurry_btn.clicked.connect(self._on_remove_blurry)
        start_btn = QPushButton("Start Processing")
        start_btn.setObjectName("PrimaryButton")
        start_btn.clicked.connect(self._on_start)
        actions.addWidget(prefs_btn)
        actions.addWidget(scan_btn)
        actions.addWidget(blurry_btn)
        actions.addStretch(1)
        actions.addWidget(start_btn)
        root.addLayout(actions)

        # --- Progress ---
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setVisible(False)
        root.addWidget(self.progress)

        self.setCentralWidget(central)

    def _build_docks(self) -> None:
        """Create the detachable log and preview dock widgets."""

        # --- Log dock (bottom, floatable) ---
        log_dock = QDockWidget("Processing Log", self)
        log_dock.setObjectName("LogDock")
        log_dock.setAllowedAreas(
            Qt.BottomDockWidgetArea | Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea
        )
        self.log = QTextEdit()
        self.log.setObjectName("LogPanel")
        self.log.setReadOnly(True)
        self.log.setMinimumHeight(100)
        log_dock.setWidget(self.log)
        self.addDockWidget(Qt.BottomDockWidgetArea, log_dock)
        self._log_dock = log_dock

        # --- Preview dock (bottom, tabbed with log, hidden until first result) ---
        preview_dock = QDockWidget("Preview", self)
        preview_dock.setObjectName("PreviewDock")
        preview_dock.setAllowedAreas(Qt.AllDockWidgetAreas)
        self._preview_panel = PreviewPanel()
        preview_dock.setWidget(self._preview_panel)
        self.addDockWidget(Qt.BottomDockWidgetArea, preview_dock)
        self.tabifyDockWidget(log_dock, preview_dock)
        preview_dock.hide()
        self._preview_dock = preview_dock

        # Raise log tab so it's visible by default
        log_dock.raise_()

        # Populate View menu now that docks exist
        self._view_menu.addAction(log_dock.toggleViewAction())
        self._view_menu.addAction(preview_dock.toggleViewAction())

    # -- option collection -----------------------------------------------

    def _current_options(self) -> ProcessingOptions:
        return ProcessingOptions(
            mask=self.mask_box.isChecked(),
            vertical_core=self.vertical_core.isChecked(),
            remove_vignette=self.remove_vignette.isChecked(),
            rotate_image=self.rotate_image.isChecked(),
            crop_image=self.crop_image.isChecked(),
            stack_images=self.stack_images.isChecked(),
            archive_images=self.archive_images.isChecked(),
            scale_path=self.scale_path,
        )

    # -- actions ----------------------------------------------------------

    def _on_add(self) -> None:
        for folder in choose_directories(self, self.settings.values["BrowsePath"]):
            self.folder_list.add_folder(folder)

    def _on_select_scale(self) -> None:
        from PySide6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getOpenFileName(
            self, "Select Scale Image", self.settings.values["BrowsePath"]
        )
        if path:
            self.scale_path = path
            self.scale_field.setText(path)

    def _on_prefs(self) -> None:
        dialog = PreferencesDialog(self.settings, self)
        dialog.exec()

    def _on_fix_stack(self) -> None:
        from .stack_fixer_dialog import StackFixerDialog

        dialog = StackFixerDialog(self.settings.values["BrowsePath"], self)
        dialog.exec()

    def _on_scan(self) -> None:
        self._append_log("Starting Scan")
        self.manager.update_options(self._current_options())
        for folder in self.folder_list.folders():
            self.manager.submit_scan(folder)

    def _on_remove_blurry(self) -> None:
        self._append_log("Starting Blurry Image Removal")
        for folder in self.folder_list.folders():
            self.manager.submit_remove_blurry(folder)

    def _on_start(self) -> None:
        self.progress.setVisible(True)
        self.manager.update_options(self._current_options())
        for folder in self.folder_list.folders():
            self.manager.submit_process(folder)

    # -- signals ----------------------------------------------------------

    def _append_log(self, text: str) -> None:
        self.log.append(text.rstrip("\n"))

    def _on_progress(self, value: int) -> None:
        self.progress.setValue(value)

    def _on_status(self, text: str) -> None:
        self.statusBar().showMessage(text)

    def _on_preview_ready(self, path: str) -> None:
        """Show the preview dock and load the latest panorama thumbnail."""
        self._preview_panel.show_preview(path)
        self._preview_dock.show()
        self._preview_dock.raise_()

    # -- shutdown ---------------------------------------------------------

    def closeEvent(self, event) -> None:  # noqa: N802
        self.ipc.shutdown()
        self.manager.shutdown()
        super().closeEvent(event)
