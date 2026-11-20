"""Tunable constants for the stitching algorithms.

These values are preserved verbatim from the original ``stitcher.py`` and
``twodstitcher.py`` ``CONFIG`` dictionaries to guarantee identical output.
"""

from __future__ import annotations

# SIFT feature detection / matching (shared by both stitchers).
MAX_FEATURES = 500
FLANN_CHECKS = 12

# Lowe's ratio test threshold.
LOWE_RATIO = 0.7

# 1-D stitcher (original stitcher.py CONFIG).
SCALE_FACTOR_1D = 0.25
DEFAULT_OVERLAP_1D = 0.35

# 2-D stitcher (original twodstitcher.py CONFIG).
SCALE_FACTOR_2D = 0.5
OVERLAP_2D = 0.55

# Preview generation.
PREVIEW_MAX_DIMENSION = 1000
