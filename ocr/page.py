from __future__ import annotations

from dataclasses import dataclass

from PIL import Image

from .grid import (
    MAX_PLAUSIBLE_COL_BOUNDS,
    crop_caption_below,
    crop_label_region,
    find_col_bounds,
    find_row_bands,
    row_has_content,
    split_into_blocks,
)
from .label_ocr import ocr_caption, ocr_label

MIN_LABEL_ALPHA_CHARS = 2


@dataclass
class PageUnit:
    """One (unit, loadout) grouping found on a page, with its physical mini
    count. `text` is the raw OCR'd label, not yet resolved to a canonical
    unit/loadout name — see mapping/ for that."""

    text: str
    copies_on_page: int
    y0: int
    y1: int


def _is_plausible_label(text: str) -> bool:
    return sum(c.isalpha() for c in text) >= MIN_LABEL_ALPHA_CHARS


def analyze_page(image: Image.Image) -> list[PageUnit]:
    """Interpret one rendered page into (label text, copies_on_page) units.
    Handles pages made of multiple independent side-by-side grid blocks (see
    split_into_blocks) by analyzing each block separately."""
    units: list[PageUnit] = []
    for block in split_into_blocks(image):
        units.extend(_analyze_block(block))
    return units


def _analyze_block(image: Image.Image) -> list[PageUnit]:
    """Interpret one single grid block into (label text, copies_on_page) units.

    Most rows carry their own rotated label to the left (bulk/options sheets);
    one mini per row, so consecutive rows sharing identical label text become
    one entry with copies_on_page = row count. Large single-model sheets have
    no per-row label — the model's front/back and base front/back are stacked
    across several unlabeled rows with one plain caption below the whole
    stack, which is one mini (copies_on_page = 1).

    Uses the full (unfiltered) row-band list, not just content-bearing rows —
    a large-model stack's trailing near-blank base cell still needs to count
    as part of the group so the caption search starts below it, not above it.
    """
    bands: list[tuple[int, int, bool, str]] = []
    for y0, y1 in find_row_bands(image):
        col_bounds = find_col_bounds(image, y0, y1)
        if len(col_bounds) < 2 or len(col_bounds) > MAX_PLAUSIBLE_COL_BOUNDS:
            continue
        content = row_has_content(image, y0, y1, col_bounds)
        label_crop = crop_label_region(image, y0, y1, col_bounds[0]) if content else None
        text = ocr_label(label_crop) if label_crop is not None else ""
        bands.append((y0, y1, content, text))

    units: list[PageUnit] = []
    i = 0
    n = len(bands)
    while i < n:
        y0, y1, content, text = bands[i]
        if content and _is_plausible_label(text):
            j = i + 1
            while j < n and bands[j][2] and bands[j][3] == text:
                j += 1
            units.append(PageUnit(text=text, copies_on_page=j - i, y0=y0, y1=bands[j - 1][1]))
            i = j
        else:
            j = i + 1
            while j < n and not (bands[j][2] and _is_plausible_label(bands[j][3])):
                j += 1
            group_y0, group_y1 = y0, bands[j - 1][1]
            bottom_limit = bands[j][0] if j < n else image.height
            caption_crop = crop_caption_below(image, group_y1, bottom_limit)
            caption_text = ocr_caption(caption_crop) if caption_crop is not None else ""
            if _is_plausible_label(caption_text):
                units.append(
                    PageUnit(text=caption_text, copies_on_page=1, y0=group_y0, y1=group_y1)
                )
            i = j
    return units
