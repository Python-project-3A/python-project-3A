from __future__ import annotations

import logging
import math
from collections.abc import Callable
from typing import Any

from src.general.general_base import BaseGeneral
from src.map.game_map import GameMap
from src.units.unit_base import Unit

logger = logging.getLogger(__name__)


class Battlefield:
    """
    Battlefield:
    - manages units & tiles
    - NEW: merged circular collision + sliding + soft_push from old system
    """

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.next_unit_id = 1
        self.game_map: GameMap = GameMap(width, height)
        self.units: dict[int, Unit] = {}
        self.generals: list[BaseGeneral] = []
        logger.info("Battlefield initialized %dx%d", width, height)

    @staticmethod
    def _tile_index_from_pos(x: float, y: float) -> tuple[int, int]:
        """Convertit une position continue (float) en coordonnées discrètes (tile)."""
        return int(x), int(y)

    def assign_unit_id(self, unit) -> int:
        if unit.id is not None:
            if unit.id >= self.next_unit_id:  #  on s'assure que notre compteur est à jour
                self.next_unit_id = unit.id + 1
            return unit.id
        unit.id = self.next_unit_id
        self.next_unit_id += 1
        return unit.id

    def isalmost(self, n, m, d=1e-2):  # 1e-2 ou 1e-3 ???
        return (abs(n - m)) < d

    # -----------------------------------------------------
    # SPAWN / REMOVE
    # -----------------------------------------------------
    def spawn_unit(self, unit_factory: Callable[[], Any], x: float, y: float, owner: int) -> int:
        """
        Créer une instance unité via une fonction factory et l'ajoute au Battlefield.
        Renvoie l'id de l'unité.
        """
        unit = unit_factory()
        unit.position = (float(x), float(y))
        unit.owner = owner
        self.assign_unit_id(unit)

        ix, iy = self._tile_index_from_pos(x, y)
        tile = self.game_map.ensure_tile(ix, iy)
        tile.add_occupant(unit)

        self.units[unit.id] = unit
        return unit.id

    def add_existing_unit(self, unit: Unit) -> int:
        """Ajoute une unité existante au Battlefield."""

        x, y = unit.position
        unit.position = (float(x), float(y))

        ix, iy = self._tile_index_from_pos(x, y)
        tile = self.game_map.ensure_tile(ix, iy)
        tile.add_occupant(unit)

        self.units[unit.id] = unit
        return unit.id

    def remove_unit(self, unit_id: int) -> None:
        """Supprime l'unité ayant l'id unit_id."""
        unit = self.units.pop(unit_id, None)
        if not unit:
            return

        x, y = unit.position
        ix, iy = self._tile_index_from_pos(x, y)
        tile = self.game_map.get_tile(ix, iy)
        if tile:
            tile.remove_occupant(unit)

    # -----------------------------------------------------
    # COLLISION SYSTEM
    # (circle checks, sliding, soft pushes)
    # -----------------------------------------------------

    def check_position(self, unit: Unit, new_x: float, new_y: float) -> bool:
        """
        Checks circular hitbox collision based on unit.radius.
        """
        for other in self.units.values():
            # Skip the unit itself and also the dead units
            if other is unit or not other.is_alive():
                continue

            ox, oy = other.position
            dx = new_x - ox
            dy = new_y - oy

            # circle collision using derived radius from width/height
            if math.hypot(dx, dy) < (unit.radius + other.radius):
                return True

        return False

    def attempt_sliding_move(self, unit: Unit, new_x: float, new_y: float):
        """
        Attempts old sliding movement:
        - try direct
        - try horizontal
        - try vertical
        - try small orthogonal offsets
        """
        if not self.check_position(unit, new_x, new_y):
            return new_x, new_y

        ux, uy = unit.position

        # horizontal
        if not self.check_position(unit, new_x, uy):
            return new_x, uy

        # vertical
        if not self.check_position(unit, ux, new_y):
            return ux, new_y

        # tiny orthogonal offsets
        eps = 0.3
        if not self.check_position(unit, new_x, new_y + eps):
            return new_x, new_y + eps
        if not self.check_position(unit, new_x, new_y - eps):
            return new_x, new_y - eps

        return unit.position

    def apply_soft_push(self, unit: Unit):
        ux, uy = unit.position

        for other in self.units.values():
            if other is unit or not other.is_alive():
                continue

            ox, oy = other.position
            dx = ux - ox
            dy = uy - oy
            dist = math.hypot(dx, dy)

            min_dist = unit.radius + other.radius
            if dist <= 0 or dist >= min_dist:
                continue

            # overlap amount
            overlap = min_dist - dist

            # orthogonal push
            ortho_x = dy
            ortho_y = -dx
            length = math.hypot(ortho_x, ortho_y)

            if length == 0:
                continue

            ortho_x /= length
            ortho_y /= length

            push_x = ortho_x * overlap * 0.5
            push_y = ortho_y * overlap * 0.5

            # Apply push directly to UNIT
            ux += push_x
            uy += push_y

        # Update unit position
        unit.position = (ux, uy)

    # -----------------------------------------------------
    # MOVEMENT SYSTEM
    # -----------------------------------------------------
    def move_unit_on_map(self, unit: Unit, new_x: float, new_y: float) -> bool:
        """
        Final merged movement:
        - bounds check
        - circular collision + sliding
        - soft push
        - tile update
        """
        # Boundaries
        if not (0 <= new_x < self.width and 0 <= new_y < self.height):
            return False

        # Circle collision detect
        if self.check_position(unit, new_x, new_y):
            new_x, new_y = self.attempt_sliding_move(unit, new_x, new_y)

        # If still blocked → no movement
        if (new_x, new_y) == unit.position:
            return False

        # Update tile occupancy
        ox, oy = unit.position
        oix, oiy = self._tile_index_from_pos(ox, oy)
        old_tile = self.game_map.get_tile(oix, oiy)
        if old_tile:
            old_tile.remove_occupant(unit)

        nix, niy = self._tile_index_from_pos(new_x, new_y)
        new_tile = self.game_map.ensure_tile(nix, niy)
        new_tile.add_occupant(unit)

        # Update unit floating position
        unit.position = (float(new_x), float(new_y))

        # apply soft push like old code
        self.apply_soft_push(unit)
        return True

    # -----------------------------------------------------
    # UTILITIES
    # -----------------------------------------------------
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
        return [u for u in self.units.values() if (u.position[0] - x) ** 2 + (u.position[1] - y) ** 2 <= r2]

    def units_in_los(self, unit: Unit) -> list[Unit]:
        """
        Returns all *living enemy* units within the given unit's vision range.
        This is typically used by AI to find a target.
        """
        # 1. Get all units in the raw circular radius (for efficiency)
        visible_units = self.units_in_radius(
            unit.position[0], 
            unit.position[1], 
            unit.vision_range
        )

        # 2. Filter the result to exclude self, dead units, and friendly units
        enemies_in_los = [
            u for u in visible_units
            if u.is_alive() and u.owner != unit.owner
        ]
        
        return enemies_in_los
    def is_battle_over(self) -> bool:
        """Renvoie True si la bataille est finie."""
        teams_alive = {u.owner for u in self.units.values() if u.is_alive()}
        return len(teams_alive) <= 1

    def snapshot(self) -> dict:
        """Renvoie un snapshot du Battlefield."""
        units_ser = []
        for u in self.units.values():
            units_ser.append({"id": u.id, "type": u.name, "owner": u.owner, "position": u.position, "hp": u.hp, "width": u.width, "height": u.height, "hibtox": u.radius})
        return {"width": self.width, "height": self.height, "units": units_ser, "generals": [str(g) for g in self.generals]}
