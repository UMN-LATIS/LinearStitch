"""Console / GUI entry point for LinearStitch."""

from __future__ import annotations

import multiprocessing
import sys


def main() -> int:
    multiprocessing.freeze_support()
    from .app import run

    return run()


if __name__ == "__main__":
    sys.exit(main())
