from .tile import Tile


class GameMap:
    """
    Représente la carte du jeu dans un espace continu.
    """

    def __init__(self, width: float, height: float):
        self.width = float(width)
        self.height = float(height)
        self.tiles: dict[tuple[float, float], Tile] = {}

    def add_tile(self, x: float, y: float, tile: Tile | None = None):
        """Ajoute une zone (x, y) sur la carte."""
        self._check_bounds(x, y)
        if tile is None:
            tile = Tile()
        self.tiles[(x, y)] = tile

    def get_tile(self, x: float, y: float):
        """Récupère la zone (x, y) s’il y en a une (coordonnée exacte)."""
        return self.tiles.get((x, y))

    def is_free(self, x: float, y: float) -> bool:
        """Retourne True si la position (x, y) n'est pas occupée."""
        tile = self.tiles.get((x, y))
        return tile is None or tile.is_free()

    def _check_bounds(self, x: float, y: float):
        """Vérifie que la position est dans les limites de la carte."""
        if not (0.0 <= x <= self.width and 0.0 <= y <= self.height):
            raise ValueError(
                f"Position ({x}, {y}) out of bounds for map {self.width}x{self.height}"
            )

    def __contains__(self, coords: tuple[float, float]):
        return coords in self.tiles

    def __repr__(self):
        return f"<GameMap {self.width}x{self.height}, {len(self.tiles)} zones>"
