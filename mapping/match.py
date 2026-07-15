from __future__ import annotations

from dataclasses import dataclass

from rapidfuzz import fuzz

from .roster import DEFAULT_LOADOUT, RosterUnit


@dataclass
class MatchResult:
    unit: str
    loadout: str
    unit_score: float
    loadout_score: float

    @property
    def confidence(self) -> float:
        """Worst of the two component scores, 0-1 — a confidently-matched unit
        with an unrecognized loadout should still read as low-confidence
        overall, for the Phase 2 human review queue."""
        return min(self.unit_score, self.loadout_score) / 100.0


def _best_name_score(text: str, names: list[str]) -> float:
    return max(fuzz.WRatio(text, name) for name in names)


def _best_loadout_match(text: str, roster: list[RosterUnit]) -> tuple[RosterUnit, str, float] | None:
    """Best (unit, loadout) match treating `text` as a loadout/title label in
    its own right, searched across every unit's loadouts rather than a
    pre-picked unit. Used for character-title labels (e.g. "Commander",
    "Drill Sergeant") that print with no unit-name line at all."""
    best: tuple[RosterUnit, str, float] | None = None
    for unit in roster:
        for loadout in unit.loadouts:
            score = fuzz.WRatio(text, loadout)
            if best is None or score > best[2]:
                best = (unit, loadout, score)
    return best


def resolve_label(raw_text: str, roster: list[RosterUnit]) -> MatchResult | None:
    """Fuzzy-match an OCR'd label against a faction roster. Two readings are
    tried and the more confident one wins:
    - split: first line is the unit name, second line (if any) is the
      loadout/weapon name, defaulting to DEFAULT_LOADOUT if there's only one
      line — the common bulk/options-sheet row format.
    - title: the whole label (lines rejoined) is itself a loadout/title name
      with no separate unit-name line — hero/squad specialist upgrade pages
      (e.g. "Commander", "Drill Sergeant") print this way, sometimes with
      the title OCR-wrapped across two lines (e.g. "Forward" / "Observer").

    Returns None if there's no text or roster to match against; the caller
    should treat that as an unresolved entry for human review, not a crash.
    """
    if not raw_text.strip() or not roster:
        return None

    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    unit_text = lines[0]
    loadout_text = lines[1] if len(lines) > 1 else None

    best_unit = max(roster, key=lambda u: _best_name_score(unit_text, u.names))
    unit_score = _best_name_score(unit_text, best_unit.names)

    if loadout_text:
        loadout = max(best_unit.loadouts, key=lambda lo: fuzz.WRatio(loadout_text, lo))
        loadout_score = fuzz.WRatio(loadout_text, loadout)
    else:
        loadout = DEFAULT_LOADOUT
        loadout_score = 100.0

    as_split = MatchResult(
        unit=best_unit.canonical_name,
        loadout=loadout,
        unit_score=unit_score,
        loadout_score=loadout_score,
    )

    title_match = _best_loadout_match(" ".join(lines), roster)
    if title_match is not None:
        title_unit, title_loadout, title_score = title_match
        as_title = MatchResult(
            unit=title_unit.canonical_name,
            loadout=title_loadout,
            unit_score=title_score,
            loadout_score=title_score,
        )
        if as_title.confidence > as_split.confidence:
            return as_title

    return as_split
