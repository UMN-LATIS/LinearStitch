"""Application branding.

The original project shipped two PyInstaller specs (``LinearStitch.spec`` and
``LinearSnap.spec``) that built the *same* code under two names. Branding is now
data-driven: the active brand is selected from the executable / environment so a
single codebase can ship under either name.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class Brand:
    """A user-facing product identity."""

    name: str
    window_title: str


LINEAR_STITCH = Brand(name="LinearStitch", window_title="LinearStitch")
LINEAR_SNAP = Brand(name="LinearSnap", window_title="LinearSnap")

_BRANDS = {
    "linearstitch": LINEAR_STITCH,
    "linearsnap": LINEAR_SNAP,
}


def current_brand() -> Brand:
    """Resolve the active brand.

    Resolution order:
    1. ``LINEARSTITCH_BRAND`` environment variable.
    2. The executable / script base name (e.g. a ``LinearSnap`` bundle).
    3. Default to :data:`LINEAR_STITCH`.
    """

    env = os.environ.get("LINEARSTITCH_BRAND", "").strip().lower()
    if env in _BRANDS:
        return _BRANDS[env]

    exe = os.path.basename(sys.argv[0] if sys.argv else "").lower()
    for key, brand in _BRANDS.items():
        if key in exe:
            return brand

    return LINEAR_STITCH
