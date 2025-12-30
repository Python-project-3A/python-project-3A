from __future__ import annotations
from typing import TYPE_CHECKING, Dict, List, Optional
import math

from src.general.general_base import BaseGeneral
from src.engine.system import CombatSystem

if TYPE_CHECKING:
    from src.engine.battlefield import Battlefield
    from src.units.unit_base import Unit


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
        self._calculate_sliding_geometry(pikemen, knights, crossbowmen, enemies, bf)

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

        my_center = self._get_centroid(infantry)
        en_center = self._get_centroid(enemies)
        total_dist = math.dist(my_center, en_center)

        if total_dist < 5.0:
            self.march_progression = 1.0
            return

        # TODO : changer la vitesse arbitraire de l'arc
        # Vitesse d'avancée de l'arc (arbitraire ou basée sur l'unité moyenne)
        # Disons 1.2 m/s (vitesse standard infanterie)
        arc_speed = 1.2
        advance = (arc_speed * dt) / total_dist
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
    def _calculate_sliding_geometry(self, pikemen: list[Unit], knights: list[Unit], crossbowmen: list[Unit], enemies: list[Unit], bf: Battlefield):
        """calculate the geometry of the arc for the sliding march"""
        if not enemies:
            return

        # 1. Définition des ancres (Départ et Arrivée)
        my_infantry = pikemen + crossbowmen
        if not my_infantry:
            my_infantry = knights

        start_center = self._get_centroid(my_infantry)
        end_center = self._get_centroid(enemies)  # Ennemi actuel

        # 2. Calcul du Centre Virtuel de l'Arc (Interpolation)
        lead_distance = 5.0

        vec_x = end_center[0] - start_center[0]
        vec_y = end_center[1] - start_center[1]
        dist_tot = math.hypot(vec_x, vec_y)

        if dist_tot > 0.1:
            dir_x = vec_x / dist_tot
            dir_y = vec_y / dist_tot
        else:
            dir_x, dir_y = 1, 0

        # Position actuelle idéale + Avance
        current_dist = dist_tot * self.march_progression
        target_dist = min(current_dist + lead_distance, dist_tot)  # On ne dépasse pas l'ennemi

        virtual_center_x = start_center[0] + dir_x * target_dist
        virtual_center_y = start_center[1] + dir_y * target_dist
        virtual_center = (virtual_center_x, virtual_center_y)

        # 3. Rayon et Angle
        attack_angle = math.atan2(vec_y, vec_x)
        max_d = 0
        for e in enemies:
            d = self.get_dist(e.position, end_center)
            if d > max_d:
                max_d = d
        enemy_radius = max_d

        # Calcul dynamique des rayons
        radius_frontline = enemy_radius + 1.5
        pikemen_depth = 0.0
        if pikemen:
            arc_len = radius_frontline * 2.44  # 2.44 = 140 degrés en radians
            pikemen_depth = len(pikemen) / max(1.0, arc_len)
            pikemen_depth += 2.0
        radius_backline = radius_frontline + pikemen_depth + 1.0

        # 4. Génération de l'arc
        self._assign_arc_orders_angular(pikemen, virtual_center, radius_frontline, attack_angle, bf)
        self._assign_arc_orders_angular(crossbowmen, virtual_center, radius_backline, attack_angle, bf)

        if knights:
            kx = virtual_center[0] - math.cos(attack_angle) * (enemy_radius + 2.0)
            ky = virtual_center[1] - math.sin(attack_angle) * (enemy_radius + 2.0)
            k_pt = self._clamp_position((kx, ky), bf)
            for k in knights:
                self.formation_orders[k.id] = k_pt

    # Fonction V2 & V3
    def _assign_arc_orders_angular(self, units: list[Unit], center: tuple, radius: float, axis_angle: float, bf: Battlefield):
        """
        Assigne les positions sur l'arc en triant les unités et les cibles par angle polaire.
        Garantit qu'il n'y a pas de croisement.
        """
        if not units:
            return
        n = len(units)
        base_angle = axis_angle + math.pi
        arc_spread = math.radians(140)

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
