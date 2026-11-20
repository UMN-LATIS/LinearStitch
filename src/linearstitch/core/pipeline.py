"""GUI-free orchestration of the processing pipeline.

Defines the discrete processing stages (scan, focus, stitch, stack, archive) and
the options that drive them. The threading/queueing layer lives in
``linearstitch.workers``; this module only contains pure stage operations so it
can be unit-tested without a GUI or worker threads.
"""

from __future__ import annotations

import os
import re
import shutil
from collections.abc import Callable
from dataclasses import dataclass, field
from os.path import isfile, join

from ..config import Settings
from . import archiving, focus, scanning, stacking
from .stitcher import Stitcher

ProgressCallback = Callable[[int, int], None]
MessageCallback = Callable[[str], None]


@dataclass(frozen=True)
class SequenceGap:
    """An inclusive range of potentially missing numbered filenames."""

    prefix: str
    suffix: str
    width: int
    first: int
    last: int

    def filename(self, number: int) -> str:
        return f"{self.prefix}{number:0{self.width}d}{self.suffix}"


SequenceGapCallback = Callable[[str, list[SequenceGap]], bool]


def find_sequence_gaps(paths: list[str]) -> list[SequenceGap]:
    """Find internal gaps when matching filenames have one varying number."""
    groups: dict[tuple[str, ...], list[tuple[list[str], str]]] = {}
    for path in sorted(paths):
        stem, extension = os.path.splitext(os.path.basename(path))
        parts = re.split(r"([0-9]+)", stem)
        if len(parts) > 1:
            groups.setdefault(tuple(parts[::2]), []).append((parts, extension))

    gaps = []
    for files in groups.values():
        numbers = [tuple(int(number) for number in parts[1::2]) for parts, _ in files]
        varying = [
            index
            for index, column in enumerate(zip(*numbers, strict=True))
            if len(set(column)) > 1
        ]
        if len(varying) != 1:
            continue

        part_index = 2 * varying[0] + 1
        ordered = sorted(files, key=lambda item: int(item[0][part_index]))
        for (lower, extension), (upper, _) in zip(ordered, ordered[1:], strict=False):
            first = int(lower[part_index]) + 1
            last = int(upper[part_index]) - 1
            if first <= last:
                width = max(
                    (
                        len(number)
                        for number in (lower[part_index], upper[part_index])
                        if len(number) > len(str(int(number)))
                    ),
                    default=0,
                )
                gaps.append(
                    SequenceGap(
                        prefix="".join(lower[:part_index]),
                        suffix="".join(lower[part_index + 1 :]) + extension,
                        width=width,
                        first=first,
                        last=last,
                    )
                )
    return gaps


def format_sequence_gaps(gaps: list[SequenceGap]) -> list[str]:
    """Describe missing filenames, using ranges for very large gaps."""
    missing = []
    for gap in gaps:
        count = gap.last - gap.first + 1
        if count > 100:
            missing.append(
                f"{gap.filename(gap.first)} through {gap.filename(gap.last)} ({count} files)"
            )
        else:
            missing.extend(gap.filename(number) for number in range(gap.first, gap.last + 1))
    return missing


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
    confirm_sequence_gap: SequenceGapCallback | None = None

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

    def stitch(
        self,
        target_folder: str,
        *,
        on_sequence_gap: SequenceGapCallback | None = None,
        log_sequence_warning: bool = True,
        on_stitch_error: MessageCallback | None = None,
    ) -> bool:
        """Stitch a core, returning False when it is skipped or has too few images."""
        files_to_stitch = [
            target_folder + "/" + f
            for f in os.listdir(target_folder)
            if isfile(join(target_folder, f)) and f.lower().endswith(".jpg")
        ]

        if len(files_to_stitch) < 2:
            return False

        gaps = find_sequence_gaps(files_to_stitch)
        if gaps:
            core_name = os.path.basename(os.path.normpath(target_folder))
            warning = f"{core_name} is potentially missing a file"
            if log_sequence_warning and self.message_callback:
                self.message_callback(warning)
            confirm = on_sequence_gap if on_sequence_gap is not None else self.confirm_sequence_gap
            if confirm is None:
                raise ValueError(warning)
            if not confirm(target_folder, gaps):
                if self.message_callback:
                    self.message_callback(f"Skipping core: {core_name}")
                return False

        stitcher = Stitcher(
            self.settings.overlap,
            message_callback=self.message_callback,
            error_callback=on_stitch_error,
        )
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
        return True

    # -- archive ----------------------------------------------------------

    def archive(self, folder: str) -> None:
        archiving.archive(
            folder, self.settings.values["ArchivePath"], echo=self.message_callback
        )
