from __future__ import annotations

import io

import fitz
from PIL import Image

DEFAULT_DPI = 150


def render_page(pdf_path: str, page_number: int, dpi: int = DEFAULT_DPI) -> Image.Image:
    """Render one page (0-indexed) of a PDF to an RGB PIL image."""
    with fitz.open(pdf_path) as doc:
        pix = doc[page_number].get_pixmap(dpi=dpi)
        return Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")


def page_count(pdf_path: str) -> int:
    with fitz.open(pdf_path) as doc:
        return doc.page_count
