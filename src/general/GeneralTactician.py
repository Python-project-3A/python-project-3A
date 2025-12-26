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
                current = unit.current_order

                # Cas A : Pas d'ordre
                if not current:
                    should_update_order = True

                # Cas B : On avait un ordre d'attaque d'unité (Target = Unit Object)
                # Comme on est arrivé ici (Priorité 3), c'est qu'on n'est plus engagé.
                # Il faut donc écraser cet ordre pour repasser en mode "Mouvement".
                elif current["type"] == "attack_unit":
                    should_update_order = True

                # Cas C : On avait déjà un ordre de mouvement (Target = Tuple (x,y))
                # Là, on peut utiliser math.dist en toute sécurité
                elif current["type"] == "attack_move":
                    if math.dist(current["target"], (dest_x, dest_y)) > 2.0:
                        should_update_order = True

                if should_update_order:
                    unit.current_order = {"type": "attack_move", "target": (dest_x, dest_y)}

    def _is_unit_engaged(self, unit: Unit, enemies: list[Unit]) -> bool:
        """Vérifie si l'unité est déjà occupée à combattre efficacement."""
        if not unit.current_order or unit.current_order["type"] != "attack_unit":
            return False

        target = unit.current_order["target"]
        # La cible est-elle toujours vivante et à portée ?
        if target.is_alive() and unit.dist_to(target) <= unit.attack_range * 1.2:
            return True

        return False

    def _get_concave_positions(self, units: list[Unit], enemies: list[Unit], bf: Battlefield, unit_spacing: float) -> dict[int, tuple[float, float]]:
        if not units:
            return {}

        # 1. ANALYSE
        center_x = sum(u.position[0] for u in units) / len(units)
        center_y = sum(u.position[1] for u in units) / len(units)

        # On utilise le barycentre global pour l'ORIENTATION (L'arc sera "droit")
        enemy_centroid = self._get_centroid(enemies)
        dx = center_x - enemy_centroid[0]
        dy = center_y - enemy_centroid[1]
        base_angle = math.atan2(dy, dx)

        # 2. CAPACITÉ PHYSIQUE
        avg_range = sum(u.attack_range for u in units) / len(units)
        is_melee = avg_range < 4.0

        circumference_needed = len(units) * unit_spacing
        max_angle = math.pi * 0.8  # On limite à 144° pour garder une force de frappe frontale
        min_radius_physic = circumference_needed / max_angle

        # 3. LE RAYON DE PRESSION
        # Pour la mêlée, on veut que le point cible soit UN PEU DERRIÈRE la ligne de front ennemie
        # pour forcer l'unité à avancer jusqu'au contact physique.
        if is_melee:
            # On ignore la portée théorique, on veut coller.
            # On prend le rayon physique, mais on le réduit de 20% pour "pousser"
            effective_radius = max(2.0, min_radius_physic * 0.8)
        else:
            # Pour les archers, on respecte la portée pour ne pas les suicider
            effective_radius = max(min_radius_physic, avg_range * 0.8)

        # 4. TRI TOPOLOGIQUE (Correction du signe pour Y-Down)
        # On projette sur la perpendiculaire.
        # Si l'asymétrie persiste, inverse le signe de dy et dx ici.
        def get_relative_position_score(u):
            return -dy * (u.position[0] - center_x) + dx * (u.position[1] - center_y)

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

            # Clamp
            tx = max(1.0, min(tx, bf.width - 1.0))
            ty = max(1.0, min(ty, bf.height - 1.0))

            assignments[unit.id] = (tx, ty)

        return assignments
