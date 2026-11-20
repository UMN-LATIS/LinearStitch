"""Tests for the stack-fixer file-shifting logic.

The algorithm cascades the trailing ``num`` files of the bad stack forward into
each subsequent stack, deleting the final overflow — so a bad stack that has
``num`` *extra* images is realigned back to the common length.
"""

from __future__ import annotations

import os

from linearstitch.core.stackfix import fix_stack


def _make_stack(base, name, count):
    folder = base / name
    folder.mkdir()
    for i in range(count):
        (folder / f"img_{i:03d}.jpg").write_text(f"{name}-{i}")
    return folder


def test_fix_stack_shifts_extra_files_forward(tmp_path):
    # stack_a has one extra image; everything realigns to 5.
    _make_stack(tmp_path, "stack_a", 6)
    _make_stack(tmp_path, "stack_b", 5)
    _make_stack(tmp_path, "stack_c", 5)

    fix_stack(str(tmp_path), "stack_a", 1, echo=lambda _m: None)

    for name in ("stack_a", "stack_b", "stack_c"):
        assert len(os.listdir(tmp_path / name)) == 5


def test_fix_stack_only_affects_from_bad_stack(tmp_path):
    _make_stack(tmp_path, "stack_a", 5)
    _make_stack(tmp_path, "stack_b", 6)
    _make_stack(tmp_path, "stack_c", 5)

    fix_stack(str(tmp_path), "stack_b", 1, echo=lambda _m: None)

    # stack_a (before the bad stack) is untouched.
    assert len(os.listdir(tmp_path / "stack_a")) == 5
    assert len(os.listdir(tmp_path / "stack_b")) == 5
    assert len(os.listdir(tmp_path / "stack_c")) == 5
