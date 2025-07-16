import os
import warnings
from pathlib import Path

import numpy as np
import pytest
from PIL import Image
from skimage.metrics import structural_similarity as ssim


class ImageSizeMismatchError(ValueError):
    def __init__(self):
        super().__init__("Image sizes do not match")


def compare_snapshot(actual_path, expected_path):
    actual_image = Image.open(actual_path).convert("L")
    expected_image = Image.open(expected_path).convert("L")

    min_width = min(actual_image.width, expected_image.width)
    min_height = min(actual_image.height, expected_image.height)

    actual_cropped = actual_image.crop((0, 0, min_width, min_height))
    expected_cropped = expected_image.crop((0, 0, min_width, min_height))

    actual_np = np.array(actual_cropped, dtype=np.uint8)
    expected_np = np.array(expected_cropped, dtype=np.uint8)

    if actual_np.shape != expected_np.shape:
        warnings.warn(f"Actual shape: {actual_np.shape}", stacklevel=2)
        warnings.warn(f"Expected shape: {expected_np.shape}", stacklevel=2)
        raise ImageSizeMismatchError

    score, _diff = ssim(actual_np, expected_np, full=True)
    return score >= 0.9, score


def assert_matches_snapshot(page, page_name):
    actual_path = f"snapshots/{page_name}_actual.png"
    expected_path = f"snapshots/{page_name}_expected.png"

    page.set_viewport_size({"width": 1280, "height": 720})
    page.screenshot(path=actual_path, full_page=True)

    if not os.path.exists(expected_path):
        warnings.warn("Expected snapshot not found — generating from current page.", stacklevel=2)
        Path(actual_path).replace(expected_path)
        return

    page.screenshot(path=actual_path, full_page=True)
    result, score = compare_snapshot(actual_path, expected_path)

    if not result:
        pytest.fail(
            f"\n{page_name} has changed ({score}). Please check screenshots/actual_{page_name}.png and update screenshots/expected_{page_name}.png if happy.",
        )
