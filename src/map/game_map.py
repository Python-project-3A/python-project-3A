from __future__ import annotations
from typing import Optional
from .tile import Tile
import math


class GameMap:
    """
    Représente la carte du jeu sous forme de grille discrète (tiles).
    Les unités, elles, évoluent dans un espace continu (floats).

    - width, height : taille de la carte (en nombre de tiles)
    - tiles[(i, j)] : Tile correspondant à la position entière (i, j)
    """

    def __init__(self, width: int, height: int):
        self.width = int(width)
        self.height = int(height)

        # Grille régulière : toutes les tiles sont créées à l’initialisation
        self.tiles: dict[tuple[int, int], Tile] = {
            (x, y): Tile()
            for x in range(self.width)
            for y in range(self.height)
        }

    # ---------------------------------------------------------
    # TILE ACCESS (ENTIÈRES)
    # ---------------------------------------------------------
    def get_tile(self, i: int, j: int) -> Optional[Tile]:
        """Retourne la Tile aux coordonnées entières (i, j)."""
        if 0 <= i < self.width and 0 <= j < self.height:
            return self.tiles[(i, j)]
        return None

    def is_tile_free(self, i: int, j: int) -> bool:
        """True si la tile entière (i, j) n'a pas d’occupants."""
        tile = self.get_tile(i, j)
        return tile is not None and tile.is_free()

    # ---------------------------------------------------------
    # FLOAT → TILE CONVERSION
    # ---------------------------------------------------------
    def tile_from_float(self, x: float, y: float) -> Optional[Tile]:
        """
        Retourne la Tile correspondant à la position continue (x, y).
        Projection standard : on utilise floor().
        """
        i = math.floor(x)
        j = math.floor(y)
        return self.get_tile(i, j)

    def is_free(self, x: float, y: float) -> bool:
        """
        Vérifie si la tile correspondant à la position float (x, y) est libre.
        """
        tile = self.tile_from_float(x, y)
        return tile is not None and tile.is_free()

    # ---------------------------------------------------------
    # MISC
    # ---------------------------------------------------------
    def __contains__(self, coords: tuple[int, int]) -> bool:
        """Permet :    (i, j) in game_map  """
        return coords in self.tiles

    def __repr__(self):
        return f"<GameMap {self.width}x{self.height}>"
