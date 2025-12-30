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
        self.march_progression = 0.0  # Pour l'arc de cerle glissant
        self.reference_arrival_time = 0.0

    def update(self, bf: Battlefield, tick: int) -> None:
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
            # APPEL V2
            # self._execute_march_logic(pikemen, knights, crossbowmen, enemies, bf, tick)
            self._execute_sliding_march_logic(pikemen, knights, crossbowmen, enemies, bf, tick)

    # =========================================================================
    # PHASE 1 : MARCHE (SLIDING ARC)
    # =========================================================================

    # Fonction V2
    def _execute_march_logic(self, pikemen: list[Unit], knights: list[Unit], crossbowmen: list[Unit], enemies: list[Unit], bf: Battlefield, tick: int):
        # A. Recalcul périodique de la géométrie (tous les 5 ticks pour stabilité)
        if tick % 5 == 0 or not self.formation_orders:
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

    # Fonction V2
    def _apply_virtual_speed_movement(self, units: list[Unit], t_ref: float, time_offset: float):
        """
        Applique le mouvement en utilisant la technique de la 'Carotte' (Virtual Speed).
        L'unité reçoit un ordre de mouvement court correspondant exactement à la distance
        qu'elle doit parcourir ce tick-ci pour arriver à l'heure.
        """
        target_time = t_ref + time_offset

        # On assume un dt (delta time) standard de 1/FPS.
        # Si le jeu tourne à 60 FPS simulés (dt ~ 0.016) ou 10 FPS (dt ~ 0.1).
        # Par sécurité, on prend une valeur arbitraire raisonnable pour le calcul du 'step',
        # car l'API move_to fera le vrai calcul physique ensuite.
        # On vise un horizon de projection de 0.2s pour lisser le mouvement.
        projection_horizon = 0.2

        for unit in units:
            if unit.id not in self.formation_orders:
                continue

            dest = self.formation_orders[unit.id]
            dist = self.get_dist(unit.position, dest)

            # Si très proche, micro-ajustement
            if dist < 0.2:
                unit.current_order = {"type": "move_to", "target": dest}
                continue

            # 1. Calcul de la vitesse requise pour arriver à T_target
            # Vitesse = Distance / Temps
            if target_time <= 0.1:
                # Retard ou temps écoulé : Vitesse Max
                req_speed = unit.speed
            else:
                req_speed = dist / target_time

            # 2. Clamping (On ne peut pas dépasser la vitesse max physique)
            final_speed = min(req_speed, unit.speed)

            # 3. Minimum vital (pour éviter le freeze total sur des arrondis)
            # On force une vitesse minimale de 10% sauf si on est vraiment arrivé
            final_speed = max(final_speed, unit.speed * 0.1)

            # 4. TECHNIQUE DE LA CAROTTE (Virtual Target Injection)
            # Au lieu de viser 'dest' (loin), on vise un point intermédiaire.
            # Ce point est à une distance = Vitesse_Voulue * Horizon
            step_dist = final_speed * projection_horizon

            # Si le pas dépasse la distance réelle, on vise la vraie cible
            if step_dist >= dist:
                virtual_target = dest
            else:
                # Projection vectorielle
                dx = dest[0] - unit.position[0]
                dy = dest[1] - unit.position[1]
                # Normalisation
                vx = dx / dist
                vy = dy / dist

                virtual_target = (unit.position[0] + vx * step_dist, unit.position[1] + vy * step_dist)

            # 5. Envoi de l'ordre
            # L'unité va essayer d'atteindre ce point proche à vitesse max,
            # ce qui reviendra physiquement à avancer de 'step_dist'.
            unit.current_order = {"type": "move_to", "target": virtual_target}

    # Fonction V3
    def _execute_sliding_march_logic(self, pikemen: list[Unit], knights: list[Unit], crossbowmen: list[Unit], enemies: list[Unit], bf: Battlefield, tick: int):
        # 1. Mise à jour de la progression de l'arc
        self._update_march_progression(pikemen + crossbowmen, enemies)

        # 2. Calcul de la géométrie SUR L'ARC INTERPOLÉ
        self._calculate_sliding_geometry(pikemen, knights, crossbowmen, enemies, bf)

        # 3. Application du mouvement avec la nouvelle fonction système
        self._apply_controlled_movement(pikemen, bf)
        self._apply_controlled_movement(crossbowmen, bf)
        self._apply_controlled_movement(knights, bf)

    # Fonction V3
    def _update_march_progression(self, infantry: list[Unit], enemies: list[Unit]):
        """
        Fait avancer le curseur de progression (0.0 -> 1.0)
        """
        if not infantry or not enemies:
            return

        # Barycentres
        my_center = self._get_centroid(infantry)
        en_center = self._get_centroid(enemies)

        total_dist = math.dist(my_center, en_center)

        if total_dist < 5.0:
            self.march_progression = 1.0
            return

        # Vitesse d'avancée de l'arc (arbitraire ou basée sur l'unité moyenne)
        # Disons 1.2 m/s (vitesse standard infanterie)
        arc_speed = 1.2

        # Progression ajoutée ce tick (dt ~ 1/60eme si 60fps, adapte selon ton moteur)
        # Supposons dt = 0.1 pour être safe ou passons le dt en paramètre si possible
        dt = 1 / 30

        advance = (arc_speed * dt) / total_dist

        self.march_progression += advance
        self.march_progression = min(self.march_progression, 1.0)

    # Fonction V3
    def _apply_controlled_movement(self, units: list[Unit], bf: Battlefield):
        # Pour l'instant, on laisse les unités aller à fond vers l'arc glissant
        # car l'arc lui-même sert de régulateur de vitesse.
        dt = 0.1  # À récupérer proprement du moteur si possible

        for unit in units:
            if unit.id not in self.formation_orders:
                continue

            target = self.formation_orders[unit.id]

            # Utilisation de la nouvelle fonction système (propre !)
            # On met speed_limit = unit.speed (à fond) car l'arc est proche.
            # Si on voulait ralentir pour attendre, on réduirait ici.

            # TRICK : On injecte l'ordre directement pour le tick suivant
            # Mais comme ton system.py gère l'ordre via unit.current_order, on adapte :

            # Option A : Si ton moteur appelle process_movement automatiquement :
            # On ne peut pas passer speed_limit dans le dict current_order standard sans modif engine.
            # SI TU AS MODIFIÉ system.py, tu peux créer un nouveau type d'ordre :

            unit.current_order = {
                "type": "move_to_controlled",  # Nouveau type à gérer dans UnitController si tu veux
                "target": target,
                "speed_limit": unit.speed,
            }

            # ATTENTION : Si tu ne veux pas modifier UnitController dans system.py,
            # Tu dois faire le mouvement "manuel" ici (hacky mais utilise la fonction propre).
            # MovementSystem.move_to_position_with_speed(unit, target[0], target[1], dt, bf, unit.speed)
            # unit.current_order = None # Pour pas que le moteur interfère

            # RECOMMANDATION : Utilise le move_to standard pour l'instant
            # car l'arc glissant gère déjà le positionnement.
            unit.current_order = {"type": "move_to", "target": target}

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

    # Fonction V2
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

    # Fonction V3
    def _calculate_sliding_geometry(self, pikemen: list[Unit], knights: list[Unit], crossbowmen: list[Unit], enemies: list[Unit], bf: Battlefield):
        if not enemies:
            return

        # 1. Définition des ancres (Départ et Arrivée)
        my_infantry = pikemen + crossbowmen
        if not my_infantry:
            my_infantry = knights

        start_center = self._get_centroid(my_infantry)
        end_center = self._get_centroid(enemies)  # Ennemi actuel

        # 2. Calcul du Centre Virtuel de l'Arc (Interpolation)
        # T = progression. Si T=0, on est sur nous. Si T=1, sur l'ennemi.
        # On ajoute un offset pour que l'arc soit toujours un peu "devant" la position théorique
        # pour forcer les unités à avancer.
        lead_distance = 5.0  # L'arc est projeté 5m devant la progression actuelle

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
        # Angle : Toujours vers l'ennemi
        attack_angle = math.atan2(vec_y, vec_x)

        # Rayon : On peut commencer petit et grandir, ou rester fixe.
        # Restons fixe sur le rayon final pour simplifier.
        max_d = 0
        for e in enemies:
            d = self.get_dist(e.position, end_center)
            if d > max_d:
                max_d = d
        enemy_radius = max_d

        # 4. Génération (On utilise ta méthode angulaire symétrique qui marche bien)
        self._assign_arc_orders_angular(pikemen, virtual_center, enemy_radius + 2.0, attack_angle, bf)
        self._assign_arc_orders_angular(crossbowmen, virtual_center, enemy_radius + 9.0, attack_angle, bf)

        if knights:
            # Les chevaliers peuvent viser directement l'impact final pour contourner
            # ou suivre l'arc. Suivons l'arc pour l'instant.
            kx = virtual_center[0] - math.cos(attack_angle) * (enemy_radius + 2.0)
            ky = virtual_center[1] - math.sin(attack_angle) * (enemy_radius + 2.0)
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
        # if self.reference_arrival_time < 0.5 and self.reference_arrival_time > 0:
        #     return True

        # 2. Ennemi au contact (Sécurité)
        for u in my_units:
            for e in enemies:
                if self.get_dist(u.position, e.position) < 4.0:
                    return True
        return False
