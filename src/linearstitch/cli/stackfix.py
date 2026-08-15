"""Command-line entry point for the stack fixer (replaces ``fixFiles.py``)."""

from __future__ import annotations

import argparse

from ..core.stackfix import fix_stack


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fix missing photos in capture stacks by shifting files forward."
    )
    parser.add_argument(
        "--sourcefolder", required=True, help="Base folder containing all your stacks"
    )
    parser.add_argument("--badstack", required=True, help="The name of the bad stack")
    parser.add_argument(
        "--num", required=True, type=int, help="Number of bad images in the bad stack"
    )
    args = parser.parse_args()

    fix_stack(args.sourcefolder, args.badstack, args.num)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
