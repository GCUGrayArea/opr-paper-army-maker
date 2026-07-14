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


def resolve_label(raw_text: str, roster: list[RosterUnit]) -> MatchResult | None:
    """Fuzzy-match an OCR'd label (one line — unit only, defaulted loadout — or
    two lines — unit, then loadout/weapon name) against a faction roster.
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

    return MatchResult(
        unit=best_unit.canonical_name,
        loadout=loadout,
        unit_score=unit_score,
        loadout_score=loadout_score,
    )
