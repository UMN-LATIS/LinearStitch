"""Fix missing photos in capture stacks by shifting files forward.

Shared logic extracted from the original ``StackFixer.py`` GUI and
``fixFiles.py`` CLI (identical algorithms). When a stack is missing ``num``
images, the trailing files of each subsequent stack are shifted forward to
realign the sequence.
"""

from __future__ import annotations

import os
import shutil
from collections.abc import Callable
from os.path import isdir, isfile, join

MessageCallback = Callable[[str], None]


def fix_stack(
    source_folder: str,
    bad_stack: str,
    num: int,
    echo: MessageCallback | None = None,
) -> None:
    """Realign stacks under ``source_folder`` starting at ``bad_stack``.

    ``num`` trailing files are shifted forward from each stack to the next,
    starting at ``bad_stack``; leftover trailing files are removed.
    """

    emit = echo or print
    children_stacks = [
        f for f in os.listdir(source_folder) if isdir(join(source_folder, f))
    ]
    children_stacks.sort()

    found_bad_stack = False
    bad_files: list[str] = []
    negative_num = -1 * num

    for stack in children_stacks:
        path_to_stack = source_folder + "/" + stack
        if stack == bad_stack:
            found_bad_stack = True

        if found_bad_stack:
            if len(bad_files) > 0:
                for bad_file in bad_files:
                    emit("moving: " + bad_file)
                    shutil.move(bad_file, path_to_stack)

            files = [
                os.path.join(path_to_stack, f)
                for f in os.listdir(path_to_stack)
                if isfile(join(path_to_stack, f))
            ]
            files.sort()
            bad_files = files[negative_num:]

    if len(bad_files) > 0:
        for bad_file in bad_files:
            emit("removing: " + bad_file)
            os.remove(bad_file)
