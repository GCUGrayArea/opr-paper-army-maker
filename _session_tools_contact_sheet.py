from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, r"C:\Users\Gray Morrow\projects\opr-paper-army-maker")

from PIL import Image, ImageDraw

from ocr.render import render_page

CELL_WIDTH = 480
CAPTION_H = 28


def make_contact_sheet(pages: list[tuple[str, int]], cols: int, out_path: Path) -> Path:
    """pages: list of (source_file, source_page) 1-indexed. Renders each, scales
    to CELL_WIDTH, tiles into a grid with a filename/page caption per cell."""
    thumbs = []
    for source_file, source_page in pages:
        img = render_page(source_file, source_page - 1)
        ratio = CELL_WIDTH / img.width
        img = img.resize((CELL_WIDTH, int(img.height * ratio)))
        thumbs.append((Path(source_file).name, source_page, img))

    rows = -(-len(thumbs) // cols)
    cell_h = max(t[2].height for t in thumbs) + CAPTION_H
    sheet = Image.new("RGB", (cols * CELL_WIDTH, rows * cell_h), "white")
    draw = ImageDraw.Draw(sheet)
    for i, (fname, pg, img) in enumerate(thumbs):
        r, c = divmod(i, cols)
        x, y = c * CELL_WIDTH, r * cell_h
        sheet.paste(img, (x, y))
        draw.rectangle([x, y + img.height, x + CELL_WIDTH, y + cell_h], fill="black")
        draw.text((x + 4, y + img.height + 6), f"{fname} p.{pg}", fill="white")
    sheet.save(out_path)
    return out_path


if __name__ == "__main__":
    pdf = "Books/Human Defense Force/Human_Defense_Force_-_Color_A.pdf"
    pages = [(pdf, p) for p in range(1, 10)]
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("test_sheet.png")
    make_contact_sheet(pages, 3, out)
