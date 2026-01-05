from __future__ import annotations

from typing import TYPE_CHECKING

from src.engine.system import CombatSystem

from .general_base import BaseGeneral

if TYPE_CHECKING:
    from src.engine.battlefield import Battlefield


class GeneralBraindead(BaseGeneral):
    """
    Captain BRAINDEAD - Pure Reactive Aggression.

    Strategy: ATTACK VISIBLE ENEMY
    - Units do NOT move unless pursuing a visible enemy.
    - As soon as an enemy is spotted (within vision_range), the unit moves to attack.
    - Prioritizes the nearest visible enemy.
    """

    def __init__(self, player_id: int):
        super().__init__(player_id, name="Captain BRAINDEAD")

    def update(self, battlefield: "Battlefield", tick: int, dt) -> None:
        """
        BRAINDEAD: Stratégie purement réactive.
        - Ne bouge jamais.
        - Tire seulement si un ennemi est DEJA à portée de tir (attack_range).
        """
        my_units = self.get_my_units(battlefield)
        enemies = self.get_enemy_units(battlefield)

        if not enemies:
            return

        for unit in my_units:
            if not unit.is_alive():
                continue

            # 1. On cherche la cible la plus proche parmi TOUS les ennemis
            # (Le général voit tout, mais l'unité ne tirera que si proche)
            target = CombatSystem.choose_nearest_target(unit, enemies, battlefield)

            if target:
                # 2. Vérification critique : Est-on à portée de TIR ?
                # (utilise attack_range, ex: 0.5 pour piquier, 5.0 pour arbalète)
                if unit.can_attack(target):
                    # OUI : On ordonne l'attaque DIRECTE (sans mouvement implicite)
                    unit.current_order = {"type": "attack_unit", "target": target}
                else:
                    # NON : On ne fait RIEN.
                    # Surtout pas de "move_towards". L'unité reste Idle.
                    unit.current_order = None
