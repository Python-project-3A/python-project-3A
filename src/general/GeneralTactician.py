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

        if self.tick_counter % 15 != 0:
            return

        # 1. PERCEPTION -> TODO : faire chaque 5/10/15 ticks
        my_units = bf.get_my_units(self.player_id)
        enemies = bf.get_enemy_units(self.player_id)

        if not enemies or not my_units:
            return

        # TODO FAIRE une version V2, avec le clustering pour faire plusieurs arcs
        target_cluster = self._get_centroid(enemies)

        # 2. TRI DES TROUPES (Séparation des Rôles)
        melee_units = []
        ranged_units = []

        for u in my_units:
            if not u.is_alive():
                continue
            # Seuil arbitraire : Si portée > 4m, c'est des unités qui peuvent attaquer à distance => second arc
            if u.attack_range > 4.0:
                ranged_units.append(u)
            else:
                melee_units.append(u)

        # 3. CALCUL DES POSITIONS (La Double Concave)
        orders = {}

        # A. Ligne de Front (Pikemen/Crossbowmen) -> Contact (petit buffer (2.5m) pour ne pas qu'ils se gênent)
        if melee_units:
            pos_melee = self._get_concave_positions(melee_units, target_cluster, bf, ideal_radius=2.5)
            orders.update(pos_melee)

        # B. Ligne Arrière -> Portée Optimale
        if ranged_units:
            avg_range = sum(u.attack_range for u in ranged_units) / len(ranged_units)
            safe_radius = avg_range * 0.8  # On se place à 80% de la portée max pour assurer le tir même si l'ennemi recule un peu
            safe_radius = max(safe_radius, 5.0)
            pos_ranged = self._get_concave_positions(ranged_units, target_cluster, bf, ideal_radius=safe_radius)
            orders.update(pos_ranged)

        # 4. EXECUTION DES ORDRES
        for unit in my_units:
            if unit.id in orders:
                dest_x, dest_y = orders[unit.id]
                unit.current_order = {"type": "attack_move", "target": (dest_x, dest_y)}

    def _get_concave_positions(self, units: list[Unit], target_pos: tuple[float, float], bf: Battlefield, ideal_radius: float) -> dict[int, tuple[float, float]]:
        """
        Calcule les positions pour former un arc de cercle (Concave) autour de la cible.
        Retourne un dictionnaire {unit_id: (target_x, target_y)}.
        """
        if not units:
            return {}

        # 1. Barycentre de NOS unités (pour savoir d'où on vient)
        center_x = sum(u.position[0] for u in units) / len(units)
        center_y = sum(u.position[1] for u in units) / len(units)

        # 2. Angle vers l'ennemi
        dx = target_pos[0] - center_x
        dy = target_pos[1] - center_y
        base_angle = math.atan2(dy, dx)

        # 3. Largeur de l'arc (Spread)
        unit_spacing_angle = 0.15  # Radians par unité
        max_spread = math.pi * 1.5
        required_spread = len(units) * unit_spacing_angle
        total_spread = min(max_spread, required_spread)

        start_angle = base_angle - total_spread / 2
        assignments = {}

        # 4. Tri angulaire pour éviter que les unités se croisent en allant à leur place
        # On trie nos unités selon leur angle actuel par rapport au centre du combat
        units_sorted = sorted(units, key=lambda u: math.atan2(u.position[1] - center_y, u.position[0] - center_x))

        for i, unit in enumerate(units_sorted):
            # Interpolation linéaire le long de l'arc
            t = i / (len(units) - 1) if len(units) > 1 else 0.5
            angle = start_angle + (t * total_spread)

            # Calcul position : Cible - (Vecteur Angle * Rayon)
            # On part de la cible et on recule vers nous
            tx = target_pos[0] - math.cos(angle) * ideal_radius
            ty = target_pos[1] - math.sin(angle) * ideal_radius

            # Limites de la carte
            tx = max(0.5, min(tx, bf.width - 0.5))
            ty = max(0.5, min(ty, bf.height - 0.5))

            assignments[unit.id] = (tx, ty)

        return assignments
