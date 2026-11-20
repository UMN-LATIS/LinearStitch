"""GPU-accelerated vignette correction (OpenCL).

Extracted verbatim from ``Stitcher.removeVignette`` to preserve numerical
output. The OpenCL kernel and clipping/rounding behaviour are unchanged.
"""

from __future__ import annotations

import cv2
import numpy as np

_MASK_KERNEL_TEMPLATE = """
__kernel void compute_mask(__global float *mask, int rows, int cols, int center_x, int center_y)
{{
    int row = get_global_id(1);
    int col = get_global_id(0);
    if (row < rows && col < cols)
        mask[row * cols + col] = 1 + {magic}*(pow((float)(row - center_y), 2) + pow((float)(col - center_x), 2))/(rows*rows + cols*cols);
}}
"""


def remove_vignette(img: np.ndarray, vignette_magic_number: float) -> np.ndarray:
    """Return ``img`` with a radial vignette correction applied."""

    import pyopencl as cl

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    rows, cols = gray.shape
    center = (cols // 2, rows // 2)
    mask = np.zeros(gray.shape, dtype=np.float32)

    mask_kernel = _MASK_KERNEL_TEMPLATE.format(magic=vignette_magic_number)

    platform = cl.get_platforms()
    my_gpu_devices = platform[0].get_devices(device_type=cl.device_type.GPU)
    ctx = cl.Context(devices=my_gpu_devices)
    queue = cl.CommandQueue(ctx)

    mask_buf = cl.Buffer(ctx, cl.mem_flags.WRITE_ONLY, mask.nbytes)

    prg = cl.Program(ctx, mask_kernel).build()
    prg.compute_mask(
        queue,
        (cols, rows),
        None,
        mask_buf,
        np.int32(rows),
        np.int32(cols),
        np.int32(center[0]),
        np.int32(center[1]),
    )

    cl.enqueue_copy(queue, mask, mask_buf)

    corrected = np.clip(img * mask[:, :, np.newaxis], 0, 255)
    return np.rint(corrected).astype(np.uint8)
