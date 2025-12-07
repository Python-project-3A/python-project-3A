from __future__ import annotations

import logging
import math
from collections.abc import Callable
from typing import Any, Iterator

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
        self.game_map.init_map()
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

    # def check_position(self, unit: Unit, new_x: float, new_y: float) -> bool:
    #     """
    #     Checks circular hitbox collision based on unit.radius.
    #     """
    #     # On cherche les voisins dans un rayon de 2 tuiles
    #     potential_colliders = self.get_potential_neighbors(new_x, new_y, range_tiles=2)

    #     for other in potential_colliders:
    #         # Skip the unit itself and also the dead units
    #         if other is unit or not other.is_alive():
    #             continue

    #         ox, oy = other.position
    #         dx = new_x - ox
    #         dy = new_y - oy

    #         # circle collision using derived radius from width/height
    #         if math.hypot(dx, dy) < (unit.radius + other.radius):
    #             return True

    #         # Optimisation
    #         # if (dx * dx + dy * dy) < ((unit.radius + other.radius) * (unit.radius + other.radius)):
    #         #     return True
    #     return False

    def check_position(self, unit: Unit, new_x: float, new_y: float) -> bool:
        """
        Checks circular hitbox collision based on unit.radius.
        Optimisation : Inlining de la recherche de voisins + Distance au carré.
        """
        # 1. On calcule la tuile centrale cible
        cx, cy = int(new_x), int(new_y)

        # 2. On itère manuellement sur les 25 tuiles autour (rayon 2), c'est moche mais c'est sensé être + perfformant
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                tile = self.game_map.get_tile(cx + dx, cy + dy)

                if not tile or not tile.occupants:
                    continue

                for other in tile.occupants:
                    if other is unit or not other.is_alive():
                        continue

                    # 3. Optimisation Mathématique (Distance Carrée)  évite math.hypot (qui fait une racine carrée)
                    d_x = new_x - other.position[0]
                    d_y = new_y - other.position[1]
                    dist_sq = d_x * d_x + d_y * d_y

                    # On compare avec (r1 + r2)^2
                    min_dist = unit.radius + other.radius
                    if dist_sq < min_dist * min_dist:
                        return True

        return False

    def attempt_sliding_move(self, unit: Unit, target_x: float, target_y: float) -> tuple[float, float]:
        """
        Gestion physique du glissement pour des cercles (Tangent Sliding).
        Si le mouvement direct est bloqué, on essaie de glisser le long de l'obstacle.
        """
        if not self.check_position(unit, target_x, target_y):
            return target_x, target_y

        ux, uy = unit.position

        # vecteur de mouvement
        move_dx = target_x - ux
        move_dy = target_y - uy

        # identification  de l'obstacle principal
        neighbors = self.get_potential_neighbors(target_x, target_y, range_tiles=2)  # On cherche le voisin le plus proche qui cause la collision (opti spatiale)
        collider = None
        min_dist_sq = float("inf")

        for other in neighbors:
            if other is unit or not other.is_alive():
                continue

            # Distance future estimée
            dx = target_x - other.position[0]
            dy = target_y - other.position[1]
            dist_sq = dx * dx + dy * dy
            radius_sum = unit.radius + other.radius

            # Si collision détectée
            if dist_sq < radius_sum * radius_sum:
                # On garde le plus proche (celui qui nous bloque le plus)
                if dist_sq < min_dist_sq:
                    min_dist_sq = dist_sq
                    collider = other

        # Si on ne trouve pas de collider (fin de map), on annule le mouvement
        if not collider:
            return ux, uy

        # Calcul du vecteur normal
        ox, oy = collider.position
        normal_x = ox - ux
        normal_y = oy - uy

        # normalisation
        norm_len = math.hypot(normal_x, normal_y)
        if norm_len == 0:
            return ux, uy
        normal_x /= norm_len
        normal_y /= norm_len

        # vecteur tangent
        tangent_x = -normal_y
        tangent_y = normal_x

        # projection du mouvement sur la tangente (produit scalaire)
        dot = move_dx * tangent_x + move_dy * tangent_y  # Direction of tangent =  V . T

        # nouveau mouvement glissé
        slide_dx = tangent_x * dot
        slide_dy = tangent_y * dot

        # application du glissement
        slide_target_x = ux + slide_dx
        slide_target_y = uy + slide_dy

        # Vérification finale : Est-ce que ce mouvement glissé est libre ?
        if not self.check_position(unit, slide_target_x, slide_target_y):
            return slide_target_x, slide_target_y

        # Si glisser est bloqué on annumle
        return ux, uy

    def apply_soft_push(self, unit: Unit):
        ux, uy = unit.position

        neighbors = self.get_potential_neighbors(ux, uy, range_tiles=1)

        for other in neighbors:
            if other is unit or not other.is_alive():
                continue

            ox, oy = other.position
            dx = ux - ox
            dy = uy - oy

            dist = math.hypot(dx, dy)
            min_dist = unit.radius + other.radius

            if dist <= 0 or dist >= min_dist:
                continue

            overlap = min_dist - dist

            # Normalisation du vecteur de collision (normal)
            nx = dx / dist
            ny = dy / dist

            correction_strength = 0.5  # force de répulsion : on fait 50% de l'overlap (l'autre unité fera l'autre moitié)
            push_x = nx * overlap * correction_strength
            push_y = ny * overlap * correction_strength

            ux += push_x
            uy += push_y

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
    # def get_all_units(self) -> list[Unit]:
    #     """Renvoie une liste des unités du Battlefield."""
    #     return list(self.units.values())

    def get_all_units(self) -> Iterator[Unit]:
        """Renvoie un itérateur sur les unités (beaucoup plus rapide que créer une liste)."""
        return self.units.values()

    def units_by_owner(self, owner: int) -> list[Unit]:
        """Renvoie une liste des unités appartenant au owner."""
        return [u for u in self.units.values() if u.owner == owner]

    def find_unit(self, unit_id: int) -> Unit | None:
        """Renvoie l'unité ayant l'id unit_id."""
        return self.units.get(unit_id)

    def units_in_radius(self, x: float, y: float, radius: float) -> list[Unit]:
        r2 = radius * radius
        return [u for u in self.units.values() if (u.position[0] - x) ** 2 + (u.position[1] - y) ** 2 <= r2]

    def units_in_radius_opti(self, x: float, y: float, radius: float) -> list[Unit]:
        """Spatial optimisation version of units_in_radius()"""
        r2 = radius * radius
        range_tiles = int(math.ceil(radius)) + 1  # on calcule combien de tuiles couvre le rayon
        candidates = self.get_potential_neighbors(x, y, range_tiles)
        return [u for u in candidates if (u.position[0] - x) ** 2 + (u.position[1] - y) ** 2 <= r2]

    def units_in_los(self, unit: Unit) -> list[Unit]:
        """
        Returns all *living enemy* units within the given unit's vision range.
        This is typically used by AI to find a target.
        """
        # 1. Get all units in the raw circular radius (for efficiency)
        # visible_units = self.units_in_radius(unit.position[0], unit.position[1], unit.vision_range)
        visible_units = self.units_in_radius_opti(unit.position[0], unit.position[1], unit.vision_range)
        # 2. Filter the result to exclude self, dead units, and friendly units
        enemies_in_los = [u for u in visible_units if u.is_alive() and u.owner != unit.owner]

        return enemies_in_los

    def get_potential_neighbors(self, x: float, y: float, range_tiles: int = 1) -> list[Unit]:
        """
        Optimisation : récupère les unités présentes sur la tuile (x,y) et ses voisines.
        C'est beaucoup plus rapide que de scanner tt les unités
        """
        cx, cy = self._tile_index_from_pos(x, y)
        neighbors = []

        # On scanne un carré autour de la tuile centrale
        for dx in range(-range_tiles, range_tiles + 1):
            for dy in range(-range_tiles, range_tiles + 1):
                nx, ny = cx + dx, cy + dy
                tile = self.game_map.get_tile(nx, ny)
                if tile:
                    neighbors.extend(tile.occupants)
        return neighbors

    def is_battle_over(self) -> bool:
        """Renvoie True si la bataille est finie."""
        teams_alive = {u.owner for u in self.units.values() if u.is_alive()}
        return len(teams_alive) <= 1

    def snapshot(self) -> dict:
        """Renvoie un snapshot du Battlefield."""
        units_ser = []
        for u in self.units.values():
            units_ser.append({"id": u.id, "type": u.name, "owner": u.owner, "position": u.position, "hp": u.hp, "radius": u.radius, "hibtox": u.radius})
        return {"width": self.width, "height": self.height, "units": units_ser, "generals": [str(g) for g in self.generals]}

    def print_battle_result(self):
        """Print battle results"""
        print("\n" + "=" * 60)
        print("=== BATTLE RESULT ===")
        print("=" * 60)

        survivors_by_owner = {}
        for unit in self.get_all_units():
            if unit.is_alive():
                if unit.owner not in survivors_by_owner:
                    survivors_by_owner[unit.owner] = []
                survivors_by_owner[unit.owner].append(unit)

        for owner_id in [0, 1]:
            general = self.generals[owner_id]
            survivors = survivors_by_owner.get(owner_id, [])

            print(f"\n️  {general.name} (Player {owner_id}):")
            print(f"   Survivors: {len(survivors)} units")

            if survivors:
                total_hp = sum(u.hp for u in survivors)
                avg_hp = total_hp / len(survivors)
                print(f"   Total HP: {total_hp:.1f}")
                print(f"   Avg HP: {avg_hp:.1f}")

        print("\n" + "-" * 60)
        if len(survivors_by_owner) == 0:
            print("  DRAW - All units eliminated!")
        elif len(survivors_by_owner) == 1:
            winner_id = list(survivors_by_owner.keys())[0]
            winner_general = self.generals[winner_id]
            print(f" VICTORY for {winner_general.name} (Player {winner_id})!")
        else:
            # counts = {owner: len(units) for owner, units in survivors_by_owner.items()}
            # winner_id = max(counts, key=counts.get)
            # winner_general = self.generals[winner_id]
            # print(f" TACTICAL VICTORY for {winner_general.name} (Player {winner_id})!")
            print(f" GAME STOPPED : BOTH TEAMS ARE ALIVE")
        print("=" * 60 + "\n")
