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

    def update(self, bf: Battlefield, tick: int) -> None:
        self.tick_counter = tick

        # 1. PERCEPTION (Macro) - TODO : Ne pas faire à chaque tick si ça rame (tous les 5/10/15 ticks)
        my_units = bf.get_my_units(self.player_id)
        enemies = bf.get_enemy_units(self.player_id)
        if not enemies or not my_units:
            return

        # Analyse des clusters ennemis (Barycentres des groupes)
        enemy_clusters = self._analyze_enemy_clusters(enemies)

        # 2. STRATÉGIE (Gestion des Escouades)
        # On réalloue les unités aux escouades si besoin
        self._manage_squads(my_units, enemy_clusters)

        # 3. TACTIQUE & MICRO (Exécution par unité)
        # Au lieu de boucler sur les unités, on boucle sur les escouades
        for squad in self.squads:
            self._execute_squad_tactics(squad, enemies, bf)

    # --- PHASE 1: PERCEPTION ---
    def _analyze_enemy_clusters(self, enemies: list[Unit]):
        # TODO: Implémenter un K-Means simple ou une heuristique de distance
        # Pour l'instant : Tout le monde est un seul cluster (le gros tas)
        return [{"center": self._get_centroid(enemies), "units": enemies}]

    def _get_centroid(self, units: list[Unit]) -> tuple[float, float]:
        if not units:
            return (0, 0)
        sx = sum(u.position[0] for u in units)
        sy = sum(u.position[1] for u in units)
        return (sx / len(units), sy / len(units))

    # --- PHASE 2: STRATÉGIE ---
    def _manage_squads(self, my_units: list[Unit], enemy_clusters):
        # Pour l'instant:
        # - knight -> Escouade Flank
        # - crossbowman -> Escouade DPS
        # - pikeman -> Escouade Tank

        # On vide et on recrée les escouades -> TODO A améliorer aussi
        knights = [u for u in my_units if u.name.lower() == "knight"]
        crossbowman = [u for u in my_units if u.name.lower() == "crossbowman"]
        pikemen = [u for u in my_units if u.name.lower() == "pikeman"]

        self.squads = []
        if knights:
            self.squads.append(Squad(knights, "FLANKER"))
        if crossbowman:
            self.squads.append(Squad(crossbowman, "DPS"))
        if pikemen:
            self.squads.append(Squad(pikemen, "TANK"))

        # Assignation des cibles d'escouade
        main_enemy_pos = enemy_clusters[0]["center"]
        for squad in self.squads:
            squad.target_position = main_enemy_pos

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
                my_archers = [s for s in self.squads if s.role == "DPS"]
                if my_archers and my_archers[0].units:
                    protect_position = self._get_centroid(my_archers[0].units)
                    self._micro_pikeman_protector(unit, all_enemies, protect_position, target_pos, bf)
                else:
                    self._micro_generic_attack(unit, all_enemies)

            elif squad.role == "FLANKER":
                self._micro_knight_flanker(unit, all_enemies, target_pos, bf)

    # --- MICRO-GESTION UNITAIRE ---

    def _micro_archer(self, unit: Unit, enemies: list[Unit], target_pos: tuple, bf: Battlefield):
        nearest = CombatSystem.choose_nearest_target(unit, enemies, bf)
        safe_dist = unit.attack_range * 0.85  # pourcentage de portée à partir de laquelle il est en danger

        # --- FUITE ---

        # Condition de fuite :  Un ennemi est trop près ET Je ne suis PAS prêt à tirer OU l'ennemi est vraiment TROP près
        critical_dist = 3.0  # Danger de mort immédiat
        is_threatened = nearest and unit.dist_to(nearest) < safe_dist
        is_critical = nearest and unit.dist_to(nearest) < critical_dist
        is_reloading = unit.reload_timer > 0

        if is_threatened:
            # Cas 1 : DANGER IMMÉDIAT (Trop près) OU Cas 2 : JE RECHARGE (Pas prêt à tirer)
            if is_critical or is_reloading:
                self._fuite_strategique(unit, enemies, bf)
                return  # Si on fuit, on ne tire pas ce tick-ci ?? Question dans le Notion
            # Cas 3 : DANGER MODÉRÉ + ARME PRÊTE
            else:
                # Je suis en danger MAIS mon arme est prête -> JE TIRE (Stutter Step)
                # On laisse le code continuer vers la section ATTACK -> séparer dans plusieurs fonctions ?
                pass

        # --- ATTAQUE ---  -> Si on est en sécurité, on applique la stratégie DPS
        # On veut le "Focus Fire" : Taper l'ennemi le plus faible à portée
        target = CombatSystem.choose_weakest_target(unit, enemies, bf)

        # Si pas de cible faible trouvée, on se rabat sur le plus proche (fallback)
        if not target:
            target = nearest

        if target:
            # Optimisation : Ne pas spammer l'ordre si c'est déjà la même cible
            if unit.current_order and unit.current_order.get("type") == "attack_unit" and unit.current_order.get("target") == target:
                return

            unit.current_order = {"type": "attack_unit", "target": target}

    def _micro_knight_flanker(self, unit: Unit, enemies: list["Unit"], target_pos: tuple, bf: Battlefield):
        # 1. Identifier les Cibles et les Menaces
        priority_targets = self._filter_enemies(enemies, ["crossbowman", "skirmisher"])
        if not priority_targets:
            self._micro_generic_attack(unit, enemies, bf)
            return

        ennemies_threats = self._filter_enemies(enemies, ["pikeman", "halberdier"])

        # 2. Trouver la cible la plus proche
        primary_target = CombatSystem.choose_nearest_target(unit, priority_targets, bf)
        dist_to_target = unit.dist_to(primary_target)

        # 3. Décision : CHARGE ou MANOEUVRE ?
        if dist_to_target < 2.0:  # si on est assez proche de la cible on attaque
            # Optimisation : Ne pas spammer l'ordre si c'est deja la meme cible
            if unit.current_order and unit.current_order.get("type") == "attack_unit" and unit.current_order.get("target") == primary_target:
                return
            unit.current_order = {"type": "attack_unit", "target": primary_target}
            return

        # 4. Calcul du Vecteur de Mouvement (Champs de Potentiel)

        # A. Vecteur d'Attraction (Vers la cible)
        dx, dy = self.soustract_vec(primary_target.position, unit.position)

        # Normalisation
        ndx, ndy = self.normalize_vec(dx, dy)
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
                rx, ry = self.normalize_vec(rx, ry)

                # Force inversement proportionnelle à la distance (linéaire et pas exponentielle)
                force = 3.0 * (1.0 - (d_threat / avoid_radius))

                repulsion_x += rx * force
                repulsion_y += ry * force

        # 5. Combinaison des vecteurs : Mouvement Final = Attraction + Répulsion
        final_vx, final_vy = self.add_vec((ndx, ndy), (repulsion_x, repulsion_y))

        # Normalisation finale
        final_vx, final_vy = self.normalize_vec(final_vx, final_vy)
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
        knights = [e for e in enemies if e.name.lower() == "knight" and e.is_alive()]
        threats = knights if knights else [e for e in enemies if e.is_alive()]

        if not threats:
            unit.current_order = {"type": "attack_move", "target": default_target_pos}
            return

        # 2. PROJECTION DU MOUVEMENT
        dir_x, dir_y = self.soustract_vec(default_target_pos, protect_target_pos)
        proj_ax, proj_ay = self._projection_vector(protect_target_pos, self.normalize_vec((dir_x, dir_y)), 6.0)  # On projette x mètres devant le groupe

        # 3. INTERCEPTION DE LA MENACE
        nearest_threat = min(threats, key=lambda e: (e.position[0] - proj_ax) ** 2 + (e.position[1] - proj_ay) ** 2)

        # Calcul du point de blocage
        dx, dy = self.soustract_vec(nearest_threat.position, (proj_ax, proj_ay))
        dist_threat = (dx**2 + dy**2) ** 0.5

        # Ratio dynamique :
        if dist_threat > 15.0:
            ratio = 0.2  # On reste à 20% du chemin vers l'ennemi (défensif)
        else:
            ratio = 0.5  # On va au contact (50%)

        block_x, block_y = self._projection_vector((proj_ax, proj_ay), (dx, dy), ratio)

        # --- ACTION ---
        if unit.dist_to(nearest_threat) < unit.attack_range + 0.5:
            unit.current_order = {"type": "attack_unit", "target": nearest_threat}
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
            unit.current_order = {"type": "attack_unit", "target": target}
        else:
            self._order_regroup(unit, bf)
