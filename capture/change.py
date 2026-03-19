"""Region-based change detection helpers for captured frames."""

from __future__ import annotations

import numpy as np

DEFAULT_GRID = (4, 4)


def _grayscale_array(image, size):
    """Convert an image into a small grayscale array for fast diff checks."""
    return np.asarray(image.convert("L").resize(size), dtype=np.int16)


def _region_bounds(width, height, rows, cols):
    """Yield pixel bounds for each region in a fixed grid."""
    for row in range(rows):
        top = int(row * height / rows)
        bottom = int((row + 1) * height / rows)
        for col in range(cols):
            left = int(col * width / cols)
            right = int((col + 1) * width / cols)
            yield row, col, left, top, right, bottom


def get_changed_regions(
    previous_image,
    current_image,
    grid=DEFAULT_GRID,
    threshold=6.0,
    thumb_size=(32, 32),
):
    """Return image-space regions whose thumbnail diff exceeds the threshold."""
    if current_image is None:
        return []

    rows, cols = grid
    total_regions = rows * cols
    if previous_image is None:
        regions = []
        for _, _, left, top, right, bottom in _region_bounds(current_image.width, current_image.height, rows, cols):
            regions.append(
                {
                    "left": left,
                    "top": top,
                    "width": max(1, right - left),
                    "height": max(1, bottom - top),
                }
            )
        return regions

    changed = []
    for _, _, left, top, right, bottom in _region_bounds(current_image.width, current_image.height, rows, cols):
        prev_region = previous_image.crop((left, top, right, bottom))
        curr_region = current_image.crop((left, top, right, bottom))
        prev_array = _grayscale_array(prev_region, thumb_size)
        curr_array = _grayscale_array(curr_region, thumb_size)
        mean_diff = np.abs(curr_array - prev_array).mean()
        if mean_diff >= threshold:
            changed.append(
                {
                    "left": left,
                    "top": top,
                    "width": max(1, right - left),
                    "height": max(1, bottom - top),
                }
            )
    return changed


def has_significant_change(previous_image, current_image, threshold=6.0, grid=DEFAULT_GRID):
    """Return True when at least one grid region changes significantly."""
    return bool(get_changed_regions(previous_image, current_image, grid=grid, threshold=threshold))
