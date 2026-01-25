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
        self.role = role
        self.target_position = (0, 0)


class GeneralSmart(BaseGeneral):
    def __init__(self, player_id: int):
        super().__init__(player_id, name="General SMART")
        self.squads = {"FRONTLINE": Squad([], "FRONTLINE"), "BACKLINE": Squad([], "BACKLINE"), "FLANKERS": Squad([], "FLANKERS"), "ROAMERS": Squad([], "ROAMERS")}
        self._squads_initialized = False

    def update(self, bf: Battlefield, tick: int, dt: float) -> None:
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
            self._maintain_squads()

        # 3. TACTIQUE & MICRO (Exécution par unité)
        for squad in self.squads.values():
            if not squad.units:
                continue
            self._execute_squad_tactics(squad, enemies, bf)

    # --- PHASE 1. INITIALISATION & MACRO ---
    def _initialize_squads(self, bf: Battlefield):
        """Scan complet de l'armée pour remplir les 4 escouades."""
        my_units = self.get_my_units(bf)

        for unit in my_units:
            name = unit.name.lower()

            # --- FRONTLINE ---
            if name in ["pikeman", "longswordsman", "cappedram"]:
                self.squads["FRONTLINE"].units.append(unit)

            # --- BACKLINE ---
            elif name in ["crossbowman", "eliteskirmisher", "onager", "scorpion"]:
                self.squads["BACKLINE"].units.append(unit)

            # --- FLANKERS ---
            elif name in ["knight", "lightcavalry"]:
                self.squads["FLANKERS"].units.append(unit)

            # --- ROAMERS ---
            elif name in ["cavalryarcher"]:
                self.squads["ROAMERS"].units.append(unit)

            else:
                assert False, f"Unknown unit type : {unit.name} : A IMPLEMENTER"

    def _maintain_squads(self):
        """Supprime les morts des listes. (O(N_vivants))."""
        for squad in self.squads.values():
            if squad.units:
                squad.units = [u for u in squad.units if u.is_alive()]

    def _macro_strategy(self, enemies, bf: Battlefield):
        """Définit la cible globale de chaque squad."""
        # enemy_clusters = self._analyze_enemy_clusters(enemies)
        ennemy_center = self._get_centroid(enemies)
        my_units = bf.get_my_units(self.player_id)
        if not my_units:
            return
        for squad in self.squads.values():
            squad.target_position = ennemy_center

    # --- PHASE 2. DISPATCHER TACTIQUE ---
    def _execute_squad_tactics(self, squad: Squad, all_enemies: list[Unit], bf: Battlefield):
        for unit in squad.units:
            if not unit.is_alive():
                continue

            name = unit.name.lower()

            # --- LOGIQUE FRONTLINE ---
            if name == "cappedram":
                self._micro_ram_tank(unit, all_enemies)
            elif name == "pikeman":
                backline_units = self.squads["BACKLINE"].units
                protect_pos = self._get_centroid(backline_units) if backline_units else unit.position
                # self._micro_pikeman_protector(unit, all_enemies, protect_pos)
                self._micro_pikeman_protector(unit, all_enemies, protect_pos, squad.target_position, bf)
            elif name == "longswordsman":
                self._micro_swordsman_charger(unit, all_enemies, bf)

            # --- LOGIQUE BACKLINE ---
            elif name == "eliteskirmisher":
                self._micro_skirmisher_meatshield(unit, all_enemies, bf)
            elif name == "crossbowman":
                self._micro_crossbow_sniper(unit, all_enemies, bf)
            elif name == "onager":
                self._micro_onager_artillery(unit, all_enemies, bf)
            elif name == "scorpion":
                self._micro_scorpion_support(unit, all_enemies, bf)

            # --- LOGIQUE FLANKERS ---
            elif name == "knight":
                self._micro_knight_brawler(unit, all_enemies, bf)
                # self._micro_knight_flanker(unit, all_enemies, squad.target_position, bf)
            elif name == "lightcavalry":
                self._micro_lightcav_assassin(unit, all_enemies, bf)

            # --- LOGIQUE ROAMERS ---
            elif name == "cavalryarcher":
                self._micro_cavalry_archer_kiter(unit, all_enemies, bf)

            else:
                # Comportement générique (Fallback)
                self._micro_generic_attack(unit, all_enemies, bf)

    # --- 3. MICRO-GESTION SPÉCIFIQUE ---

    # --- FRONTLINE ---

    def _micro_ram_tank(self, unit: Unit, enemies: list[Unit]):
        """avance vers les archers pour tanker."""
        # Cible prioritaire : Archers et Sièges
        targets = self._filter_enemies(enemies, ["crossbowman", "eliteskirmisher", "cavalryarcher", "scorpion"])
        if not targets:
            targets = enemies  # Sinon n'importe qui

        # Il n'attaque pas (Dmg 3), il MOVE sur eux
        target = self._get_nearest(unit, targets)
        if target:
            unit.current_order = {"type": "move_to", "target": target.position}

    def _micro_swordsman_charger(self, unit: Unit, enemies: list[Unit], bf: Battlefield):
        """Charge l'infanterie adverse."""
        # Appétence : Piquiers, autres épéistes
        infantry = self._filter_enemies(enemies, ["pikeman", "longswordsman", "skirmisher"])
        target = self._get_best_target(unit, infantry, enemies)

        if target:
            self._order_attack_opti(unit, target)

    def _micro_pikeman_protector(self, unit: Unit, enemies: list["Unit"], protect_target_pos: tuple, default_target_pos: tuple, bf: Battlefield):
        """
        Logique de protection hybride :
        1. SELF-DEFENSE : Si on peut taper quelqu'un, on tape (Priorité Cavalerie > PV bas).
        2. MISSION : Sinon, on intercepte la cavalerie ou on avance vers le front.
        """
        # --- 1. ACQUISITION DES CIBLES LOCALES ---
        enemies_in_range = [e for e in enemies if e.is_alive() and unit.dist_to(e) <= unit.attack_range + 0.5]

        if enemies_in_range:
            knights_nearby = self._filter_enemies(enemies_in_range, ["knight", "lightcavalry", "cavalryarcher"])
            target = min(knights_nearby if knights_nearby else enemies_in_range, key=lambda e: e.hp)
            self._order_attack_opti(unit, target)
            return

        # --- 2. ANALYSE DE LA MENACE STRATÉGIQUE ---
        knights = self._filter_enemies(enemies, ["knight", "lightcavalry", "cavalryarcher"])
        threats = knights if knights else [e for e in enemies if e.is_alive()]

        if not threats:
            unit.current_order = {"type": "attack_move", "target": default_target_pos}
            return

        nearest_threat = min(threats, key=lambda e: unit.dist_to(e))
        is_cavalry_threat = nearest_threat.name.lower() in ["knight", "lightcavalry", "cavalryarcher"]

        if is_cavalry_threat and unit.dist_to(nearest_threat) > 15.0:
            is_cavalry_threat = False

        # --- 3. EXÉCUTION DE LA MISSION ---

        # BRANCHE A : INFANTERIE (Approche en bloc)
        if not is_cavalry_threat:
            unit.current_order = {"type": "attack_move", "target": nearest_threat.position}
            return

        # BRANCHE B : CAVALERIE (Interception géométrique)
        # calcule du point de blocage entre nos archers et la charge
        dir_x, dir_y = self.soustract_vec(default_target_pos, protect_target_pos)
        proj_ax, proj_ay = self._projection_vector(protect_target_pos, self.normalize_vec((dir_x, dir_y)), 6.0)

        dx, dy = self.soustract_vec(nearest_threat.position, (proj_ax, proj_ay))
        dist_threat = (dx**2 + dy**2) ** 0.5
        block_x, block_y = self._projection_vector((proj_ax, proj_ay), (dx, dy), 0.5)

        if dist_threat < 4.0:
            unit.current_order = {"type": "attack_move", "target": (block_x, block_y)}
        else:
            unit.current_order = {"type": "move_to", "target": (block_x, block_y)}

    # --- BACKLINE ---
    def _micro_skirmisher_meatshield(self, unit: Unit, enemies: list[Unit], bf: Battlefield):
        # --- GESTION DE LA FUITE ---
        nearest = self._get_nearest(unit, enemies)
        if nearest:
            dist = unit.dist_to(nearest)
            ranged_units = ["crossbowman", "eliteskirmisher", "cavalryarcher", "scorpion", "onager"]
            is_ranged_threat = nearest.name.lower() in ranged_units

            if not is_ranged_threat and dist < 5.0:
                self._do_kiting_move(unit, [nearest], bf)
                return

        # --- CIBLAGE ---
        enemy_archers = self._filter_enemies(enemies, ["crossbowman", "eliteskirmisher", "cavalryarcher"])
        target = self._get_nearest(unit, enemy_archers) if enemy_archers else self._get_nearest(unit, enemies)

        # --- ACTION AVEC PRESSION VERS L'AVANT ---
        if target:
            real_attack_range = unit.attack_range
            tanking_range = real_attack_range * 0.70

            dist_to_target = unit.dist_to(target)
            if unit.reload_timer > 0 or dist_to_target > tanking_range:
                unit.current_order = {"type": "move_to", "target": target.position}
            else:
                self._order_attack_opti(unit, target)

    def _micro_crossbow_sniper(self, unit: Unit, enemies: list[Unit], bf: Battlefield):
        """
        Logique Mixte :
        1. Fuite si menacé.
        2. Sniper : Focus LOURD en priorité.
        3. Stutter Step : Avance pendant le rechargement pour compresser la ligne.
        """
        nearest = CombatSystem.choose_nearest_target(unit, enemies, bf)
        is_reloading = unit.reload_timer > 0

        # --- 1. FUITE ---
        if nearest:
            (is_threatened, is_critical) = self.is_threatened(unit, nearest)
            if is_threatened:
                if is_critical or is_reloading:
                    (move_target_x, move_target_y) = self._fuite_strategique(unit, enemies, bf)
                    if not (move_target_x, move_target_y) == unit.position:
                        unit.current_order = {"type": "move_to", "target": (move_target_x, move_target_y)}
                        return

        # --- 2. SÉLECTION DE CIBLE
        visible_enemies = [e for e in enemies if e.is_alive() and unit.dist_to(e) <= unit.vision_range]
        target = None

        if visible_enemies:
            heavy_targets_in_sight = [e for e in visible_enemies if e.name.lower() in ["knight", "longswordsman"]]
            if heavy_targets_in_sight:
                target = self._get_best_target(unit, heavy_targets_in_sight, visible_enemies)
            else:
                target = self._get_nearest(unit, visible_enemies)
        else:
            heavy_global = self._filter_enemies(enemies, ["knight", "longswordsman"])
            target = self._get_nearest(unit, heavy_global) if heavy_global else self._get_nearest(unit, enemies)

        if not target:
            target = nearest

        # --- 3. ACTION  ---
        if target:
            if not is_reloading:
                self._order_attack_opti(unit, target)
            else:
                dist = unit.dist_to(target)
                ideal_range_ratio = 0.75
                if dist > unit.attack_range * ideal_range_ratio:
                    unit.current_order = {"type": "move_to", "target": target.position}
                else:
                    pass

    def _micro_onager_artillery(self, unit: Unit, enemies: list[Unit], bf: Battlefield):
        """Tir de zone. Sécurité distance min."""
        # Sécurité Min Range (3m)
        nearest = self._get_nearest(unit, enemies)
        if nearest and unit.dist_to(nearest) < 4.0:  # Marge de 1m
            self._do_kiting_move(unit, [nearest], bf)
            return

        center_mass = self._get_centroid(enemies)  # Vise le tas
        # On trouve l'ennemi le plus proche du centre de masse
        best_target = min(enemies, key=lambda e: math.dist(e.position, center_mass))

        self._order_attack_opti(unit, best_target)

    def _micro_scorpion_support(self, unit: Unit, enemies: list[Unit], bf: Battlefield):
        """Comme l'arbalétrier mais fuit plus vite."""
        nearest = self._get_nearest(unit, enemies)
        if nearest and unit.dist_to(nearest) < 8.0:  # Très fragile
            self._do_kiting_move(unit, [nearest], bf)
            return

        target = CombatSystem.choose_nearest_target(unit, enemies, bf)
        if target:
            self._order_attack_opti(unit, target)

    # --- FLANKERS ---
    def _micro_knight_brawler(self, unit: Unit, enemies: list[Unit], bf: Battlefield):
        """Préfère combattre les cavaliers."""

        # --- PERSISTANCE ---
        if unit.current_order and unit.current_order["type"] == "attack_unit":
            current_target = unit.current_order["target"]
            if current_target.is_alive() and unit.dist_to(current_target) <= unit.attack_range + 0.5:
                return

        # Filtrage de base
        valid_enemies = [e for e in enemies if e.name.lower() != "cappedram"]
        if not valid_enemies:
            return

        target = None

        # ---  ANALYSE LOCALE ---
        visible_enemies = [e for e in valid_enemies if e.is_alive() and unit.dist_to(e) <= unit.vision_range]

        if visible_enemies:
            local_priorities = [e for e in visible_enemies if e.name.lower() in ["knight", "cavalryarcher", "longswordsman"]]

            if local_priorities:
                target = self._get_nearest(unit, local_priorities)
            else:
                target = self._get_nearest(unit, visible_enemies)

        else:
            global_priorities = self._filter_enemies(valid_enemies, ["knight", "cavalryarcher", "longswordsman"])

            if global_priorities:
                target = self._get_nearest(unit, global_priorities)
            else:
                target = self._get_nearest(unit, valid_enemies)

        if target:
            self._order_attack_opti(unit, target)

    def _micro_lightcav_assassin(self, unit: Unit, enemies: list[Unit], bf: Battlefield):
        """Contourne les Piquiers. Focus Siège/Archers."""
        # 1. Évitement des Piquiers (Champ de potentiel simplifié)
        pikes = self._filter_enemies(enemies, ["pikeman", "halberdier"])
        nearest_pike = self._get_nearest(unit, pikes)

        if nearest_pike and unit.dist_to(nearest_pike) < 6.0:
            # Vecteur de fuite par rapport au piquier
            self._do_kiting_move(unit, enemies, bf)
            return

        # 2. Cibles : Siège > Archers
        targets = self._filter_enemies(enemies, ["onager", "scorpion", "crossbowman", "eliteskirmisher"])
        target = self._get_best_target(unit, targets, enemies)

        if target:
            # On utilise move_to si on est loin pour utiliser la vitesse, attack si proche
            if unit.dist_to(target) > 2.0:
                unit.current_order = {"type": "move_to", "target": target.position}
            else:
                self._order_attack_opti(unit, target)

    def _micro_knight_flanker(self, unit: Unit, enemies: list["Unit"], target_pos: tuple, bf: Battlefield):
        # 1. Identifier les Cibles et les Menaces
        valid_enemies = [e for e in enemies if e.name.lower() != "cappedram"]
        priority_targets = self._filter_enemies(valid_enemies, ["knight", "cavalryarcher", "longswordsman"])
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
            ndx, ndy = self.scale_vec((ndx, ndy), 2.5)  # POIDS D'ATTRACTION FORT (2.0) pour se mieux se diriger vers la cible

        # B. Vecteur de Répulsion (Éviter les Piquiers)
        # On ne regarde que les piquiers sur le chemin (moins de xm, valeur arbitraire qu'on peut changer)
        avoid_radius = 5.0
        repulsion_x, repulsion_y = 0.0, 0.0

        for threat in ennemies_threats:
            d_threat = unit.dist_to(threat)
            if d_threat < avoid_radius:
                # Vecteur : De la menace vers le kngiht (pour s'éloigner)
                rx, ry = self.soustract_vec(unit.position, threat.position)
                rx, ry = self.normalize_vec((rx, ry))

                # Force inversement proportionnelle à la distance (linéaire et pas exponentielle)
                force = 15 * ((1.0 - (d_threat / avoid_radius)) ** 2)

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

    # --- ROAMERS ---
    def _micro_cavalry_archer_kiter(self, unit: Unit, enemies: list[Unit], bf: Battlefield):
        """Hit & Run avec Fuite Stratégique."""
        nearest = self._get_nearest(unit, enemies)

        if nearest:
            (is_threatened, _) = self.is_threatened(unit, nearest)
            if is_threatened:
                self._do_kiting_move(unit, enemies, bf)
                return

        target = CombatSystem.choose_weakest_target(unit, enemies, bf)
        if target:
            self._order_attack_opti(unit, target)

    # --- UTILS ---

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

    def _do_kiting_move(self, unit: Unit, enemies: list[Unit], bf: Battlefield):
        """Wrapper qui appelle la fonction _fuite_strategique et applique l'ordre."""
        (mx, my) = self._fuite_strategique(unit, enemies, bf)
        if (mx, my) != unit.position:
            unit.current_order = {"type": "move_to", "target": (mx, my)}

    def _is_path_obscured(self, unit: Unit, target: Unit, bf: Battlefield) -> bool:
        """
        Vérifie si le chemin direct vers la cible est bloqué par une autre unité (Allié ou Ennemi).
        Utilisé pour éviter de charger une cible inaccessible derrière un mur de chair.
        """
        dist_target = unit.dist_to(target)
        obstacles = bf.units_in_radius_opti(unit.position[0], unit.position[1], dist_target)

        valid_obstacles = [o for o in obstacles if o != unit and o != target and o.is_alive()]

        if not valid_obstacles:
            return False

        # 2. Pré-calcul du segment AB (Unit -> Target)
        ax, ay = unit.position
        bx, by = target.position
        dx, dy = bx - ax, by - ay
        seg_len_sq = dx * dx + dy * dy

        if seg_len_sq == 0:
            return False

        collision_threshold = 0.8

        for obs in valid_obstacles:
            cx, cy = obs.position

            # Projection du point C sur le segment AB
            t = ((cx - ax) * dx + (cy - ay) * dy) / seg_len_sq

            # On regarde si l'obstacle est ENTRE le début et la fin (0 < t < 1)
            if 0 < t < 1:
                proj_x = ax + t * dx
                proj_y = ay + t * dy
                dist_sq = (cx - proj_x) ** 2 + (cy - proj_y) ** 2

                if dist_sq < collision_threshold**2:
                    return True  # CHEMIN BLOQUÉ

        return False
