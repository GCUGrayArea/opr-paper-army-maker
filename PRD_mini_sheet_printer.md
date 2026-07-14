# PRD: Army List → Print-Ready Mini Sheet Generator

## 1. Problem Statement

Tabletop wargame miniature "paper mini" PDFs are typically laid out as print sheets — each page or row containing one or more physical miniature cutouts tied to a specific unit and equipment loadout. Given an army list (e.g., from OPR Army Forge), a player currently must manually identify which pages of a (often 50–70 page, non-searchable) source PDF correspond to their units and loadouts, then manually assemble a print-ready PDF for a print shop.

This tool automates that process: given a structured army list and a one-time-indexed set of source mini PDFs, it generates a single print-ready PDF containing exactly the pages needed (with correct repeat counts) to build that army.

## 2. Goals

- Eliminate manual page-hunting and PDF assembly for players ordering physical minis.
- Support source material distributed in varying formats:
  - Full-army files pre-split into Color and BW versions.
  - Per-release files that mix Color and BW pages and cover multiple armies.
- Do the expensive work (OCR, indexing, file classification) once per faction/release as an offline pipeline; keep the always-on request path fast and dependency-light.
- Design the request/response boundary as a clean HTTP API so it can later be called from OPR Army Forge (or any other client) without coupling to Army Forge's stack.

## 3. Non-Goals

- Not building a general-purpose PDF editor.
- Not attempting fully unsupervised, zero-review ingestion of new faction files — a human-in-the-loop verification step is acceptable and expected for onboarding new factions.
- Not handling pose/artwork variant selection (e.g., "which sculpt of Warrior do I want") — out of scope unless later requested.
- Not targeting serverless/ephemeral-storage deployment — assume persistent local disk on a small always-on host.

## 4. Users

- **Primary:** Tabletop players building an army list who want a single print-ready PDF to send to a print shop.
- **Secondary (future):** Army Forge itself, calling the API programmatically as part of list-building/checkout flow.

## 5. Core Concepts & Data Model

### 5.1 Page ≠ Unit ≠ Model

A single sheet/page may represent:
- A **bulk default-loadout sheet**: e.g., one page = 5 copies of "Warrior / Pistol," representing a full unit's worth of the default loadout in one print.
- An **options sheet**: e.g., one page with 4 rows, each a *different* single special-weapon model (Shock, Spike, Flamer, Blast), each usable independently.

The data model must capture **copies per page**, not just page identity, so the generator can compute how many times to print a page to satisfy a given model count.

### 5.2 Index Schema (SQLite)

Minimum fields per indexed page-entry:

| Field | Description |
|---|---|
| `faction` | Normalized faction/army name |
| `source_file` | Path/identifier of the source PDF |
| `source_page` | Page number within that source file |
| `unit` | Unit name (normalized, matchable to Army Forge unit names) |
| `loadout` | Loadout/weapon variant label as printed on the sheet |
| `copies_on_page` | How many models of this loadout appear on this page |
| `color_mode` | `color` or `bw` |
| `confidence` | Optional — confidence score if entry was LLM/fuzzy-match assisted, for audit purposes |

Key design point: pages are addressed as `(source_file, source_page)`, and a faction may be backed by **multiple source files** (never assume one file per faction).

## 6. Functional Requirements

### 6.1 Offline Ingestion & Indexing Pipeline (run per-faction, one-time)

1. **File intake** — accept one or more PDFs per faction/release as input.
2. **Color/BW classification** — per page, detect color vs. black-and-white programmatically (pixel chroma variance on rendered page image; no ML needed). Tag each page/file accordingly so the system can serve either version on request.
3. **OCR** — run OCR (ocrmypdf/Tesseract) to extract page labels. Given labels are often small, rotated (vertical banner text), and sparse rather than paragraph text:
   - Consider cropping/isolating the label region before OCR to improve accuracy.
   - Use a sparse-text page segmentation mode rather than default paragraph assumptions.
4. **Unit/loadout resolution** — resolve OCR'd text to canonical unit/loadout names via fuzzy matching (e.g., `rapidfuzz`) against the known army-book roster, tolerant of OCR errors.
5. **Release-file → faction mapping (stretch goal)** — for per-release files that mix content from multiple armies/releases:
   - Gather cheap signal per file (filename, OCR text from first 1–2 pages).
   - Use an LLM to propose candidate faction/release mappings with confidence scores, given the army book roster as context.
   - Treat LLM output as **candidate generation, not ground truth** — surface a human review step (e.g., a thumbnail contact sheet) for one-time confirmation per faction.
6. **Persist** — write confirmed index entries to SQLite. This step is run once per faction and its output (index + normalized source PDFs) is what the runtime service depends on. OCR/Tesseract/LLM tooling does not need to be present at runtime.

### 6.2 Runtime API (Flask)

A single always-on Flask service exposing (at minimum) one endpoint:

**Request:** structured army list, e.g.:
```json
{
  "faction": "Saurian Starhost",
  "color_mode": "bw",
  "units": [
    {
      "unit": "Saurian Warrior",
      "size": 5,
      "loadout_swaps": [
        { "loadout": "Shock Charger", "count": 1 }
      ]
    }
  ]
}
```

**Processing (allocation logic):**
- For each unit, subtract loadout-swap counts from unit size to determine how many default-loadout models are needed.
- Look up index entries for the unit's default loadout and each swapped loadout, respecting `copies_on_page`.
- Compute page print counts: e.g., a default-loadout sheet providing 5 copies/page is printed once even if only 4 are "needed" (excess is expected/acceptable); a single-copy options page is printed once per swap required (multiplied if more than one copy of that swap is needed).
- Resolve `color_mode` to the correct source file/pages.

**Response:** a single generated PDF (via `qpdf`/`pikepdf` page extraction and assembly from the resolved page list, potentially spanning multiple source files), returned as the API response body or a link to the generated file.

### 6.3 Error Handling / Edge Cases

- Unit or loadout not found in index for requested faction → clear error identifying the unresolved unit/loadout rather than silent omission.
- Requested `color_mode` unavailable for a given faction (e.g., only mixed files indexed, no clean split) → clear error or fallback behavior (TBD — flag as open question).
- Loadout swap count exceeds unit size → validation error.

## 7. Non-Functional Requirements

- **Deployment target:** small always-on host ("$30 thin client" class), single exposed API endpoint. No serverless/ephemeral storage assumptions — source PDFs (potentially several GB across factions) and generated output live on local persistent disk.
- **Runtime dependencies:** Flask, `qpdf`/`pikepdf`, SQLite. OCR/Tesseract/LLM dependencies are confined to the offline ingestion pipeline and are not required at runtime.
- **Decoupling:** the API is the integration boundary. It must not assume anything about the caller's stack, so it can be called directly by a human tool, a script, or eventually Army Forge (likely JS/TS) without coupling implementation languages.

## 8. Proposed Repo Structure

```
/ingest    — file classification (color/BW detection, format/pattern sniffing, multi-file intake)
/ocr       — ocrmypdf wrapper, page-image rendering, label-region cropping/isolation
/mapping   — fuzzy match + LLM-assisted file→faction resolution, human-review CLI/contact-sheet tool
/index     — SQLite schema + queries (source_file, source_page, faction, unit, loadout, copies_on_page, color_mode)
/generate  — allocation logic (army list JSON → required page counts) + qpdf/pikepdf invocation
/api       — Flask app exposing the runtime endpoint(s)
```

`ingest`, `ocr`, and `mapping` are one-time/offline tooling and are not deployed to the runtime host. `index`, `generate`, and `api` constitute the deployed runtime service.

## 9. Open Questions

1. What should the API return when a color/BW split isn't cleanly available for a requested mode — best-effort fallback, or hard error?
2. Should the human-review step for LLM-assisted file mapping be a CLI tool, or worth a minimal web UI given it's a recurring (per-faction) task?
3. Do we need versioning/re-indexing support if a publisher updates a mini PDF, or is the index treated as static once confirmed?
4. Should generated output PDFs be cached (e.g., same army list requested twice) or always regenerated fresh? Given qpdf's speed this is likely a non-issue, but worth noting.
5. What's the long-term ownership story if this gets folded into Army Forge — does Army Forge host the index/service, or does it remain a separately-run tool that AF calls out to?

## 10. Success Criteria

- Given a faction's confirmed index and a valid army list, the service returns a single, correctly-ordered/repeated, print-shop-ready PDF in one request.
- Onboarding a new faction (ingestion → confirmed index) requires no manual PDF page-hunting beyond a single review/confirmation pass.
- The API contract is stable and stack-agnostic enough that it could be called by Army Forge without requiring changes to this project's internals.
