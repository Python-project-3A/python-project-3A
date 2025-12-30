from __future__ import annotations
from typing import TYPE_CHECKING, Dict, List, Optional
import math

from src.general.general_base import BaseGeneral
from src.engine.system import CombatSystem

if TYPE_CHECKING:
    from src.engine.battlefield import Battlefield
    from src.units.unit_base import Unit


# TODO : implémenter la gestion des Knights : attaque au centre au lieu des bords de l'arc
class GeneralTactician(BaseGeneral):
    def __init__(self, player_id: int):
        super().__init__(player_id, name="General TACTICIAN")

        # --- ÉTAT INTERNE ---
        self.phase = "MARCH"
        self.formation_orders: Dict[int, tuple[float, float]] = {}
        self.march_progression = 0.0  # Pour l'arc de cerle glissant
        self.reference_arrival_time = 0.0

    def update(self, bf: Battlefield, tick: int, dt) -> None:
        # 1. PERCEPTION
        my_units = self.get_my_units(bf)
        enemies = self.get_enemy_units(bf)

        if not my_units or not enemies:
            return

        # 2. CLASSIFICATION
        pikemen = []
        crossbowmen = []
        knights = []

        for u in my_units:
            name_lower = u.name.lower()
            if "knight" in name_lower:
                knights.append(u)
            elif "crossbowman" in name_lower:
                crossbowmen.append(u)
            elif "pikeman" in name_lower:
                pikemen.append(u)
            else:
                assert False, f"Unknown unit type : {u.name} : A IMPLEMENTER"

        # 3. KILL SWITCH (Passage en phase combat)
        if self.phase == "MARCH":
            if self._check_charge_condition(my_units, enemies) or self.march_progression >= 0.95:
                self.phase = "COMBAT"
                self.formation_orders.clear()

        # 4. EXÉCUTION LOGIQUE
        if self.phase == "COMBAT":
            self._execute_combat_logic(pikemen, knights, crossbowmen, enemies, bf)
        else:
            self._execute_sliding_march_logic(pikemen, knights, crossbowmen, enemies, bf, tick, dt)

    # =========================================================================
    # PHASE 1 : MARCHE (SLIDING ARC)
    # =========================================================================

    # Fonction V3
    def _execute_sliding_march_logic(self, pikemen: list[Unit], knights: list[Unit], crossbowmen: list[Unit], enemies: list[Unit], bf: Battlefield, tick: int, dt):
        # 1. Mise à jour de la progression de l'arc
        self._update_march_progression(pikemen + crossbowmen, enemies, dt)

        # 2. Calcul de la géométrie SUR L'ARC INTERPOLÉ
        self._calculate_sliding_geometry(pikemen, knights, crossbowmen, enemies, bf, 180)

        # 3. Application du mouvement avec la nouvelle fonction système
        self._apply_controlled_movement(pikemen, bf, dt)
        self._apply_controlled_movement(crossbowmen, bf, dt)
        self._apply_controlled_movement(knights, bf, dt)

    # Fonction V3
    def _update_march_progression(self, infantry: list[Unit], enemies: list[Unit], dt):
        """
        Fait avancer le curseur de progression (0.0 -> 1.0)
        """
        if not infantry or not enemies:
            return

        if infantry:
            min_speed = min(u.speed for u in infantry)
            formation_speed = min_speed * 0.95
        else:
            formation_speed = 1.0

        my_center = self._get_centroid(infantry)
        en_center = self._get_centroid(enemies)
        total_dist = math.dist(my_center, en_center)

        if total_dist < 2.0:
            self.march_progression = 1.0
            return

        advance = (formation_speed * dt) / total_dist
        self.march_progression += advance
        self.march_progression = min(self.march_progression, 1.0)

    # Fonction V3
    def _apply_controlled_movement(self, units: list[Unit], bf: Battlefield, dt):
        for unit in units:
            if unit.id not in self.formation_orders:
                continue
            target = self.formation_orders[unit.id]
            unit.current_order = {"type": "move_controlled", "target": target, "speed_limit": unit.speed}

    # =========================================================================
    # PHASE 2 : COMBAT (OPTIMISÉE)
    # =========================================================================

    # Fonction V2 &V3
    def _execute_combat_logic(self, pikemen: list[Unit], knights: list[Unit], crossbowmen: list[Unit], enemies: list[Unit], bf: Battlefield):
        """execute combat logic for all units"""
        melee_forces = pikemen + knights
        for unit in melee_forces:
            if self._is_unit_engaged(unit, enemies):
                continue
            if enemies:
                nearest = CombatSystem.choose_nearest_target(unit, enemies, bf)
                self._order_attack_opti(unit, nearest)

        for unit in crossbowmen:
            self._micro_archer(unit, enemies, unit.position, bf)

    # =========================================================================
    # GÉOMÉTRIE (TRI ANGULAIRE & CALCULS)
    # =========================================================================

    # Fonction V3
    def _calculate_sliding_geometry(self, pikemen: list[Unit], knights: list[Unit], crossbowmen: list[Unit], enemies: list[Unit], bf: Battlefield, angle_deg=140):
        """
        Calcule la géométrie de l'arc glissant avec un ancrage
        et un rayon adaptatif qui ne rétrécit pas sous le seuil physique des unités.
        """
        if not enemies:
            return

        # --- CONSTANTES DE CONFIGURATION ---
        UNIT_DIAMETER = 1.0  # TODO : remplacer cette constante
        CONTACT_BUFFER = 2.0  # TODO : remplacer cette constante
        PIKEMEN_BACK_BUFFER = 2.0  # TODO : Remplacer cette constante
        LEAD_PROJECTION = 5.0  # Distance de projection de l'arc
        OVERSHOOT_MARGIN = 5.0  # TODO : Remplacer cette constante (Rayon de l'arc ?)

        # 1. Analyse des Centres
        my_infantry = pikemen + crossbowmen or knights
        start_center = self._get_centroid(my_infantry)
        end_center = self._get_centroid(enemies)

        vec_x = end_center[0] - start_center[0]
        vec_y = end_center[1] - start_center[1]
        dist_to_enemy = math.hypot(vec_x, vec_y)

        if dist_to_enemy > 0.01:
            dir_x, dir_y = vec_x / dist_to_enemy, vec_y / dist_to_enemy
        else:
            dir_x, dir_y = 1, 0  # Fallback

        # 3. Calcul du Rayon Ennemi (Bounding Circle)
        enemy_radius = 0.0
        for e in enemies:
            d = self.get_dist(e.position, end_center)
            if d > enemy_radius:
                enemy_radius = d

        # 4. Calcul du Rayon de Formation
        count_frontline = len(pikemen)
        if count_frontline == 0:
            count_frontline = len(crossbowmen)

        arc_angle_rad = math.radians(angle_deg)
        required_arc_length = count_frontline * UNIT_DIAMETER
        min_density_radius = required_arc_length / arc_angle_rad
        radius_frontline = max(enemy_radius + CONTACT_BUFFER, min_density_radius)

        # 5. Calcul de l'Ancrage
        overshoot_dist = radius_frontline + OVERSHOOT_MARGIN
        total_maneuver_dist = dist_to_enemy + overshoot_dist
        current_travel = (total_maneuver_dist * self.march_progression) + LEAD_PROJECTION
        target_dist = min(current_travel, total_maneuver_dist)
        virtual_center = (start_center[0] + dir_x * target_dist, start_center[1] + dir_y * target_dist)

        # 6. Calcul de la Ligne Arrière
        if pikemen:
            actual_arc_len = radius_frontline * arc_angle_rad
            total_pikemen_area = len(pikemen) * (UNIT_DIAMETER * 1.2)  # 1.2 = facteur profondeur
            pikemen_depth = total_pikemen_area / max(1.0, actual_arc_len)
            radius_backline = radius_frontline + pikemen_depth + PIKEMEN_BACK_BUFFER

        attack_angle = math.atan2(vec_y, vec_x)

        # 7. Génération des ordres
        self._assign_arc_orders_angular(pikemen, virtual_center, radius_frontline, attack_angle, bf, angle_deg)
        self._assign_arc_orders_angular(crossbowmen, virtual_center, radius_backline, attack_angle, bf, angle_deg)

        # Knights : Protection des flancs extérieurs
        if knights:
            k_radius = radius_frontline + 2.0
            kx = virtual_center[0] - math.cos(attack_angle) * k_radius
            ky = virtual_center[1] - math.sin(attack_angle) * k_radius
            k_pt = self._clamp_position((kx, ky), bf)
            for k in knights:
                self.formation_orders[k.id] = k_pt

    # Fonction V2 & V3
    def _assign_arc_orders_angular(self, units: list[Unit], center: tuple, radius: float, axis_angle: float, bf: Battlefield, angle):
        """
        Assigne les positions sur l'arc en triant les unités et les cibles par angle polaire.
        Garantit qu'il n'y a pas de croisement.
        """
        if not units:
            return
        n = len(units)
        base_angle = axis_angle + math.pi
        arc_spread = math.radians(angle)

        # Ajustement densité : Si trop d'unités, on élargit le rayon
        final_radius = max(radius, (n * 1.0) / arc_spread)

        # 1. Génération des Slots Cibles (triés par angle)
        target_slots = []
        start_angle = base_angle - (arc_spread / 2)

        for i in range(n):
            t = i / (n - 1) if n > 1 else 0.5
            ang = start_angle + (t * arc_spread)
            tx = center[0] + math.cos(ang) * final_radius
            ty = center[1] + math.sin(ang) * final_radius
            target_slots.append({"angle": ang, "pos": self._clamp_position((tx, ty), bf)})

        # 2. Analyse des Unités (triées par angle relatif)
        unit_slots = []
        for u in units:
            ang = math.atan2(u.position[1] - center[1], u.position[0] - center[0])
            unit_slots.append({"angle": ang, "unit": u})

        # Fonction de tri relatif pour gérer la discontinuité -PI/PI
        def relative_angle_diff(a):
            diff = a - base_angle
            return math.atan2(math.sin(diff), math.cos(diff))

        target_slots.sort(key=lambda x: relative_angle_diff(x["angle"]))
        unit_slots.sort(key=lambda x: relative_angle_diff(x["angle"]))

        # 3. Assignation 1 pour 1
        for i in range(n):
            u_id = unit_slots[i]["unit"].id
            pos = target_slots[i]["pos"]
            self.formation_orders[u_id] = pos

    # Fonction V2 & V3
    def _check_charge_condition(self, my_units: list[Unit], enemies: list[Unit]) -> bool:
        """Déclenche la charge si le temps est écoulé ou si l'ennemi est trop proche."""
        # TODO : Optimiser cette fonction
        for u in my_units:
            for e in enemies:
                if self.get_dist(u.position, e.position) < 4.0:
                    return True
        return False
