# src/engine/battlefield.py
from __future__ import annotations
from typing import Dict, List, Tuple, Optional, Callable, Any
import logging
from math import hypot  # distance euclidienne : sqrt(dx*dx + dy*dy)

# Try to import the real GameMap/Tile; if module not present (dev stage),
# provide a very small mock to allow running tests.
try:
    from src.map.game_map import GameMap
    from src.map.tile import Tile
except Exception:
    # Minimal mock implementations for local testing
    class Tile:
        """
        Représente une case de terrain (grid cell).
        - occupants : liste d'unités présentes sur la tile (peut être vide)
        - terrain : string (ex: "grass", "water", "rock")
        - elevation : int (hauteur)
        """

        def __init__(self, elevation: int = 0):  # , terrain: str = "grass"):
            self.elevation = elevation
            self.occupants: List[Any] = []  # liste d'unités

        def is_free(self) -> bool:
            """Considère 'free' si pas d'occupants."""  # NB : On peut redéfinir la logique si besoin -> nottament pour la taille des unités, si elles "rentrent ou non sur cette Tile"
            return len(self.occupants) == 0

        def add_occupant(self, unit: Any) -> None:
            """Ajoute une unité à occupants."""
            self.occupants.append(unit)

        def remove_occupant(self, unit: Any) -> None:
            """Retire une unité si présente."""
            try:
                self.occupants.remove(unit)
            except ValueError:
                pass

        # rajouter un get tile ?

    class GameMap:
        """
        Sparse grid map: dict[(ix,iy)] -> Tile.
        - The indexing (ix,iy) are integers (tile indices).
        - Units keep float positions; we map floats to tile index via int(x), int(y).
        """

        def __init__(self, width: int, height: int):
            self.width = width
            self.height = height
            # self.tile lie une clé (x, y) → tuple d’entiers vers une valeur Tile (objet Tile)
            self.tiles: Dict[Tuple[int, int], Tile] = {}

        def _in_bounds(self, ix: int, iy: int) -> bool:
            """Test si (x, y) est dans la carte."""
            return 0 <= ix < self.width and 0 <= iy < self.height

        def add_tile(self, ix: int, iy: int, tile: Optional[Tile] = None) -> None:
            """Ajoute une tile en (ix, iy)."""
            if not self._in_bounds(ix, iy):
                raise ValueError("add_tile: out of bounds")
            if tile is None:
                tile = Tile()
            self.tiles[(ix, iy)] = tile

        def get_tile(self, ix: int, iy: int) -> Optional[Tile]:
            """Récupère une tile en (ix, iy) si présent, renvoie None sinon."""
            return self.tiles.get((ix, iy))

        def ensure_tile(self, ix: int, iy: int) -> Tile:
            """Retourne un tile ou le crée si absent."""
            if not self._in_bounds(ix, iy):
                raise ValueError("ensure_tile: out of bounds")
            t = self.get_tile(ix, iy)
            if t is None:
                t = Tile()
                self.tiles[(ix, iy)] = t
            return t

        def is_free(self, ix: int, iy: int) -> bool:
            """Vérifie si la tile existe, et si elle est vide renvoie True"""  # plus si terrain walkable et pas d'obstacle ?
            if not self._in_bounds(ix, iy):
                return False
            t = self.get_tile(ix, iy)
            return (t is None) or t.is_free()  # ATTENTION : is_free() = méthode du TILE ici -> NB : peut être qu'il faut changer de non une des deux fonctions


logger = logging.getLogger(__name__)


class Battlefield:
    """
    Battlefield: état global. Gère:
    - game_map
    - unités (dict id -> instance)
    - généraux (liste)
    - spawn/add/remove/move with collision checking based on unit.size (radius)
    """

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.game_map: GameMap = GameMap(width, height)
        self.units: Dict[int, Any] = {}
        self.generals: List[Any] = []
        self._next_unit_id: int = 1
        logger.info("Battlefield initialized %dx%d", width, height)

    # ------------------------
    # internal helpers
    # ------------------------
    def _assign_id_if_needed(self, unit: Any) -> None:
        """Assigne un id si besoin."""
        if not hasattr(unit, "id") or getattr(unit, "id") is None:
            unit.id = self._next_unit_id
            self._next_unit_id += 1

    @staticmethod  # fontion dans une classe qui ne dépend pas de self
    def _tile_index_from_pos(x: float, y: float) -> Tuple[int, int]:
        """Convertit une position continue (float) en coordonnées discrètes (tile) en utilisant un arrondi inférieur (floor)."""
        # NB : int(3.99) → 3 -> jsp si c'est la meilleur option
        return int(x), int(y)

    # ------------------------
    # spawn / add / remove units
    # ------------------------
    def spawn_unit(self, unit_factory: Callable[[], Any], x: float, y: float, owner: int) -> int:
        """
        Créer une instance unité via une fonction factory et l'ajoute au Battlefield.
        L'unité doit avoir une .position (tuple) et un .owner., optionnellement .size (float radius), .hp
        """
        unit = unit_factory()
        self._assign_id_if_needed(unit)
        unit.position = (float(x), float(y))
        unit.owner = owner
        unit.battlefield = self
        unit.x, unit.y = x, y
        # taille par defaut  (0.4 tile radius)
        if not hasattr(unit, "size"):
            unit.size = 0.4

        ix, iy = self._tile_index_from_pos(x, y)
        # ensure tile exists
        tile = self.game_map.ensure_tile(ix, iy)
        # add unit to structures
        tile.add_occupant(unit)
        self.units[unit.id] = unit
        logger.debug("spawned unit %s at (%.2f,%.2f) owner=%s", unit.id, x, y, owner)
        return unit.id

    def add_existing_unit(self, unit: Any) -> int:
        """Ajoute une unité existante au Battlefield."""
        if not hasattr(unit, "position"):
            raise ValueError("add_existing_unit: unit n'a pas de position")
        x, y = unit.position
        unit.position = (float(x), float(y))
        self._assign_id_if_needed(unit)
        if not hasattr(unit, "size"):
            unit.size = 0.4
        ix, iy = self._tile_index_from_pos(x, y)
        tile = self.game_map.ensure_tile(ix, iy)
        tile.add_occupant(unit)
        self.units[unit.id] = unit
        logger.debug("added existing unit %s at (%.2f,%.2f)", unit.id, x, y)
        return unit.id

    def remove_unit(self, unit_id: int) -> None:
        """Supprime l'unité ayant l'id unit_id."""
        unit = self.units.pop(unit_id, None)
        if unit is None:
            return
        x, y = getattr(unit, "position", (None, None))
        if x is not None:
            ix, iy = self._tile_index_from_pos(x, y)
            tile = self.game_map.get_tile(ix, iy)
            if tile is not None:
                tile.remove_occupant(unit)
        logger.debug("removed unit %s", unit_id)

    # ------------------------
    # mouvement avec collision
    # ------------------------
    def move_unit_on_map(self, unit: Any, new_x: float, new_y: float, push: bool = False) -> None:
        """
        Déplacement unité vers (new_x,new_y)
        - terrain
        - terrain block (example: eau)
        - collision : assure aucune collision avec les unités existantes (avec les tailles)
        Si push=True, va essayer de faire un push naif (pas implémenté completement).
        Raises ValueError si déplacement invalide.
        """
        # bounds check # TODO remplacer par la méthode in_bounds
        if not (0 <= new_x < self.width and 0 <= new_y < self.height):
            raise ValueError("move_unit_on_map: target out of bounds")

        # tile check (example terrain block)
        ix, iy = self._tile_index_from_pos(new_x, new_y)
        tile = self.game_map.get_tile(ix, iy)

        # terrain check (pas utile pour l'instant)
        # if tile is not None and getattr(tile, "terrain", None) == "water":
        #     raise ValueError("move_unit_on_map: target blocked by water")

        # collision check with all units (naive O(n); optimize later)
        # unit must have .size attribute (radius)
        u_size = getattr(unit, "size", 0.4)
        for other in self.units.values():
            if other is unit:
                continue
            op = getattr(other, "position", None)
            if op is None:
                continue
            ox, oy = op
            # compute euclidean distance
            dist = hypot(ox - new_x, oy - new_y)
            other_size = getattr(other, "size", 0.4)
            if dist < (u_size + other_size):
                # collision!
                if push:
                    # naive: do not implement complex pushing here; raise for now
                    raise ValueError("move_unit_on_map: collision (would need push handling)")
                else:
                    raise ValueError("move_unit_on_map: collision with unit %s" % getattr(other, "id", "?"))

        # passed checks -> update occupant lists and unit.position
        old_pos = getattr(unit, "position", (None, None))
        if old_pos is not None:
            ox, oy = old_pos
            oix, oiy = self._tile_index_from_pos(ox, oy)
            otile = self.game_map.get_tile(oix, oiy)
            if otile is not None:
                otile.remove_occupant(unit)

        # ensure target tile exists
        target_tile = self.game_map.ensure_tile(ix, iy)
        target_tile.add_occupant(unit)
        unit.position = (float(new_x), float(new_y))
        logger.debug("unit %s moved to (%.2f,%.2f)", getattr(unit, "id", None), new_x, new_y)

    # ------------------------
    # requêtes et utilitaires
    # ------------------------
    def get_all_units(self) -> List[Any]:
        """Renvoie une liste des unité du Battlefield."""
        return list(self.units.values())

    def units_by_owner(self, owner: int) -> List[Any]:
        """Renvoie une liste des unité du Battlefield appartenant au team owner."""
        return [u for u in self.units.values() if getattr(u, "owner", None) == owner]

    def find_unit(self, unit_id: int) -> Optional[Any]:
        """Renvoie l'unité ayant l'id unit_id."""
        return self.units.get(unit_id)

    def units_in_radius(self, x: float, y: float, radius: float) -> List[Any]:
        """Renvoie une liste des unité du Battlefield dans un rayon de radius autour de (x,y)."""
        result: List[Any] = []
        for u in self.units.values():
            ux, uy = getattr(u, "position", (None, None))
            if ux is None:
                continue
            if hypot(ux - x, uy - y) <= float(radius):
                result.append(u)
        return result

    def is_battle_over(self) -> bool:
        """Renvoie True si la bataille est finie."""
        teams_alive = {u.owner for u in self.units.values() if getattr(u, "is_alive", lambda: False)()}
        return len(teams_alive) <= 1

    def snapshot(self) -> dict:
        """Renvoie un snapshot du Battlefield."""
        units_ser = []
        for u in self.units.values():
            units_ser.append(
                {
                    "id": getattr(u, "id", None),
                    "type": getattr(u, "type", getattr(u, "__class__", type(u)).__name__),
                    "owner": getattr(u, "owner", None),
                    "position": getattr(u, "position", None),
                    "hp": getattr(u, "hp", None),
                    "size": getattr(u, "size", None),
                }
            )
        return {"width": self.width, "height": self.height, "units": units_ser, "generals": [str(g) for g in self.generals]}
