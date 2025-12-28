from __future__ import annotations
from typing import TYPE_CHECKING
from src.general.general_base import BaseGeneral
from src.engine.system import CombatSystem
import math

if TYPE_CHECKING:
    from src.engine.battlefield import Battlefield
    from src.units.unit_base import Unit


class GeneralTactician(BaseGeneral):
    def __init__(self, player_id: int):
        super().__init__(player_id, name="General Tactician")
        self.tick_counter = 0

    def update(self, bf: Battlefield, tick: int) -> None:
        self.tick_counter = tick

        # 1. PERCEPTION
        my_units = bf.get_my_units(self.player_id)
        enemies = bf.get_enemy_units(self.player_id)
        if not enemies or not my_units:
            return

        # 2. CALCUL DE LA GÉOMÉTRIE
        orders = {}

        melee_units = [u for u in my_units if u.attack_range <= 4.0]
        ranged_units = [u for u in my_units if u.attack_range > 4.0]

        # Calcul des positions idéales de l'arc
        if melee_units:
            orders.update(self._get_concave_positions(melee_units, enemies, bf, 0.6))
        if ranged_units:
            orders.update(self._get_concave_positions(ranged_units, enemies, bf, 1.2))

        # 3. LOGIQUE D'ENGAGEMENT
        for unit in my_units:
            nearest = CombatSystem.choose_nearest_target(unit, enemies, bf)
            if self._is_unit_engaged(unit, enemies):
                continue

            if unit in ranged_units:
                (is_threatened, is_critical) = self.is_threatened(unit, nearest)
                if is_threatened:
                    if is_critical or unit.reload_timer > 0:
                        (move_target_x, move_target_y) = self._fuite_strategique(unit, enemies, bf)
                        if not (move_target_x, move_target_y) == unit.position:
                            unit.current_order = {"type": "move_to", "target": (move_target_x, move_target_y)}
                            continue

            # PRIORITÉ 2 : Si un ennemi est très proche, on l'attaque TODO : WARNING : vision range c'est pas très proche, voir si on garde ça ou si on donne la prio à la formation
            if enemies:  # Sécurité si enemies est vide
                if unit.dist_to(nearest) <= unit.vision_range:
                    unit.current_order = {"type": "attack_unit", "target": nearest}
                    continue

            # PRIORITÉ 3 : Retour à la formation (attack_move)
            if unit.id in orders:
                dest_x, dest_y = orders[unit.id]
                should_update_order = False

                # Cas A : Pas d'ordre
                if not unit.current_order:
                    should_update_order = True

                # Cas B : On avait un ordre d'attaque d'unité (Target = Unit Object)
                # Comme on est arrivé ici (Priorité 3), c'est qu'on n'est plus engagé.
                # Il faut donc écraser cet ordre pour repasser en mode "Mouvement".

                elif unit.current_order["type"] == "attack_unit":
                    should_update_order = True

                # Cas C : On avait déjà un ordre de mouvement (Target = Tuple (x,y))
                # Là, on peut utiliser math.dist en toute sécurité

                elif unit.current_order["type"] == "attack_move":
                    if math.dist(unit.current_order["target"], (dest_x, dest_y)) > 1.0:  # TODO : reprendre ce bout de code et le mettre dans une fonction order movement opti
                        should_update_order = True

                if should_update_order:
                    unit.current_order = {"type": "attack_move", "target": (dest_x, dest_y)}

    def _get_concave_positions(self, units: list[Unit], enemies: list[Unit], bf: Battlefield, unit_spacing: float) -> dict[int, tuple[float, float]]:
        if not units:
            return {}

        # 1. ANALYSE
        my_centroid = self._get_centroid(units)
        enemy_centroid = self._get_centroid(enemies)
        dx = my_centroid[0] - enemy_centroid[0]
        dy = my_centroid[1] - enemy_centroid[1]
        dist_to_enemy = math.sqrt(dx**2 + dy**2)
        base_angle = math.atan2(dy, dx)
        avg_range = sum(u.attack_range for u in units) / len(units)

        # 2. CAPACITÉ PHYSIQUE
        is_melee = avg_range < 4.0

        circumference_needed = len(units) * unit_spacing
        max_angle = math.pi * 0.85
        min_radius_physic = circumference_needed / max_angle
        expansion_factor = dist_to_enemy * 0.4

        # 3. LE RAYON DE PRESSION
        if is_melee:
            effective_radius = max(min_radius_physic * 0.9, expansion_factor)
        else:
            target_range = max(min_radius_physic, avg_range * 0.85)
            effective_radius = max(target_range, expansion_factor)

        # 4. TRI TOPOLOGIQUE
        def get_relative_position_score(u):
            """projection sur la perpendiculaire de la ligne d'attaque"""
            return -dy * (u.position[0] - my_centroid[0]) + (dx) * (u.position[1] - my_centroid[1])

        def get_angular_score(u):
            angle_to_center = math.atan2(u.position[1] - my_centroid[1], u.position[0] - my_centroid[0])
            diff = angle_to_center - base_angle
            while diff <= -math.pi:
                diff += 2 * math.pi
            while diff > math.pi:
                diff -= 2 * math.pi
            return diff

        units_sorted = sorted(units, key=get_relative_position_score)

        # 5. GÉNÉRATION
        total_spread = circumference_needed / effective_radius
        total_spread = min(max_angle, total_spread)
        start_angle = base_angle - total_spread / 2

        assignments = {}
        for i, unit in enumerate(units_sorted):
            t = i / (len(units) - 1) if len(units) > 1 else 0.5
            current_angle = start_angle + (t * total_spread)

            # On utilise le centroid ennemi comme centre de rotation pour la symétrie
            tx = enemy_centroid[0] + math.cos(current_angle) * effective_radius
            ty = enemy_centroid[1] + math.sin(current_angle) * effective_radius
            tx, ty = self._clamp_position((tx, ty), bf)

            assignments[unit.id] = (tx, ty)

        return assignments
