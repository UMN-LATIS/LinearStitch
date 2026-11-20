"""Image straightening + cropping using libvips (pyvips).

Extracted from ``Stitcher.rotateAndCrop``. ``pyvips`` is imported lazily so the
package still imports on systems without libvips installed.
"""

from __future__ import annotations

from collections.abc import Callable

import cv2
import numpy as np


def rotate_and_crop(image: np.ndarray, log: Callable[[str], None] | None = None) -> np.ndarray:
    """Straighten ``image`` based on its dominant contour and centre-crop it."""

    import pyvips

    emit = log or print

    scale_percent = 2.5  # percent of original size
    width = int(image.shape[1] * scale_percent / 100)
    height = int(image.shape[0] * scale_percent / 100)
    dim = (width, height)

    resized = cv2.resize(image, dim, interpolation=cv2.INTER_AREA)

    # Preserved debug artifact written by the original implementation.
    cv2.imwrite("scaled_image.jpg", resized)

    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    (_thresh, black_and_white) = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)

    blurred = cv2.GaussianBlur(black_and_white, (5, 5), 0)

    contours, _ = cv2.findContours(blurred, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    max_area = 0
    largest_contour = None
    for contour in contours:
        area = cv2.contourArea(contour)
        if area > max_area:
            max_area = area
            largest_contour = contour

    angle = 0.0
    if largest_contour is not None:
        (_x, _y), (_ma_minor, _ma_major), angle = cv2.fitEllipse(largest_contour)

    vips_image = pyvips.Image.new_from_array(image[..., ::-1])
    vips_image = vips_image.rotate(
        (90 - angle), interpolate=pyvips.Interpolate.new("bicubic")
    )

    emit(str(angle))

    crop_height = int(image.shape[1] * np.abs(np.sin(np.radians(90 - angle))))
    vips_image = vips_image.crop(
        0, crop_height, vips_image.width, vips_image.height - (crop_height * 2)
    )

    result = vips_image.numpy()
    return result[..., ::-1]
