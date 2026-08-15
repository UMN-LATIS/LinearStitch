"""GUI smoke tests (pytest-qt).

These verify the widgets build, options are collected correctly and the
preferences dialog binds to and persists settings — without running any image
processing. The worker manager and IPC listener are stubbed so no threads,
sockets or multiprocessing pools start during the test.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from linearstitch.config import Settings  # noqa: E402
from linearstitch.core.pipeline import ProcessingOptions  # noqa: E402


@pytest.fixture
def settings(tmp_path):
    return Settings(config_path=tmp_path / "config.ini")


@pytest.fixture
def main_window(qtbot, settings, monkeypatch, tmp_path):
    # Stub the worker manager and IPC listener to avoid real threads/sockets.
    import linearstitch.gui.main_window as mw

    class FakeSignals:
        class _Sig:
            def connect(self, *a, **k):
                pass

        message = _Sig()
        progress = _Sig()
        status = _Sig()
        preview_ready = _Sig()

    class FakeManager:
        def __init__(self, settings):
            self.signals = FakeSignals()
            self.submitted_scan = []
            self.submitted_blurry = []
            self.submitted_process = []
            self.options = None

        def start(self):
            pass

        def update_options(self, options):
            self.options = options

        def submit_scan(self, folder):
            self.submitted_scan.append(folder)

        def submit_remove_blurry(self, folder):
            self.submitted_blurry.append(folder)

        def submit_process(self, folder):
            self.submitted_process.append(folder)

        def shutdown(self, *a, **k):
            pass

    class FakeIPC:
        def __init__(self, handler):
            self.handler = handler

        def start(self):
            pass

        def shutdown(self):
            pass

    monkeypatch.setattr(mw, "WorkerManager", FakeManager)
    monkeypatch.setattr(mw, "IPCListener", FakeIPC)

    # Keep persisted window state out of the user's real settings store.
    from PySide6.QtCore import QSettings

    ini = str(tmp_path / "ui.ini")
    monkeypatch.setattr(mw, "QSettings", lambda: QSettings(ini, QSettings.IniFormat))

    window = mw.MainWindow(settings)
    qtbot.addWidget(window)
    return window


def test_window_builds(main_window):
    assert main_window.windowTitle() in ("LinearStitch", "LinearSnap")
    assert main_window.crop_image.isChecked()
    assert main_window.stack_images.isChecked()
    assert main_window.archive_images.isChecked()
    assert main_window.progress.isHidden()


def test_options_collected(main_window):
    main_window.mask_box.setChecked(True)
    main_window.vertical_core.setChecked(True)
    options = main_window._current_options()
    assert isinstance(options, ProcessingOptions)
    assert options.mask is True
    assert options.vertical_core is True
    assert options.crop_image is True


def test_start_submits_folders(main_window):
    main_window.folder_list.add_folder("/tmp/core_a")
    main_window.folder_list.add_folder("/tmp/core_b")
    main_window._on_start()
    assert main_window.manager.submitted_process == ["/tmp/core_a", "/tmp/core_b"]
    assert not main_window.progress.isHidden()


def test_scan_submits_folders(main_window):
    main_window.folder_list.add_folder("/tmp/core_a")
    main_window._on_scan()
    assert main_window.manager.submitted_scan == ["/tmp/core_a"]


def test_window_fits_small_screens(main_window):
    assert main_window.minimumSizeHint().height() < 600


def test_results_pane_collapses_and_restores(main_window):
    splitter = main_window._splitter
    splitter.setSizes([400, 200])

    main_window._results_action.setChecked(False)
    assert splitter.sizes()[1] == 0

    main_window._results_action.setChecked(True)
    assert splitter.sizes()[1] > 0


def test_folder_list_dedup_and_clear(main_window):
    main_window.folder_list.add_folder("/tmp/x")
    main_window.folder_list.add_folder("/tmp/x")
    assert main_window.folder_list.folders() == ["/tmp/x"]
    main_window.folder_list.clear_all()
    assert main_window.folder_list.folders() == []


def test_preferences_dialog_binds_and_saves(qtbot, settings):
    from linearstitch.gui.preferences_dialog import PreferencesDialog

    dialog = PreferencesDialog(settings)
    qtbot.addWidget(dialog)

    assert dialog.overlap.value() == pytest.approx(0.35)
    assert dialog.core_count.value() == 4

    dialog.overlap.setValue(0.5)
    dialog.core_count.setValue(8)
    dialog.right_to_left.setChecked(True)
    dialog._on_save()

    reloaded = Settings(config_path=settings.config_path)
    assert reloaded.values["Overlap"] == "0.5"
    assert reloaded.values["CoreCount"] == "8"
    assert reloaded.values["RightToLeft"] is True
