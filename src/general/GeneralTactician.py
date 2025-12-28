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

        # --- ÉTAT INTERNE ---
        self.phase = "MARCH"
        self.formation_orders = {}  # {unit_id: (target_x, target_y)}
        self.reference_arrival_time = 0.0

    def update(self, bf: Battlefield, tick: int) -> None:
        # 1. PERCEPTION & NETTOYAGE
        my_units = self.get_my_units(bf)
        enemies = self.get_enemy_units(bf)

        if not my_units or not enemies:
            return

        # Classification simplifiée et robuste
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
                pikemen.append(u)

        # 2. GESTION DE LA PHASE (KILL SWITCH)
        if self.phase == "MARCH":
            if self._check_charge_condition(my_units, enemies):
                self.phase = "COMBAT"
                self.formation_orders.clear()

        # 3. BRANCHEMENT LOGIQUE
        if self.phase == "COMBAT":
            self._execute_combat_logic(pikemen, knights, crossbowmen, enemies, bf)
        else:
            self._execute_march_logic(pikemen, knights, crossbowmen, enemies, bf, tick)

    # =========================================================================
    # PHASE 1 : LOGIQUE DE MARCHE (TIME ON TARGET)
    # =========================================================================

    def _execute_march_logic(self, pikemen: list[Unit], knights: list[Unit], crossbowmen: list[Unit], enemies: list[Unit], bf: Battlefield, tick: int):
        # A. RECALCUL GÉOMÉTRIQUE (Moins fréquent pour stabilité, mais tri topologique assure la fluidité)
        if tick % 5 == 0 or not self.formation_orders:
            self._calculate_formation_geometry(pikemen, knights, crossbowmen, enemies, bf)

        # B. CALCUL DU TEMPS DE RÉFÉRENCE (T_ref)
        infantry = pikemen + crossbowmen
        if infantry:
            max_time_needed = 0.0
            for u in infantry:
                if u.id in self.formation_orders:
                    target = self.formation_orders[u.id]
                    dist = self.get_dist(u.position, target)  # DRY: Utilisation helper
                    time_needed = dist / u.speed if u.speed > 0 else 0
                    if time_needed > max_time_needed:
                        max_time_needed = time_needed
            self.reference_arrival_time = max_time_needed

        # C. APPLICATION DU MOUVEMENT (ToT)
        self._apply_tot_movement(pikemen, self.reference_arrival_time, 0.0)
        self._apply_tot_movement(crossbowmen, self.reference_arrival_time, 0.0)
        self._apply_tot_movement(knights, self.reference_arrival_time, -2.0)

    def _apply_tot_movement(self, units: list[Unit], t_ref: float, time_offset: float):
        target_time = t_ref + time_offset

        for unit in units:
            if unit.id not in self.formation_orders:
                continue

            dest = self.formation_orders[unit.id]
            dist = self.get_dist(unit.position, dest)  # DRY

            if dist < 0.5:
                continue

            # Logique ToT: Ralentir pour arriver pile à l'heure
            if target_time <= 0:
                req_speed = unit.speed
            else:
                req_speed = dist / target_time

            final_speed = min(req_speed, unit.speed)
            # Clamping vitesse min pour éviter l'arrêt total (cible mouvante)
            final_speed = max(final_speed, unit.speed * 0.2)

            # Note: Si l'API le permettait, on set_speed ici.
            # A défaut, on donne l'ordre move_to classique vers la destination finale.
            # L'ajustement fin de vitesse nécessiterait une interpolation de position,
            # mais pour l'instant on mise sur la synchro macro.
            unit.current_order = {"type": "move_to", "target": dest}

    # =========================================================================
    # PHASE 2 : COMBAT
    # =========================================================================

    def _execute_combat_logic(self, pikemen: list[Unit], knights: list[Unit], crossbowmen: list[Unit], enemies: list[Unit], bf: Battlefield):
        # Mêlée : "Chien d'attaque"
        melee_forces = pikemen + knights
        for unit in melee_forces:
            if self._is_unit_engaged(unit, enemies):
                continue

            # DRY: Utilisation de unit.dist_to (méthode de Unit) ou self.get_dist
            nearest = min(enemies, key=lambda e: self.get_dist(unit.position, e.position))
            self._order_attack_opti(unit, nearest)

        # Distance : Micro-gestion basique
        for unit in crossbowmen:
            self._micro_archer(unit, enemies, unit.position, bf)

    # =========================================================================
    # GÉOMÉTRIE (LE CERVEAU)
    # =========================================================================

    def _calculate_formation_geometry(self, pikemen: list[Unit], knights: list[Unit], crossbowmen: list[Unit], enemies: list[Unit], bf: Battlefield):
        if not enemies:
            return

        # 1. ANALYSE ENNEMI
        enemy_centroid = self._get_centroid(enemies)

        # Rayon Ennemi (Bounding Circle)
        # DRY: get_dist au carré manuel optimisé ou simple dist
        max_dist = 0
        for e in enemies:
            d = self.get_dist(e.position, enemy_centroid)
            if d > max_dist:
                max_dist = d
        enemy_radius = max_dist

        # 2. AXE D'ATTAQUE (Complet X et Y)
        my_infantry = pikemen + crossbowmen
        if not my_infantry:
            my_infantry = knights

        if not my_infantry:
            return

        my_centroid = self._get_centroid(my_infantry)

        # Vecteur de Nous -> Eux
        dx = enemy_centroid[0] - my_centroid[0]
        dy = enemy_centroid[1] - my_centroid[1]
        attack_angle = math.atan2(dy, dx)  # Angle complet, pas de suppression de Y

        # 3. GÉNÉRATION DES ARCS (Topologie stricte pour éviter la dérive)

        # Piquiers : Contact strict
        self._assign_arc_orders_topological(pikemen, enemy_centroid, enemy_radius + 1.0, attack_angle, bf)

        # Arbalétriers : Arrière ligne
        c_radius = enemy_radius + 8.0  # Valeur fixe plus stable que avg_range * 0.8 qui fluctue
        self._assign_arc_orders_topological(crossbowmen, enemy_centroid, c_radius, attack_angle, bf)

        # 4. KNIGHTS (Percussion)
        if knights:
            # Impact point: Sur le cercle ennemi, face à nous
            # On inverse le vecteur d'attaque pour trouver le point de contact face à nous
            impact_x = enemy_centroid[0] - math.cos(attack_angle) * (enemy_radius + 2.0)
            impact_y = enemy_centroid[1] - math.sin(attack_angle) * (enemy_radius + 2.0)

            impact_point = self._clamp_position((impact_x, impact_y), bf)

            # Les chevaliers s'agglutinent sur ce point de rupture
            for k in knights:
                self.formation_orders[k.id] = impact_point

    def _assign_arc_orders_topological(self, units: list[Unit], center: tuple, radius: float, axis_angle: float, bf: Battlefield):
        """
        Génère l'arc et assigne les positions en triant les unités et les points
        selon leur angle relatif. Cela empêche les croisements et la dérive.
        """
        if not units:
            return

        n = len(units)
        # Arc de 140 degrés centré sur l'axe d'attaque inversé (face à nous)
        # L'angle d'attaque va de Nous -> Eux. L'arc de formation doit être "derrière" le point de contact par rapport à l'ennemi.
        # En réalité, on veut entourer l'ennemi. Donc on centre l'arc sur attack_angle + PI (le côté face à nous).
        base_angle = axis_angle + math.pi

        arc_spread = math.radians(140)

        # Gestion densité
        circumference = n * 1.0  # 1m par unité
        req_radius = circumference / arc_spread
        final_radius = max(radius, req_radius)

        start_angle = base_angle - (arc_spread / 2)

        # 1. Création des points cibles (Target Points)
        points = []
        for i in range(n):
            t = i / (n - 1) if n > 1 else 0.5
            angle = start_angle + (t * arc_spread)

            tx = center[0] + math.cos(angle) * final_radius
            ty = center[1] + math.sin(angle) * final_radius
            points.append(self._clamp_position((tx, ty), bf))

        # 2. Tri Topologique (La solution à la dérive)
        # On projette la position des unités sur le vecteur perpendiculaire à l'attaque.
        # Cela nous donne leur "gauche/droite" relative.

        # Vecteur perpendiculaire (rotation 90deg)
        perp_angle = axis_angle + (math.pi / 2)
        perp_x = math.cos(perp_angle)
        perp_y = math.sin(perp_angle)

        def get_projection_score(u: Unit):
            # Produit scalaire avec la perpendiculaire
            # (projette l'unité sur l'axe gauche-droite relatif à l'attaque)
            rel_x = u.position[0] - center[0]
            rel_y = u.position[1] - center[1]
            return (rel_x * perp_x) + (rel_y * perp_y)

        # On trie les unités de "Gauche" à "Droite" (relativement à l'axe d'attaque)
        sorted_units = sorted(units, key=get_projection_score, reverse=True)

        # Les points sont déjà générés de manière ordonnée angulairement.
        # Il faut juste s'assurer que l'ordre des points correspond au sens du tri des unités.
        # L'arc est généré de (base - spread/2) à (base + spread/2).
        # Vérifions si cela correspond au sens du vecteur perpendiculaire.
        # Pour simplifier : On assigne i -> i. Si ça croise massivement, c'est que l'arc est généré à l'envers
        # par rapport au tri perp, mais mathématiquement cos(angle) suit la projection.

        for i, u in enumerate(sorted_units):
            self.formation_orders[u.id] = points[i]

    def _check_charge_condition(self, my_units: list[Unit], enemies: list[Unit]) -> bool:
        if self.reference_arrival_time < 0.5 and self.reference_arrival_time > 0:
            return True

        # Optimisation DRY
        for u in my_units:
            # On vérifie seulement si on est TRES proche d'un ennemi quelconque
            # Pas besoin de trier toute la liste enemies
            for e in enemies:
                if self.get_dist(u.position, e.position) < 4.0:
                    return True
        return False
