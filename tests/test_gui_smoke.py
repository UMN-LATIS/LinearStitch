"""GUI smoke tests (pytest-qt).

These verify the widgets build, options are collected correctly and the
preferences dialog binds to and persists settings. The main window fixture
stubs the worker manager and IPC listener.
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
        sequence_gap = _Sig()

    class FakeManager:
        def __init__(self, settings):
            self.signals = FakeSignals()
            self.submitted_scan = []
            self.submitted_blurry = []
            self.submitted_process = []
            self.submitted_batches = []
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

        def submit_process_batch(self, folders):
            self.submitted_batches.append(folders)

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
    assert main_window.windowTitle() in ("LinearStitch")
    assert main_window.crop_image.isChecked()
    assert main_window.stack_images.isChecked()
    assert main_window.archive_images.isChecked()
    assert main_window.progress.isHidden()


def test_window_and_scan_do_not_spawn_processes(qtbot, settings, monkeypatch, tmp_path):
    import cv2
    import numpy as np
    from PySide6.QtCore import QSettings

    import linearstitch.gui.main_window as mw
    from linearstitch.core.scanning import scan_folder

    def reject_process(*args, **kwargs):
        raise AssertionError("Scanning must not start a child process")

    monkeypatch.setattr("multiprocessing.process.BaseProcess.start", reject_process)
    monkeypatch.setattr(
        "multiprocessing.resource_tracker.ResourceTracker.ensure_running", reject_process
    )
    monkeypatch.setattr(mw.IPCListener, "start", lambda self: None)
    monkeypatch.setattr(mw.IPCListener, "shutdown", lambda self: None)
    monkeypatch.setattr(
        mw, "QSettings", lambda: QSettings(str(tmp_path / "ui.ini"), QSettings.IniFormat)
    )
    for name, value in (("a.jpg", 100), ("b.jpg", 100), ("c.jpg", 150)):
        assert cv2.imwrite(str(tmp_path / name), np.full((8, 8, 3), value, dtype=np.uint8))

    window = mw.MainWindow(settings)
    qtbot.addWidget(window)
    try:
        window.show()
        window.activateWindow()
        window.setFocus()
        qtbot.waitExposed(window)
        assert scan_folder(str(tmp_path), window.manager._pool) == (["c.jpg"], 0)
    finally:
        window.close()


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
    assert main_window.manager.submitted_batches == [["/tmp/core_a", "/tmp/core_b"]]
    assert not main_window.progress.isHidden()


def test_scan_submits_folders(main_window):
    main_window.folder_list.add_folder("/tmp/core_a")
    main_window._on_scan()
    assert main_window.manager.submitted_scan == ["/tmp/core_a"]


@pytest.mark.parametrize("choice", ["Skip this core", "Continue", "close"])
def test_sequence_gap_dialog(main_window, qtbot, choice):
    import queue

    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QMessageBox

    from linearstitch.core.pipeline import SequenceGap

    response = queue.Queue()
    observed = {}

    def choose():
        dialog = main_window.findChild(QMessageBox)
        observed["message"] = dialog.text()
        observed["missing"] = dialog.informativeText()
        observed["buttons"] = {button.text() for button in dialog.buttons()}
        if choice == "close":
            dialog.close()
        else:
            next(button for button in dialog.buttons() if button.text() == choice).click()

    QTimer.singleShot(0, choose)
    gaps = [SequenceGap(prefix="img_", suffix=".jpg", width=2, first=2, last=3)]
    main_window._on_sequence_gap("/tmp/core_a/", gaps, response)
    assert observed["message"] == "core_a is potentially missing a file"
    assert observed["missing"] == "Potentially missing:\nimg_02.jpg\nimg_03.jpg"
    assert observed["buttons"] == {"Skip this core", "Continue"}
    assert response.get_nowait() is (choice == "Continue")


@pytest.mark.parametrize("large_gap", [False, True])
def test_sequence_gap_dialog_handles_long_lists(main_window, qtbot, large_gap):
    import queue

    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QMessageBox

    from linearstitch.core.pipeline import SequenceGap

    response = queue.Queue()
    observed = {}

    def choose():
        dialog = main_window.findChild(QMessageBox)
        observed["missing"] = dialog.informativeText()
        observed["details"] = dialog.detailedText()
        if not large_gap:
            details_button = next(
                button for button in dialog.buttons() if button.text().startswith("Show Details")
            )
            details_button.click()
            observed["expanded"] = details_button.text()
        next(button for button in dialog.buttons() if button.text() == "Continue").click()

    QTimer.singleShot(0, choose)
    last = 9998 if large_gap else 14
    gaps = [SequenceGap(prefix="img_", suffix=".jpg", width=4, first=2, last=last)]
    main_window._on_sequence_gap("/tmp/core_a", gaps, response)
    assert response.get_nowait() is True
    if large_gap:
        assert observed["missing"] == (
            "Potentially missing:\nimg_0002.jpg through img_9998.jpg (9997 files)"
        )
    else:
        assert "img_0002.jpg" in observed["missing"]
        assert "img_0011.jpg" in observed["missing"]
        assert "img_0014.jpg" in observed["details"]
        assert "3 more" in observed["missing"]
        assert observed["expanded"].startswith("Hide Details")


@pytest.mark.parametrize("continue_stitching", [True, False])
def test_worker_waits_for_sequence_decision(qtbot, settings, tmp_path, continue_stitching):
    from unittest.mock import Mock

    from linearstitch.core.pipeline import SequenceGap
    from linearstitch.workers.manager import WorkerManager

    core = tmp_path / "core_a"
    core.mkdir()
    manager = WorkerManager(settings)

    def stack(folder):
        assert folder == str(core)
        for name in ("01.jpg", "03.jpg"):
            (core / name).touch()

    manager.pipeline.stack = Mock(side_effect=stack)
    # Exercise the real pipeline check without invoking image processing.
    import linearstitch.core.pipeline as pipeline_module

    with pytest.MonkeyPatch.context() as patch:
        stitcher = Mock()
        patch.setattr(pipeline_module, "Stitcher", Mock(return_value=stitcher))
        patch.setattr(pipeline_module.shutil, "copy", Mock())
        requests = []
        manager.signals.sequence_gap.connect(
            lambda folder, gaps, response: requests.append((folder, gaps, response))
        )
        manager._spawn(manager._stitch_worker)
        manager._spawn(manager._stack_worker)
        try:
            manager.submit_process(str(core))
            qtbot.waitUntil(lambda: len(requests) == 1)
            manager.pipeline.stack.assert_called_once_with(str(core))
            assert requests[0][0] == str(core)
            assert requests[0][1] == [
                SequenceGap(prefix="", suffix=".jpg", width=2, first=2, last=2)
            ]
            stitcher.stitch_file_list.assert_not_called()
            assert manager.archive_queue.empty()
            requests[0][2].put(continue_stitching)
            qtbot.waitUntil(lambda: manager.stitch_queue.unfinished_tasks == 0)
            assert stitcher.stitch_file_list.called is continue_stitching
            assert manager.archive_queue.empty() is (not continue_stitching)
            # A skipped core must not prevent the next queued core from running.
            if not continue_stitching:
                manager.pipeline.options.stack_images = False
                manager.submit_process(str(core))
                qtbot.waitUntil(lambda: len(requests) == 2)
                requests[1][2].put(True)
                qtbot.waitUntil(lambda: manager.stitch_queue.unfinished_tasks == 0)
                stitcher.stitch_file_list.assert_called_once()
        finally:
            manager.shutdown()


def test_shutdown_releases_pending_sequence_warning(qtbot, settings):
    from linearstitch.workers.manager import WorkerManager

    manager = WorkerManager(settings)
    requests = []
    decisions = []
    manager.signals.sequence_gap.connect(lambda *args: requests.append(args))
    manager._spawn(lambda: decisions.append(manager._confirm_sequence_gap("/tmp/core_a", [])))
    qtbot.waitUntil(lambda: len(requests) == 1)
    manager.shutdown()
    assert decisions == [False]


def test_missing_files_reported_after_entire_batch(
    qtbot, settings, tmp_path, monkeypatch, main_window
):
    import threading
    from pathlib import Path
    from unittest.mock import Mock

    import linearstitch.core.pipeline as pipeline_module
    from linearstitch.workers.manager import WorkerManager

    settings.values["PauseOnMissingFiles"] = False
    first, second = tmp_path / "core_a", tmp_path / "core_b"
    first.mkdir()
    second.mkdir()
    stack_started = threading.Event()
    release_stack = threading.Event()
    archive_started = threading.Event()
    release_archive = threading.Event()

    def stack(folder):
        if folder == str(second):
            stack_started.set()
            assert release_stack.wait(timeout=10)
        names = ("img_01.jpg", "img_03.jpg") if folder == str(first) else (
            "img_04.jpg", "img_07.jpg"
        )
        for name in names:
            (Path(folder) / name).touch()

    def archive(folder):
        if folder == str(second):
            archive_started.set()
            assert release_archive.wait(timeout=10)

    manager = WorkerManager(settings)
    manager.pipeline.stack = Mock(side_effect=stack)
    manager.pipeline.archive = Mock(side_effect=archive)
    stitcher = Mock()
    monkeypatch.setattr(pipeline_module, "Stitcher", Mock(return_value=stitcher))
    monkeypatch.setattr(pipeline_module.shutil, "copy", Mock())
    messages = []
    prompts = []
    manager.signals.message.connect(messages.append)
    manager.signals.message.connect(main_window._append_log)
    manager.signals.sequence_gap.connect(lambda *args: prompts.append(args))
    manager._spawn(manager._stack_worker)
    manager._spawn(manager._stitch_worker)
    manager._spawn(manager._archive_worker)
    try:
        manager.submit_process_batch([str(first), str(second)])
        qtbot.waitUntil(lambda: stack_started.is_set() and manager.pipeline.archive.call_count == 1)
        qtbot.wait(30)
        assert not messages
        assert not main_window.log.toPlainText()
        assert not prompts

        release_stack.set()
        qtbot.waitUntil(archive_started.is_set)
        qtbot.wait(30)
        assert not messages

        release_archive.set()
        qtbot.waitUntil(lambda: any(message.startswith("Batch completed with issues:") for message in messages))
        summary = next(message for message in messages if message.startswith("Batch completed with issues:"))
        assert str(first) in summary and "img_02.jpg" in summary
        assert str(second) in summary and "img_05.jpg" in summary and "img_06.jpg" in summary
        assert stitcher.stitch_file_list.call_count == 2
        assert manager.pipeline.archive.call_count == 2
        assert not prompts
        qtbot.waitUntil(lambda: "img_06.jpg" in main_window.log.toPlainText())
        assert "Batch completed with issues:" in main_window.log.toPlainText()
    finally:
        release_stack.set()
        release_archive.set()
        manager.shutdown()


@pytest.mark.parametrize("failed_stage", ["Stack", "Stitch", "Archive", "Insufficient images"])
def test_batch_reports_stage_errors_and_keeps_processing(
    qtbot, settings, tmp_path, monkeypatch, failed_stage
):
    from pathlib import Path
    from unittest.mock import Mock

    import linearstitch.core.pipeline as pipeline_module
    from linearstitch.workers.manager import WorkerManager

    settings.values["PauseOnMissingFiles"] = False
    broken, good = tmp_path / "broken", tmp_path / "good"
    broken.mkdir()
    good.mkdir()
    archived = []

    def stack(folder):
        if folder == str(broken) and failed_stage == "Stack":
            raise RuntimeError("intentional failure")
        names = (
            ("01.jpg",) if folder == str(broken) and failed_stage == "Insufficient images"
            else ("01.jpg", "03.jpg")
        )
        for name in names:
            (Path(folder) / name).touch()

    def stitch(files, *_args):
        if Path(files[0]).parent == broken and failed_stage == "Stitch":
            raise RuntimeError("intentional failure")

    def archive(folder):
        if folder == str(broken) and failed_stage == "Archive":
            raise RuntimeError("intentional failure")
        archived.append(folder)

    manager = WorkerManager(settings)
    manager.pipeline.stack = Mock(side_effect=stack)
    manager.pipeline.archive = Mock(side_effect=archive)
    stitcher = Mock()
    stitcher.stitch_file_list.side_effect = stitch
    monkeypatch.setattr(pipeline_module, "Stitcher", Mock(return_value=stitcher))
    monkeypatch.setattr(pipeline_module.shutil, "copy", Mock())
    messages = []
    prompts = []
    manager.signals.message.connect(messages.append)
    manager.signals.sequence_gap.connect(lambda *args: prompts.append(args))
    manager._spawn(manager._stack_worker)
    manager._spawn(manager._stitch_worker)
    manager._spawn(manager._archive_worker)
    try:
        manager.submit_process_batch([str(broken), str(good)])
        qtbot.waitUntil(lambda: any(message.startswith("Batch completed with issues:") for message in messages))
        summary = next(message for message in messages if message.startswith("Batch completed with issues:"))
        assert str(broken) in summary
        expected = (
            "Stitch error: fewer than two JPG images"
            if failed_stage == "Insufficient images"
            else f"{failed_stage} error: intentional failure"
        )
        assert expected in summary
        assert str(good) in summary and "02.jpg" in summary
        assert str(good) in archived
        assert not prompts
    finally:
        manager.shutdown()


def test_batch_reports_are_separate_and_preference_is_snapshotted(
    qtbot, settings, tmp_path, monkeypatch
):
    from unittest.mock import Mock

    import linearstitch.core.pipeline as pipeline_module
    from linearstitch.workers.manager import WorkerManager

    settings.values["PauseOnMissingFiles"] = False
    folders = [tmp_path / name for name in ("first", "second", "ipc", "complete")]
    for folder in folders:
        folder.mkdir()
        names = ("01.jpg", "02.jpg") if folder == folders[3] else ("01.jpg", "03.jpg")
        for name in names:
            (folder / name).touch()

    manager = WorkerManager(settings)
    manager.update_options(ProcessingOptions(stack_images=False, archive_images=False))
    monkeypatch.setattr(pipeline_module, "Stitcher", Mock())
    monkeypatch.setattr(pipeline_module.shutil, "copy", Mock())
    messages = []
    prompts = []
    manager.signals.message.connect(messages.append)
    manager.signals.sequence_gap.connect(lambda *args: prompts.append(args))
    manager.submit_process_batch([str(folders[0]), str(folders[1])])
    manager.submit_process(str(folders[2]))
    manager.submit_process(str(folders[3]))
    settings.values["PauseOnMissingFiles"] = True
    manager._spawn(manager._stitch_worker)
    try:
        qtbot.waitUntil(
            lambda: sum(message.startswith("Batch completed with issues:") for message in messages) == 2
        )
        qtbot.waitUntil(lambda: manager.stitch_queue.unfinished_tasks == 0)
        summaries = [message for message in messages if message.startswith("Batch completed with issues:")]
        assert str(folders[0]) in summaries[0] and str(folders[1]) in summaries[0]
        assert str(folders[2]) not in summaries[0]
        assert str(folders[2]) in summaries[1]
        assert str(folders[0]) not in summaries[1] and str(folders[1]) not in summaries[1]
        assert not prompts

        manager.submit_process(str(folders[2]))
        qtbot.waitUntil(lambda: len(prompts) == 1)
        prompts[0][2].put(False)
        qtbot.waitUntil(lambda: manager.stitch_queue.unfinished_tasks == 0)
        assert sum(message.startswith("Batch completed with issues:") for message in messages) == 2
    finally:
        manager.shutdown()


@pytest.mark.parametrize("fail_first_pair", [False, True])
def test_noninteractive_batch_writes_stitch_and_reports_pair_errors(
    qtbot, settings, tmp_path, stitch_inputs, monkeypatch, fail_first_pair
):
    from pathlib import Path

    import cv2

    from linearstitch.core.stitcher import Stitcher
    from linearstitch.workers.manager import WorkerManager

    core = tmp_path / "core"
    output = tmp_path / "output"
    core.mkdir()
    output.mkdir()
    for index, source in enumerate(stitch_inputs):
        number = index if index == 0 else index + 1
        Path(source).rename(core / f"tile_{number:03d}.jpg")

    settings.values["PauseOnMissingFiles"] = False
    settings.values["CoreOutputPath"] = str(output)
    if fail_first_pair:
        calls = []

        def stitch_images(_self, _image1, image2, _mask):
            calls.append(1)
            if len(calls) == 1:
                raise RuntimeError("simulated overlap failure")
            return image2.copy()

        monkeypatch.setattr(Stitcher, "stitch_images", stitch_images)

    manager = WorkerManager(settings)
    manager.update_options(ProcessingOptions(stack_images=False, archive_images=False))
    messages = []
    prompts = []
    manager.signals.message.connect(messages.append)
    manager.signals.sequence_gap.connect(lambda *args: prompts.append(args))
    manager._spawn(manager._stitch_worker)
    try:
        manager.submit_process_batch([str(core)])
        qtbot.waitUntil(
            lambda: any(message.startswith("Batch completed with issues:") for message in messages),
            timeout=20000,
        )
        summary = next(message for message in messages if message.startswith("Batch completed with issues:"))
        assert "tile_001.jpg" in summary
        image = cv2.imread(str(output / "core.tiff"))
        assert image is not None
        assert not prompts
        if fail_first_pair:
            assert len(calls) == len(stitch_inputs) - 1
            assert "Error stitching" in summary
            assert "simulated overlap failure" in summary
        else:
            assert image.shape[1] > 300
            assert "Error stitching" not in summary
    finally:
        manager.shutdown()


def test_window_fits_small_screens(main_window):
    assert main_window.minimumSizeHint().height() < 600


def test_preview_scales_image_to_fit_viewport(qtbot, tmp_path):
    from PySide6.QtGui import QPixmap

    from linearstitch.gui.widgets.preview_panel import PreviewPanel

    image_path = tmp_path / "wide-preview.png"
    QPixmap(1200, 300).save(str(image_path))

    panel = PreviewPanel()
    qtbot.addWidget(panel)
    panel.resize(300, 100)
    panel.show()
    panel.show_preview(str(image_path))
    qtbot.wait(20)

    displayed = panel._label.pixmap()
    assert displayed.width() <= panel.viewport().width()
    assert displayed.height() <= panel.viewport().height()
    assert panel.horizontalScrollBar().maximum() == 0

    panel.resize(500, 200)
    qtbot.wait(20)
    displayed = panel._label.pixmap()
    assert displayed.width() <= panel.viewport().width()
    assert displayed.height() <= panel.viewport().height()


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


@pytest.mark.parametrize("focused", [True, False])
def test_folder_selection_stays_readable(qtbot, focused):
    from PySide6.QtCore import Qt

    from linearstitch.app import _load_stylesheet
    from linearstitch.gui.widgets.file_list import FolderListWidget

    def luminance(color):
        channels = (color.redF(), color.greenF(), color.blueF())
        linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
        return sum(c * weight for c, weight in zip(linear, (0.2126, 0.7152, 0.0722), strict=True))

    def contrast(first, second):
        values = sorted((luminance(first), luminance(second)))
        return (values[1] + 0.05) / (values[0] + 0.05)

    folders = FolderListWidget()
    qtbot.addWidget(folders)
    folders.setStyleSheet(_load_stylesheet())
    folders.resize(500, 140)
    folders.add_folder("/tmp/capture_folder")
    folders.show()
    qtbot.waitExposed(folders)

    rect = folders.visualItemRect(folders.item(0))
    sample = rect.topRight()
    sample.setX(sample.x() - 10)
    sample.setY(rect.center().y())
    viewport = folders.viewport()
    unselected_background = viewport.grab().toImage().scaled(viewport.size()).pixelColor(sample)

    qtbot.mouseClick(folders.viewport(), Qt.MouseButton.LeftButton, pos=rect.center())
    if focused:
        folders.setFocus()
    else:
        folders.clearFocus()

    image = viewport.grab().toImage().scaled(viewport.size())
    background = image.pixelColor(sample)
    assert folders.folders() == ["/tmp/capture_folder"]
    assert folders.item(0).isSelected()
    assert contrast(background, unselected_background) >= 1.5
    readable_pixels = sum(
        contrast(image.pixelColor(x, y), background) >= 4.5
        for x in range(rect.left() + 10, rect.left() + 130)
        for y in range(rect.top() + 4, rect.bottom() - 4)
    )
    assert readable_pixels >= 10


def test_preferences_dialog_binds_and_saves(qtbot, settings):
    from linearstitch.gui.preferences_dialog import PreferencesDialog

    dialog = PreferencesDialog(settings)
    qtbot.addWidget(dialog)
    dialog.show()
    qtbot.waitExposed(dialog)

    assert dialog.browse_path.width() >= 250

    assert dialog.overlap.value() == pytest.approx(0.35)
    assert dialog.core_count.value() == 4
    assert dialog.pause_on_missing_files.isChecked()

    proc_form = dialog.pause_on_missing_files.parentWidget().layout()
    right_to_left_row = proc_form.getWidgetPosition(dialog.right_to_left)[0]
    pause_on_missing_row = proc_form.getWidgetPosition(dialog.pause_on_missing_files)[0]
    assert right_to_left_row >= 0
    assert pause_on_missing_row == right_to_left_row + 1

    dialog.overlap.setValue(0.5)
    dialog.core_count.setValue(8)
    dialog.right_to_left.setChecked(True)
    dialog.pause_on_missing_files.setChecked(False)
    dialog._on_save()

    reloaded = Settings(config_path=settings.config_path)
    assert reloaded.values["Overlap"] == "0.5"
    assert reloaded.values["CoreCount"] == "8"
    assert reloaded.values["RightToLeft"] is True
    assert reloaded.pause_on_missing_files is False

    reopened = PreferencesDialog(reloaded)
    qtbot.addWidget(reopened)
    assert not reopened.pause_on_missing_files.isChecked()
    reopened.pause_on_missing_files.setChecked(True)
    reopened._on_save()
    assert Settings(config_path=settings.config_path).pause_on_missing_files is True
