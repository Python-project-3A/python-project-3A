from __future__ import annotations

from src.engine.battlefield import Battlefield
from src.engine.system import CombatSystem

from .general_base import BaseGeneral


class GeneralDaft(BaseGeneral):
    """
    Major DAFT - Dumb as fuck.

    Strategy: ATTACK NEAREST ENEMY
    - Every unit attacks the nearest enemy
    - No formations
    - No tactics
    - No counter-type considerations
    - Pure mindless aggression
    """

    def __init__(self, player_id: int):
        super().__init__(player_id, name="Major DAFT")

    def update(self, battlefield: "Battlefield", tick: int) -> None:
        """
        DAFT: Agressivité totale.
        - Utilise la vision globale du Général.
        - Ignore la vision_range locale.
        - Chasse l'ennemi le plus proche sur toute la carte.
        """
        my_units = self.get_my_units(battlefield)
        enemies = self.get_enemy_units(battlefield)

        # Filtre ennemis vivants
        alive_enemies = [e for e in enemies if e.is_alive()]
        if not alive_enemies:
            return

        # Gestion anti-embouteillage (Conga Line)
        target_counts = {e.id: 0 for e in alive_enemies}
        CROWDING_PENALTY = 3.0  # Ajoute virtuellement 3m de distance par attaquant déjà dessus

        for unit in my_units:
            if not unit.is_alive():
                continue

            # 1. Trouver la cible optimale sur TOUTE la carte
            best_target = None
            best_score = float("inf")

            for enemy in alive_enemies:
                dist = unit.dist_to(enemy)
                # On choisit le plus proche, mais on évite ceux qui sont déjà submergés
                score = dist + (target_counts[enemy.id] * CROWDING_PENALTY)

                if score < best_score:
                    best_score = score
                    best_target = enemy

            # 2. Donner l'ordre de chasse
            if best_target:
                # L'ordre 'attack_unit' va déclencher le mouvement via UnitController
                # jusqu'à ce que l'unité soit à portée d'attaque.
                unit.current_order = {"type": "attack_unit", "target": best_target}
                target_counts[best_target.id] += 1
