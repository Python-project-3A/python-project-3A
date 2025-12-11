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
                # Les piquiers doivent protéger les archers s'ils existent
                # Sinon ils attaquent
                my_archers = [s for s in self.squads if s.role == "DPS"]
                if my_archers:
                    protect_target = self._get_centroid(my_archers[0].units)
                    self._micro_pikeman_protector(unit, all_enemies, protect_target, target_pos)
                else:
                    self._micro_generic_attack(unit, all_enemies)

            elif squad.role == "FLANKER":
                self._micro_knight_flanker(unit, all_enemies, target_pos)

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

    def _micro_knight_flanker(self, unit: Unit, enemies: list[Unit], target_pos: tuple):
        pass

    def _micro_pikeman_protector(self, unit: Unit, enemies: list[Unit], protect_pos: tuple, threat_pos: tuple):
        pass

    def _micro_generic_attack(self, unit: Unit, all_enemies: list[Unit]):
        pass

    # --- HELPERS --- TODO : ( _order_flee, etc.)

    def _fuite_strategique(self, unit: "Unit", enemies: list["Unit"], bf: "Battlefield"):
        """
        Calcule un vecteur de fuite basé sur la somme des répulsions.
        Prend en compte : Les ennemis proches, les murs.
        """
        # Vecteur de mouvement final (x, y)
        move_x, move_y = 0.0, 0.0

        # 1. RÉPULSION DES ENNEMIS (Barycentre pondéré)
        threat_radius = 10.0
        threat_count = 0

        for enemy in enemies:
            if not enemy.is_alive():
                continue

            dx = unit.position[0] - enemy.position[0]
            dy = unit.position[1] - enemy.position[1]
            dist_sq = dx * dx + dy * dy

            if dist_sq < threat_radius * threat_radius:  # répulsion inversement proportionnelle à la distance
                dist = math.sqrt(dist_sq)
                factor = 1.0 / (dist + 0.1)  # +0.1 pour éviter division par zéro

                move_x += (dx / dist) * factor
                move_y += (dy / dist) * factor
                threat_count += 1

        # 2. RÉPULSION DES MURS
        wall_margin = 5.0  # valeur arbitraire qu'on peut changer

        # Mur Gauche (x=0) -> Pousse vers la droite (+x)
        if unit.position[0] < wall_margin:
            force = (wall_margin - unit.position[0]) / wall_margin
            move_x += force * 2.0  # *2.0 pour donner priorité à l'évitement du mur

        # Mur Droit (x=Width) -> Pousse vers la gauche (-x)
        if unit.position[0] > bf.width - wall_margin:
            force = (unit.position[0] - (bf.width - wall_margin)) / wall_margin
            move_x -= force * 2.0

        # Mur Haut (y=0) -> Pousse vers le bas (+y)
        if unit.position[1] < wall_margin:
            force = (wall_margin - unit.position[1]) / wall_margin
            move_y += force * 2.0

        # Mur Bas (y=Height) -> Pousse vers le haut (-y)
        if unit.position[1] > bf.height - wall_margin:
            force = (unit.position[1] - (bf.height - wall_margin)) / wall_margin
            move_y -= force * 2.0

        # 3. NORMALISATION & APPLICATION
        length = math.hypot(move_x, move_y)
        if length <= 0.01:
            return
        else:  # lengyh > 0.1
            move_x /= length
            move_y /= length

            # On projette le point cible loin devant
            target_x = unit.position[0] + move_x * 10.0
            target_y = unit.position[1] + move_y * 10.0

            # Clamp final de sécurité
            target_x = max(0, min(target_x, bf.width - 1))
            target_y = max(0, min(target_y, bf.height - 1))

            unit.current_order = {"type": "move_to", "target": (target_x, target_y)}
        unit.current_order = {"type": "move_to", "target": (target_x, target_y)}
