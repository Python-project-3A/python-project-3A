from __future__ import annotations
from typing import TYPE_CHECKING
from src.general.general_base import BaseGeneral
from src.engine.system import CombatSystem
import math

if TYPE_CHECKING:
    from src.engine.battlefield import Battlefield
    from src.units.unit_base import Unit


class Squad:
    """Représente un groupe logique d'unités avec un objectif commun."""

    def __init__(self, units: list[Unit], role: str):
        self.units = units
        self.role = role  # "MAIN_ASSAULT", "FLANK_LEFT", "PROTECTION"
        self.target_position = (0, 0)
        self.target_cluster = None  # Groupe d'ennemis visé


class GeneralSmart(BaseGeneral):
    def __init__(self, player_id: int):
        super().__init__(player_id, name="General SMART")
        # self.squads: list[Squad] = []
        self.tick_counter = 0
        # Paramètres de personnalité (pour faire varier les IA plus tard)
        self.aggressiveness = 0.5
        self.formation_spacing = 1.5
        self.squads = {"FLANKER": Squad([], "FLANKER"), "DPS": Squad([], "DPS"), "TANK": Squad([], "TANK")}
        self._squads_initialized = False

    def update(self, bf: Battlefield, tick: int) -> None:
        self.tick_counter = tick
        enemies = bf.get_enemy_units(self.player_id)
        if not enemies:
            return
        if not self._squads_initialized:
            self._initialize_squads(bf)
            self._squads_initialized = True
            self._macro_strategy(enemies, bf)

        # 1. PERCEPTION (Macro)
        if tick % 15 == 0:
            self._macro_strategy(enemies, bf)

        # 3. TACTIQUE & MICRO (Exécution par unité)
        for squad in self.squads.values():
            if not squad.units:
                continue
            self._execute_squad_tactics(squad, enemies, bf)

    # --- PHASE 1: PERCEPTION --- --> Dans general_base.py

    # --- PHASE 2: STRATÉGIE ---

    def _macro_strategy(self, enemies, bf: Battlefield):
        """Regroupe toute la réflexion lente."""
        enemy_clusters = self._analyze_enemy_clusters(enemies)
        self._maintain_squads()

        my_units = bf.get_my_units(self.player_id)
        if not my_units:
            return
        self._manage_squads(my_units, enemy_clusters)

    def _initialize_squads(self, bf: Battlefield):
        """
        Scan complet de l'armée pour remplir les escouades.
        """
        my_units = bf.get_my_units(self.player_id)

        for unit in my_units:
            name = unit.name.lower()
            if name == "knight":
                self.squads["FLANKER"].units.append(unit)
            elif name == "crossbowman":
                self.squads["DPS"].units.append(unit)
            elif name == "pikeman":
                self.squads["TANK"].units.append(unit)

    def _maintain_squads(self):
        """
        Supprime les morts des listes. (O(N_vivants)).
        """
        for squad in self.squads.values():
            if squad.units:
                squad.units = [u for u in squad.units if u.is_alive()]

    def _manage_squads(self, my_units: list[Unit], enemy_clusters):
        # CIBLAGE
        if enemy_clusters:
            for squad in self.squads.values():
                squad.target_position = enemy_clusters[0]["center"]

    # --- PHASE 3 & 4: TACTIQUE & MICRO ---
    def _execute_squad_tactics(self, squad: Squad, all_enemies: list[Unit], bf: Battlefield):
        target_pos = squad.target_position

        for unit in squad.units:
            if not unit.is_alive():
                continue

            # --- COMPORTEMENT SPÉCIFIQUE PAR RÔLE ---

            if squad.role == "DPS":
                self._micro_archer(unit, all_enemies, target_pos, bf)

            elif squad.role == "TANK":
                my_archers = [s for s in self.squads.values() if s.role == "DPS"]
                if my_archers and my_archers[0].units:
                    protect_position = self._get_centroid(my_archers[0].units)
                    self._micro_pikeman_protector(unit, all_enemies, protect_position, target_pos, bf)
                else:
                    self._micro_generic_attack(unit, all_enemies, bf)

            elif squad.role == "FLANKER":
                self._micro_knight_flanker(unit, all_enemies, target_pos, bf)

    # --- MICRO-GESTION UNITAIRE ---

    def _micro_knight_flanker(self, unit: Unit, enemies: list["Unit"], target_pos: tuple, bf: Battlefield):
        # 1. Identifier les Cibles et les Menaces
        priority_targets = self._filter_enemies(enemies, ["crossbowman"])  # , "skirmisher"
        if not priority_targets:
            self._micro_generic_attack(unit, enemies, bf)
            return

        ennemies_threats = self._filter_enemies(enemies, ["pikeman", "halberdier"])

        # 2. Trouver la cible la plus proche
        primary_target = CombatSystem.choose_nearest_target(unit, priority_targets, bf)
        dist_to_target = unit.dist_to(primary_target)

        # --- GESTION DU DOGFIGHT (Knights vs Knights) ---
        enemy_knights = self._filter_enemies(enemies, ["knight"])
        if enemy_knights:
            nearest_knight = min(enemy_knights, key=lambda e: self.get_dist(unit.position, e.position))
            dist_knight = self.get_dist(unit.position, nearest_knight.position)

            # SEUIL D'INTERCEPTION (5 mètres)
            if dist_knight < 5.0:
                self._order_attack_opti(unit, nearest_knight)
                return

        # 3. Si pas de duel : ATTAQUE ou MANOEUVRE ?
        if dist_to_target < 3.0:  # si on est assez proche de la cible on attaque
            self._order_attack_opti(unit, primary_target)
            return

        # 4. Calcul du Vecteur de Mouvement (Champs de Potentiel)

        # A. Vecteur d'Attraction (Vers la cible)
        dx, dy = self.soustract_vec(primary_target.position, unit.position)

        # Normalisation
        ndx, ndy = self.normalize_vec((dx, dy))
        if (ndx, ndy) != (0, 0):
            ndx, ndy = self.scale_vec((ndx, ndy), 2.0)  # POIDS D'ATTRACTION FORT (2.0) pour se mieux se diriger vers la cible

        # B. Vecteur de Répulsion (Éviter les Piquiers)
        # On ne regarde que les piquiers sur le chemin (moins de xm, valeur arbitraire qu'on peut changer)
        avoid_radius = 8.0
        repulsion_x, repulsion_y = 0.0, 0.0

        for threat in ennemies_threats:
            d_threat = unit.dist_to(threat)
            if d_threat < avoid_radius:
                # Vecteur : De la menace vers le kngiht (pour s'éloigner)
                rx, ry = self.soustract_vec(unit.position, threat.position)
                rx, ry = self.normalize_vec((rx, ry))

                # Force inversement proportionnelle à la distance (linéaire et pas exponentielle)
                force = 3.0 * (1.0 - (d_threat / avoid_radius))

                repulsion_x += rx * force
                repulsion_y += ry * force

        # 5. Combinaison des vecteurs : Mouvement Final = Attraction + Répulsion
        final_vx, final_vy = self.add_vec((ndx, ndy), (repulsion_x, repulsion_y))

        # Normalisation finale
        final_vx, final_vy = self.normalize_vec((final_vx, final_vy))
        if (final_vx, final_vy) != (0, 0):
            # Projection vers l'avant
            move_target_x, move_target_y = self._projection_vector(unit.position, (final_vx, final_vy), 4.0)

            # Clamp bordures de map
            move_target_x, move_target_y = self._clamp_position((move_target_x, move_target_y), bf)

            unit.current_order = {"type": "move_to", "target": (move_target_x, move_target_y)}  # move to pour pas attaqer les ennemis sur le chemin
        else:
            unit.current_order = {"type": "attack_unit", "target": primary_target}

    def _micro_pikeman_protector(self, unit: Unit, enemies: list["Unit"], protect_target_pos: tuple, default_target_pos: tuple, bf: Battlefield):
        """Logique : S'interposer entre la menace et les protégés."""
        # 1. CIBLAGE
        knights = self._filter_enemies(enemies, ["knight"])
        threats = knights if knights else [e for e in enemies if e.is_alive()]

        if not threats:
            unit.current_order = {"type": "attack_move", "target": default_target_pos}
            return

        # 2. PROJECTION DU MOUVEMENT
        dir_x, dir_y = self.soustract_vec(default_target_pos, protect_target_pos)
        proj_ax, proj_ay = self._projection_vector(protect_target_pos, self.normalize_vec((dir_x, dir_y)), 10.0)  # On projette x mètres devant le groupe

        # 3. INTERCEPTION DE LA MENACE
        nearest_threat = min(threats, key=lambda e: (e.position[0] - proj_ax) ** 2 + (e.position[1] - proj_ay) ** 2)
        is_fast_threat = nearest_threat.name.lower() in ["knight"]

        # Calcul du point de blocage
        dx, dy = self.soustract_vec(nearest_threat.position, (proj_ax, proj_ay))
        dist_threat = (dx**2 + dy**2) ** 0.5

        # --- LOGIQUE D'INTERCEPTION ---
        if is_fast_threat:
            # CAS 1 : CONTRE CAVALERIE
            if dist_threat > 15.0:
                ratio = 0.2
            else:
                ratio = 0.6  # On va chercher l'ennemi à 60% du chemin (Agressif)
        else:
            # CAS 2 : CONTRE INFANTERIE
            ratio = 0.1  # On ne s'avance que de 10% vers l'ennemi (Défensif)

        block_x, block_y = self._projection_vector((proj_ax, proj_ay), (dx, dy), ratio)

        # --- ACTION ---
        if unit.dist_to(nearest_threat) < unit.attack_range + 0.5:
            self._order_attack_opti(unit, nearest_threat)
        else:
            if dist_threat < 8.0:
                unit.current_order = {"type": "attack_move", "target": (block_x, block_y)}
            else:
                unit.current_order = {"type": "move_to", "target": (block_x, block_y)}

    def _micro_generic_attack(self, unit: Unit, enemies: list["Unit"], bf: Battlefield):
        """
        Attaque intelligente : Garde sa cible actuelle si possible,
        sinon cherche la plus faible à proximité.
        """
        # PERSISTANCE
        if unit.current_order and unit.current_order["type"] == "attack_unit":
            current_target = unit.current_order["target"]
            # Si la cible est toujours vivante et visible, on continue le focus
            if current_target.is_alive() and unit.dist_to(current_target) <= unit.vision_range:
                return

        # SÉLECTION DE CIBLE
        target = CombatSystem.choose_weakest_target(unit, enemies, bf)

        if not target:
            target = CombatSystem.choose_nearest_target(unit, enemies, bf)
        if target:
            self._order_attack_opti(unit, target)
            return
        else:
            self._order_regroup(unit, bf)
