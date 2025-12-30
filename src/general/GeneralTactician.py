from __future__ import annotations
from typing import TYPE_CHECKING, Dict, List, Optional
import math

from src.general.general_base import BaseGeneral

if TYPE_CHECKING:
    from src.engine.battlefield import Battlefield
    from src.units.unit_base import Unit


class GeneralTactician(BaseGeneral):
    def __init__(self, player_id: int):
        super().__init__(player_id, name="General TACTICIAN")

        # --- ÉTAT INTERNE ---
        self.phase = "MARCH"
        self.formation_orders: Dict[int, tuple[float, float]] = {}
        self.reference_arrival_time = 0.0

    def update(self, bf: Battlefield, tick: int) -> None:
        # 1. PERCEPTION
        my_units = self.get_my_units(bf)
        enemies = self.get_enemy_units(bf)

        if not my_units or not enemies:
            return

        # 2. CLASSIFICATION ROBUSTE
        pikemen = []
        crossbowmen = []
        knights = []

        for u in my_units:
            name_lower = u.name.lower()
            if "knight" in name_lower or "cavalry" in name_lower or u.speed > 1.5:
                knights.append(u)
            elif "cross" in name_lower or u.attack_range >= 4.0:
                crossbowmen.append(u)
            else:
                # Fallback par défaut (Piquiers)
                pikemen.append(u)

        # 3. KILL SWITCH (Passage en phase combat)
        if self.phase == "MARCH":
            if self._check_charge_condition(my_units, enemies):
                self.phase = "COMBAT"
                self.formation_orders.clear()

        # 4. EXÉCUTION LOGIQUE
        if self.phase == "COMBAT":
            self._execute_combat_logic(pikemen, knights, crossbowmen, enemies, bf)
        else:
            self._execute_march_logic(pikemen, knights, crossbowmen, enemies, bf, tick)

    # =========================================================================
    # PHASE 1 : MARCHE (TIME ON TARGET AVEC VITESSE VIRTUELLE)
    # =========================================================================

    def _execute_march_logic(self, pikemen: list[Unit], knights: list[Unit], crossbowmen: list[Unit], enemies: list[Unit], bf: Battlefield, tick: int):
        # A. Recalcul périodique de la géométrie (tous les 5 ticks pour stabilité)
        if tick % 2 == 0 or not self.formation_orders:
            self._calculate_formation_geometry(pikemen, knights, crossbowmen, enemies, bf)

        # B. Calcul du Temps de Référence (Robustesse 90ème percentile)
        all_infantry = pikemen + crossbowmen
        arrival_times = []

        for u in all_infantry:
            if u.id in self.formation_orders:
                target = self.formation_orders[u.id]
                dist = self.get_dist(u.position, target)
                safe_speed = u.speed if u.speed > 0.1 else 0.1
                arrival_times.append(dist / safe_speed)

        if arrival_times:
            arrival_times.sort()
            # On ignore les 10% les plus lents (unités bloquées ou outliers)
            cutoff_index = int(len(arrival_times) * 0.9)
            cutoff_index = min(cutoff_index, len(arrival_times) - 1)
            self.reference_arrival_time = arrival_times[cutoff_index]
        else:
            self.reference_arrival_time = 0.0

        # C. Application du mouvement avec modulation de vitesse
        # Offset 0.0 = Synchro parfaite.
        # On pourrait mettre -1.0 aux Knights pour qu'ils arrivent 1s AVANT l'impact si voulu.
        self._apply_virtual_speed_movement(pikemen, self.reference_arrival_time, 0.0)
        self._apply_virtual_speed_movement(crossbowmen, self.reference_arrival_time, 0.0)
        self._apply_virtual_speed_movement(knights, self.reference_arrival_time, 0.0)

    def _apply_virtual_speed_movement(self, units: list[Unit], t_ref: float, time_offset: float):
        """
        Stratégie "Rush & Wait" (Sprint Total) :
        On court à vitesse maximale jusqu'à être quasiment sur le point (0.5m).
        On ne ralentit JAMAIS avant d'être arrivé.
        Cela garantit que toute l'armée bouge instantanément, même ceux qui sont près.
        """
        target_time = t_ref + time_offset

        # On réduit la zone de synchro au strict minimum (un pas)
        # Tant qu'on est à plus de 50cm, on considère qu'on est en voyage.
        FINAL_APPROACH_DIST = 0.5

        # Horizon de projection pour éviter les vibrations à l'arrivée
        projection_horizon = 0.2

        for unit in units:
            if unit.id not in self.formation_orders:
                continue

            dest = self.formation_orders[unit.id]
            dist = self.get_dist(unit.position, dest)

            # --- CAS 1 : SPRINT ABSOLU ---
            # C'est la modification radicale.
            # Peu importe le timing, peu importe les autres.
            # Si tu n'es pas "sur" ton point, tu fonces.
            if dist > FINAL_APPROACH_DIST:
                unit.current_order = {"type": "move_to", "target": dest}
                continue

            # --- CAS 2 : ARRIVÉE & ATTENTE (Le "Luxe") ---
            # On est à moins de 50cm. On est techniquement "en place".
            # C'est MAINTENANT qu'on regarde la montre.

            # Si on est arrivé mais qu'il reste du temps (les copains du Nord arrivent),
            # on ralentit/s'arrête pour maintenir la formation serrée.

            if dist < 0.1:
                # Pile dessus : On garde la position (micro-correction)
                unit.current_order = {"type": "move_to", "target": dest}
                continue

            # On est dans la zone de 10cm à 50cm.
            # On utilise la vitesse virtuelle pour "glisser" doucement vers le point exact
            # en attendant l'heure H.

            if target_time <= 0.1:
                req_speed = unit.speed
            else:
                req_speed = dist / target_time

            # On clamp pour éviter les arrêts complets bizarres
            final_speed = min(req_speed, unit.speed)
            final_speed = max(final_speed, unit.speed * 0.05)  # 5% min pour finir le glissement

            # Application "Carotte" courte portée
            step_dist = final_speed * projection_horizon

            # Projection simple
            dx = dest[0] - unit.position[0]
            dy = dest[1] - unit.position[1]
            virtual_target = (unit.position[0] + (dx / dist) * step_dist, unit.position[1] + (dy / dist) * step_dist)

            unit.current_order = {"type": "move_to", "target": virtual_target}

    # =========================================================================
    # PHASE 2 : COMBAT (OPTIMISÉE)
    # =========================================================================

    def _execute_combat_logic(self, pikemen: list[Unit], knights: list[Unit], crossbowmen: list[Unit], enemies: list[Unit], bf: Battlefield):
        # Mêlée : Comportement agressif (Chien d'attaque)
        melee_forces = pikemen + knights
        for unit in melee_forces:
            if self._is_unit_engaged(unit, enemies):
                continue

            # Recherche locale optimisée via la méthode de Battlefield si accessible,
            # sinon recherche globale brute (fallback sur min/dist)
            if enemies:
                nearest = min(enemies, key=lambda e: self.get_dist(unit.position, e.position))
                self._order_attack_opti(unit, nearest)

        # Distance : Micro-gestion (Kiting)
        for unit in crossbowmen:
            self._micro_archer(unit, enemies, unit.position, bf)

    # =========================================================================
    # GÉOMÉTRIE (TRI ANGULAIRE & CALCULS)
    # =========================================================================

    def _calculate_formation_geometry(self, pikemen: list[Unit], knights: list[Unit], crossbowmen: list[Unit], enemies: list[Unit], bf: Battlefield):
        if not enemies:
            return

        # Centroid Ennemi
        ex_sum = sum(e.position[0] for e in enemies)
        ey_sum = sum(e.position[1] for e in enemies)
        enemy_centroid = (ex_sum / len(enemies), ey_sum / len(enemies))

        # Rayon Ennemi (Bounding Circle)
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

        # Génération Arcs (Triangulation Angulaire pour éviter les croisements)
        # Piquiers : Contact strict (+1m)
        self._assign_arc_orders_angular(pikemen, enemy_centroid, enemy_radius + 2.0, attack_angle, bf)

        # Arbalétriers : Seconde ligne (+8m)
        self._assign_arc_orders_angular(crossbowmen, enemy_centroid, enemy_radius + 9.0, attack_angle, bf)

        # Knights : Point de choc frontal
        if knights:
            kx = enemy_centroid[0] - math.cos(attack_angle) * (enemy_radius + 2.0)
            ky = enemy_centroid[1] - math.sin(attack_angle) * (enemy_radius + 2.0)
            k_pt = self._clamp_position((kx, ky), bf)
            for k in knights:
                self.formation_orders[k.id] = k_pt

    def _assign_arc_orders_angular(self, units: list[Unit], center: tuple, radius: float, axis_angle: float, bf: Battlefield):
        """
        Assigne les positions sur l'arc en triant les unités et les cibles par angle polaire.
        Garantit qu'il n'y a pas de croisement (L'unité la plus à gauche va à la cible la plus à gauche).
        """
        if not units:
            return
        n = len(units)

        # Arc de 140 degrés centré face à nous (donc opposé à l'ennemi)
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

    def _check_charge_condition(self, my_units: list[Unit], enemies: list[Unit]) -> bool:
        """Déclenche la charge si le temps est écoulé ou si l'ennemi est trop proche."""
        # 1. Temps écoulé (Impact imminent)
        if self.reference_arrival_time < 0.5 and self.reference_arrival_time > 0:
            return True

        # 2. Ennemi au contact (Sécurité)
        for u in my_units:
            for e in enemies:
                if self.get_dist(u.position, e.position) < 4.0:
                    return True
        return False
