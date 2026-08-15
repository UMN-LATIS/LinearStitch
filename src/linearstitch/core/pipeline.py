"""GUI-free orchestration of the processing pipeline.

Defines the discrete processing stages (scan, focus, stitch, stack, archive) and
the options that drive them. The threading/queueing layer lives in
``linearstitch.workers``; this module only contains pure stage operations so it
can be unit-tested without a GUI or worker threads.
"""

from __future__ import annotations

import os
import shutil
from collections.abc import Callable
from dataclasses import dataclass, field
from os.path import isfile, join

from ..config import Settings
from . import archiving, focus, scanning, stacking
from .stitcher import Stitcher

ProgressCallback = Callable[[int, int], None]
MessageCallback = Callable[[str], None]


@dataclass
class ProcessingOptions:
    """User-selected processing options (mirrors the GUI checkboxes)."""

    mask: bool = False
    vertical_core: bool = False
    remove_vignette: bool = False
    rotate_image: bool = False
    crop_image: bool = True
    stack_images: bool = True
    archive_images: bool = True
    scale_path: str = ""


@dataclass
class Pipeline:
    """Runs individual processing stages against capture folders."""

    settings: Settings
    options: ProcessingOptions = field(default_factory=ProcessingOptions)
    progress_callback: ProgressCallback | None = None
    message_callback: MessageCallback | None = None

    # -- scan / focus -----------------------------------------------------

    def scan_core(self, folder: str, pool) -> None:
        scanning.scan_core(folder, pool, echo=self.message_callback)

    def remove_blurry_images(self, folder: str) -> None:
        children = [
            f for f in os.listdir(folder) if os.path.isdir(join(folder, f))
        ]
        children.sort()
        for core in children:
            focus.remove_blurry_images(
                folder + "/" + core,
                self.settings.focus_threshold,
                echo=self.message_callback,
            )

    # -- stack ------------------------------------------------------------

    def stack(self, folder: str) -> None:
        if not self.options.stack_images:
            return
        selection = self.settings.stacker_selection
        if selection == "Zerene":
            stacking.stack_zerene(folder, self.settings, echo=self.message_callback)
        elif selection == "FocusStack":
            stacking.stack_focus_stack(folder, self.settings, echo=self.message_callback)

    # -- stitch -----------------------------------------------------------

    def stitch(self, target_folder: str) -> None:
        stitcher = Stitcher(
            self.settings.overlap, message_callback=self.message_callback
        )
        files_to_stitch = [
            target_folder + "/" + f
            for f in os.listdir(target_folder)
            if isfile(join(target_folder, f)) and f.lower().endswith(".jpg")
        ]

        if len(files_to_stitch) < 2:
            return

        files_to_stitch.sort()
        parent_dir = os.path.dirname(files_to_stitch[0])
        parent_name = os.path.split(parent_dir)[1]
        output_file = os.path.join(parent_dir, parent_name + ".tiff")
        scaled_preview_file = os.path.join(parent_dir, parent_name + "_preview.jpg")
        log_file = os.path.join(parent_dir, parent_name + "_log.txt")

        if self.settings.right_to_left:
            files_to_stitch.reverse()

        stitcher.stitch_file_list(
            files_to_stitch,
            output_file,
            scaled_preview_file,
            log_file,
            self.progress_callback,
            self.options.mask,
            self.options.scale_path,
            self.options.vertical_core,
            self.options.remove_vignette,
            self.settings.vignette_magic,
            self.options.rotate_image,
            self.options.crop_image,
        )

        shutil.copy(output_file, self.settings.values["CoreOutputPath"])

    # -- archive ----------------------------------------------------------

    def archive(self, folder: str) -> None:
        archiving.archive(
            folder, self.settings.values["ArchivePath"], echo=self.message_callback
        )
