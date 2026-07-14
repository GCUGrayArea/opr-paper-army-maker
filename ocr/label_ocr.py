from __future__ import annotations

import shutil

import pytesseract
from PIL import Image

TESSERACT_CONFIG = "--psm 6"

# Fallback for Windows installs where the installer didn't put tesseract.exe on
# PATH for this shell (default UB-Mannheim install location).
_WINDOWS_FALLBACK = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

if shutil.which(pytesseract.pytesseract.tesseract_cmd) is None and shutil.which(
    _WINDOWS_FALLBACK
):
    pytesseract.pytesseract.tesseract_cmd = _WINDOWS_FALLBACK


def _mean_confidence(image: Image.Image) -> tuple[float, str]:
    data = pytesseract.image_to_data(
        image, config=TESSERACT_CONFIG, output_type=pytesseract.Output.DICT
    )
    confidences = [int(c) for c in data["conf"] if str(c) != "-1"]
    text = pytesseract.image_to_string(image, config=TESSERACT_CONFIG).strip()
    if not confidences:
        return -1.0, text
    return sum(confidences) / len(confidences), text


def ocr_label(image: Image.Image) -> str:
    """OCR a rotated label crop. The crop's rotation direction (clockwise vs.
    counter-clockwise) isn't assumed — both are tried and the one Tesseract is
    more confident about wins, since a wrong-direction read produces garbled
    text with much lower per-word confidence rather than a clean failure."""
    best_text = ""
    best_conf = -1.0
    for angle in (90, -90):
        rotated = image.rotate(angle, expand=True)
        conf, text = _mean_confidence(rotated)
        if conf > best_conf:
            best_conf = conf
            best_text = text
    return best_text


def ocr_caption(image: Image.Image) -> str:
    """OCR a plain, non-rotated caption crop (large-model layouts — see
    ocr/page.py)."""
    _, text = _mean_confidence(image)
    return text
