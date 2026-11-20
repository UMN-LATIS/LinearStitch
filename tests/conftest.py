"""Shared pytest fixtures: deterministic synthetic panoramas for stitching tests."""

from __future__ import annotations

import pathlib

import cv2
import numpy as np
import pytest


def _make_panorama(width: int = 900, height: int = 250, seed: int = 1234) -> np.ndarray:
    """Build a deterministic, feature-rich panorama for SIFT to align."""

    rng = np.random.default_rng(seed)
    img = np.full((height, width, 3), 40, dtype=np.uint8)

    # Light random texture so SIFT always has keypoints.
    noise = rng.integers(0, 60, size=(height, width, 3), dtype=np.uint8)
    img = cv2.add(img, noise)

    # Strong, distinctive shapes spread across the whole width.
    for i in range(60):
        cx = int(rng.integers(0, width))
        cy = int(rng.integers(0, height))
        color = tuple(int(c) for c in rng.integers(80, 255, size=3))
        shape = i % 3
        if shape == 0:
            cv2.circle(img, (cx, cy), int(rng.integers(8, 25)), color, -1)
        elif shape == 1:
            cv2.rectangle(
                img, (cx, cy), (cx + int(rng.integers(10, 40)), cy + int(rng.integers(10, 40))), color, -1
            )
        else:
            cv2.line(img, (cx, cy), (cx + int(rng.integers(-40, 40)), cy + int(rng.integers(-40, 40))), color, 3)

    return img


@pytest.fixture
def stitch_inputs(tmp_path: pathlib.Path) -> list[str]:
    """Write a panorama split into overlapping tiles; return the tile file paths."""

    pano = _make_panorama()
    height, width = pano.shape[:2]
    tile_w = 300
    step = 200

    paths: list[str] = []
    starts = list(range(0, width - tile_w + 1, step))
    if starts[-1] != width - tile_w:
        starts.append(width - tile_w)

    for idx, x in enumerate(starts):
        tile = pano[:, x : x + tile_w]
        out = tmp_path / f"tile_{idx:03d}.jpg"
        cv2.imwrite(str(out), tile, [cv2.IMWRITE_JPEG_QUALITY, 95])
        paths.append(str(out))

    return paths
