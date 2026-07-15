from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, r"C:\Users\Gray Morrow\projects\opr-paper-army-maker")
os.chdir(r"C:\Users\Gray Morrow\projects\opr-paper-army-maker")

from index import PageEntry, confirm_entry, connect, insert_entry, reject_entry

from contact_sheet import make_contact_sheet

DB_PATH = r"C:\Users\Gray Morrow\projects\opr-paper-army-maker\data\index.sqlite"
BATCH_SIZE = 9
COLS = 3


def load_pending(faction: str) -> list[dict]:
    conn = connect(DB_PATH)
    rows = conn.execute(
        """
        SELECT id, source_file, source_page, unit, loadout, copies_on_page, color_mode, confidence
        FROM page_entries WHERE faction = ? AND confirmed = 0
        ORDER BY source_file, source_page, id
        """,
        (faction,),
    ).fetchall()
    return [dict(r) for r in rows]


def page_key(row: dict) -> tuple[str, int]:
    return (row["source_file"], row["source_page"])


def unique_pages(rows: list[dict]) -> list[tuple[str, int]]:
    seen = []
    for r in rows:
        k = page_key(r)
        if k not in seen:
            seen.append(k)
    return seen


def cmd_list(faction: str) -> None:
    rows = load_pending(faction)
    pages = unique_pages(rows)
    batches = [pages[i : i + BATCH_SIZE] for i in range(0, len(pages), BATCH_SIZE)]
    print(f"{len(rows)} pending entries across {len(pages)} pages, {len(batches)} batches of up to {BATCH_SIZE}")


def cmd_sheet(faction: str, batch_index: int, out_path: str) -> None:
    rows = load_pending(faction)
    pages = unique_pages(rows)
    batches = [pages[i : i + BATCH_SIZE] for i in range(0, len(pages), BATCH_SIZE)]
    if batch_index >= len(batches):
        print(f"no such batch ({len(batches)} total)")
        return
    batch_pages = batches[batch_index]
    make_contact_sheet(batch_pages, COLS, Path(out_path))

    by_page = {}
    for r in rows:
        by_page.setdefault(page_key(r), []).append(r)

    print(f"=== batch {batch_index}/{len(batches) - 1} ({len(batch_pages)} pages) -> {out_path} ===")
    for pg in batch_pages:
        print(f"-- {Path(pg[0]).name} p.{pg[1]} --")
        for r in by_page[pg]:
            conf = f"{r['confidence']:.2f}" if r["confidence"] is not None else "n/a"
            print(
                f"  id={r['id']:<4} unit={r['unit']!r:28} loadout={r['loadout']!r:24} "
                f"copies={r['copies_on_page']} color={r['color_mode']:<5} conf={conf}"
            )


def cmd_apply(faction: str, decisions_path: str) -> None:
    decisions = json.loads(Path(decisions_path).read_text())
    conn = connect(DB_PATH)
    confirmed = edited = rejected = inserted = 0
    for d in decisions:
        action = d["action"]
        if action == "confirm":
            confirm_entry(conn, d["id"])
            confirmed += 1
        elif action == "edit":
            corrections = {k: v for k, v in d.items() if k in ("unit", "loadout", "copies_on_page", "color_mode")}
            confirm_entry(conn, d["id"], **corrections)
            edited += 1
        elif action == "reject":
            reject_entry(conn, d["id"])
            rejected += 1
        elif action == "insert":
            # Manually authored entry for real content the detector never
            # produced a candidate for at all (see PROGRESS notes on merged
            # rows) -- inserted pre-confirmed since it's already vision-reviewed.
            entry = PageEntry(
                faction=faction,
                source_file=d["source_file"],
                source_page=d["source_page"],
                unit=d["unit"],
                loadout=d["loadout"],
                copies_on_page=d["copies_on_page"],
                color_mode=d["color_mode"],
                confidence=None,
                confirmed=True,
            )
            insert_entry(conn, entry)
            inserted += 1
        else:
            raise ValueError(f"unknown action {action!r} in {d!r}")
    print(
        f"applied {len(decisions)}: {confirmed} confirmed, {edited} edited+confirmed, "
        f"{rejected} rejected, {inserted} manually inserted"
    )


if __name__ == "__main__":
    cmd, *rest = sys.argv[1:]
    if cmd == "list":
        cmd_list(rest[0])
    elif cmd == "sheet":
        cmd_sheet(rest[0], int(rest[1]), rest[2])
    elif cmd == "apply":
        cmd_apply(rest[0], rest[1])
    else:
        raise SystemExit(f"unknown command {cmd!r}")
