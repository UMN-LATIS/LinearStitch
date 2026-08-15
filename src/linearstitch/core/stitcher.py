"""1-D (single horizontal row) image stitcher.

A faithful, typed refactor of the original ``stitcher.Stitcher``. The alignment
maths, seam placement and compositing are byte-for-byte equivalent to the
original; only structure, logging and typing have changed.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

import cv2
import numpy as np

from . import constants
from .rotation import rotate_and_crop
from .vignette import remove_vignette

ProgressCallback = Callable[[int, int], None]
MessageCallback = Callable[[str], None]


class Stitcher:
    """Stitch a horizontal sequence of overlapping images into one panorama."""

    def __init__(
        self,
        overlap: float,
        message_callback: MessageCallback | None = None,
    ) -> None:
        self.overlap = overlap
        self.max_offset = 0
        self._message_callback = message_callback
        self._log_file = None

    # -- logging ----------------------------------------------------------

    def _log(self, message: str) -> None:
        if self._log_file is not None:
            self._log_file.write(message + "\n")
        if self._message_callback is not None:
            self._message_callback(message)
        else:
            print(message)

    # -- alignment --------------------------------------------------------

    def calculate_offset(
        self, img1: np.ndarray, img2: np.ndarray, enable_mask: bool
    ) -> tuple[float, float]:
        """Return the ``(x, y)`` offset aligning ``img2`` onto ``img1``."""

        overlap_px = img2.shape[1] * self.overlap

        sf = constants.SCALE_FACTOR_1D
        i1 = cv2.cvtColor(
            cv2.resize(img1[:, -int(overlap_px):, :], (0, 0), fx=sf, fy=sf),
            cv2.COLOR_BGR2GRAY,
        )
        i2 = cv2.cvtColor(
            cv2.resize(img2[:, : int(overlap_px), :], (0, 0), fx=sf, fy=sf),
            cv2.COLOR_BGR2GRAY,
        )

        if enable_mask:
            height, width = i1.shape[:2]
            mask = np.zeros(i1.shape[:2], np.uint8)
            rounded = round(height / 4)
            mask[rounded : height - rounded, 0:width] = 255
        else:
            mask = None

        sift = cv2.SIFT_create(nfeatures=constants.MAX_FEATURES)
        self._log("\t- Finding keypoints and descriptors for image 1")
        kp1, des1 = sift.detectAndCompute(i1, mask)
        self._log("\t- Finding keypoints and descriptors for image 2")
        kp2, des2 = sift.detectAndCompute(i2, mask)

        self._log("\t- Finding matches")
        flann = cv2.FlannBasedMatcher(
            {"algorithm": 0, "trees": 5}, {"checks": constants.FLANN_CHECKS}
        )
        matches = flann.knnMatch(des1, des2, k=2)

        good_matches = [
            m for m, n in matches if m.distance < constants.LOWE_RATIO * n.distance
        ]
        src_pts = np.float32(
            [kp1[match.queryIdx].pt for match in good_matches]
        ).reshape(-1, 1, 2)
        dst_pts = np.float32(
            [kp2[match.trainIdx].pt for match in good_matches]
        ).reshape(-1, 1, 2)

        x_offset = int(np.median([elem[0][0] for elem in np.subtract(src_pts, dst_pts)]))
        y_offset = int(np.median([elem[0][1] for elem in np.subtract(src_pts, dst_pts)]))

        inv_sf = 1 / sf
        self._log(f"\t- X Offset found: {x_offset * inv_sf} px")
        self._log(f"\t- Y Offset found: {y_offset * inv_sf} px")
        return (x_offset * inv_sf, y_offset * inv_sf)

    # -- compositing ------------------------------------------------------

    def stitch_images(
        self, img1: np.ndarray, img2: np.ndarray, enable_mask: bool
    ) -> np.ndarray:
        """Stitch ``img2`` to the right of ``img1`` and return the composite."""

        x_offset, y_offset = self.calculate_offset(img1, img2, enable_mask)

        x_seam = int(img1.shape[1] - (img2.shape[1] * self.overlap * 0.5) + x_offset)
        partial_image = int(img2.shape[1] * self.overlap * 0.5)

        self.max_offset = max(self.max_offset, y_offset)

        width = x_seam + (img2.shape[1] - partial_image)
        height = img2.shape[0] + abs(int(self.max_offset))

        if y_offset < 0.0:
            comp_img = np.zeros((height + int(abs(y_offset)), width, 3), np.uint8)
            self.max_offset += int(abs(y_offset))
            comp_img[
                int(abs(y_offset)) : img1.shape[0] + int(abs(y_offset)), 0:x_seam
            ] = img1[0 : img1.shape[0], 0:x_seam]
            comp_img[
                0 : img2.shape[0], x_seam : (x_seam + img2.shape[1] - partial_image)
            ] = img2[0 : img2.shape[0], partial_image : img2.shape[1]]
        else:
            comp_img = np.zeros((height, width, 3), np.uint8)
            comp_img[0 : img1.shape[0], 0:x_seam] = img1[0 : img1.shape[0], 0:x_seam]
            comp_img[
                int(y_offset) : img2.shape[0] + int(y_offset),
                x_seam : (x_seam + img2.shape[1] - partial_image),
            ] = img2[0 : img2.shape[0], partial_image : img2.shape[1]]

        return comp_img

    # -- batch ------------------------------------------------------------

    def stitch_file_list(
        self,
        images: Sequence[str],
        output_path: str,
        scaled_preview_file: str,
        log_file: str,
        callback: ProgressCallback | None,
        enable_mask: bool,
        scale_image: str,
        vertical_core: bool,
        remove_vignette_flag: bool,
        vignette_magic_number: float = 1.1,
        rotate_image: bool = False,
        crop_image: bool = False,
    ) -> None:
        """Stitch ``images`` left-to-right, writing the result and a preview."""

        with open(log_file, "w") as handle:
            self._log_file = handle
            try:
                self._stitch_run(
                    images,
                    output_path,
                    scaled_preview_file,
                    callback,
                    enable_mask,
                    scale_image,
                    vertical_core,
                    remove_vignette_flag,
                    vignette_magic_number,
                    rotate_image,
                    crop_image,
                )
            finally:
                self._log_file = None

    def _stitch_run(
        self,
        images: Sequence[str],
        output_path: str,
        scaled_preview_file: str,
        callback: ProgressCallback | None,
        enable_mask: bool,
        scale_image: str,
        vertical_core: bool,
        remove_vignette_flag: bool,
        vignette_magic_number: float,
        rotate_image: bool,
        crop_image: bool,
    ) -> None:
        composite = None

        self._log("Beginning batch processing for: " + output_path)
        self._log("Masking is: " + str(enable_mask))
        if scale_image:
            self._log("Scale File Is: " + scale_image)

        first_image = True
        for i in range(0, len(images) - 1):
            if i == 0:
                img1 = cv2.imread(images[i])
                img2 = cv2.imread(images[i + 1])
                if remove_vignette_flag:
                    img1 = remove_vignette(img1, vignette_magic_number)
                    img2 = remove_vignette(img2, vignette_magic_number)
                if vertical_core:
                    img1 = cv2.rotate(img1, cv2.ROTATE_90_COUNTERCLOCKWISE)
                    img2 = cv2.rotate(img2, cv2.ROTATE_90_COUNTERCLOCKWISE)
            else:
                img1 = composite
                img2 = cv2.imread(images[i + 1])
                if remove_vignette_flag:
                    img2 = remove_vignette(img2, vignette_magic_number)
                if vertical_core:
                    img2 = cv2.rotate(img2, cv2.ROTATE_90_COUNTERCLOCKWISE)

            try:
                self._log(f"Stitching Image {images[i]} and {images[i + 1]}")
                composite = self.stitch_images(img1, img2, enable_mask)
                if first_image:
                    first_image = False
                    if scale_image:
                        scale_img = cv2.imread(scale_image)
                        h1, w1 = scale_img.shape[:2]
                        h2, w2 = composite.shape[:2]
                        vis = np.zeros((max(h1, h2), w1 + w2, 3), np.uint8)
                        vis[:h1, :w1] = scale_img
                        vis[:h2, w1 : w1 + w2] = composite
                        composite = vis
                self._log("Size of Composite: " + str(composite.shape))
                if callback:
                    callback(1, round(i / len(images) * 100))
            except Exception as e:  # noqa: BLE001 — preserve original tolerant behaviour
                print(e)
                self._log(f"Error stitching {images[i]} and {images[i + 1]}")

        if crop_image and not rotate_image:
            self._log("Cropping Image")
            composite = composite[
                int(self.max_offset) : (composite.shape[0] - int(self.max_offset)),
                0 : composite.shape[1],
            ]

        if rotate_image:
            self._log("Rotating Image")
            composite = rotate_and_crop(composite, log=self._log)

        self._log("Size of Composite: " + str(composite.shape))
        if composite is not None:
            cv2.imwrite(output_path, composite)

        if (
            composite.shape[0] > constants.PREVIEW_MAX_DIMENSION
            or composite.shape[1] > constants.PREVIEW_MAX_DIMENSION
        ):
            self._log("Writing preview image")
            if composite.shape[0] > composite.shape[1]:
                scale_percent = constants.PREVIEW_MAX_DIMENSION / composite.shape[0] * 100
            else:
                scale_percent = constants.PREVIEW_MAX_DIMENSION / composite.shape[1] * 100
            width = int(composite.shape[1] * scale_percent / 100)
            height = int(composite.shape[0] * scale_percent / 100)
            dim = (width, height)
            resized = cv2.resize(composite, dim, interpolation=cv2.INTER_AREA)
            cv2.imwrite(scaled_preview_file, resized)

        self._log("Finished")
        if callback:
            callback(1, 100)
