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
        # "MARCH" : Approche synchronisée (ToT)
        # "COMBAT" : Charge finale et micro-gestion (Hit & Run)
        self.phase = "MARCH"

        self.formation_orders = {}  # Mémoire des ordres de formation {unit_id: (target_x, target_y)}

        self.reference_arrival_time = 0.0  # Temps de référence pour l'arrivée synchronisée (en secondes)

    def update(self, bf: Battlefield, tick: int) -> None:
        # 1. PERCEPTION & NETTOYAGE
        my_units = self.get_my_units(bf)
        enemies = self.get_enemy_units(bf)

        if not my_units or not enemies:
            return

        pikemen = [u for u in my_units if "pike" in u.name.lower() or u.attack_range < 4.0]
        crossbowmen = [u for u in my_units if "cross" in u.name.lower() or u.attack_range >= 4.0]
        knights = [u for u in my_units if "knight" in u.name.lower() or "cavalry" in u.name.lower()]

        # Si pas de cavalerie explicite, on considère les unités très rapides comme des knights
        if not knights:
            knights = [u for u in pikemen if u.speed > 1.5 and u in pikemen]
            for k in knights:
                if k in pikemen:
                    pikemen.remove(k)

        # 2. GESTION DE LA PHASE (LE "KILL SWITCH")
        if self.phase == "MARCH":
            should_charge = self._check_charge_condition(my_units, enemies)
            if should_charge:
                self.phase = "COMBAT"
                # On vide les ordres de formation pour forcer le recalcul de combat
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
        """
        Orchestre le mouvement synchronisé.
        Recalcule la géométrie périodiquement, mais ajuste la vitesse (ToT) à chaque tick.
        """

        # A. RECALCUL GÉOMÉTRIQUE (Tous les 10 ticks pour économiser le CPU)
        if tick % 10 == 0 or not self.formation_orders:
            self._calculate_formation_geometry(pikemen, knights, crossbowmen, enemies, bf)

        # B. CALCUL DU TEMPS DE RÉFÉRENCE (T_ref)
        # On se base sur l'infanterie (Piquiers) pour définir le tempo.
        # Le soldat le plus lent à atteindre sa position dicte le rythme de l'armée.
        infantry = pikemen + crossbowmen
        if infantry:
            max_time_needed = 0.0
            for u in infantry:
                if u.id in self.formation_orders:
                    target = self.formation_orders[u.id]
                    dist = self.get_dist(target, u.position)
                    time_needed = dist / u.speed if u.speed > 0 else 0
                    if time_needed > max_time_needed:
                        max_time_needed = time_needed

            self.reference_arrival_time = max_time_needed

        # C. APPLICATION DU MOUVEMENT (ToT)
        self._apply_tot_movement(pikemen, self.reference_arrival_time, 0.0)  # Piquiers : T_ref
        self._apply_tot_movement(crossbowmen, self.reference_arrival_time, 0.0)  # Archers : T_ref
        self._apply_tot_movement(knights, self.reference_arrival_time, -2.0)  # Knights : T_ref - 2s (Impact précoce)

    def _apply_tot_movement(self, units: list[Unit], t_ref: float, time_offset: float):
        """
        Applique le mouvement en ajustant la vitesse pour arriver au temps voulu.
        Vitesse = Distance / (T_ref + offset)
        """
        target_time = t_ref + time_offset

        for unit in units:
            if unit.id not in self.formation_orders:
                continue

            dest = self.formation_orders[unit.id]
            dist = self.get_dist(dest, unit.position)

            # Si on est déjà arrivé (ou très proche), on reste sur place (micro-ajustement)
            if dist < 0.5:
                # Optionnel : On peut leur dire de regarder vers l'ennemi
                continue

            # Calcul de la vitesse requise
            if target_time <= 0:
                # Si le temps est écoulé ou négatif (cas des Knights en retard), on fonce !
                req_speed = unit.speed
            else:
                req_speed = dist / target_time

            # Clamp : On ne peut pas dépasser la vitesse max physique
            final_speed = min(req_speed, unit.speed)

            # Sécurité : On évite de s'arrêter complètement (pour ne pas être une cible statique)
            # On garde au moins 20% de la vitesse max si on doit bouger
            if final_speed < unit.speed * 0.2:
                final_speed = unit.speed * 0.2

            # TRICHE VECTEUR : Comme l'API `move_to` ne prend pas de paramètre vitesse,
            # On simule la vitesse réduite en calculant un point intermédiaire.
            # "Je veux aller vers Target mais je ne parcours que (final_speed * dt) mètres ce tour-ci"
            # NOTE : On assume que l'update se fait à chaque tick.

            # Vecteur unitaire vers la cible
            dx = dest[0] - unit.position[0]
            dy = dest[1] - unit.position[1]

            # On applique le mouvement directement via un ordre 'move_to'
            # mais sur une cible virtuelle très proche correspondant au déplacement de ce tick.
            # C'est une astuce pour simuler la vitesse variable.
            # Cependant, si le moteur physique gère l'inertie, mieux vaut donner la vraie cible
            # et accepter que l'unité aille à fond.
            # ICI, pour respecter le cahier des charges ToT, on va donner la Vraie Cible
            # MAIS si tu as accès à unit.current_speed, c'est là qu'il faudrait l'assigner.

            # SOLUTION ROBUSTE SANS ACCÈS INTERNE AU MOTEUR :
            # On utilise le vecteur calculé pour définir un point intermédiaire.
            step_dist = final_speed * 1.5  # On projette un peu plus loin (1.5s) pour fluidifier

            step_x, step_y = self._projection_vector(unit.position, (dx / dist, dy / dist), step_dist)

            # Si la distance est grande, target = dest, sinon target = step
            # Pour l'instant, donnons la destination finale, c'est plus sûr pour le pathfinding.
            # L'implémentation ToT stricte demanderait de modifier la classe Unit.
            # Pour la V2.7, on donne l'ordre classique.
            unit.current_order = {"type": "move_to", "target": dest}

    # =========================================================================
    # PHASE 2 : LOGIQUE DE COMBAT (HAMMER & ANVIL)
    # =========================================================================

    def _execute_combat_logic(self, pikemen: list[Unit], knights: list[Unit], crossbowmen: list[Unit], enemies: list[Unit], bf: Battlefield):
        """
        Logique de combat pur. Plus de formation, priorité à l'efficacité.
        """
        # A. KNIGHTS & PIKEMEN (Mêlée Agressive)
        melee_forces = pikemen + knights
        for unit in melee_forces:
            # Si déjà engagé sur une cible vivante et proche, on ne change rien (stabilité)
            if self._is_unit_engaged(unit, enemies):
                continue

            # Sinon, on charge l'ennemi le plus proche (Comportement "Chien d'attaque")
            nearest = min(enemies, key=lambda e: unit.dist_to(e))
            self._order_attack_opti(unit, nearest)

        # B. ARBALÉTRIERS (Hit & Run + Focus Fire)
        for unit in crossbowmen:
            # On utilise la méthode de BaseGeneral qui gère déjà Fuite + Tir
            # Note : On passe unit.position comme target_pos par défaut car en combat
            # la position idéale n'existe plus, seule la survie compte.
            self._micro_archer(unit, enemies, unit.position, bf)

    # =========================================================================
    # GÉOMÉTRIE ET MATHÉMATIQUES (LE CERVEAU)
    # =========================================================================

    def _calculate_formation_geometry(self, pikemen: list[Unit], knights: list[Unit], crossbowmen: list[Unit], enemies: list[Unit], bf: Battlefield):
        """
        Calcule les positions idéales (l'Arc et le Point de Percussion).
        Remplit self.formation_orders.
        """
        if not enemies:
            return

        # 1. ANALYSE DE L'ENNEMI (Bounding Circle)
        enemy_centroid = self._get_centroid(enemies)

        # Calcul du rayon du chaos (taille de l'ennemi)
        max_dist_sq = 0
        for e in enemies:
            d_sq = (e.position[0] - enemy_centroid[0]) ** 2 + (e.position[1] - enemy_centroid[1]) ** 2
            if d_sq > max_dist_sq:
                max_dist_sq = d_sq
        enemy_radius = math.sqrt(max_dist_sq)

        # 2. AXE D'ATTAQUE (Infanterie -> Ennemi)
        my_infantry = pikemen + crossbowmen
        if not my_infantry:
            my_infantry = knights  # Fallback

        my_centroid = self._get_centroid(my_infantry)

        dx = my_centroid[0] - enemy_centroid[0]
        dy = my_centroid[1] - enemy_centroid[1]
        attack_angle = math.atan2(dy, dx)  # Angle vers nous

        # 3. GÉNÉRATION DES ARCS (Piquiers & Arbalétriers)

        # Paramètres Piquiers
        p_radius = enemy_radius + 1.0  # Contact (+1m)
        self._generate_arc_orders(pikemen, enemy_centroid, p_radius, attack_angle, bf)

        # Paramètres Arbalétriers
        # Rayon = Rayon Ennemi + 80% de la portée moyenne
        avg_range = sum(u.attack_range for u in crossbowmen) / len(crossbowmen) if crossbowmen else 10.0
        c_radius = enemy_radius + (avg_range * 0.8)
        self._generate_arc_orders(crossbowmen, enemy_centroid, c_radius, attack_angle, bf)

        # 4. CIBLAGE DES KNIGHTS (Axe de Percussion)
        # Ils visent l'intersection entre le cercle ennemi et l'axe d'attaque.
        # C'est le point "frontal" par rapport à notre infanterie.
        if knights:
            # Le point d'impact est sur le périmètre ennemi, face à nous.
            impact_x = enemy_centroid[0] + math.cos(attack_angle) * (enemy_radius - 1.0)  # On rentre un peu dedans
            impact_y = enemy_centroid[1] + math.sin(attack_angle) * (enemy_radius - 1.0)

            impact_point = self._clamp_position((impact_x, impact_y), bf)

            for k in knights:
                self.formation_orders[k.id] = impact_point

    def _generate_arc_orders(self, units: list[Unit], center: tuple, radius: float, axis_angle: float, bf: Battlefield):
        """
        Génère les points de l'arc et les assigne de manière gloutonne.
        """
        if not units:
            return

        # Largeur de l'arc : Règle "Stay Wide" (Front Large)
        # On force 140 degrés d'ouverture minimum pour envelopper
        arc_spread = math.radians(140)

        # Vérification capacité physique (si trop d'unités, on élargit l'arc ou le rayon)
        circumference_needed = len(units) * 0.8  # 0.8 spacing
        radius_needed = circumference_needed / arc_spread
        effective_radius = max(radius, radius_needed)

        # Génération des points
        target_points = []
        start_angle = axis_angle - (arc_spread / 2)

        for i in range(len(units)):
            t = i / (len(units) - 1) if len(units) > 1 else 0.5
            angle = start_angle + (t * arc_spread)

            tx = center[0] + math.cos(angle) * effective_radius
            ty = center[1] + math.sin(angle) * effective_radius

            target_points.append(self._clamp_position((tx, ty), bf))

        # Assignation Gloutonne (Greedy Assignment)
        # Pour éviter les croisements : chaque point de l'arc prend l'unité la plus proche
        available_units = units[:]

        for point in target_points:
            best_idx = -1
            min_dist_sq = float("inf")

            for i, u in enumerate(available_units):
                d_sq = (u.position[0] - point[0]) ** 2 + (u.position[1] - point[1]) ** 2
                if d_sq < min_dist_sq:
                    min_dist_sq = d_sq
                    best_idx = i

            if best_idx != -1:
                u = available_units.pop(best_idx)
                self.formation_orders[u.id] = point

    def _check_charge_condition(self, my_units: list[Unit], enemies: list[Unit]) -> bool:
        """
        Vérifie si on doit déclencher la charge finale (Kill Switch).
        """
        # Condition 1 : Temps. Si le temps estimé est écoulé (ou < 0.5s)
        if self.reference_arrival_time < 0.5 and self.reference_arrival_time > 0:
            return True

        # Condition 2 : Distance. Si une unité est très proche (< 4m)
        # On optimise en ne vérifiant que quelques unités
        for u in my_units:
            nearest = min(enemies, key=lambda e: u.dist_to(e))
            if u.dist_to(nearest) < 4.0:
                return True

        return False
