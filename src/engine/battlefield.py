from __future__ import annotations

import logging
from collections.abc import Callable
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

    @staticmethod
    def _tile_index_from_pos(x: float, y: float) -> tuple[int, int]:
        """Convertit une position continue (float) en coordonnées discrètes (tile)."""
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
        tile = self.game_map.ensure_tile(ix, iy)
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
        u_w = unit.width
        u_h = unit.height

        for other in self.units.values():
            # Skip the unit itself
            if other is unit:
                continue

            # Skip dead units
            if not other.is_alive():
                continue

            o_w = other.width
            o_h = other.height
            ox, oy = other.position

            dx = abs(ox - new_x)
            dy = abs(oy - new_y)

            required_x = (u_w + o_w) / 2
            required_y = (u_h + o_h) / 2

            # ALLOW 80% overlap
            overlap_x = required_x - dx
            overlap_y = required_y - dy

            # If they overlap more than 20%, block
            if overlap_x > required_x * 0.8 and overlap_y > required_y * 0.8:
                return True

        return False

    def move_unit_on_map(self, unit: Unit, new_x: float, new_y: float) -> bool:
        """
        Tente de déplacer `unit` à (new_x, new_y).
        - Vérifie les bounds.
        - Vérifie la collision via check_collision (AABB).
        - Si collision : NE FAIT RIEN et retourne False.
        - Si OK : met à jour les occupant/liste de tiles et unit.position, retourne True.
        """
        # Bounds check
        if not (0 <= new_x < self.width and 0 <= new_y < self.height):
            return False

        # Collision check (AABB)
        if self.check_collision(unit, new_x, new_y):
            return False  # Collision detected

        # No collision, apply movement
        old_pos = unit.position
        if old_pos is not None:
            ox, oy = old_pos
            oix, oiy = self._tile_index_from_pos(ox, oy)
            otile = self.game_map.get_tile(oix, oiy)
            if otile is not None:
                otile.remove_occupant(unit)

        # Add to new tile
        ix, iy = self._tile_index_from_pos(new_x, new_y)
        target_tile = self.game_map.ensure_tile(ix, iy)
        target_tile.add_occupant(unit)

        # Update unit position
        unit.position = (float(new_x), float(new_y))
        return True

    # ------------------------
    # requêtes et utilitaires
    # ------------------------

    def get_all_units(self) -> list[Unit]:
        """Renvoie une liste des unités du Battlefield."""
        return list(self.units.values())

    def units_by_owner(self, owner: int) -> list[Unit]:
        """Renvoie une liste des unités appartenant au owner."""
        return [u for u in self.units.values() if u.owner == owner]

    def find_unit(self, unit_id: int) -> Unit | None:
        """Renvoie l'unité ayant l'id unit_id."""
        return self.units.get(unit_id)

    def units_in_radius(self, x: float, y: float, radius: float) -> list[Unit]:
        r2 = radius * radius
        return [
            u
            for u in self.units.values()
            if (dx := u.position[0] - x) * dx + (dy := u.position[1] - y) * dy <= r2
        ]
    
    def units_in_los(self, unit: Unit) -> list[Unit]:
        vision = getattr(unit, "vision_range", 4.0)
        x, y = unit.position
        return [
            u for u in self.units.values()
            if u is not unit and u.is_alive() and unit.dist_to(u) <= vision
        ]
    
    def is_battle_over(self) -> bool:
        """Renvoie True si la bataille est finie."""
        teams_alive = {u.owner for u in self.units.values() if u.is_alive()}
        return len(teams_alive) <= 1

    def snapshot(self) -> dict:
        """Renvoie un snapshot du Battlefield."""
        units_ser = []
        for u in self.units.values():
            units_ser.append({
                "id": u.id,
                "type": u.name,
                "owner": u.owner,
                "position": u.position,
                "hp": u.hp,
                "u_width": u.width,
                "u_height": u.height,
            })
        return {
            "width": self.width,
            "height": self.height,
            "units": units_ser,
            "generals": [str(g) for g in self.generals]
        }