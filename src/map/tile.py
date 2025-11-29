from dataclasses import dataclass, field

from src.units.unit_base import Unit


@dataclass
class Tile:
    terrain: str = "grass"
    elevation: float = 0.0
    occupants: list[Unit] = field(default_factory=list)

    def is_free(self) -> bool:
        return len(self.occupants) == 0

    def add_occupant(self, unit: Unit):
        self.occupants.append(unit)

    def remove_occupant(self, unit: Unit):
        if unit in self.occupants:
            self.occupants.remove(unit)
