"""Golden test for the 2-D stitcher: refactored core must match the original."""

from __future__ import annotations

import importlib.util
import pathlib
import sys
import types

import cv2
import numpy as np

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]


def _install_native_stubs() -> None:
    for name in ("pyopencl", "pyvips"):
        if name not in sys.modules:
            sys.modules[name] = types.ModuleType(name)


def _load_original_2d():
    _install_native_stubs()
    spec = importlib.util.spec_from_file_location(
        "_original_twodstitcher", REPO_ROOT / "tests" / "_legacy" / "original_twodstitcher.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _read(path: str) -> np.ndarray:
    img = cv2.imread(path)
    assert img is not None
    return img


def test_2d_horizontal_matches_original(stitch_inputs):
    original_mod = _load_original_2d()
    from linearstitch.core.stitcher2d import TwoDStitcher

    img1 = _read(stitch_inputs[0])
    img2 = _read(stitch_inputs[1])

    orig = original_mod.TwoDStitcher()
    new = TwoDStitcher()

    orig_comp = orig.stitch_images(img1.copy(), img2.copy(), "horizontal")
    new_comp = new.stitch_images(img1.copy(), img2.copy(), "horizontal")

    assert orig_comp.shape == new_comp.shape
    assert np.array_equal(orig_comp, new_comp)


def test_2d_offset_matches_original(stitch_inputs):
    original_mod = _load_original_2d()
    from linearstitch.core.stitcher2d import TwoDStitcher

    img1 = _read(stitch_inputs[0])
    img2 = _read(stitch_inputs[1])

    orig_offset = original_mod.TwoDStitcher().calculate_offset(img1, img2, "horizontal")
    new_offset = TwoDStitcher().calculate_offset(img1, img2, "horizontal")

    assert orig_offset == new_offset
