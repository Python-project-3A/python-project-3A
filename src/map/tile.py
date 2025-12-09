from dataclasses import field

from src.units.unit_base import Unit


class Tile:
    """
    Représente une case de terrain (grid cell).
    - occupants : liste d'unités présentes sur la tile (peut être vide)
    - terrain : string (ex: "grass", "water", "rock")
    - elevation : float (hauteur)
    """

    __slots__ = ("terrain", "elevation", "occupants")

    def __init__(self, terrain: str = "grass", elevation: float = 0.0):
        self.terrain = terrain
        self.elevation = elevation
        self.occupants: list[Unit] = []

    def is_free(self) -> bool:
        """Considère 'free' si pas d'occupants."""
        return not self.occupants

    def add_occupant(self, unit: Unit):
        """Ajoute une unité à occupants."""
        self.occupants.append(unit)

    def remove_occupant(self, unit: Unit):
        """Retire l'unité de occupants."""
        # if unit in self.occupants:
        #     self.occupants.remove(unit)
        # Optimisation : try/except est plus rapide que "if in" si l'erreur est rare
        try:
            self.occupants.remove(unit)
        except ValueError:
            pass
