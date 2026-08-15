"""Background worker manager.

Replaces the original daemon-thread-plus-``time.sleep(1)`` polling design with
worker threads that block on their queues and signal results back to the GUI
thread via Qt signals. Provides graceful shutdown.
"""

from __future__ import annotations

import multiprocessing
import os
import queue
import threading
from os.path import isdir, join

from PySide6.QtCore import QObject, Signal

from ..config import Settings
from ..core.pipeline import Pipeline, ProcessingOptions

_SENTINEL = object()


class PipelineSignals(QObject):
    """Qt signals emitted from worker threads (delivered on the GUI thread)."""

    message = Signal(str)
    progress = Signal(int)
    status = Signal(str)         # current operation, e.g. "Stitching: col_0001"
    preview_ready = Signal(str)  # path to _preview.jpg after a successful stitch


class WorkerManager:
    """Owns the processing queues, worker threads and the multiprocessing pool."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.signals = PipelineSignals()

        self._stop = threading.Event()
        self._threads: list[threading.Thread] = []
        self._pool: multiprocessing.pool.Pool | None = None

        self.scan_queue: queue.Queue = queue.Queue()
        self.focus_queue: queue.Queue = queue.Queue()
        self.stitch_queue: queue.Queue = queue.Queue()
        self.stack_queue: queue.Queue = queue.Queue()
        self.archive_queue: queue.Queue = queue.Queue()

        self.pipeline = Pipeline(
            settings=settings,
            options=ProcessingOptions(),
            progress_callback=lambda _status, progress: self.signals.progress.emit(progress),
            message_callback=self.signals.message.emit,
        )

    # -- lifecycle --------------------------------------------------------

    def start(self) -> None:
        self._pool = multiprocessing.Pool()
        core_count = self.settings.core_count

        for _ in range(core_count):
            self._spawn(self._scan_worker)
        for _ in range(core_count):
            self._spawn(self._focus_worker)
        self._spawn(self._stitch_worker)
        self._spawn(self._stack_worker)
        self._spawn(self._archive_worker)

    def _spawn(self, target) -> None:
        thread = threading.Thread(target=target, daemon=True)
        thread.start()
        self._threads.append(thread)

    def shutdown(self, timeout: float = 5.0) -> None:
        """Signal all workers to stop and wait for them to finish."""

        self._stop.set()
        for q in (
            self.scan_queue,
            self.focus_queue,
            self.stitch_queue,
            self.stack_queue,
            self.archive_queue,
        ):
            q.put(_SENTINEL)
        for thread in self._threads:
            thread.join(timeout=timeout)
        if self._pool is not None:
            self._pool.terminate()
            self._pool.join()
            self._pool = None

    # -- public submission API -------------------------------------------

    def update_options(self, options: ProcessingOptions) -> None:
        self.pipeline.options = options

    def submit_scan(self, folder: str) -> None:
        self.scan_queue.put(folder)

    def submit_remove_blurry(self, folder: str) -> None:
        children = [f for f in os.listdir(folder) if isdir(join(folder, f))]
        children.sort()
        for core in children:
            self.focus_queue.put(folder + "/" + core)

    def submit_process(self, folder: str) -> None:
        if self.pipeline.options.stack_images:
            self.stack_queue.put(folder)
        else:
            self.stitch_queue.put(folder)

    # -- worker loops -----------------------------------------------------

    def _next(self, q: queue.Queue):
        try:
            item = q.get(timeout=0.5)
        except queue.Empty:
            return None
        if item is _SENTINEL:
            return None
        return item

    def _scan_worker(self) -> None:
        while not self._stop.is_set():
            folder = self._next(self.scan_queue)
            if folder is None:
                continue
            try:
                self.signals.status.emit(f"Scanning: {os.path.basename(folder)}")
                self.pipeline.scan_core(folder, self._pool)
            except Exception as e:  # noqa: BLE001
                self.signals.message.emit(f"Scan error: {e}")
            finally:
                self.scan_queue.task_done()

    def _focus_worker(self) -> None:
        while not self._stop.is_set():
            folder = self._next(self.focus_queue)
            if folder is None:
                continue
            try:
                self.signals.status.emit(f"Checking focus: {os.path.basename(folder)}")
                from ..core import focus

                focus.remove_blurry_images(
                    folder, self.settings.focus_threshold, echo=self.signals.message.emit
                )
            except Exception as e:  # noqa: BLE001
                self.signals.message.emit(f"Blur removal error: {e}")
            finally:
                self.focus_queue.task_done()

    def _stack_worker(self) -> None:
        while not self._stop.is_set():
            folder = self._next(self.stack_queue)
            if folder is None:
                continue
            try:
                self.signals.status.emit(f"Stacking: {os.path.basename(folder)}")
                self.pipeline.stack(folder)
                self.stitch_queue.put(folder)
            except Exception as e:  # noqa: BLE001
                self.signals.message.emit(f"Stack error: {e}")
            finally:
                self.stack_queue.task_done()

    def _stitch_worker(self) -> None:
        while not self._stop.is_set():
            folder = self._next(self.stitch_queue)
            if folder is None:
                continue
            try:
                self.signals.status.emit(f"Stitching: {os.path.basename(folder)}")
                self.pipeline.stitch(folder)
                preview_path = os.path.join(
                    folder, os.path.basename(folder) + "_preview.jpg"
                )
                if os.path.isfile(preview_path):
                    self.signals.preview_ready.emit(preview_path)
                if self.pipeline.options.archive_images:
                    self.archive_queue.put(folder)
            except Exception as e:  # noqa: BLE001
                self.signals.message.emit(f"Stitch error: {e}")
            finally:
                self.stitch_queue.task_done()

    def _archive_worker(self) -> None:
        while not self._stop.is_set():
            folder = self._next(self.archive_queue)
            if folder is None:
                continue
            try:
                self.signals.status.emit(f"Archiving: {os.path.basename(folder)}")
                self.pipeline.archive(folder)
            except Exception as e:  # noqa: BLE001
                self.signals.message.emit(f"Archive error: {e}")
            finally:
                self.archive_queue.task_done()
