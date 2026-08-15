"""Blur detection and removal via the variance of the Laplacian."""

from __future__ import annotations

import os
from collections.abc import Callable

import cv2
from imutils import paths

MessageCallback = Callable[[str], None]


def variance_of_laplacian(image) -> float:
    """Return the focus measure (variance of the Laplacian) of a grayscale image."""

    return cv2.Laplacian(image, cv2.CV_64F).var()


def remove_blurry_images(
    path: str, focus_threshold: float, echo: MessageCallback | None = None
) -> None:
    """Rename images in ``path`` whose focus measure is below ``focus_threshold``.

    Blurry images are renamed with a ``_blurry`` suffix, preserving the original
    behaviour exactly.
    """

    emit = echo or print
    for image_path in sorted(paths.list_images(path)):
        image = cv2.imread(image_path)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        fm = variance_of_laplacian(gray)

        if fm > focus_threshold:
            emit(f"{image_path} - Not Blurry: {fm}")

        if fm < focus_threshold:
            emit(f"{image_path} - Blurry: {fm}")
            os.rename(image_path, image_path + "_blurry")
