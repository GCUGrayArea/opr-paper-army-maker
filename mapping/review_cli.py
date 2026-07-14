from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

from index import PageEntry, confirm_entry, connect, get_pending_entries, reject_entry
from ocr.render import render_page

THUMBNAIL_MAX_SIZE = (900, 1200)
EDITABLE_FIELDS = ("unit", "loadout", "copies_on_page", "color_mode")


def _open_page_preview(entry: PageEntry) -> Path:
    """Render the entry's source page, downsize it for a quick glance, save to
    a temp file, and open it in the OS default image viewer. One temp file per
    (source_file, source_page) rather than per entry, since bulk/options sheets
    put many entries on the same page."""
    image = render_page(entry.source_file, entry.source_page - 1)
    image.thumbnail(THUMBNAIL_MAX_SIZE)
    fd, path_str = tempfile.mkstemp(suffix=".png", prefix="mini_sheet_review_")
    os.close(fd)
    path = Path(path_str)
    image.save(path)
    os.startfile(path)  # noqa: Windows-only tool, matches this project's dev platform.
    return path


def _print_entry(entry: PageEntry, index: int, total: int) -> None:
    conf = f"{entry.confidence:.2f}" if entry.confidence is not None else "n/a"
    print(f"\n[{index}/{total}] {Path(entry.source_file).name} p.{entry.source_page}")
    print(f"  unit:       {entry.unit}")
    print(f"  loadout:    {entry.loadout}")
    print(f"  copies:     {entry.copies_on_page}")
    print(f"  color_mode: {entry.color_mode}")
    print(f"  confidence: {conf}")


def _prompt_corrections(entry: PageEntry) -> dict:
    print("Editing - press Enter to keep the current value.")
    corrections = {}
    for field in EDITABLE_FIELDS:
        current = getattr(entry, field)
        raw = input(f"  {field} [{current}]: ").strip()
        if not raw:
            continue
        if field == "copies_on_page":
            try:
                raw = int(raw)
            except ValueError:
                print("  not a number, keeping current value")
                continue
        elif field == "color_mode" and raw not in ("color", "bw"):
            print("  must be 'color' or 'bw', keeping current value")
            continue
        corrections[field] = raw
    return corrections


def review_faction(conn, faction: str) -> None:
    entries = get_pending_entries(conn, faction)
    if not entries:
        print(f"No pending entries for faction: {faction}")
        return

    confirmed = rejected = skipped = 0
    last_page_key = None
    total = len(entries)
    i = 0
    while i < total:
        entry = entries[i]
        page_key = (entry.source_file, entry.source_page)
        if page_key != last_page_key:
            _open_page_preview(entry)
            last_page_key = page_key
        _print_entry(entry, i + 1, total)

        action = input("[c]onfirm  [e]dit  [r]eject  [s]kip  [o]pen image again  [q]uit\n> ").strip().lower()
        if action == "c":
            confirm_entry(conn, entry.id)
            confirmed += 1
            i += 1
        elif action == "e":
            corrections = _prompt_corrections(entry)
            confirm_entry(conn, entry.id, **corrections)
            confirmed += 1
            i += 1
        elif action == "r":
            reject_entry(conn, entry.id)
            rejected += 1
            i += 1
        elif action == "s":
            skipped += 1
            i += 1
        elif action == "o":
            _open_page_preview(entry)
        elif action == "q":
            skipped += total - i
            break
        else:
            print("Unrecognized input, try again.")

    print(
        f"\n{faction}: {confirmed} confirmed, {rejected} rejected, "
        f"{skipped} left pending out of {total} entries reviewed this session."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Review proposed index entries for a faction before persisting them.")
    parser.add_argument("faction", help="Faction name as stored in the index (matches the ingested folder name)")
    parser.add_argument("--db", type=Path, default=Path("data/index.sqlite"))
    args = parser.parse_args(argv)

    conn = connect(args.db)
    review_faction(conn, args.faction)
    return 0


if __name__ == "__main__":
    sys.exit(main())
