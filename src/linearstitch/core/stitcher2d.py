"""2-D (grid) image stitcher.

A faithful, typed refactor of the original ``twodstitcher.TwoDStitcher``. The
alignment maths and compositing for both ``vertical`` and ``horizontal`` passes
are preserved exactly, including the Windows brute-force matcher fallback.
"""

from __future__ import annotations

import platform
from collections.abc import Callable, Sequence

import cv2
import numpy as np

from . import constants

ProgressCallback = Callable[[int, int], None]


class TwoDStitcher:
    """Stitch a 2-D grid of overlapping images via vertical then horizontal passes."""

    def __init__(self) -> None:
        self.max_offset = 0

    def calculate_offset(
        self, img1: np.ndarray, img2: np.ndarray, orientation: str
    ) -> tuple[float, float]:
        sf = constants.SCALE_FACTOR_2D
        overlap = constants.OVERLAP_2D

        if orientation == "vertical":
            overlap_px = img2.shape[0] * overlap
            i1 = cv2.cvtColor(
                cv2.resize(img1[-int(overlap_px):, :, :], (0, 0), fx=sf, fy=sf),
                cv2.COLOR_BGR2GRAY,
            )
            i2 = cv2.cvtColor(
                cv2.resize(img2[: int(overlap_px), :, :], (0, 0), fx=sf, fy=sf),
                cv2.COLOR_BGR2GRAY,
            )
        else:
            overlap_px = img2.shape[1] * overlap
            i1 = cv2.cvtColor(
                cv2.resize(img1[:, -int(overlap_px):, :], (0, 0), fx=sf, fy=sf),
                cv2.COLOR_BGR2GRAY,
            )
            i2 = cv2.cvtColor(
                cv2.resize(img2[:, : int(overlap_px), :], (0, 0), fx=sf, fy=sf),
                cv2.COLOR_BGR2GRAY,
            )

        sift = cv2.SIFT_create(nfeatures=constants.MAX_FEATURES)
        print("\t- Finding keypoints and descriptors for image 1")
        kp1, des1 = sift.detectAndCompute(i1, None)
        print("\t- Finding keypoints and descriptors for image 2")
        kp2, des2 = sift.detectAndCompute(i2, None)

        print("\t- Finding matches")
        if platform.system() != "Windows":
            flann = cv2.FlannBasedMatcher(
                {"algorithm": 0, "trees": 5}, {"checks": constants.FLANN_CHECKS}
            )
            matches = flann.knnMatch(des1, des2, k=2)
        else:
            bf_match = cv2.BFMatcher(cv2.NORM_L2)
            matches = bf_match.knnMatch(des1, des2, k=2)

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
        print(f"\t- X Offset found: {x_offset * inv_sf} px")
        print(f"\t- Y Offset found: {y_offset * inv_sf} px")
        return (x_offset * inv_sf, y_offset * inv_sf)

    def stitch_images(
        self, img1: np.ndarray, img2: np.ndarray, orientation: str
    ) -> np.ndarray:
        x_offset, y_offset = self.calculate_offset(img1, img2, orientation)
        overlap = constants.OVERLAP_2D

        if orientation == "vertical":
            seam = int(img1.shape[0] - (img2.shape[0] * overlap * 0.5) + y_offset)
            partial_image = int(img2.shape[0] * overlap * 0.5)

            self.max_offset = max(self.max_offset, x_offset)
            height = seam + (img2.shape[0] - partial_image)
            width = img2.shape[1] + abs(int(self.max_offset))
            if x_offset < 0.0:
                comp_img = np.zeros((height, width + int(abs(x_offset)), 3), np.uint8)
                self.max_offset += int(abs(x_offset))
                comp_img[
                    0:seam, int(abs(x_offset)) : img1.shape[1] + int(abs(x_offset))
                ] = img1[0:seam, 0 : img1.shape[1]]
                comp_img[
                    seam : (seam + img2.shape[0] - partial_image), 0 : img2.shape[1]
                ] = img2[partial_image : img2.shape[0], 0 : img2.shape[1]]
            else:
                comp_img = np.zeros((height, width, 3), np.uint8)
                comp_img[0:seam, 0 : img1.shape[1]] = img1[0:seam, 0 : img1.shape[1]]
                comp_img[
                    seam : (seam + img2.shape[0] - partial_image),
                    int(x_offset) : img2.shape[1] + int(x_offset),
                ] = img2[partial_image : img2.shape[0], 0 : img2.shape[1]]
        else:
            seam = int(img1.shape[1] - (img2.shape[1] * overlap * 0.5) + x_offset)
            partial_image = int(img2.shape[1] * overlap * 0.5)

            self.max_offset = max(self.max_offset, y_offset)
            width = seam + (img2.shape[1] - partial_image)
            height = max(img1.shape[0], img2.shape[0] + abs(int(self.max_offset)))
            if y_offset < 0.0:
                comp_img = np.zeros((height + int(abs(y_offset)), width, 3), np.uint8)
                self.max_offset += int(abs(y_offset))
                comp_img[
                    int(abs(y_offset)) : img1.shape[0] + int(abs(y_offset)), 0:seam
                ] = img1[0 : img1.shape[0], 0:seam]
                comp_img[
                    0 : img2.shape[0], seam : (seam + img2.shape[1] - partial_image)
                ] = img2[0 : img2.shape[0], partial_image : img2.shape[1]]
            else:
                comp_img = np.zeros((height, width, 3), np.uint8)
                comp_img[0 : img1.shape[0], 0:seam] = img1[0 : img1.shape[0], 0:seam]
                comp_img[
                    int(y_offset) : img2.shape[0] + int(y_offset),
                    seam : (seam + img2.shape[1] - partial_image),
                ] = img2[0 : img2.shape[0], partial_image : img2.shape[1]]

        return comp_img

    def stitch_file_list(
        self,
        images: Sequence[str],
        output_path: str,
        orientation: str,
        callback: ProgressCallback | None,
    ) -> None:
        composite = None
        for i in range(0, len(images) - 1):
            if i == 0:
                img1 = cv2.imread(images[i])
                img2 = cv2.imread(images[i + 1])
            else:
                img1 = composite
                img2 = cv2.imread(images[i + 1])

            print(f"Stitching Image {i} and {i + 1}")
            composite = self.stitch_images(img1, img2, orientation)
            print(f"SIZE OF COMPOSITE: {composite.shape}")
            if callback:
                callback(1, round(i / len(images) * 100))

        cv2.imwrite(output_path, composite)
        if callback:
            callback(1, 100)
