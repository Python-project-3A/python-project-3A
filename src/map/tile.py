from dataclasses import dataclass, field
from typing import Any


@dataclass
class Tile:
    """
    Représente une case de terrain (grid cell).
    - occupants : liste d'unités présentes sur la tile (peut être vide)
    - terrain : string (ex: "grass", "water", "rock")
    - elevation : float (hauteur)
    """

    terrain: str = "grass"
    elevation: float = 0.0
    occupants: list[Any] = field(default_factory=list)

    def is_free(self) -> bool:
        """Considère 'free' si pas d'occupants."""
        return len(self.occupants) == 0

    def add_occupant(self, unit: Any):
        """Ajoute une unité à occupants."""
        self.occupants.append(unit)

    def remove_occupant(self, unit: Any):
        """Retire l'unité de occupants."""
        if unit in self.occupants:
            self.occupants.remove(unit)
