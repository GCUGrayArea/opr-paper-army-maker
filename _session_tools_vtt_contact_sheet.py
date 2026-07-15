from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw

CELL_W = 320
CELL_H = 420
CAPTION_H = 30


def flatten(image: Image.Image) -> Image.Image:
    if image.mode != "RGBA":
        return image.convert("RGB")
    bg = Image.new("RGB", image.size, "white")
    bg.paste(image, mask=image.split()[3])
    return bg


def fit(image: Image.Image, w: int, h: int) -> Image.Image:
    img = image.copy()
    img.thumbnail((w, h))
    canvas = Image.new("RGB", (w, h), "white")
    x = (w - img.width) // 2
    y = (h - img.height) // 2
    canvas.paste(img, (x, y))
    return canvas


def make_sheet(indices: list[int], vtt_dir: Path, cols: int, out_path: Path) -> Path:
    thumbs = []
    for i in indices:
        img = flatten(Image.open(vtt_dir / f"hdf-vtt-fb-1-{i}.png"))
        thumbs.append((i, fit(img, CELL_W, CELL_H)))

    rows = -(-len(thumbs) // cols)
    sheet = Image.new("RGB", (cols * CELL_W, rows * (CELL_H + CAPTION_H)), "white")
    draw = ImageDraw.Draw(sheet)
    for n, (i, img) in enumerate(thumbs):
        r, c = divmod(n, cols)
        x, y = c * CELL_W, r * (CELL_H + CAPTION_H)
        sheet.paste(img, (x, y))
        draw.rectangle([x, y + CELL_H, x + CELL_W, y + CELL_H + CAPTION_H], fill="black")
        draw.text((x + 8, y + CELL_H + 6), f"idx {i}", fill="white")
    sheet.save(out_path)
    return out_path


if __name__ == "__main__":
    vtt_dir = Path(sys.argv[1])
    start = int(sys.argv[2])
    end = int(sys.argv[3])
    out_path = Path(sys.argv[4])
    cols = int(sys.argv[5]) if len(sys.argv) > 5 else 4
    make_sheet(list(range(start, end + 1)), vtt_dir, cols, out_path)
