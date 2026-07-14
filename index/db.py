from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

from .models import PageEntry

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def connect(db_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_PATH.read_text())
    conn.commit()


def insert_entry(conn: sqlite3.Connection, entry: PageEntry) -> int:
    """Insert a proposed entry, or refresh it in place if re-ingested (identity is
    source_file + source_page + unit + loadout). Confirmation status is preserved."""
    cur = conn.execute(
        """
        INSERT INTO page_entries
            (faction, source_file, source_page, unit, loadout,
             copies_on_page, color_mode, confidence, confirmed)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (source_file, source_page, unit, loadout) DO UPDATE SET
            copies_on_page = excluded.copies_on_page,
            color_mode     = excluded.color_mode,
            confidence     = excluded.confidence
        """,
        (
            entry.faction,
            entry.source_file,
            entry.source_page,
            entry.unit,
            entry.loadout,
            entry.copies_on_page,
            entry.color_mode,
            entry.confidence,
            int(entry.confirmed),
        ),
    )
    conn.commit()
    return cur.lastrowid


def get_pending_entries(conn: sqlite3.Connection, faction: str) -> list[PageEntry]:
    """Proposed entries awaiting human review (Phase 2)."""
    rows = conn.execute(
        """
        SELECT * FROM page_entries
        WHERE faction = ? AND confirmed = 0
        ORDER BY source_file, source_page
        """,
        (faction,),
    ).fetchall()
    return [_row_to_entry(row) for row in rows]


def confirm_entry(conn: sqlite3.Connection, entry_id: int, **corrections) -> None:
    """Mark an entry confirmed, optionally overriding unit/loadout/copies_on_page/
    color_mode with human-reviewed corrections."""
    allowed = {"unit", "loadout", "copies_on_page", "color_mode"}
    fields = {k: v for k, v in corrections.items() if k in allowed}
    set_clause = "".join(f"{k} = ?, " for k in fields)
    conn.execute(
        f"UPDATE page_entries SET {set_clause}confirmed = 1 WHERE id = ?",
        (*fields.values(), entry_id),
    )
    conn.commit()


def reject_entry(conn: sqlite3.Connection, entry_id: int) -> None:
    conn.execute("DELETE FROM page_entries WHERE id = ?", (entry_id,))
    conn.commit()


def find_entries(
    conn: sqlite3.Connection,
    faction: str,
    unit: str,
    loadout: str,
    color_mode: str,
) -> list[PageEntry]:
    """Confirmed entries matching a unit/loadout/color_mode, for allocation lookups."""
    rows = conn.execute(
        """
        SELECT * FROM page_entries
        WHERE faction = ? AND unit = ? AND loadout = ? AND color_mode = ? AND confirmed = 1
        """,
        (faction, unit, loadout, color_mode),
    ).fetchall()
    return [_row_to_entry(row) for row in rows]


def _row_to_entry(row: sqlite3.Row) -> PageEntry:
    return PageEntry(
        id=row["id"],
        faction=row["faction"],
        source_file=row["source_file"],
        source_page=row["source_page"],
        unit=row["unit"],
        loadout=row["loadout"],
        copies_on_page=row["copies_on_page"],
        color_mode=row["color_mode"],
        confidence=row["confidence"],
        confirmed=bool(row["confirmed"]),
    )
