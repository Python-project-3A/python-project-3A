from __future__ import annotations

import logging
from collections.abc import Callable
from math import hypot  # distance euclidienne : sqrt(dx*dx + dy*dy)
from typing import Any

from src.map.game_map import GameMap
from src.units.unit_base import Unit

logger = logging.getLogger(__name__)


class Battlefield:
    """
    Battlefield: état global. Gère:
    - game_map
    - unités
    - généraux (liste)
    - spawn/add/remove/move with collision checking based on unit.size (radius)
    """

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.game_map: GameMap = GameMap(width, height)
        self.units: dict[int, Unit] = {}
        self.generals: list[Any] = []
        logger.info("Battlefield initialized %dx%d", width, height)

    @staticmethod  # fontion dans une classe qui ne dépend pas de self
    def _tile_index_from_pos(x: float, y: float) -> tuple[int, int]:
        """Convertit une position continue (float) en coordonnées discrètes (tile) en utilisant un arrondi inférieur (floor)."""
        return int(x), int(y)

    # ------------------------
    # spawn / add / remove units
    # ------------------------
    def spawn_unit(self, unit_factory: Callable[[], Any], x: float, y: float, owner: int) -> int:
        """
        Créer une instance unité via une fonction factory et l'ajoute au Battlefield.
        Renvoie l'id de l'unité.
        """
        unit = unit_factory()
        unit.position = (float(x), float(y))
        unit.owner = owner

        ix, iy = self._tile_index_from_pos(x, y)
        # ensure tile exists
        tile = self.game_map.ensure_tile(ix, iy)
        # add unit to structures
        tile.add_occupant(unit)
        self.units[unit.id] = unit
        logger.debug("spawned unit %s at (%.2f,%.2f) owner=%s", unit.id, x, y, owner)
        return unit.id

    def add_existing_unit(self, unit: Unit) -> int:
        """Ajoute une unité existante au Battlefield."""
        if not hasattr(unit, "position"):
            raise ValueError("add_existing_unit: unit n'a pas de position")

        x, y = unit.position
        unit.position = (float(x), float(y))
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
        x, y = unit.position
        ix, iy = self._tile_index_from_pos(x, y)
        tile = self.game_map.get_tile(ix, iy)
        if tile is not None:
            tile.remove_occupant(unit)
        logger.debug("removed unit %s", unit_id)

    # ------------------------
    # mouvement
    # ------------------------
    def check_collision(self, unit: Unit, new_x: float, new_y: float) -> bool:
        """
        Vérifie s'il y a collision AABB entre `unit` déplacée à (new_x,new_y)
        et n'importe quelle autre unité.
        Retourne True s'il y a collision, False sinon.
        NE MODIFIE RIEN.
        """
        u_w = unit.width
        u_h = unit.height

        for other in self.units.values():
            # on ignore l'unité testée
            if other is unit:
                continue

            if not other.is_alive():
                continue

            o_w = other.width
            o_h = other.height

            # Test AABB : il doit y avoir chevauchement sur les 2 axes pour collision
            ox, oy = other.position
            overlap_x = abs(ox - new_x) < (u_w / 2 + o_w / 2)
            overlap_y = abs(oy - new_y) < (u_h / 2 + o_h / 2)

            return overlap_x and overlap_y  # collision détectée

        return False  # pas de collision

    def move_unit_on_map(self, unit: Unit, new_x: float, new_y: float) -> bool:
        """
        Tente de déplacer `unit` à (new_x, new_y).
        - Vérifie les bounds.
        - Vérifie la collision via check_collision (AABB).
        - Si collision : NE FAIT RIEN et retourne False.
        - Si OK : met à jour les occupant/liste de tiles et unit.position, retourne True.
        """
        # bounds check
        if not (0 <= new_x < self.width and 0 <= new_y < self.height):
            # hors carte -> pas de déplacement
            return False

        # collision check (AABB)
        if self.check_collision(unit, new_x, new_y):
            return False  # collision détectée -> on n'applique pas le déplacement

        # --- Aucune collision, on applique le déplacement ---

        # retirer de l'ancienne tile
        old_pos = unit.position
        if old_pos is not None:
            ox, oy = old_pos
            oix, oiy = self._tile_index_from_pos(ox, oy)
            otile = self.game_map.get_tile(oix, oiy)
            if otile is not None:
                otile.remove_occupant(unit)

        # ajouter à la nouvelle tile (on s'assure qu'elle existe)
        ix, iy = self._tile_index_from_pos(new_x, new_y)
        target_tile = self.game_map.ensure_tile(ix, iy)
        target_tile.add_occupant(unit)

        # mise à jour des coordonnées de l'unité
        unit.position = (float(new_x), float(new_y))
        # logger.debug("unit %s moved to (%.2f,%.2f)", getattr(unit, "id", None), new_x, new_y)

        return True

    # ------------------------
    # requêtes et utilitaires
    # ------------------------
    def get_all_units(self) -> list[Unit]:
        """Renvoie une liste des unité du Battlefield."""
        return list(self.units.values())

    def units_by_owner(self, owner: int) -> list[Unit]:
        """Renvoie une liste des unité du Battlefield appartenant au team owner."""
        return [u for u in self.units.values() if getattr(u, "owner", None) == owner]

    def find_unit(self, unit_id: int) -> Unit | None:
        """Renvoie l'unité ayant l'id unit_id."""
        return self.units.get(unit_id)

    def units_in_radius(self, x: float, y: float, radius: float) -> list[Unit]:
        """Renvoie une liste des unité du Battlefield dans un rayon de radius autour de (x,y)."""
        result: list[Unit] = []
        for u in self.units.values():
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
                    "id": getattr(u, "id", None),
                    "type": getattr(u, "type", getattr(u, "__class__", type(u)).__name__),
                    "owner": getattr(u, "owner", None),
                    "position": getattr(u, "position", None),
                    "hp": getattr(u, "hp", None),
                    "u_width": getattr(u, "width", None),
                    "u_height": getattr(u, "height", None),
                }
            )
        return {"width": self.width, "height": self.height, "units": units_ser, "generals": [str(g) for g in self.generals]}
