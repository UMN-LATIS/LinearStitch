"""Golden tests: the refactored core must match the original ``stitcher.py`` byte-for-byte.

The original module imports ``pyopencl`` (and optionally ``pyvips``) at import
time, which are not needed for the default stitching path. We inject lightweight
stub modules so the original code can be imported and exercised without those
native dependencies.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys
import types

import cv2
import numpy as np
import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]


def _install_native_stubs() -> None:
    """Stub out pyopencl / pyvips so import-time side effects don't fail."""

    for name in ("pyopencl", "pyvips"):
        if name not in sys.modules:
            module = types.ModuleType(name)
            sys.modules[name] = module


def _load_original_stitcher():
    _install_native_stubs()
    spec = importlib.util.spec_from_file_location(
        "_original_stitcher", REPO_ROOT / "tests" / "_legacy" / "original_stitcher.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _read(path: str) -> np.ndarray:
    img = cv2.imread(path)
    assert img is not None, f"failed to read {path}"
    return img


@pytest.fixture(autouse=True)
def _stubs():
    _install_native_stubs()
    yield


def test_calculate_offset_matches_original(stitch_inputs):
    original_mod = _load_original_stitcher()
    from linearstitch.core.stitcher import Stitcher as NewStitcher

    img1 = _read(stitch_inputs[0])
    img2 = _read(stitch_inputs[1])

    orig = original_mod.Stitcher(0.35)
    orig.logFile = open("/dev/null", "w")  # original logMessage writes to a file
    new = NewStitcher(0.35, message_callback=lambda _m: None)

    orig_offset = orig.calculate_offset(img1, img2, False)
    new_offset = new.calculate_offset(img1, img2, False)
    orig.logFile.close()

    assert orig_offset == new_offset


def test_stitch_images_matches_original(stitch_inputs):
    original_mod = _load_original_stitcher()
    from linearstitch.core.stitcher import Stitcher as NewStitcher

    img1 = _read(stitch_inputs[0])
    img2 = _read(stitch_inputs[1])

    orig = original_mod.Stitcher(0.35)
    orig.logFile = open("/dev/null", "w")
    new = NewStitcher(0.35, message_callback=lambda _m: None)

    orig_comp = orig.stitch_images(img1.copy(), img2.copy(), False)
    new_comp = new.stitch_images(img1.copy(), img2.copy(), False)
    orig.logFile.close()

    assert orig_comp.shape == new_comp.shape
    assert np.array_equal(orig_comp, new_comp)


def test_stitch_file_list_matches_original(stitch_inputs, tmp_path):
    original_mod = _load_original_stitcher()
    from linearstitch.core.stitcher import Stitcher as NewStitcher

    # Original
    orig_out = str(tmp_path / "orig.tiff")
    orig_prev = str(tmp_path / "orig_preview.jpg")
    orig_log = str(tmp_path / "orig_log.txt")
    original_mod.Stitcher(0.35).stitchFileList(
        list(stitch_inputs), orig_out, orig_prev, orig_log, None,
        False, "", False, False, 1.1, False, True,
    )

    # New
    new_out = str(tmp_path / "new.tiff")
    new_prev = str(tmp_path / "new_preview.jpg")
    new_log = str(tmp_path / "new_log.txt")
    NewStitcher(0.35, message_callback=lambda _m: None).stitch_file_list(
        list(stitch_inputs), new_out, new_prev, new_log, None,
        False, "", False, False, 1.1, False, True,
    )

    orig_img = _read(orig_out)
    new_img = _read(new_out)
    assert orig_img.shape == new_img.shape
    assert np.array_equal(orig_img, new_img)
