from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_LOADOUT = "Default"


@dataclass
class RosterUnit:
    """A unit's canonical names and the loadout names it can be printed with —
    its default weapons plus every weapon it can be upgraded/swapped to,
    sourced from an Army Forge army book export (see PRD open question on
    roster source)."""

    names: list[str]
    loadouts: list[str] = field(default_factory=lambda: [DEFAULT_LOADOUT])

    @property
    def canonical_name(self) -> str:
        return self.names[0]


def load_army_book(path: str | Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# Both gain types show up as their own printed mini-sheet row/page (a distinct
# weapon swap, or a distinct named character title such as "Commander" /
# "Drill Sergeant" granted by a hero- or squad-model upgrade), so both are
# matchable loadout labels. ArmyBookRule gains are excluded — a rules-text
# buff with no separate sculpt (e.g. a vehicle transport rule) isn't a label
# that will ever appear printed on a sheet.
LOADOUT_GAIN_TYPES = {"ArmyBookWeapon", "ArmyBookItem"}


def extract_roster(army_book: dict) -> list[RosterUnit]:
    """Build one RosterUnit per unit in an army book, with loadouts collected
    from the unit's base weapons plus every weapon-swap or named-character-title
    upgrade option reachable from it."""
    packages_by_uid = {p["uid"]: p for p in army_book.get("upgradePackages", [])}

    roster = []
    for unit in army_book.get("units", []):
        names = [n for n in (unit.get("name"), unit.get("genericName")) if n]
        loadouts = {DEFAULT_LOADOUT}
        for upgrade_uid in unit.get("upgrades", []):
            package = packages_by_uid.get(upgrade_uid)
            if not package:
                continue
            for section in package.get("sections", []):
                for option in section.get("options", []):
                    for gain in option.get("gains", []):
                        if gain.get("type") in LOADOUT_GAIN_TYPES and gain.get("name"):
                            loadouts.add(gain["name"])
        roster.append(RosterUnit(names=names, loadouts=sorted(loadouts)))
    return roster
