import os
import warnings
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from PIL import Image
from skimage.metrics import structural_similarity as ssim

VIEWPORTS = {
    "desktop": {"width": 1280, "height": 720},
    "mobile": {"width": 375, "height": 667},
}


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
        error_message = "Image sizes do not match"
        raise ValueError(error_message)

    score, _diff = ssim(actual_np, expected_np, full=True)
    return score >= 0.9, score


def assert_matches_snapshot(
    page,
    page_name,
    viewport_breakpoint: str | None = None,
    clip: dict | None = None,
):
    regenerate = os.getenv("E2E_REGENERATE_SNAPSHOTS", "false").lower() == "true"

    viewports = [(viewport_breakpoint, VIEWPORTS[viewport_breakpoint])] if viewport_breakpoint else VIEWPORTS.items()
    screenshot_opts: dict[str, Any] = {"full_page": True}

    if clip:
        screenshot_opts["full_page"] = False
        screenshot_opts["clip"] = clip

    for label, viewport in viewports:
        actual_path = f"snapshots/{page_name}_{label}_actual.png"
        expected_path = f"snapshots/{page_name}_{label}_expected.png"

        page.set_viewport_size(viewport)
        page.screenshot(path=actual_path, **screenshot_opts)

        if not os.path.exists(expected_path):
            Path(actual_path).replace(expected_path)
            if regenerate:
                return

            warnings.warn("Expected snapshot not found — generating from current page.", stacklevel=2)
            return

        result, score = compare_snapshot(actual_path, expected_path)

        if not result:
            if regenerate:
                Path(actual_path).replace(expected_path)
                continue

            pytest.fail(
                f"\n{page_name} on {label} has changed ({score}). Please check snapshots/{page_name}_{label}_actual.png and update snapshots/{page_name}_{label}_expected.png if happy.",
            )
