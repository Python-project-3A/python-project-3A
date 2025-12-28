from __future__ import annotations
from typing import TYPE_CHECKING
import math

from src.general.general_base import BaseGeneral

if TYPE_CHECKING:
    from src.engine.battlefield import Battlefield
    from src.units.unit_base import Unit


class GeneralTactician(BaseGeneral):
    def __init__(self, player_id: int):
        super().__init__(player_id, name="General TACTICIAN")
        self.phase = "MARCH"
        self.formation_orders = {}
        self.reference_arrival_time = 0.0

    def update(self, bf: Battlefield, tick: int) -> None:
        my_units = self.get_my_units(bf)
        enemies = self.get_enemy_units(bf)

        if not my_units or not enemies:
            return

        # 1. CLASSIFICATION ROBUSTE
        pikemen = []
        crossbowmen = []
        knights = []

        for u in my_units:
            name_lower = u.name.lower()
            if "knight" in name_lower or "cavalry" in name_lower or u.speed > 1.5:
                knights.append(u)
            elif "cross" in name_lower or u.attack_range >= 4.0:
                crossbowmen.append(u)
            elif "pike" in name_lower or "spear" in name_lower:
                pikemen.append(u)
            else:
                pikemen.append(u)

        # 2. KILL SWITCH
        if self.phase == "MARCH":
            if self._check_charge_condition(my_units, enemies):
                self.phase = "COMBAT"
                self.formation_orders.clear()

        # 3. LOGIQUE
        if self.phase == "COMBAT":
            self._execute_combat_logic(pikemen, knights, crossbowmen, enemies, bf)
        else:
            self._execute_march_logic(pikemen, knights, crossbowmen, enemies, bf, tick)

    # =========================================================================
    # PHASE MARCHE
    # =========================================================================

    def _execute_march_logic(self, pikemen: list[Unit], knights: list[Unit], crossbowmen: list[Unit], enemies: list[Unit], bf: Battlefield, tick: int):
        # A. Recalcul périodique
        if tick % 5 == 0 or not self.formation_orders:
            self._calculate_formation_geometry(pikemen, knights, crossbowmen, enemies, bf)

        # B. Calcul Temps Référence (Robustesse 90eme percentile)
        all_infantry = pikemen + crossbowmen
        arrival_times = []
        for u in all_infantry:
            if u.id in self.formation_orders:
                target = self.formation_orders[u.id]
                dist = self.get_dist(u.position, target)
                speed = u.speed if u.speed > 0.1 else 0.1
                arrival_times.append(dist / speed)

        if arrival_times:
            arrival_times.sort()
            # On ignore les 10% les plus lents (bloqués ou loin)
            cutoff = int(len(arrival_times) * 0.9)
            cutoff = min(cutoff, len(arrival_times) - 1)
            self.reference_arrival_time = arrival_times[cutoff]
        else:
            self.reference_arrival_time = 0.0

        # C. Mouvement
        # On remet tout le monde à 0.0 offset pour tester la fluidité maximale
        self._apply_tot_movement(pikemen, self.reference_arrival_time, 0.0)
        self._apply_tot_movement(crossbowmen, self.reference_arrival_time, 0.0)
        self._apply_tot_movement(knights, self.reference_arrival_time, 0.0)

    def _apply_tot_movement(self, units: list[Unit], t_ref: float, time_offset: float):
        target_time = t_ref + time_offset
        sync_tolerance = 0.5

        for unit in units:
            if unit.id not in self.formation_orders:
                continue

            dest = self.formation_orders[unit.id]
            dist = self.get_dist(unit.position, dest)

            if dist < 0.5:
                # Arrivé au poste : micro-mouvement pour rester actif
                unit.current_order = {"type": "move_to", "target": unit.position}
                continue

            # --- LE RETOUR DE LA FLUIDITÉ ---
            # Si on est loin (> 5m), ON COURT.
            # On ignore complètement le timing. C'est ça qui manquait.
            # Les unités vont avancer "ensemble" car elles ont toutes l'ordre de bouger.
            if dist > 5.0:
                unit.current_order = {"type": "move_to", "target": dest}
                continue
            # --------------------------------

            # Si on est proche (< 5m), on active le frein intelligent (ToT)
            # pour que l'impact final soit synchronisé.
            my_time_needed = dist / unit.speed if unit.speed > 0 else 0

            if my_time_needed < (target_time - sync_tolerance):
                # Trop en avance pour l'impact final -> On attend
                unit.current_order = {"type": "move_to", "target": unit.position}
            else:
                # C'est le moment d'y aller
                unit.current_order = {"type": "move_to", "target": dest}

    # =========================================================================
    # PHASE COMBAT
    # =========================================================================

    def _execute_combat_logic(self, pikemen: list[Unit], knights: list[Unit], crossbowmen: list[Unit], enemies: list[Unit], bf: Battlefield):
        melee = pikemen + knights
        for unit in melee:
            if self._is_unit_engaged(unit, enemies):
                continue
            if enemies:
                nearest = min(enemies, key=lambda e: self.get_dist(unit.position, e.position))
                self._order_attack_opti(unit, nearest)

        for unit in crossbowmen:
            self._micro_archer(unit, enemies, unit.position, bf)

    # =========================================================================
    # GÉOMÉTRIE (TRI ANGULAIRE COMPLET)
    # =========================================================================

    def _calculate_formation_geometry(self, pikemen: list[Unit], knights: list[Unit], crossbowmen: list[Unit], enemies: list[Unit], bf: Battlefield):
        if not enemies:
            return

        # Centroid Ennemi
        ex_sum, ey_sum = 0, 0
        for e in enemies:
            ex_sum += e.position[0]
            ey_sum += e.position[1]
        enemy_centroid = (ex_sum / len(enemies), ey_sum / len(enemies))

        # Rayon Ennemi
        max_d = 0
        for e in enemies:
            d = self.get_dist(e.position, enemy_centroid)
            if d > max_d:
                max_d = d
        enemy_radius = max_d

        # Axe Attaque
        my_infantry = pikemen + crossbowmen
        if not my_infantry:
            my_infantry = knights
        if not my_infantry:
            return

        mx = sum(u.position[0] for u in my_infantry) / len(my_infantry)
        my = sum(u.position[1] for u in my_infantry) / len(my_infantry)

        dx = enemy_centroid[0] - mx
        dy = enemy_centroid[1] - my
        attack_angle = math.atan2(dy, dx)

        # Génération Arcs
        self._assign_arc_orders_angular(pikemen, enemy_centroid, enemy_radius + 2.0, attack_angle, bf)
        self._assign_arc_orders_angular(crossbowmen, enemy_centroid, enemy_radius + 9.0, attack_angle, bf)

        # Knights : Impact Frontal
        if knights:
            kx = enemy_centroid[0] - math.cos(attack_angle) * (enemy_radius + 2.0)
            ky = enemy_centroid[1] - math.sin(attack_angle) * (enemy_radius + 2.0)
            k_pt = self._clamp_position((kx, ky), bf)
            for k in knights:
                self.formation_orders[k.id] = k_pt

    def _assign_arc_orders_angular(self, units: list[Unit], center: tuple, radius: float, axis_angle: float, bf: Battlefield):
        if not units:
            return
        n = len(units)
        base_angle = axis_angle + math.pi
        arc_spread = math.radians(140)

        # Densité
        final_radius = max(radius, (n * 1.0) / arc_spread)

        # 1. Slots cibles
        target_slots = []
        start = base_angle - (arc_spread / 2)
        for i in range(n):
            t = i / (n - 1) if n > 1 else 0.5
            ang = start + (t * arc_spread)
            tx = center[0] + math.cos(ang) * final_radius
            ty = center[1] + math.sin(ang) * final_radius
            target_slots.append({"angle": ang, "pos": self._clamp_position((tx, ty), bf)})

        # 2. Slots unités
        unit_slots = []
        for u in units:
            ang = math.atan2(u.position[1] - center[1], u.position[0] - center[0])
            unit_slots.append({"angle": ang, "unit": u})

        # 3. Tri relatif
        def rel_angle(a):
            d = a - base_angle
            return math.atan2(math.sin(d), math.cos(d))

        target_slots.sort(key=lambda x: rel_angle(x["angle"]))
        unit_slots.sort(key=lambda x: rel_angle(x["angle"]))

        # 4. Assignation
        for i in range(n):
            self.formation_orders[unit_slots[i]["unit"].id] = target_slots[i]["pos"]

    def _check_charge_condition(self, my_units: list[Unit], enemies: list[Unit]) -> bool:
        if self.reference_arrival_time < 0.5 and self.reference_arrival_time > 0:
            return True
        for u in my_units:
            for e in enemies:
                if self.get_dist(u.position, e.position) < 4.0:
                    return True
        return False
