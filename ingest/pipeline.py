from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from index import PageEntry, connect, init_db, insert_entry
from mapping.match import resolve_label
from mapping.roster import RosterUnit, extract_roster, load_army_book
from ocr.page import analyze_page
from ocr.render import page_count, render_page

from .classify import classify_color_mode


@dataclass
class IngestStats:
    """Counts from one faction ingestion run, for the CLI summary line."""

    entries_written: int = 0
    pages_with_no_units: int = 0
    unresolved_units: int = 0


def ingest_pdf(conn, faction: str, pdf_path: Path, roster: list[RosterUnit]) -> IngestStats:
    """Render every page of one PDF, classify color mode, detect (label, copies)
    units on the page, resolve each label against the faction roster, and write
    proposed (unconfirmed) PageEntry rows. `source_page` is 1-indexed."""
    stats = IngestStats()
    for page_number in range(page_count(str(pdf_path))):
        image = render_page(str(pdf_path), page_number)
        color_mode, _ = classify_color_mode(image)
        units = analyze_page(image)
        if not units:
            stats.pages_with_no_units += 1
            continue
        for unit in units:
            match = resolve_label(unit.text, roster)
            if match is None:
                # Defensive only — analyze_page already filters implausible
                # labels, so this should mean an empty roster, not bad OCR.
                stats.unresolved_units += 1
                continue
            insert_entry(
                conn,
                PageEntry(
                    faction=faction,
                    source_file=str(pdf_path),
                    source_page=page_number + 1,
                    unit=match.unit,
                    loadout=match.loadout,
                    copies_on_page=unit.copies_on_page,
                    color_mode=color_mode,
                    confidence=match.confidence,
                ),
            )
            stats.entries_written += 1
    return stats


def ingest_faction(conn, faction: str, pdf_paths: list[Path], roster: list[RosterUnit]) -> IngestStats:
    total = IngestStats()
    for pdf_path in pdf_paths:
        stats = ingest_pdf(conn, faction, pdf_path, roster)
        total.entries_written += stats.entries_written
        total.pages_with_no_units += stats.pages_with_no_units
        total.unresolved_units += stats.unresolved_units
    return total


def _faction_dir_inputs(book_dir: Path) -> tuple[str, Path, list[Path]]:
    """A faction folder is expected to hold `<faction name>.json` (the Army
    Forge book export) alongside its source PDFs — see TASKS_mini_sheet_printer.md
    fixture layout (Books/<faction>/<faction>.json + *.pdf)."""
    faction = book_dir.name
    army_book_path = book_dir / f"{faction}.json"
    pdf_paths = sorted(book_dir.glob("*.pdf"))
    return faction, army_book_path, pdf_paths


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Ingest a faction's source PDFs into the pending-review index (Phase 1 -> Phase 2 handoff)."
    )
    parser.add_argument(
        "book_dir", type=Path, help="Faction folder containing <faction>.json and its source PDFs"
    )
    parser.add_argument("--db", type=Path, default=Path("data/index.sqlite"))
    args = parser.parse_args(argv)

    faction, army_book_path, pdf_paths = _faction_dir_inputs(args.book_dir)
    if not army_book_path.exists():
        parser.error(f"army book not found: {army_book_path}")
    if not pdf_paths:
        parser.error(f"no PDFs found in {args.book_dir}")

    roster = extract_roster(load_army_book(army_book_path))
    if not roster:
        parser.error(f"no units found in army book: {army_book_path}")

    conn = connect(args.db)
    init_db(conn)
    stats = ingest_faction(conn, faction, pdf_paths, roster)
    print(
        f"{faction}: {stats.entries_written} candidate entries written from {len(pdf_paths)} file(s) "
        f"({stats.pages_with_no_units} page(s) with no detected units, "
        f"{stats.unresolved_units} unresolved unit(s))"
    )
    print(f"Review with: python -m mapping.review_cli \"{faction}\" --db {args.db}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
