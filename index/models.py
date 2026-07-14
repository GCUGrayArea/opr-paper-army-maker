from dataclasses import dataclass
from typing import Optional


@dataclass
class PageEntry:
    """One (unit, loadout) entry appearing on a source PDF page. See PRD §5.2."""

    faction: str
    source_file: str
    source_page: int
    unit: str
    loadout: str
    copies_on_page: int
    color_mode: str  # "color" or "bw"
    confidence: Optional[float] = None
    confirmed: bool = False
    id: Optional[int] = None
