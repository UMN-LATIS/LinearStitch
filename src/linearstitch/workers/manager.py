"""Background worker manager.

Replaces the original daemon-thread-plus-``time.sleep(1)`` polling design with
worker threads that block on their queues and signal results back to the GUI
thread via Qt signals. Provides graceful shutdown.
"""

from __future__ import annotations

import os
import queue
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from functools import partial
from os.path import isdir, join

from PySide6.QtCore import QObject, Signal

from ..config import Settings
from ..core.pipeline import Pipeline, ProcessingOptions, SequenceGap, format_sequence_gaps

_SENTINEL = object()


@dataclass
class _ProcessBatch:
    remaining: int
    pause_on_missing_files: bool
    issues: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class _ProcessJob:
    folder: str
    batch: _ProcessBatch


class PipelineSignals(QObject):
    """Qt signals emitted from worker threads (delivered on the GUI thread)."""

    message = Signal(str)
    progress = Signal(int)
    status = Signal(str)         # current operation, e.g. "Stitching: col_0001"
    preview_ready = Signal(str)  # path to _preview.jpg after a successful stitch
    sequence_gap = Signal(str, object, object)  # folder, gaps and response queue


class WorkerManager:
    """Owns the processing queues, worker threads and the scan pool."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.signals = PipelineSignals()

        self._stop = threading.Event()
        self._batch_lock = threading.Lock()
        self._threads: list[threading.Thread] = []
        self._pool: ThreadPoolExecutor | None = None

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
            confirm_sequence_gap=self._confirm_sequence_gap,
        )

    # -- lifecycle --------------------------------------------------------

    def start(self) -> None:
        self._pool = ThreadPoolExecutor()
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
            self._pool.shutdown(wait=False, cancel_futures=True)
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
        self.submit_process_batch([folder])

    def submit_process_batch(self, folders: list[str]) -> None:
        if not folders:
            return
        batch = _ProcessBatch(len(folders), self.settings.pause_on_missing_files)
        target_queue = self.stack_queue if self.pipeline.options.stack_images else self.stitch_queue
        for folder in folders:
            target_queue.put(_ProcessJob(folder, batch))

    # -- worker loops -----------------------------------------------------

    def _handle_sequence_gap(
        self, batch: _ProcessBatch, folder: str, gaps: list[SequenceGap]
    ) -> bool:
        if batch.pause_on_missing_files:
            return self._confirm_sequence_gap(folder, gaps)
        missing = "\n  ".join(format_sequence_gaps(gaps))
        self._record_batch_issue(batch, f"{folder} is potentially missing a file:\n  {missing}")
        return True

    def _confirm_sequence_gap(self, folder: str, gaps: list[SequenceGap]) -> bool:
        response: queue.Queue[bool] = queue.Queue(maxsize=1)
        self.signals.sequence_gap.emit(folder, gaps, response)
        while not self._stop.is_set():
            try:
                return response.get(timeout=0.1)
            except queue.Empty:
                continue
        return False

    def _record_batch_issue(self, batch: _ProcessBatch, issue: str) -> None:
        with self._batch_lock:
            batch.issues.append(issue)

    def _record_process_error(self, job: _ProcessJob, stage: str, error: Exception) -> None:
        message = f"{stage} error: {error}"
        self.signals.message.emit(message)
        if not job.batch.pause_on_missing_files:
            self._record_batch_issue(job.batch, f"{job.folder}: {message}")

    def _finish_process_job(self, job: _ProcessJob) -> None:
        summary = None
        with self._batch_lock:
            job.batch.remaining -= 1
            if job.batch.remaining == 0 and job.batch.issues:
                summary = "Batch completed with issues:\n" + "\n".join(job.batch.issues)
        if summary is not None:
            self.signals.message.emit(summary)

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
            job = self._next(self.stack_queue)
            if job is None:
                continue
            forwarded = False
            try:
                self.signals.status.emit(f"Stacking: {os.path.basename(job.folder)}")
                self.pipeline.stack(job.folder)
                self.stitch_queue.put(job)
                forwarded = True
            except Exception as e:  # noqa: BLE001
                self._record_process_error(job, "Stack", e)
            finally:
                self.stack_queue.task_done()
                if not forwarded:
                    self._finish_process_job(job)

    def _stitch_worker(self) -> None:
        while not self._stop.is_set():
            job = self._next(self.stitch_queue)
            if job is None:
                continue
            forwarded = False
            try:
                folder = job.folder
                self.signals.status.emit(f"Stitching: {os.path.basename(folder)}")
                if not self.pipeline.stitch(
                    folder,
                    on_sequence_gap=partial(self._handle_sequence_gap, job.batch),
                    log_sequence_warning=job.batch.pause_on_missing_files,
                    on_stitch_error=(
                        None if job.batch.pause_on_missing_files
                        else partial(self._record_batch_issue, job.batch)
                    ),
                ):
                    if not job.batch.pause_on_missing_files:
                        # Automatic mode never rejects a gap, so this means too few inputs.
                        self._record_batch_issue(
                            job.batch, f"{folder}: Stitch error: fewer than two JPG images"
                        )
                    continue
                preview_path = os.path.join(
                    folder, os.path.basename(folder) + "_preview.jpg"
                )
                if os.path.isfile(preview_path):
                    self.signals.preview_ready.emit(preview_path)
                if self.pipeline.options.archive_images:
                    self.archive_queue.put(job)
                    forwarded = True
            except Exception as e:  # noqa: BLE001
                self._record_process_error(job, "Stitch", e)
            finally:
                self.stitch_queue.task_done()
                if not forwarded:
                    self._finish_process_job(job)

    def _archive_worker(self) -> None:
        while not self._stop.is_set():
            job = self._next(self.archive_queue)
            if job is None:
                continue
            try:
                self.signals.status.emit(f"Archiving: {os.path.basename(job.folder)}")
                self.pipeline.archive(job.folder)
            except Exception as e:  # noqa: BLE001
                self._record_process_error(job, "Archive", e)
            finally:
                self.archive_queue.task_done()
                self._finish_process_job(job)
