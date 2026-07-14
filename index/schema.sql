CREATE TABLE IF NOT EXISTS page_entries (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    faction        TEXT    NOT NULL,
    source_file    TEXT    NOT NULL,
    source_page    INTEGER NOT NULL,
    unit           TEXT    NOT NULL,
    loadout        TEXT    NOT NULL,
    copies_on_page INTEGER NOT NULL,
    color_mode     TEXT    NOT NULL CHECK (color_mode IN ('color', 'bw')),
    confidence     REAL,
    confirmed      INTEGER NOT NULL DEFAULT 0,
    UNIQUE (source_file, source_page, unit, loadout)
);

CREATE INDEX IF NOT EXISTS idx_page_entries_lookup
    ON page_entries (faction, unit, loadout, color_mode, confirmed);
