"""The main application window."""

from __future__ import annotations

import ctypes.util
import os

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QAction, QGuiApplication
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QToolBar,
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


def _card(title: str) -> tuple[QWidget, QVBoxLayout]:
    """A titled panel: a small caption above a rounded content card.

    Returns the wrapper to add to a layout and the card's content layout.
    """
    wrapper = QWidget()
    outer = QVBoxLayout(wrapper)
    outer.setContentsMargins(0, 0, 0, 0)
    outer.setSpacing(5)

    caption = QLabel(title.upper())
    caption.setObjectName("SectionLabel")
    outer.addWidget(caption)

    card = QFrame()
    card.setObjectName("Card")
    content = QVBoxLayout(card)
    content.setContentsMargins(12, 12, 12, 12)
    outer.addWidget(card, 1)

    return wrapper, content


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
        self._qsettings = QSettings()
        self._build_menu()
        self._build_ui()
        self.statusBar().showMessage("Ready")
        self._restore_state()

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
        controls = QWidget()
        root = QVBoxLayout(controls)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        # --- Folder queue (with the scale reference folded in) ---
        folders_card, folders_group_layout = _card("Capture Folders")
        folders_group_layout.setSpacing(6)

        folders_layout = QHBoxLayout()
        self.folder_list = FolderListWidget()
        self.folder_list.setMinimumHeight(70)
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
        folders_group_layout.addLayout(folders_layout, 1)

        scale_layout = QHBoxLayout()
        select_scale = QPushButton("Select Scale…")
        select_scale.clicked.connect(self._on_select_scale)
        self.scale_field = QLineEdit()
        self.scale_field.setReadOnly(True)
        self.scale_field.setPlaceholderText("Optional scale image prepended to the panorama")
        scale_layout.addWidget(select_scale)
        scale_layout.addWidget(self.scale_field, 1)
        folders_group_layout.addLayout(scale_layout)

        root.addWidget(folders_card, 1)

        # --- Options (4-column grid saves vertical space) ---
        options_card, options_box = _card("Processing Options")
        options_layout = QGridLayout()
        options_layout.setHorizontalSpacing(24)
        options_layout.setVerticalSpacing(2)
        options_box.addLayout(options_layout)

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

        vips_missing = (
            os.name == "nt"
            and ctypes.util.find_library("libvips-42") is None
            and ctypes.util.find_library("libvips") is None
        )

        checkboxes = [
            self.mask_box,
            self.vertical_core,
            self.remove_vignette,
            self.rotate_image,
            self.crop_image,
            self.stack_images,
            self.archive_images,
        ]
        if vips_missing:
            self.rotate_image.hide()
            checkboxes.remove(self.rotate_image)
        self._option_boxes = {
            "mask": self.mask_box,
            "verticalCore": self.vertical_core,
            "removeVignette": self.remove_vignette,
            "rotate": self.rotate_image,
            "crop": self.crop_image,
            "stack": self.stack_images,
            "archive": self.archive_images,
        }
        columns = 4
        for i, box in enumerate(checkboxes):
            options_layout.addWidget(box, i // columns, i % columns)

        root.addWidget(options_card)

        # --- Progress ---
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setVisible(False)
        root.addWidget(self.progress)

        self._build_toolbar()

        # --- Results pane: controls above, log/preview below, freely collapsible ---
        controls_scroll = QScrollArea()
        controls_scroll.setObjectName("ControlsScrollArea")
        controls_scroll.setWidgetResizable(True)
        controls_scroll.setFrameShape(QScrollArea.NoFrame)
        controls_scroll.setWidget(controls)

        self.log = QTextEdit()
        self.log.setObjectName("LogPanel")
        self.log.setReadOnly(True)
        self.log.setMinimumHeight(60)

        self._preview_panel = PreviewPanel()

        self._results_tabs = QTabWidget()
        self._results_tabs.setObjectName("ResultsTabs")
        self._results_tabs.addTab(self.log, "Log")
        self._results_tabs.addTab(self._preview_panel, "Preview")
        self._results_tabs.setMinimumHeight(0)

        splitter = QSplitter(Qt.Vertical)
        splitter.setObjectName("MainSplitter")
        splitter.setChildrenCollapsible(True)
        splitter.addWidget(controls_scroll)
        splitter.addWidget(self._results_tabs)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([420, 200])
        splitter.splitterMoved.connect(self._sync_results_action)
        self._splitter = splitter

        self.setCentralWidget(splitter)

        self._results_action = QAction("Show Results Pane", self)
        self._results_action.setCheckable(True)
        self._results_action.setChecked(True)
        self._results_action.toggled.connect(self._toggle_results_pane)
        self._view_menu.addAction(self._results_action)

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Actions", self)
        toolbar.setObjectName("ActionToolBar")
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        # QSS padding/spacing is ignored on QToolBar, so set them on its layout.
        toolbar.layout().setContentsMargins(14, 10, 14, 10)
        toolbar.layout().setSpacing(10)
        self.addToolBar(toolbar)

        for text, handler in (
            ("Preferences", self._on_prefs),
            ("Scan for Problems", self._on_scan),
            ("Remove Blurry Images", self._on_remove_blurry),
        ):
            button = QPushButton(text)
            button.clicked.connect(handler)
            toolbar.addWidget(button)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        toolbar.addWidget(spacer)

        start_btn = QPushButton("Start Processing")
        start_btn.setObjectName("PrimaryButton")
        start_btn.clicked.connect(self._on_start)
        toolbar.addWidget(start_btn)

    # -- results pane -----------------------------------------------------

    def _toggle_results_pane(self, visible: bool) -> None:
        sizes = self._splitter.sizes()
        if visible:
            if sizes[1] == 0:
                restored = getattr(self, "_last_results_height", 200) or 200
                self._splitter.setSizes([max(sizes[0] - restored, 120), restored])
        elif sizes[1]:
            self._last_results_height = sizes[1]
            self._splitter.setSizes([sizes[0] + sizes[1], 0])

    def _sync_results_action(self, *_args) -> None:
        """Keep the View menu checkmark in step with a manually dragged handle."""
        expanded = self._splitter.sizes()[1] > 0
        if expanded != self._results_action.isChecked():
            self._results_action.blockSignals(True)
            self._results_action.setChecked(expanded)
            self._results_action.blockSignals(False)

    def _show_results_pane(self) -> None:
        if self._splitter.sizes()[1] == 0:
            self._results_action.setChecked(True)

    # -- persisted window state -------------------------------------------

    def _restore_state(self) -> None:
        geometry = self._qsettings.value("window/geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)
            screen = QGuiApplication.primaryScreen()
            if screen is not None:
                available = screen.availableGeometry()
                self.resize(
                    min(self.width(), available.width()),
                    min(self.height(), available.height()),
                )

        sizes = self._qsettings.value("window/splitterSizes")
        if sizes:
            self._splitter.setSizes([int(size) for size in sizes])
            self._sync_results_action()

        for key, box in self._option_boxes.items():
            if box.isHidden():
                continue
            saved = self._qsettings.value(f"options/{key}")
            if saved is not None:
                box.setChecked(saved in (True, "true", "1"))

    def _save_state(self) -> None:
        self._qsettings.setValue("window/geometry", self.saveGeometry())
        self._qsettings.setValue("window/splitterSizes", self._splitter.sizes())
        for key, box in self._option_boxes.items():
            self._qsettings.setValue(f"options/{key}", box.isChecked())

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
        """Reveal the results pane and load the latest panorama thumbnail."""
        self._preview_panel.show_preview(path)
        self._show_results_pane()
        self._results_tabs.setCurrentWidget(self._preview_panel)

    # -- shutdown ---------------------------------------------------------

    def closeEvent(self, event) -> None:  # noqa: N802
        self._save_state()
        self.ipc.shutdown()
        self.manager.shutdown()
        super().closeEvent(event)
