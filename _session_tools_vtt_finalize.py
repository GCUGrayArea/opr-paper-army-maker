from __future__ import annotations

import os
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, r"C:\Users\Gray Morrow\projects\opr-paper-army-maker")
os.chdir(r"C:\Users\Gray Morrow\projects\opr-paper-army-maker")

from index import connect
from vtt_identifications import IDENTIFICATIONS
from vtt_pipeline import build_references, DB_PATH, VTT_DIR

OUT_DIR = Path("Books/Human Defense Force/VTT_identified")
FRONT_DIR = OUT_DIR / "front"
BACK_DIR = OUT_DIR / "back"


def safe(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "_", name)


def main():
    FRONT_DIR.mkdir(parents=True, exist_ok=True)
    BACK_DIR.mkdir(parents=True, exist_ok=True)

    conn = connect(DB_PATH)
    refs, _ = build_references(conn)

    front_count = back_count = 0
    for idx, (unit, loadout, confident) in IDENTIFICATIONS.items():
        tag = "" if confident else " (GUESS)"
        base = safe(f"{unit} - {loadout}{tag}")

        color_src = VTT_DIR / f"hdf-vtt-fb-1-{idx}.png"
        bw_src = VTT_DIR / f"hdf-vtt-fb-bw-{idx}.png"
        shutil.copy(color_src, FRONT_DIR / f"{base} - color [hdf-vtt-fb-1-{idx}].png")
        shutil.copy(bw_src, FRONT_DIR / f"{base} - bw [hdf-vtt-fb-bw-{idx}].png")
        front_count += 2

        if not confident:
            continue
        for color_mode, suffix in (("color", "1"), ("bw", "bw")):
            ref = refs.get((unit, loadout, color_mode))
            if ref is None or ref["back"] is None:
                print(f"  no back-view found for ({unit}, {loadout}, {color_mode}) -- idx {idx}")
                continue
            out_name = f"{base} - back - {color_mode} [from hdf-vtt-fb-{suffix}-{idx} match].png"
            ref["back"].save(BACK_DIR / out_name)
            back_count += 1

    print(f"\nwrote {front_count} front images, {back_count} back-view crops")
    print(f"to {OUT_DIR}")


if __name__ == "__main__":
    main()
