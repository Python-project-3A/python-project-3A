from __future__ import annotations

from .tile import Tile


class GameMap:
    """
    Sparse grid map: dict[(ix, iy)] -> Tile.
    Units move in continuous space (floats),
    terrain and occupancy are indexed by integer tiles.
    """

    def __init__(self, width: int, height: int):
        self.width = int(width)
        self.height = int(height)
        self.tiles: dict[tuple[int, int], Tile] = {}  # sparse

    # --------------------------
    # Bounds
    # --------------------------
    def _in_bounds(self, ix: int, iy: int) -> bool:
        return 0 <= ix < self.width and 0 <= iy < self.height

    # --------------------------
    # Discrete access
    # --------------------------
    def get_tile(self, ix: int, iy: int) -> Tile | None:
        """Return the tile if stored (sparse)."""
        return self.tiles.get((ix, iy))

    def add_tile(self, ix: int, iy: int, tile: Tile | None = None) -> None:
        """Create or replace a tile at integer coords."""
        if not self._in_bounds(ix, iy):
            raise ValueError("add_tile: out of bounds")
        if tile is None:
            tile = Tile()
        self.tiles[(ix, iy)] = tile

    def ensure_tile(self, ix: int, iy: int) -> Tile:
        """Return a tile; create if absent."""
        if not self._in_bounds(ix, iy):
            raise ValueError("ensure_tile: out of bounds")

        tile = self.tiles.get((ix, iy))
        if tile is None:
            tile = Tile()
            self.tiles[(ix, iy)] = tile
        return tile

    def is_free(self, ix: int, iy: int) -> bool:
        """True if tile has no occupants or is not present (default empty)."""
        tile = self.get_tile(ix, iy)
        return tile is None or tile.is_free()

    # --------------------------
    # Float → Tile conversion
    # --------------------------
    def tile_from_float(self, x: float, y: float) -> Tile | None:
        ix = int(x)
        iy = int(y)
        if not self._in_bounds(ix, iy):
            return None
        return self.ensure_tile(ix, iy)

    def is_free_float(self, x: float, y: float) -> bool:
        tile = self.tile_from_float(x, y)
        return tile.is_free() if tile else False

    # --------------------------
    # Utils
    # --------------------------
    def __contains__(self, coords):
        return coords in self.tiles

    def __repr__(self):
        return f"<SparseGameMap {self.width}x{self.height} / {len(self.tiles)} tiles>"
