from __future__ import annotations

from .tile import Tile


class GameMap:
    """
    Stores static and semi-static world grid (tiles, walkability, terrain).
    Does NOT know unit logic or collisions.
    """

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.tiles: dict[tuple[int, int], Tile] = {}

    # --------------------------
    # Bounds / Tile access
    # --------------------------
    def in_bounds(self, ix: int, iy: int) -> bool:
        return 0 <= ix < self.width and 0 <= iy < self.height

    def get_tile(self, ix: int, iy: int) -> Tile | None:
        return self.tiles.get((ix, iy))

    def ensure_tile(self, ix: int, iy: int) -> Tile:
        if not self.in_bounds(ix, iy):
            raise ValueError("Out of bounds")
        return self.tiles.setdefault((ix, iy), Tile())

    # --------------------------
    # Terrain / Walkability
    # --------------------------
    def is_walkable(self, ix: int, iy: int) -> bool:
        if not self.in_bounds(ix, iy):
            return False
        # later: check terrain, cliffs, water
        return True

    # --------------------------
    # Tile neighbors
    # --------------------------
    def neighbors(self, ix: int, iy: int, diag=False):
        around = [(ix + 1, iy), (ix - 1, iy), (ix, iy + 1), (ix, iy - 1)]
        if diag:
            around += [(ix + 1, iy + 1), (ix + 1, iy - 1), (ix - 1, iy + 1), (ix - 1, iy - 1)]
        return [(x, y) for (x, y) in around if self.in_bounds(x, y)]

    # --------------------------
    # Tile occupancy (no logic)
    # --------------------------
    def add_occupant(self, ix: int, iy: int, unit):
        tile = self.ensure_tile(ix, iy)
        tile.add_occupant(unit)

    def remove_occupant(self, ix: int, iy: int, unit):
        tile = self.get_tile(ix, iy)
        if tile:
            tile.remove_occupant(unit)

    def init_map(self):
        self.tiles = {(i, j): Tile() for i in range(self.width) for j in range(self.height)}
