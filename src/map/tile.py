from dataclasses import dataclass


@dataclass
class Tile:
    """
    Représente une case (tuile) du terrain.

    Attributes
    ----------
    terrain : str
        Type de terrain (ex: 'grass', 'water', 'rock').
    elevation : int
        Niveau de hauteur (utile pour les bonus de combat).
    occupied : Optional[object]
        Référence vers un occupant (unité, obstacle...), None si libre.
    """

    elevation: float = 0
    occupied: object | None = None

    def is_free(self):
        """Retourne True si la case n'est pas occupée."""
        return self.occupied is None
