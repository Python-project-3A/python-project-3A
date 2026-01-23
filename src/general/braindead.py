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
        BRAINDEAD: pour l'instant : innactif total, répond seulement aux attaquess
        """
        my_units = self.get_my_units(battlefield)
        enemies = self.get_enemy_units(battlefield)

        if not enemies:
            return

        for unit in my_units:
            if not unit.is_alive():
                continue
            target = CombatSystem.choose_nearest_target(unit, enemies, battlefield)

            if target:
                # if unit.dist_to(target) <= unit.vision_range: #Si on veut un braindead moins passif
                if unit.can_attack(target):
                    self._order_attack_opti(unit, target)
                else:
                    unit.current_order = None
