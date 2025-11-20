from dataclasses import dataclass, field
from typing import Any, List

@dataclass
class Tile:
    terrain: str = "grass"  
    elevation: float = 0.0
    occupants: List[Any] = field(default_factory=list)

    def is_free(self) -> bool:
        return len(self.occupants) == 0

    def add_occupant(self, unit: Any):
        self.occupants.append(unit)

    def remove_occupant(self, unit: Any):
        if unit in self.occupants:
            self.occupants.remove(unit)
