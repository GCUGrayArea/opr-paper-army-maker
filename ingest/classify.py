from __future__ import annotations

import numpy as np
from PIL import Image

COLOR_MODE_COLOR = "color"
COLOR_MODE_BW = "bw"

# A pixel counts as "colorful" once its max-min RGB channel spread exceeds this.
PIXEL_CHROMA_THRESHOLD = 8
# A page is "color" once more than this fraction of pixels are colorful.
DEFAULT_COLORFUL_FRACTION_THRESHOLD = 0.003


def classify_color_mode(
    image: Image.Image, threshold: float = DEFAULT_COLORFUL_FRACTION_THRESHOLD
) -> tuple[str, float]:
    """Classify a rendered page image as color or black-and-white.

    Score is the fraction of pixels whose RGB channel spread (max-min) exceeds
    PIXEL_CHROMA_THRESHOLD. A plain mean-chroma-over-the-page metric is diluted
    by mostly-white page backgrounds and fails to separate color from BW pages;
    counting colorful pixels directly does not have that problem.
    """
    arr = np.asarray(image, dtype=np.int16)
    chroma = arr.max(axis=2) - arr.min(axis=2)
    score = float((chroma > PIXEL_CHROMA_THRESHOLD).mean())
    mode = COLOR_MODE_COLOR if score > threshold else COLOR_MODE_BW
    return mode, score
