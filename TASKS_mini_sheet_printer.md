# Task List: Army List → Print-Ready Mini Sheet Generator

Companion to `PRD_mini_sheet_printer.md`. Ordered ingestion-first: a populated,
confirmed index for at least one faction is a prerequisite for meaningful API work.

Test fixtures live in `/Books` (gitignored, not committed): `Human Defense Force`
(pre-split Color_A/Color_B/BW files) and `Saurian Starhost` (four per-release
files, each mixing color and BW pages). Since files are already sorted into
faction folders, the PRD's "release-file → faction mapping" stretch goal is not
needed for these two fixtures — ingestion only needs to resolve unit/loadout per
page, not which army a file belongs to.

## Phase 0 — Scaffolding
1. Set up repo structure (`/ingest`, `/ocr`, `/mapping`, `/index`, `/generate`, `/api`),
   Python project config, and confirm runtime deps (Flask, pikepdf, qpdf CLI) vs.
   offline-only deps (ocrmypdf, Tesseract, rapidfuzz) are cleanly separated.
2. Define the SQLite schema from PRD §5.2 and a thin `/index` module (create/query helpers).

## Phase 1 — Ingestion pipeline
3. Color/BW classifier: render each page to an image, compute chroma variance, tag
   color/bw. Validate against HDF (should match filenames exactly) and Saurian sets
   (mixed — real test of the algorithm).
4. Page-image rendering + label-region cropping (isolate the sparse rotated banner-text
   area) for OCR input prep.
5. OCR wrapper around ocrmypdf/Tesseract using sparse-text segmentation mode.
6. Unit/loadout resolution: fuzzy-match OCR output against each faction's known roster
   (rapidfuzz), producing `(unit, loadout, confidence)` candidates.
7. Copies-per-page detection — determine `copies_on_page` per entry (bulk sheet vs.
   options sheet).

## Phase 2 — Human review & confirmation
8. Build a CLI review tool: shows proposed index entries (with confidence, and a page
   thumbnail or OCR crop) per faction, lets a human confirm/correct/reject before
   persisting.
9. Persist confirmed entries to SQLite.

## Phase 3 — First real indexes
10. Run the full pipeline end-to-end against Human Defense Force (the simpler,
    pre-split case) and confirm its index via the CLI.
11. Run end-to-end against Saurian Starhost (mixed color/BW per file) and confirm its
    index — real test of the classifier and per-file `copies_on_page`/loadout
    resolution.

## Phase 4 — Runtime API
12. `/generate` allocation logic: army-list JSON → per-unit default/swap counts → index
    lookups → page print-count computation (per PRD §6.2 rules).
13. PDF assembly via pikepdf/qpdf: extract resolved `(source_file, source_page)` pages
    (with repeats) into one output PDF, potentially spanning multiple source files.
14. Flask `/api` endpoint wiring request → allocation → assembly → response.
15. Error handling: unresolved unit/loadout (named error), color_mode unavailable (hard
    error), swap count > unit size (validation error).

## Phase 5 — Verification
16. End-to-end test: a real HDF army list and a real Saurian Starhost list (with
    loadout swaps) → generated PDF, manually inspect correctness (right pages, right
    counts, right order).

## Deferred (from PRD Open Questions, non-blocking for MVP)
- Re-indexing/versioning if a publisher updates a source PDF — index treated as
  static once confirmed, for now.
- Caching generated output PDFs — regenerate fresh each request; revisit only if
  qpdf assembly proves slow in practice.
- Long-term ownership story if folded into Army Forge — not a build task.
