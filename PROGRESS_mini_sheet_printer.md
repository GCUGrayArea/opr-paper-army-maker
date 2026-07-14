# Progress Notes: Army List → Print-Ready Mini Sheet Generator

Companion to `PRD_mini_sheet_printer.md` / `TASKS_mini_sheet_printer.md`. Read this
first when picking the work back up, especially on a different machine.

## Where we are

**Phase 0 (scaffolding) and Phase 1 (ingestion building blocks) are complete** and
committed (`37fd099`, `9d4d06f`).

**Phase 2 (human review & confirmation) is built** in this WIP commit:
- `ingest/pipeline.py` — the orchestrator that Phase 1 didn't have yet: walks a
  faction folder's PDFs page by page (`render_page` → `classify_color_mode` →
  `analyze_page` → `resolve_label` against the faction roster) and writes proposed
  (`confirmed=0`) rows via `insert_entry`. Run as:
  ```
  python -m ingest.pipeline "Books/<Faction Name>" --db data/index.sqlite
  ```
  Expects `Books/<Faction Name>/<Faction Name>.json` (Army Forge book export) plus
  `*.pdf` source files in that same folder.
- `mapping/review_cli.py` — the human review tool: walks pending entries for a
  faction in `(source_file, source_page)` order, opens a downsized page thumbnail
  in the OS default image viewer (Windows-only right now, via `os.startfile`; only
  reopens when the page changes), and prompts
  `[c]onfirm  [e]dit  [r]eject  [s]kip  [o]pen image again  [q]uit`. Run as:
  ```
  python -m mapping.review_cli "<Faction Name>" --db data/index.sqlite
  ```
  Safe to quit partway through — unreviewed entries just stay pending, re-run to
  pick up where you left off (they're not reordered).

**Phase 3 (first real indexes) is in progress:**
- Human Defense Force: **ingested, not yet reviewed.** Ran `ingest.pipeline`
  against all three source files (`Human_Defense_Force_-_BW.pdf`, `-_Color_A.pdf`,
  `-_Color_B.pdf`, 62 pages each). Result: 332 unique pending entries in
  `data/index.sqlite` (337 candidates written, 5 collapsed as duplicate
  source_file+page+unit+loadout upserts), 3 pages with no detected units
  (likely cover/TOC), 0 unresolved. **0 confirmed so far** — the review pass
  hasn't started.
  - Confidence spread across the 332 pending entries:
    | confidence | count |
    |---|---|
    | ≥ 0.9 | 204 |
    | 0.7–0.9 | 12 |
    | 0.5–0.7 | 83 |
    | < 0.5 | 33 |
  - Notable: every "Storm Leader" entry landed at 0.38–0.45 confidence — worth
    extra scrutiny during review, likely either a roster-name mismatch or OCR
    struggling on those specific pages (garbled OCR text like `"a: ir Dela"` was
    seen in ad-hoc testing on what looked like a Storm Leader page).
- Saurian Starhost: **not started.** Real test of the classifier (mixed color/BW
  per file) and per-file copies/loadout resolution once we get there.

## Resuming on another machine

`Books/` (source PDFs + army book JSON) and `data/` (SQLite index, generated
output) are both gitignored — neither is in this repo. To pick up review work
elsewhere:

1. Make sure `Books/` is present (same fixture layout: `Books/<Faction
   Name>/<Faction Name>.json` + `*.pdf`).
2. For Human Defense Force specifically: since **nothing has been confirmed
   yet**, it's safe to just re-run ingestion fresh rather than copying
   `data/index.sqlite` over —
   ```
   python -m ingest.pipeline "Books/Human Defense Force" --db data/index.sqlite
   ```
   (Ingestion is deterministic given the same inputs, so this reproduces the
   same 332 pending entries.) If review has progressed by the time you read
   this, copy `data/index.sqlite` instead of re-ingesting, to preserve
   confirmed/edited state.
3. Run the review CLI:
   ```
   python -m mapping.review_cli "Human Defense Force" --db data/index.sqlite
   ```
4. Runtime deps for ingestion: `pip install -r requirements-offline.txt`, plus a
   system Tesseract install (the code falls back to
   `C:\Program Files\Tesseract-OCR\tesseract.exe` on Windows if `tesseract` isn't
   on `PATH`).

## Next steps (in order)

1. Finish reviewing Human Defense Force's 332 pending entries via
   `mapping.review_cli` (task 10).
2. Run `ingest.pipeline` + `mapping.review_cli` against Saurian Starhost — the
   real test of mixed color/BW-per-file classification (task 11).
3. Phase 4: `/generate` allocation logic, PDF assembly via pikepdf/qpdf, Flask
   `/api` endpoint, error handling (tasks 12–15).
4. Phase 5: end-to-end verification with a real army list for each faction
   (task 16).
