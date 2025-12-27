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
        super().__init__(player_id, name="General TACTICIAN")
        self.tick_counter = 0

    def update(self, bf: Battlefield, tick: int) -> None:
        self.tick_counter = tick

        # 1. PERCEPTION
        my_units = bf.get_my_units(self.player_id)
        enemies = bf.get_enemy_units(self.player_id)
        if not enemies or not my_units:
            return

        # 2. CALCUL DE LA GÉOMÉTRIE (Uniquement si nécessaire)
        # On ne calcule l'arc que si on est en phase d'approche
        orders = {}

        # On sépare les unités
        melee_units = [u for u in my_units if u.attack_range <= 4.0]
        ranged_units = [u for u in my_units if u.attack_range > 4.0]

        # Calcul des positions idéales de l'arc
        if melee_units:
            orders.update(self._get_concave_positions(melee_units, enemies, bf, 0.8))
        if ranged_units:
            orders.update(self._get_concave_positions(ranged_units, enemies, bf, 1.2))

        # 3. LOGIQUE D'ENGAGEMENT
        for unit in my_units:
            # PRIORITÉ 1 : Si engagé, on ne touche à rien
            if self._is_unit_engaged(unit, enemies):
                continue

            if unit.attack_range > 4.0:
                unit.current_order = self.micro_ranged_unit_logic(unit, enemies, bf)
                if unit.current_order:
                    return

            # PRIORITÉ 2 : Si un ennemi est très proche, on charge (attack_unit)
            if enemies:  # Sécurité si enemies est vide
                nearest_threat = min(enemies, key=lambda e: unit.dist_to(e))
                engagement_range = unit.attack_range * 1.1

                if unit.dist_to(nearest_threat) <= engagement_range:
                    unit.current_order = {"type": "attack_unit", "target": nearest_threat}
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
                    if math.dist(unit.current_order["target"], (dest_x, dest_y)) > 2.0:
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

        # 2. CAPACITÉ PHYSIQUE
        avg_range = sum(u.attack_range for u in units) / len(units)
        is_melee = avg_range < 4.0

        circumference_needed = len(units) * unit_spacing
        max_angle = math.pi * 0.8
        min_radius_physic = circumference_needed / max_angle
        expansion_factor = dist_to_enemy * 0.3

        # 3. LE RAYON DE PRESSION
        if is_melee:
            effective_radius = max(min_radius_physic * 0.8, expansion_factor)
        else:
            target_range = max(min_radius_physic, avg_range * 0.8)
            effective_radius = max(target_range, expansion_factor)

        # 4. TRI TOPOLOGIQUE (Correction du signe pour Y-Down)
        def get_relative_position_score(u):
            """projection sur la perpendiculaire de la ligne d'attaque"""
            return -dy * (u.position[0] - my_centroid[0]) + dx * (u.position[1] - my_centroid[1])

        def get_angular_score(u):
            angle_to_center = math.atan2(u.position[1] - my_centroid[1], u.position[0] - my_centroid[0])
            relative_angle = angle_to_center - base_angle
            while relative_angle <= -math.pi:
                relative_angle += 2 * math.pi
            while relative_angle > math.pi:
                relative_angle -= 2 * math.pi
            return relative_angle

        units_sorted = sorted(units, key=get_angular_score)

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

            # Clamp
            tx = max(1.0, min(tx, bf.width - 1.0))
            ty = max(1.0, min(ty, bf.height - 1.0))

            assignments[unit.id] = (tx, ty)

        return assignments
