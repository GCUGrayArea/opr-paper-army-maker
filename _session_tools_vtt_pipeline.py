from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, r"C:\Users\Gray Morrow\projects\opr-paper-army-maker")
os.chdir(r"C:\Users\Gray Morrow\projects\opr-paper-army-maker")

import numpy as np
from PIL import Image

from index import connect
from ocr.grid import find_col_bounds, find_row_bands, row_has_content, split_into_blocks
from ocr.render import render_page

DB_PATH = "data/index.sqlite"
FACTION = "Human Defense Force"
VTT_DIR = Path("Books/Human Defense Force/VTT")


def content_bbox_crop(image: Image.Image, threshold: int = 245, margin: int = 2) -> Image.Image:
    """Crop to the bounding box of non-near-white content, so a VTT token's
    generous canvas padding and a PDF cell's odd framing don't dilute the hash
    with differing amounts of blank border."""
    arr = np.asarray(image.convert("L"))
    mask = arr < threshold
    if not mask.any():
        return image
    rows = np.where(mask.any(axis=1))[0]
    cols = np.where(mask.any(axis=0))[0]
    r0, r1 = max(0, rows.min() - margin), min(arr.shape[0], rows.max() + margin + 1)
    c0, c1 = max(0, cols.min() - margin), min(arr.shape[1], cols.max() + margin + 1)
    return image.crop((c0, r0, c1, r1))


def ahash(image: Image.Image, size: int = 24) -> np.ndarray:
    """Average hash: tight-crop to content, resize small, grayscale, threshold
    against the mean. Robust to minor scale/crop differences between a VTT
    token and a PDF crop of the same source artwork -- both are
    white-background silhouette art."""
    gray = content_bbox_crop(image).convert("L").resize((size, size))
    arr = np.asarray(gray, dtype=np.float32)
    return (arr > arr.mean()).flatten()


def hash_distance(a: np.ndarray, b: np.ndarray) -> int:
    return int(np.count_nonzero(a != b))


def page_cells(image: Image.Image) -> list[dict]:
    """One dict per detected row: y0, y1, col_bounds, front crop, back crop
    (None if that row's cell layout doesn't look like the expected
    [blank, front, back, blank] pattern)."""
    out = []
    for block in split_into_blocks(image):
        for y0, y1 in find_row_bands(block):
            cb = find_col_bounds(block, y0, y1)
            if not (2 <= len(cb) <= 8):
                continue
            content_cells = []
            for i in range(len(cb) - 1):
                x0, x1 = cb[i], cb[i + 1]
                cell = block.crop((x0, y0, x1, y1))
                arr = np.asarray(cell.convert("L"))
                if arr.size and arr.mean() < 250:  # not blank/near-white
                    # Page content is rotated for the sideways banner-label
                    # layout; VTT tokens are upright -- rotate to match before
                    # any comparison happens (confirmed direction empirically,
                    # see PROGRESS notes).
                    content_cells.append(cell.rotate(90, expand=True))
            front = content_cells[0] if len(content_cells) >= 1 else None
            back = content_cells[1] if len(content_cells) >= 2 else None
            out.append({"y0": y0, "y1": y1, "front": front, "back": back})
    return out


def build_references(conn) -> dict[tuple[str, str, str], dict]:
    """(unit, loadout, color_mode) -> {"front": Image, "back": Image|None,
    "source_file", "source_page"}. Only built for pages where the number of
    detected rows matches the number of DB entries on that page (safe
    positional alignment) -- see PROGRESS notes on why a text-based
    re-match isn't reliable after manual corrections."""
    pages = conn.execute(
        "SELECT DISTINCT source_file, source_page FROM page_entries WHERE faction = ?",
        (FACTION,),
    ).fetchall()

    refs: dict[tuple[str, str, str], dict] = {}
    skipped = []
    for row in pages:
        source_file, source_page = row["source_file"], row["source_page"]
        entries = conn.execute(
            """SELECT unit, loadout, color_mode FROM page_entries
               WHERE faction = ? AND source_file = ? AND source_page = ?
               ORDER BY id ASC""",
            (FACTION, source_file, source_page),
        ).fetchall()

        image = render_page(source_file, source_page - 1)
        cells = page_cells(image)

        if len(cells) != len(entries):
            skipped.append((source_file, source_page, len(cells), len(entries)))
            continue

        for cell, entry in zip(cells, entries):
            key = (entry["unit"], entry["loadout"], entry["color_mode"])
            if key in refs:
                continue  # keep the first (lowest source_page) reference found
            refs[key] = {
                "front": cell["front"],
                "back": cell["back"],
                "source_file": source_file,
                "source_page": source_page,
            }

    print(f"built {len(refs)} references, skipped {len(skipped)} pages (row/entry count mismatch)")
    return refs, skipped


def match_vtt_tokens(refs: dict) -> list[dict]:
    """For each color VTT token, find the best-matching reference by front-image
    hash distance among color_mode='color' refs with a usable front crop."""
    color_refs = {k: v for k, v in refs.items() if k[2] == "color" and v["front"] is not None}
    ref_hashes = {k: ahash(v["front"]) for k, v in color_refs.items()}

    results = []
    color_files = sorted(VTT_DIR.glob("hdf-vtt-fb-1-*.png"), key=lambda p: int(p.stem.rsplit("-", 1)[1]))
    for f in color_files:
        idx = int(f.stem.rsplit("-", 1)[1])
        token_hash = ahash(Image.open(f))
        best_key, best_dist = None, None
        for k, h in ref_hashes.items():
            d = hash_distance(token_hash, h)
            if best_dist is None or d < best_dist:
                best_key, best_dist = k, d
        results.append({"index": idx, "file": f, "match": best_key, "distance": best_dist})
    return results


if __name__ == "__main__":
    conn = connect(DB_PATH)
    refs, skipped = build_references(conn)
    for s in skipped[:20]:
        print("  skipped:", s)
    matches = match_vtt_tokens(refs)
    matches.sort(key=lambda m: m["distance"])
    print("\nBest matches (lowest distance first):")
    for m in matches[:15]:
        print(f"  idx={m['index']:<3} dist={m['distance']:<4} -> {m['match']}")
    print("\nWorst matches (highest distance -- likely no good reference exists):")
    for m in matches[-15:]:
        print(f"  idx={m['index']:<3} dist={m['distance']:<4} -> {m['match']}")
