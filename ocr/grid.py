from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from PIL import Image

DARK_PIXEL_THRESHOLD = 128
# Real horizontal grid rules on a clean row measure ~0.90-0.98 dark-pixel
# coverage, but some genuine rules (observed down to 0.8497 on a real HDF
# page) render fainter, and a missed rule silently drops that row's entry
# entirely — with nothing downstream to notice or recover it. A too-low
# false-positive rule just becomes a low-quality candidate for the
# human/vision review pass to reject, which is a far cheaper failure mode
# than silent data loss, so this threshold is deliberately biased toward
# recall.
ROW_LINE_FRACTION = 0.8
# Column-rule detection needs the opposite bias: complex die-cut artwork
# (e.g. overlapping wheel/weapon silhouettes on a merged/misdetected row)
# throws off many spurious near-full-height vertical edges once the
# threshold drops much below ~0.9, which explodes the detected column count
# past MAX_PLAUSIBLE_COL_BOUNDS and causes the whole row to be rejected —
# turning a merged-but-salvageable row into a totally silent one. Keep this
# one strict.
COL_LINE_FRACTION = 0.9
CELL_INK_FRACTION = 0.02

# Non-grid content (cover art, logos, body text) can trip the line-fraction
# detector into reporting a "row" with many spurious column edges. Real mini
# sheets have a small, fixed column count per row (base/model cells, see
# RowRegion docstring), so a row reporting far more column rules than that is
# not a real grid row.
MAX_PLAUSIBLE_COL_BOUNDS = 8

# How far below a row band to look for a plain (non-rotated) caption, used for
# large-model layouts where the label isn't a per-row rotated crop (see
# ocr/page.py). In page-image pixels at the render DPI used elsewhere in this
# pipeline (150) — scales roughly with row height, but a fixed cap is simplest.
CAPTION_SEARCH_HEIGHT = 100


@dataclass
class RowRegion:
    """One grid row. Each row is one physical mini: front/back of the model plus
    front/back of its base, laid out as cells within the row (nearly always
    left-to-right in the unrotated page: base-front | model-front | model-back |
    base-back, adjacent to a rotated label further left). Some cells — usually
    the base cells — carry little ink and are not separately identified here;
    what matters is that one row band, regardless of its filled-cell count, is
    one mini. See ocr/page.py for how rows become (unit, loadout, copies)."""

    y0: int
    y1: int
    label_crop: Image.Image
    has_content: bool


def _merge_adjacent(positions: np.ndarray, gap: int = 2) -> list[int]:
    """Collapse a run of adjacent line-pixel indices (e.g. a 2px-thick rule) into
    one boundary position per rule, at the run's midpoint."""
    if len(positions) == 0:
        return []
    groups: list[list[int]] = [[int(positions[0])]]
    for x in positions[1:]:
        if x - groups[-1][-1] <= gap:
            groups[-1].append(int(x))
        else:
            groups.append([int(x)])
    return [int(np.mean(g)) for g in groups]


def _dark_array(image: Image.Image) -> np.ndarray:
    gray = np.asarray(image.convert("L"))
    return gray < DARK_PIXEL_THRESHOLD


def split_into_blocks(image: Image.Image) -> list[Image.Image]:
    """Split a page into independent side-by-side grid blocks, if any.

    Some layouts (e.g. a "chief" model shown on several alternate mounts) place
    two unrelated grids next to each other, not vertically aligned with one
    another. find_row_bands's line-fraction test is computed across the whole
    ink bounding box, so two misaligned blocks dilute each other's line
    fraction below the detection threshold and nothing is found at all. If the
    whole image yields no row bands but clearly has real content, retry by
    splitting at the ink bounding box's horizontal midpoint and recursing —
    this only fires on the whole-image failure case, so single-block pages
    (the common case) are unaffected.
    """
    if find_row_bands(image):
        return [image]

    dark = _dark_array(image)
    ink_cols = np.where(dark.any(axis=0))[0]
    if len(ink_cols) == 0:
        return []  # genuinely blank page

    c0, c1 = int(ink_cols.min()), int(ink_cols.max())
    mid = (c0 + c1) // 2
    # +1 because the two blocks can sit directly adjacent with the shared
    # border rule itself landing exactly on `mid` — PIL crop's right/bottom
    # bound is exclusive, so without this the left block loses that rule.
    left = image.crop((0, 0, mid + 1, image.height))
    right = image.crop((mid, 0, image.width, image.height))
    blocks = [b for b in (left, right) if find_row_bands(b)]
    return blocks


def find_row_bands(image: Image.Image) -> list[tuple[int, int]]:
    """Detect horizontal grid-rule positions and return (y0, y1) bands between
    consecutive rules, in absolute page-image pixel coordinates."""
    dark = _dark_array(image)
    ink_rows = np.where(dark.any(axis=1))[0]
    ink_cols = np.where(dark.any(axis=0))[0]
    if len(ink_rows) == 0 or len(ink_cols) == 0:
        return []
    r0, r1 = int(ink_rows.min()), int(ink_rows.max())
    c0, c1 = int(ink_cols.min()), int(ink_cols.max())
    # Restrict to the ink bounding box on both axes — a full-width row_frac
    # would dilute the fraction wherever the grid doesn't span the whole page.
    box = dark[r0 : r1 + 1, c0 : c1 + 1]
    row_frac = box.mean(axis=1)
    line_positions = np.where(row_frac > ROW_LINE_FRACTION)[0]
    boundaries = _merge_adjacent(line_positions)
    return [(r0 + boundaries[i], r0 + boundaries[i + 1]) for i in range(len(boundaries) - 1)]


def find_col_bounds(image: Image.Image, y0: int, y1: int) -> list[int]:
    """Detect vertical grid-rule positions within a row band, in absolute
    page-image pixel x-coordinates. Restricting to one row band (rather than the
    whole page) keeps this accurate when multiple independent grids or unrelated
    content share a page."""
    dark = _dark_array(image)
    band = dark[y0:y1, :]
    ink_cols = np.where(band.any(axis=0))[0]
    if len(ink_cols) == 0:
        return []
    c0, c1 = int(ink_cols.min()), int(ink_cols.max())
    sub = band[:, c0 : c1 + 1]
    col_frac = sub.mean(axis=0)
    line_positions = np.where(col_frac > COL_LINE_FRACTION)[0]
    boundaries = _merge_adjacent(line_positions)
    return [c0 + b for b in boundaries]


def row_has_content(image: Image.Image, y0: int, y1: int, col_bounds: list[int]) -> bool:
    """Whether any cell in this row band carries more than trace ink. Rows made
    up entirely of near-blank base-cutout cells (no model artwork at all) are
    not real rows — e.g. a page's leftover header/footer band."""
    dark = _dark_array(image)
    margin = 3
    for i in range(len(col_bounds) - 1):
        x0, x1 = col_bounds[i], col_bounds[i + 1]
        sub = dark[y0 + margin : y1 - margin, x0 + margin : x1 - margin]
        if sub.size and sub.mean() > CELL_INK_FRACTION:
            return True
    return False


MIN_CROP_SIZE = 5


def crop_label_region(image: Image.Image, y0: int, y1: int, grid_left_x: int) -> Image.Image | None:
    """Crop the label-text zone to the left of the grid's leftmost rule for one
    row band. The zone is not itself bordered, so its left edge is taken as a
    generous multiple of the grid's own column spacing, clamped to the page.

    Returns None if there's no room to the grid's left to crop at all — this
    happens when column detection is degenerate (e.g. on an imperfectly split
    side-by-side block, see split_into_blocks), and should be treated as "no
    label found" rather than fed to OCR.
    """
    x1 = grid_left_x
    x0 = max(0, x1 - 200)
    if x1 - x0 < MIN_CROP_SIZE or y1 - y0 < MIN_CROP_SIZE:
        return None
    return image.crop((x0, y0, x1, y1))


def crop_caption_below(image: Image.Image, y1: int, bottom_limit: int) -> Image.Image | None:
    """Crop a plain (non-rotated) caption strip below a row band, used for
    large-model layouts whose label is a single caption under the whole stack
    of rows rather than a per-row rotated crop. Bounded by the next row band's
    top (or the page bottom) so it doesn't run into subsequent content.
    Returns None if there's no room below (e.g. the next block starts
    immediately with no gap)."""
    bottom = min(bottom_limit, y1 + CAPTION_SEARCH_HEIGHT)
    if bottom - y1 < MIN_CROP_SIZE:
        return None
    return image.crop((0, y1, image.width, bottom))


def analyze_rows(image: Image.Image) -> list[RowRegion]:
    """Split a rendered mini-sheet page into row bands (one per physical mini —
    see RowRegion), each carrying its label crop. Does not decide unit/loadout
    text or how rows group into copy counts; see ocr/page.py for that."""
    rows = []
    for y0, y1 in find_row_bands(image):
        col_bounds = find_col_bounds(image, y0, y1)
        if len(col_bounds) < 2 or len(col_bounds) > MAX_PLAUSIBLE_COL_BOUNDS:
            continue
        if not row_has_content(image, y0, y1, col_bounds):
            continue
        label_crop = crop_label_region(image, y0, y1, col_bounds[0])
        rows.append(RowRegion(y0=y0, y1=y1, label_crop=label_crop, has_content=True))
    return rows
