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

    # ---------- HELEPERS--------------
    def isalmost(self, n, m, d=1e-2):  # 1e-2 ou 1e-3 ???
        return (abs(n - m)) < d

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

    def spawn_unit(self, unit_factory: Callable[[], Any], x: float, y: float, owner: int) -> int:
        """
        Créer une instance unité via une fonction factory et l'ajoute au Battlefield.
        Renvoie l'id de l'unité.
        """
        unit = unit_factory()
        self._assign_id_if_needed(unit)
        unit.position = (float(x), float(y))
        unit.owner = owner
        unit.battlefield = self

        ix, iy = self._tile_index_from_pos(x, y)
        # ensure tile exists
        tile = self.game_map.ensure_tile(ix, iy)
        # add unit to structures
        tile.add_occupant(unit)
        self.units[unit.id] = unit
        logger.debug("spawned unit %s at (%.2f,%.2f) owner=%s", unit.id, x, y, owner)
        return unit.id

    def add_existing_unit(self, unit) -> int:
        """Ajoute une unité existante au Battlefield (tile) et renvoie son id."""
        x, y = unit.position
        self._assign_id_if_needed(unit)
        tx, ty = self._tile_index_from_pos(x, y)
        tile = self.game_map.ensure_tile(tx, ty)
        tile.add_occupant(unit)
        self.units[unit.id] = unit
        return unit.id

    def _add_unit_to_tile(self, unit, x, y):
        """Ajoute une unité à une tile via sa position."""
        ix, iy = self._tile_index_from_pos(x, y)
        tile = self.game_map.ensure_tile(ix, iy)
        tile.add_occupant(unit)
        unit.position = (float(x), float(y))

    def remove_unit(self, unit_id: int) -> None:
        """Supprime l'unité ayant l'id unit_id."""
        unit = self.units.pop(unit_id, None)
        x, y = unit.position
        tx, ty = self._tile_index_from_pos(x, y)
        tile = self.game_map.get_tile(tx, ty)
        if tile:
            tile.remove_occupant(unit)

    def check_position(self, unit, new_x: float, new_y: float) -> bool:
        """vérifie si une unité est présente sur ces coordonnées."""
        for other in self.units.values():
            if other is unit:
                continue
            if self.isalmost(other.position[0], new_x) and self.isalmost(other.position[1], new_y):
                return True
        return False

    def _remove_unit_from_old_tile(self, unit):
        """Retire l'unité de la tile correspondant à son ancienne position."""
        ox, oy = unit.position
        otx, oty = self._tile_index_from_pos(ox, oy)
        tile = self.game_map.get_tile(otx, oty)
        if tile:  # sécurité minimale
            tile.remove_occupant(unit)

    def in_map(self, x: float, y: float) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    # ------------- MOUVEMENT --------------

    def attempt_sliding_move(self, unit, new_x, new_y):
        """Tente un glissement si le mouvement direct est bloqué.
        Retourne (x,y) soit corrigé soit identique.
        """

        # mouvement direct
        if not self.check_collision(unit, new_x, new_y):
            return new_x, new_y

        ux, uy = unit.position

        # 1) slide horizontal
        if not self.check_collision(unit, new_x, uy):
            return new_x, uy

        # 2) slide vertical
        if not self.check_collision(unit, ux, new_y):
            return ux, new_y

        # 3) petit décalage orthogonal
        eps = 0.3
        if not self.check_collision(unit, new_x, new_y + eps):
            return new_x, new_y + eps
        if not self.check_collision(unit, new_x, new_y - eps):
            return new_x, new_y - eps

        # rien à faire → bloqué
        return unit.position

    def move_unit_on_map(self, unit: Any, new_x: float, new_y: float) -> bool:
        """
        Tente de déplacer `unit` à (new_x, new_y).
        - Vérifie les bordures de map.
        - Vérifie la collision (position).
        - Si collision : tente un slide move.
        - Si OK : met à jour les occupant/liste de tiles et unit.position, retourne True.
        """
        # --------- CHECK BORDURES  ----------
        if not self.in_map(new_x, new_y):
            return False  # hors carte -> pas de déplacement

        # --------- CHECK COLLISION ---------
        if self.check_position(unit, new_x, new_y):
            sx, sy = self.attempt_sliding_move(unit, new_x, new_y)
            if (sx, sy) == unit.position:
                return False  # bloqué -> pas de déplacement
            new_x, new_y = sx, sy  # sinon on remplace la cible par la version slidée

        # --- Aucune collision, on applique le déplacement -------------
        self._remove_unit_from_old_tile(unit)  # retirer de l'ancienne tile
        self._add_unit_to_tile(unit, new_x, new_y)  # ajouter à la nouvelle

        return True

    # ------------- UTILS --------------
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
        for u in self.get_all_units():
            ux, uy = u.position
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
                    "id": u.id,
                    "type": u.name,
                    "owner": u.owner,
                    "position": u.position,  # "position": tuple(int(v * 100) / 100 for v in u.position
                    "hp": u.hp,
                    "u_width": u.width,
                    "u_height": u.height,
                }
            )
        return {"width": self.width, "height": self.height, "units": units_ser, "generals": [str(g) for g in self.generals], "tiles": len(self.game_map.tiles)}
