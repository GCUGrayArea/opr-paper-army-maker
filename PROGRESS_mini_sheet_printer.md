# Progress Notes: Army List → Print-Ready Mini Sheet Generator

Companion to `PRD_mini_sheet_printer.md` / `TASKS_mini_sheet_printer.md`. Read this
first when picking the work back up, especially on a different machine.

## MAJOR PIVOT: standees from VTT token art, not PDF page extraction

The project direction changed significantly after the PDF-review work documented
below. The publisher's paper-mini downloads also bundle VTT (virtual tabletop)
token art: `Books/<Faction>/VTT/*.png` — clean, single-pose, front-view-only
images, one per unit/loadout, no identifying text or filenames (just opaque
sequence numbers like `hdf-vtt-fb-1-23.png` / `hdf-vtt-fb-bw-23.png` — color and
bw indices correspond 1:1, confirmed by direct comparison).

**Decision: pivot entirely to composing our own standee sheets from this token
art**, rather than extracting pages from the print PDFs. Reasons: it sidesteps
essentially all of the OCR/grid-detection/fuzzy-matching fragility documented
below (this is the whole reason the pivot happened), and it lets us pack minis
more densely than the publisher's fixed page layout, saving paper/print cost for
whoever orders. The catch: VTT packs are front-view only. The workaround
(confirmed working): extract matching back-views from the print PDFs using the
grid-geometry code we already built (`find_row_bands`/`find_col_bounds`) —
geometry-only cropping, no OCR needed, since identification now comes from
matching against the VTT front image instead of reading banner text.

**An email was sent to OPR** (draft in `OUTREACH_EMAIL_opr_back_view_assets.md`)
asking if they'd just provide clean back-view PNGs directly, which would remove
the need for PDF cropping entirely if they say yes. Proceeding with the PDF-crop
workaround in the meantime since a reply isn't guaranteed.

### Technical notes on the extraction pipeline (`_session_tools_vtt_*.py`)

- **PDF page cells are rotated 90° relative to VTT tokens** (the whole PDF page
  layout is designed for sideways banner-label reading). Confirmed empirically:
  `cell.rotate(90, expand=True)` produces the correct upright orientation — do
  not skip this, comparisons against VTT art are meaningless without it.
- **Column layout per detected row** (at least for the rows checked): 4 cells
  from `find_col_bounds`, of which cell index 0 and the last are blank
  margins, cell index 1 (first non-blank) is the **front** pose, cell index 2
  (second non-blank) is the **back** pose. `page_cells()` in
  `_session_tools_vtt_pipeline.py` implements this by taking the first two
  non-blank (ink-mean < 250) cells rather than hardcoding indices, since not
  every row necessarily has the same cell count.
- **Two automated image-matching approaches were tried and both failed** —
  don't retry them without a real reason to think it'll go differently:
  - Average-hash (aHash), even after adding a tight content-bbox crop and
    bumping resolution: no clean separation between "confident match" and
    "no match" distances (23–57 out of 256, worst not meaningfully worse than
    best). The tight-crop version was *worse* — a token I'd already visually
    confirmed as correct landed in the "worst matches" list.
  - ORB (OpenCV) keypoint feature matching: even more wrong — a known-correct
    pair scored *lower* (19 good matches) than a known-different pair (314).
    Best guess: these mini sculpts share too much generic low/mid-level
    texture (armor plating, scale patterns, consistent rendering style across
    the whole faction) for generic CV similarity to key on the actually
    distinguishing content (specific weapon/pose) rather than "looks like a
    similarly-armored sci-fi soldier."
  - **What actually works: direct vision identification** — batching VTT
    tokens into contact sheets (`_session_tools_vtt_contact_sheet.py`, ~16 per
    sheet, 4×4 grid, legible) and identifying each by eye against roster
    vocabulary, the same method used for the PDF review. Slower, but reliable.
- `opencv-python-headless` was added to `requirements-offline.txt` for the ORB
  attempt — it's not being used for anything that worked, but left in since
  it's an ingestion-only dependency and may be useful again. Reconsider
  removing it if nothing ends up using it.

### Human Defense Force VTT identification: current state

All 69 unique HDF VTT tokens (138 files incl. bw) were identified by vision and
processed via `_session_tools_vtt_finalize.py`. Output in
`Books/Human Defense Force/VTT_identified/`:
- `front/` — all 138 renamed files:
  `<Unit> - <Loadout>[ (GUESS)] - <color|bw> [<original hdf-vtt-fb-... notation>].png`
  — original notation always preserved in the filename per the user's request,
  so these can be re-matched to official back-views later if OPR provides them.
- `back/` — 14 extracted back-view crops (7 unit/loadout pairs × color+bw),
  spot-checked visually against their fronts and confirmed correct (same pose,
  viewed from behind).

**Only 11 of 69 identifications are confidence="confirmed"** (vision-matched
against a PDF page already reviewed this session): Company Leader (Master Drum
Pistol, Master Rifle, Sniper Leader), Combat Bikers (Default, Hunting Lance),
Infantry Squad (Field Radio, Flamer, Company Standard), Recruits (Default),
GRUNT Robots (Default), Snipers (Default). The other **58 are best-effort
guesses flagged `(GUESS)` in the filename** — the *unit* is generally
confident (distinct sculpt per unit made that identifiable), but the *specific
loadout name* is a guess against the roster's loadout vocabulary, unverified,
explicitly deferred per the user's direction (2026-07-14 session). Notably:
**Storm Leader (12 tokens) and Veterans (12 tokens) account for 24 of the 58
guesses** — Veterans in particular has an unusually large loadout list (~22
options incl. several rule-only "may introduce additional models" upgrades per
the user, so the skew is expected, not a detection problem).

Back-view crops only exist for the 11 confident pairs — the 58 guessed ones
have no known PDF page to crop from yet (guessing a loadout name doesn't tell
you which page has it). Filling those in requires either resolving the guesses
against further PDF review, or getting official back-views from OPR.

### Next steps for the VTT pivot

1. Resolve the 58 `(GUESS)` loadout names — likely by reviewing more HDF PDF
   pages (the ones covering Storm Leader/Veterans specialist/weapon variants)
   and matching against them, same as the confident 11 were resolved.
2. Once resolved, extract their back-views the same way (the pipeline already
   supports it — `build_references()` just needs those pages to exist among
   its 104 built references, or to be added).
3. Do the same identification pass for Saurian Starhost's VTT set (114 images,
   no PDF review started there at all yet).
4. Design the actual generation path: composing a densely-packed standee sheet
   from front+back token pairs (this hasn't been built yet — everything so far
   is ingestion/identification, not the `/generate` output side).
5. Decide what happens to the old PDF-page-extraction index
   (`data/index.sqlite`'s `page_entries` table, 359 HDF rows, 100 confirmed)
   now that generation won't extract PDF pages directly — it's still useful as
   a source of "known (unit, loadout) → page" references for VTT matching
   (that's what `build_references()` uses it for), so don't delete it, but its
   original purpose (direct page extraction for `/generate`) is superseded.

## Where we are (pre-pivot, PDF-page-extraction approach)

The sections below document the PDF-based approach's state at the time of the
pivot. Kept for reference (the grid-detection/roster/matcher bug fixes are
still real and still in the working tree regardless of the pivot; the
page-by-page review progress is not currently the active path forward).

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

**Phase 3 (first real indexes) is in progress, and turned up real Phase 1 bugs.**
The original ingest-then-review plan changed shape significantly this session —
read this whole section before resuming.

### Human Defense Force: three Phase 1 code bugs found and fixed

Started reviewing the first ingestion pass (332 pending entries, 0 confirmed) via
vision (the user asked me to review with vision directly rather than via the
`mapping.review_cli` human tool — see "How review is actually happening" below).
Cross-checking rendered pages against candidate entries surfaced three real bugs
in the Phase 1 code, **all now fixed in the working tree, none committed to git
yet**:

1. **`ocr/grid.py` — row-rule detection threshold too strict, silently dropping
   real rows.** `GRID_LINE_FRACTION` was a single hardcoded 0.9 cutoff (dark-pixel
   coverage fraction) used for *both* row-rule and column-rule detection. Real
   row rules were observed as low as 0.8497 on genuine HDF content (a "Storm
   Leader" row whose divider line just didn't hit 0.9), and a missed row boundary
   silently drops that row's candidate entirely — nothing downstream can recover
   it. Fix: split into two constants, `ROW_LINE_FRACTION = 0.8` (biased toward
   recall — a false-positive row just becomes a low-quality candidate for review
   to reject, which is far cheaper than silent data loss) and
   `COL_LINE_FRACTION = 0.9` (kept strict — lowering column sensitivity too was
   tried first and caused a *regression*: complex die-cut artwork, e.g.
   overlapping motorcycle/weapon silhouettes, threw off enough spurious column
   edges to exceed `MAX_PLAUSIBLE_COL_BOUNDS` and made whole rows vanish. First
   attempt at a single shared lower threshold: entries 337→311, empty pages
   3→20 — a net regression, caught before it got re-ingested for real).
2. **`mapping/roster.py` — `extract_roster` only collected `ArmyBookWeapon` gains
   as loadouts**, missing every `ArmyBookItem` gain — the army book uses this
   type for named character/squad-specialist titles (e.g. "Commander", "Drill
   Sergeant", "Forward Observer", "Psy-Hacker", "Sergeant", "Radio", "Medic",
   "Banner"). 55 such gains exist across the HDF book alone, vs. 1 lone
   `ArmyBookRule` gain (a non-visual vehicle ability, correctly still excluded).
   Fix: `LOADOUT_GAIN_TYPES = {"ArmyBookWeapon", "ArmyBookItem"}`.
3. **`mapping/match.py` — `resolve_label` assumed line 1 = unit name, line 2 =
   loadout**, but specialist-title pages print with *no unit-name line at all*
   (just "Commander", or a title OCR-wrapped across two lines like "Forward" /
   "Observer" — which the old code misread as unit="Forward", loadout="Observer").
   Fix: `resolve_label` now tries both the split reading and a "whole label is a
   loadout/title on its own" reading (searching every unit's loadouts, not just
   the guessed unit's), and keeps whichever is more confident.

   **Known remaining ambiguity from this fix** (flagged by the user before I
   implemented it, and confirmed real): several hero units (Company Leader, Tank
   Company Leader, Storm Leader) each have their *own* copy of the same title
   names (their own "Commander", their own "Drill Sergeant", etc.), so a
   title-only label is textually ambiguous about *which unit* it belongs to —
   `_best_loadout_match` breaks ties by roster list order, which is frequently
   wrong. The algorithm now gets the *loadout/title* right with high confidence
   but can guess the wrong *unit*. This is only resolvable by looking at the
   artwork (sculpt/pose family), which is exactly why the vision review pass
   matters here — every title-only entry needs its unit double-checked by eye,
   not just trusted from its confidence score.

After all three fixes, HDF was wiped and re-ingested clean:
**350 candidate entries, 4 pages with no detected units** (BW p.1/p.62, Color_A
p.62, Color_B p.62 — covers/back matter), 0 unresolved. (Prior to the fixes it
was 337 candidates / 3 empty pages; the numbers moved because real content that
was previously mis-detected or silently dropped is now being found.)

### A residual detection gap remains — handled by manual insert, not code

Even after the fixes, **some pages still merge multiple real rows into a single
detected band** — e.g. two overlapping die-cut model silhouettes (motorcycle
"Biker Leader Pistol"/"Biker Leader Lance") or a run of several specialist-title
rows (Banner/Radio/Medic/Sergeant) where only one row's rule is found and the
rest are invisible to `find_row_bands` even at the lowered threshold. This is a
real remaining limitation of the line-fraction-based detector on complex/tightly
packed content — not something a further threshold tweak safely fixes (tried
going lower; it reintroduces false column splits on other pages).

**Decision (asked and confirmed with the user):** rather than leave these pages
silently incomplete, when I can clearly identify the missing row from the
artwork + roster vocabulary, I manually author and pre-confirm a `PageEntry`
directly (same effect as if the pipeline had proposed it and I'd confirmed it).
This has happened **10 times so far** across HDF's BW.pdf and Color_A.pdf, always
for specialist-title pages (Storm Troopers, Infantry Squad, Veterans "Sergeant /
Radio / Medic / Banner"-style pages) or the Combat Bikers merged Pistol/Lance
pages. Pattern so far: the crop that *does* get read is usually **not**
consistently the first or last row — check with `analyze_page` directly on the
specific page rather than assuming.

Two roster-vocabulary mappings used repeatedly that are **worth double-checking
against the actual rules text later** (chosen by best fuzzy sense, not certain):
- Printed "Sergeant" → roster's `Sgt. Hand Weapon` (there's also a
  `Sgt. Pistol`/`Sgt. Heavy Pistol` option per-unit; picked hand-weapon from the
  artwork's silhouette, not confirmed against rules text).
- Combat Bikers' printed "Pistol" loadout (no such name in the roster's
  extracted loadout list — `Default`, `Hunting Lance`, `Anti-Tank Lance`, etc.
  but nothing gun-named) → mapped to roster's `Default`, on the theory the
  base/unmodified weapon is what's depicted. Same reasoning applied to OGRE
  Robots' printed "Minigun" → `Default` (no matching named loadout either).

### How review is actually happening (not via `mapping/review_cli.py`)

The user asked me to review all entries myself using vision rather than have a
human click through `mapping.review_cli`. I built an ad-hoc driver for this,
**now copied from the session scratchpad into the repo root** (not yet
integrated into the package, not committed) so it survives a context reset:
- `_session_tools_contact_sheet.py` — renders N pages of a PDF into one tiled
  contact-sheet PNG with filename/page captions, for a single vision read per
  batch instead of per page. 9 pages per sheet (3×3 grid) was the sweet spot
  found by testing — legible enough to read rotated banner text directly, few
  enough tool round-trips to be practical.
- `_session_tools_review_helper.py` — three subcommands, all operating on
  `data/index.sqlite` directly (bypasses `review_cli.py`'s interactive loop
  entirely):
  - `list <faction>` — prints total pending-entry/page/batch counts.
  - `sheet <faction> <batch_index> <out_path>` — generates a contact sheet for
    one batch of (up to 9) pending pages, and prints the matching entries
    (id/unit/loadout/copies/color/confidence) grouped by page, for
    cross-referencing against the image.
  - `apply <faction> <decisions.json>` — applies a list of
    `{"id": N, "action": "confirm"}` / `{"action": "edit", "unit": ..., ...}` /
    `{"action": "reject"}` / `{"action": "insert", "source_file": ..., ...}`
    decisions in one shot.

  **Known bug in this tool, importantly affecting the current DB state — read
  before continuing review:** `sheet`'s `batch_index` is computed fresh against
  *whatever's currently pending* each call, not a stable offset into the
  original full list. Since `apply` confirms/removes entries from the pending
  pool, calling `sheet ... 1 ...` right after applying what I'd called "batch 0"
  does **not** yield the next 9 pages — it re-numbers from the new (shrunken)
  pending pool, so "batch 1" can skip however many pages were just confirmed out
  from under index 0. This actually happened: **batches were called 0, 1, 2, 3,
  4 in sequence without regenerating from 0 each time, and it silently skipped
  three page ranges in `Human_Defense_Force_-_BW.pdf` (pages 11–19, 29–37,
  47–55) and one in `Human_Defense_Force_-_Color_A.pdf` (pages 4–12) — 36 pages
  with real pending entries that were never shown for review.** These are NOT
  reviewed yet, and are currently indistinguishable in the DB from normal
  not-yet-reached pending pages — the list below is the only record of which
  ones were skipped-by-bug vs. simply not-yet-reached.
  **Fix before resuming**: always call `sheet <faction> 0 <out_path>` (index
  always 0 — it's always "the next unreviewed batch" since confirmed entries
  drop out of the pool), never increment the index manually.

### Current DB state (Human Defense Force), as of this note

- 359 total entries, **100 confirmed**, 259 pending.
- Reviewed and applied so far (5 "batches" worth, ~110 decisions): BW.pdf pages
  2–10, 20–28, 38–46, 56–61; Color_A.pdf pages 1–3, 13–21.
- **Skipped by the batch-index bug above, not yet reviewed:** BW.pdf pages
  11–19, 29–37, 47–55 (27 pages); Color_A.pdf pages 4–12 (9 pages).
- **Not yet reached (normal, review just hasn't gotten there):** Color_A.pdf
  pages 22–61; all of Color_B.pdf (1–61).
- Corrections applied so far: ~50 confirmed as-is, ~15 edited (mostly unit
  misattribution on title-only pages per the `match.py` ambiguity above, or a
  roster loadout name too different from the printed label for fuzzy match to
  find, e.g. `Company Standard` vs. printed "Banner"), 2 rejected (cover-page
  chroma-blob false positives, same failure mode as the original Storm-Leader
  cover-page garbage entry from before the fixes), 10 manually inserted.

- Saurian Starhost: **not started.** Real test of the classifier (mixed color/BW
  per file) and per-file copies/loadout resolution once we get there.

## IMPORTANT: uncommitted state right now

- **Code fixes are NOT committed.** `ocr/grid.py`, `mapping/roster.py`,
  `mapping/match.py` all have working-tree changes (the three bug fixes above).
  `git status`/`git diff` before doing anything else.
- **`data/index.sqlite` reflects those fixes** (359 entries, 100 confirmed) —
  it does NOT match what's in any Drive zip uploaded before this session's bug
  fixes. If resuming from a Drive zip, check whether it predates this note; if
  so, prefer continuing from the live `data/index.sqlite` on this machine over
  unzipping an older one.
- `_session_tools_contact_sheet.py` and `_session_tools_review_helper.py` in
  the repo root are this session's vision-review driver, copied out of the
  scratchpad so they'd survive — not part of the actual package, not committed.
  Delete or formalize them once the review approach is settled.

## Resuming on another machine

`Books/` (source PDFs + army book JSON) and `data/` (SQLite index, generated
output) are both gitignored — neither is in this repo.

1. Make sure `Books/` is present (same fixture layout: `Books/<Faction
   Name>/<Faction Name>.json` + `*.pdf`).
2. Make sure the three code fixes above are present (they're uncommitted, so a
   fresh `git clone` on another machine will NOT have them — copy the working
   tree, don't just clone).
3. Make sure `data/index.sqlite` matches this machine's (359 entries / 100
   confirmed) — copy it directly rather than re-ingesting, since review
   progress now exists and re-ingesting from scratch would lose confirmed/edited
   state (ingestion only writes proposed rows; it doesn't touch already-confirmed
   ones, but you'd still need the existing DB file as the base, not a fresh one).
4. To continue vision review: regenerate the next batch with
   `python _session_tools_review_helper.py sheet "Human Defense Force" 0 <out_path.png>`
   — **always pass `0`**, see the batch-index bug above. Cross-reference the
   printed entry list against the image, write a decisions JSON, then
   `python _session_tools_review_helper.py apply "Human Defense Force" <decisions.json>`.
   First priority: the 36 skipped-by-bug pages listed above, before continuing
   into not-yet-reached territory.
5. Runtime deps for ingestion: `pip install -r requirements-offline.txt`, plus a
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
