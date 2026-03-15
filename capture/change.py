"""Basic thumbnail-based change detection for captured frames."""

import numpy as np


def has_significant_change(previous_image, current_image, threshold=12.0, size=(64, 64)):
    """Compare image thumbnails and return True when the mean pixel diff is high."""
    if previous_image is None or current_image is None:
        return True

    prev_thumb = previous_image.convert("L").resize(size)
    curr_thumb = current_image.convert("L").resize(size)
    prev_array = np.asarray(prev_thumb, dtype=np.int16)
    curr_array = np.asarray(curr_thumb, dtype=np.int16)
    mean_diff = np.abs(curr_array - prev_array).mean()
    return mean_diff >= threshold
