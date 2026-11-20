"""Archiving processed folders into ZIP files."""

from __future__ import annotations

import os
from collections.abc import Callable
from zipfile import ZipFile

MessageCallback = Callable[[str], None]


def get_all_file_paths(directory: str) -> list[str]:
    """Return a recursive list of every file path under ``directory``."""

    file_paths: list[str] = []
    for root, _directories, files in os.walk(directory):
        for filename in files:
            file_paths.append(os.path.join(root, filename))
    return file_paths


def archive(folder: str, archive_path: str, echo: MessageCallback | None = None) -> None:
    """Zip ``folder`` into ``archive_path``.

    A sentinel ``archive_path`` of ``'NULL'`` disables archiving, matching the
    original behaviour.
    """

    emit = echo or print
    if archive_path == "NULL":
        emit("WARNING: Folder not archived. See Archive option in config.ini file.")
        return

    output_file = os.path.basename(folder) + ".zip"
    output_file_path = os.path.join(archive_path, output_file)
    file_paths = get_all_file_paths(folder)
    emit("Zipping to: " + output_file_path)
    with ZipFile(output_file_path, "w") as zip_file:
        for file in file_paths:
            zip_file.write(file, os.path.relpath(file, os.path.join(folder, "..")))
